# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

基于硅基流动 Qwen3-VL-72B 多模态大模型的智能视频内容审核系统，专为音乐 MV 审核设计。支持 12 种审核规则，自动分类视频到通过/拒绝/人工复核目录。

## 常用命令

```bash
# 运行审核（默认目录 ./data/to_review）
python siliconflow_review.py

# 指定视频目录
python siliconflow_review.py /path/to/videos

# 指定配置文件
python siliconflow_review.py -c config/custom.yaml

# 使用启动脚本
./start_review.sh                    # Linux/macOS
start_review.bat                     # Windows

# 安装依赖
pip install -r requirements.txt
```

## 架构设计

### 双方案架构

1. **主方案（生产使用）**：`siliconflow_review.py` - 独立的 API 调用脚本，不依赖 src/ 模块
2. **备选方案（未来扩展）**：`src/` 模块 - 本地白名单方案（需要 torch/transformers/faiss）

### 数据流

```
视频输入 → 预检查(时长/格式) → 帧提取 → Base64编码
  → API调用(Qwen3-VL) → JSON解析 → 决策判断 → 自动分类
```

### 核心模块

| 模块 | 职责 |
|------|------|
| `siliconflow_review.py` | 主审核脚本，包含 Config 和 SiliconFlowReviewer 类 |
| `config/config.yaml` | 配置文件（API Key、路径、参数） |
| `src/features/` | CLIP 视频特征提取（可选） |
| `src/pipeline/` | 白名单匹配审核流程（可选） |
| `src/whitelist/` | 特征存储与检索（可选） |

### 输出目录逻辑

审核结果目录跟随输入目录创建：
- `{输入目录}/approved/` - 通过的视频
- `{输入目录}/rejected/` - 拒绝的视频
- `{输入目录}/manual_review/` - 需人工复核
- `{输入目录}/review_results.json` - 审核结果报告

## 配置说明

API Key 优先级：环境变量 `SILICONFLOW_API_KEY` > 配置文件 `config/config.yaml`

关键配置项：
- `video.num_frames`: 采样帧数（影响准确率和 token 消耗）
- `video.min_duration`: 最小时长限制（秒）
- `image.max_size`: 图片最大边长（影响传输速度）
- `model_params.temperature`: 温度参数（越低越稳定）

## 审核规则（12种）

**格式类**：竖屏视频、上下黑边、左右黑边超一半、时长<2分钟

**质量类**：画面模糊、马赛克遮挡

**内容类**：林夕作品、暴露/导向问题、纯风景无人物、风景超一半时长、广告内容、吸毒画面

修改审核规则位置：`siliconflow_review.py` 中 `SiliconFlowReviewer.__init__()` 的 `review_prompt`

## 代码规范

- Python 3.8+，遵循 PEP 8
- 命名：类名 PascalCase，函数/变量 snake_case，常量 UPPER_SNAKE_CASE
- 错误处理：API 调用失败标记为 manual_review，视频读取失败标记为 rejected
