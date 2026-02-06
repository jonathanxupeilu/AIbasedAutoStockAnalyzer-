"""修复缓存问题，强制使用真实API数据"""
from technical_analyzer import TechnicalAnalyzer
from pathlib import Path
import json

def fix_cache_issue():
    """清理旧缓存并强制使用真实API数据"""
    ta = TechnicalAnalyzer()
    cache_file = ta._get_kline_cache_file('000001')
    
    print('=== 清理旧缓存 ===')
    print(f'删除缓存文件: {cache_file}')
    
    if cache_file.exists():
        # 先查看缓存内容
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_content = json.load(f)
        
        # 判断数据源
        is_real_data = False
        if cache_content.get('data') and len(cache_content['data']) > 0:
            first_record = cache_content['data'][0]
            is_real_data = 'stockCode' in first_record
        
        data_source = '真实API' if is_real_data else '模拟数据'
        print(f'缓存数据源: {data_source}')
        print(f'缓存时间: {cache_content.get("timestamp")}')
        
        # 删除缓存文件
        cache_file.unlink()
        print('缓存文件已删除')
    else:
        print('缓存文件不存在')
    
    print('\n=== 重新获取数据 ===')
    # 强制重新获取数据
    kline_data = ta.get_stock_kline_data('000001', period='weekly', limit=52)
    
    if kline_data is not None:
        data_source = '真实API' if 'stockCode' in kline_data.columns else '模拟数据'
        print(f'数据获取成功，数据源: {data_source}')
        print(f'数据形状: {kline_data.shape}')
        
        # 检查最新数据
        latest_date = kline_data.index[-1]
        latest_price = kline_data.iloc[-1]['close']
        print(f'最新数据日期: {latest_date}')
        print(f'最新收盘价: {latest_price:.2f}')
        
        # 检查数据时效性
        from datetime import datetime
        if hasattr(latest_date, 'date'):
            days_diff = (datetime.now().date() - latest_date.date()).days
            print(f'数据时效性: 与当前日期相差{days_diff}天')
            
        return kline_data
    else:
        print('数据获取失败')
        return None

if __name__ == "__main__":
    fix_cache_issue()