#!/usr/bin/env python3
"""
Bili2text 主程序 - 使用 faster-whisper + large-v3
高准确度版本，专门针对财经等专业内容优化
"""

from utils import download_bilibili
from exAudio import *
import shutil
from realtime_recognition_faster import FasterRealtimeRecognizer
import time

def bilibili_mode():
    """B站视频识别模式（使用faster-whisper）"""
    print("\n注意：本版本使用 faster-whisper，首次运行需要下载模型")

    av = input("请输入BV号：")
    folder = download_bilibili(av)

    bv = av if av.startswith('BV') else f"BV{av}"
    bv = bv.split('/')[-1]

    foldername = process_audio_split(bv)

    # 使用 faster-whisper
    from faster_whisper import WhisperModel
    print("\n加载 faster-whisper large-v3 模型...")

    # 检测设备
    import torch
    if torch.cuda.is_available():
        device = "cuda"
        compute_type = "float16"
    else:
        device = "cpu"
        compute_type = "int8"

    model = WhisperModel("large-v3", device=device, compute_type=compute_type)

    # 询问是否需要自定义 prompt
    custom_prompt = input("需要添加关键词提示吗？(直接回车跳过): ").strip()

    if custom_prompt:
        initial_prompt = f"以下是普通话的句子。这是关于{custom_prompt}的内容。"
    else:
        initial_prompt = "以下是普通话的句子。"

    # 开始识别
    print("正在识别音频...")
    audio_list = os.listdir(f"audio/slice/{foldername}")
    audio_files = sorted(audio_list, key=lambda x: int(os.path.splitext(x)[0]))

    os.makedirs("outputs", exist_ok=True)

    i = 1
    for fn in audio_files:
        print(f"正在转换第{i}/{len(audio_files)}个音频... {fn}")

        # 使用 faster-whisper 识别
        segments, info = model.transcribe(
            f"audio/slice/{foldername}/{fn}",
            language="zh",
            initial_prompt=initial_prompt,
            beam_size=5,
            best_of=5,
            temperature=0.0,
            vad_filter=True,
            vad_parameters=dict(
                threshold=0.5,
                min_silence_duration_ms=500,
                speech_pad_ms=400
            )
        )

        # 提取文本
        text = ""
        for segment in segments:
            text += segment.text

        print(text)

        with open(f"outputs/{foldername}.txt", "a", encoding="utf-8") as f:
            f.write(text)
            f.write("\n")
        i += 1

    output_path = f"outputs/{foldername}.txt"
    print(f"\n转换完成！文件保存在: {output_path}")

    # 询问是否删除中间文件
    print("\n" + "="*50)
    cleanup = input("是否删除下载的视频和音频文件？(y/n，默认n): ").strip().lower()

    if cleanup == 'y' or cleanup == 'yes':
        try:
            video_path = f"bilibili_video/{bv}"
            if os.path.exists(video_path):
                shutil.rmtree(video_path)
                print(f"✓ 已删除视频: {video_path}")

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


def realtime_mode():
    """实时音频识别模式（使用faster-whisper）"""
    print("\n" + "="*50)
    print("实时音频识别模式（faster-whisper + large-v3）")
    print("="*50)

    print("\n优势：")
    print("• 比原版Whisper快4倍")
    print("• large-v3模型识别准确度最高")
    print("• 特别适合财经、技术等专业内容")
    print("-"*50)

    # 选择模型
    print("\n选择Whisper模型:")
    print("1. tiny   (39M, 最快)")
    print("2. base   (74M, 快速)")
    print("3. small  (244M, 平衡)")
    print("4. medium (769M, 较准确)")
    print("5. large-v2 (1550M, 很准确)")
    print("6. large-v3 (1550M, 最准确，强烈推荐)")

    model_choice = input("\n请选择 (1-6，默认6): ").strip() or "6"
    model_map = {
        "1": "tiny",
        "2": "base",
        "3": "small",
        "4": "medium",
        "5": "large-v2",
        "6": "large-v3"
    }
    model_name = model_map.get(model_choice, "large-v3")

    # 询问关键词提示
    print("\n设置关键词提示（强烈建议设置）:")
    print("财经示例: '股票、基金、投资、K线、涨跌、市值'")
    print("技术示例: '编程、Python、API、数据库、算法'")
    print("游戏示例: '游戏解说、装备、技能、副本'")
    custom_prompt = input("\n请输入关键词或主题: ").strip()

    if custom_prompt:
        prompt = f"以下是普通话的句子。这是关于{custom_prompt}的内容。"
        print(f"✓ 已设置提示词")
    else:
        prompt = ""

    # 幻觉过滤（默认开启）
    enable_filter = True
    print("✓ 幻觉过滤已启用")

    print(f"\n正在加载 {model_name} 模型（首次加载需要下载）...")

    try:
        recognizer = FasterRealtimeRecognizer(
            model_name=model_name,
            initial_prompt=prompt,
            enable_hallucination_filter=enable_filter
        )

        print("\n" + "="*50)
        print("准备开始实时识别")
        print("按回车开始，按 Ctrl+C 停止")
        print("="*50)
        input()

        recognizer.start_recording()

        # 保持运行直到用户中断
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n正在停止识别...")
    except Exception as e:
        print(f"\n发生错误: {e}")
    finally:
        if 'recognizer' in locals():
            recognizer.cleanup()


def main():
    """主函数"""
    print("\n" + "="*60)
    print("    Bili2text 高准确度版本")
    print("    Powered by faster-whisper + large-v3")
    print("="*60)

    while True:
        print("\n请选择模式:")
        print("1. B站视频识别")
        print("2. 实时音频识别")
        print("3. 退出")

        choice = input("\n请输入选项 (1-3): ").strip()

        if choice == "1":
            print("\n" + "-"*50)
            print("B站视频识别模式")
            print("-"*50)
            bilibili_mode()
            print("\n完成！")

        elif choice == "2":
            realtime_mode()
            print("\n完成！")

        elif choice == "3":
            print("\n感谢使用，再见！")
            break

        else:
            print("\n无效选项，请重新选择")

        # 询问是否继续
        if choice in ["1", "2"]:
            continue_choice = input("\n是否继续使用？(y/n，默认y): ").strip().lower()
            if continue_choice == 'n' or continue_choice == 'no':
                print("\n感谢使用，再见！")
                break


if __name__ == "__main__":
    main()