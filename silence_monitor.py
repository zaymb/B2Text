#!/usr/bin/env python3
"""
静音监视器 - 用于 Tab 3 录音时并行检测静音
通过独立的 PyAudio 输入流做 VAD 检测，对录音管线零侵入。
"""

import pyaudio
import numpy as np
import threading
import time


class SilenceMonitor:
    def __init__(self, device_name, warning_threshold=10, stop_threshold=30,
                 energy_threshold=0.0003, on_warning=None, on_stop=None,
                 on_speech_resumed=None, level_callback=None):
        """
        初始化静音监视器
        :param device_name: 音频设备名称
        :param warning_threshold: 静音警告阈值（秒）
        :param stop_threshold: 静音自动停止阈值（秒）
        :param energy_threshold: 音频能量阈值，低于此值视为静音
        :param on_warning: 静音警告回调 fn(duration)
        :param on_stop: 静音停止回调 fn(duration)
        :param on_speech_resumed: 声音恢复回调 fn()
        """
        self.device_name = device_name
        self.warning_threshold = warning_threshold
        self.stop_threshold = stop_threshold
        self.energy_threshold = energy_threshold
        self.on_warning = on_warning
        self.on_stop = on_stop
        self.on_speech_resumed = on_speech_resumed
        self.level_callback = level_callback

        # 音频参数（与 RealtimeRecognizer 一致）
        self.FORMAT = pyaudio.paFloat32
        self.CHANNELS = 2
        self.RATE = 16000
        self.CHUNK = 1024 * 2

        # 内部状态
        self._lock = threading.Lock()
        self._running = False
        self._silence_start_time = None
        self._warning_sent = False
        self._stream = None
        self._pa = None
        self._thread = None

    def start(self):
        """启动静音监听"""
        self._pa = pyaudio.PyAudio()
        device_index = self._find_device_index()

        try:
            self._stream = self._pa.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.CHUNK
            )
        except Exception as e:
            print(f"[SilenceMonitor] 无法打开音频流: {e}")
            if self._pa:
                self._pa.terminate()
                self._pa = None
            raise

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        print("[SilenceMonitor] 静音监听已启动")

    def stop(self):
        """停止静音监听"""
        self._running = False

        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None

        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if self._pa:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None

        print("[SilenceMonitor] 静音监听已停止")

    def _monitor_loop(self):
        """监听主循环：读帧 → 算能量 → 跟踪静音时长 → 触发回调"""
        while self._running:
            try:
                data = self._stream.read(self.CHUNK, exception_on_overflow=False)
                audio_array = np.frombuffer(data, dtype=np.float32)

                # 双声道转单声道
                if self.CHANNELS == 2:
                    audio_array = audio_array.reshape(-1, 2).mean(axis=1)

                # 回调音频波形数据
                if self.level_callback:
                    self.level_callback(audio_array)

                silent = self._is_silence(audio_array)

                with self._lock:
                    if silent:
                        if self._silence_start_time is None:
                            self._silence_start_time = time.time()

                        duration = time.time() - self._silence_start_time

                        # 检查停止阈值
                        if duration >= self.stop_threshold:
                            if self.on_stop:
                                self.on_stop(duration)
                            self._running = False
                            return

                        # 检查警告阈值
                        if duration >= self.warning_threshold and not self._warning_sent:
                            if self.on_warning:
                                self.on_warning(duration)
                            self._warning_sent = True
                    else:
                        # 声音恢复
                        if self._warning_sent and self.on_speech_resumed:
                            self.on_speech_resumed()
                        self._silence_start_time = None
                        self._warning_sent = False

            except Exception as e:
                if self._running:
                    print(f"[SilenceMonitor] 监听错误: {e}")
                break

    def _is_silence(self, audio_array):
        """检测音频是否为静音（与 RealtimeRecognizer.is_silence 相同公式）"""
        energy = np.sum(audio_array ** 2) / len(audio_array)
        return energy < self.energy_threshold

    def _find_device_index(self):
        """查找音频设备索引（复用 realtime_recognition.py 的设备名匹配逻辑）"""
        info = self._pa.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')

        for i in range(num_devices):
            device_info = self._pa.get_device_info_by_host_api_device_index(0, i)
            name = device_info.get('name')
            max_channels = device_info.get('maxInputChannels')

            if max_channels > 0 and self.device_name.lower() in name.lower():
                print(f"[SilenceMonitor] 找到设备: {name} (index={i})")
                return i

        # 未找到指定设备，使用默认输入
        default_index = self._pa.get_default_input_device_info()['index']
        print(f"[SilenceMonitor] 未找到设备 '{self.device_name}'，使用默认设备 (index={default_index})")
        return default_index
