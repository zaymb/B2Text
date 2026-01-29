from utils import download_bilibili
from exAudio import *
from speech2text import *
import shutil

av = input("请输入BV号：")
folder = download_bilibili(av)

bv = av if av.startswith('BV') else f"BV{av}"
bv = bv.split('/')[-1]

foldername = process_audio_split(bv)

load_whisper("medium")

# 询问是否需要自定义 prompt
custom_prompt = input("需要添加关键词提示吗？(直接回车跳过): ").strip()

if custom_prompt:
    run_analysis(foldername, prompt=custom_prompt)
    print(f"使用自定义提示: {custom_prompt}")
else:
    run_analysis(foldername)
    print("使用默认设置")

output_path = f"outputs/{foldername}.txt"
print(f"\n转换完成！文件保存在: {output_path}")

# 询问是否删除中间文件
print("\n" + "="*50)
cleanup = input("是否删除下载的视频和音频文件？(y/n，默认n): ").strip().lower()

if cleanup == 'y' or cleanup == 'yes':
    try:
        # 删除这次下载的视频文件夹
        video_path = f"bilibili_video/{bv}"
        if os.path.exists(video_path):
            shutil.rmtree(video_path)
            print(f"✓ 已删除视频: {video_path}")
        
        # 删除这次转换的音频文件
        audio_conv_path = f"audio/conv/{foldername}.mp3"
        if os.path.exists(audio_conv_path):
            os.remove(audio_conv_path)
            print(f"✓ 已删除转换音频: {audio_conv_path}")
        
        audio_slice_path = f"audio/slice/{foldername}"
        if os.path.exists(audio_slice_path):
            shutil.rmtree(audio_slice_path)
            print(f"✓ 已删除分割音频: {audio_slice_path}")
        
        print("清理完成！")
    except Exception as e:
        print(f"清理时出错: {e}")
else:
    print("保留中间文件。")
    print(f"视频位置: bilibili_video/{bv}/")
    print(f"音频位置: audio/conv/{foldername}.mp3 和 audio/slice/{foldername}/")

print("\n完成！")
