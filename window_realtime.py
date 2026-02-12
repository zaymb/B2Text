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
import shutil
import time
from datetime import datetime


class Bili2TextGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Bili2text - 视频转文字 & 实时识别工具")
        self.root.geometry("800x600")

        # 实时识别相关
        self.recognizer = None
        self.is_realtime_recording = False
        self.update_thread = None

        self.setup_ui()

    def setup_ui(self):
        """设置UI界面"""
        # 创建标签页
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # B站视频识别标签页
        self.bili_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.bili_frame, text='B站视频识别')
        self.setup_bili_tab()

        # 实时音频识别标签页
        self.realtime_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.realtime_frame, text='实时音频识别')
        self.setup_realtime_tab()

        # 本地文件识别标签页
        self.local_file_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.local_file_frame, text='本地文件识别')
        self.setup_local_file_tab()

        # 关于标签页
        self.about_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.about_frame, text='关于')
        self.setup_about_tab()

    def setup_bili_tab(self):
        """设置B站视频识别标签页"""
        # 标题
        title_label = ttk.Label(self.bili_frame, text="B站视频转文字", font=('Arial', 16, 'bold'))
        title_label.pack(pady=10)

        # 输入框架
        input_frame = ttk.Frame(self.bili_frame)
        input_frame.pack(pady=10)

        ttk.Label(input_frame, text="BV号:").grid(row=0, column=0, padx=5)
        self.bv_entry = ttk.Entry(input_frame, width=30)
        self.bv_entry.grid(row=0, column=1, padx=5)

        # 模型选择
        ttk.Label(input_frame, text="Whisper模型:").grid(row=1, column=0, padx=5, pady=5)
        self.bili_model_var = tk.StringVar(value="base")
        model_combo = ttk.Combobox(input_frame, textvariable=self.bili_model_var,
                                    values=["tiny", "base", "small", "medium", "large"],
                                    state="readonly", width=27)
        model_combo.grid(row=1, column=1, padx=5, pady=5)

        # 关键词提示
        ttk.Label(input_frame, text="关键词提示:").grid(row=2, column=0, padx=5, pady=5)
        self.keyword_entry = ttk.Entry(input_frame, width=30)
        self.keyword_entry.grid(row=2, column=1, padx=5, pady=5)

        # 按钮
        button_frame = ttk.Frame(self.bili_frame)
        button_frame.pack(pady=10)

        self.bili_start_btn = ttk.Button(button_frame, text="开始转换",
                                          command=self.start_bili_conversion)
        self.bili_start_btn.pack(side='left', padx=5)

        # 进度显示
        self.bili_progress = ttk.Progressbar(self.bili_frame, mode='indeterminate')
        self.bili_progress.pack(pady=10, padx=20, fill='x')

        # 日志显示
        log_label = ttk.Label(self.bili_frame, text="处理日志:")
        log_label.pack(pady=5)

        self.bili_log = scrolledtext.ScrolledText(self.bili_frame, height=15, width=70)
        self.bili_log.pack(pady=5, padx=20, fill='both', expand=True)

    def setup_realtime_tab(self):
        """设置实时音频识别标签页"""
        # 标题
        title_label = ttk.Label(self.realtime_frame, text="实时音频识别",
                                font=('Arial', 16, 'bold'))
        title_label.pack(pady=10)

        # 说明文本
        info_text = """使用说明:
1. 支持 Background Music 或 BlackHole
2. 如果已安装Background Music，会自动使用
3. 确保虚拟音频设备正在运行
4. 点击'开始识别'即可实时转文字"""

        info_label = ttk.Label(self.realtime_frame, text=info_text, justify='left')
        info_label.pack(pady=10)

        # 设置框架
        settings_frame = ttk.Frame(self.realtime_frame)
        settings_frame.pack(pady=10)

        # 模型选择
        ttk.Label(settings_frame, text="Whisper模型:").grid(row=0, column=0, padx=5)
        self.realtime_model_var = tk.StringVar(value="base")
        model_combo = ttk.Combobox(settings_frame, textvariable=self.realtime_model_var,
                                    values=["tiny", "base", "small", "medium", "large"],
                                    state="readonly", width=20)
        model_combo.grid(row=0, column=1, padx=5)

        # 音频设备选择
        ttk.Label(settings_frame, text="音频设备:").grid(row=1, column=0, padx=5, pady=5)
        self.device_var = tk.StringVar(value="自动检测")
        self.device_entry = ttk.Entry(settings_frame, textvariable=self.device_var, width=22)
        self.device_entry.grid(row=1, column=1, padx=5, pady=5)

        # 关键词提示
        ttk.Label(settings_frame, text="关键词提示:").grid(row=2, column=0, padx=5, pady=5)
        self.realtime_keyword_var = tk.StringVar()
        self.realtime_keyword_entry = ttk.Entry(settings_frame, textvariable=self.realtime_keyword_var, width=22)
        self.realtime_keyword_entry.grid(row=2, column=1, padx=5, pady=5)

        # 提示说明
        hint_label = ttk.Label(settings_frame, text="(如：编程教程、游戏解说、音乐等)",
                               font=('Arial', 9), foreground='gray')
        hint_label.grid(row=3, column=0, columnspan=2, pady=2)

        # 幻觉过滤选项
        self.enable_filter_var = tk.BooleanVar(value=True)
        filter_check = ttk.Checkbutton(settings_frame, text="启用幻觉过滤（防止重复和错误内容）",
                                       variable=self.enable_filter_var)
        filter_check.grid(row=4, column=0, columnspan=2, pady=5)

        # 静音检测选项
        self.rt_silence_detect_var = tk.BooleanVar(value=True)
        rt_silence_check = ttk.Checkbutton(settings_frame,
                                           text="启用静音超时检测（30秒无声自动停止）",
                                           variable=self.rt_silence_detect_var)
        rt_silence_check.grid(row=5, column=0, columnspan=2, pady=5)

        # 控制按钮
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

        # 状态显示
        self.status_label = ttk.Label(self.realtime_frame, text="状态: 未开始",
                                       font=('Arial', 10))
        self.status_label.pack(pady=5)

        # 实时文本显示
        text_label = ttk.Label(self.realtime_frame, text="识别结果:")
        text_label.pack(pady=5)

        self.realtime_text = scrolledtext.ScrolledText(self.realtime_frame, height=15, width=70)
        self.realtime_text.pack(pady=5, padx=20, fill='both', expand=True)

    def setup_local_file_tab(self):
        """设置本地文件识别标签页（带录音功能）"""
        # 标题
        title_label = ttk.Label(self.local_file_frame, text="本地文件识别 & 录音",
                                font=('Arial', 16, 'bold'))
        title_label.pack(pady=5)

        # 录音状态框架
        record_status_frame = ttk.Frame(self.local_file_frame)
        record_status_frame.pack(pady=5)

        self.record_status_label = ttk.Label(record_status_frame,
                                             text="录音状态: 未开始",
                                             font=('Arial', 11, 'bold'))
        self.record_status_label.pack()

        # 录音控制按钮框架
        record_control_frame = ttk.Frame(self.local_file_frame)
        record_control_frame.pack(pady=5)

        self.start_record_btn = ttk.Button(record_control_frame, text="开始录制",
                                           command=self.start_recording)
        self.start_record_btn.pack(side='left', padx=5)

        self.stop_record_btn = ttk.Button(record_control_frame, text="停止录制",
                                          command=self.stop_recording,
                                          state='disabled')
        self.stop_record_btn.pack(side='left', padx=5)

        self.browse_btn = ttk.Button(record_control_frame, text="选择已有文件...",
                                     command=self.browse_file)
        self.browse_btn.pack(side='left', padx=5)

        # 录音设备选择框架
        device_frame = ttk.Frame(self.local_file_frame)
        device_frame.pack(pady=5)

        ttk.Label(device_frame, text="录音设备:").pack(side='left', padx=5)

        # 获取可用音频设备（使用分段录音器的方法）
        self.audio_devices = ChunkedAudioRecorder.get_audio_devices()
        self.record_device_var = tk.StringVar(value=self.audio_devices[0] if self.audio_devices else "default")

        self.device_combo = ttk.Combobox(device_frame,
                                         textvariable=self.record_device_var,
                                         values=self.audio_devices,
                                         state="readonly", width=30)
        self.device_combo.pack(side='left', padx=5)

        # 刷新设备按钮
        refresh_btn = ttk.Button(device_frame, text="刷新",
                                 command=self.refresh_audio_devices,
                                 width=6)
        refresh_btn.pack(side='left', padx=2)

        # 静音检测设置框架
        silence_frame = ttk.LabelFrame(self.local_file_frame, text="静音自动检测")
        silence_frame.pack(pady=5, padx=20, fill='x')

        self.silence_detect_var = tk.BooleanVar(value=True)
        silence_check = ttk.Checkbutton(silence_frame, text="启用静音自动检测",
                                        variable=self.silence_detect_var)
        silence_check.pack(anchor='w', padx=5, pady=2)

        silence_params_frame = ttk.Frame(silence_frame)
        silence_params_frame.pack(anchor='w', padx=20, pady=2)

        ttk.Label(silence_params_frame, text="警告阈值(秒):").pack(side='left', padx=2)
        self.silence_warn_var = tk.IntVar(value=10)
        warn_spin = ttk.Spinbox(silence_params_frame, from_=5, to=60,
                                textvariable=self.silence_warn_var, width=5)
        warn_spin.pack(side='left', padx=2)

        ttk.Label(silence_params_frame, text="自动停止(秒):").pack(side='left', padx=(10, 2))
        self.silence_stop_var = tk.IntVar(value=30)
        stop_spin = ttk.Spinbox(silence_params_frame, from_=10, to=120,
                                textvariable=self.silence_stop_var, width=5)
        stop_spin.pack(side='left', padx=2)

        # 文件路径显示框架
        file_path_frame = ttk.Frame(self.local_file_frame)
        file_path_frame.pack(pady=5, fill='x', padx=20)

        ttk.Label(file_path_frame, text="已选文件:").pack(side='left')
        self.file_path_var = tk.StringVar()
        file_path_label = ttk.Label(file_path_frame,
                                    textvariable=self.file_path_var,
                                    font=('Arial', 9),
                                    foreground='blue')
        file_path_label.pack(side='left', padx=5)

        # 分隔线
        ttk.Separator(self.local_file_frame, orient='horizontal').pack(fill='x', pady=10, padx=20)

        # Whisper设置框架
        whisper_frame = ttk.Frame(self.local_file_frame)
        whisper_frame.pack(pady=5)

        # 模型选择
        model_frame = ttk.Frame(whisper_frame)
        model_frame.pack(pady=2)

        ttk.Label(model_frame, text="Whisper模型:").pack(side='left', padx=5)
        self.local_model_var = tk.StringVar(value="base")
        model_combo = ttk.Combobox(model_frame, textvariable=self.local_model_var,
                                   values=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
                                   state="readonly", width=15)
        model_combo.pack(side='left', padx=5)

        # 关键词提示
        keyword_frame = ttk.Frame(whisper_frame)
        keyword_frame.pack(pady=2)

        ttk.Label(keyword_frame, text="关键词提示:").pack(side='left', padx=5)
        self.local_keyword_var = tk.StringVar()
        self.local_keyword_entry = ttk.Entry(keyword_frame,
                                            textvariable=self.local_keyword_var,
                                            width=30)
        self.local_keyword_entry.pack(side='left', padx=5)

        ttk.Label(keyword_frame, text="(可选)",
                 font=('Arial', 9), foreground='gray').pack(side='left')

        # 开始识别按钮
        recognize_frame = ttk.Frame(self.local_file_frame)
        recognize_frame.pack(pady=10)

        self.local_start_btn = ttk.Button(recognize_frame, text="开始识别",
                                          command=self.start_local_recognition,
                                          state='disabled')
        self.local_start_btn.pack()

        # 进度条
        self.local_progress = ttk.Progressbar(self.local_file_frame, mode='indeterminate')
        self.local_progress.pack(pady=5, padx=20, fill='x')

        # 识别状态标签
        self.local_status_label = ttk.Label(self.local_file_frame,
                                            text="状态: 就绪",
                                            font=('Arial', 10),
                                            foreground='blue')
        self.local_status_label.pack(pady=2)

        # 识别结果框架
        result_frame = ttk.Frame(self.local_file_frame)
        result_frame.pack(fill='both', expand=True, padx=20, pady=5)

        result_label = ttk.Label(result_frame, text="识别结果:")
        result_label.pack(anchor='w')

        # 结果文本框
        self.local_result_text = scrolledtext.ScrolledText(result_frame, height=10, width=70)
        self.local_result_text.pack(fill='both', expand=True, pady=5)

        # 保存按钮
        save_frame = ttk.Frame(self.local_file_frame)
        save_frame.pack(pady=5)

        self.local_save_btn = ttk.Button(save_frame, text="保存结果",
                                         command=self.save_local_result,
                                         state='disabled')
        self.local_save_btn.pack()

        # 初始化录音相关
        self.audio_recorder = None
        self.local_recognizer = None
        self.local_result = None
        self.recording_timer_thread = None
        self.chunk_files = None  # 存储分段文件列表

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

    def start_bili_conversion(self):
        """开始B站视频转换"""
        bv = self.bv_entry.get().strip()
        if not bv:
            messagebox.showerror("错误", "请输入BV号")
            return

        # 在新线程中执行
        thread = threading.Thread(target=self._bili_conversion_thread, args=(bv,))
        thread.daemon = True
        thread.start()

    def _bili_conversion_thread(self, bv):
        """B站视频转换线程"""
        try:
            self.bili_start_btn.config(state='disabled')
            self.bili_progress.start()
            self.bili_log.delete(1.0, tk.END)

            # 下载视频
            self.log_bili("开始下载视频...")
            folder = download_bilibili(bv)

            bv = bv if bv.startswith('BV') else f"BV{bv}"
            bv = bv.split('/')[-1]

            # 处理音频
            self.log_bili("提取和分割音频...")
            foldername = process_audio_split(bv)

            # 加载模型
            model = self.bili_model_var.get()
            self.log_bili(f"加载{model}模型...")
            load_whisper(model)

            # 开始识别
            self.log_bili("开始语音识别...")
            keyword = self.keyword_entry.get().strip()
            if keyword:
                run_analysis(foldername, prompt=keyword)
            else:
                run_analysis(foldername)

            output_path = f"outputs/{foldername}.txt"
            self.log_bili(f"转换完成！文件保存在: {output_path}")

            messagebox.showinfo("完成", f"转换完成！\n文件保存在: {output_path}")

        except Exception as e:
            self.log_bili(f"错误: {str(e)}")
            messagebox.showerror("错误", str(e))

        finally:
            self.bili_progress.stop()
            self.bili_start_btn.config(state='normal')

    def log_bili(self, message):
        """添加B站转换日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.bili_log.insert(tk.END, f"[{timestamp}] {message}\n")
        self.bili_log.see(tk.END)
        self.root.update()

    def start_realtime_recognition(self):
        """开始实时识别"""
        try:
            # 获取设置
            model = self.realtime_model_var.get()
            device = self.device_var.get()
            if device == "自动检测" or device == "自动检测BlackHole":
                device = None

            # 获取关键词提示
            keyword = self.realtime_keyword_var.get().strip()
            if keyword:
                prompt = f"以下是普通话的内容。这是关于{keyword}的内容。"
            else:
                prompt = ""

            # 获取幻觉过滤设置
            enable_filter = self.enable_filter_var.get()

            # 创建识别器
            self.status_label.config(text="状态: 正在加载模型...")
            self.root.update()

            # 静音检测配置
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
                **silence_kwargs
            )

            # 开始录音
            self.recognizer.start_recording()
            self.is_realtime_recording = True

            # 更新UI
            self.realtime_start_btn.config(state='disabled')
            self.realtime_stop_btn.config(state='normal')
            self.status_label.config(text="状态: 正在识别...")

            # 启动更新线程
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
            # 保存文件路径
            if hasattr(self.recognizer, 'output_file'):
                output_file = self.recognizer.output_file
            if hasattr(self.recognizer, 'clean_output_file'):
                clean_output_file = self.recognizer.clean_output_file

            self.recognizer.stop_recording()
            self.is_realtime_recording = False

            # 等待更新线程结束
            if self.update_thread:
                self.update_thread.join(timeout=2)

            self.recognizer.cleanup()
            self.recognizer = None

        # 更新UI
        self.realtime_start_btn.config(state='normal')
        self.realtime_stop_btn.config(state='disabled')
        self.status_label.config(text="状态: 已停止")

        # 显示保存位置
        if output_file and clean_output_file:
            messagebox.showinfo("完成",
                f"识别结果已保存:\n\n"
                f"📝 带时间戳版本:\n{output_file}\n\n"
                f"📄 干净版本(无时间戳):\n{clean_output_file}")

    def _update_realtime_text(self):
        """更新实时识别文本"""
        while self.is_realtime_recording:
            if self.recognizer:
                # 获取最新识别结果
                new_texts = self.recognizer.get_latest_text()
                for text in new_texts:
                    self.realtime_text.insert(tk.END, text + "\n")
                    self.realtime_text.see(tk.END)

            time.sleep(0.5)

    def clear_realtime_text(self):
        """清空实时识别文本"""
        self.realtime_text.delete(1.0, tk.END)

    # 本地文件识别相关方法
    # 录音相关方法
    def start_recording(self):
        """开始录音（使用分段录音器，突破6分30秒限制）"""
        try:
            device = self.record_device_var.get()

            # 静音检测配置
            silence_kwargs = {}
            if self.silence_detect_var.get():
                silence_kwargs = dict(
                    silence_warning_threshold=self.silence_warn_var.get(),
                    silence_stop_threshold=self.silence_stop_var.get(),
                    on_silence_warning=self._on_silence_warning,
                    on_silence_stop=self._on_silence_stop,
                    on_speech_resumed=self._on_speech_resumed,
                )

            # 使用分段录音器，每5分钟一段，支持长时间录音
            self.audio_recorder = ChunkedAudioRecorder(
                device_name=device,
                chunk_duration=300,  # 5分钟一段
                **silence_kwargs
            )

            # 启动录音
            if self.audio_recorder.start_recording(duration_callback=self._update_record_duration):
                # 更新UI状态
                self.record_status_label.config(text="录音状态: 录制中 00:00 (第1段)")
                self.start_record_btn.config(state='disabled')
                self.stop_record_btn.config(state='normal')
                self.browse_btn.config(state='disabled')
                self.local_start_btn.config(state='disabled')

            else:
                messagebox.showerror("错误", "无法启动录音，请检查音频设备")

        except Exception as e:
            messagebox.showerror("错误", f"录音失败: {str(e)}")

    def stop_recording(self):
        """停止录音（返回分段文件列表）"""
        if self.audio_recorder:
            self.record_status_label.config(text="录音状态: 正在保存...")
            self.root.update()

            # 不合并，返回分段文件列表
            chunk_files = self.audio_recorder.stop_recording(merge=False)

            if chunk_files:
                # 存储分段文件列表
                self.chunk_files = chunk_files if isinstance(chunk_files, list) else [chunk_files]

                # 显示文件信息
                if len(self.chunk_files) > 1:
                    self.file_path_var.set(f"已录制 {len(self.chunk_files)} 个分段文件")
                    self.record_status_label.config(
                        text=f"录音状态: 已完成（{len(self.chunk_files)}段，待识别）"
                    )
                    files_info = "\n".join([os.path.basename(f) for f in self.chunk_files[:3]])
                    if len(self.chunk_files) > 3:
                        files_info += f"\n... 等{len(self.chunk_files)}个文件"
                    messagebox.showinfo("录音完成",
                                      f"录音已完成，共{len(self.chunk_files)}个分段:\n{files_info}")
                else:
                    self.file_path_var.set(self.chunk_files[0])
                    self.record_status_label.config(text=f"录音状态: 已完成")
                    messagebox.showinfo("录音完成", f"录音已保存到:\n{self.chunk_files[0]}")

                self.local_start_btn.config(state='normal')
            else:
                self.record_status_label.config(text="录音状态: 未开始")
                self.chunk_files = None

            # 恢复UI状态
            self.start_record_btn.config(state='normal')
            self.stop_record_btn.config(state='disabled')
            self.browse_btn.config(state='normal')

            self.audio_recorder = None

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
            self.local_start_btn.config(state='normal')
            self.record_status_label.config(text="录音状态: 已选择文件")
            # 清除分段文件记录
            self.chunk_files = None

    def start_local_recognition(self):
        """开始本地文件识别（支持分段识别）"""
        # 检查是否有分段文件
        if hasattr(self, 'chunk_files') and self.chunk_files:
            # 分段识别模式
            if len(self.chunk_files) > 1:
                response = messagebox.askyesno("分段识别",
                                              f"检测到{len(self.chunk_files)}个分段文件。\n"
                                              f"是否进行分段识别（逐个识别，避免爆内存）？")
                if not response:
                    return
        else:
            # 单文件模式
            file_path = self.file_path_var.get().strip()
            if not file_path:
                messagebox.showerror("错误", "请先选择文件")
                return

            if "个分段文件" not in file_path and not os.path.exists(file_path):
                messagebox.showerror("错误", "文件不存在")
                return

        # 在新线程中执行
        thread = threading.Thread(target=self._local_recognition_thread)
        thread.daemon = True
        thread.start()

    def _local_recognition_thread(self):
        """本地文件识别线程（支持分段）"""
        try:
            # 禁用按钮
            self.local_start_btn.config(state='disabled')
            self.browse_btn.config(state='disabled')
            self.local_progress.start()

            # 获取设置
            model = self.local_model_var.get()
            keyword = self.local_keyword_var.get().strip()

            # 设置提示词
            if keyword:
                initial_prompt = f"以下是普通话的句子。这是关于{keyword}的内容。"
            else:
                initial_prompt = ""

            # 清空结果区
            self.local_result_text.delete(1.0, tk.END)

            # 判断是分段识别还是单文件识别
            if hasattr(self, 'chunk_files') and self.chunk_files and len(self.chunk_files) > 1:
                # 使用分段识别器
                self.record_status_label.config(text=f"识别状态: 准备识别{len(self.chunk_files)}个分段...")
                self.local_status_label.config(text="状态: 正在进行分段识别...")

                # 创建分段识别器
                chunked_recognizer = ChunkedFileRecognizer(
                    model_name=model,
                    initial_prompt=initial_prompt,
                    progress_callback=self._update_local_status
                )

                # 识别所有分段（完成后删除分段文件）
                self.local_result = chunked_recognizer.process_chunks(
                    self.chunk_files,
                    save_to_file=True,
                    delete_after=True  # 识别完成后删除分段文件
                )

                self.record_status_label.config(text=f"识别状态: 完成（已识别{len(self.chunk_files)}段，文件已清理）")
                # 清空分段文件记录
                self.chunk_files = None

            else:
                # 单文件识别（原逻辑）
                file_path = self.file_path_var.get().strip()
                self.record_status_label.config(text="识别状态: 正在识别...")

                # 创建单文件识别器
                self.local_recognizer = LocalFileRecognizer(
                    model_name=model,
                    initial_prompt=initial_prompt,
                    progress_callback=self._update_local_status
                )

                # 开始识别
                self.local_result = self.local_recognizer.process_file(file_path, save_to_file=True)

            # 显示结果
            self.local_result_text.insert(tk.END, self.local_result)
            self.local_result_text.see(1.0)

            # 启用保存按钮
            self.local_save_btn.config(state='normal')

            # 显示完成消息
            self.record_status_label.config(text="录音状态: 识别完成")
            messagebox.showinfo("完成", "文件识别完成！\n结果已自动保存到 outputs 目录")

        except Exception as e:
            self.record_status_label.config(text=f"录音状态: 错误")
            messagebox.showerror("错误", str(e))

        finally:
            # 恢复按钮
            self.local_start_btn.config(state='normal')
            self.browse_btn.config(state='normal')
            self.local_progress.stop()

    def _update_local_status(self, message):
        """更新本地识别状态"""
        self.local_status_label.config(text=f"状态: {message}")
        self.root.update()

    def save_local_result(self):
        """保存本地识别结果"""
        if not self.local_result:
            messagebox.showerror("错误", "没有识别结果")
            return

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

    def clear_local_text(self):
        """清空本地识别结果"""
        self.local_result_text.delete(1.0, tk.END)
        self.local_result = None
        self.local_save_btn.config(state='disabled')
        self.local_status_label.config(text="状态: 就绪")

    # ---- 系统通知 ----
    def _send_notification(self, title, message):
        """发送 macOS 系统通知"""
        try:
            import subprocess
            subprocess.Popen([
                'osascript', '-e',
                f'display notification "{message}" with title "{title}"'
            ])
        except Exception:
            pass

    # ---- Tab 3 静音检测回调 ----
    def _on_silence_warning(self, duration):
        """Tab 3: 静音警告"""
        self.root.after(0, lambda: self.record_status_label.config(
            text=f"录音状态: 静音警告! 已静音 {int(duration)} 秒",
            foreground='orange'))
        self._send_notification("录音静音警告",
                                f"已静音 {int(duration)} 秒，{self.silence_stop_var.get()} 秒后将自动停止")

    def _on_silence_stop(self, duration):
        """Tab 3: 静音自动停止"""
        self.root.after(0, lambda: self._do_silence_stop_recording(duration))
        self._send_notification("录音已自动停止",
                                f"持续静音 {int(duration)} 秒，录音已自动停止")

    def _do_silence_stop_recording(self, duration):
        """在主线程中执行停止录音"""
        self.record_status_label.config(
            text=f"录音状态: 已自动停止（静音 {int(duration)} 秒）",
            foreground='red')
        self.stop_recording()

    def _on_speech_resumed(self):
        """Tab 3: 声音恢复"""
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
    # 检查依赖
    try:
        import pyaudio
    except ImportError:
        messagebox.showerror("缺少依赖",
                             "请先安装pyaudio:\npip install pyaudio\n\n"
                             "macOS用户可能需要:\nbrew install portaudio\npip install pyaudio")
        return

    root = tk.Tk()
    app = Bili2TextGUI(root)

    # 设置窗口关闭事件
    def on_closing():
        if app.is_realtime_recording:
            if messagebox.askokcancel("退出", "正在进行实时识别，确定要退出吗？"):
                app.stop_realtime_recognition()
                root.destroy()
        else:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()