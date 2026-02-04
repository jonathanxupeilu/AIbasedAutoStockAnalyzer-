"""
个股新闻API测试模块
测试东方财富个股新闻接口 stock_news_em
接口文档参考: https://www.akshare.xyz/data/stock/stock.html#id57
"""

import unittest
import pandas as pd
import akshare as ak
from datetime import datetime
from typing import Dict, List, Optional


class StockNewsAPITest(unittest.TestCase):
    """个股新闻API功能测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_symbols = [
            "000426",  # 兴业银锡
        ]
        self.required_columns = [
            "关键词", "新闻标题", "新闻内容", 
            "发布时间", "文章来源", "新闻链接"
        ]
    
    def test_api_connection(self):
        """测试API连接是否正常"""
        print("\n=== 测试API连接 ===")
        try:
            df = ak.stock_news_em(symbol=self.test_symbols[0])
            self.assertIsNotNone(df, "API返回不应为None")
            print(f"[OK] API连接成功，获取到 {len(df)} 条新闻")
        except Exception as e:
            self.fail(f"API连接失败: {e}")
    
    def test_response_data_structure(self):
        """测试返回数据结构是否符合预期"""
        print("\n=== 测试数据结构 ===")
        df = ak.stock_news_em(symbol=self.test_symbols[0])
        
        # 检查是否为DataFrame
        self.assertIsInstance(df, pd.DataFrame, "返回应为pandas DataFrame")
        
        # 检查必需列是否存在
        for col in self.required_columns:
            self.assertIn(col, df.columns, f"缺少必需列: {col}")
        
        print(f"[OK] 数据结构正确，包含列: {list(df.columns)}")
    
    def test_data_content_validity(self):
        """测试返回数据内容有效性"""
        print("\n=== 测试数据内容 ===")
        df = ak.stock_news_em(symbol=self.test_symbols[0])
        
        if len(df) == 0:
            print("⚠ 返回数据为空，跳过内容验证")
            return
        
        # 检查第一行数据
        first_row = df.iloc[0]
        
        # 验证标题不为空
        self.assertIsNotNone(first_row["新闻标题"], "新闻标题不应为None")
        self.assertNotEqual(str(first_row["新闻标题"]).strip(), "", "新闻标题不应为空")
        
        # 验证发布时间格式
        pub_time = first_row["发布时间"]
        self.assertIsNotNone(pub_time, "发布时间不应为None")
        print(f"[OK] 发布时间示例: {pub_time}")
        
        # 验证新闻链接格式
        link = first_row["新闻链接"]
        if pd.notna(link):
            self.assertTrue(
                link.startswith("http"), 
                f"新闻链接应以http开头: {link}"
            )
        
        print(f"[OK] 数据内容有效，标题: {first_row['新闻标题'][:30]}...")
    
    def test_multiple_stocks(self):
        """测试多只股票新闻获取"""
        print("\n=== 测试多只股票 ===")
        results = {}
        
        for symbol in self.test_symbols:
            try:
                df = ak.stock_news_em(symbol=symbol)
                results[symbol] = {
                    "count": len(df),
                    "success": True
                }
                print(f"  {symbol}: 获取到 {len(df)} 条新闻")
            except Exception as e:
                results[symbol] = {
                    "count": 0,
                    "success": False,
                    "error": str(e)
                }
                print(f"  {symbol}: 获取失败 - {e}")
        
        # 至少有一只股票获取成功
        success_count = sum(1 for r in results.values() if r["success"])
        self.assertGreater(success_count, 0, "至少应有一只股票获取成功")
        print(f"[OK] 多只股票测试完成，{success_count}/{len(self.test_symbols)} 成功")
    
    def test_data_volume_limit(self):
        """测试数据量限制（应返回最近100条）"""
        print("\n=== 测试数据量限制 ===")
        df = ak.stock_news_em(symbol=self.test_symbols[0])
        
        # 根据文档，应返回最近100条
        self.assertLessEqual(
            len(df), 100, 
            f"返回数据量({len(df)})不应超过100条"
        )
        print(f"[OK] 数据量符合限制: {len(df)} 条 (<=100)")
    
    def test_invalid_symbol_handling(self):
        """测试无效股票代码处理"""
        print("\n=== 测试无效代码处理 ===")
        invalid_symbols = ["999999", "invalid", ""]
        
        for symbol in invalid_symbols:
            try:
                df = ak.stock_news_em(symbol=symbol)
                # 无效代码应返回空DataFrame或正常处理
                print(f"  '{symbol}': 返回 {len(df)} 条数据")
            except Exception as e:
                # 抛出异常也是可接受的
                print(f"  '{symbol}': 抛出异常 - {type(e).__name__}")
        
        print("[OK] 无效代码处理测试完成")


class StockNewsDataExtractor:
    """个股新闻数据提取器（用于实际业务场景）"""
    
    @staticmethod
    def fetch_news(symbol: str, max_items: int = 20) -> List[Dict]:
        """
        获取个股新闻并格式化为字典列表
        
        Args:
            symbol: 股票代码
            max_items: 最大返回条数
            
        Returns:
            新闻列表，每项为字典
        """
        try:
            df = ak.stock_news_em(symbol=symbol)
            
            if df.empty:
                return []
            
            # 限制返回数量
            df = df.head(max_items)
            
            # 转换为字典列表
            news_list = []
            for _, row in df.iterrows():
                news_item = {
                    "keyword": row.get("关键词", ""),
                    "title": row.get("新闻标题", ""),
                    "content": row.get("新闻内容", ""),
                    "publish_time": row.get("发布时间", ""),
                    "source": row.get("文章来源", ""),
                    "url": row.get("新闻链接", "")
                }
                news_list.append(news_item)
            
            return news_list
            
        except Exception as e:
            print(f"[ERROR] 获取新闻失败 {symbol}: {e}")
            return []
    
    @staticmethod
    def format_news_for_analysis(news_list: List[Dict]) -> str:
        """
        将新闻格式化为分析用的文本
        
        Args:
            news_list: 新闻列表
            
        Returns:
            格式化后的文本
        """
        if not news_list:
            return "暂无相关新闻数据"
        
        lines = ["## 近期相关新闻\n"]
        
        for i, news in enumerate(news_list[:10], 1):  # 最多显示10条
            lines.append(f"{i}. **{news['title']}**")
            lines.append(f"   - 来源: {news['source']} | 时间: {news['publish_time']}")
            if news['content']:
                content = news['content'][:100] + "..." if len(news['content']) > 100 else news['content']
                lines.append(f"   - 摘要: {content}")
            lines.append("")
        
        return "\n".join(lines)


def run_demo():
    """运行演示示例"""
    print("=" * 60)
    print("个股新闻API演示")
    print("=" * 60)
    
    symbol = "000426"  # 兴业银锡
    
    print(f"\n获取股票 {symbol} 的最新新闻...")
    
    # 获取新闻
    news_list = StockNewsDataExtractor.fetch_news(symbol, max_items=5)
    
    if news_list:
        print(f"\n成功获取 {len(news_list)} 条新闻:\n")
        for i, news in enumerate(news_list, 1):
            print(f"{i}. {news['title']}")
            print(f"   来源: {news['source']} | 时间: {news['publish_time']}")
            print()
        
        # 显示格式化输出
        print("\n" + "=" * 60)
        print("格式化输出示例:")
        print("=" * 60)
        formatted = StockNewsDataExtractor.format_news_for_analysis(news_list)
        print(formatted)
    else:
        print("未获取到新闻数据")


if __name__ == "__main__":
    # 运行单元测试
    print("\n" + "=" * 60)
    print("运行单元测试")
    print("=" * 60)
    unittest.main(verbosity=2, exit=False)
    
    # 运行演示
    print("\n")
    run_demo()
