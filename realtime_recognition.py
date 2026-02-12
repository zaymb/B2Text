import pyaudio
import numpy as np
import whisper
import threading
import queue
import time
import wave
from datetime import datetime
import os

class RealtimeRecognizer:
    def __init__(self, model_name="base", device_name=None, initial_prompt="",
                 enable_hallucination_filter=True,
                 silence_warning_threshold=None, silence_stop_threshold=None,
                 on_silence_warning=None, on_silence_stop=None, on_speech_resumed=None):
        """
        初始化实时识别器
        :param model_name: whisper模型名称 (tiny, base, small, medium, large)
        :param device_name: 音频设备名称，如果为None则自动检测BlackHole
        :param initial_prompt: 初始提示词，用于提高识别准确度
        :param enable_hallucination_filter: 是否启用幻觉过滤
        :param silence_warning_threshold: 静音警告阈值（秒），None 表示不启用
        :param silence_stop_threshold: 静音自动停止阈值（秒），None 表示不启用
        :param on_silence_warning: 静音警告回调 fn(duration)
        :param on_silence_stop: 静音自动停止回调 fn(duration)
        :param on_speech_resumed: 声音恢复回调 fn()
        """
        self.model = whisper.load_model(model_name)
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.text_queue = queue.Queue()
        self.device_index = None
        self.device_name = device_name
        self.initial_prompt = initial_prompt or "以下是普通话的内容。"

        # 音频参数
        self.FORMAT = pyaudio.paFloat32
        self.CHANNELS = 2
        self.RATE = 16000
        self.CHUNK = 1024 * 2
        self.RECORD_SECONDS = 5  # 每5秒处理一次

        # 幻觉检测参数
        self.enable_hallucination_filter = enable_hallucination_filter
        self.energy_threshold = 0.001  # 音频能量阈值
        self.recent_texts = []  # 最近识别的文本，用于检测重复
        self.max_recent_texts = 5  # 保留最近5个识别结果
        self.hallucination_keywords = []  # 从initial_prompt提取关键词
        if initial_prompt and enable_hallucination_filter:
            # 提取prompt中的关键词用于幻觉检测
            import re
            words = re.findall(r'[\u4e00-\u9fa5]+', initial_prompt)
            self.hallucination_keywords = [w for w in words if len(w) > 2]

        # 静音检测配置
        self.silence_warning_threshold = silence_warning_threshold
        self.silence_stop_threshold = silence_stop_threshold
        self.on_silence_warning = on_silence_warning
        self.on_silence_stop = on_silence_stop
        self.on_speech_resumed = on_speech_resumed
        self._silence_start_time = None
        self._silence_warning_sent = False

        # 查找BlackHole设备
        self.find_blackhole_device()

    def is_silence(self, audio_array):
        """检测音频是否为静音"""
        energy = np.sum(audio_array ** 2) / len(audio_array)
        return energy < self.energy_threshold

    def is_hallucination(self, text):
        """检测是否为幻觉文本"""
        if not text or len(text.strip()) < 2:
            return True

        # 检查是否为重复文本
        if self.recent_texts:
            # 如果与最近的文本完全相同
            if text in self.recent_texts:
                return True
            # 如果连续3个文本都很相似（编辑距离很小）
            if len(self.recent_texts) >= 2:
                similar_count = sum(1 for recent in self.recent_texts[-2:]
                                  if self.similarity(text, recent) > 0.8)
                if similar_count >= 2:
                    return True

        # 检查是否主要包含prompt关键词
        if self.hallucination_keywords:
            keyword_count = sum(1 for kw in self.hallucination_keywords if kw in text)
            if keyword_count >= len(self.hallucination_keywords) * 0.5:
                # 如果文本主要由prompt关键词组成
                text_without_keywords = text
                for kw in self.hallucination_keywords:
                    text_without_keywords = text_without_keywords.replace(kw, '')
                if len(text_without_keywords.strip()) < len(text) * 0.3:
                    return True

        # 检查是否包含典型的幻觉模式
        hallucination_patterns = [
            '谢谢观看', '感谢观看', '请订阅', '点赞', '关注我',
            '下期再见', '我们下期', '拜拜', 'bye', 'thank you',
            '字幕制作', '字幕组', '© '
        ]
        for pattern in hallucination_patterns:
            if pattern.lower() in text.lower():
                return True

        return False

    def similarity(self, s1, s2):
        """计算两个字符串的相似度（简单版）"""
        if not s1 or not s2:
            return 0
        # 简单的字符重叠率
        common = sum(1 for c in s1 if c in s2)
        return common / max(len(s1), len(s2))

    def find_blackhole_device(self):
        """查找虚拟音频设备（BlackHole或Background Music）"""
        info = self.p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')

        virtual_devices = []
        print("\n可用的音频设备:")
        print("-" * 50)

        for i in range(0, numdevices):
            device_info = self.p.get_device_info_by_host_api_device_index(0, i)
            device_name = device_info.get('name')
            max_channels = device_info.get('maxInputChannels')

            print(f"设备 {i}: {device_name} (输入通道: {max_channels})")

            # 查找虚拟音频设备
            if max_channels > 0:
                if self.device_name:
                    if self.device_name.lower() in device_name.lower():
                        self.device_index = i
                        print(f"  -> 找到指定设备: {device_name}")
                        return
                # 支持BlackHole和Background Music
                elif 'blackhole' in device_name.lower() or 'background music' in device_name.lower():
                    virtual_devices.append((i, device_name))

        # 优先选择Background Music，其次是BlackHole
        if virtual_devices and not self.device_index:
            # 优先选择Background Music
            for idx, name in virtual_devices:
                if 'background music' in name.lower():
                    self.device_index = idx
                    print(f"\n自动选择Background Music设备: {name}")
                    return

            # 否则选择第一个虚拟设备
            self.device_index = virtual_devices[0][0]
            print(f"\n自动选择虚拟音频设备: {virtual_devices[0][1]}")
        elif not self.device_index:
            print("\n警告: 未找到虚拟音频设备（BlackHole/Background Music），将使用默认输入设备")
            self.device_index = self.p.get_default_input_device_info()['index']

    def start_recording(self):
        """开始录音"""
        if self.is_recording:
            print("已经在录音中...")
            return

        print(f"\n开始录音，使用设备索引: {self.device_index}")
        self.is_recording = True

        # 创建输出目录
        os.makedirs("outputs", exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_file = f"outputs/realtime_{timestamp}.txt"
        self.clean_output_file = f"outputs/realtime_{timestamp}_clean.txt"

        # 用于存储所有识别的文本（干净版本）
        self.all_texts = []

        # 打开音频流
        try:
            self.stream = self.p.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.CHUNK
            )

            # 启动录音线程
            self.record_thread = threading.Thread(target=self._record_audio)
            self.record_thread.start()

            # 启动识别线程
            self.recognize_thread = threading.Thread(target=self._recognize_audio)
            self.recognize_thread.start()

            print(f"录音已开始，识别结果将保存到: {self.output_file}")
            print("按 Ctrl+C 停止录音\n")

        except Exception as e:
            print(f"无法打开音频流: {e}")
            self.is_recording = False

    def _record_audio(self):
        """录音线程"""
        frames = []
        chunk_frames = int(self.RATE / self.CHUNK * self.RECORD_SECONDS)

        while self.is_recording:
            try:
                # 收集音频数据
                current_frames = []
                for _ in range(chunk_frames):
                    if not self.is_recording:
                        break
                    data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                    current_frames.append(data)

                if current_frames:
                    # 将音频数据加入队列
                    audio_data = b''.join(current_frames)
                    self.audio_queue.put(audio_data)

            except Exception as e:
                print(f"录音错误: {e}")
                break

    def _recognize_audio(self):
        """识别线程"""
        # 初始化带时间戳的文件
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(f"实时识别开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")

        # 初始化干净版本文件
        with open(self.clean_output_file, 'w', encoding='utf-8') as f:
            f.write("")  # 创建空文件

        while self.is_recording or not self.audio_queue.empty():
            try:
                # 从队列获取音频数据
                audio_data = self.audio_queue.get(timeout=1)

                # 转换为numpy数组
                audio_array = np.frombuffer(audio_data, dtype=np.float32)

                # 如果是双声道，转换为单声道
                if self.CHANNELS == 2:
                    audio_array = audio_array.reshape(-1, 2).mean(axis=1)

                # 归一化音频
                if np.max(np.abs(audio_array)) > 0:
                    audio_array = audio_array / np.max(np.abs(audio_array))

                # 检测是否为静音（仅在启用过滤时）
                if self.enable_hallucination_filter and self.is_silence(audio_array):
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 检测到静音，跳过...")

                    # 静音时长追踪（如果启用了静音检测）
                    if self.silence_warning_threshold and self.silence_stop_threshold:
                        if self._silence_start_time is None:
                            self._silence_start_time = time.time()
                        silence_duration = time.time() - self._silence_start_time

                        if silence_duration >= self.silence_stop_threshold:
                            if self.on_silence_stop:
                                self.on_silence_stop(silence_duration)
                            return  # 退出识别循环
                        elif silence_duration >= self.silence_warning_threshold and not self._silence_warning_sent:
                            if self.on_silence_warning:
                                self.on_silence_warning(silence_duration)
                            self._silence_warning_sent = True

                    continue
                else:
                    # 非静音：如果之前发过警告，触发恢复回调并重置
                    if self._silence_warning_sent and self.on_speech_resumed:
                        self.on_speech_resumed()
                    self._silence_start_time = None
                    self._silence_warning_sent = False

                # 使用Whisper识别
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在识别音频片段...")

                if self.enable_hallucination_filter:
                    # 启用幻觉过滤时，使用优化参数
                    result = self.model.transcribe(
                        audio_array,
                        language="zh",
                        initial_prompt=self.initial_prompt,
                        temperature=0.0,  # 降低随机性，减少幻觉
                        no_speech_threshold=0.6,  # 提高静音阈值
                        logprob_threshold=-1.0,  # 过滤低置信度结果
                        compression_ratio_threshold=2.4,  # 过滤重复内容
                        condition_on_previous_text=False  # 不依赖前文，减少错误传播
                    )
                else:
                    # 不启用过滤时，使用默认参数
                    result = self.model.transcribe(
                        audio_array,
                        language="zh",
                        initial_prompt=self.initial_prompt
                    )

                text = result["text"].strip()

                # 检测是否为幻觉文本（仅在启用过滤时）
                if text and (not self.enable_hallucination_filter or not self.is_hallucination(text)):
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    output_line = f"[{timestamp}] {text}"
                    print(f"识别结果: {text}")

                    # 更新最近识别的文本列表
                    self.recent_texts.append(text)
                    if len(self.recent_texts) > self.max_recent_texts:
                        self.recent_texts.pop(0)

                    # 保存带时间戳版本
                    with open(self.output_file, 'a', encoding='utf-8') as f:
                        f.write(output_line + "\n")

                    # 保存到干净版本（不换行，连续文本）
                    self.all_texts.append(text)

                    # 加入文本队列（供UI使用）
                    self.text_queue.put(output_line)
                elif text:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 检测到幻觉内容，已过滤: {text[:30]}...")

            except queue.Empty:
                continue
            except Exception as e:
                print(f"识别错误: {e}")

    def stop_recording(self):
        """停止录音"""
        if not self.is_recording:
            return

        print("\n停止录音...")
        self.is_recording = False

        # 等待线程结束
        if hasattr(self, 'record_thread'):
            self.record_thread.join()
        if hasattr(self, 'recognize_thread'):
            self.recognize_thread.join()

        # 保存干净版本的完整文本
        if hasattr(self, 'all_texts') and self.all_texts:
            with open(self.clean_output_file, 'w', encoding='utf-8') as f:
                # 将所有文本连接成一个连续的段落
                full_text = ''.join(self.all_texts)
                f.write(full_text)

        # 关闭音频流
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()

        print(f"\n录音已停止")
        print(f"带时间戳版本: {self.output_file}")
        print(f"干净版本: {self.clean_output_file}")

    def cleanup(self):
        """清理资源"""
        self.stop_recording()
        self.p.terminate()

    def get_latest_text(self):
        """获取最新的识别文本（供UI调用）"""
        texts = []
        while not self.text_queue.empty():
            texts.append(self.text_queue.get())
        return texts


