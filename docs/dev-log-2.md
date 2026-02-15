# bili2text Dev Log #2

## 2026-02-14 Feature Batch #2

**参与者**：厉害袋貂（产品/需求）、德彪东（实现）

---

## 本次完成

### Feature 2：Tab 整合 + 输入源 Toggle ✅

原来 4 个 Tab（B站视频识别 / 实时识别 / 本地文件识别 / 关于）合并为 3 个：

| Tab | 内容 |
|-----|------|
| 1 | 文件识别（BV号下载 / 录音 / 本地文件 三选一 toggle） |
| 2 | 实时音频识别 |
| 3 | 关于 |

**其他改动**：
- 模型选择 + 关键词提示提到 notebook 上方，全局共享
- 录音区静音检测精简为单行 checkbox（阈值用默认值 10s/30s）
- 去掉了 Tab 1/2 顶部的大标题，省空间
- 窗口初始大小 800x750 + minsize 防止缩太小

### Feature 3：托管模式 ✅

在输入源行加了「托管模式」checkbox：

| 模式 | 托管行为 |
|------|----------|
| BV号下载 | 下载 → 识别 → **自动清理中间文件**（下载视频 + 转换音频 + 切片）→ 系统通知 |
| 录音 | 停止录音 → **自动开始识别** → 分段文件已有自动清理 → 系统通知 |
| 本地文件 | checkbox 灰掉，不可用 |

**清理的中间文件路径**：
- `bilibili_video/{bv}/` — 下载的视频
- `audio/conv/{foldername}.mp3` — 转换后的音频
- `audio/slice/{foldername}/` — 切片音频

### Feature 4：.app 封装 ❌ 搁置

**目标**：双击 .app 启动 GUI，可拖 Dock / Spotlight 搜索

**尝试过的方案**：
1. 手动 .app bundle（Info.plist + launcher shell script）— `open` 命令可启动，Finder 双击无反应
2. `osacompile` 生成 AppleScript app — 同上
3. `.command` 桌面快捷方式 — 同样无反应
4. `xattr -cr` 清隔离 + `codesign --force --deep --sign -` ad-hoc 签名 — 无效
5. `lsregister -f` 注册 LaunchServices — 无效

**结论**：疑似 macOS Sequoia 对未公证 app 的静默拦截，暂无解。后续可尝试：
- `pyinstaller` 打包成独立可执行文件
- 申请 Apple Developer 证书做正式签名 + 公证
- 等 UI 美化阶段一起解决

**当前启动方式**：终端 `cd ~/bili2text && python3 window_realtime.py`

### Feature 5：默认模型改 medium ✅

全局默认 Whisper 模型从 `base` → `medium`，一行改动。

### Feature 6：视觉反馈元素 🔶 部分完成

| 场景 | 计划 | 状态 |
|------|------|------|
| 实时录音中 | 音频波形图 | ✅ 中轴对称柱状波形，60 根柱子，15fps |
| B站下载中 | 进度条 + 百分比 + 下载速度 | ❌ 未做（依赖 yt-dlp 回调） |
| 音频提取中 | 转圈 + 文字 | ✅ 已有 |
| Whisper 识别中 | 进度条 + 段落数 | ✅ 分段识别确定进度条 |
| 静音检测中 | 绿/黄/红状态图标 | 🔶 有文字颜色变化，无独立图标 |

**波形实现细节**：
- Canvas 画布在全局设置和 notebook 之间，录音和实时模式共用
- `SilenceMonitor` / `RealtimeRecognizer` 通过 `level_callback` 回传原始音频数组
- 采样方式：`np.linspace` 均匀抽取 60 个采样点的绝对值
- 活跃时蓝色 `#4a9eff`，静默时灰色 `#d0d0d0`

### 额外改动（不在原始计划内）

- **一键清理文件按钮**：Tab 1「清理文件」按钮（BV 中间文件 / 录音分段），Tab 2 清理实时识别输出文件
- **静音暂停后继续录制**：30s 静音后界面切换为"继续录制"按钮（非托管）或直接进入识别（托管）
- **去掉录音完成弹窗**：段数在 `record_status_label` 显示，不再弹 messagebox
- **识别重复检测**：每段识别完检查重复短语，连续 2 段重复自动中止并警告
- **静音能量阈值调优**：`energy_threshold` 从 0.001 降至 0.0003，适配虚拟音频设备低电平

---

## 后续想法 💡

### 本地文件托管模式（批量自动处理）

厉害袋貂提出：本地文件模式目前灰掉了托管，但后续可以考虑支持批量自动处理——选一个文件夹，自动逐个识别里面的音频/视频文件，全部完成后通知。

---

## 开发进度

### 已完成 ✅
- [x] Feature 1：静音检测双阈值（含能量阈值调优）
- [x] Feature 2：Tab 整合 + 输入源 Toggle
- [x] Feature 3：托管模式（含静音暂停分流逻辑）
- [x] Feature 5：默认模型改 medium
- [x] Feature 6（部分）：波形图 + 确定进度条 + 状态颜色
- [x] 全局模型选择 + 关键词提示
- [x] UI 布局优化（去标题、精简静音设置）
- [x] 一键清理文件按钮
- [x] 静音暂停后继续录制
- [x] 去掉录音完成弹窗
- [x] 识别重复检测
- [x] 帧级进度条（monkey-patch whisper tqdm，分段+单文件全覆盖）

### 搁置 ⏸️
- [ ] Feature 4：.app 封装（macOS Sequoia 安全策略问题，待后续方案）

### 下期待测 🧪
- [ ] 帧级进度条验证（分段识别 + 单文件识别，确认进度条按帧推进）

### 下期待办 📋
- [ ] Feature 6 剩余：B站下载进度条、静音状态图标
- [ ] 自定义 logo
- [ ] UI 美化（待收集灵感，截图/Figma 导出给德彪东）
- [ ] 本地文件批量托管模式
- [ ] .app 封装重新尝试（pyinstaller / Apple Developer 签名）
- [ ] README 重写

---

## 文件变更

| 文件 | 操作 |
|------|------|
| `window_realtime.py` | 大量改动（~980 行，新增波形/清理/帧级进度条/重复检测/暂停继续） |
| `silence_monitor.py` | 新增 `level_callback`，能量阈值 0.001 → 0.0003 |
| `audio_recorder_chunked.py` | 新增 `level_callback`，传递给 SilenceMonitor |
| `realtime_recognition.py` | 新增 `level_callback`，录音循环中回传音频数据 |
| `chunked_file_recognition.py` | 新增 `chunk_callback` + `frame_callback`（重复检测 + 帧级进度） |
| `local_file_recognition.py` | `verbose=True` → `verbose=False`（启用 tqdm 进度） |
