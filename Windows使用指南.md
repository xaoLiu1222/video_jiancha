# Windows 使用指南

## 快速开始

### 1. 安装 Python
- 下载 Python 3.8+ : https://www.python.org/downloads/
- 安装时勾选 "Add Python to PATH"

### 2. 安装依赖
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 设置 API Key
```cmd
set SILICONFLOW_API_KEY=sk-xxxxxxxx
```

**永久设置（推荐）：**
- 右键"此电脑" → 属性 → 高级系统设置 → 环境变量
- 新建用户变量：`SILICONFLOW_API_KEY` = `sk-xxxxxxxx`

### 4. 运行审核

**默认目录：**
```cmd
start_review.bat
```

**自定义目录（U盘）：**
```cmd
start_review.bat D:\视频
start_review.bat E:\
start_review.bat "C:\Users\用户名\Videos"
```

**直接运行 Python：**
```cmd
python siliconflow_review.py D:\视频
```

## 注意事项

- 路径包含空格时需要加引号
- 支持格式：mp4, avi, mov, ts, mkv, flv
- 审核后视频自动分类到 `data\approved`、`data\rejected`、`data\manual_review`
