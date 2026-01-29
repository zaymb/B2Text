#!/usr/bin/env python3
"""
Bili2text 主程序 - 支持B站视频识别和实时音频识别
"""

from utils import download_bilibili
from exAudio import *
from speech2text import *
import shutil
from realtime_recognition import RealtimeRecognizer
import time

def bilibili_mode():
    """B站视频识别模式"""
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


def realtime_mode():
    """实时音频识别模式（使用虚拟音频设备）"""
    print("\n" + "="*50)
    print("实时音频识别模式")
    print("="*50)

    print("\n支持的虚拟音频设备:")
    print("• Background Music (推荐，如已安装会自动使用)")
    print("• BlackHole")
    print("\n使用说明:")
    print("1. 如果使用Background Music，确保它正在运行")
    print("2. 如果使用BlackHole，需要在音频MIDI设置中配置")
    print("3. 程序会自动检测并使用可用的虚拟音频设备")
    print("-"*50)

    # 选择模型
    print("\n选择Whisper模型:")
    print("1. tiny   (39MB, 最快，准确度较低)")
    print("2. base   (74MB, 平衡)")
    print("3. small  (244MB, 较准确)")
    print("4. medium (769MB, 准确)")
    print("5. large  (1550MB, 最准确但很慢)")

    model_choice = input("\n请选择 (1-5，默认2): ").strip() or "2"
    model_map = {
        "1": "tiny",
        "2": "base",
        "3": "small",
        "4": "medium",
        "5": "large"
    }
    model_name = model_map.get(model_choice, "base")

    # 询问关键词提示
    print("\n设置关键词提示（可大幅提高识别准确度）:")
    print("示例：")
    print("  - 技术教程：'编程、Python、开发'")
    print("  - 游戏直播：'游戏解说、游戏术语'")
    print("  - 学习视频：'数学、物理、化学'")
    custom_prompt = input("\n请输入关键词或主题（回车跳过）: ").strip()

    if custom_prompt:
        prompt = f"以下是普通话的内容。这是关于{custom_prompt}的内容。"
        print(f"✓ 已设置提示词")
    else:
        prompt = ""

    # 询问是否启用幻觉过滤
    print("\n是否启用幻觉过滤？（可防止重复和错误内容）")
    filter_choice = input("启用过滤？(y/n，默认y): ").strip().lower()
    enable_filter = filter_choice != 'n'
    if enable_filter:
        print("✓ 已启用幻觉过滤")
    else:
        print("✗ 已禁用幻觉过滤")

    print(f"\n正在加载 {model_name} 模型...")

    try:
        recognizer = RealtimeRecognizer(
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
    print("    Bili2text - B站视频转文字 & 实时音频识别工具")
    print("="*60)

    while True:
        print("\n请选择模式:")
        print("1. B站视频识别（下载视频并转文字）")
        print("2. 实时音频识别（捕获系统音频）")
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