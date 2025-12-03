[根目录](../../CLAUDE.md) > [src](../) > **utils**

# 工具模块 - src/utils/

## 变更记录 (Changelog)

### 2025-12-03
- 初始化模块文档

---

## 模块职责

提供通用工具函数，包括日志记录、文件操作等辅助功能。

**核心功能**：
- 日志记录配置
- 控制台和文件日志输出
- 日志格式化

---

## 入口与启动

**主入口**：`logger.py`

**使用示例**：
```python
from src.utils.logger import setup_logger

# 基础使用（仅控制台输出）
logger = setup_logger("video_review")
logger.info("开始处理视频")
logger.warning("视频质量较低")
logger.error("处理失败")

# 同时输出到文件
logger = setup_logger(
    name="video_review",
    level=logging.INFO,
    log_file="./logs/review.log"
)

# 自定义格式
logger = setup_logger(
    name="video_review",
    format_string="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
)
```

---

## 对外接口

### setup_logger 函数

**函数签名**：
```python
def setup_logger(
    name: str = "video_review",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger
```

**参数说明**：
- `name` - 日志器名称（默认 "video_review"）
- `level` - 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- `log_file` - 日志文件路径（可选，None 则仅输出到控制台）
- `format_string` - 日志格式字符串（可选）

**返回值**：
- 配置好的 `logging.Logger` 对象

**默认格式**：
```
[2025-12-03 10:30:00] [INFO] 日志消息内容
```

---

## 关键依赖与配置

### 依赖
- `logging` - Python 标准库

### 日志级别

| 级别 | 数值 | 用途 |
|------|------|------|
| DEBUG | 10 | 详细调试信息 |
| INFO | 20 | 一般信息（默认） |
| WARNING | 30 | 警告信息 |
| ERROR | 40 | 错误信息 |
| CRITICAL | 50 | 严重错误 |

### 日志格式占位符

| 占位符 | 说明 |
|--------|------|
| `%(asctime)s` | 时间戳 |
| `%(name)s` | 日志器名称 |
| `%(levelname)s` | 日志级别 |
| `%(message)s` | 日志消息 |
| `%(filename)s` | 文件名 |
| `%(lineno)d` | 行号 |
| `%(funcName)s` | 函数名 |

---

## 数据模型

无持久化数据模型。

---

## 测试与质量

### 测试示例

```python
import logging
from src.utils.logger import setup_logger

def test_logger():
    # 测试基础日志
    logger = setup_logger("test_logger")
    logger.info("测试信息")
    logger.warning("测试警告")
    logger.error("测试错误")

    # 测试文件日志
    logger = setup_logger(
        name="test_file_logger",
        log_file="./test.log"
    )
    logger.info("写入文件")

    # 验证文件存在
    import os
    assert os.path.exists("./test.log")

    # 清理
    os.remove("./test.log")
```

---

## 常见问题 (FAQ)

### Q1: 如何设置不同的日志级别？

```python
import logging

# DEBUG 级别（显示所有日志）
logger = setup_logger(level=logging.DEBUG)

# WARNING 级别（仅显示警告和错误）
logger = setup_logger(level=logging.WARNING)
```

### Q2: 如何同时输出到多个文件？

```python
import logging

# 方案 1：创建多个 logger
logger1 = setup_logger("logger1", log_file="./log1.log")
logger2 = setup_logger("logger2", log_file="./log2.log")

# 方案 2：手动添加处理器
logger = setup_logger("main")
file_handler = logging.FileHandler("./additional.log")
logger.addHandler(file_handler)
```

### Q3: 如何自定义日志格式？

```python
# 详细格式（包含文件名和行号）
logger = setup_logger(
    format_string="[%(asctime)s] [%(filename)s:%(lineno)d] [%(levelname)s] %(message)s"
)

# 简洁格式
logger = setup_logger(
    format_string="%(levelname)s: %(message)s"
)
```

### Q4: 如何禁用日志输出？

```python
import logging

# 设置为 CRITICAL 以上级别（实际上禁用所有日志）
logger = setup_logger(level=logging.CRITICAL + 1)

# 或者移除所有处理器
logger = setup_logger()
logger.handlers.clear()
```

### Q5: 日志文件太大怎么办？

```python
import logging
from logging.handlers import RotatingFileHandler

# 使用轮转文件处理器
logger = logging.getLogger("video_review")
handler = RotatingFileHandler(
    "./logs/review.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5            # 保留 5 个备份
)
logger.addHandler(handler)
```

### Q6: 如何在多模块中使用同一个 logger？

```python
# 模块 A
from src.utils.logger import setup_logger
logger = setup_logger("video_review")
logger.info("模块 A 日志")

# 模块 B
import logging
logger = logging.getLogger("video_review")  # 获取已存在的 logger
logger.info("模块 B 日志")
```

---

## 相关文件清单

```
src/utils/
├── __init__.py              # 模块初始化
└── logger.py                # 日志工具（主文件）
```

---

## 扩展建议

### 1. 添加彩色日志输出

```python
# 安装 colorlog
pip install colorlog

# 使用彩色日志
import colorlog

def setup_colored_logger(name):
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s[%(levelname)s]%(reset)s %(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    ))
    logger = colorlog.getLogger(name)
    logger.addHandler(handler)
    return logger
```

### 2. 添加结构化日志

```python
import json
import logging

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName
        }
        return json.dumps(log_data)

# 使用
handler = logging.FileHandler("./logs/structured.log")
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
```

### 3. 添加远程日志

```python
from logging.handlers import HTTPHandler

# 发送日志到远程服务器
handler = HTTPHandler(
    "logging.example.com:8080",
    "/log",
    method="POST"
)
logger.addHandler(handler)
```

---

**最后更新**: 2025-12-03
