# 视频审核系统

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

基于硅基流动 Qwen2.5-VL-72B 多模态大模型的智能视频内容审核系统，专为音乐 MV 审核设计。

## 特性

- **AI 智能审核** - Qwen2.5-VL-72B 大模型，准确识别视频内容
- **完全免费** - 硅基流动提供 2000 万 tokens 免费额度
- **智能采样** - 基于场景变化的关键帧提取
- **多轮审核** - 低置信度结果自动二次确认
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

访问 [硅基流动](https://siliconflow.cn) → 控制台 → API 密钥 → 创建

### 3. 配置 API Key

编辑 `config/config.yaml`：

```yaml
siliconflow:
  api_key: "sk-xxxxxxxx"
```

或设置环境变量：

```bash
export SILICONFLOW_API_KEY='sk-xxxxxxxx'
```

### 4. 开始审核

```bash
# 使用默认目录
python siliconflow_review.py

# 指定视频目录（如 U 盘）
python siliconflow_review.py /media/usb/videos

# Windows
python siliconflow_review.py F:\videos
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

## 配置说明

主要配置项（`config/config.yaml`）：

```yaml
video:
  num_frames: 12              # 采样帧数
  smart_extraction: true      # 智能关键帧提取

image:
  max_size: 768               # 图片分辨率

review:
  enable_double_check: true   # 启用二次审核
  confidence_threshold: 0.8   # 置信度阈值
```

## 成本

| 项目 | 说明 |
|------|------|
| 免费额度 | 2000 万 tokens |
| 可审核数量 | 约 5,000-10,000 个视频 |
| 超出后成本 | 约 0.002-0.004 元/视频 |

## 许可证

MIT License
