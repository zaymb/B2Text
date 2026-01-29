from utils import download_bilibili
from exAudio import process_audio_split

def process_video(self):
    try:
        self.log("[LOG][INFO] ==========")
        self.log("[LOG][INFO] 正在下载视频...")

        folder = download_bilibili(self.input_var.get(), need_cookies=False)

        self.log(f"[LOG][INFO] 下载成功：{folder}")
        self.log("[LOG][INFO] 正在分割音频...")

        out = process_audio_split(folder)
        self.log(f"[LOG][INFO] 分割完成：{out}")

    except Exception as e:
        import traceback; traceback.print_exc()
        self.log(f"[LOG][INFO] 失败：{e}")
        return