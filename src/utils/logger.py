"""
日志工具模块
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "video_review",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    配置日志记录器

    Args:
        name: 日志器名称
        level: 日志级别
        log_file: 日志文件路径（可选）
        format_string: 日志格式

    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 清除已有的处理器
    logger.handlers.clear()

    # 默认格式
    if format_string is None:
        format_string = "[%(asctime)s] [%(levelname)s] %(message)s"

    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器（可选）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
