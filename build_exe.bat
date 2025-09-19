@echo off
chcp 65001 >nul
echo ========================================
echo Python 应用程序构建脚本
echo ========================================

:: 设置项目根目录
set PROJECT_ROOT=%~dp0
cd /d "%PROJECT_ROOT%"

:: 设置虚拟环境路径
set VENV_PATH=%PROJECT_ROOT%.venv
set PYTHON_EXE=%VENV_PATH%\Scripts\python.exe
set PIP_EXE=%VENV_PATH%\Scripts\pip.exe
set PYINSTALLER_EXE=%VENV_PATH%\Scripts\pyinstaller.exe

:: 检查虚拟环境是否存在
if not exist "%VENV_PATH%" (
    echo 错误: 虚拟环境不存在，请先创建虚拟环境
    echo 运行命令: python -m venv .venv
    pause
    exit /b 1
)

:: 检查虚拟环境中的 Python 是否可用
"%PYTHON_EXE%" --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 虚拟环境中的 Python 不可用
    pause
    exit /b 1
)

echo 使用虚拟环境: %VENV_PATH%
echo Python 版本:
"%PYTHON_EXE%" --version

:: 检查 PyInstaller 是否安装
"%PYTHON_EXE%" -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo 正在虚拟环境中安装 PyInstaller...
    "%PIP_EXE%" install pyinstaller
    if errorlevel 1 (
        echo 错误: PyInstaller 安装失败
        pause
        exit /b 1
    )
)

:: 安装项目依赖
echo 正在安装项目依赖...
"%PIP_EXE%" install -r requirements.txt
if errorlevel 1 (
    echo 错误: 依赖安装失败
    pause
    exit /b 1
)

:: 测试导入是否正常
echo 正在测试模块导入...
cd MyExe
"%PYTHON_EXE%" -c "from gui import run; from server import FastAPIServer; from scheduler import SimpleScheduler; from utils.time_utils import current_datetime_str; from utils.config_loader import Config; print('✓ 所有模块导入成功')"
if errorlevel 1 (
    echo 错误: 模块导入测试失败
    cd ..
    pause
    exit /b 1
)
cd ..

:: 清理之前的构建文件
echo 正在清理之前的构建文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "__pycache__" rmdir /s /q "__pycache__"

:: 构建选项菜单
echo.
echo 请选择构建选项:
echo 1. 构建主程序 (main.exe) - 无控制台窗口
echo 2. 构建调试版本 (MyExeApp.exe) - 带控制台窗口
echo 3. 构建两个版本
echo 4. 退出
echo.
set /p choice=请输入选择 (1-4): 

if "%choice%"=="1" goto build_main
if "%choice%"=="2" goto build_debug
if "%choice%"=="3" goto build_both
if "%choice%"=="4" goto end
echo 无效选择，请重新运行脚本
pause
exit /b 1

:build_main
echo.
echo ========================================
echo 正在构建主程序 (main.exe)...
echo ========================================
echo 使用命令: "%PYINSTALLER_EXE%" --clean main.spec
"%PYINSTALLER_EXE%" --clean main.spec
if errorlevel 1 (
    echo 错误: 主程序构建失败
    pause
    exit /b 1
)
echo 主程序构建完成！
goto check_output

:build_debug
echo.
echo ========================================
echo 正在构建调试版本 (MyExeApp.exe)...
echo ========================================
echo 使用命令: "%PYINSTALLER_EXE%" --clean MyExeApp.spec
"%PYINSTALLER_EXE%" --clean MyExeApp.spec
if errorlevel 1 (
    echo 错误: 调试版本构建失败
    pause
    exit /b 1
)
echo 调试版本构建完成！
goto check_output

:build_both
echo.
echo ========================================
echo 正在构建两个版本...
echo ========================================
echo 构建主程序...
"%PYINSTALLER_EXE%" --clean main.spec
if errorlevel 1 (
    echo 错误: 主程序构建失败
    pause
    exit /b 1
)
echo 主程序构建完成！

echo.
echo 构建调试版本...
"%PYINSTALLER_EXE%" --clean MyExeApp.spec
if errorlevel 1 (
    echo 错误: 调试版本构建失败
    pause
    exit /b 1
)
echo 调试版本构建完成！
goto check_output

:check_output
echo.
echo ========================================
echo 构建完成！输出文件位置:
echo ========================================
if exist "dist\main\main.exe" (
    echo 主程序: dist\main\main.exe
)
if exist "dist\MyExeApp\MyExeApp.exe" (
    echo 调试版本: dist\MyExeApp\MyExeApp.exe
)

echo.
echo 文件大小信息:
if exist "dist\main\main.exe" (
    for %%A in ("dist\main\main.exe") do echo 主程序: %%~zA 字节
)
if exist "dist\MyExeApp\MyExeApp.exe" (
    for %%A in ("dist\MyExeApp\MyExeApp.exe") do echo 调试版本: %%~zA 字节
)

echo.
echo 测试运行 (使用虚拟环境):
echo 原始命令: %PYTHON_EXE% %PROJECT_ROOT%MyExe\main.py
echo 是否要测试运行？
set /p test_choice=输入 y 测试运行，其他键跳过: 
if /i "%test_choice%"=="y" (
    echo 使用虚拟环境测试运行...
    cd MyExe
    "%PYTHON_EXE%" main.py
    cd ..
)

echo.
echo 是否要运行构建的程序？
set /p run_choice=输入 y 运行，其他键退出: 
if /i "%run_choice%"=="y" (
    if exist "dist\main\main.exe" (
        echo 启动主程序...
        start "" "dist\main\main.exe"
    ) else if exist "dist\MyExeApp\MyExeApp.exe" (
        echo 启动调试版本...
        start "" "dist\MyExeApp\MyExeApp.exe"
    )
)

:end
echo.
echo 构建脚本执行完毕！
echo 虚拟环境路径: %VENV_PATH%
echo 原始启动命令: %PYTHON_EXE% %PROJECT_ROOT%MyExe\main.py
pause
