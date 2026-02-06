#!/usr/bin/env python3
"""
测试缓存文件创建问题修复效果
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from stock_analyzer.core.technical_analyzer import TechnicalAnalyzer
import json
import pandas as pd

def test_cache_environment():
    """测试缓存环境检查功能"""
    print("=== 测试缓存环境检查功能 ===")
    
    analyzer = TechnicalAnalyzer()
    cache_file = analyzer._get_kline_cache_file("test_cache_env")
    
    # 测试环境检查
    result = analyzer._ensure_cache_environment(cache_file)
    print(f"缓存环境检查结果: {'正常' if result else '异常'}")
    
    # 检查目录是否创建
    cache_dir = cache_file.parent
    print(f"缓存目录存在: {cache_dir.exists()}")
    print(f"缓存目录可写: {os.access(cache_dir, os.W_OK)}")
    
    return result

def test_cache_save_enhanced():
    """测试增强版缓存保存功能"""
    print("\n=== 测试增强版缓存保存功能 ===")
    
    analyzer = TechnicalAnalyzer()
    cache_file = analyzer._get_kline_cache_file("test_stock")
    
    # 清理旧缓存
    if cache_file.exists():
        cache_file.unlink()
        print("清理旧缓存文件")
    
    # 创建测试数据（包含各种数据类型）
    test_data = [
        {
            'date': pd.Timestamp("2025-01-01"),
            'open': 10.5,
            'high': 11.2,
            'low': 10.1,
            'close': 10.8,
            'volume': 1000000,
            'amount': 10800000.0,
            'change': 0.03,
            'stockCode': 'test_stock',
            'to_r': 0.05,
            'nested_data': {'key': 'value'},  # 测试嵌套数据
            'list_data': [1, 2, 3]  # 测试列表数据
        },
        {
            'date': pd.Timestamp("2025-01-08"),
            'open': 10.8,
            'high': 11.5,
            'low': 10.6,
            'close': 11.2,
            'volume': 1200000,
            'amount': 13440000.0,
            'change': 0.037,
            'stockCode': 'test_stock',
            'to_r': 0.06
        }
    ]
    
    # 测试缓存保存
    try:
        analyzer._save_kline_to_cache(cache_file, test_data)
        print("[SUCCESS] 缓存保存测试完成")
        
        # 验证缓存文件
        if cache_file.exists():
            print(f"[SUCCESS] 缓存文件已创建: {cache_file}")
            
            # 读取并验证缓存内容
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_content = json.load(f)
            
            print(f"缓存数据条数: {len(cached_content['data'])}")
            print(f"缓存时间: {cached_content.get('timestamp')}")
            print(f"元数据: {cached_content.get('metadata', {})}")
            
            # 验证数据完整性
            first_record = cached_content['data'][0]
            print(f"数据类型处理验证:")
            print(f"  - 日期字段: {first_record.get('date')}")
            print(f"  - 数值字段: {first_record.get('open')}")
            print(f"  - 嵌套字段: {first_record.get('nested_data')}")
            
        else:
            print("[ERROR] 缓存文件未创建")
            
    except Exception as e:
        print(f"[ERROR] 缓存保存失败: {e}")

def test_cache_load_enhanced():
    """测试缓存加载功能"""
    print("\n=== 测试缓存加载功能 ===")
    
    analyzer = TechnicalAnalyzer()
    cache_file = analyzer._get_kline_cache_file("test_stock")
    
    if cache_file.exists():
        try:
            cached_data = analyzer._load_kline_from_cache(cache_file)
            if cached_data is not None:
                print("[SUCCESS] 缓存加载成功")
                print(f"数据形状: {cached_data.shape}")
                print(f"列名: {cached_data.columns.tolist()}")
                print("前3行数据:")
                print(cached_data.head(3))
            else:
                print("[ERROR] 缓存加载失败")
        except Exception as e:
            print(f"[ERROR] 缓存加载异常: {e}")
    else:
        print("[ERROR] 缓存文件不存在")

def test_atomic_write():
    """测试原子性写入"""
    print("\n=== 测试原子性写入功能 ===")
    
    analyzer = TechnicalAnalyzer()
    cache_file = analyzer._get_kline_cache_file("atomic_test")
    
    # 清理旧文件
    temp_file = cache_file.with_suffix('.tmp')
    if cache_file.exists():
        cache_file.unlink()
    if temp_file.exists():
        temp_file.unlink()
    
    # 模拟写入过程
    test_data = [{'date': pd.Timestamp("2025-01-01"), 'close': 10.0}]
    
    try:
        analyzer._save_kline_to_cache(cache_file, test_data)
        
        # 检查临时文件是否被清理
        if not temp_file.exists():
            print("[SUCCESS] 临时文件已正确清理")
        else:
            print("[ERROR] 临时文件未清理")
            
        # 检查主文件是否存在
        if cache_file.exists():
            print("[SUCCESS] 主缓存文件正确创建")
        else:
            print("[ERROR] 主缓存文件未创建")
            
    except Exception as e:
        print(f"[ERROR] 原子性写入测试失败: {e}")

def main():
    """主测试函数"""
    print("缓存文件创建问题修复测试")
    print("=" * 50)
    
    # 运行所有测试
    test_cache_environment()
    test_cache_save_enhanced()
    test_cache_load_enhanced()
    test_atomic_write()
    
    print("\n" + "=" * 50)
    print("缓存修复测试完成!")

if __name__ == "__main__":
    main()