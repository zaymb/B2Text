import os
import re
import shlex
import glob
import subprocess

YTDLP = "/usr/local/bin/yt-dlp"  # yt-dlp 绝对路径

def _extract_bv(s: str) -> str:
    s = (s or "").strip()
    m = re.search(r"(BV[0-9A-Za-z]{10,})", s)
    if not m:
        raise ValueError("请输入合法的 BV 号或 URL")
    return m.group(1)

def download_bilibili(url_or_bv: str, out_root: str = "bilibili_video", need_cookies: bool = False, browser: str = "safari") -> str:
    """使用 yt-dlp 下载 B 站视频并返回下载目录路径。"""
    bv = _extract_bv(url_or_bv)
    url = f"https://www.bilibili.com/video/{bv}"

    os.makedirs(out_root, exist_ok=True)
    tmpl = os.path.join(out_root, "%(id)s/%(id)s.%(ext)s")

    cmd = f'{shlex.quote(YTDLP)} -S "res:1080" -o {shlex.quote(tmpl)} {shlex.quote(url)}'
    if need_cookies:
        cmd += f" --cookies-from-browser {shlex.quote(browser)}"

    proc = subprocess.run(cmd, shell=True)
    if proc.returncode != 0:
        raise RuntimeError("下载失败：yt-dlp 返回非零状态码")

    folder = os.path.join(out_root, bv)
    media_files = glob.glob(os.path.join(folder, "*.*"))
    if not (os.path.isdir(folder) and media_files):
        raise FileNotFoundError(f"下载目录无媒体文件：{folder}")

    for xml in glob.glob(os.path.join(folder, "*.xml")):
        try:
            os.remove(xml)
        except Exception:
            pass

    return folder