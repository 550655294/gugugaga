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

rem ---- 检查 DeepSeek API Key ----
set "ENV_FILE=%SCRIPT_DIR%\.env"

rem 优先级1: 系统环境变量已设置 → 跳过
if defined DEEPSEEK_API_KEY (
    echo   ✅ 检测到系统环境变量 DEEPSEEK_API_KEY，跳过配置
    echo.
    goto :launch
)

rem 优先级2: .env 文件存在且有有效内容 → 跳过
if exist "%ENV_FILE%" (
    echo   ✅ 检测到 .env 配置文件，跳过配置
    echo.
    goto :launch
)

rem 优先级3: 都没有 → 首次引导输入
echo   ============================================
echo     ⚠️  需要配置 DeepSeek API Key
echo   ============================================
echo.
echo   【如何获取 API Key】
echo   1. 打开浏览器访问:
echo      https://platform.deepseek.com/api_keys
echo   2. 注册/登录 DeepSeek 开放平台
echo   3. 点击「创建 API Key」, 复制生成的密钥
echo      （格式类似: sk-xxxxxxxxxxxxxxxx）
echo   4. 粘贴到下方并回车
echo.
echo   💡 费用: 很便宜，几块钱够生成几十集
echo   💡 充值: https://platform.deepseek.com/top_up
echo.
set /p API_KEY_INPUT="   请输入 API Key (sk-...): "
echo DEEPSEEK_API_KEY=%API_KEY_INPUT%> "%ENV_FILE%"
echo.
echo   ✅ 已保存到 .env 文件（下次启动无需再输入）
echo.

:launch

rem ---- 启动 ----
echo   🚀 正在启动服务器...
echo.

rem 先用 start 在后台启动 Python 服务器
start "" "%PYTHON%" generate_scripts.py

rem 等 3 秒让服务器就绪
echo   等待服务器就绪...
timeout /t 3 /nobreak >nul

rem 再打开浏览器
echo   🌐 打开浏览器 http://localhost:8765
start http://localhost:8765

echo   ⏹  关闭此窗口即可停止
echo.

pause
