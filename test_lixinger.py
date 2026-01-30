#!/usr/bin/env python3
"""测试理杏仁API集成方案"""

import os
import sys
from lixinger_provider import get_fundamental_provider

def test_lixinger_api():
    """测试理杏仁API功能"""
    print("=== 理杏仁API集成测试 ===")
    
    # 检查是否配置了token
    token = os.getenv("LIXINGER_TOKEN")
    if token:
        print("[OK] 检测到LIXINGER_TOKEN配置")
    else:
        print("[WARN] 未检测到LIXINGER_TOKEN，将使用模拟数据")
    
    # 获取数据提供者
    provider = get_fundamental_provider()
    
    # 测试获取所有数据
    print("\n1. 获取所有股票数据...")
    all_data = provider.get_fundamentals([])
    if not all_data.empty:
        print(f"[SUCCESS] 成功获取 {len(all_data)} 只股票数据")
        print("\n数据示例:")
        print(all_data.head().to_string())
    else:
        print("[ERROR] 数据获取失败")
    
    # 测试获取特定股票数据
    print("\n2. 获取特定股票数据...")
    test_codes = ["000001", "600519", "300750"]
    specific_data = provider.get_fundamentals(test_codes)
    if not specific_data.empty:
        print(f"[SUCCESS] 成功获取 {len(specific_data)} 只指定股票数据")
        print("\n指定股票数据:")
        print(specific_data.to_string(index=False))
    else:
        print("[ERROR] 指定股票数据获取失败")
    
    print("\n=== 测试完成 ===")

def test_screener_integration():
    """测试筛选器集成"""
    print("\n=== 筛选器集成测试 ===")
    
    from screener import run_screener
    
    # 测试筛选条件
    criteria = {"pe_max": 25, "pb_max": 4}
    
    try:
        result = run_screener(criteria, "test_candidates.md")
        
        if not result.empty:
            print(f"[SUCCESS] 筛选成功，得到 {len(result)} 只候选股票")
            print("\n候选股票:")
            print(result.to_string(index=False))
        else:
            print("[ERROR] 筛选未得到候选股票")
            
    except Exception as e:
        print(f"[ERROR] 筛选器测试失败: {e}")

if __name__ == "__main__":
    test_lixinger_api()
    test_screener_integration()