@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" goto missing
if not exist "data\ocr-evaluation\images" mkdir "data\ocr-evaluation\images"
echo OCR 测试图片目录：%CD%\data\ocr-evaluation\images
echo 测试不写入营业数据库。首次运行可能需要下载模型，请保持窗口开启。
echo.
".venv\Scripts\python.exe" scripts\benchmark_ocr.py %*
set "KTV_OCR_EXIT=%errorlevel%"
echo.
echo 测试结束。若提示没有图片，请先放入两张原图再运行。
echo 报告在 data\ocr-evaluation\results 的本次运行目录中。
echo 按任意键关闭。
pause >nul
exit /b %KTV_OCR_EXIT%
:missing
echo 未找到 Python 环境，请先按 README 安装依赖。
pause
exit /b 3
