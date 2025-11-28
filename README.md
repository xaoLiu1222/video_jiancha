# 视频审核系统 - Video Review System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

基于硅基流动 Qwen3-VL-72B 多模态大模型的智能视频内容审核系统，专为音乐 MV 内容审核设计。

## ✨ 特性

- 🤖 **AI 智能审核** - 使用 Qwen3-VL-72B 大模型，准确识别视频内容
- 💰 **完全免费** - 硅基流动提供 2000 万 tokens 免费额度
- ⚙️ **灵活配置** - 支持配置文件管理所有参数
- 📂 **自定义目录** - 支持 U 盘、外部硬盘等任意视频路径
- 📊 **自动分类** - 审核后自动将视频移动到对应目录
- 🎯 **规则全面** - 支持 12 种审核规则
- 🌍 **跨平台** - 支持 Linux / macOS / Windows

## 📋 审核规则

| # | 规则 | 说明 |
|---|------|------|
| 1 | 林夕作品 | 识别作词作曲为林夕的作品 |
| 2 | 竖屏视频 | 拒绝竖屏格式 |
| 3 | 上下黑边 | 有上下两条黑边直接拒绝 |
| 4 | 左右黑边 | 左右黑边超过屏幕一半拒绝 |
| 5 | 马赛克遮挡 | 演唱画面有马赛克遮挡 |
| 6 | 画面模糊 | 画质差、失焦、噪点严重 |
| 7 | 暴露/导向 | 内容暴露或导向有问题 |
| 8 | 纯风景 | 只有风景画面无其他内容 |
| 9 | 风景过长 | 风景画面超过视频一半时长 |
| 10 | 广告内容 | 包含品牌 logo、联系方式等 |
| 11 | 吸毒画面 | 包含吸毒相关内容 |
| 12 | 时长限制 | 视频时长少于 2 分钟（本地检测）|

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/video_jiancha.git
cd video_jiancha
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 获取 API Key

1. 访问 [硅基流动](https://siliconflow.cn)
2. 注册并登录
3. 进入控制台 → API 密钥
4. 创建新的 API Key

### 4. 配置 API Key

编辑 `config/config.yaml`：

```yaml
siliconflow:
  api_key: "sk-xxxxxxxx"  # 替换为你的 API Key
```

### 5. 开始审核

```bash
# 使用默认目录（./data/to_review/）
python siliconflow_review.py

# 指定视频目录（如 U 盘）
python siliconflow_review.py /media/usb/videos
```

📖 **详细文档**: 查看 [使用说明.md](./使用说明.md) 获取完整使用指南

## 📁 项目结构

```
video_jiancha/
├── siliconflow_review.py    # 核心审核脚本
├── start_review.sh          # 快速启动脚本
├── requirements.txt         # 依赖清单
├── README.md                # 项目说明
├── config/
│   └── config.yaml          # 配置文件 ⭐
└── data/
    ├── to_review/           # 待审核视频（默认）
    ├── approved/            # ✅ 通过的视频
    ├── rejected/            # ❌ 拒绝的视频
    ├── manual_review/       # ❓ 需人工复核
    └── results/             # 📊 审核报告
```

## ⚙️ 配置文件说明

配置文件位于 `config/config.yaml`，主要配置项：

```yaml
# API 配置
siliconflow:
  api_key: ""                              # API 密钥
  model: "Qwen/Qwen3-VL-72B-Instruct"     # 使用的模型
  timeout: 180                             # API 超时（秒）

# 目录配置
paths:
  video_dir: "./data/to_review"            # 待审核视频目录
  approved_dir: "./data/approved"          # 通过视频目录
  rejected_dir: "./data/rejected"          # 拒绝视频目录

# 视频配置
video:
  num_frames: 6                            # 采样帧数
  min_duration: 120                        # 最小时长（秒）
  formats:                                 # 支持的格式
    - ".mp4"
    - ".avi"
    - ".mov"
    - ".ts"
    - ".mkv"
    - ".flv"
```

## 💡 使用示例

### 命令行使用

```bash
# 基本使用
python siliconflow_review.py

# 指定视频目录
python siliconflow_review.py /path/to/videos

# 指定配置文件
python siliconflow_review.py -c /path/to/config.yaml

# 查看帮助
python siliconflow_review.py --help
```

### 代码调用

```python
from siliconflow_review import Config, SiliconFlowReviewer

# 加载配置
config = Config("./config/config.yaml")

# 初始化审核器
reviewer = SiliconFlowReviewer(config=config, video_dir="/media/usb/videos")

# 审核单个视频
result = reviewer.review_video("/path/to/video.mp4")
print(f"决策: {result['decision']}")
print(f"原因: {result['reason']}")

# 批量审核
video_paths = ["/path/to/video1.mp4", "/path/to/video2.mp4"]
summary = reviewer.review_batch(video_paths)
```

## 📊 审核结果

审核完成后，视频会自动移动到对应目录：

| 结果 | 目录 | 说明 |
|------|------|------|
| ✅ 通过 | `./data/approved/` | 符合所有标准 |
| ❌ 拒绝 | `./data/rejected/` | 违反审核规则 |
| ❓ 复核 | `./data/manual_review/` | 需人工确认 |

详细报告保存在 `./data/results/review_results.json`

## 💰 成本说明

| 项目 | 说明 |
|------|------|
| 免费额度 | 2000 万 tokens |
| 可审核数量 | 约 10,000-20,000 个视频 |
| 超出后成本 | 约 0.001-0.002 元/视频 |

## 🆘 常见问题

**Q: API Key 在哪里获取？**

A: https://siliconflow.cn → 控制台 → API 密钥

**Q: 环境变量和配置文件哪个优先？**

A: 环境变量优先级更高，会覆盖配置文件中的设置

**Q: 支持哪些视频格式？**

A: mp4, avi, mov, ts, mkv, flv（可在配置文件中添加更多）

**Q: 如何审核 U 盘中的视频？**

A: `python siliconflow_review.py /media/username/USB_NAME/videos`

**Q: API 调用超时怎么办？**

A: 在配置文件中增加 `timeout` 值（默认 180 秒）

## 📚 文档

- [使用说明.md](./使用说明.md) - 完整使用指南
- [快速开始.md](./快速开始.md) - 快速入门教程
- [Windows使用指南.md](./Windows使用指南.md) - Windows 系统使用说明

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

- [硅基流动](https://siliconflow.cn) - 提供免费 API 服务
- [Qwen3-VL](https://github.com/QwenLM/Qwen-VL) - 阿里巴巴开源多模态模型

## ⭐ Star History

如果这个项目对你有帮助，请给个 Star ⭐️
