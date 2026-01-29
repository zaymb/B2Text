#!/usr/bin/env python3
"""
本地文件识别模块 - 支持音频/视频文件的离线转写
支持格式：mp3, wav, m4a, flac, mp4, mkv, avi, mov 等
"""

import os
import whisper
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path


class LocalFileRecognizer:
    def __init__(self, model_name="base", initial_prompt="", progress_callback=None):
        """
        初始化本地文件识别器
        :param model_name: whisper模型名称 (tiny, base, small, medium, large, large-v2, large-v3)
        :param initial_prompt: 初始提示词，用于提高识别准确度
        :param progress_callback: 进度回调函数，用于更新GUI
        """
        self.model_name = model_name
        self.model = None
        self.initial_prompt = initial_prompt or "以下是普通话的句子。"
        self.progress_callback = progress_callback
        self.is_processing = False

        # 支持的文件格式
        self.audio_formats = {'.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.wma', '.opus'}
        self.video_formats = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
        self.supported_formats = self.audio_formats | self.video_formats

    def load_model(self):
        """加载Whisper模型"""
        if self.model is None:
            self._update_progress("正在加载模型...")
            print(f"加载 Whisper {self.model_name} 模型...")
            self.model = whisper.load_model(self.model_name)
            self._update_progress(f"模型 {self.model_name} 加载完成")
            print(f"模型 {self.model_name} 加载完成")
        return self.model

    def is_supported_file(self, file_path):
        """检查文件是否支持"""
        ext = Path(file_path).suffix.lower()
        return ext in self.supported_formats

    def extract_audio_from_video(self, video_path):
        """从视频文件提取音频"""
        self._update_progress("正在从视频提取音频...")

        # 创建临时音频文件
        temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_audio_path = temp_audio.name
        temp_audio.close()

        try:
            # 使用 ffmpeg 提取音频
            cmd = [
                'ffmpeg', '-i', video_path,
                '-ar', '16000',  # 16kHz 采样率
                '-ac', '1',      # 单声道
                '-y',            # 覆盖输出文件
                temp_audio_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                raise Exception(f"音频提取失败: {result.stderr}")

            self._update_progress("音频提取完成")
            return temp_audio_path

        except FileNotFoundError:
            raise Exception("未找到 ffmpeg，请先安装: brew install ffmpeg")

    def process_file(self, file_path, save_to_file=True):
        """
        处理文件并转写
        :param file_path: 文件路径
        :param save_to_file: 是否保存到文件
        :return: 识别的文本
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        if not self.is_supported_file(file_path):
            raise ValueError(f"不支持的文件格式: {Path(file_path).suffix}")

        self.is_processing = True
        temp_audio_path = None

        try:
            # 加载模型
            self.load_model()

            # 获取文件信息
            file_name = Path(file_path).stem
            file_ext = Path(file_path).suffix.lower()

            # 如果是视频文件，先提取音频
            if file_ext in self.video_formats:
                temp_audio_path = self.extract_audio_from_video(file_path)
                audio_path = temp_audio_path
            else:
                audio_path = file_path

            # 开始识别
            self._update_progress("正在识别音频内容...")
            print(f"开始识别: {file_path}")

            # 使用 Whisper 识别
            result = self.model.transcribe(
                audio_path,
                language="zh",
                initial_prompt=self.initial_prompt,
                temperature=0.0,  # 降低随机性
                fp16=False,  # 兼容性更好
                verbose=True  # 显示进度
            )

            # 提取文本
            text = result["text"].strip()

            # 添加时间戳信息（如果有）
            full_text = self._format_result(text, result.get("segments", []))

            # 保存到文件
            if save_to_file:
                output_dir = "outputs"
                os.makedirs(output_dir, exist_ok=True)

                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = f"{output_dir}/local_{file_name}_{timestamp}.txt"

                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"文件: {file_path}\n")
                    f.write(f"模型: {self.model_name}\n")
                    f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    if self.initial_prompt and self.initial_prompt != "以下是普通话的句子。":
                        f.write(f"提示词: {self.initial_prompt}\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(full_text)

                self._update_progress(f"识别完成！结果已保存到: {output_file}")
                print(f"结果保存到: {output_file}")
            else:
                self._update_progress("识别完成！")

            return full_text

        except Exception as e:
            self._update_progress(f"错误: {str(e)}")
            raise e

        finally:
            self.is_processing = False

            # 清理临时文件
            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                except:
                    pass

    def _format_result(self, text, segments):
        """格式化识别结果"""
        if not segments:
            return text

        # 如果有分段信息，添加时间戳
        formatted_lines = []
        formatted_lines.append("【带时间戳版本】\n")

        for segment in segments:
            start_time = self._format_time(segment.get('start', 0))
            end_time = self._format_time(segment.get('end', 0))
            segment_text = segment.get('text', '').strip()

            if segment_text:
                formatted_lines.append(f"[{start_time} -> {end_time}] {segment_text}")

        formatted_lines.append("\n" + "=" * 50 + "\n")
        formatted_lines.append("【纯文本版本】\n")
        formatted_lines.append(text)

        return "\n".join(formatted_lines)

    def _format_time(self, seconds):
        """格式化时间戳"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    def _update_progress(self, message):
        """更新进度"""
        if self.progress_callback:
            self.progress_callback(message)

    def stop_processing(self):
        """停止处理（预留接口）"""
        self.is_processing = False


def main():
    """测试函数"""
    print("本地文件识别测试")
    print("=" * 50)

    # 获取文件路径
    file_path = input("请输入音频/视频文件路径: ").strip()

    if not os.path.exists(file_path):
        print("文件不存在！")
        return

    # 选择模型
    print("\n选择 Whisper 模型:")
    print("1. tiny (最快)")
    print("2. base (平衡)")
    print("3. small (较准)")
    print("4. medium (准确)")
    print("5. large (最准确)")

    choice = input("选择 (1-5, 默认2): ").strip() or "2"
    model_map = {
        "1": "tiny",
        "2": "base",
        "3": "small",
        "4": "medium",
        "5": "large"
    }
    model_name = model_map.get(choice, "base")

    # 关键词提示
    prompt = input("\n输入关键词提示（可选，回车跳过）: ").strip()
    if prompt:
        initial_prompt = f"以下是普通话的句子。这是关于{prompt}的内容。"
    else:
        initial_prompt = ""

    # 创建识别器
    recognizer = LocalFileRecognizer(
        model_name=model_name,
        initial_prompt=initial_prompt,
        progress_callback=lambda msg: print(f"[进度] {msg}")
    )

    try:
        # 处理文件
        result = recognizer.process_file(file_path)
        print("\n" + "=" * 50)
        print("识别结果:")
        print(result[:500] + "..." if len(result) > 500 else result)

    except Exception as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    main()