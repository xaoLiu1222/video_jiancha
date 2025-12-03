# 视频审核系统

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

基于 Google Gemini 2.0 多模态大模型的智能视频内容审核系统，专为音乐 MV 审核设计。

## 特性

- **原生视频理解** - Gemini 直接分析视频，无需手动提取帧
- **高准确率** - Google 最新多模态模型
- **免费使用** - Gemini API 有免费层
- **自动分类** - 审核后自动移动视频到对应目录

## 审核规则（12种）

| 类型 | 规则 |
|------|------|
| 格式 | 竖屏视频、上下黑边、左右黑边超一半、时长<2分钟 |
| 画质 | 画面模糊、马赛克遮挡 |
| 内容 | 林夕作品、暴露/导向问题、纯风景无人物、风景过长、广告、吸毒画面 |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 获取 API Key

访问 [Google AI Studio](https://aistudio.google.com/apikey) → 创建 API Key

### 3. 配置 API Key

设置环境变量（推荐）：

```bash
# Linux/Mac
export GEMINI_API_KEY='your-api-key'

# Windows
set GEMINI_API_KEY=your-api-key
```

或编辑 `config/config.yaml`：

```yaml
gemini:
  api_key: "your-api-key"
```

### 4. 开始审核

```bash
# 使用默认目录
python gemini_review.py

# 指定视频目录
python gemini_review.py /media/usb/videos

# Windows
python gemini_review.py F:\videos
```

## 审核结果

视频会自动移动到**输入目录下**的子文件夹：

```
<输入目录>/
├── approved/           # 通过
├── rejected/           # 拒绝
├── manual_review/      # 需人工复核
└── review_results.json # 审核报告
```

## 备选方案

如果无法使用 Gemini API，可以使用硅基流动方案：

```bash
# 设置硅基流动 API Key
export SILICONFLOW_API_KEY='sk-xxxxxxxx'

# 运行硅基流动版本
python siliconflow_review.py /path/to/videos
```

## 成本对比

| 方案 | 免费额度 | 每视频成本 | 准确率 |
|------|----------|-----------|--------|
| **Gemini 2.0 Flash** | 有免费层 | ~$0.02 | ⭐⭐⭐⭐⭐ |
| 硅基流动 Qwen2.5-VL | 2000万 tokens | ~¥0.003 | ⭐⭐⭐⭐ |

## 许可证

MIT License
