@echo off
chcp 65001 >nul
title 咕咕嘎嘎剧本生成器

rem ---- 自动定位项目根目录（bat 在 工具脚本/ 下，根目录是上级） ----
set "TOOL_DIR=%~dp0"
cd /d "%TOOL_DIR%\.."

echo.
echo   ========================================
echo     咕咕嘎嘎 剧本自动生成器
echo   ========================================
echo.

rem ---- 检测 Python（实测运行，不用 where）----
set "PYTHON="

rem 方法1: py 启动器（Windows Python Launcher，最可靠）
py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=py -3"
    goto :found_python
)

rem 方法2: python 命令
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=python"
    goto :found_python
)

rem 方法3: python3 命令
python3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=python3"
    goto :found_python
)

rem 方法4: CodeBuddy 内置 Python（绝对路径）
set "CB_PYTHON=%USERPROFILE%\.workbuddy\binaries\python\versions\3.14.3\python.exe"
if exist "%CB_PYTHON%" (
    set "PYTHON=%CB_PYTHON%"
    goto :found_python
)

rem 都没找到
goto :no_python

:no_python
echo   [错误] 未找到 Python！
echo.
echo   请安装 Python 3.9+ ： https://python.org
echo   安装时务必勾选 "Add Python to PATH"
echo.
pause
exit /b 1

:found_python
echo   Python 已找到: %PYTHON%
echo.

rem ---- 检查 DeepSeek API Key ----
set "ENV_FILE=%SCRIPT_DIR%\.env"

rem 优先级1: 系统环境变量已设置
if defined DEEPSEEK_API_KEY (
    echo   检测到系统环境变量 DEEPSEEK_API_KEY，跳过配置
    echo.
    goto :launch
)

rem 优先级2: .env 文件存在
if exist "%ENV_FILE%" (
    echo   检测到 .env 配置文件，跳过配置
    echo.
    goto :launch
)

rem 优先级3: 首次引导输入
echo   ============================================
echo     需要配置 DeepSeek API Key
echo   ============================================
echo.
echo   1. 打开 https://platform.deepseek.com/api_keys
echo   2. 注册/登录后点击「创建 API Key」
echo   3. 复制密钥粘贴到下方并回车
echo.
set /p API_KEY_INPUT="   请输入 API Key (sk-...): "
echo DEEPSEEK_API_KEY=%API_KEY_INPUT%> "%ENV_FILE%"
echo.
echo   已保存到 .env 文件（下次启动无需再输入）
echo.

:launch

rem 安全检查
if "%PYTHON%"=="" (
    echo   [内部错误] PYTHON 变量为空，无法启动
    pause
    exit /b 1
)

echo   启动服务器...
echo   服务器就绪后会自动打开浏览器
echo   按 Ctrl+C 停止
echo.

%PYTHON% -u "工具脚本\generate_scripts.py"

pause
