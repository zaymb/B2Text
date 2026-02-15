#!/usr/bin/env python3
"""
分段文件识别器 - 逐个识别多个音频文件，合并结果
避免大文件爆内存，支持进度显示
"""

import os
import whisper
from datetime import datetime
from pathlib import Path


class ChunkedFileRecognizer:
    def __init__(self, model_name="base", initial_prompt="", progress_callback=None):
        """
        初始化分段识别器
        :param model_name: Whisper模型名称
        :param initial_prompt: 初始提示词
        :param progress_callback: 进度回调函数
        """
        self.model_name = model_name
        self.initial_prompt = initial_prompt or "以下是普通话的句子。"
        self.progress_callback = progress_callback
        self.model = None

        # 加载模型
        self._load_model()

    def _load_model(self):
        """加载Whisper模型"""
        self._update_progress(f"正在加载{self.model_name}模型...")
        device = "cuda" if whisper.torch.cuda.is_available() else "cpu"
        self.model = whisper.load_model(self.model_name, device=device)
        self._update_progress(f"模型加载完成 (设备: {device})")

    def _update_progress(self, message):
        """更新进度信息"""
        print(message)
        if self.progress_callback:
            self.progress_callback(message)

    def process_chunks(self, chunk_files, save_to_file=True, delete_after=False,
                       chunk_callback=None, frame_callback=None):
        """
        处理多个分段文件
        :param chunk_files: 文件路径列表或单个文件路径
        :param save_to_file: 是否保存到文件
        :param delete_after: 识别完成后是否删除分段文件
        :param chunk_callback: 每段识别后的回调 fn(idx, total, text) -> bool，返回 False 中止
        :param frame_callback: 帧级进度回调 fn(chunk_idx, total_chunks, current_frames, total_frames)
        :return: 合并后的识别文本
        """
        # 确保是列表
        if isinstance(chunk_files, str):
            chunk_files = [chunk_files]

        if not chunk_files:
            self._update_progress("错误: 没有文件需要识别")
            return ""

        # 排序文件（确保按顺序处理）
        chunk_files = sorted(chunk_files)

        total_chunks = len(chunk_files)
        self._update_progress(f"开始识别 {total_chunks} 个分段文件...")

        all_results = []
        previous_text = ""  # 用于上下文传递

        # 逐个识别每个分段
        for i, chunk_path in enumerate(chunk_files, 1):
            if not os.path.exists(chunk_path):
                self._update_progress(f"警告: 文件不存在 {chunk_path}")
                continue

            file_name = os.path.basename(chunk_path)
            self._update_progress(f"[{i}/{total_chunks}] 正在识别: {file_name}")

            try:
                # 使用前一段的末尾作为提示（改善上下文连贯性）
                if previous_text:
                    # 取前一段最后50个字符作为上下文
                    context = previous_text[-100:].strip()
                    prompt = f"{self.initial_prompt} {context}"
                else:
                    prompt = self.initial_prompt

                # 识别当前分段（捕获 tqdm 帧级进度）
                if frame_callback:
                    import whisper.transcribe as _wt
                    from tqdm import tqdm as _orig_tqdm
                    _chunk_i, _total_c = i, total_chunks

                    class _ProgressTqdm(_orig_tqdm):
                        def update(self, n=1):
                            super().update(n)
                            frame_callback(_chunk_i, _total_c, self.n, self.total)

                    _saved = _wt.tqdm
                    _wt.tqdm = _ProgressTqdm
                    try:
                        result = self.model.transcribe(
                            chunk_path, language="zh", initial_prompt=prompt,
                            temperature=0.2, fp16=False, verbose=False)
                    finally:
                        _wt.tqdm = _saved
                else:
                    result = self.model.transcribe(
                        chunk_path, language="zh", initial_prompt=prompt,
                        temperature=0.2, fp16=False, verbose=False)

                # 提取文本
                text = result["text"].strip()
                if text:
                    all_results.append(text)
                    previous_text = text

                    # 计算进度百分比
                    progress = int((i / total_chunks) * 100)
                    self._update_progress(f"[{i}/{total_chunks}] 完成 {progress}% - {len(text)}字符")

                    # 回调检查（重复检测等）
                    if chunk_callback and not chunk_callback(i, total_chunks, text):
                        self._update_progress("识别已中止")
                        break

            except Exception as e:
                self._update_progress(f"识别失败 {file_name}: {str(e)}")
                continue

        # 合并所有结果
        self._update_progress("正在合并识别结果...")
        final_text = "\n".join(all_results)

        # 保存到文件
        if save_to_file and final_text:
            output_file = self._save_result(final_text, chunk_files[0])
            self._update_progress(f"识别完成！结果已保存到: {output_file}")
        else:
            self._update_progress("识别完成！")

        # 删除分段文件（如果需要）
        if delete_after and chunk_files:
            self._cleanup_chunks(chunk_files)

        return final_text

    def _save_result(self, text, first_file_path):
        """保存识别结果到文件"""
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)

        # 生成输出文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = Path(first_file_path).stem.replace('_part001', '')
        output_file = f"{output_dir}/chunked_{base_name}_{timestamp}.txt"

        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"分段识别结果\n")
            f.write(f"模型: {self.model_name}\n")
            f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"分段数: {len(text.split('\\n'))}段\n")
            if self.initial_prompt and self.initial_prompt != "以下是普通话的句子。":
                f.write(f"提示词: {self.initial_prompt}\n")
            f.write("=" * 50 + "\n\n")
            f.write(text)

        return output_file

    def _cleanup_chunks(self, chunk_files):
        """
        清理分段文件
        :param chunk_files: 要删除的文件列表
        """
        deleted_count = 0
        for chunk_path in chunk_files:
            try:
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)
                    deleted_count += 1
                    print(f"已删除: {os.path.basename(chunk_path)}")
            except Exception as e:
                print(f"删除文件失败 {chunk_path}: {e}")

        if deleted_count > 0:
            self._update_progress(f"已清理 {deleted_count} 个分段文件")

    def process_single_file(self, file_path, save_to_file=True):
        """
        处理单个文件（兼容接口）
        """
        return self.process_chunks([file_path], save_to_file, delete_after=False)


# 测试代码
if __name__ == "__main__":
    import glob

    print("分段识别测试")
    print("=" * 50)

    # 查找测试文件
    test_files = sorted(glob.glob("recordings/录制_*_part*.wav"))

    if test_files:
        print(f"找到 {len(test_files)} 个分段文件:")
        for f in test_files[:3]:  # 显示前3个
            print(f"  - {os.path.basename(f)}")

        # 创建分段识别器
        recognizer = ChunkedFileRecognizer(
            model_name="base",
            initial_prompt="以下是普通话的内容。"
        )

        # 识别所有分段
        result = recognizer.process_chunks(test_files)

        if result:
            print("\n识别结果预览:")
            print(result[:200] + "..." if len(result) > 200 else result)
    else:
        print("没有找到分段文件")
        print("请先使用分段录音器录制音频")