def main():
    """主函数，用于测试"""
    print("=" * 50)
    print("实时音频识别（使用虚拟音频设备）")
    print("=" * 50)
    print("\n支持的虚拟音频设备:")
    print("• Background Music (已检测到会自动使用)")
    print("• BlackHole")
    print("\n如果使用Background Music:")
    print("1. 确保Background Music正在运行")
    print("2. 系统音频会自动被捕获")
    print("-" * 50)

    # 选择模型
    print("\n选择Whisper模型:")
    print("1. tiny (最快，准确度较低)")
    print("2. base (平衡)")
    print("3. small (较慢，准确度较高)")
    print("4. medium (慢，准确度高)")

    model_choice = input("请选择 (1-4，默认2): ").strip() or "2"
    model_map = {"1": "tiny", "2": "base", "3": "small", "4": "medium"}
    model_name = model_map.get(model_choice, "base")

    # 询问关键词提示
    print("\n设置关键词提示（提高识别准确度）:")
    print("示例：")
    print("  - 技术内容: '这是关于编程、软件开发的内容'")
    print("  - 游戏内容: '这是关于游戏、游戏解说的内容'")
    print("  - 教学内容: '这是教学视频，包含专业术语'")
    custom_prompt = input("请输入关键词提示（回车跳过使用默认）: ").strip()

    if custom_prompt:
        # 组合提示词
        full_prompt = f"以下是普通话的内容。{custom_prompt}"
        print(f"使用提示词: {full_prompt}")
    else:
        full_prompt = ""
        print("使用默认设置")

    print(f"\n加载{model_name}模型中...")
    recognizer = RealtimeRecognizer(model_name=model_name, initial_prompt=full_prompt)

    try:
        recognizer.start_recording()

        # 保持运行直到用户中断
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n检测到中断信号...")
    finally:
        recognizer.cleanup()
        print("\n程序结束")


if __name__ == "__main__":
    main()