#!/usr/bin/env python3
"""
测试逐次提问分析功能的脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analyst import _generate_analysis_sequentially

def test_sequential_analysis():
    """测试逐次提问分析功能"""
    
    # 模拟股票数据
    test_stock_code = "600519"
    test_stock_name = "贵州茅台"
    
    # 模拟基本面数据
    test_fundamentals = {
        "PE(TTM)估算": 28.0,
        "PB": 6.5,
        "股息率": 1.2,
        "总市值(亿)": 20000.0,
        "ROE(TTM)": 25.0
    }
    
    print("=== 测试逐次提问分析功能 ===")
    print(f"股票: {test_stock_name}({test_stock_code})")
    print(f"基本面数据: {test_fundamentals}")
    print()
    
    # 测试逐次提问分析
    try:
        result = _generate_analysis_sequentially(test_stock_code, test_stock_name, test_fundamentals)
        
        if result:
            print("✅ 逐次提问分析成功！")
            print(f"结果长度: {len(result)} 字符")
            print("\n=== 分析结果预览 ===")
            print(result[:500] + "..." if len(result) > 500 else result)
        else:
            print("❌ 逐次提问分析失败")
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sequential_analysis()