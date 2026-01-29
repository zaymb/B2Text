#!/bin/bash
# Bili2text 快捷命令设置脚本

echo "正在设置 Bili2text 快捷命令..."

# 检查Python3是否存在
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: python3 未找到"
    echo "请先安装Python3:"
    echo "  brew install python3"
    echo "或从 https://www.python.org/downloads/ 下载"
    exit 1
fi

echo "✅ 检测到 Python3: $(python3 --version)"

# 获取当前目录的绝对路径
BILI2TEXT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 检测 shell 类型
if [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
    SHELL_NAME="zsh"
elif [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
    SHELL_NAME="bash"
else
    SHELL_RC="$HOME/.profile"
    SHELL_NAME="sh"
fi

echo "检测到 Shell: $SHELL_NAME"
echo "配置文件: $SHELL_RC"

# 创建 alias 配置
cat >> "$SHELL_RC" << EOF

# Bili2text 快捷命令
export BILI2TEXT_HOME="$BILI2TEXT_DIR"

# 主程序（原版 Whisper）
alias bili2text="cd $BILI2TEXT_DIR && python3 main_with_realtime.py"

# 高准确度版本（faster-whisper + large-v3）
alias bili2text-hd="cd $BILI2TEXT_DIR && python3 main_faster.py"

# 实时识别（原版）
alias bili2text-rt="cd $BILI2TEXT_DIR && python3 realtime_recognition.py"

# 实时识别（高准确度）
alias bili2text-rt-hd="cd $BILI2TEXT_DIR && python3 realtime_recognition_faster.py"

# GUI 界面
alias bili2text-gui="cd $BILI2TEXT_DIR && python3 window_realtime.py"

# 快速 B站下载（原版主程序）
alias bili2text-dl="cd $BILI2TEXT_DIR && python3 main.py"

# 查看输出文件
alias bili2text-out="cd $BILI2TEXT_DIR/outputs && ls -la"

# 清理临时文件
alias bili2text-clean="cd $BILI2TEXT_DIR && rm -rf bilibili_video/* audio/conv/* audio/slice/*"

# 显示帮助
alias bili2text-help="echo '
Bili2text 快捷命令:
  bili2text        - 主程序（支持B站下载和实时识别）
  bili2text-hd     - 高准确度版本（faster-whisper + large-v3，推荐）
  bili2text-rt     - 实时识别（原版）
  bili2text-rt-hd  - 实时识别（高准确度，推荐财经内容）
  bili2text-gui    - GUI界面
  bili2text-dl     - B站视频下载转文字
  bili2text-out    - 查看输出文件
  bili2text-clean  - 清理临时文件
  bili2text-help   - 显示此帮助
'"

EOF

echo ""
echo "✅ 快捷命令已添加到 $SHELL_RC"
echo ""
echo "请运行以下命令使配置生效："
echo "  source $SHELL_RC"
echo ""
echo "或重新打开终端"
echo ""
echo "可用的快捷命令："
echo "  bili2text        - 主程序"
echo "  bili2text-hd     - 高准确度版本（推荐）"
echo "  bili2text-rt     - 实时识别"
echo "  bili2text-rt-hd  - 实时识别高准确度"
echo "  bili2text-gui    - GUI界面"
echo "  bili2text-help   - 查看所有命令"