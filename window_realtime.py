#!/usr/bin/env python3
"""
Bili2text GUI界面 - 支持B站视频识别和实时音频识别
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
from utils import download_bilibili
from exAudio import *
from speech2text import *
from realtime_recognition import RealtimeRecognizer
from local_file_recognition import LocalFileRecognizer
from audio_recorder import AudioRecorder
from audio_recorder_chunked import ChunkedAudioRecorder
from chunked_file_recognition import ChunkedFileRecognizer
import subprocess
import shutil
import time
from datetime import datetime


class Bili2TextGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Bili2text - 视频转文字 & 实时识别工具")
        self.root.geometry("800x750")
        self.root.minsize(800, 750)

        # 实时识别相关
        self.recognizer = None
        self.is_realtime_recording = False
        self.update_thread = None

        # 录音/识别相关
        self.audio_recorder = None
        self.local_recognizer = None
        self.local_result = None
        self.recording_timer_thread = None
        self.chunk_files = None
        self._cleanable_paths = []  # Tab 1 待清理的中间文件路径
        self._rt_cleanable_paths = []  # Tab 2 待清理的输出文件路径
        self._test_monitor = None  # 音频测试用 SilenceMonitor
        self._last_output_path = None  # 最近一次识别的输出文件路径
        self._recognition_running = False  # 识别线程是否在跑
        self._pending_session = None  # 排队等待识别的 chunk_files

        self.setup_ui()

    def setup_ui(self):
        """设置UI界面"""
        # === 全局设置（notebook 上方） ===
        global_frame = ttk.Frame(self.root)
        global_frame.pack(pady=(10, 0), padx=10, fill='x')

        ttk.Label(global_frame, text="Whisper模型:").pack(side='left', padx=(0, 5))
        self.model_var = tk.StringVar(value="medium")
        ttk.Combobox(global_frame, textvariable=self.model_var,
                     values=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
                     state="readonly", width=12).pack(side='left', padx=(0, 15))

        ttk.Label(global_frame, text="关键词提示:").pack(side='left', padx=(0, 5))
        self.keyword_var = tk.StringVar()
        ttk.Entry(global_frame, textvariable=self.keyword_var,
                  width=25).pack(side='left', padx=(0, 5))
        ttk.Label(global_frame, text="(可选)",
                  font=('Arial', 9), foreground='gray').pack(side='left')

        # === 音频波形 ===
        self.waveform_canvas = tk.Canvas(self.root, height=36, highlightthickness=0)
        self.waveform_canvas.pack(fill='x', padx=10, pady=(5, 0))

        self.waveform_bars = 60
        self.waveform_data = [0.0] * self.waveform_bars
        self._waveform_active = False
        self._draw_waveform()

        # === Notebook ===
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=(5, 10))

        # Tab 1: 文件识别（整合 BV + 录音 + 本地文件）
        self.file_tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.file_tab_frame, text='文件识别')
        self.setup_file_tab()

        # Tab 2: 实时音频识别（不动）
        self.realtime_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.realtime_frame, text='实时音频识别')
        self.setup_realtime_tab()

        # Tab 3: 关于（不动）
        self.about_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.about_frame, text='关于')
        self.setup_about_tab()

    def setup_file_tab(self):
        """设置文件识别标签页（整合 BV号下载 + 录音 + 本地文件）"""
        # === 输入源选择 ===
        mode_frame = ttk.LabelFrame(self.file_tab_frame, text="输入源")
        mode_frame.pack(pady=5, padx=20, fill='x')

        self.input_mode_var = tk.StringVar(value="bv")

        radio_frame = ttk.Frame(mode_frame)
        radio_frame.pack(anchor='w', padx=10, pady=5)

        ttk.Radiobutton(radio_frame, text="BV号下载", variable=self.input_mode_var,
                        value="bv", command=self._switch_input_mode).pack(side='left', padx=10)
        ttk.Radiobutton(radio_frame, text="录音", variable=self.input_mode_var,
                        value="record", command=self._switch_input_mode).pack(side='left', padx=10)
        ttk.Radiobutton(radio_frame, text="本地文件", variable=self.input_mode_var,
                        value="file", command=self._switch_input_mode).pack(side='left', padx=10)

        # 托管模式
        self.managed_mode_var = tk.BooleanVar(value=False)
        self.managed_check = ttk.Checkbutton(radio_frame, text="托管模式",
                                             variable=self.managed_mode_var)
        self.managed_check.pack(side='left', padx=(20, 10))

        # === 动态区域容器 ===
        self.dynamic_container = ttk.Frame(self.file_tab_frame)
        self.dynamic_container.pack(pady=5, padx=20, fill='x')

        # --- BV 输入帧 ---
        self.bv_input_frame = ttk.Frame(self.dynamic_container)

        bv_row = ttk.Frame(self.bv_input_frame)
        bv_row.pack(pady=5)
        ttk.Label(bv_row, text="BV号:").pack(side='left', padx=5)
        self.bv_entry = ttk.Entry(bv_row, width=30)
        self.bv_entry.pack(side='left', padx=5)

        # --- 录音输入帧 ---
        self.record_input_frame = ttk.Frame(self.dynamic_container)

        # 录音状态
        self.record_status_label = ttk.Label(self.record_input_frame,
                                             text="录音状态: 未开始",
                                             font=('Arial', 11, 'bold'))
        self.record_status_label.pack(pady=3)

        # 录音控制按钮
        record_control = ttk.Frame(self.record_input_frame)
        record_control.pack(pady=3)

        self.start_record_btn = ttk.Button(record_control, text="开始录制",
                                           command=self.start_recording)
        self.start_record_btn.pack(side='left', padx=5)

        self.stop_record_btn = ttk.Button(record_control, text="停止录制",
                                          command=self.stop_recording,
                                          state='disabled')
        self.stop_record_btn.pack(side='left', padx=5)

        self.test_audio_btn = ttk.Button(record_control, text="测试音频",
                                         command=self._toggle_audio_test)
        self.test_audio_btn.pack(side='left', padx=5)

        # 设备选择
        device_frame = ttk.Frame(self.record_input_frame)
        device_frame.pack(pady=3)

        ttk.Label(device_frame, text="录音设备:").pack(side='left', padx=5)

        self.audio_devices = ChunkedAudioRecorder.get_audio_devices()
        self.record_device_var = tk.StringVar(
            value=self.audio_devices[0] if self.audio_devices else "default")

        self.device_combo = ttk.Combobox(device_frame,
                                         textvariable=self.record_device_var,
                                         values=self.audio_devices,
                                         state="readonly", width=30)
        self.device_combo.pack(side='left', padx=5)

        refresh_btn = ttk.Button(device_frame, text="刷新",
                                 command=self.refresh_audio_devices, width=6)
        refresh_btn.pack(side='left', padx=2)

        # 静音检测
        self.silence_detect_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.record_input_frame,
                        text="启用静音自动检测（10秒警告，30秒自动停止）",
                        variable=self.silence_detect_var).pack(anchor='w', padx=10, pady=3)

        # --- 本地文件输入帧 ---
        self.file_input_frame = ttk.Frame(self.dynamic_container)

        file_row = ttk.Frame(self.file_input_frame)
        file_row.pack(pady=5, fill='x')

        self.browse_btn = ttk.Button(file_row, text="选择文件...",
                                     command=self.browse_file)
        self.browse_btn.pack(side='left', padx=5)

        self.file_path_var = tk.StringVar()
        file_path_label = ttk.Label(file_row, textvariable=self.file_path_var,
                                    font=('Arial', 9), foreground='blue')
        file_path_label.pack(side='left', padx=5)

        # 开始按钮
        btn_frame = ttk.Frame(self.file_tab_frame)
        btn_frame.pack(pady=5)

        self.file_start_btn = ttk.Button(btn_frame, text="开始转换",
                                         command=self._start_file_action)
        self.file_start_btn.pack()

        # 进度条
        self.file_progress = ttk.Progressbar(self.file_tab_frame, mode='indeterminate')
        self.file_progress.pack(pady=5, padx=20, fill='x')

        # 状态标签
        self.file_status_label = ttk.Label(self.file_tab_frame,
                                           text="状态: 就绪",
                                           font=('Arial', 10),
                                           foreground='blue')
        self.file_status_label.pack(pady=2)

        # 识别结果
        result_frame = ttk.Frame(self.file_tab_frame)
        result_frame.pack(fill='both', expand=True, padx=20, pady=5)

        ttk.Label(result_frame, text="识别结果:").pack(anchor='w')

        self.file_result_text = scrolledtext.ScrolledText(result_frame, height=10, width=70)
        self.file_result_text.pack(fill='both', expand=True, pady=5)

        # 保存 + 清理按钮
        save_frame = ttk.Frame(self.file_tab_frame)
        save_frame.pack(pady=5)

        self.file_save_btn = ttk.Button(save_frame, text="查看结果",
                                        command=self._open_result_file,
                                        state='disabled')
        self.file_save_btn.pack(side='left', padx=5)

        self.file_clean_btn = ttk.Button(save_frame, text="清理文件",
                                         command=self._clean_source_files,
                                         state='disabled')
        self.file_clean_btn.pack(side='left', padx=5)

        # 默认显示 BV 输入帧
        self._switch_input_mode()

    def _switch_input_mode(self):
        """切换输入源，显示/隐藏对应的动态帧"""
        mode = self.input_mode_var.get()

        # 切换模式时停止音频测试
        if self._test_monitor is not None:
            self._test_monitor.stop()
            self._test_monitor = None
            self._stop_waveform()
            self.test_audio_btn.config(text="测试音频")
            self._update_record_btn_state()
            self.device_combo.config(state='readonly')

        # 隐藏所有动态帧
        for frame in (self.bv_input_frame, self.record_input_frame, self.file_input_frame):
            frame.pack_forget()

        # 显示选中的帧 + 托管模式状态
        if mode == "bv":
            self.bv_input_frame.pack(fill='x', padx=5, pady=5)
            self.file_start_btn.config(text="开始转换", state='normal')
            self.managed_check.config(state='normal')
        elif mode == "record":
            self.record_input_frame.pack(fill='x', padx=5, pady=5)
            has_chunks = hasattr(self, 'chunk_files') and self.chunk_files
            self.file_start_btn.config(text="开始识别",
                                       state='normal' if has_chunks else 'disabled')
            self.managed_check.config(state='normal')
        elif mode == "file":
            self.file_input_frame.pack(fill='x', padx=5, pady=5)
            has_file = self.file_path_var.get().strip() != ""
            self.file_start_btn.config(text="开始识别",
                                       state='normal' if has_file else 'disabled')
            self.managed_mode_var.set(False)
            self.managed_check.config(state='disabled')

    def _start_file_action(self):
        """统一开始按钮：根据输入模式分发"""
        if self._recognition_running:
            messagebox.showinfo("提示", "上一轮识别还在跑，请稍候")
            return

        mode = self.input_mode_var.get()

        if mode == "bv":
            bv = self.bv_entry.get().strip()
            if not bv:
                messagebox.showerror("错误", "请输入BV号")
                return
            thread = threading.Thread(target=self._bv_conversion_thread, args=(bv,))
            thread.daemon = True
            thread.start()

        elif mode == "record":
            if not (hasattr(self, 'chunk_files') and self.chunk_files):
                messagebox.showerror("错误", "请先录制音频")
                return
            thread = threading.Thread(target=self._local_recognition_thread)
            thread.daemon = True
            thread.start()

        elif mode == "file":
            file_path = self.file_path_var.get().strip()
            if not file_path:
                messagebox.showerror("错误", "请先选择文件")
                return
            if not os.path.exists(file_path):
                messagebox.showerror("错误", "文件不存在")
                return
            thread = threading.Thread(target=self._local_recognition_thread)
            thread.daemon = True
            thread.start()

    # ---- BV 转换 ----

    def _bv_conversion_thread(self, bv):
        """BV号下载+识别线程"""
        try:
            self.file_start_btn.config(state='disabled')
            self.file_progress.start()
            self.file_result_text.delete(1.0, tk.END)
            self.file_save_btn.config(state='disabled')

            self._log_result("开始下载视频...")
            folder = download_bilibili(bv)

            bv = bv if bv.startswith('BV') else f"BV{bv}"
            bv = bv.split('/')[-1]

            self._log_result("提取和分割音频...")
            foldername = process_audio_split(bv)

            model = self.model_var.get()
            self._log_result(f"加载{model}模型...")
            load_whisper(model)

            self._log_result("开始语音识别...")
            keyword = self.keyword_var.get().strip()
            if keyword:
                run_analysis(foldername, prompt=keyword)
            else:
                run_analysis(foldername)

            output_path = f"outputs/{foldername}.txt"
            self._last_output_path = output_path
            self._log_result(f"转换完成！文件保存在: {output_path}")

            # 读取结果到文本框
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                    result_content = f.read()
                self.file_result_text.delete(1.0, tk.END)
                self.file_result_text.insert(tk.END, result_content)
                self.file_result_text.see(1.0)
                self.local_result = result_content
                self.file_save_btn.config(state='normal')
            except Exception:
                pass

            # 记录可清理的中间文件
            self._cleanable_paths = [
                f"bilibili_video/{bv}",
                f"audio/conv/{foldername}.mp3",
                f"audio/slice/{foldername}"
            ]

            if self.managed_mode_var.get():
                self._log_result("托管模式：自动清理中间文件...")
                self._do_clean_files()
                self._send_notification("BV转换完成", f"结果已保存到 {output_path}")
            else:
                self.file_clean_btn.config(state='normal')

            self._update_file_status("转换完成")
            messagebox.showinfo("完成", f"转换完成！\n文件保存在: {output_path}")

        except Exception as e:
            self._log_result(f"错误: {str(e)}")
            self._update_file_status("错误")
            messagebox.showerror("错误", str(e))

        finally:
            self.file_progress.stop()
            self.file_start_btn.config(state='normal')

    # ---- 本地/录音识别 ----

    def _local_recognition_thread(self):
        """本地文件/录音识别线程"""
        self._recognition_running = True
        # snapshot chunk_files 到局部变量，不依赖 self.chunk_files（可能被新录音覆盖）
        snapshot_chunks = list(self.chunk_files) if self.chunk_files else None

        try:
            self.file_start_btn.config(state='disabled')
            self.browse_btn.config(state='disabled')
            self.file_progress.start()

            model = self.model_var.get()
            keyword = self.keyword_var.get().strip()
            initial_prompt = f"以下是普通话的句子。这是关于{keyword}的内容。" if keyword else ""

            self.file_result_text.delete(1.0, tk.END)

            if snapshot_chunks and len(snapshot_chunks) > 1:
                # 分段识别
                num_chunks = len(snapshot_chunks)
                self.record_status_label.config(
                    text=f"识别状态: 准备识别{num_chunks}个分段...")
                self._update_file_status("正在进行分段识别...")

                # 切换为确定进度条（精度 1000，帧级更新）
                self.file_progress.stop()
                self.file_progress.config(mode='determinate', maximum=1000, value=0)

                managed = self.managed_mode_var.get()
                self._cleanable_paths = list(snapshot_chunks)

                # 帧级进度回调
                def on_frame_progress(chunk_idx, total_chunks, current_frames, total_frames):
                    chunk_share = 1000 / total_chunks
                    base = (chunk_idx - 1) * chunk_share
                    within = (current_frames / total_frames * chunk_share) if total_frames > 0 else 0
                    self.file_progress.config(value=int(base + within))

                # 重复检测 + 段完成回调
                self._repetitive_streak = 0

                def on_chunk_done(idx, total, text):
                    self.file_progress.config(value=int(idx / total * 1000))
                    if self._is_repetitive(text):
                        self._repetitive_streak += 1
                        if self._repetitive_streak >= 2:
                            self._update_file_status("检测到连续重复，已中止识别")
                            self.root.after(0, lambda: messagebox.showwarning(
                                "识别异常",
                                "连续多段识别结果出现大量重复词句，\n"
                                "可能是录音出了问题，已自动中止。\n"
                                "建议重新录制。"))
                            return False
                        self._update_file_status(f"第{idx}段可能存在重复，继续检查下一段...")
                    else:
                        self._repetitive_streak = 0
                    return True

                chunked_recognizer = ChunkedFileRecognizer(
                    model_name=model,
                    initial_prompt=initial_prompt,
                    progress_callback=self._update_file_status
                )

                self.local_result = chunked_recognizer.process_chunks(
                    snapshot_chunks,
                    save_to_file=True,
                    delete_after=managed,
                    chunk_callback=on_chunk_done,
                    frame_callback=on_frame_progress
                )

                self._last_output_path = chunked_recognizer.last_output_file

                if managed:
                    if self.local_result and self.local_result.strip():
                        self.record_status_label.config(
                            text=f"识别状态: 完成（已识别{num_chunks}段，文件已清理）")
                        self._cleanable_paths = []
                    else:
                        # 识别失败，文件未删除
                        self.record_status_label.config(
                            text=f"识别状态: 失败（文件已保留，可手动清理）")
                        self.file_clean_btn.config(state='normal')
                else:
                    self.record_status_label.config(
                        text=f"识别状态: 完成（已识别{num_chunks}段）")
                    self.file_clean_btn.config(state='normal')

            elif snapshot_chunks and len(snapshot_chunks) == 1:
                # 单个录音分段
                self.record_status_label.config(text="识别状态: 正在识别...")
                self._update_file_status("正在识别...")
                self._cleanable_paths = list(snapshot_chunks)

                # 确定进度条
                self.file_progress.stop()
                self.file_progress.config(mode='determinate', maximum=1000, value=0)

                self.local_recognizer = LocalFileRecognizer(
                    model_name=model,
                    initial_prompt=initial_prompt,
                    progress_callback=self._update_file_status
                )

                self.local_result = self._transcribe_with_progress(
                    lambda: self.local_recognizer.process_file(
                        snapshot_chunks[0], save_to_file=True))

                self._last_output_path = self.local_recognizer.last_output_file

                # 重复检测
                if self.local_result and self._is_repetitive(self.local_result):
                    self.root.after(0, lambda: messagebox.showwarning(
                        "识别异常",
                        "识别结果出现大量重复词句，\n"
                        "可能是录音出了问题。建议重新录制。"))

                if self.managed_mode_var.get():
                    if self.local_result and self.local_result.strip():
                        self._do_clean_files()
                    else:
                        self.file_clean_btn.config(state='normal')
                else:
                    self.file_clean_btn.config(state='normal')

            else:
                # 本地文件模式
                file_path = self.file_path_var.get().strip()
                self._update_file_status("正在识别...")

                # 确定进度条
                self.file_progress.stop()
                self.file_progress.config(mode='determinate', maximum=1000, value=0)

                self.local_recognizer = LocalFileRecognizer(
                    model_name=model,
                    initial_prompt=initial_prompt,
                    progress_callback=self._update_file_status
                )

                self.local_result = self._transcribe_with_progress(
                    lambda: self.local_recognizer.process_file(
                        file_path, save_to_file=True))

                self._last_output_path = self.local_recognizer.last_output_file

            # 显示结果
            self.file_result_text.insert(tk.END, self.local_result)
            self.file_result_text.see(1.0)
            self.file_save_btn.config(state='normal')

            self._update_file_status("识别完成")
            if self.input_mode_var.get() == "record":
                self.record_status_label.config(text="录音状态: 识别完成")

            if self.managed_mode_var.get():
                self._send_notification("识别完成", "录音已自动识别，结果已保存到 outputs 目录")

            messagebox.showinfo("完成", "文件识别完成！\n结果已自动保存到 outputs 目录")

        except Exception as e:
            self._update_file_status("错误")
            if self.input_mode_var.get() == "record":
                self.record_status_label.config(text="录音状态: 错误")
            messagebox.showerror("错误", str(e))

        finally:
            self._recognition_running = False
            self.file_start_btn.config(state='normal')
            self.browse_btn.config(state='normal')
            self.file_progress.stop()
            self.file_progress.config(mode='indeterminate', value=0)

            # 检查排队的 session
            if self._pending_session:
                self.chunk_files = self._pending_session
                self._pending_session = None
                self.root.after(0, self._start_file_action)

            # 刷新录制按钮状态
            self.root.after(0, self._update_record_btn_state)

    # ---- 录音相关 ----

    def start_recording(self):
        """开始录音"""
        try:
            device = self.record_device_var.get()

            silence_kwargs = {}
            if self.silence_detect_var.get():
                silence_kwargs = dict(
                    silence_warning_threshold=10,
                    silence_stop_threshold=30,
                    on_silence_warning=self._on_silence_warning,
                    on_silence_stop=self._on_silence_stop,
                    on_speech_resumed=self._on_speech_resumed,
                )

            self.audio_recorder = ChunkedAudioRecorder(
                device_name=device,
                chunk_duration=300,
                level_callback=self._on_audio_level,
                **silence_kwargs
            )

            if self.audio_recorder.start_recording(duration_callback=self._update_record_duration):
                self._start_waveform()
                self.record_status_label.config(text="录音状态: 录制中 00:00 (第1段)",
                                                foreground='black')
                self.start_record_btn.config(text="开始录制")
                self._update_record_btn_state()
                self.stop_record_btn.config(state='normal')
                self.file_start_btn.config(state='disabled')
            else:
                messagebox.showerror("错误", "无法启动录音，请检查音频设备")

        except Exception as e:
            messagebox.showerror("错误", f"录音失败: {str(e)}")

    def stop_recording(self):
        """停止录音"""
        if not self.audio_recorder:
            return

        self._stop_waveform()
        self.record_status_label.config(text="录音状态: 正在保存...")
        self.root.update()

        chunk_files = self.audio_recorder.stop_recording(merge=False)
        self.audio_recorder = None
        self.stop_record_btn.config(state='disabled')

        if chunk_files:
            new_chunks = chunk_files if isinstance(chunk_files, list) else [chunk_files]

            # 托管模式：识别正在跑 → 排队
            if self.managed_mode_var.get() and self._recognition_running:
                self._pending_session = new_chunks
                self.record_status_label.config(
                    text="托管模式：上一轮识别中，新录音已排队")
                # 给下一轮录音腾位置（chunk_files 已被 snapshot）
                self.chunk_files = None
            elif self.managed_mode_var.get():
                # 托管模式：直接开始识别
                self.chunk_files = new_chunks
                self._cleanable_paths = list(new_chunks)
                self.file_clean_btn.config(state='normal')
                self.record_status_label.config(text="托管模式：自动开始识别...")
                self._start_file_action()
            else:
                # 非托管模式
                if self.chunk_files is None:
                    self.chunk_files = []
                self.chunk_files.extend(new_chunks)

                total = len(self.chunk_files)
                self.record_status_label.config(
                    text=f"录音状态: 已完成（{total}段，待识别）")
                self.file_start_btn.config(state='normal')

                # 启用清理按钮（允许用户丢弃本次录音）
                self._cleanable_paths = list(self.chunk_files)
                self.file_clean_btn.config(state='normal')
        else:
            if not self.chunk_files:
                self.record_status_label.config(text="录音状态: 未开始")

        self.start_record_btn.config(text="开始录制")
        self._update_record_btn_state()

    def _update_record_duration(self, duration):
        """更新录音时长显示"""
        self.record_status_label.config(text=f"录音状态: 录制中 {duration}")
        self.root.update()

    def refresh_audio_devices(self):
        """刷新音频设备列表"""
        self.audio_devices = ChunkedAudioRecorder.get_audio_devices()
        self.device_combo['values'] = self.audio_devices
        if self.audio_devices:
            self.record_device_var.set(self.audio_devices[0])
        messagebox.showinfo("刷新完成", f"找到 {len(self.audio_devices)} 个音频设备")

    def browse_file(self):
        """浏览选择文件"""
        file_path = filedialog.askopenfilename(
            title="选择音频/视频文件",
            filetypes=[
                ("音频文件", "*.mp3 *.wav *.m4a *.flac *.aac *.ogg"),
                ("视频文件", "*.mp4 *.mkv *.avi *.mov *.wmv *.flv"),
                ("所有文件", "*.*")
            ]
        )
        if file_path:
            self.file_path_var.set(file_path)
            self.file_start_btn.config(state='normal')
            self.chunk_files = None

    # ---- 波形相关 ----

    def _on_audio_level(self, audio_array):
        """音频波形回调（从后端线程调用），接收单声道 numpy 数组"""
        if not self._waveform_active:
            return
        import numpy as np
        n = self.waveform_bars
        # 均匀抽样，取绝对值作为柱高
        indices = np.linspace(0, len(audio_array) - 1, n, dtype=int)
        self.waveform_data = [abs(float(audio_array[i])) for i in indices]

    def _draw_waveform(self):
        """定时重绘波形 Canvas — 中轴对称，实时反映当前音频"""
        canvas = self.waveform_canvas
        canvas.delete('all')

        w = canvas.winfo_width() or 760
        h = canvas.winfo_height() or 36
        mid_y = h / 2

        bar_w = 3
        total_w = self.waveform_bars * bar_w + (self.waveform_bars - 1) * 2
        x_offset = (w - total_w) / 2  # 居中

        for i, level in enumerate(self.waveform_data):
            # 归一化：乘以放大系数，限幅到 mid_y
            bar_h = min(level * 300, mid_y - 1)
            bar_h = max(bar_h, 1)

            x = x_offset + i * (bar_w + 2)

            if self._waveform_active and level > 0.005:
                color = '#4a9eff'
            else:
                color = '#d0d0d0'

            canvas.create_rectangle(x, mid_y - bar_h, x + bar_w, mid_y + bar_h,
                                    fill=color, outline='')

        self.root.after(66, self._draw_waveform)

    def _start_waveform(self):
        """开始波形显示"""
        self._waveform_active = True
        self.waveform_data = [0.0] * self.waveform_bars

    def _stop_waveform(self):
        """停止波形显示"""
        self._waveform_active = False
        self.waveform_data = [0.0] * self.waveform_bars

    def _toggle_audio_test(self):
        """切换音频测试：开始/停止麦克风音量检测"""
        if self._test_monitor is not None:
            # 停止测试
            self._test_monitor.stop()
            self._test_monitor = None
            self._stop_waveform()
            self.test_audio_btn.config(text="测试音频")
            self._update_record_btn_state()
            self.device_combo.config(state='readonly')
        else:
            # 开始测试
            device = self.record_device_var.get()
            try:
                from silence_monitor import SilenceMonitor
                self._test_monitor = SilenceMonitor(
                    device_name=device,
                    level_callback=self._on_audio_level
                )
                self._test_monitor.start()
                self._start_waveform()
                self.test_audio_btn.config(text="停止测试")
                self.start_record_btn.config(state='disabled')
                self.device_combo.config(state='disabled')
            except Exception as e:
                self._test_monitor = None
                messagebox.showerror("错误", f"音频测试启动失败: {str(e)}")

    # ---- 录制状态辅助 ----

    def _can_record(self):
        """判断当前是否可以开始录制（硬件未被占用）"""
        return self.audio_recorder is None and self._test_monitor is None

    def _update_record_btn_state(self):
        """根据当前状态刷新 '开始录制' 按钮"""
        state = 'normal' if self._can_record() else 'disabled'
        self.start_record_btn.config(state=state)

    # ---- 辅助方法 ----

    def _update_file_status(self, message):
        """更新文件识别状态"""
        self.file_status_label.config(text=f"状态: {message}")
        self.root.update()

    def _log_result(self, message):
        """带时间戳写入结果文本框"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.file_result_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.file_result_text.see(tk.END)
        self.root.update()

    def _clean_source_files(self):
        """清理文件按钮回调（Tab 1）"""
        if not self._cleanable_paths:
            messagebox.showinfo("提示", "没有需要清理的文件")
            return

        existing = [p for p in self._cleanable_paths if os.path.exists(p)]
        if not existing:
            messagebox.showinfo("提示", "文件已被清理")
            self._cleanable_paths = []
            self.file_clean_btn.config(state='disabled')
            return

        names = "\n".join([os.path.basename(p) for p in existing[:5]])
        if len(existing) > 5:
            names += f"\n... 等{len(existing)}个文件/目录"

        if messagebox.askyesno("确认清理", f"将删除以下文件:\n{names}\n\n确定要清理吗？"):
            self._do_clean_files()
            self._pending_session = None  # 避免已删文件还排着队
            self.file_clean_btn.config(state='disabled')

            # 如果在录音模式下，重置录音会话状态
            if self.input_mode_var.get() == "record":
                self.chunk_files = None
                self.record_status_label.config(text="录音状态: 未开始",
                                                foreground='black')
                self.file_start_btn.config(state='disabled')
                self.file_result_text.delete(1.0, tk.END)

            messagebox.showinfo("清理完成", "中间文件已清理")

    def _do_clean_files(self):
        """执行文件清理（通用）"""
        for path in self._cleanable_paths:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                elif os.path.isfile(path):
                    os.remove(path)
            except Exception as e:
                print(f"[清理] 删除失败 {path}: {e}")
        self._cleanable_paths = []

    def _clean_rt_files(self):
        """清理实时识别输出文件（Tab 2）"""
        if not self._rt_cleanable_paths:
            messagebox.showinfo("提示", "没有需要清理的文件")
            return

        existing = [p for p in self._rt_cleanable_paths if os.path.exists(p)]
        if not existing:
            messagebox.showinfo("提示", "文件已被清理")
            self._rt_cleanable_paths = []
            self.rt_clean_btn.config(state='disabled')
            return

        names = "\n".join([os.path.basename(p) for p in existing])
        if messagebox.askyesno("确认清理", f"将删除以下文件:\n{names}\n\n确定要清理吗？"):
            for path in existing:
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"[清理] 删除失败 {path}: {e}")
            self._rt_cleanable_paths = []
            self.rt_clean_btn.config(state='disabled')
            messagebox.showinfo("清理完成", "输出文件已清理")

    def _transcribe_with_progress(self, transcribe_fn):
        """包装识别调用，捕获 whisper 内部 tqdm 进度到 GUI 进度条"""
        import tqdm as _tqdm_mod
        from tqdm import tqdm as _orig_tqdm
        progress_bar = self.file_progress

        class _ProgressTqdm(_orig_tqdm):
            def update(self, n=1):
                super().update(n)
                if self.total and self.total > 0:
                    progress_bar.config(value=int(self.n / self.total * 1000))

        _saved_cls = _tqdm_mod.tqdm
        _tqdm_mod.tqdm = _ProgressTqdm
        try:
            return transcribe_fn()
        finally:
            _tqdm_mod.tqdm = _saved_cls

    def _is_repetitive(self, text):
        """检测文本是否存在大量重复（Whisper 幻觉特征）"""
        if len(text) < 20:
            return False

        import re
        from collections import Counter

        parts = re.split(r'[。，！？、；：,.!?\n]+', text)
        parts = [p.strip() for p in parts if len(p.strip()) >= 2]

        if len(parts) < 4:
            return False

        counter = Counter(parts)
        most_common_count = counter.most_common(1)[0][1]

        # 任一短语出现超过 50% 或超过 5 次
        if most_common_count > max(3, len(parts) * 0.5):
            return True

        return False

    def _open_result_file(self):
        """查看结果：用系统默认应用打开已保存的结果文件，若无则 fallback 到另存为"""
        if self._last_output_path and os.path.exists(self._last_output_path):
            subprocess.Popen(['open', self._last_output_path])
        elif self.local_result:
            # fallback：另存为
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
            )
            if file_path:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(self.local_result)
                    messagebox.showinfo("成功", f"结果已保存到:\n{file_path}")
                except Exception as e:
                    messagebox.showerror("错误", f"保存失败: {str(e)}")
        else:
            messagebox.showinfo("提示", "没有可查看的结果文件")

    # ---- Tab 2: 实时音频识别（不动） ----

    def setup_realtime_tab(self):
        """设置实时音频识别标签页"""
        info_text = """使用说明:
1. 支持 Background Music 或 BlackHole
2. 如果已安装Background Music，会自动使用
3. 确保虚拟音频设备正在运行
4. 点击'开始识别'即可实时转文字"""

        info_label = ttk.Label(self.realtime_frame, text=info_text, justify='left')
        info_label.pack(pady=10)

        settings_frame = ttk.Frame(self.realtime_frame)
        settings_frame.pack(pady=10)

        ttk.Label(settings_frame, text="音频设备:").grid(row=0, column=0, padx=5, pady=5)
        self.device_var = tk.StringVar(value="自动检测")
        self.device_entry = ttk.Entry(settings_frame, textvariable=self.device_var, width=22)
        self.device_entry.grid(row=0, column=1, padx=5, pady=5)

        self.enable_filter_var = tk.BooleanVar(value=True)
        filter_check = ttk.Checkbutton(settings_frame, text="启用幻觉过滤（防止重复和错误内容）",
                                       variable=self.enable_filter_var)
        filter_check.grid(row=1, column=0, columnspan=2, pady=5)

        self.rt_silence_detect_var = tk.BooleanVar(value=True)
        rt_silence_check = ttk.Checkbutton(settings_frame,
                                           text="启用静音超时检测（30秒无声自动停止）",
                                           variable=self.rt_silence_detect_var)
        rt_silence_check.grid(row=2, column=0, columnspan=2, pady=5)

        control_frame = ttk.Frame(self.realtime_frame)
        control_frame.pack(pady=10)

        self.realtime_start_btn = ttk.Button(control_frame, text="开始识别",
                                              command=self.start_realtime_recognition)
        self.realtime_start_btn.pack(side='left', padx=5)

        self.realtime_stop_btn = ttk.Button(control_frame, text="停止识别",
                                             command=self.stop_realtime_recognition,
                                             state='disabled')
        self.realtime_stop_btn.pack(side='left', padx=5)

        self.realtime_clear_btn = ttk.Button(control_frame, text="清空文本",
                                              command=self.clear_realtime_text)
        self.realtime_clear_btn.pack(side='left', padx=5)

        self.rt_clean_btn = ttk.Button(control_frame, text="清理文件",
                                       command=self._clean_rt_files,
                                       state='disabled')
        self.rt_clean_btn.pack(side='left', padx=5)

        self.status_label = ttk.Label(self.realtime_frame, text="状态: 未开始",
                                       font=('Arial', 10))
        self.status_label.pack(pady=5)

        text_label = ttk.Label(self.realtime_frame, text="识别结果:")
        text_label.pack(pady=5)

        self.realtime_text = scrolledtext.ScrolledText(self.realtime_frame, height=15, width=70)
        self.realtime_text.pack(pady=5, padx=20, fill='both', expand=True)

    def setup_about_tab(self):
        """设置关于标签页"""
        about_text = """
Bili2text - 视频转文字工具

版本: 2.0
作者: lanbinleo

功能特性:
• B站视频下载并转文字
• 实时音频识别（使用BlackHole）
• 本地音频/视频文件识别
• 支持多种Whisper模型
• 自动音频分割处理

技术栈:
• Python + Tkinter
• OpenAI Whisper
• PyAudio
• BlackHole (macOS音频路由)

GitHub: https://github.com/lanbinleo/bili2text
        """

        about_label = ttk.Label(self.about_frame, text=about_text, justify='left',
                                font=('Arial', 11))
        about_label.pack(pady=20, padx=20)

    # ---- Tab 2: 实时识别方法（不动） ----

    def start_realtime_recognition(self):
        """开始实时识别"""
        try:
            model = self.model_var.get()
            device = self.device_var.get()
            if device == "自动检测" or device == "自动检测BlackHole":
                device = None

            keyword = self.keyword_var.get().strip()
            if keyword:
                prompt = f"以下是普通话的内容。这是关于{keyword}的内容。"
            else:
                prompt = ""

            enable_filter = self.enable_filter_var.get()

            self.status_label.config(text="状态: 正在加载模型...")
            self.root.update()

            silence_kwargs = {}
            if self.rt_silence_detect_var.get():
                silence_kwargs = dict(
                    silence_warning_threshold=10,
                    silence_stop_threshold=30,
                    on_silence_warning=self._on_rt_silence_warning,
                    on_silence_stop=self._on_rt_silence_stop,
                    on_speech_resumed=self._on_rt_speech_resumed,
                )

            self.recognizer = RealtimeRecognizer(
                model_name=model,
                device_name=device,
                initial_prompt=prompt,
                enable_hallucination_filter=enable_filter,
                level_callback=self._on_audio_level,
                **silence_kwargs
            )

            self.recognizer.start_recording()
            self.is_realtime_recording = True
            self._start_waveform()

            self.realtime_start_btn.config(state='disabled')
            self.realtime_stop_btn.config(state='normal')
            self.status_label.config(text="状态: 正在识别...")

            self.update_thread = threading.Thread(target=self._update_realtime_text)
            self.update_thread.daemon = True
            self.update_thread.start()

        except Exception as e:
            messagebox.showerror("错误", f"启动识别失败: {str(e)}")
            self.status_label.config(text="状态: 错误")

    def stop_realtime_recognition(self):
        """停止实时识别"""
        output_file = None
        clean_output_file = None

        if self.recognizer:
            if hasattr(self.recognizer, 'output_file'):
                output_file = self.recognizer.output_file
            if hasattr(self.recognizer, 'clean_output_file'):
                clean_output_file = self.recognizer.clean_output_file

            self.recognizer.stop_recording()
            self.is_realtime_recording = False

            if self.update_thread:
                self.update_thread.join(timeout=2)

            self.recognizer.cleanup()
            self.recognizer = None

        self._stop_waveform()
        self.realtime_start_btn.config(state='normal')
        self.realtime_stop_btn.config(state='disabled')
        self.status_label.config(text="状态: 已停止")

        # 记录可清理的输出文件
        rt_files = [f for f in [output_file, clean_output_file] if f]
        if rt_files:
            self._rt_cleanable_paths = rt_files
            self.rt_clean_btn.config(state='normal')

        if output_file and clean_output_file:
            messagebox.showinfo("完成",
                f"识别结果已保存:\n\n"
                f"📝 带时间戳版本:\n{output_file}\n\n"
                f"📄 干净版本(无时间戳):\n{clean_output_file}")

    def _update_realtime_text(self):
        """更新实时识别文本"""
        while self.is_realtime_recording:
            if self.recognizer:
                new_texts = self.recognizer.get_latest_text()
                for text in new_texts:
                    self.realtime_text.insert(tk.END, text + "\n")
                    self.realtime_text.see(tk.END)
            time.sleep(0.5)

    def clear_realtime_text(self):
        """清空实时识别文本"""
        self.realtime_text.delete(1.0, tk.END)

    # ---- 系统通知 ----
    def _send_notification(self, title, message):
        """发送 macOS 系统通知"""
        try:
            subprocess.Popen([
                'osascript', '-e',
                f'display notification "{message}" with title "{title}"'
            ])
        except Exception:
            pass

    # ---- 录音静音检测回调 ----
    def _on_silence_warning(self, duration):
        """录音: 静音警告"""
        self.root.after(0, lambda: self.record_status_label.config(
            text=f"录音状态: 静音警告! 已静音 {int(duration)} 秒",
            foreground='orange'))
        self._send_notification("录音静音警告",
                                f"已静音 {int(duration)} 秒，30 秒后将自动停止")

    def _on_silence_stop(self, duration):
        """录音: 静音自动停止"""
        self.root.after(0, lambda: self._do_silence_stop_recording(duration))
        self._send_notification("录音已自动停止",
                                f"持续静音 {int(duration)} 秒，录音已自动停止")

    def _do_silence_stop_recording(self, duration):
        """静音自动暂停"""
        # 停止当前录制，获取已录分段
        self._stop_waveform()
        chunk_files = self.audio_recorder.stop_recording(merge=False)
        self.audio_recorder = None

        new_chunks = None
        if chunk_files:
            new_chunks = chunk_files if isinstance(chunk_files, list) else [chunk_files]

        if self.managed_mode_var.get() and new_chunks:
            if self._recognition_running:
                # 上一轮还在跑 → 排队
                self._pending_session = new_chunks
                self.chunk_files = None
                self.record_status_label.config(
                    text="托管模式：静音停止，新录音已排队等待识别",
                    foreground='black')
            else:
                # 直接进入识别流程
                self.chunk_files = new_chunks
                self._cleanable_paths = list(new_chunks)
                self.record_status_label.config(
                    text="托管模式：静音自动停止，开始识别...",
                    foreground='black')
                self.stop_record_btn.config(state='disabled')
                self.file_start_btn.config(state='normal')
                self._start_file_action()
        else:
            # 非托管（或无有效录音）
            if new_chunks:
                if self.chunk_files is None:
                    self.chunk_files = []
                self.chunk_files.extend(new_chunks)

            total = len(self.chunk_files) if self.chunk_files else 0
            self.record_status_label.config(
                text=f"录音状态: 静音暂停（已录{total}段）— 可继续录制或开始识别",
                foreground='red')
            self.stop_record_btn.config(state='disabled')
            if total > 0:
                self.file_start_btn.config(state='normal')
                self._cleanable_paths = list(self.chunk_files)
                self.file_clean_btn.config(state='normal')
            self._send_notification("录音静音暂停",
                f"已静音 {int(duration)} 秒，录音已暂停（已录{total}段）")

        self.start_record_btn.config(text="继续录制")
        self._update_record_btn_state()

    def _on_speech_resumed(self):
        """录音: 声音恢复"""
        self.root.after(0, lambda: self.record_status_label.config(
            text="录音状态: 录制中（声音已恢复）",
            foreground='green'))

    # ---- Tab 2 静音检测回调 ----
    def _on_rt_silence_warning(self, duration):
        """Tab 2: 静音警告"""
        self.root.after(0, lambda: self.status_label.config(
            text=f"状态: 静音警告! 已静音 {int(duration)} 秒",
            foreground='orange'))
        self._send_notification("实时识别静音警告",
                                f"已静音 {int(duration)} 秒，30 秒后将自动停止")

    def _on_rt_silence_stop(self, duration):
        """Tab 2: 静音自动停止"""
        self.root.after(0, lambda: self._do_rt_silence_stop(duration))
        self._send_notification("实时识别已自动停止",
                                f"持续静音 {int(duration)} 秒，识别已自动停止")

    def _do_rt_silence_stop(self, duration):
        """在主线程中执行停止实时识别"""
        self.status_label.config(
            text=f"状态: 已自动停止（静音 {int(duration)} 秒）",
            foreground='red')
        self.stop_realtime_recognition()

    def _on_rt_speech_resumed(self):
        """Tab 2: 声音恢复"""
        self.root.after(0, lambda: self.status_label.config(
            text="状态: 正在识别...",
            foreground='black'))


def main():
    """主函数"""
    try:
        import pyaudio
    except ImportError:
        messagebox.showerror("缺少依赖",
                             "请先安装pyaudio:\npip install pyaudio\n\n"
                             "macOS用户可能需要:\nbrew install portaudio\npip install pyaudio")
        return

    root = tk.Tk()
    app = Bili2TextGUI(root)

    def on_closing():
        if app._test_monitor is not None:
            app._test_monitor.stop()
            app._test_monitor = None
        if app.is_realtime_recording:
            if messagebox.askokcancel("退出", "正在进行实时识别，确定要退出吗？"):
                app.stop_realtime_recognition()
                root.destroy()
        elif app.audio_recorder and app.audio_recorder.recording:
            if messagebox.askokcancel("退出", "正在录音中，确定要退出吗？"):
                app.stop_recording()
                root.destroy()
        else:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
