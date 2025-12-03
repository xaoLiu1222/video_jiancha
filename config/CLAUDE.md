[根目录](../CLAUDE.md) > **config**

# 配置模块 - config/

## 变更记录 (Changelog)

### 2025-12-03
- 初始化模块文档

---

## 模块职责

管理系统所有配置参数，包括：
- API 密钥和端点配置
- 视频处理参数
- 目录路径配置
- 模型参数配置
- 审核规则配置

---

## 入口与启动

**配置文件**：
- `config.yaml` - 实际配置文件（包含敏感信息，不提交到 Git）
- `config.example.yaml` - 配置模板（提交到 Git）

**使用方式**：
```python
from siliconflow_review import Config

# 加载默认配置
config = Config()

# 加载指定配置
config = Config("./config/custom.yaml")

# 访问配置
api_key = config.api_key
model = config.model
video_dir = config.video_dir
```

---

## 对外接口

### Config 类

**主要属性**：
```python
# API 配置
config.api_key          # API 密钥（环境变量优先）
config.model            # 模型名称
config.api_base         # API 基础地址
config.timeout          # 超时时间（秒）

# 路径配置
config.video_dir        # 待审核视频目录
config.approved_dir     # 通过视频目录
config.rejected_dir     # 拒绝视频目录
config.manual_review_dir # 人工复核目录
config.results_path     # 结果保存路径

# 视频配置
config.num_frames       # 采样帧数
config.video_formats    # 支持的格式列表
config.min_duration     # 最小时长（秒）

# 图片配置
config.image_max_size   # 图片最大边长
config.image_quality    # JPEG 压缩质量

# 模型参数
config.max_tokens       # 最大输出 token
config.temperature      # 温度参数
```

**主要方法**：
```python
config.get(key, default)  # 获取配置值（支持点号分隔）
```

---

## 关键依赖与配置

### 依赖
- `pyyaml` - YAML 文件解析

### 配置文件结构

```yaml
# ============ API 配置 ============
siliconflow:
  api_key: ""                              # API 密钥（必填）
  model: "Qwen/Qwen3-VL-72B-Instruct"     # 模型名称
  api_base: "https://api.siliconflow.cn/v1"
  timeout: 180                             # 超时时间（秒）

# ============ 目录配置 ============
paths:
  video_dir: "./data/to_review"            # 待审核目录
  approved_dir: "./data/approved"          # 通过目录
  rejected_dir: "./data/rejected"          # 拒绝目录
  manual_review_dir: "./data/manual_review" # 复核目录
  results_path: "./data/results/review_results.json"

# ============ 视频处理配置 ============
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

# ============ 图片压缩配置 ============
image:
  max_size: 512                            # 最大边长（像素）
  quality: 75                              # JPEG 质量（1-100）

# ============ 审核规则配置 ============
review_rules:
  format_check_enabled: true               # 是否启用格式检查
  reject_vertical: true                    # 是否拒绝竖屏
  black_border_threshold: 20               # 黑边检测阈值

# ============ 模型参数配置 ============
model_params:
  max_tokens: 512                          # 最大输出 token
  temperature: 0.3                         # 温度参数（0-1）
```

---

## 数据模型

无持久化数据模型，仅内存中的配置对象。

---

## 测试与质量

### 测试方法

```bash
# 测试配置加载
python -c "
from siliconflow_review import Config
config = Config('./config/config.yaml')
print(f'API Key: {config.api_key[:10]}...')
print(f'Model: {config.model}')
print(f'Video Dir: {config.video_dir}')
"
```

### 配置验证

```python
# 检查必填项
if not config.api_key:
    raise ValueError("未设置 API Key")

# 检查路径存在性
from pathlib import Path
if not Path(config.video_dir).exists():
    print(f"警告：视频目录不存在 {config.video_dir}")
```

---

## 常见问题 (FAQ)

### Q1: 如何设置 API Key？

**方式一：配置文件**（推荐）
```yaml
# config/config.yaml
siliconflow:
  api_key: "sk-xxxxxxxx"
```

**方式二：环境变量**（优先级更高）
```bash
export SILICONFLOW_API_KEY='sk-xxxxxxxx'
```

### Q2: 配置文件找不到怎么办？

```python
# 指定配置文件路径
config = Config("/absolute/path/to/config.yaml")
```

### Q3: 如何添加新的配置项？

1. 在 `config.yaml` 中添加配置
2. 在 `Config` 类中添加 `@property` 方法
3. 使用 `self.get()` 方法获取值

```python
@property
def new_param(self) -> str:
    return self.get("section.new_param", "default_value")
```

### Q4: 环境变量和配置文件哪个优先？

环境变量优先级更高，会覆盖配置文件中的设置。

---

## 相关文件清单

```
config/
├── config.yaml              # 实际配置（不提交）
└── config.example.yaml      # 配置模板（提交）
```

---

**最后更新**: 2025-12-03
