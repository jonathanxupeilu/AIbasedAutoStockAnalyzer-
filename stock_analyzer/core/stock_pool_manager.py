from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
import pandas as pd


class StockPoolManager:
    """统一股票池管理器"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.stock_pool_file = data_dir / "stock_pool.md"
        self.watch_list_file = data_dir / "watch_list.yaml"
        self.quant_cache_file = data_dir / "quant_screened.json"
    
    def load_watch_list(self) -> List[Dict[str, Any]]:
        """加载自选股列表"""
        if not self.watch_list_file.exists():
            return []
        
        try:
            with open(self.watch_list_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            manual_stocks = config.get('manual_stocks', [])
            
            # 构建自选股数据结构
            watch_list = []
            for stock_code in manual_stocks:
                watch_list.append({
                    "代码": stock_code,
                    "名称": f"Stock-{stock_code}",  # 名称将在合并时从量化数据中获取
                    "type": "manual_selected"
                })
            
            return watch_list
        except Exception as e:
            print(f"[WARN] 加载自选股配置文件失败: {e}")
            return []
    
    def load_quant_cache(self) -> List[Dict[str, Any]]:
        """加载量化筛选缓存"""
        if not self.quant_cache_file.exists():
            return []
        
        try:
            df = pd.read_json(self.quant_cache_file)
            quant_stocks = df.to_dict('records')
            
            # 确保股票代码是字符串格式
            for stock in quant_stocks:
                stock["type"] = "quant_screened"
                if "代码" in stock:
                    stock["代码"] = str(stock["代码"]).zfill(6)  # 确保6位代码格式
            
            return quant_stocks
        except Exception as e:
            print(f"[WARN] 加载量化筛选缓存失败: {e}")
            return []
    
    def save_quant_cache(self, quant_stocks: pd.DataFrame) -> None:
        """保存量化筛选结果到缓存"""
        try:
            quant_stocks.to_json(self.quant_cache_file, orient='records', force_ascii=False)
        except Exception as e:
            print(f"[WARN] 保存量化筛选缓存失败: {e}")
    
    def merge_stock_pool(self, quant_stocks: List[Dict[str, Any]], 
                        manual_stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """合并股票池，处理去重逻辑（自选股优先）"""
        stock_map: Dict[str, Dict[str, Any]] = {}
        
        # 第一步：添加量化筛选结果（包含完整财务数据）
        for stock in quant_stocks:
            stock_code = stock["代码"]
            stock["type"] = "quant_screened"
            stock_map[stock_code] = stock
        
        # 第二步：用自选股覆盖量化筛选结果（自选股优先）
        for stock in manual_stocks:
            stock_code = stock["代码"]
            
            # 如果自选股在量化筛选中存在，则合并数据（保留量化数据，但使用自选股标签）
            if stock_code in stock_map:
                existing_stock = stock_map[stock_code]
                # 保留量化数据，但更新类型为自选股
                existing_stock["type"] = "manual_selected"
            else:
                # 纯自选股，使用股票代码作为名称占位符
                stock["type"] = "manual_selected"
                # 确保有名称字段
                if "名称" not in stock:
                    stock["名称"] = f"Stock-{stock_code}"
                stock_map[stock_code] = stock
        
        return list(stock_map.values())
    
    def _dataframe_to_markdown(self, df: pd.DataFrame) -> str:
        """将DataFrame转换为Markdown表格"""
        if df.empty:
            return "# 股票池\n\n暂无股票数据"
        
        # 确保DataFrame包含类型列
        if "type" not in df.columns:
            df = df.copy()
            df["type"] = "quant_screened"  # 默认类型
        
        # 重命名type列为中文"类型"
        df_renamed = df.rename(columns={"type": "类型"})
        
        # 重新排列列顺序：类型、代码、名称在前，然后是其他指标
        columns = ["类型", "代码", "名称"]
        other_cols = [col for col in df_renamed.columns if col not in columns]
        ordered_cols = columns + other_cols
        
        df_ordered = df_renamed[ordered_cols]
        
        headers = list(df_ordered.columns)
        lines = []
        lines.append("# 股票池")
        lines.append("")
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        
        for _, row in df_ordered.iterrows():
            values = [str(row[h]) for h in headers]
            lines.append("| " + " | ".join(values) + " |")
        
        lines.append("")
        lines.append("**类型说明:**")
        lines.append("- `quant_screened`: 量化筛选出的股票")
        lines.append("- `manual_selected`: 用户自选股")
        
        return "\n".join(lines)
    
    def save_stock_pool(self, stock_list: List[Dict[str, Any]]) -> None:
        """保存统一股票池到文件"""
        if not stock_list:
            return
        
        try:
            # 转换为DataFrame
            df = pd.DataFrame(stock_list)
            
            # 保存为Markdown格式
            markdown_content = self._dataframe_to_markdown(df)
            
            self.stock_pool_file.parent.mkdir(parents=True, exist_ok=True)
            self.stock_pool_file.write_text(markdown_content, encoding='utf-8')
            
            print(f"[SUCCESS] 股票池已保存到: {self.stock_pool_file}")
            print(f"[INFO] 当前股票池包含 {len(stock_list)} 只股票")
            
        except Exception as e:
            print(f"[ERROR] 保存股票池失败: {e}")
    
    def update_stock_pool(self, new_quant_stocks: pd.DataFrame) -> None:
        """更新股票池：合并新量化筛选结果和现有自选股"""
        # 保存量化筛选结果到缓存
        self.save_quant_cache(new_quant_stocks)
        
        # 加载现有数据
        quant_stocks = self.load_quant_cache()
        manual_stocks = self.load_watch_list()
        
        # 合并股票池（去重）
        merged_pool = self.merge_stock_pool(quant_stocks, manual_stocks)
        
        # 保存统一股票池
        self.save_stock_pool(merged_pool)
    
    def get_stock_pool(self) -> pd.DataFrame:
        """获取当前股票池"""
        if not self.stock_pool_file.exists():
            return pd.DataFrame()
        
        try:
            # 读取Markdown文件并解析为DataFrame
            content = self.stock_pool_file.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            # 找到表格开始位置
            table_start = -1
            for i, line in enumerate(lines):
                if line.startswith('|') and '---' in lines[i+1] if i+1 < len(lines) else False:
                    table_start = i
                    break
            
            if table_start == -1:
                return pd.DataFrame()
            
            # 解析表头
            header_line = lines[table_start]
            headers = [h.strip() for h in header_line.strip('|').split('|')]
            
            # 解析数据行
            data_rows = []
            for i in range(table_start + 2, len(lines)):
                line = lines[i].strip()
                if not line.startswith('|'):
                    break
                values = [v.strip() for v in line.strip('|').split('|')]
                if len(values) == len(headers):
                    data_rows.append(dict(zip(headers, values)))
            
            return pd.DataFrame(data_rows)
            
        except Exception as e:
            print(f"[WARN] 读取股票池文件失败: {e}")
            return pd.DataFrame()


def get_stock_pool_manager() -> StockPoolManager:
    """获取股票池管理器实例"""
    data_dir = Path(__file__).parent.parent.parent / "data"
    return StockPoolManager(data_dir)