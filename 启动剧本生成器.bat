@echo off
chcp 65001 >nul
title 咕咕嘎嘎剧本生成器

rem ---- 自动定位脚本所在目录 ----
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo.
echo   ========================================
echo     🐧 咕咕嘎嘎 剧本自动生成器
echo   ========================================
echo.

rem ---- 检查 Python ----
call :check_cmd python  || call :check_cmd python3 || goto :no_python
goto :found_python

:check_cmd
where %1 >nul 2>&1
if %errorlevel%==0 ( set "PYTHON=%1" && exit /b 0 )
exit /b 1

:no_python
echo   [错误] 未找到 Python！
echo   请安装 Python 3.9+ https://python.org
echo   安装时请勾选 "Add Python to PATH"
echo.
pause
exit /b 1

:found_python
echo   ✅ Python 已找到: %PYTHON%
echo.

rem ---- 创建 .env 文件（如果不存在） ----
set "ENV_FILE=%SCRIPT_DIR%\.env"
if not exist "%ENV_FILE%" (
    echo   ⚠️  首次运行，请配置 DeepSeek API Key
    echo.
    set /p API_KEY_INPUT="  请输入 DeepSeek API Key (sk-...): "
    echo DEEPSEEK_API_KEY=!API_KEY_INPUT!> "%ENV_FILE%"
    echo   ✅ 已保存到 .env 文件
    echo.
)

rem ---- 启动 ----
echo   🚀 启动服务器...
echo   🌐 浏览器将自动打开 http://localhost:8765
echo   ⏹  关闭此窗口即可停止
echo.
start http://localhost:8765
"%PYTHON%" "generate_scripts.py"

pause
