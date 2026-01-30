#!/usr/bin/env python3
"""
测试理杏仁估值数据API接口
"""

import os
import sys
sys.path.append(os.path.dirname(__file__))

from lixinger_provider import LixingerProvider
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_valuation_api():
    """测试理杏仁估值数据API"""
    print("=== 理杏仁估值数据API测试 ===")
    
    # 获取token
    token = os.getenv("LIXINGER_TOKEN")
    if not token:
        print("[ERROR] 未找到LIXINGER_TOKEN环境变量")
        print("请检查.env文件是否包含: LIXINGER_TOKEN=your_token_here")
        return False
    
    print(f"[INFO] 找到token: {token[:8]}...")
    
    # 创建提供者实例
    provider = LixingerProvider(token)
    
    # 测试股票代码
    test_codes = ["300750", "600519", "600157"]
    print(f"[INFO] 测试股票代码: {test_codes}")
    
    # 获取估值数据
    print("[INFO] 调用估值数据API...")
    try:
        result = provider.get_fundamentals(test_codes)
        
        if result is not None and not result.empty:
            print("[SUCCESS] API调用成功!")
            print(f"获取到 {len(result)} 只股票的估值数据:")
            print("=" * 80)
            print(result.to_string(index=False))
            print("=" * 80)
            
            # 显示数据列信息
            print("\n数据列详情:")
            print(f"列名: {list(result.columns)}")
            print(f"数据类型:\n{result.dtypes}")
            
            return True
        else:
            print("[ERROR] API调用成功但返回空数据")
            return False
            
    except Exception as e:
        print(f"[ERROR] API调用异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dummy_provider():
    """测试模拟数据提供者"""
    print("\n=== 模拟数据提供者测试 ===")
    
    from lixinger_provider import DummyDataProvider
    
    provider = DummyDataProvider()
    test_codes = ["000001", "600519", "300750"]
    
    result = provider.get_fundamentals(test_codes)
    
    if result is not None and not result.empty:
        print("[SUCCESS] 模拟数据获取成功!")
        print(f"获取到 {len(result)} 只股票的模拟数据:")
        print("=" * 80)
        print(result.to_string(index=False))
        print("=" * 80)
        return True
    else:
        print("[ERROR] 模拟数据获取失败")
        return False

if __name__ == "__main__":
    print("理杏仁估值数据API集成测试")
    print("-" * 50)
    
    # 测试真实API
    api_success = test_valuation_api()
    
    # 测试模拟数据（备用方案）
    dummy_success = test_dummy_provider()
    
    print("\n" + "=" * 50)
    if api_success:
        print("[SUCCESS] 理杏仁估值数据API集成测试通过")
    else:
        print("[FAILED] 理杏仁估值数据API测试失败，但备用方案可用")
        
    if dummy_success:
        print("[SUCCESS] 模拟数据提供者测试通过")
    
    print("=" * 50)