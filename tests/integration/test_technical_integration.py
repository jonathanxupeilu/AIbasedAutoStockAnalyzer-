#!/usr/bin/env python3
"""
测试技术指标分析功能集成
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from stock_analyzer.core.technical_analyzer import TechnicalAnalyzer
from stock_analyzer.core.analyst import analyze_stock


def test_technical_analyzer():
    """测试技术分析器功能"""
    print("=== 测试技术分析器功能 ===")
    
    # 创建技术分析器
    analyzer = TechnicalAnalyzer()
    
    # 检查Token配置
    if analyzer.token:
        print("[OK] 已配置LIXINGER_TOKEN，将尝试调用真实API")
    else:
        print("[WARN] 未配置LIXINGER_TOKEN，将使用模拟数据")
    
    # 测试不同股票代码的技术分析
    test_cases = [
        ("000001", "平安银行"),
        ("600519", "贵州茅台"),
        ("300750", "宁德时代")
    ]
    
    for stock_code, stock_name in test_cases:
        print(f"\n--- 测试 {stock_name}({stock_code}) ---")
        
        # 获取技术分析数据
        result = analyzer.analyze_stock_technical(stock_code, stock_name)
        
        print(f"分析状态: {result['status']}")
        print(f"时间戳: {result['analysis_timestamp']}")
        
        if result['status'] == 'success':
            data = result['technical_data']
            print(f"数据源: {data.get('data_source', 'N/A')}")
            print(f"当前价格: {data.get('current_price', 'N/A'):.2f}")
            print(f"数据周期: {data.get('data_period', 'N/A')}")
            print(f"周涨幅: {data.get('price_change_1w', 'N/A'):.2f}%")
            
            # 显示技术分析提示词
            print("\n技术分析提示词:")
            print("-" * 50)
            print(result['technical_prompt'][:300] + "...")  # 显示前300字符
            print("-" * 50)
            
            # 显示技术分析摘要
            summary = analyzer.get_technical_analysis_summary(result)
            print(f"\n技术分析摘要:\n{summary}")
            
            # 测试K线数据获取
            print(f"\n测试直接获取K线数据...")
            kline_data = analyzer.get_stock_kline_data(stock_code)
            if kline_data is not None:
                print(f"[OK] 成功获取K线数据，共 {len(kline_data)} 条记录")
                print(f"数据范围: {kline_data.index[0]} 到 {kline_data.index[-1]}")
                print(f"列名: {list(kline_data.columns)}")
        else:
            print("[FAIL] K线数据获取失败")

    else:
        print(f"错误: {result['technical_data'].get('error', '未知错误')}")


def test_integration_with_analyst():
    """测试技术分析与现有分析器的集成"""
    print("\n\n=== 测试技术分析与现有分析器的集成 ===")
    
    # 测试一个股票的分析
    stock_code = "000001"
    stock_name = "平安银行"
    output_dir = "./test_reports"
    
    print(f"分析股票: {stock_name}({stock_code})")
    print(f"输出目录: {output_dir}")
    
    try:
        # 调用分析函数
        result = analyze_stock(stock_code, stock_name, output_dir)
        
        if result:
            print(f"分析成功!")
            print(f"股票代码: {result['stock_code']}")
            print(f"股票名称: {result['stock_name']}")
            print(f"报告路径: {result['report_path']}")
            
            # 读取报告内容
            report_path = Path(result['report_path'])
            if report_path.exists():
                content = report_path.read_text(encoding='utf-8')
                # 检查是否包含技术分析内容
                if "技术指标分析" in content:
                    print("[OK] 技术分析内容已成功集成到报告中")
                else:
                    print("[FAIL] 技术分析内容未在报告中找到")
                
                # 显示报告前几行
                print("\n报告预览:")
                print("-" * 50)
                lines = content.split('\n')[:10]
                for line in lines:
                    print(line)
                print("-" * 50)
            else:
                print("[FAIL] 报告文件未找到")
        else:
            print("[FAIL] 分析失败")
            
    except Exception as e:
        print(f"集成测试失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主测试函数"""
    print("技术指标分析功能集成测试")
    print("=" * 60)
    
    # 测试技术分析器
    test_technical_analyzer()
    
    # 测试集成
    test_integration_with_analyst()
    
    print("\n\n测试完成!")


if __name__ == "__main__":
    main()