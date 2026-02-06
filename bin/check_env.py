#!/usr/bin/env python3
"""检查环境变量加载情况"""

import os
from dotenv import load_dotenv

def check_environment():
    print("=== 环境变量检查 ===")
    
    # 尝试加载.env文件
    try:
        load_dotenv()
        print("[INFO] .env文件已加载")
    except Exception as e:
        print(f"[WARN] 无法加载.env文件: {e}")
    
    # 检查LIXINGER_TOKEN
    token = os.getenv("LIXINGER_TOKEN")
    if token:
        print(f"[SUCCESS] LIXINGER_TOKEN已配置 (长度: {len(token)})")
        # 显示部分token（保护隐私）
        if len(token) > 8:
            print(f"       Token预览: {token[:8]}...{token[-4:]}")
    else:
        print("[ERROR] LIXINGER_TOKEN未配置")
    
    # 检查其他环境变量
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    if deepseek_key:
        print(f"[SUCCESS] DEEPSEEK_API_KEY已配置")
    else:
        print("[WARN] DEEPSEEK_API_KEY未配置")
    
    print("\n=== 测试理杏仁API连接 ===")
    
    if token:
        import requests
        
        url = "https://open.lixinger.com/api/cn/company"
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "token": token,
            "stockCodes": ["000001"],
            "date": "2025-01-30",
            "metrics": ["pe_ttm", "pb"]
        }
        
        try:
            print("[INFO] 测试理杏仁API连接...")
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 200:
                    print("[SUCCESS] 理杏仁API连接正常")
                    print(f"       返回数据条数: {len(data.get('data', []))}")
                else:
                    error_msg = data.get("message", "未知错误")
                    print(f"[ERROR] API返回错误: {error_msg}")
                    print(f"       错误详情: {data}")
            else:
                print(f"[ERROR] HTTP请求失败，状态码: {response.status_code}")
                try:
                    error_detail = response.text
                    print(f"       错误详情: {error_detail[:200]}")
                except:
                    pass
                
        except requests.exceptions.Timeout:
            print("[ERROR] API请求超时")
        except requests.exceptions.ConnectionError:
            print("[ERROR] 网络连接失败")
        except Exception as e:
            print(f"[ERROR] API调用异常: {e}")
    else:
        print("[SKIP] 未配置LIXINGER_TOKEN，跳过API测试")

if __name__ == "__main__":
    check_environment()