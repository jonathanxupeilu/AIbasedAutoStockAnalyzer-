"""调试技术分析器数据获取问题"""
import os
from dotenv import load_dotenv
from technical_analyzer import TechnicalAnalyzer
import pandas as pd

print('=== 调试技术分析器 ===')

# 检查环境变量加载
print('1. 检查环境变量加载')
load_dotenv()
token = os.getenv('LIXINGER_TOKEN')
print(f'LIXINGER_TOKEN: {token[:10]}...' if token else 'LIXINGER_TOKEN: None')

# 创建分析器实例
print('\n2. 创建技术分析器实例')
analyzer = TechnicalAnalyzer()
print(f'分析器Token: {analyzer.token[:10]}...' if analyzer.token else '分析器Token: None')

# 测试缓存检查
print('\n3. 测试缓存检查')
cache_file = analyzer._get_kline_cache_file('000001')
print(f'缓存文件: {cache_file}')
print(f'缓存文件存在: {cache_file.exists()}')

if cache_file.exists():
    print(f'缓存有效: {analyzer._is_kline_cache_valid(cache_file)}')
    cached_data = analyzer._load_kline_from_cache(cache_file)
    if cached_data is not None:
        print('缓存数据加载成功!')
        print(f'缓存数据形状: {cached_data.shape}')
        print('缓存数据前5行:')
        print(cached_data.head())
        print('缓存数据后5行:')
        print(cached_data.tail())

# 测试API调用
print('\n4. 测试API调用')
api_data = analyzer._fetch_kline_from_lixinger('000001', 52)
if api_data is not None:
    print('API调用成功!')
    print(f'API数据形状: {api_data.shape}')
    print('API数据后5行:')
    print(api_data.tail())
else:
    print('API调用失败或返回空数据')

# 测试完整数据获取流程
print('\n5. 测试完整数据获取流程')
kline_data = analyzer.get_stock_kline_data('000001', period='weekly', limit=52)

if kline_data is not None:
    print('数据获取成功!')
    print(f'数据形状: {kline_data.shape}')
    data_source_type = '真实API' if 'stockCode' in kline_data.columns else '模拟数据'
    print(f'数据源: {data_source_type}')
    print('最新5条数据:')
    print(kline_data.tail())
    
    # 格式化技术数据
    print('\n6. 格式化技术数据')
    tech_data = analyzer.format_kline_data_for_analysis(kline_data, '000001', '平安银行')
    print(f'当前价格: {tech_data.get(\"current_price\", \"N/A\")}')
    print(f'最新日期: {tech_data.get(\"latest_date\", \"N/A\")}')
    print(f'数据源: {tech_data.get(\"data_source\", \"N/A\")}')
else:
    print('数据获取失败')