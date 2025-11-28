@echo off
chcp 65001 >nul
REM 硅基流动视频审核 - Windows 启动脚本

echo ============================================================
echo 视频审核系统 - 硅基流动方案
echo ============================================================

REM 检查 API Key
if "%SILICONFLOW_API_KEY%"=="" (
    echo.
    echo ❌ 未设置 API Key
    echo.
    echo 请按以下步骤操作：
    echo.
    echo 1️⃣  访问 https://siliconflow.cn
    echo 2️⃣  注册并登录
    echo 3️⃣  进入控制台 → API 密钥
    echo 4️⃣  创建新的 API Key
    echo.
    echo 5️⃣  设置环境变量：
    echo     set SILICONFLOW_API_KEY=sk-xxxxxxxx
    echo.
    echo 6️⃣  重新运行此脚本
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ API Key 已设置
echo.

REM 获取视频目录（支持命令行参数）
if "%~1"=="" (
    set "VIDEO_DIR=.\data\to_review"
) else (
    set "VIDEO_DIR=%~1"
)

echo 📁 视频目录: %VIDEO_DIR%
echo.

REM 检查目录是否存在
if not exist "%VIDEO_DIR%" (
    echo ❌ 目录不存在: %VIDEO_DIR%
    echo.
    echo 使用方法：
    echo   start_review.bat                    # 使用默认目录
    echo   start_review.bat D:\视频            # 使用自定义目录
    echo   start_review.bat E:\                # 使用 U 盘
    echo.
    pause
    exit /b 1
)

REM 检查是否有视频文件
set video_count=0
for %%f in ("%VIDEO_DIR%\*.mp4" "%VIDEO_DIR%\*.avi" "%VIDEO_DIR%\*.mov" "%VIDEO_DIR%\*.ts" "%VIDEO_DIR%\*.mkv" "%VIDEO_DIR%\*.flv") do (
    if exist "%%f" set /a video_count+=1
)

if %video_count%==0 (
    echo ⚠️  目录中没有视频文件: %VIDEO_DIR%
    echo.
    echo 请将待审核的视频放入此目录
    pause
    exit /b 0
)

echo 📹 找到 %video_count% 个待审核视频
echo.

REM 激活虚拟环境并运行
call venv\Scripts\activate.bat
python siliconflow_review.py "%VIDEO_DIR%"

echo.
echo ============================================================
echo 审核完成！
echo ============================================================
echo.
echo 📄 结果已保存到: .\data\results\siliconflow_review.json
echo.
pause
