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

rem ---- 检测 Python（绝对路径优先，最可靠） ----
set "PYTHON="

rem 方法1: CodeBuddy 内置 Python（绝对路径）
set "WB_PYTHON=%USERPROFILE%\.workbuddy\binaries\python\versions\3.14.3\python.exe"
if exist "%WB_PYTHON%" (
    set "PYTHON=%WB_PYTHON%"
    goto :found_python
)

rem 方法2: Codex 运行时 Python（绝对路径）
set "CX_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%CX_PYTHON%" (
    set "PYTHON=%CX_PYTHON%"
    goto :found_python
)

rem 方法3: py 启动器
py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=py -3"
    goto :found_python
)

rem 方法4: python（系统 PATH）
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=python"
    goto :found_python
)

rem 方法5: python3（系统 PATH）
python3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=python3"
    goto :found_python
)

goto :no_python

:no_python
echo   [错误] 未找到 Python！
echo   请安装 Python 3.9+ ： https://python.org
echo.
pause
exit /b 1

:found_python
echo   Python: %PYTHON%
echo.
echo   启动服务器...
echo   浏览器就绪后会自动打开
echo   按 Ctrl+C 停止
echo.

%PYTHON% -u "工具脚本\extract_last_frame.py"

pause
