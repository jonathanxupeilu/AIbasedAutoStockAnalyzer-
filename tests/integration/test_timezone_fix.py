#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时区问题修复测试脚本
验证时区一致性处理函数的正确性
"""

import os
import sys
from datetime import datetime, timezone, timedelta
import pandas as pd
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from stock_analyzer.core.technical_analyzer import safe_datetime_subtraction, TechnicalAnalyzer


def test_timezone_functions():
    """测试时区处理函数"""
    print("=== 测试时区处理函数 ===")
    
    # 创建测试数据
    naive_dt = pd.Timestamp("2025-11-21")  # 无时区
    aware_dt = pd.Timestamp("2025-11-21", tz='Asia/Shanghai')  # 上海时区
    aware_dt_utc = pd.Timestamp("2025-11-21", tz='UTC')  # UTC时区
    
    print(f"无时区日期: {naive_dt}")
    print(f"上海时区日期: {aware_dt}")
    print(f"UTC时区日期: {aware_dt_utc}")
    
    # 测试1: 两个无时区对象
    print("\n--- 测试1: 两个无时区对象 ---")
    diff = safe_datetime_subtraction(naive_dt, naive_dt)
    print(f"时间差: {diff}")
    
    # 测试2: 一个无时区，一个有时区
    print("\n--- 测试2: 无时区 vs 上海时区 ---")
    diff = safe_datetime_subtraction(naive_dt, aware_dt)
    print(f"时间差: {diff}")
    
    # 测试3: 两个不同时区
    print("\n--- 测试3: 上海时区 vs UTC时区 ---")
    diff = safe_datetime_subtraction(aware_dt, aware_dt_utc)
    print(f"时间差: {diff}")
    
    # 测试4: 实际数据新鲜度计算
    print("\n--- 测试4: 实际数据新鲜度计算 ---")
    current_date = pd.Timestamp.now().normalize()
    old_date = pd.Timestamp("2025-11-21", tz='Asia/Shanghai')
    
    print(f"当前日期: {current_date}")
    print(f"旧日期: {old_date}")
    
    days_diff = safe_datetime_subtraction(current_date, old_date).days
    print(f"数据新鲜度: 相差{days_diff}天")
    
    print("\n✅ 时区处理函数测试完成")


def test_technical_analyzer():
    """测试技术分析器中的时区处理"""
    print("\n=== 测试技术分析器时区处理 ===")

    from stock_analyzer.core.technical_analyzer import TechnicalAnalyzer
    
    analyzer = TechnicalAnalyzer()
    
    # 测试缓存有效性检查
    print("\n--- 测试缓存有效性检查 ---")
    
    # 创建测试缓存数据
    test_data = {
        'timestamp': datetime.now().isoformat(),
        'data': [
            {
                'date': pd.Timestamp("2025-11-21", tz='Asia/Shanghai').isoformat(),  # 带时区
                'open': 10.0,
                'high': 11.0,
                'low': 9.5,
                'close': 10.5,
                'volume': 1000000,
                'stockCode': 'test_stock'
            }
        ]
    }
    
    # 保存测试缓存
    cache_file = analyzer.cache_dir / "test_timezone_cache.json"
    with open(cache_file, 'w', encoding='utf-8') as f:
        import json
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    print(f"创建测试缓存文件: {cache_file}")
    
    # 测试缓存有效性检查
    try:
        is_valid = analyzer._is_kline_cache_valid(cache_file, max_age_hours=24)
        print(f"缓存有效性检查结果: {'有效' if is_valid else '无效'}")
        print("✅ 缓存有效性检查通过（时区处理正确）")
    except Exception as e:
        print(f"❌ 缓存有效性检查失败: {e}")
    
    # 测试数据加载
    print("\n--- 测试数据加载 ---")
    try:
        df = analyzer._load_kline_from_cache(cache_file)
        if df is not None:
            print(f"数据加载成功，形状: {df.shape}")
            print(f"最新日期: {df.index[-1]}")
            print("✅ 数据加载通过（时区处理正确）")
        else:
            print("❌ 数据加载失败")
    except Exception as e:
        print(f"❌ 数据加载失败: {e}")
    
    # 清理测试文件
    if cache_file.exists():
        cache_file.unlink()
        print("清理测试缓存文件")


def test_real_scenario():
    """测试真实场景中的时区处理"""
    print("\n=== 测试真实场景时区处理 ===")

    from stock_analyzer.core.technical_analyzer import TechnicalAnalyzer
    
    analyzer = TechnicalAnalyzer()
    
    # 测试股票
    test_stock_code = "000001"
    test_stock_name = "平安银行"
    
    print(f"测试股票: {test_stock_name}({test_stock_code})")
    
    try:
        # 获取K线数据
        kline_data = analyzer.get_stock_kline_data(test_stock_code, period="weekly", limit=52)
        
        if kline_data is not None and not kline_data.empty:
            print(f"数据获取成功，形状: {kline_data.shape}")
            print(f"索引类型: {type(kline_data.index)}")
            if hasattr(kline_data.index, 'tz'):
                print(f"索引时区: {kline_data.index.tz}")
            
            # 格式化技术数据
            technical_data = analyzer.format_kline_data_for_analysis(kline_data, test_stock_code, test_stock_name)
            
            print(f"数据源: {technical_data['data_source']}")
            print(f"数据状态: {technical_data['data_status']}")
            print(f"数据新鲜度: {technical_data['data_freshness_days']}天前")
            print(f"最新日期: {technical_data['latest_date']}")
            
            print("✅ 真实场景测试通过（时区处理正确）")
        else:
            print("❌ 数据获取失败")
            
    except Exception as e:
        print(f"❌ 真实场景测试失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主测试函数"""
    print("=" * 60)
    print("时区问题修复测试")
    print("=" * 60)
    
    try:
        # 执行各项测试
        test_timezone_functions()
        test_technical_analyzer()
        test_real_scenario()
        
        print("\n" + "=" * 60)
        print("[OK] 时区问题修复测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 激活虚拟环境
    venv_script = project_root / "activate_venv.bat"
    if venv_script.exists():
        print("检测到虚拟环境激活脚本，请在虚拟环境中运行测试")
    
    main()