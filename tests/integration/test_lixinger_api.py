import requests
import os
from datetime import datetime, timedelta

def test_lixinger_api():
    """测试理杏仁API调用"""
    token = os.getenv('LIXINGER_TOKEN')
    print('LIXINGER_TOKEN配置:', '已配置' if token else '未配置')
    
    if not token:
        print('未配置LIXINGER_TOKEN，无法测试API')
        return
        
    # 准备API请求
    end_date = datetime.now()
    start_date = end_date - timedelta(weeks=52)
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        'token': token,
        'stockCode': '000001',
        'type': 'lxr_fc_rights',
        'startDate': start_date.strftime('%Y-%m-%d'),
        'endDate': end_date.strftime('%Y-%m-%d'),
        'limit': 52
    }
    
    print('API请求参数:')
    print(f'  股票代码: {payload["stockCode"]}')
    print(f'  数据周期: {payload["startDate"]} 至 {payload["endDate"]}')
    
    try:
        print('\n正在调用理杏仁API...')
        response = requests.post(
            'https://open.lixinger.com/api/cn/company/candlestick',
            json=payload, 
            headers=headers, 
            timeout=30
        )
        
        print(f'API响应状态码: {response.status_code}')
        
        if response.status_code == 200:
            data = response.json()
            print(f'API返回代码: {data.get("code")}')
            print(f'API返回消息: {data.get("message", "无消息")}')
            
            if data.get('code') == 1:
                kline_data = data.get('data', [])
                print(f'API调用成功! 获取到{len(kline_data)}条K线数据')
                if kline_data:
                    print('\n最新5条K线数据:')
                    for i, item in enumerate(kline_data[-5:], 1):
                        print(f'  第{i}条: 日期{item.get("date")}, 收盘价{item.get("close")}')
            else:
                print('API调用失败，错误详情:')
                print(data)
        else:
            print(f'API请求失败，状态码: {response.status_code}')
            print(f'响应内容: {response.text[:200]}')
            
    except requests.exceptions.Timeout:
        print('API请求超时')
    except requests.exceptions.ConnectionError:
        print('网络连接失败，无法访问API')
    except Exception as e:
        print(f'API调用异常: {e}')

if __name__ == "__main__":
    test_lixinger_api()