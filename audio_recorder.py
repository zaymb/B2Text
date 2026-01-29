#!/usr/bin/env python3
"""
音频录制模块 - 使用 ffmpeg 录制系统音频
"""

import subprocess
import os
import time
import threading
from datetime import datetime
from pathlib import Path


class AudioRecorder:
    def __init__(self, device_name="BlackHole 2ch", output_dir="recordings"):
        """
        初始化录音器
        :param device_name: 音频设备名称
        :param output_dir: 输出目录
        """
        self.device_name = device_name
        self.output_dir = output_dir
        self.recording = False
        self.process = None
        self.output_path = None
        self.start_time = None
        self.duration_callback = None
        self.duration_thread = None

        # 创建录音目录
        os.makedirs(output_dir, exist_ok=True)

    @staticmethod
    def get_audio_devices():
        """获取系统可用的音频输入设备（macOS）"""
        try:
            # 使用 ffmpeg 列出音频设备
            result = subprocess.run(
                ['ffmpeg', '-f', 'avfoundation', '-list_devices', 'true', '-i', ''],
                capture_output=True,
                text=True
            )

            # ffmpeg 将设备列表输出到 stderr
            output = result.stderr

            devices = []
            audio_section = False

            for line in output.split('\n'):
                if 'audio devices' in line.lower():
                    audio_section = True
                elif 'video devices' in line.lower():
                    audio_section = False
                elif audio_section and '[AVFoundation' in line and '] [' in line:
                    # 提取设备名称
                    # 格式: [AVFoundation indev @ 0x...] [0] BlackHole 2ch
                    # 找到 "] [" 模式，设备名在第二个 ] 后面
                    try:
                        # 找到最后一个 "] " 后的内容
                        idx = line.rfind('] ')
                        if idx != -1:
                            device_name = line[idx+2:].strip()
                            if device_name and device_name != 'none':
                                devices.append(device_name)
                    except:
                        pass

            # 如果没找到设备，添加默认选项
            if not devices:
                devices = ['default']

            # 优先排序虚拟音频设备
            priority_devices = []
            regular_devices = []

            for device in devices:
                if any(keyword in device.lower() for keyword in ['blackhole', 'background music', 'soundflower', 'loopback']):
                    priority_devices.append(device)
                else:
                    regular_devices.append(device)

            return priority_devices + regular_devices

        except FileNotFoundError:
            print("ffmpeg 未安装，无法获取音频设备列表")
            return ['default']
        except Exception as e:
            print(f"获取音频设备失败: {e}")
            return ['default']

    def start_recording(self, duration_callback=None):
        """
        开始录音
        :param duration_callback: 时长回调函数，用于更新UI
        """
        if self.recording:
            print("已经在录音中...")
            return False

        # 生成输出文件名
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.output_path = os.path.join(self.output_dir, f"录制_{timestamp}.wav")

        # 构建 ffmpeg 命令
        # macOS 使用 avfoundation - 注意：avfoundation有约6分30秒的内部限制
        cmd = [
            'ffmpeg', '-y',  # 覆盖已有文件
            '-f', 'avfoundation',  # macOS 音频框架
            '-i', f':{self.device_name}',  # 音频输入设备
            '-acodec', 'pcm_s16le',  # WAV 格式
            '-ar', '44100',  # 采样率
            '-ac', '2',  # 立体声
            self.output_path
        ]

        try:
            # 启动 ffmpeg 进程
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            self.recording = True
            self.start_time = time.time()
            self.duration_callback = duration_callback

            # 启动时长更新线程
            if duration_callback:
                self.duration_thread = threading.Thread(target=self._update_duration)
                self.duration_thread.daemon = True
                self.duration_thread.start()

            print(f"开始录音: {self.output_path}")
            return True

        except Exception as e:
            print(f"启动录音失败: {e}")
            self.recording = False
            return False

    def stop_recording(self):
        """停止录音"""
        if not self.recording or not self.process:
            return None

        try:
            # 发送 'q' 命令优雅退出 ffmpeg
            if self.process.stdin:
                self.process.stdin.write(b'q')
                self.process.stdin.flush()

            # 等待进程结束
            self.process.wait(timeout=3)

        except:
            # 如果优雅退出失败，强制终止
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                self.process.kill()

        self.recording = False
        self.process = None

        # 停止时长更新
        if self.duration_thread:
            self.duration_thread = None

        print(f"录音已保存: {self.output_path}")
        return self.output_path

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

                self.duration_callback(time_str)

            time.sleep(1)

    def get_recording_path(self):
        """获取当前录音文件路径"""
        return self.output_path

    def is_recording(self):
        """检查是否正在录音"""
        return self.recording

    def cleanup(self):
        """清理资源"""
        if self.recording:
            self.stop_recording()


def main():
    """测试函数"""
    print("音频录制测试")
    print("=" * 50)

    # 获取音频设备
    print("\n可用音频设备:")
    devices = AudioRecorder.get_audio_devices()
    for i, device in enumerate(devices):
        print(f"{i+1}. {device}")

    # 选择设备
    choice = input("\n选择音频设备 (默认1): ").strip() or "1"
    try:
        device_idx = int(choice) - 1
        device_name = devices[device_idx]
    except:
        device_name = devices[0]

    print(f"\n使用设备: {device_name}")

    # 创建录音器
    recorder = AudioRecorder(device_name=device_name)

    # 开始录音
    print("\n按 Enter 开始录音...")
    input()

    def print_duration(duration):
        print(f"\r录音时长: {duration}", end='', flush=True)

    recorder.start_recording(duration_callback=print_duration)

    print("\n录音中... 按 Enter 停止")
    input()

    # 停止录音
    output_path = recorder.stop_recording()

    if output_path:
        print(f"\n\n录音文件: {output_path}")
    else:
        print("\n录音失败")


if __name__ == "__main__":
    main()