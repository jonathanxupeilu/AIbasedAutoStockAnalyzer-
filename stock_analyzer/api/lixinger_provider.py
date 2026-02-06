import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests
import pandas as pd
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()


class LixingerProvider:
    """理杏仁API数据提供者"""
    
    def __init__(self, token: str = None):
        self.token = token or os.getenv("LIXINGER_TOKEN")
        self.base_url = "https://open.lixinger.com/api"
        self.cache_dir = Path(".cache")
        self.cache_dir.mkdir(exist_ok=True)
        
    def _get_cache_file(self, stock_codes: List[str]) -> Path:
        """获取缓存文件路径"""
        codes_str = "_".join(sorted(stock_codes))
        cache_filename = f"lixinger_data_{codes_str}.json"
        return self.cache_dir / cache_filename
    
    def _is_cache_valid(self, cache_file: Path, max_age_hours: int = 24) -> bool:
        """检查缓存是否有效"""
        if not cache_file.exists():
            return False
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            timestamp_str = data.get('timestamp', '')
            if not timestamp_str:
                return False
                
            cache_time = datetime.fromisoformat(timestamp_str)
            now = datetime.now()
            return (now - cache_time) < timedelta(hours=max_age_hours)
            
        except Exception:
            return False
    
    def _load_from_cache(self, cache_file: Path) -> Optional[pd.DataFrame]:
        """从缓存加载数据"""
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if 'data' in data and isinstance(data['data'], list):
                df = pd.DataFrame(data['data'])
                print(f"[INFO] 从缓存加载数据，缓存时间: {data.get('timestamp', '未知')}")
                return df
                
        except Exception as e:
            print(f"[WARN] 缓存数据加载失败: {e}")
            
        return None
    
    def _save_to_cache(self, cache_file: Path, data: List[Dict[str, Any]]):
        """保存数据到缓存"""
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
            print(f"[INFO] 数据已缓存到: {cache_file}")
            
        except Exception as e:
            print(f"[WARN] 缓存保存失败: {e}")
    
    def _fetch_roe_data(self, stock_codes: List[str]) -> Dict[str, Any]:
        """
        获取ROE数据（预留端口）
        
        TODO(未来扩展): 理杏仁API的财务指标端点需要单独的API密钥或权限
        未来可以通过以下方式扩展：
        1. 调用理杏仁财务报表端点：/cn/company/fundamental/financial
        2. 使用AKShare财务指标接口：ak.stock_financial_analysis_indicator()
        3. 集成其他数据源（如东方财富、同花顺等）
        
        当前暂时返回空字典，ROE字段将保持为None
        """
        # 预留：未来可扩展ROE数据获取逻辑
        # 目前理杏仁API的非金融端点不支持ROE等财务指标
        # 财务指标端点需要单独的API访问权限
        return {}
    
    def _fetch_batch_data(self, stock_codes: List[str]) -> Optional[pd.DataFrame]:
        """批量获取理杏仁估值数据"""
        if not self.token:
            print("[ERROR] 未配置LIXINGER_TOKEN，无法调用理杏仁API")
            return None
            
        if not stock_codes:
            print("[WARN] 股票代码列表为空")
            return None
            
        # 检查缓存
        cache_file = self._get_cache_file(stock_codes)
        if self._is_cache_valid(cache_file):
            cached_data = self._load_from_cache(cache_file)
            if cached_data is not None:
                return cached_data
        
        # 准备API请求 - 使用正确的估值数据端点
        url = f"{self.base_url}/cn/company/fundamental/non_financial"
        headers = {
            "Content-Type": "application/json"
        }
        
        # 计算昨天的日期（确保有数据）
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        payload = {
            "token": self.token,
            "date": yesterday,
            "stockCodes": stock_codes,
            "metricsList": [
                "pe_ttm",           # 市盈率(TTM)
                "pb",               # 市净率 
                "ps_ttm",           # 市销率(TTM)
                "dyr",              # 股息率
                "pe_ttm.y10.cvpos"  # 市盈率历史分位数
            ]
        }
        
        try:
            print(f"[INFO] 调用理杏仁API获取 {len(stock_codes)} 只股票基本面数据...")
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # 理杏仁API返回code=1表示成功
                if data.get("code") == 1 and "data" in data:
                    # 处理API返回的估值数据
                    processed_data = []
                    
                    for item in data["data"]:
                        stock_data = {
                            "代码": item.get("stockCode", ""),
                            "PE(TTM)": item.get("pe_ttm"),
                            "PB": item.get("pb"),
                            "PS(TTM)": item.get("ps_ttm"),
                            "股息率": item.get("dyr"),
                            "PE历史分位数": item.get("pe_ttm.y10.cvpos")
                        }
                        processed_data.append(stock_data)
                    
                    df = pd.DataFrame(processed_data)
                    
                    # 尝试获取ROE数据（预留端口，当前返回空）
                    roe_data = self._fetch_roe_data(stock_codes)
                    if roe_data:
                        # 将ROE数据合并到DataFrame
                        df["ROE(年度)"] = df["代码"].map(roe_data)
                    else:
                        # 添加ROE字段但设为None，保持数据结构一致性
                        df["ROE(年度)"] = None
                    
                    # 保存到缓存
                    self._save_to_cache(cache_file, processed_data)
                    
                    print(f"[SUCCESS] 理杏仁API成功获取 {len(df)} 只股票估值数据")
                    return df
                    
                else:
                    error_msg = data.get("message", "未知错误")
                    print(f"[ERROR] 理杏仁API返回错误: {error_msg}")
                    print(f"        错误详情: {data}")
                    
            else:
                print(f"[ERROR] 理杏仁API请求失败，状态码: {response.status_code}")
                try:
                    error_detail = response.text
                    print(f"        错误详情: {error_detail[:200]}")
                except:
                    pass
                
        except requests.exceptions.Timeout:
            print("[ERROR] 理杏仁API请求超时")
        except requests.exceptions.ConnectionError:
            print("[ERROR] 网络连接失败，无法访问理杏仁API")
        except Exception as e:
            print(f"[ERROR] 理杏仁API调用异常: {e}")
            
        return None
    
    def get_fundamentals(self, stock_codes: List[str]) -> pd.DataFrame:
        """获取基本面数据（支持批量处理）"""
        if not stock_codes:
            return pd.DataFrame()
            
        # 分批处理（理杏仁API限制最多100只股票）
        batch_size = 100
        all_data = []
        
        for i in range(0, len(stock_codes), batch_size):
            batch_codes = stock_codes[i:i + batch_size]
            
            # 尝试获取数据
            batch_data = self._fetch_batch_data(batch_codes)
            
            if batch_data is not None and not batch_data.empty:
                all_data.append(batch_data)
            else:
                print(f"[WARN] 批量 {i//batch_size + 1} 数据获取失败")
            
            # API限流控制
            if i + batch_size < len(stock_codes):
                time.sleep(1)  # 1秒间隔
        
        # 合并所有批次数据
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        else:
            print("[WARN] 所有批次数据获取均失败，返回空DataFrame")
            return pd.DataFrame()


