#!/usr/bin/env python3
"""
测试新闻数据集成功能
验证个股新闻API是否成功集成到LLM分析流程中
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from stock_analyzer.utils.news_formatter import StockNewsFormatter
from stock_analyzer.core.analyst import _generate_analysis_sequentially


def test_news_formatter():
    """测试新闻格式化器功能"""
    print("=" * 60)
    print("测试新闻格式化器功能")
    print("=" * 60)
    
    formatter = StockNewsFormatter()
    
    # 测试兴业银锡
    symbol = "000426"
    stock_name = "兴业银锡"
    
    # 测试新闻获取
    print(f"\n1. 测试新闻数据获取 - {stock_name}({symbol})")
    df = formatter.fetch_stock_news(symbol)
    if df is not None and not df.empty:
        print(f"   [OK] 成功获取到 {len(df)} 条新闻")
        print(f"   [OK] 新闻列名: {list(df.columns)}")
        
        # 显示最新新闻标题
        latest_title = df.iloc[0]['新闻标题'] if '新闻标题' in df.columns else '无标题'
        print(f"   [OK] 最新新闻标题: {latest_title[:50]}...")
    else:
        print("   [ERROR] 新闻获取失败")
        return False
    
    # 测试新闻格式化
    print(f"\n2. 测试新闻数据格式化")
    formatted_news = formatter.format_news_for_analysis(symbol, stock_name)
    if formatted_news and len(formatted_news) > 0:
        print(f"   [OK] 新闻格式化成功，文本长度: {len(formatted_news)}")
        
        # 显示格式化后的新闻片段
        lines = formatted_news.split('\n')[:8]  # 显示前8行
        print("   [OK] 格式化新闻预览:")
        for line in lines:
            if line.strip():
                print(f"      {line}")
    else:
        print("   [ERROR] 新闻格式化失败")
        return False
    
    # 测试新闻摘要
    print(f"\n3. 测试新闻摘要统计")
    summary = formatter.get_news_summary(symbol, stock_name)
    if summary:
        print(f"   [OK] 新闻摘要获取成功")
        print(f"   [OK] 新闻数量: {summary['news_count']}")
        print(f"   [OK] 最新时间: {summary['latest_news_time']}")
        print(f"   [OK] 新闻来源: {summary['sources'][:3]}...")  # 显示前3个来源
        if summary['keywords']:
            print(f"   [OK] 关键词: {summary['keywords'][:5]}")  # 显示前5个关键词
    else:
        print("   [ERROR] 新闻摘要获取失败")
        return False
    
    return True


def test_analysis_integration():
    """测试新闻数据集成到分析流程"""
    print("\n" + "=" * 60)
    print("测试新闻数据集成到分析流程")
    print("=" * 60)
    
    # 模拟基本面数据
    fundamentals = {
        "PE(TTM)估算": 15.8,
        "PB": 2.1,
        "股息率": 3.2,
        "总市值(亿)": 150.5,
        "ROE(TTM)": 12.5
    }
    
    symbol = "000426"
    stock_name = "兴业银锡"
    
    print(f"\n测试股票: {stock_name}({symbol})")
    print("基本面数据:", fundamentals)
    
    # 测试顺序分析函数（不实际调用API）
    print("\n测试新闻数据集成逻辑...")
    
    # 检查是否能够正确调用
    try:
        # 这里我们不实际调用API，只测试逻辑
        from analyst import _load_analysis_framework
        config = _load_analysis_framework()
        framework = config.get("analysis_framework", [])
        
        # 检查综合投资建议步骤的prompt
        for item in framework:
            if item["question"] == "综合投资建议":
                prompt_template = item["prompt"]
                print(f"[OK] 找到综合投资建议prompt模板")
                print(f"[OK] 模板中包含news_data变量: {'{news_data}' in prompt_template}")
                
                # 测试变量替换
                test_news = "**测试新闻数据**\n- 测试新闻1\n- 测试新闻2"
                try:
                    formatted_prompt = prompt_template.format(
                        pe=fundamentals["PE(TTM)估算"],
                        pb=fundamentals["PB"],
                        dividend_yield=fundamentals["股息率"],
                        market_cap_billion=fundamentals["总市值(亿)"],
                        roe=fundamentals["ROE(TTM)"],
                        stock_code=symbol,
                        stock_name=stock_name,
                        news_data=test_news
                    )
                    print("[OK] 新闻数据变量替换成功")
                    
                    # 检查是否包含新闻数据
                    if "测试新闻数据" in formatted_prompt:
                        print("[OK] 新闻数据成功集成到prompt中")
                    else:
                        print("[ERROR] 新闻数据未正确集成")
                        return False
                        
                except KeyError as e:
                    print(f"[ERROR] 变量替换失败: {e}")
                    return False
                
                break
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("个股新闻数据集成测试")
    print("=" * 60)
    
    # 测试新闻格式化器
    news_test_passed = test_news_formatter()
    
    # 测试分析集成
    integration_test_passed = test_analysis_integration()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    
    if news_test_passed:
        print("[OK] 新闻格式化器测试 - 通过")
    else:
        print("[ERROR] 新闻格式化器测试 - 失败")
    
    if integration_test_passed:
        print("[OK] 分析集成测试 - 通过")
    else:
        print("[ERROR] 分析集成测试 - 失败")
    
    overall_passed = news_test_passed and integration_test_passed
    
    if overall_passed:
        print("\n[SUCCESS] 所有测试通过！新闻数据集成功能正常")
        print("\n下一步建议:")
        print("1. 运行完整分析流程: python main_pipeline.py --stock_codes 000426")
        print("2. 检查生成的报告是否包含新闻数据")
        print("3. 验证投资建议是否考虑了新闻因素")
    else:
        print("\n[ERROR] 部分测试失败，请检查代码实现")
    
    return overall_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)