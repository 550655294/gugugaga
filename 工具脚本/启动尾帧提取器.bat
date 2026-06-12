@echo off
chcp 65001 >nul
title 视频尾帧提取器

rem ---- 自动定位项目根目录 ----
set "TOOL_DIR=%~dp0"
cd /d "%TOOL_DIR%\.."

echo.
echo   ========================================
echo     视频尾帧提取器
echo   ========================================
echo.

rem ---- 检测 Python ----
set "PYTHON="

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=py -3"
    goto :found_python
)

python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=python"
    goto :found_python
)

python3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=python3"
    goto :found_python
)

set "CB_PYTHON=%USERPROFILE%\.workbuddy\binaries\python\versions\3.14.3\python.exe"
if exist "%CB_PYTHON%" (
    set "PYTHON=%CB_PYTHON%"
    goto :found_python
)

echo   [错误] 未找到 Python！
echo   请安装 Python 3.9+ ： https://python.org
echo.
pause
exit /b 1

:found_python
echo   Python 已找到: %PYTHON%
echo.

echo   启动服务器（端口 8766）...
echo   服务器就绪后会自动打开浏览器
echo   按 Ctrl+C 停止
echo.

%PYTHON% -u "工具脚本\extract_last_frame.py"

pause
