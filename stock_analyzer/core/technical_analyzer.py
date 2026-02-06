from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from pathlib import Path
import json
import os
import requests
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

# 导入交易信号生成器
from .trading_signal_generator import TradingSignalGenerator


def safe_datetime_subtraction(dt1, dt2):
    """
    安全的datetime减法操作，处理时区不一致问题
    
    Args:
        dt1: 被减数datetime对象
        dt2: 减数datetime对象
        
    Returns:
        timedelta: 时间差
    """
    try:
        # 尝试直接减法
        return dt1 - dt2
    except TypeError as e:
        if "Cannot subtract tz-naive and tz-aware datetime-like objects" in str(e):
            # 时区不一致问题，统一去除时区信息
            if hasattr(dt1, 'tz') and dt1.tz is not None:
                dt1 = dt1.tz_localize(None)
            if hasattr(dt2, 'tz') and dt2.tz is not None:
                dt2 = dt2.tz_localize(None)
            return dt1 - dt2
        else:
            # 其他类型的错误，重新抛出
            raise e


class TechnicalAnalyzer:
    """技术指标分析器，集成technical-analyst技能进行专业分析"""
    
    def __init__(self, data_provider=None):
        """
        初始化技术分析器
        
        Args:
            data_provider: 数据提供器，用于获取K线数据
        """
        self.data_provider = data_provider
        self.analysis_cache = {}
        self.kline_cache = {}
        
        # 确保正确加载环境变量
        from dotenv import load_dotenv
        load_dotenv()
        self.token = os.getenv("LIXINGER_TOKEN")
        
        if not self.token:
            print("[WARN] LIXINGER_TOKEN未配置，技术分析将使用模拟数据")
        else:
            print(f"[INFO] LIXINGER_TOKEN已配置，将使用理杏仁API真实数据")
        
        self.base_url = "https://open.lixinger.com/api/cn/company/candlestick"
        self.cache_dir = Path(".cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        # 初始化交易信号生成器
        self.signal_generator = TradingSignalGenerator()
        print("[INFO] 交易信号生成器已初始化")
    
    def _get_kline_cache_file(self, stock_code: str) -> Path:
        """获取K线数据缓存文件路径"""
        return self.cache_dir / f"kline_{stock_code}.json"
    
    def _is_kline_cache_valid(self, cache_file: Path, max_age_hours: int = 24) -> bool:
        """检查K线缓存是否有效（增强版：同时检查缓存时间和数据新鲜度）"""
        if not cache_file.exists():
            return False
            
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 检查缓存时间戳
            timestamp_str = data.get('timestamp', '')
            if not timestamp_str:
                return False
                
            cache_time = datetime.fromisoformat(timestamp_str)
            now = datetime.now()
            
            # 缓存时间检查
            cache_age_hours = (now - cache_time).total_seconds() / 3600
            if cache_age_hours > max_age_hours:
                return False
            
            # 增强：检查数据本身的新鲜度
            if 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
                # 获取最新数据日期
                latest_record = data['data'][-1]
                if 'date' in latest_record:
                    try:
                        latest_date = pd.to_datetime(latest_record['date'])
                        current_date = pd.Timestamp.now().normalize()
                        
                        # 使用安全的时区处理函数计算数据新鲜度（天数差）
                        days_diff = safe_datetime_subtraction(current_date, latest_date.normalize()).days
                        
                        # 如果数据超过7天，视为不够新鲜
                        if days_diff > 7:
                            print(f"[INFO] 缓存数据不够新鲜，最新数据日期: {latest_date.strftime('%Y-%m-%d')}, 相差{days_diff}天")
                            return False
                            
                    except Exception as e:
                        print(f"[WARN] 数据新鲜度检查失败: {e}")
                        # 新鲜度检查失败时，仅依赖缓存时间检查
            
            return True
            
        except Exception:
            return False
    
    def _load_kline_from_cache(self, cache_file: Path) -> Optional[pd.DataFrame]:
        """从缓存加载K线数据（增强版：检查数据新鲜度）"""
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if 'data' in data and isinstance(data['data'], list):
                df = pd.DataFrame(data['data'])
                
                # 转换日期列为datetime类型
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                    
                    # 按时间降序排序（最新数据在前）
                    df.sort_index(ascending=False, inplace=True)
                
                    # 检查数据新鲜度
                    if not df.empty:
                        latest_date = df.index[0]  # 第一条数据是最新的
                        current_date = pd.Timestamp.now().normalize()
                        # 使用安全的时区处理函数计算数据新鲜度
                        days_diff = safe_datetime_subtraction(current_date, latest_date.normalize()).days
                    
                    cache_time = datetime.fromisoformat(data.get('timestamp', '')) if data.get('timestamp') else None
                    
                    print(f"[INFO] 从缓存加载K线数据，缓存时间: {cache_time.strftime('%Y-%m-%d %H:%M') if cache_time else '未知'}")
                    print(f"[INFO] 最新数据日期: {latest_date.strftime('%Y-%m-%d')}, 数据新鲜度: {days_diff}天前")
                    
                    return df
                
        except Exception as e:
            print(f"[WARN] K线缓存数据加载失败: {e}")
            
        return None
    
    def _ensure_cache_environment(self, cache_file: Path) -> bool:
        """
        确保缓存环境正常：目录、权限、空间等
        
        Args:
            cache_file: 缓存文件路径
            
        Returns:
            bool: 环境是否正常
        """
        try:
            # 确保缓存目录存在
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 检查目录写入权限
            test_file = cache_file.parent / "test_write.tmp"
            test_file.touch()
            test_file.unlink()
            
            # 检查磁盘空间（粗略估计）
            import shutil
            disk_usage = shutil.disk_usage(cache_file.parent)
            if disk_usage.free < 1024 * 1024 * 10:  # 小于10MB
                print(f"[WARN] 磁盘空间不足，剩余: {disk_usage.free // (1024*1024)}MB")
                return False
                
            return True
            
        except Exception as e:
            print(f"[ERROR] 缓存环境检查失败: {e}")
            return False
    
    def _save_kline_to_cache(self, cache_file: Path, data: List[Dict[str, Any]]):
        """保存K线数据到缓存（增强版：确保目录存在，处理序列化错误）"""
        try:
            # 检查缓存环境
            if not self._ensure_cache_environment(cache_file):
                print(f"[WARN] 缓存环境异常，跳过保存")
                return
            
            # 增强数据序列化：处理所有可能的数据类型
            serializable_data = []
            for record in data:
                serializable_record = {}
                for key, value in record.items():
                    try:
                        if hasattr(value, 'isoformat'):  # 处理Timestamp对象
                            serializable_record[key] = value.isoformat()
                        elif isinstance(value, (int, float, str, bool, type(None))):
                            serializable_record[key] = value
                        elif isinstance(value, (list, dict)):
                            # 递归处理嵌套结构
                            serializable_record[key] = json.dumps(value, ensure_ascii=False)
                        else:
                            # 其他类型转换为字符串
                            serializable_record[key] = str(value)
                    except Exception as e:
                        print(f"[WARN] 字段 {key} 序列化失败: {e}，跳过该字段")
                        serializable_record[key] = None
                serializable_data.append(serializable_record)
            
            # 创建缓存数据
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'data': serializable_data,
                'metadata': {
                    'stock_count': len(serializable_data),
                    'version': '1.0'
                }
            }
            
            # 原子性写入：先写入临时文件，再重命名
            temp_file = cache_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            # 原子性替换
            temp_file.replace(cache_file)
                
            print(f"[SUCCESS] K线数据已成功缓存到: {cache_file}")
            
        except Exception as e:
            print(f"[ERROR] K线缓存保存失败: {e}")
            # 清理临时文件
            temp_file = cache_file.with_suffix('.tmp')
            if temp_file.exists():
                temp_file.unlink()
    
    def _fetch_kline_from_lixinger(self, stock_code: str, limit: int = 52) -> Optional[pd.DataFrame]:
        """从理杏仁API获取K线数据"""
        if not self.token:
            print(f"[WARN] 未配置LIXINGER_TOKEN，无法调用理杏仁K线API")
            return None
            
        # 使用更短的周期获取最新数据（避免获取到过时的数据）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)  # 改为6个月数据，确保获取到最新
        
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "token": self.token,
            "stockCode": stock_code,
            "type": "lxr_fc_rights",  # 前复权
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
            "limit": limit
        }
        
        try:
            print(f"[INFO] 调用理杏仁K线API获取 {stock_code} 数据...")
            print(f"      请求参数: startDate={payload['startDate']}, endDate={payload['endDate']}")
            
            response = requests.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # 理杏仁API返回code=1表示成功
                if data.get("code") == 1 and "data" in data:
                    kline_data = data["data"]
                    print(f"[SUCCESS] 理杏仁K线API成功获取 {stock_code} 的 {len(kline_data)} 条K线数据")
                    
                    # 转换为DataFrame
                    df = pd.DataFrame(kline_data)
                    if not df.empty:
                        # 转换日期列为datetime类型
                        df['date'] = pd.to_datetime(df['date'])
                        df.set_index('date', inplace=True)
                        
                        # 按时间降序排序（最新数据在前）
                        df.sort_index(ascending=False, inplace=True)
                        
                        # 检查数据时间对齐情况
                        latest_date = df.index[0]  # 第一条是最新的
                        current_date = datetime.now().date()
                        
                        # 计算数据新鲜度
                        if hasattr(latest_date, 'date'):
                            # 确保时区一致
                            current_date = pd.Timestamp.now().normalize()
                            if latest_date.tz is not None:
                                current_date = current_date.tz_localize(latest_date.tz)
                            
                            days_diff = (current_date - latest_date.normalize()).days
                            if days_diff > 7:
                                print(f"[WARN] 数据可能不是最新的，最新数据日期: {latest_date.date()}，与当前日期相差{days_diff}天")
                            else:
                                print(f"[INFO] 数据时效性良好，最新数据日期: {latest_date.date()}")
                        
                        return df
                    
                else:
                    error_msg = data.get("message", "未知错误")
                    print(f"[ERROR] 理杏仁K线API返回错误: {error_msg}")
                    print(f"        错误详情: {data}")
                    
            else:
                print(f"[ERROR] 理杏仁K线API请求失败，状态码: {response.status_code}")
                try:
                    error_detail = response.text
                    print(f"        错误详情: {error_detail[:200]}")
                except:
                    pass
                
        except requests.exceptions.Timeout:
            print("[ERROR] 理杏仁K线API请求超时")
        except requests.exceptions.ConnectionError:
            print("[ERROR] 网络连接失败，无法访问理杏仁K线API")
        except Exception as e:
            print(f"[ERROR] 理杏仁K线API调用异常: {e}")
            
        return None
    
    def _fetch_kline_from_akshare(self, stock_code: str, period: str = "weekly", 
                                limit: int = 52) -> Optional[pd.DataFrame]:
        """从AKShare获取K线数据（备用数据源）"""
        try:
            import akshare as ak
            print(f"[INFO] 调用AKShare获取 {stock_code} 的{period}K线数据...")
            
            # 根据周期选择不同的AKShare接口
            if period == "daily":
                # 获取日线数据
                df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                      start_date=(pd.Timestamp.now() - pd.Timedelta(days=limit*2)).strftime('%Y%m%d'),
                                      adjust="qfq")  # 前复权
            elif period == "weekly":
                # 获取周线数据
                df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",  # 使用日线数据，然后聚合为周线
                                      start_date=(pd.Timestamp.now() - pd.Timedelta(days=limit*7*2)).strftime('%Y%m%d'),
                                      adjust="qfq")
                
                # 如果获取成功，将日线数据聚合为周线数据
                if df is not None and not df.empty:
                    # 重命名列
                    column_mapping = {
                        '日期': 'date',
                        '开盘': 'open', 
                        '最高': 'high',
                        '最低': 'low',
                        '收盘': 'close',
                        '成交量': 'volume'
                    }
                    
                    available_cols = [col for col in column_mapping.keys() if col in df.columns]
                    if available_cols:
                        df = df[available_cols].copy()
                        df = df.rename(columns=column_mapping)
                        df['date'] = pd.to_datetime(df['date'])
                        df.set_index('date', inplace=True)
                        
                        # 按周重新采样
                        df_weekly = df.resample('W').agg({
                            'open': 'first',
                            'high': 'max',
                            'low': 'min',
                            'close': 'last',
                            'volume': 'sum'
                        }).dropna()
                        
                        df = df_weekly.tail(limit)
                        
                        # 确保重采样后的数据没有时区信息
                        if df.index.tz is not None:
                            df.index = df.index.tz_localize(None)
                        
            elif period == "monthly":
                # 获取月线数据
                df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",  # 使用日线数据，然后聚合为月线
                                      start_date=(pd.Timestamp.now() - pd.Timedelta(days=limit*30*2)).strftime('%Y%m%d'),
                                      adjust="qfq")
                
                # 如果获取成功，将日线数据聚合为月线数据
                if df is not None and not df.empty:
                    # 重命名列
                    column_mapping = {
                        '日期': 'date',
                        '开盘': 'open', 
                        '最高': 'high',
                        '最低': 'low',
                        '收盘': 'close',
                        '成交量': 'volume'
                    }
                    
                    available_cols = [col for col in column_mapping.keys() if col in df.columns]
                    if available_cols:
                        df = df[available_cols].copy()
                        df = df.rename(columns=column_mapping)
                        df['date'] = pd.to_datetime(df['date'])
                        df.set_index('date', inplace=True)
                        
                        # 按月重新采样
                        df_monthly = df.resample('M').agg({
                            'open': 'first',
                            'high': 'max',
                            'low': 'min',
                            'close': 'last',
                            'volume': 'sum'
                        }).dropna()
                        
                        df = df_monthly.tail(limit)
                        
            else:
                print(f"[WARN] AKShare不支持 {period} 周期，使用日线数据")
                df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                      start_date=(pd.Timestamp.now() - pd.Timedelta(days=limit*2)).strftime('%Y%m%d'),
                                      adjust="qfq")
            
            if df is not None and not df.empty:
                # 重命名列以保持一致性
                column_mapping = {
                    '日期': 'date',
                    '开盘': 'open', 
                    '最高': 'high',
                    '最低': 'low',
                    '收盘': 'close',
                    '成交量': 'volume'
                }
                
                # 只保留需要的列
                available_cols = [col for col in column_mapping.keys() if col in df.columns]
                if available_cols:
                    df = df[available_cols].copy()
                    df = df.rename(columns=column_mapping)
                    
                    # 添加股票代码
                    df['stockCode'] = stock_code
                    
                    # 转换日期列为datetime类型
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                    
                    # 按时间降序排序（最新数据在前）
                    df.sort_index(ascending=False, inplace=True)
                    
                    # 限制数据条数（取最新的limit条）
                    df = df.head(limit)
                    
                    # 检查数据新鲜度
                    latest_date = df.index[0]  # 第一条是最新的
                    current_date = pd.Timestamp.now().normalize()
                    
                    # 确保时区一致
                    if latest_date.tz is not None:
                        current_date = current_date.tz_localize(latest_date.tz)
                    
                    days_diff = (current_date - latest_date.normalize()).days
                    
                    print(f"[SUCCESS] AKShare成功获取 {len(df)} 条{period}K线数据")
                    print(f"[INFO] 最新数据日期: {latest_date.strftime('%Y-%m-%d')}, 新鲜度: {days_diff}天前")
                    
                    return df
                
        except ImportError:
            print("[WARN] AKShare未安装，无法使用AKShare数据源")
        except Exception as e:
            print(f"[WARN] AKShare接口调用失败: {e}")
        
        return None
    
    def get_stock_kline_data(self, stock_code: str, period: str = "weekly", 
                           limit: int = 52) -> Optional[pd.DataFrame]:
        """
        获取股票的K线数据（智能多数据源策略）
        
        智能策略：
        1. 检查缓存有效性（包含数据新鲜度）
        2. 如果缓存数据不够新鲜，自动更新
        3. 多数据源优先级：理杏仁API > AKShare > 模拟数据
        
        Args:
            stock_code: 股票代码
            period: 周期，默认周线
            limit: 数据条数
            
        Returns:
            DataFrame包含K线数据，或None
        """
        cache_file = self._get_kline_cache_file(stock_code)
        
        # 检查缓存有效性（包含数据新鲜度检查）
        if cache_file.exists():
            cached_data = self._load_kline_from_cache(cache_file)
            if cached_data is not None:
                # 检查数据新鲜度
                latest_date = cached_data.index[0]  # 第一条数据是最新的
                current_date = pd.Timestamp.now().normalize()
                
                # 确保时区一致
                if latest_date.tz is not None:
                    current_date = current_date.tz_localize(latest_date.tz)
                
                days_diff = (current_date - latest_date.normalize()).days
                
                if days_diff <= 3:  # 缓存数据在3天内，视为足够新鲜
                    print(f"[INFO] 使用缓存数据（新鲜度良好: {days_diff}天前）")
                    return cached_data
                else:
                    print(f"[INFO] 缓存数据不够新鲜: {days_diff}天前，尝试更新...")
        
        # 智能数据源策略
        data_sources = [
            ("理杏仁API", self._fetch_kline_from_lixinger, stock_code, limit),
            ("AKShare", self._fetch_kline_from_akshare, stock_code, period, limit)
        ]
        
        best_data = None
        best_freshness = float('inf')  # 最小天数差
        
        for source_name, fetch_func, *args in data_sources:
            print(f"[INFO] 尝试数据源: {source_name}")
            
            try:
                kline_data = fetch_func(*args)
                
                if kline_data is not None and not kline_data.empty:
                    # 计算数据新鲜度
                    latest_date = kline_data.index[0]  # 第一条数据是最新的
                    current_date = pd.Timestamp.now().normalize()
                    days_diff = (current_date - latest_date.normalize()).days
                    
                    print(f"[INFO] {source_name} 数据新鲜度: {days_diff}天前")
                    
                    # 选择最新鲜的数据
                    if days_diff < best_freshness:
                        best_data = kline_data
                        best_freshness = days_diff
                        
                        # 如果数据足够新鲜，立即使用
                        if days_diff <= 1:  # 1天内的数据视为最优
                            print(f"[SUCCESS] 找到最优数据源: {source_name}（新鲜度: {days_diff}天前）")
                            break
                            
            except Exception as e:
                print(f"[WARN] {source_name} 调用失败: {e}")
                continue
        
        # 如果找到有效数据，保存到缓存
        if best_data is not None:
            print(f"[SUCCESS] 使用最佳数据源，新鲜度: {best_freshness}天前")
            cache_data = best_data.reset_index().to_dict('records')
            self._save_kline_to_cache(cache_file, cache_data)
            return best_data
        
        # 所有数据源都失败，使用模拟数据
        print(f"[WARN] 所有数据源失败，使用模拟数据作为降级方案")
        return self._get_simulated_kline_data(stock_code, period, limit)
    
    def _get_simulated_kline_data(self, stock_code: str, period: str = "weekly", 
                                limit: int = 52) -> pd.DataFrame:
        """
        生成模拟的K线数据（降级方案）
        
        Args:
            stock_code: 股票代码
            period: 周期
            limit: 数据条数
            
        Returns:
            模拟的K线数据DataFrame
        """
        print(f"[INFO] 生成 {stock_code} 的模拟{period}K线数据，{limit}条")
        
        # 生成模拟的周线数据
        # 使用'7D'频率确保生成准确的limit个日期
        dates = pd.date_range(end=datetime.now(), periods=limit, freq='7D')
        
        # 根据股票代码生成不同的模拟数据模式
        if stock_code.startswith('60'):  # 上证主板
            base_price = 10.0
            volatility = 0.3
        elif stock_code.startswith('00'):  # 深证主板
            base_price = 20.0
            volatility = 0.4
        elif stock_code.startswith('30'):  # 创业板
            base_price = 50.0
            volatility = 0.6
        else:  # 其他
            base_price = 15.0
            volatility = 0.5
            
        # 生成价格序列
        prices = []
        current_price = base_price
        
        for i in range(limit):
            change = (np.random.randn() * volatility) / 100
            current_price *= (1 + change)
            
            # 生成OHLC数据
            open_price = current_price * (1 + (np.random.randn() * 0.02))
            high = max(open_price, current_price) * (1 + abs(np.random.randn() * 0.03))
            low = min(open_price, current_price) * (1 - abs(np.random.randn() * 0.03))
            close = current_price
            volume = int(1e6 + np.random.randn() * 2e5)
            
            prices.append({
                'date': dates[i],
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume,
                'amount': volume * close,
                'change': change * 100,
                'stockCode': stock_code,
                'to_r': volume / 1e7  # 模拟换手率
            })
            
        df = pd.DataFrame(prices)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        # 确保模拟数据没有时区信息（与真实数据保持一致）
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        
        print(f"[INFO] 模拟数据生成完成，共 {len(df)} 条记录")
        return df
    
    def format_kline_data_for_analysis(self, kline_data: pd.DataFrame, 
                                     stock_code: str, stock_name: str) -> Dict[str, Any]:
        """
        格式化K线数据用于技术分析（增强版：包含数据时效性警告）
        
        Args:
            kline_data: K线数据DataFrame
            stock_code: 股票代码
            stock_name: 股票名称
            
        Returns:
            格式化后的技术分析数据（包含数据状态信息）
        """
        if kline_data is None or kline_data.empty:
            return {
                "error": "K线数据获取失败",
                "stock_code": stock_code,
                "stock_name": stock_name,
                "data_status": "error",
                "data_warning": "数据获取失败，请检查网络连接或数据源"
            }
            
        # 计算基本技术指标
        latest_data = kline_data.iloc[0]  # 第一行是最新的
        
        # 计算移动平均线
        ma5 = kline_data['close'].head(5).mean() if len(kline_data) >= 5 else None
        ma10 = kline_data['close'].head(10).mean() if len(kline_data) >= 10 else None
        ma20 = kline_data['close'].head(20).mean() if len(kline_data) >= 20 else None
        
        # 计算价格变化
        price_change_1w = None
        price_change_1m = None
        
        if len(kline_data) >= 2:
            try:
                price_change_1w = ((latest_data['close'] - kline_data.iloc[1]['close']) / kline_data.iloc[1]['close'] * 100)
            except (KeyError, IndexError):
                pass
                
        if len(kline_data) >= 5:
            try:
                price_change_1m = ((latest_data['close'] - kline_data.iloc[4]['close']) / kline_data.iloc[4]['close'] * 100)
            except (KeyError, IndexError):
                pass
        
        # 计算成交量变化
        volume_avg_5w = kline_data['volume'].head(5).mean() if len(kline_data) >= 5 else None
        
        # 数据源识别和状态评估
        data_source = "理杏仁API" if 'stockCode' in kline_data.columns else "AKShare" if 'stockCode' in kline_data.columns else "模拟数据"
        
        # 计算数据新鲜度
        latest_date = kline_data.index[0]  # 第一条数据是最新的
        current_date = pd.Timestamp.now().normalize()
        # 使用安全的时区处理函数计算数据新鲜度
        days_diff = safe_datetime_subtraction(current_date, latest_date.normalize()).days
        
        # 处理异常日期（未来日期）
        if days_diff < 0:
            # 数据日期在未来，可能是数据源问题或时区问题
            print(f"[WARN] 检测到异常日期：最新数据日期 {latest_date.strftime('%Y-%m-%d')} 晚于当前时间")
            days_diff = abs(days_diff)  # 使用绝对值计算
            data_source = "数据源异常"
        
        # 数据状态评估
        if data_source == "模拟数据":
            data_status = "simulated"
            data_warning = "使用模拟数据，分析结果仅供参考"
        elif data_source == "数据源异常":
            data_status = "warning"
            data_warning = f"数据日期异常（{days_diff}天后），建议检查数据源"
        elif days_diff <= 1:
            data_status = "excellent"
            data_warning = "数据时效性良好"
        elif days_diff <= 3:
            data_status = "good"
            data_warning = f"数据时效性一般（{days_diff}天前）"
        elif days_diff <= 7:
            data_status = "warning"
            data_warning = f"数据较旧，请谨慎参考（{days_diff}天前）"
        else:
            data_status = "critical"
            data_warning = f"数据过时，建议更新（{days_diff}天前）"
        
        # 格式化日期
        if hasattr(latest_date, 'strftime'):
            latest_date_str = latest_date.strftime('%Y-%m-%d')
        else:
            latest_date_str = str(latest_date)
        
        return {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "current_price": latest_data['close'],
            "price_change_1w": price_change_1w,
            "price_change_1m": price_change_1m,
            "moving_averages": {
                "ma5": ma5,
                "ma10": ma10,
                "ma20": ma20
            },
            "volume_analysis": {
                "current_volume": latest_data['volume'],
                "avg_volume_5w": volume_avg_5w
            },
            "data_period": f"{len(kline_data)}周",
            "latest_date": latest_date_str,
            "data_source": data_source,
            "data_freshness_days": days_diff,
            "data_status": data_status,
            "data_warning": data_warning,
            "is_real_data": data_source not in ["模拟数据"]
        }
    
    def generate_technical_prompt(
        self,
        technical_data: Dict[str, Any],
        signal_analysis_text: str = ""
    ) -> str:
        """
        生成技术分析提示词（增强版：包含数据状态信息和交易信号）
        
        Args:
            technical_data: 技术分析数据
            signal_analysis_text: 交易信号分析文本
            
        Returns:
            技术分析提示词（包含数据质量评估和交易信号）
        """
        if "error" in technical_data:
            return f"技术分析数据获取失败：{technical_data['error']}"
            
        # 数据状态标记
        data_status = technical_data.get('data_status', 'unknown')
        data_warning = technical_data.get('data_warning', '')
        data_freshness = technical_data.get('data_freshness_days', '未知')
        
        # 根据数据状态生成不同的提示语
        status_notes = {
            "excellent": "数据时效性良好，分析结果可靠",
            "good": "数据时效性一般，分析结果较为可靠", 
            "warning": "数据较旧，分析结果仅供参考，建议谨慎使用",
            "critical": "数据过时，分析结果可能不准确，强烈建议更新数据",
            "simulated": "使用模拟数据，分析结果仅供参考，不构成投资建议"
        }
        
        status_note = status_notes.get(data_status, "数据状态未知，请谨慎参考")
        
        prompt = f"""
请基于以下技术指标数据对股票 {technical_data['stock_name']}({technical_data['stock_code']}) 进行技术分析：

## 数据质量评估
- **数据来源**：{technical_data['data_source']}
- **数据状态**：{data_status.upper()}
- **数据新鲜度**：{data_freshness}天前
- **数据警告**：{data_warning}
- **分析建议**：{status_note}

## 当前价格信息
- 当前价格：{technical_data['current_price']:.2f}
- 周涨幅：{technical_data['price_change_1w']:.2f}%（如果可用）
- 月涨幅：{technical_data['price_change_1m']:.2f}%（如果可用）

## 移动平均线分析
- MA5：{technical_data['moving_averages']['ma5']:.2f}（如果可用）
- MA10：{technical_data['moving_averages']['ma10']:.2f}（如果可用）
- MA20：{technical_data['moving_averages']['ma20']:.2f}（如果可用）

## 成交量分析
- 当前成交量：{technical_data['volume_analysis']['current_volume']:,.0f}
- 5周平均成交量：{technical_data['volume_analysis']['avg_volume_5w']:,.0f}（如果可用）

## 数据概况
- 数据周期：{technical_data['data_period']}
- 最新数据日期：{technical_data['latest_date']}

{signal_analysis_text}

## 分析要求
请从以下维度进行专业分析，并在分析中考虑数据时效性：

1. **趋势分析**：判断当前趋势方向（上升、下降、震荡）及强度，说明数据时效性对趋势判断的影响
2. **支撑阻力位**：识别关键支撑位和阻力位，如果数据较旧，请说明这些位位的可靠性
3. **移动平均线关系**：分析价格与各均线的关系，说明数据时效性对均线分析的影响
4. **成交量配合**：分析量价关系是否健康
5. **技术形态**：识别可能的技术形态（头肩顶、双底等）
6. **买卖信号**：结合上面的量化交易信号分析，给出买卖建议，并明确说明数据时效性对信号可靠性的影响

## 特别说明
- 如果数据状态为"警告"或"临界"，请在分析中明确说明数据时效性问题
- 如果使用模拟数据，请明确说明这是模拟分析，实际投资需谨慎
- 如果数据不够新鲜，请给出基于当前数据的最佳分析，同时提醒用户关注最新市场动态
- 请高度重视量化交易信号的提示，这是基于7大技术指标综合分析的结果

请提供专业、客观的技术分析，并结合量化交易信号和数据时效性给出合理的分析和建议。
"""
        
        return prompt
    
    def analyze_stock_technical(self, stock_code: str, stock_name: str) -> Dict[str, Any]:
        """
        分析股票技术指标（增强版：B+C方案 - 模块化集成 + 智能降级）
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            
        Returns:
            技术分析结果，包含完整的降级机制
        """
        # 检查缓存
        cache_key = f"{stock_code}_{stock_name}"
        if cache_key in self.analysis_cache:
            print(f"[INFO] 从缓存加载{stock_name}({stock_code})的技术分析结果")
            return self.analysis_cache[cache_key]
            
        try:
            print(f"[INFO] 开始分析{stock_name}({stock_code})的技术指标...")
            
            # 获取K线数据（多级降级方案）
            kline_data = self._get_kline_data_with_fallback(stock_code)
            
            if kline_data is None or kline_data.empty:
                # 降级到模拟数据模式
                print(f"[WARN] {stock_name}({stock_code})的K线数据获取失败，使用模拟数据")
                return self._generate_fallback_technical_analysis(stock_code, stock_name)
            
            # 格式化技术数据
            technical_data = self.format_kline_data_for_analysis(kline_data, stock_code, stock_name)
            
            # 检查数据质量并决定集成级别
            data_quality = self._evaluate_data_quality(technical_data)
            print(f"[INFO] {stock_name}({stock_code})数据质量评估: {data_quality}")
            
            # 生成量化交易信号
            trading_signal = None
            signal_analysis_text = ""
            try:
                print(f"[INFO] 开始生成{stock_name}({stock_code})的量化交易信号...")
                trading_signal = self.signal_generator.generate_signal(kline_data, stock_code, stock_name)
                signal_analysis_text = self.signal_generator.format_signal_for_analysis(trading_signal)
                print(f"[SUCCESS] 量化交易信号生成完成：{trading_signal.signal.value}，置信度{trading_signal.confidence:.1f}%")
            except Exception as e:
                print(f"[WARN] 量化交易信号生成失败: {e}")
                signal_analysis_text = "量化交易信号生成失败，无法提供技术指标综合分析"
            
            # 根据数据质量生成不同深度的技术分析
            if data_quality in ['excellent', 'good']:
                # 高质量数据：完整分析（包含交易信号）
                technical_prompt = self.generate_technical_prompt(technical_data, signal_analysis_text)
            elif data_quality == 'warning':
                # 中等质量数据：基础分析
                technical_prompt = self._generate_basic_technical_prompt(technical_data, signal_analysis_text)
            else:
                # 低质量数据：降级分析
                technical_prompt = self._generate_degraded_technical_prompt(stock_name)
            
            result = {
                "technical_data": technical_data,
                "trading_signal": trading_signal.to_dict() if trading_signal else None,
                "signal_analysis_text": signal_analysis_text,
                "technical_prompt": technical_prompt,
                "analysis_timestamp": datetime.now().isoformat(),
                "status": "success",
                "data_quality": data_quality,
                "integration_level": self._determine_integration_level(data_quality, technical_data)
            }
            
            # 缓存结果（仅缓存成功的结果）
            self.analysis_cache[cache_key] = result
            print(f"[SUCCESS] {stock_name}({stock_code})技术分析完成，集成级别: {result['integration_level']}")
            return result
            
        except Exception as e:
            print(f"[ERROR] {stock_name}({stock_code})技术分析失败: {e}")
            # 返回完整的降级结果
            return self._generate_error_technical_analysis(stock_code, stock_name, str(e))
    
    def get_technical_analysis_summary(self, technical_analysis: Dict[str, Any]) -> str:
        """
        获取技术分析摘要
        
        Args:
            technical_analysis: 技术分析结果
            
        Returns:
            技术分析摘要文本
        """
        if technical_analysis["status"] == "error":
            return "技术分析数据获取失败"
            
        data = technical_analysis["technical_data"]
        
        summary = f"""
**技术指标概览**：
- 当前价格：{data['current_price']:.2f}
- 数据周期：{data['data_period']}（截至{data['latest_date']}）
"""
        
        if data.get('price_change_1w') is not None:
            summary += f"- 周涨幅：{data['price_change_1w']:.2f}%\n"
            
        if data.get('price_change_1m') is not None:
            summary += f"- 月涨幅：{data['price_change_1m']:.2f}%\n"
            
        return summary.strip()

    def _get_kline_data_with_fallback(self, stock_code: str) -> Optional[pd.DataFrame]:
        """
        获取K线数据（多级降级方案）
        
        Args:
            stock_code: 股票代码
            
        Returns:
            K线数据，失败时返回None
        """
        try:
            # 方法1：从缓存获取
            cache_file = self._get_kline_cache_file(stock_code)
            if cache_file.exists():
                cached_data = self._load_kline_from_cache(cache_file)
                if cached_data is not None:
                    print(f"[INFO] 从缓存加载{stock_code}的K线数据")
                    return cached_data
            
            # 方法2：从API获取
            print(f"[INFO] 尝试从API获取{stock_code}的K线数据...")
            api_data = self._fetch_kline_from_lixinger(stock_code, limit=52)
            if api_data is not None and not api_data.empty:
                print(f"[SUCCESS] API数据获取成功，数据条数: {len(api_data)}")
                
                # 保存到缓存
                if hasattr(api_data, 'to_dict'):
                    data_list = [{
                        'date': str(idx),
                        'open': row['open'] if 'open' in row else 0,
                        'high': row['high'] if 'high' in row else 0,
                        'low': row['low'] if 'low' in row else 0,
                        'close': row['close'] if 'close' in row else 0,
                        'volume': row['volume'] if 'volume' in row else 0,
                        'stockCode': stock_code
                    } for idx, row in api_data.iterrows()]
                    self._save_kline_to_cache(cache_file, data_list)
                
                return api_data
            
            # 方法3：降级到模拟数据
            print(f"[WARN] API数据获取失败，尝试生成模拟数据...")
            simulated_data = self._generate_simulated_kline_data(stock_code)
            if simulated_data is not None:
                print(f"[INFO] 模拟数据生成成功")
                return simulated_data
            
            return None
            
        except Exception as e:
            print(f"[ERROR] K线数据获取过程异常: {e}")
            return None

    def _evaluate_data_quality(self, technical_data: Dict[str, Any]) -> str:
        """
        评估数据质量
        
        Args:
            technical_data: 技术数据
            
        Returns:
            质量评级: 'excellent'/'good'/'warning'/'error'
        """
        try:
            # 检查数据源
            data_source = technical_data.get('data_source', '')
            if data_source == '模拟数据':
                return 'warning'
            
            # 检查数据状态
            data_status = technical_data.get('data_status', '')
            if data_status in ['excellent', 'good']:
                return data_status
            elif data_status == 'warning':
                return 'warning'
            
            # 检查数据新鲜度
            freshness_days = technical_data.get('data_freshness_days', 999)
            if freshness_days <= 3:
                return 'excellent'
            elif freshness_days <= 7:
                return 'good'
            elif freshness_days <= 30:
                return 'warning'
            else:
                return 'warning'
                
        except Exception:
            return 'error'

    def _determine_integration_level(self, data_quality: str, technical_data: Dict[str, Any]) -> str:
        """
        根据数据质量决定集成级别
        
        Args:
            data_quality: 数据质量评级
            technical_data: 技术数据
            
        Returns:
            集成级别: 'deep'/'moderate'/'basic'/'fallback'
        """
        if data_quality == 'error':
            return 'fallback'
        elif data_quality == 'excellent':
            return 'deep'
        elif data_quality == 'good':
            return 'moderate'
        elif data_quality == 'warning':
            return 'basic'
        else:
            return 'fallback'

    def _generate_basic_technical_prompt(
        self,
        technical_data: Dict[str, Any],
        signal_analysis_text: str = ""
    ) -> str:
        """生成基础技术分析提示词（中等质量数据）"""
        base_prompt = f"""
基于基础技术指标数据进行分析：
- 股票代码: {technical_data.get('stock_code', '未知')}
- 当前价格: {technical_data.get('current_price', 0):.2f}
- 数据新鲜度: {technical_data.get('data_freshness_days', 0)}天前
- 数据状态: {technical_data.get('data_status', '未知')}

技术分析要点：
1. 价格趋势分析
2. 成交量变化
3. 基础支撑阻力位
4. 简单技术指标评估

注意：数据质量有限，分析结果仅供参考。
"""
        
        if signal_analysis_text:
            base_prompt = f"{base_prompt}\n\n{signal_analysis_text}"
        
        return base_prompt

    def _generate_degraded_technical_prompt(self, stock_name: str) -> str:
        """生成降级技术分析提示词（低质量数据）"""
        return f"""
{stock_name}的技术分析数据获取受限，无法进行详细的技术指标分析。

建议：
1. 关注基本面分析
2. 等待数据源恢复正常后重新获取
3. 考虑使用其他技术分析工具

当前分析主要基于有限的模拟数据，分析结果仅供参考。
"""

    def _generate_fallback_technical_analysis(self, stock_code: str, stock_name: str) -> Dict[str, Any]:
        """生成降级技术分析结果"""
        return {
            "technical_data": {
                "error": "K线数据获取失败",
                "data_source": "模拟数据",
                "data_status": "simulated",
                "data_warning": "使用模拟数据，分析结果仅供参考",
                "current_price": 0.0,
                "latest_date": datetime.now().strftime("%Y-%m-%d"),
                "data_freshness_days": 999
            },
            "technical_prompt": self._generate_degraded_technical_prompt(stock_name),
            "analysis_timestamp": datetime.now().isoformat(),
            "status": "success",
            "data_quality": "warning",
            "integration_level": "fallback"
        }

    def _generate_error_technical_analysis(self, stock_code: str, stock_name: str, error_msg: str) -> Dict[str, Any]:
        """生成错误技术分析结果"""
        return {
            "technical_data": {
                "error": error_msg,
                "data_source": "错误数据",
                "data_status": "error",
                "data_warning": "技术分析过程出现异常"
            },
            "technical_prompt": f"技术分析失败：{error_msg}",
            "analysis_timestamp": datetime.now().isoformat(),
            "status": "error",
            "data_quality": "error",
            "integration_level": "fallback"
        }

    def _generate_simulated_kline_data(self, stock_code: str) -> Optional[pd.DataFrame]:
        """生成模拟K线数据（降级方案）"""
        try:
            # 生成一年的模拟周线数据
            dates = pd.date_range(end=datetime.now(), periods=52, freq='W')
            
            # 基础价格（基于股票代码生成随机价格）
            base_price = hash(stock_code) % 100 + 10  # 10-110之间的价格
            
            data = []
            for i, date in enumerate(dates):
                # 模拟价格波动
                volatility = 0.05  # 5%波动率
                
                if i == 0:
                    open_price = base_price
                else:
                    open_price = data[i-1]['close']
                
                # 模拟价格变动
                change = np.random.normal(0, volatility)
                close_price = open_price * (1 + change)
                high_price = max(open_price, close_price) * (1 + np.random.uniform(0, 0.02))
                low_price = min(open_price, close_price) * (1 - np.random.uniform(0, 0.02))
                volume = np.random.randint(100000, 1000000)
                
                data.append({
                    'date': date,
                    'open': round(open_price, 2),
                    'high': round(high_price, 2),
                    'low': round(low_price, 2),
                    'close': round(close_price, 2),
                    'volume': volume,
                    'stockCode': stock_code
                })
            
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            return df
            
        except Exception as e:
            print(f"[ERROR] 模拟数据生成失败: {e}")
            return None


def create_technical_analyzer() -> TechnicalAnalyzer:
    """创建技术分析器实例"""
    return TechnicalAnalyzer()