"""
个股新闻数据格式化工具
用于获取和格式化个股新闻数据，供LLM分析使用
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class StockNewsFormatter:
    """个股新闻数据格式化器"""
    
    def __init__(self, max_news_count: int = 10):
        """
        初始化新闻格式化器
        
        Args:
            max_news_count: 最大新闻数量，默认10条
        """
        self.max_news_count = max_news_count
        self.required_columns = [
            "关键词", "新闻标题", "新闻内容", 
            "发布时间", "文章来源", "新闻链接"
        ]
    
    def fetch_stock_news(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        获取个股新闻数据
        
        Args:
            symbol: 股票代码，如"000426"
            
        Returns:
            pandas DataFrame 或 None（获取失败时）
        """
        try:
            df = ak.stock_news_em(symbol=symbol)
            if df is not None and not df.empty:
                # 确保包含必需列
                for col in self.required_columns:
                    if col not in df.columns:
                        df[col] = ""
                return df.head(self.max_news_count)
            return None
        except Exception as e:
            print(f"[ERROR] 获取股票 {symbol} 新闻失败: {e}")
            return None
    
    def format_news_for_analysis(self, symbol: str, stock_name: str) -> str:
        """
        格式化新闻数据供LLM分析使用
        
        Args:
            symbol: 股票代码
            stock_name: 股票名称
            
        Returns:
            格式化后的新闻文本
        """
        df = self.fetch_stock_news(symbol)
        if df is None or df.empty:
            return f"\n**最新新闻动态**: 暂未获取到{stock_name}({symbol})的最新新闻数据\n"
        
        formatted_news = f"\n**{stock_name}({symbol}) 最新新闻动态**\n\n"
        
        # 按时间倒序排序，获取最新的新闻
        if '发布时间' in df.columns:
            df = df.sort_values('发布时间', ascending=False)
        
        for idx, row in df.iterrows():
            # 格式化单条新闻
            news_item = f"**{idx + 1}. {row.get('新闻标题', '无标题')}**\n"
            
            # 添加发布时间
            if pd.notna(row.get('发布时间')):
                news_item += f"- 发布时间: {row.get('发布时间')}\n"
            
            # 添加来源
            if pd.notna(row.get('文章来源')):
                news_item += f"- 来源: {row.get('文章来源')}\n"
            
            # 添加新闻内容摘要（前100字符）
            if pd.notna(row.get('新闻内容')):
                content = str(row.get('新闻内容', ''))
                if len(content) > 100:
                    content = content[:100] + "..."
                news_item += f"- 内容摘要: {content}\n"
            
            # 添加关键词
            if pd.notna(row.get('关键词')) and row.get('关键词') != "":
                news_item += f"- 关键词: {row.get('关键词')}\n"
            
            formatted_news += news_item + "\n"
        
        # 添加新闻统计信息
        formatted_news += f"\n**新闻统计**: 共获取到 {len(df)} 条最新新闻，涵盖市场动态、机构观点、行业事件等信息。\n"
        
        return formatted_news
    
    def get_news_summary(self, symbol: str, stock_name: str) -> Dict[str, any]:
        """
        获取新闻数据摘要统计
        
        Args:
            symbol: 股票代码
            stock_name: 股票名称
            
        Returns:
            新闻摘要字典
        """
        df = self.fetch_stock_news(symbol)
        if df is None or df.empty:
            return {
                "news_count": 0,
                "latest_news_time": None,
                "sources": [],
                "keywords": []
            }
        
        # 统计信息
        sources = df['文章来源'].dropna().unique().tolist() if '文章来源' in df.columns else []
        
        # 提取关键词
        all_keywords = []
        if '关键词' in df.columns:
            for keywords in df['关键词'].dropna():
                if isinstance(keywords, str):
                    all_keywords.extend([k.strip() for k in keywords.split(',') if k.strip()])
        
        # 最新新闻时间
        latest_time = None
        if '发布时间' in df.columns:
            latest_time = df['发布时间'].max()
        
        return {
            "news_count": len(df),
            "latest_news_time": latest_time,
            "sources": sources,
            "keywords": list(set(all_keywords))[:10]  # 去重，最多10个关键词
        }


def format_news_for_prompt(symbol: str, stock_name: str) -> str:
    """
    快捷函数：格式化新闻数据供LLM提示词使用
    
    Args:
        symbol: 股票代码
        stock_name: 股票名称
        
    Returns:
        格式化后的新闻文本
    """
    formatter = StockNewsFormatter()
    return formatter.format_news_for_analysis(symbol, stock_name)


if __name__ == "__main__":
    # 测试代码
    formatter = StockNewsFormatter()
    
    # 测试兴业银锡
    symbol = "000426"
    stock_name = "兴业银锡"
    
    print("=" * 60)
    print("个股新闻数据格式化工具测试")
    print("=" * 60)
    
    # 测试格式化功能
    formatted_news = formatter.format_news_for_analysis(symbol, stock_name)
    print(formatted_news)
    
    # 测试摘要功能
    summary = formatter.get_news_summary(symbol, stock_name)
    print("\n新闻摘要:")
    print(f"- 新闻数量: {summary['news_count']}")
    print(f"- 最新新闻时间: {summary['latest_news_time']}")
    print(f"- 新闻来源: {summary['sources']}")
    print(f"- 关键词: {summary['keywords']}")