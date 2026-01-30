#!/bin/bash
# AI股票分析系统启动脚本 (Linux/Mac)

echo "============================================"
echo "    AI股票深度分析系统"
echo "============================================"
echo

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "正在创建虚拟环境..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "错误：创建虚拟环境失败"
        exit 1
    fi
    echo "虚拟环境创建成功！"
    echo
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 检查是否已安装依赖
python3 -c "import pandas, akshare, openai, yaml" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "正在安装依赖包..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "错误：依赖安装失败"
        exit 1
    fi
    echo "依赖安装完成！"
    echo
fi

# 检查环境变量配置
if [ ! -f ".env" ]; then
    echo "警告：未找到.env配置文件"
    echo "请复制.env.example为.env并配置API密钥"
    echo
fi

# 运行分析系统
echo "启动AI股票分析系统..."
echo
python3 main_pipeline.py "$@"