@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   高校学科竞赛管理系统  启动中...
echo ============================================
echo.

python --version >nul 2>nul
if errorlevel 1 (
    echo [错误] 没找到 python 命令。
    echo 请确认装 Python 时勾选了 "Add Python to PATH"。
    echo.
    pause
    exit /b 1
)

python -c "import flask" >nul 2>nul
if errorlevel 1 (
    echo 第一次运行，正在安装 Flask，请稍等...
    python -m pip install flask -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo.
        echo [错误] Flask 安装失败，检查一下网络。
        pause
        exit /b 1
    )
)

echo.
echo 启动成功后，在浏览器打开： http://127.0.0.1:5000
echo 停止运行：在这个窗口按 Ctrl + C，或者直接关掉窗口
echo.
python app.py

echo.
echo 服务已停止。
pause
