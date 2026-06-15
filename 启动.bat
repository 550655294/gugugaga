@echo off
chcp 65001 >nul
title 咕咕嘎嘎剧本生成器

rem 定位项目根目录（bat 在哪，根目录就在哪）
cd /d "%~dp0"

echo.
echo   ========================================
echo     咕咕嘎嘎 剧本自动生成器 v4.17
echo   ========================================
echo.

rem 检测 Python
set "PYTHON="

py -3 --version >nul 2>&1
if not errorlevel 1 (set "PYTHON=py -3" & goto :found)

python --version >nul 2>&1
if not errorlevel 1 (set "PYTHON=python" & goto :found)

python3 --version >nul 2>&1
if not errorlevel 1 (set "PYTHON=python3" & goto :found)

:no_python
echo   [错误] 未找到 Python！
echo   请安装 Python 3.9+ → https://python.org
echo.
pause
exit /b 1

:found
echo   Python: %PYTHON%
echo   启动 → http://localhost:8765
echo   按 Ctrl+C 停止
echo.

%PYTHON% -u generate_scripts.py

pause
