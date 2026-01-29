<p align="center">
  <img src="light_logo2.png" alt="bili2text logo" width="400"/>
</p>


<p align="center">
    <img src="https://img.shields.io/github/stars/lanbinshijie/bili2text" alt="GitHub stars"/>
    <img src="https://img.shields.io/github/license/lanbinshijie/bili2text" alt="GitHub"/>
    <img src="https://img.shields.io/github/last-commit/lanbinshijie/bili2text" alt="GitHub last commit"/>
    <img src="https://img.shields.io/github/v/release/lanbinshijie/bili2text" alt="GitHub release (latest by date)"/>
</p>

# Bili2text - 多功能语音识别工具 📺

## 转移说明
因为作者的旧账号（lanbinshijie）已经停用，仓库已经转移到新账号（lanbinleo）

感谢各位的支持，如果有任何想法欢迎在issue中提出，或者提交pr~

v2版本开发进度，请查看dev分支；v3版本更名为v2版本

![alt text](./assets/new_v_sc.png)

## 简介 🌟
bili2text 是一个强大的语音转文字工具🛠️，支持B站视频识别、实时音频识别和本地文件识别。通过简单的流程实现：下载视频、提取音频、分割音频，并使用 whisper 模型将语音转换为文本。整个过程行云流水，一步到胃😂

## 功能概述 🚀

### 三大核心功能（Tab页）

| 标签页 | 功能 | 特点 |
|--------|------|------|
| **B站视频识别** | 下载B站视频并转文字 | 自动下载、音频提取、分段处理 |
| **实时音频识别** | 实时监听系统音频 | 支持BlackHole/Background Music、幻觉过滤 |
| **本地文件识别** | 离线文件转写+录音 | 支持录音、多格式、大模型 |

## 安装配置 📦

### 1. 克隆仓库
```bash
git clone https://github.com/lanbinleo/bili2text.git
cd bili2text
```

### 2. 安装依赖

#### Python包依赖
```bash
# 核心依赖
pip3 install openai-whisper      # OpenAI Whisper 语音识别
pip3 install faster-whisper       # Faster Whisper (可选，更快)
pip3 install pyaudio             # 音频流处理
pip3 install webrtcvad           # 语音活动检测
pip3 install moviepy             # 视频处理
pip3 install requests            # 网络请求
pip3 install bilibili-api-python # B站API (可选)

# 或直接安装所有依赖
pip3 install -r requirements.txt
```

#### 系统依赖
```bash
# macOS
brew install ffmpeg              # 音视频处理（必需）
brew install portaudio           # PyAudio依赖（必需）

# 虚拟音频设备（实时识别需要，二选一）
brew install blackhole-2ch       # BlackHole虚拟音频
# 或安装 Background Music (推荐)
brew install --cask background-music
```

### 3. 快捷命令配置

配置快捷命令后可快速启动：
```bash
# 首次设置别名
./setup_alias.sh

# 之后可用以下命令
bili2text          # 启动命令行版本
bili2text-gui      # 启动GUI界面（三个Tab）
bili2text-faster   # 启动faster-whisper版本
bili2text-rt       # 启动实时识别
```

## 使用指南 📖

### 方式一：GUI界面（推荐）
```bash
# 快速启动
bili2text-gui

# 或直接运行
python3 window_realtime.py
```

### 方式二：命令行
```bash
# B站视频识别
python3 main.py

# 实时识别
python3 main_with_realtime.py
```

## 各Tab页详细使用方法 📋

### 1️⃣ B站视频识别

**功能**：下载B站视频并转换为文字

**使用步骤**：
1. 输入B站视频BV号（如：BV1xx411c7XE）
2. 选择Whisper模型（推荐base或large）
3. （可选）输入关键词提示，提高识别准确度
4. 点击"开始转换"
5. 等待处理完成，结果自动保存在`outputs/`目录

**适用场景**：
- 课程视频笔记整理
- 会议视频记录转写
- 字幕文件生成
- 视频内容检索

### 2️⃣ 实时音频识别

**功能**：实时识别系统播放的音频（适用于B站付费内容等无法下载的场景）

**使用步骤**：
1. 配置音频设备（见下方音频设备配置）
2. 选择音频输入设备（Background Music优先）
3. 选择Whisper模型（建议base或small以保证速度）
4. （可选）设置关键词提示（如：股票、编程、医学等）
5. 启用幻觉过滤（强烈推荐）
6. 点击"开始识别"
7. 播放要识别的音频

