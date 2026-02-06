#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试模拟数据生成函数
"""

from datetime import datetime
import pandas as pd

def debug_date_range():
    """调试日期范围生成"""
    limit = 52
    
    print("=== 调试日期范围生成 ===")
    print(f"limit: {limit}")
    
    # 测试不同的频率
    freq_options = ['W', 'W-MON', 'W-FRI', '7D']
    
    for freq in freq_options:
        try:
            dates = pd.date_range(end=datetime.now(), periods=limit, freq=freq)
            print(f"频率 '{freq}': 生成了 {len(dates)} 个日期")
            if len(dates) > 0:
                print(f"  第一个日期: {dates[0]}")
                print(f"  最后一个日期: {dates[-1]}")
        except Exception as e:
            print(f"频率 '{freq}': 错误 - {e}")
        print()

if __name__ == "__main__":
    debug_date_range()