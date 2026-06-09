@echo off
chcp 65001 >nul
title 咕咕嘎嘎剧本生成器
cd /d "E:\咕咕嘎嘎"

echo 🐧 正在启动剧本生成器...
echo.

rem 检查 Python
C:\Users\MSI-NB\.workbuddy\binaries\python\envs\default\Scripts\python.exe --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Python 未找到
    pause
    exit /b 1
)

rem 检查 API Key
C:\Users\MSI-NB\.workbuddy\binaries\python\envs\default\Scripts\python.exe -c "import os; k=os.environ.get('DEEPSEEK_API_KEY',''); exit(0 if k else 1)" >nul 2>&1
if errorlevel 1 (
    echo [错误] 未设置 DEEPSEEK_API_KEY 环境变量
    echo 请设置后重试
    pause
    exit /b 1
)

echo 🚀 启动服务器...
echo 🌐 浏览器将自动打开 http://localhost:8765
echo ⏱ 按窗口的 X 或 Ctrl+C 可停止
echo.

start http://localhost:8765

C:\Users\MSI-NB\.workbuddy\binaries\python\envs\default\Scripts\python.exe "E:\咕咕嘎嘎\generate_scripts.py"

pause