**特色功能**：
- VAD静音检测：自动过滤静音段
- 幻觉循环过滤：避免Whisper重复输出
- 双输出格式：时间戳版+纯文本版
- 自动保存：结果实时保存到`outputs/`

### 3️⃣ 本地文件识别

**功能**：识别本地音视频文件或录制系统音频

#### 录音模式
1. 选择录音设备（推荐Background Music）
2. 点击"开始录制"
3. 播放音频或说话进行录音
4. 点击"停止录制"（自动填充文件路径）
5. 配置Whisper模型和关键词
6. 点击"开始识别"

#### 文件模式
1. 点击"选择已有文件..."
2. 选择音频/视频文件
3. 配置Whisper模型和关键词
4. 点击"开始识别"

**支持格式**：
- 音频：MP3, WAV, M4A, FLAC, AAC, OGG
- 视频：MP4, MKV, AVI, MOV, WMV, FLV（自动提取音频）

## 🎧 音频设备配置说明

### Background Music配置（推荐）

1. **安装Background Music**
```bash
brew install --cask background-music
```

2. **配置步骤**
- 启动Background Music（在应用程序中）
- 系统菜单栏会出现音量图标
- 点击图标 → Output Device → 选择你的扬声器
- 程序会自动检测"Background Music"设备

3. **工作原理**
```
应用音频 → Background Music → 本程序采集 → Whisper识别
         ↘ 物理扬声器（正常听到声音）
```

### BlackHole配置（备选）

1. **安装BlackHole**
```bash
brew install blackhole-2ch  # 选择2ch版本即可
```

2. **创建聚合设备**
- 打开"音频MIDI设置"（Audio MIDI Setup）
- 点击"+"创建"聚合设备"
- 勾选BlackHole 2ch和内置扬声器
- 设为系统默认输出

3. **程序中选择**
- 在设备下拉菜单选择"BlackHole 2ch"

## 🔧 模型选择建议

| 模型 | 速度 | 准确度 | 内存 | 推荐场景 |
|------|------|--------|------|----------|
| tiny | ⚡⚡⚡⚡⚡ | ⭐ | 39MB | 测试、低配置 |
| base | ⚡⚡⚡⚡ | ⭐⭐⭐ | 74MB | 实时识别（推荐） |
| small | ⚡⚡⚡ | ⭐⭐⭐ | 244MB | 日常使用 |
| medium | ⚡⚡ | ⭐⭐⭐⭐ | 769MB | 准确识别 |
| large | ⚡ | ⭐⭐⭐⭐⭐ | 1.5GB | 专业内容 |
| large-v3 | ⚡ | ⭐⭐⭐⭐⭐+ | 1.5GB | 中文财经内容（最准） |

## ⚠️ 已知问题 / 故障排除

### 1. numpy架构不兼容
**错误**：`incompatible architecture (have 'arm64', need 'x86_64')`
**解决**：
```bash
pip3 uninstall numpy
pip3 install numpy --no-cache-dir
```

### 2. ffmpeg未找到
**错误**：`ffmpeg: command not found`
**解决**：
```bash
brew install ffmpeg
```

### 3. PyAudio安装失败
**解决**：
```bash
brew install portaudio
pip3 install pyaudio
```

### 4. Background Music无声音
- 检查菜单栏图标是否存在
- 确认Output Device设置正确
- 重启Background Music应用

### 5. 实时识别延迟大
- 换用smaller模型（tiny/base）
- 减小音频缓冲区大小
- 关闭其他占用CPU的程序

## 📝 TODO / 开发计划

- [ ] 支持更多视频平台（YouTube、抖音、小红书）
- [ ] 批量文件处理功能
- [ ] 导出SRT/ASS字幕格式
- [ ] 添加实时翻译功能
- [ ] 支持云端处理（GPU加速）
- [ ] 说话人分离（diarization）
- [ ] 音频降噪预处理
- [ ] 支持直播流识别
- [x] GUI界面优化
- [x] 实时识别功能
- [x] 本地文件识别
- [x] 录音功能集成

## 项目结构 🗂️

