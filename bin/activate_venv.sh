#!/bin/bash
# 激活Python虚拟环境脚本 (Linux/Mac)

echo "正在激活虚拟环境..."
source venv/bin/activate
echo "虚拟环境已激活！"
echo
echo "接下来可以安装依赖："
echo "pip install -r requirements.txt"
echo
echo "或者直接运行分析："
echo "python main_pipeline.py --stock_codes 000001 600519"