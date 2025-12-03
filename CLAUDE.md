# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

基于 Google Gemini 2.0 多模态大模型的智能视频内容审核系统，专为音乐 MV 审核设计。支持 12 种审核规则，自动分类视频到通过/拒绝/人工复核目录。

## 常用命令

```bash
# Gemini 方案（推荐，准确率更高）
python gemini_review.py                    # 使用默认目录
python gemini_review.py /path/to/videos    # 指定视频目录
python gemini_review.py F:\videos          # Windows

# 硅基流动方案（备选）
python siliconflow_review.py /path/to/videos

# 安装依赖
pip install -r requirements.txt
```

## 架构设计

### 双方案架构

| 方案 | 脚本 | 特点 |
|------|------|------|
| **Gemini（推荐）** | `gemini_review.py` | 原生视频理解，准确率高 |
| 硅基流动（备选） | `siliconflow_review.py` | 需提取帧，国内访问快 |

### 数据流

**Gemini 方案：**
```
视频输入 → 预检查(时长) → 上传到Gemini → 原生视频分析 → JSON解析 → 自动分类
```

**硅基流动方案：**
```
视频输入 → 预检查(时长) → 智能帧提取 → Base64编码 → API调用 → JSON解析 → 自动分类
```

### 核心文件

| 文件 | 职责 |
|------|------|
| `gemini_review.py` | Gemini 审核脚本（推荐） |
| `siliconflow_review.py` | 硅基流动审核脚本（备选） |
| `config/config.yaml` | 配置文件（API Key、参数） |

### 输出目录逻辑

审核结果目录跟随输入目录创建：
- `{输入目录}/approved/` - 通过的视频
- `{输入目录}/rejected/` - 拒绝的视频
- `{输入目录}/manual_review/` - 需人工复核
- `{输入目录}/review_results.json` - 审核结果报告

## 配置说明

### Gemini API（推荐）
- 环境变量：`GEMINI_API_KEY` 或 `GOOGLE_API_KEY`
- 配置文件：`gemini.api_key`
- 获取地址：https://aistudio.google.com/apikey

### 硅基流动 API（备选）
- 环境变量：`SILICONFLOW_API_KEY`
- 配置文件：`siliconflow.api_key`
- 获取地址：https://siliconflow.cn

## 审核规则（12种）

**格式类**：竖屏视频、上下黑边、左右黑边超一半、时长<2分钟

**质量类**：画面模糊、马赛克遮挡

**内容类**：林夕作品、暴露/导向问题、纯风景无人物、风景超一半时长、广告内容、吸毒画面

修改审核规则：
- Gemini：`gemini_review.py` 中 `GeminiReviewer.__init__()` 的 `review_prompt`
- 硅基流动：`siliconflow_review.py` 中 `SiliconFlowReviewer.__init__()` 的 `review_prompt`

## 代码规范

- Python 3.8+，遵循 PEP 8
- 命名：类名 PascalCase，函数/变量 snake_case
- 错误处理：API 调用失败标记为 manual_review
