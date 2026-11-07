@echo off
chcp 65001 >nul
setlocal
title KTV 账单 - 本地后端
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" goto missing

echo 正在检查本地后端，请稍候...
".venv\Scripts\python.exe" scripts\check_backend.py
if errorlevel 2 goto occupied
if not errorlevel 1 goto running

echo.
echo 正在启动 KTV 账单后端...
echo 健康检查：http://127.0.0.1:8000/api/v1/health
echo 接口文档：http://127.0.0.1:8000/docs
echo 手机请在小程序设置中填写电脑实际局域网地址。
echo 保持本窗口开启；按 Ctrl+C 可停止后端。
echo.
".venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
set "KTV_EXIT_CODE=%errorlevel%"
echo.
if not "%KTV_EXIT_CODE%"=="0" echo 后端启动失败或异常退出，请查看上方错误信息。
if "%KTV_EXIT_CODE%"=="0" echo 后端已停止。
echo 按任意键关闭此窗口。
pause >nul
exit /b %KTV_EXIT_CODE%

:running
echo.
echo KTV 后端已在运行，数据库连接正常，无需重复启动。
echo 健康检查：http://127.0.0.1:8000/api/v1/health
echo 接口文档：http://127.0.0.1:8000/docs
echo 你可以直接进入小程序设置连接地址。
echo 关闭当前提示窗口不会停止已经运行的后端。
echo 按任意键关闭此窗口。
pause >nul
exit /b 0

:occupied
echo.
echo 8000 端口已被占用，但未检测到正常的 KTV 后端。
echo 请检查是否有其他服务或后端仍在启动，不要重复启动多个窗口。
echo 按任意键关闭此窗口。
pause >nul
exit /b 2

:missing
echo.
echo 未找到项目 Python 环境：.venv\Scripts\python.exe
echo 请按 README.md 的环境安装步骤完成安装后重试。
echo 按任意键关闭此窗口。
pause >nul
exit /b 3
