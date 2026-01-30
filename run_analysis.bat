@echo off
rem AI股票分析系统启动脚本 (Windows)

echo ============================================
echo    AI股票深度分析系统
echo ============================================
echo.

rem 检查虚拟环境是否存在
if not exist "venv\Scripts\activate.bat" (
    echo 正在创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo 错误：创建虚拟环境失败
        pause
        exit /b 1
    )
    echo 虚拟环境创建成功！
    echo.
)

rem 激活虚拟环境
echo 激活虚拟环境...
call venv\Scripts\activate.bat

rem 检查是否已安装依赖
python -c "import pandas, akshare, openai, yaml" 2>nul
if errorlevel 1 (
    echo 正在安装依赖包...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo 错误：依赖安装失败
        pause
        exit /b 1
    )
    echo 依赖安装完成！
    echo.
)

rem 检查环境变量配置
if not exist ".env" (
    echo 警告：未找到.env配置文件
    echo 请复制.env.example为.env并配置API密钥
    echo.
)

rem 运行分析系统
echo 启动AI股票分析系统...
echo.
python main_pipeline.py %*

rem 保持窗口打开
pause