class DummyDataProvider:
    """模拟数据提供者（备用方案）"""
    
    def __init__(self):
        self.dummy_data = self._build_dummy_data()
    
    def _build_dummy_data(self) -> pd.DataFrame:
        """构建模拟数据"""
        data = [
            {"代码": "000001", "PE(TTM)": 8.5, "PB": 0.9, "PS(TTM)": 1.2, "股息率": 3.2, "总市值": 2800, "PE历史分位数": 0.25, "ROE(年度)": 12.5},
            {"代码": "600519", "PE(TTM)": 28.0, "PB": 6.5, "PS(TTM)": 12.5, "股息率": 0.8, "总市值": 22000, "PE历史分位数": 0.75, "ROE(年度)": 25.8},
            {"代码": "300750", "PE(TTM)": 35.0, "PB": 5.2, "PS(TTM)": 8.3, "股息率": 0.5, "总市值": 9800, "PE历史分位数": 0.65, "ROE(年度)": 18.2},
            {"代码": "601318", "PE(TTM)": 10.2, "PB": 1.2, "PS(TTM)": 0.8, "股息率": 2.8, "总市值": 8500, "PE历史分位数": 0.35, "ROE(年度)": 15.6},
            {"代码": "000858", "PE(TTM)": 25.5, "PB": 4.8, "PS(TTM)": 6.2, "股息率": 1.2, "总市值": 6800, "PE历史分位数": 0.60, "ROE(年度)": 20.3},
        ]
        return pd.DataFrame(data)
    
    def get_fundamentals(self, stock_codes: List[str]) -> pd.DataFrame:
        """获取模拟数据"""
        print("[INFO] 使用模拟数据（备用方案）")
        
        if not stock_codes:
            return self.dummy_data.copy()
        
        # 过滤出请求的股票代码
        filtered_data = []
        for code in stock_codes:
            stock_data = self.dummy_data[self.dummy_data["代码"] == code]
            if not stock_data.empty:
                filtered_data.append(stock_data.iloc[0].to_dict())
        
        if filtered_data:
            return pd.DataFrame(filtered_data)
        else:
            # 如果没有匹配的股票，返回所有模拟数据
            return self.dummy_data.copy()


def get_fundamental_provider():
    """获取数据提供者实例（主方案：理杏仁API，备选：模拟数据）"""
    token = os.getenv("LIXINGER_TOKEN")
    
    if token:
        print("[INFO] 使用理杏仁API作为主要数据源")
        return LixingerProvider(token)
    else:
        print("[WARN] 未配置LIXINGER_TOKEN，使用模拟数据")
        return DummyDataProvider()