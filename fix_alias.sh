#!/bin/bash
# 修复alias配置，将python改为python3

echo "修复 Bili2text alias 配置..."
echo "="
echo ""

# 获取当前目录
BILI2TEXT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 函数：清理和更新配置文件
fix_config_file() {
    local config_file=$1
    local file_name=$(basename "$config_file")

    if [ -f "$config_file" ]; then
        echo ""
        echo "处理 $file_name..."

        # 备份原配置
        cp "$config_file" "$config_file.backup.$(date +%Y%m%d_%H%M%S)"
        echo "✅ 已备份 $file_name"

        # 清理旧的bili2text配置
        echo "清理旧配置..."
        sed -i '' '/# Bili2text 快捷命令/,/bili2text-help/d' "$config_file"

        # 也清理可能存在的单独alias行
        sed -i '' '/^alias bili2text/d' "$config_file"
        sed -i '' '/^export BILI2TEXT_HOME/d' "$config_file"

        echo "✅ 已清理 $file_name 中的旧配置"
    fi
}

# 修复 .zshrc
fix_config_file "$HOME/.zshrc"

# 修复 .bashrc
fix_config_file "$HOME/.bashrc"

# 修复 .bash_profile (如果存在)
fix_config_file "$HOME/.bash_profile"

# 选择要添加配置的文件（优先.zshrc）
if [ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ]; then
    CONFIG_FILE="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ] || [ -f "$HOME/.bashrc" ]; then
    CONFIG_FILE="$HOME/.bashrc"
else
    CONFIG_FILE="$HOME/.zshrc"
fi

echo ""
echo "添加新配置到 $(basename $CONFIG_FILE)（使用python3）..."

# 添加新的配置（使用python3）
cat >> "$CONFIG_FILE" << EOF

# Bili2text 快捷命令（已更新为python3）
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
echo "✅ 配置已修复！"
echo ""
echo "现在运行以下命令使配置生效："
echo ""
echo "  source ~/.zshrc"
echo ""
echo "然后就可以使用了："
echo "  bili2text-gui"
echo ""