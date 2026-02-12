#!/usr/bin/env python3
"""
分段录音器 - 避免6分30秒限制
每5分钟自动创建新文件，连续录音
"""

import subprocess
import os
import time
import threading
from datetime import datetime


class ChunkedAudioRecorder:
    def __init__(self, device_name="Background Music", output_dir="recordings", chunk_duration=300,
                 silence_warning_threshold=None, silence_stop_threshold=None,
                 on_silence_warning=None, on_silence_stop=None, on_speech_resumed=None):
        """
        初始化分段录音器
        :param device_name: 音频设备名称
        :param output_dir: 输出目录
        :param chunk_duration: 每段时长（秒），默认5分钟
        :param silence_warning_threshold: 静音警告阈值（秒），None 表示不启用
        :param silence_stop_threshold: 静音自动停止阈值（秒），None 表示不启用
        :param on_silence_warning: 静音警告回调
        :param on_silence_stop: 静音自动停止回调
        :param on_speech_resumed: 声音恢复回调
        """
        self.device_name = device_name
        self.output_dir = output_dir
        self.chunk_duration = chunk_duration  # 每段时长（秒）
        self.recording = False
        self.current_process = None
        self.chunk_thread = None
        self.chunks = []  # 存储所有分段文件路径
        self.start_time = None
        self.duration_callback = None
        self.current_chunk = 0
        self.session_id = None  # 添加session ID用于区分不同录音会话

        # 静音检测配置
        self.silence_warning_threshold = silence_warning_threshold
        self.silence_stop_threshold = silence_stop_threshold
        self.on_silence_warning = on_silence_warning
        self.on_silence_stop = on_silence_stop
        self.on_speech_resumed = on_speech_resumed
        self.silence_monitor = None

        # 创建录音目录
        os.makedirs(output_dir, exist_ok=True)

    def start_recording(self, duration_callback=None):
        """开始分段录音"""
        if self.recording:
            return False

        self.recording = True
        self.start_time = time.time()
        self.duration_callback = duration_callback
        self.chunks = []
        self.current_chunk = 0
        # 生成唯一的session ID
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 启动分段录音线程
        self.chunk_thread = threading.Thread(target=self._record_chunks)
        self.chunk_thread.daemon = True
        self.chunk_thread.start()

        # 启动时长更新线程
        if duration_callback:
            duration_thread = threading.Thread(target=self._update_duration)
            duration_thread.daemon = True
            duration_thread.start()

        # 启动静音监视器（如果配置了阈值）
        if self.silence_warning_threshold and self.silence_stop_threshold:
            try:
                from silence_monitor import SilenceMonitor
                self.silence_monitor = SilenceMonitor(
                    device_name=self.device_name,
                    warning_threshold=self.silence_warning_threshold,
                    stop_threshold=self.silence_stop_threshold,
                    on_warning=self.on_silence_warning,
                    on_stop=self.on_silence_stop,
                    on_speech_resumed=self.on_speech_resumed
                )
                self.silence_monitor.start()
            except Exception as e:
                print(f"静音监视器启动失败（不影响录音）: {e}")
                self.silence_monitor = None

        print("开始分段录音（每5分钟一个文件）...")
        return True

    def _record_chunks(self):
        """录音主循环 - 每5分钟创建新文件"""
        # 使用类成员的session_id，确保整个录音会话使用相同ID
        while self.recording:
            self.current_chunk += 1
            chunk_filename = f"录制_{self.session_id}_part{self.current_chunk:03d}.wav"
            chunk_path = os.path.join(self.output_dir, chunk_filename)
            self.chunks.append(chunk_path)

            # 构建 ffmpeg 命令（限制时长）
            cmd = [
                'ffmpeg', '-y',
                '-f', 'avfoundation',
                '-i', f':{self.device_name}',
                '-t', str(self.chunk_duration),  # 限制每段时长
                '-acodec', 'pcm_s16le',
                '-ar', '44100',
                '-ac', '2',
                chunk_path
            ]

            try:
                print(f"录制第 {self.current_chunk} 段: {chunk_filename}")
                self.current_process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

                # 等待当前段录制完成或被中断
                self.current_process.wait()

                # 检查是否是正常结束（录满5分钟）还是用户停止
                if self.recording and self.current_process.returncode == 0:
                    print(f"第 {self.current_chunk} 段录制完成")
                    continue  # 继续下一段
                else:
                    break  # 用户停止或出错

            except Exception as e:
                print(f"录制出错: {e}")
                break

    def stop_recording(self, merge=False):
        """
        停止录音
        :param merge: 是否合并文件，False则返回分段列表
        :return: 合并后的文件路径或分段文件列表
        """
        if not self.recording:
            return None

        self.recording = False

        # 先停止静音监视器
        if self.silence_monitor:
            try:
                self.silence_monitor.stop()
            except Exception:
                pass
            self.silence_monitor = None

        # 停止当前录制进程
        if self.current_process:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=3)
            except:
                self.current_process.kill()
                self.current_process.wait(timeout=2)

        # 等待线程结束
        if self.chunk_thread:
            self.chunk_thread.join(timeout=5)

        # 如果需要合并
        if merge and len(self.chunks) > 1:
            return self._merge_chunks()

        # 返回文件列表（用于分段识别）
        if self.chunks:
            print(f"录音完成: {len(self.chunks)} 个分段文件")
            return self.chunks

        return None

    def _merge_chunks(self):
        """合并所有分段文件"""
        if not self.chunks:
            return None

        # 生成合并后的文件名
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_path = os.path.join(self.output_dir, f"录制_合并_{timestamp}.wav")

        # 创建文件列表
        list_file = os.path.join(self.output_dir, 'concat_list.txt')
        with open(list_file, 'w') as f:
            for chunk in self.chunks:
                if os.path.exists(chunk):
                    f.write(f"file '{os.path.basename(chunk)}'\n")

        # 使用 ffmpeg 合并文件
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            '-c', 'copy',
            output_path
        ]

        try:
            print(f"合并 {len(self.chunks)} 个文件...")
            subprocess.run(cmd, check=True, cwd=self.output_dir,
                         capture_output=True, text=True)

            # 删除临时文件
            os.remove(list_file)

            # 可选：删除分段文件
            # for chunk in self.chunks:
            #     if os.path.exists(chunk):
            #         os.remove(chunk)

            print(f"合并完成: {output_path}")
            return output_path

        except subprocess.CalledProcessError as e:
            print(f"合并失败: {e}")
            return self.chunks[0] if self.chunks else None

    def _update_duration(self):
        """更新录音时长"""
        while self.recording and self.duration_callback:
            if self.start_time:
                duration = int(time.time() - self.start_time)
                hours = duration // 3600
                minutes = (duration % 3600) // 60
                seconds = duration % 60

                if hours > 0:
                    time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    time_str = f"{minutes:02d}:{seconds:02d}"

                # 添加当前段信息
                time_str += f" (第{self.current_chunk}段)"
                self.duration_callback(time_str)

            time.sleep(1)

    @staticmethod
    def get_audio_devices():
        """获取系统音频设备（复用原方法）"""
        from audio_recorder import AudioRecorder
        return AudioRecorder.get_audio_devices()


# 测试代码
if __name__ == "__main__":
    print("分段录音测试")
    print("=" * 50)

    # 创建分段录音器（每30秒一段，便于测试）
    recorder = ChunkedAudioRecorder(
        device_name="Background Music",
        chunk_duration=30  # 测试用30秒
    )

    def print_duration(duration):
        print(f"\r录音时长: {duration}", end='', flush=True)

    # 开始录音
    if recorder.start_recording(duration_callback=print_duration):
        print("\n录音已开始（每30秒一段）...")
        print("按 Ctrl+C 停止录音")

        try:
            # 录音2分钟测试
            time.sleep(120)
        except KeyboardInterrupt:
            print("\n用户中断")

        # 停止录音
        output_file = recorder.stop_recording()
        if output_file:
            print(f"\n最终文件: {output_file}")
        else:
            print("\n录音失败")