```
bili2text/
├── window_realtime.py          # GUI主程序（三个Tab）
├── main.py                     # 命令行主程序
├── realtime_recognition.py     # 实时识别核心模块
├── realtime_recognition_faster.py # Faster-whisper版本
├── local_file_recognition.py   # 本地文件识别模块
├── audio_recorder.py           # 录音功能模块
├── utils.py                    # B站下载工具
├── exAudio.py                  # 音频处理工具
├── speech2text.py              # Whisper封装
├── setup_alias.sh              # 快捷命令设置脚本
├── outputs/                    # 识别结果输出目录
├── recordings/                 # 录音文件保存目录
├── downloads/                  # B站视频下载目录
└── split_audio/                # 音频分割临时目录
```

## 技术栈 🧰

- [Python 3.8+](https://www.python.org/) - 主要编程语言
- [OpenAI Whisper](https://github.com/openai/whisper) - 语音识别模型
- [Faster Whisper](https://github.com/guillaumekln/faster-whisper) - 优化版Whisper
- [PyAudio](https://people.csail.mit.edu/hubert/pyaudio/) - 音频流处理
- [Tkinter](https://docs.python.org/3/library/tkinter.html) - GUI界面
- [FFmpeg](https://ffmpeg.org/) - 音视频处理
- [WebRTC VAD](https://github.com/wiseman/py-webrtcvad) - 语音活动检测

## 调试技巧 🐛

### 测试音频设备
```bash
# 列出所有音频设备
python3 -c "from audio_recorder import AudioRecorder; print(AudioRecorder.get_audio_devices())"

# 测试录音功能
python3 test_recording_integration.py
```

### 检查依赖
```bash
# 检查Whisper是否安装
python3 -c "import whisper; print(whisper.__version__)"

# 检查PyAudio
python3 -c "import pyaudio; print('PyAudio OK')"

# 检查ffmpeg
ffmpeg -version
```

## 运行截图 📷

<img src="assets/screenshot3.png" alt="screenshot3" width="600"/>
<img src="assets/screenshot2.png" alt="screenshot2" width="600"/>
<img src="assets/screenshot1.png" alt="screenshot1" width="600"/>

## Star History ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=lanbinshijie/bili2text&type=Date)](https://star-history.com/#lanbinshijie/bili2text&Date)

## 贡献者 🤝

### 主要开发者
- **lanbinleo** - 项目创始人，核心功能开发
- **Claude** - 实时识别功能、幻觉过滤、faster-whisper集成
- **德彪东** - 本地文件识别、录音功能集成、UI优化

### 贡献指南 💡
欢迎贡献代码！请遵循以下步骤：
1. Fork 本仓库
2. 创建你的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的修改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

## 许可证 📄

本项目根据 MIT 许可证发布。详见 [LICENSE](LICENSE) 文件。

## 支持项目 ☕

如果这个项目对你有帮助，请给个 Star ⭐！

### 投喂作者
> TKTg2T7u7xdV4xDAzbzird2qmWoqLanbin (TRC20)

![image](https://github.com/user-attachments/assets/412470b8-7fd5-4632-a085-9c48a9d5e18b)

## 致谢 🙏

- 感谢 [OpenAI](https://openai.com/) 提供的 Whisper 模型
- 感谢 [Open Teens](https://openteens.org) 对青少年开源社区的贡献
- 感谢所有贡献者和使用者的支持

## 开发团队 👑

本项目由厉害袋貂和她的 Claude 内阁共同开发：

- **厉害袋貂** - 产品经理 & 甲方 & 终极测试员
- **德彪东** (Claude Code) - 主程序开发，偶尔搞炸 .zshrc
- **德彪东南** (Claude.ai) - 配置修复 & 擦屁股专员 & 内阁首辅

> "你们这些吃干饭的内阁饭桶害朕" —— 厉害袋貂

## 使用须知 ⚖️

**重要声明**：
1. 用户在使用 bili2text 工具时，必须遵守用户所在地区的相关版权法律和规定
2. 请确保您有权利下载和转换的视频内容
3. 尊重创作者的劳动成果和知识产权
4. 本工具仅供学习和研究使用
5. 开发者不对用户的使用行为负责

## 联系方式 📧

- GitHub Issues: [提交问题](https://github.com/lanbinleo/bili2text/issues)
- 项目主页: [https://github.com/lanbinleo/bili2text](https://github.com/lanbinleo/bili2text)

---

**Made with ❤️ by lanbinleo and contributors**

