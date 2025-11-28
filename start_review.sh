#!/bin/bash
# ============================================================
# 视频审核系统 - 快速启动脚本
# Video Review System - Quick Start Script
# ============================================================

echo "============================================================"
echo "视频审核系统 - Video Review System"
echo "============================================================"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查配置文件中的 API Key
CONFIG_FILE="./config/config.yaml"
CONFIG_API_KEY=""

if [ -f "$CONFIG_FILE" ]; then
    CONFIG_API_KEY=$(grep -E "^\s*api_key:" "$CONFIG_FILE" | head -1 | sed 's/.*api_key:\s*["'\'']\?\([^"'\'']*\)["'\'']\?.*/\1/' | tr -d ' ')
fi

# 检查 API Key（环境变量或配置文件）
if [ -z "$SILICONFLOW_API_KEY" ] && [ -z "$CONFIG_API_KEY" ]; then
    echo "❌ 未设置 API Key"
    echo ""
    echo "请选择以下任一方式设置："
    echo ""
    echo "📄 方式一：配置文件（推荐）"
    echo "   编辑 config/config.yaml，设置 siliconflow.api_key"
    echo ""
    echo "🔧 方式二：环境变量"
    echo "   export SILICONFLOW_API_KEY='sk-xxxxxxxx'"
    echo ""
    echo "📍 获取 API Key："
    echo "   1. 访问 https://siliconflow.cn"
    echo "   2. 注册并登录"
    echo "   3. 进入控制台 → API 密钥"
    echo ""
    exit 1
fi

if [ -n "$SILICONFLOW_API_KEY" ]; then
    echo "✅ API Key 已设置（环境变量）"
else
    echo "✅ API Key 已设置（配置文件）"
fi
echo ""

# 获取视频目录（支持命令行参数）
VIDEO_DIR="${1:-}"

if [ -z "$VIDEO_DIR" ]; then
    # 从配置文件读取默认目录
    if [ -f "$CONFIG_FILE" ]; then
        VIDEO_DIR=$(grep -E "^\s*video_dir:" "$CONFIG_FILE" | head -1 | sed 's/.*video_dir:\s*["'\'']\?\([^"'\'']*\)["'\'']\?.*/\1/' | tr -d ' ')
    fi
    VIDEO_DIR="${VIDEO_DIR:-./data/to_review}"
fi

echo "📁 视频目录: $VIDEO_DIR"
echo ""

# 检查目录是否存在
if [ ! -d "$VIDEO_DIR" ]; then
    echo "❌ 目录不存在: $VIDEO_DIR"
    echo ""
    echo "使用方法："
    echo "  ./start_review.sh                       # 使用配置文件中的默认目录"
    echo "  ./start_review.sh /media/usb/videos    # 审核 U 盘中的视频"
    echo "  ./start_review.sh ~/Desktop/mv         # 审核桌面目录"
    echo ""
    exit 1
fi

# 检查是否有视频文件
video_count=$(find "$VIDEO_DIR" -maxdepth 1 -type f \( -name "*.mp4" -o -name "*.avi" -o -name "*.mov" -o -name "*.ts" -o -name "*.mkv" -o -name "*.flv" \) 2>/dev/null | wc -l)

if [ "$video_count" -eq 0 ]; then
    echo "⚠️  目录中没有视频文件"
    echo ""
    echo "支持的格式: mp4, avi, mov, ts, mkv, flv"
    echo "请将待审核视频放入 $VIDEO_DIR"
    exit 0
fi

echo "📹 找到 $video_count 个待审核视频"
echo ""

# 检查虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 运行审核脚本
if [ -n "$VIDEO_DIR" ] && [ "$VIDEO_DIR" != "./data/to_review" ]; then
    python siliconflow_review.py "$VIDEO_DIR"
else
    python siliconflow_review.py
fi

echo ""
echo "============================================================"
echo "审核完成！"
echo "============================================================"
echo ""
echo "📊 结果目录："
echo "   ✅ 通过: ./data/approved/"
echo "   ❌ 拒绝: ./data/rejected/"
echo "   ❓ 复核: ./data/manual_review/"
echo ""
echo "📄 详细报告: ./data/results/review_results.json"
echo ""
