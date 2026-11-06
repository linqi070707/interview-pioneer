@echo off
chcp 65001 >nul
title 面试先锋 - 自动部署与启动
echo ===================================================
echo               面试先锋 (Interview Pioneer)
echo ===================================================
echo.

:: 1. 检查 deepseek.txt 配置文件是否存在
if not exist "deepseek.txt" (
    echo [警告] 未检测到 deepseek.txt 文件！应用可能无法连接大模型。
    echo 请在此文件夹下新建一个 deepseek.txt，第一行填入你的 API Key：
    echo sk-xxxxxxxxxxxxxxxxxxxx
    echo.
    pause
)

:: 2. 检查是否安装 Python (检测 python 或 py 命令)
python --version >nul 2>&1
if %errorlevel% equ 0 goto HasPython
py --version >nul 2>&1
if %errorlevel% equ 0 goto HasPython

echo [环境检测] 未检测到 Python，正在从清华镜像自动下载安装...
set "PYTHON_URL=https://mirrors.tuna.tsinghua.edu.cn/python/3.12.6/python-3.12.6-amd64.exe"
set "PYTHON_INSTALLER=%TEMP%\python-3.12.6-amd64.exe"

powershell -Command "Write-Host '正在下载 Python 安装包...'; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%'"

if not exist "%PYTHON_INSTALLER%" (
    echo [错误] Python 下载失败，请检查网络连接或手动安装 Python。
    pause
    exit /b 1
)

echo [环境安装] 正在静默安装 Python，请稍候...
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
echo [环境安装] 安装完成。

:HasPython
echo.
echo [1/3] 正在检查本地虚拟环境...

:: 测试现有的 .venv 是否可用，如果不可用就删掉
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [警告] 检测到无效的旧虚拟环境（可能来自其他电脑），正在清理...
        rmdir /s /q ".venv"
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo 正在创建全新的虚拟环境...
    python -m venv .venv
    if %errorlevel% neq 0 (
        py -m venv .venv
    )
)

echo.
echo [2/3] 正在通过清华源安装所需依赖...
echo 首次运行可能需要几分钟（尤其是 OCR 组件），请耐心等待...
.venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo [3/3] 环境准备完毕，正在启动应用...
echo 浏览器将自动打开，请勿关闭此黑窗口！
echo.
.venv\Scripts\python.exe -m streamlit run app.py

pause