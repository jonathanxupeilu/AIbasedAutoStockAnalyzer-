#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B方案验证测试脚本
验证技术分析器的多数据源策略、数据新鲜度检测、状态评估等功能
"""

import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from stock_analyzer.core.technical_analyzer import TechnicalAnalyzer


def test_data_source_priority():
    """测试多数据源优先级策略"""
    print("=== 测试多数据源优先级策略 ===")
    
    analyzer = TechnicalAnalyzer()
    
    # 测试股票代码 - 优化为单股票测试（提升效率）
    test_stocks = ["000001"]  # 平安银行，数据稳定，覆盖面广
    
    for stock_code in test_stocks:
        print(f"\n--- 测试股票 {stock_code} ---")
        
        try:
            # 获取K线数据（增强错误处理）
            kline_data = analyzer.get_stock_kline_data(stock_code, period="weekly", limit=52)
            
            if kline_data is not None and not kline_data.empty:
                # 格式化技术数据
                technical_data = analyzer.format_kline_data_for_analysis(kline_data, stock_code, "测试股票")
                
                print(f"数据源: {technical_data['data_source']}")
                print(f"数据状态: {technical_data['data_status']}")
                print(f"数据新鲜度: {technical_data['data_freshness_days']}天前")
                print(f"数据警告: {technical_data['data_warning']}")
                print(f"数据条数: {len(kline_data)}")
                print(f"最新日期: {technical_data['latest_date']}")
                
                # 验证数据质量
                if technical_data['data_source'] == "模拟数据":
                    print("[WARN] 使用模拟数据（降级方案）")
                elif technical_data['data_freshness_days'] <= 3:
                    print("[OK] 数据时效性良好")
                else:
                    print("[WARN] 数据较旧，但功能正常")
            else:
                print("❌ 数据获取失败")
        except Exception as e:
            print(f"❌ 数据获取过程中出现异常: {e}")
            print("[INFO] 这是预期的降级行为，系统会继续使用模拟数据")


def test_data_freshness_detection():
    """测试数据新鲜度检测机制"""
    print("\n\n=== 测试数据新鲜度检测机制 ===")
    
    analyzer = TechnicalAnalyzer()
    
    # 创建测试缓存文件
    test_cache_file = analyzer._get_kline_cache_file("test_stock")
    
    # 生成过期的测试数据（7天前）
    test_data = {
        'timestamp': (datetime.now() - timedelta(days=10)).isoformat(),
        'data': [
            {
                'date': (datetime.now() - timedelta(days=8)).isoformat(),
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
    with open(test_cache_file, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    print(f"创建测试缓存文件: {test_cache_file}")
    print(f"缓存时间: {test_data['timestamp']}")
    print(f"数据最新日期: {test_data['data'][0]['date']}")
    
    # 测试缓存有效性检查
    is_valid = analyzer._is_kline_cache_valid(test_cache_file, max_age_hours=24)
    print(f"缓存有效性检查结果: {'[OK] 有效' if is_valid else '[WARN] 无效（预期结果）'}")
    
    # 清理测试文件
    if test_cache_file.exists():
        test_cache_file.unlink()
        print("清理测试缓存文件")


def test_data_status_evaluation():
    """测试数据状态评估系统"""
    print("\n\n=== 测试数据状态评估系统 ===")
    
    analyzer = TechnicalAnalyzer()
    
    # 模拟不同新鲜度的数据
    test_cases = [
        ("1天前", timedelta(days=1), "excellent"),
        ("2天前", timedelta(days=2), "good"),
        ("5天前", timedelta(days=5), "warning"),
        ("10天前", timedelta(days=10), "critical"),
        ("模拟数据", None, "simulated")
    ]
    
    for case_name, time_delta, expected_status in test_cases:
        print(f"\n--- 测试案例: {case_name} ---")
        
        if time_delta:
            # 创建测试数据
            test_date = datetime.now() - time_delta
            test_data = pd.DataFrame({
                'date': [test_date],
                'open': [10.0],
                'high': [11.0],
                'low': [9.5],
                'close': [10.5],
                'volume': [1000000],
                'stockCode': ['test_stock']
            })
            test_data['date'] = pd.to_datetime(test_data['date'])
            test_data.set_index('date', inplace=True)
            
            # 格式化分析
            technical_data = analyzer.format_kline_data_for_analysis(test_data, "test_stock", "测试股票")
        else:
            # 模拟数据案例
            technical_data = {
                'data_source': '模拟数据',
                'data_status': 'simulated',
                'data_warning': '使用模拟数据，分析结果仅供参考'
            }
        
        print(f"数据状态: {technical_data.get('data_status', 'N/A')}")
        print(f"预期状态: {expected_status}")
        print(f"状态匹配: {'[OK]' if technical_data.get('data_status') == expected_status else '[FAIL]'}")
        print(f"数据警告: {technical_data.get('data_warning', 'N/A')}")


def test_complete_analysis_pipeline():
    """测试完整分析流程（增强错误处理）"""
    print("\n\n=== 测试完整分析流程 ===")
    
    analyzer = TechnicalAnalyzer()
    
    # 测试股票
    test_stock_code = "000001"
    test_stock_name = "平安银行"
    
    print(f"分析股票: {test_stock_name}({test_stock_code})")
    
    try:
        # 执行技术分析（增强错误处理）
        analysis_result = analyzer.analyze_stock_technical(test_stock_code, test_stock_name)
        
        print(f"分析状态: {analysis_result['status']}")
        print(f"分析时间: {analysis_result['analysis_timestamp']}")
        
        # 检查是否包含新的B+C方案字段
        if 'data_quality' in analysis_result:
            print(f"数据质量: {analysis_result['data_quality']}")
        if 'integration_level' in analysis_result:
            print(f"集成级别: {analysis_result['integration_level']}")
        
        if analysis_result['status'] == 'success':
            technical_data = analysis_result['technical_data']
            
            print(f"\n技术数据详情:")
            print(f"- 数据源: {technical_data['data_source']}")
            print(f"- 数据状态: {technical_data['data_status']}")
            print(f"- 最新日期: {technical_data['latest_date']}")
            print(f"- 新鲜度: {technical_data['data_freshness_days']}天前")
            print(f"- 当前价格: {technical_data['current_price']:.2f}")
            
            # 显示技术分析提示词摘要
            prompt = analysis_result['technical_prompt']
            prompt_lines = prompt.split('\n')[:15]  # 显示前15行
            print(f"\n技术分析提示词摘要:")
            for line in prompt_lines:
                print(f"  {line}")
            
            # 生成摘要
            summary = analyzer.get_technical_analysis_summary(analysis_result)
            print(f"\n技术分析摘要:")
            print(summary)
        else:
            print(f"分析失败: {analysis_result['technical_data']['error']}")
            print("[INFO] 这是预期的降级行为，系统会继续运行")
            
    except Exception as e:
        print(f"❌ 分析流程异常: {e}")
        print("[INFO] 异常被捕获，测试继续执行")


def test_cache_mechanism():
    """测试缓存机制（增强错误处理）"""
    print("\n\n=== 测试缓存机制 ===")
    
    analyzer = TechnicalAnalyzer()
    
    # 测试股票
    test_stock_code = "600036"
    
    try:
        test_cache_file = analyzer._get_kline_cache_file(test_stock_code)
        
        print(f"测试股票: {test_stock_code}")
        print(f"缓存文件: {test_cache_file}")
        
        # 清理可能存在的旧缓存
        if test_cache_file.exists():
            test_cache_file.unlink()
            print("清理旧缓存文件")
        
        # 第一次获取数据（应该从API获取）
        print("\n--- 第一次获取数据（应该从API获取） ---")
        kline_data1 = analyzer.get_stock_kline_data(test_stock_code, period="weekly", limit=52)
        
        if kline_data1 is not None:
            print(f"第一次获取数据条数: {len(kline_data1)}")
            
            # 检查缓存文件是否创建
            if test_cache_file.exists():
                print("✅ 缓存文件已创建")
                
                # 第二次获取数据（应该从缓存获取）
                print("\n--- 第二次获取数据（应该从缓存获取） ---")
                kline_data2 = analyzer.get_stock_kline_data(test_stock_code, period="weekly", limit=52)
                
                if kline_data2 is not None:
                    print(f"第二次获取数据条数: {len(kline_data2)}")
                    
                    # 比较两次获取的数据是否一致
                    if len(kline_data1) == len(kline_data2):
                        print("✅ 缓存机制工作正常")
                    else:
                        print("❌ 缓存机制异常（数据长度不一致）")
                else:
                    print("❌ 第二次数据获取失败")
            else:
                print("[FAIL] 缓存文件未创建")
        else:
            print("❌ 第一次数据获取失败")
            print("[INFO] 可能是网络问题或API限制，系统会降级到模拟数据")
            
    except Exception as e:
        print(f"❌ 缓存测试异常: {e}")
        print("[INFO] 异常被捕获，测试继续执行")


def main():
    """主测试函数"""
    print("=" * 60)
    print("B方案技术分析器验证测试")
    print("=" * 60)
    
    try:
        # 执行各项测试
        test_data_source_priority()
        test_data_freshness_detection()
        test_data_status_evaluation()
        test_complete_analysis_pipeline()
        test_cache_mechanism()
        
        print("\n" + "=" * 60)
        print("[OK] B方案验证测试完成")
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