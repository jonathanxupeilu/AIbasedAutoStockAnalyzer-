from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import requests

from ..api.lixinger_provider import get_fundamental_provider
from .stock_pool_manager import get_stock_pool_manager


def _build_dummy_market_data() -> pd.DataFrame:
    """构建模拟数据（兼容旧接口）"""
    data = [
        {"代码": "000001", "名称": "平安银行", "PE": 8.5, "PB": 0.9},
        {"代码": "600519", "名称": "贵州茅台", "PE": 28.0, "PB": 6.5},
        {"代码": "300750", "名称": "宁德时代", "PE": 35.0, "PB": 5.2},
    ]
    return pd.DataFrame(data)


def _fetch_eastmoney_a_spot() -> pd.DataFrame:
    """获取东方财富A股实时数据（带代理检测和AKShare备用）"""
    import warnings
    
    # 方法1：尝试使用更健壮的AKShare接口
    try:
        import akshare as ak
        print("[INFO] 尝试使用AKShare获取股票数据...")
        
        # 获取A股实时行情数据
        df_ak = ak.stock_zh_a_spot_em()
        
        if df_ak is not None and not df_ak.empty:
            # 选择需要的列并重命名
            required_cols = ['代码', '名称', '市盈率-动态', '市净率', '总市值']
            available_cols = [col for col in required_cols if col in df_ak.columns]
            
            if available_cols:
                df_result = df_ak[available_cols].copy()
                
                # 重命名列以保持一致性
                column_mapping = {
                    '市盈率-动态': 'PE',
                    '市净率': 'PB',
                    '总市值': '总市值'
                }
                df_result = df_result.rename(columns=column_mapping)
                
                # 清理数据
                df_result = df_result.dropna(subset=['代码', '名称'])
                
                if not df_result.empty:
                    print(f"[SUCCESS] AKShare成功获取 {len(df_result)} 只股票数据")
                    return df_result
                
    except Exception as e:
        print(f"[WARN] AKShare接口调用失败: {e}")
    
    # 方法2：尝试东方财富API（绕过代理）
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": "1",
        "pz": "100",  # 进一步减少数据量
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2",
        "invt": "2",
        "fid": "f3",
        "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23",
        "fields": "f12,f14,f9,f23,f20",
    }
    
    headers = {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://quote.eastmoney.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        # 尝试不设置代理，让系统自动选择
        resp = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10,
            verify=False  # 禁用SSL验证，减少代理问题
        )
        resp.raise_for_status()
        data = resp.json()
        
        if data and "data" in data and "diff" in data["data"]:
            items = data["data"]["diff"]
            rows = []
            
            for item in items:
                code = item.get("f12")
                name = item.get("f14")
                if code and name:
                    row = {"代码": code, "名称": name}
                    
                    pe_dyn = item.get("f9")
                    if pe_dyn and pe_dyn != "":
                        try:
                            row["PE"] = float(pe_dyn)
                        except:
                            pass
                            
                    pb = item.get("f23")
                    if pb and pb != "":
                        try:
                            row["PB"] = float(pb)
                        except:
                            pass
                            
                    total_mv = item.get("f20")
                    if total_mv and total_mv != "":
                        try:
                            row["总市值"] = float(total_mv)
                        except:
                            pass
                            
                    rows.append(row)
            
            if rows:
                df = pd.DataFrame(rows)
                print(f"[SUCCESS] 东方财富API成功获取 {len(df)} 只股票数据")
                return df
                
    except Exception as e:
        print(f"[WARN] 东方财富API调用失败: {e}")
    
    # 方法3：返回模拟数据作为最后手段
    print("[INFO] 使用模拟数据作为备用方案")
    return _build_dummy_market_data()


def _load_market_data() -> pd.DataFrame:
    """加载市场数据（优先使用理杏仁API）"""
    
    # 方法1：尝试使用理杏仁API获取基本面数据
    try:
        provider = get_fundamental_provider()
        
        # 获取所有股票数据（理杏仁API会返回所有可用的股票）
        df_lixinger = provider.get_fundamentals([])
        
        if df_lixinger is not None and not df_lixinger.empty:
            # 重命名列以保持兼容性
            column_mapping = {}
            if "PE(TTM)" in df_lixinger.columns:
                column_mapping["PE(TTM)"] = "PE"
            
            df_lixinger = df_lixinger.rename(columns=column_mapping)
            
            # 选择需要的列
            wanted = [c for c in ["代码", "名称", "PE", "PB"] if c in df_lixinger.columns]
            if wanted:
                df_result = df_lixinger[wanted].copy()
                df_result = df_result.dropna(subset=["代码", "名称"])
                
                if not df_result.empty:
                    print(f"[SUCCESS] 理杏仁API成功获取 {len(df_result)} 只股票数据")
                    return df_result
                    
    except Exception as e:
        print(f"[WARN] 理杏仁API调用失败: {e}")
    
    # 方法2：尝试东方财富API（备用方案）
    df_eastmoney = _fetch_eastmoney_a_spot()
    if df_eastmoney is not None and not df_eastmoney.empty:
        wanted = [c for c in ["代码", "名称", "PE", "PB"] if c in df_eastmoney.columns]
        if wanted:
            df_result = df_eastmoney[wanted].copy()
            df_result = df_result.dropna(subset=["代码", "名称"])
            
            if not df_result.empty:
                print(f"[SUCCESS] 东方财富API成功获取 {len(df_result)} 只股票数据")
                return df_result
    
    # 方法3：返回模拟数据作为最后手段
    print("[INFO] 使用模拟数据作为最终备用方案")
    return _build_dummy_market_data()


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    if "代码" not in df.columns:
        if "symbol" in df.columns:
            df["代码"] = df["symbol"]
        elif "code" in df.columns:
            df["代码"] = df["code"]

    if "名称" not in df.columns:
        if "name" in df.columns:
            df["名称"] = df["name"]

    return df


def _apply_screening(df: pd.DataFrame, criteria: Dict[str, Any]) -> pd.DataFrame:
    result = df.copy()

    pe_max = criteria.get("pe_max")
    if pe_max is not None:
        if "PE" in result.columns:
            result = result[result["PE"] <= pe_max]
        elif "pe_ttm" in result.columns:
            result = result[result["pe_ttm"] <= pe_max]

    pb_max = criteria.get("pb_max")
    if pb_max is not None:
        if "PB" in result.columns:
            result = result[result["PB"] <= pb_max]
        elif "pb" in result.columns:
            result = result[result["pb"] <= pb_max]

    return result.reset_index(drop=True)


def _dataframe_to_markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return "暂无符合条件的股票"

    headers = list(df.columns)
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for _, row in df.iterrows():
        values = [str(row[h]) for h in headers]
        lines.append("| " + " | ".join(values) + " |")

    return "\n".join(lines)


def _save_candidate_markdown(df: pd.DataFrame, path: str) -> None:
    markdown = _dataframe_to_markdown(df)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(markdown, encoding="utf-8")


def run_screener(criteria: Dict[str, Any], candidate_output_path: str) -> pd.DataFrame:
    df = _load_market_data()
    df = _normalize_columns(df)
    screened = _apply_screening(df, criteria)
    
    # 保存到传统候选池文件（保持兼容性）
    _save_candidate_markdown(screened, candidate_output_path)
    
    # 更新统一股票池
    stock_pool_manager = get_stock_pool_manager()
    stock_pool_manager.update_stock_pool(screened)
    
    return screened
