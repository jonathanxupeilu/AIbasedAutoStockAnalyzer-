from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List
import sys
import os
import yaml
from openai import OpenAI

from screener import _fetch_eastmoney_a_spot
from lixinger_provider import get_fundamental_provider


def _load_analysis_framework() -> Dict[str, Any]:
    """加载分析框架配置文件"""
    config_path = Path(__file__).parent / "analysis_framework.yaml"
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        print(f"[WARN] 配置文件 {config_path} 不存在，使用默认框架")
        return _get_default_framework()
    except Exception as e:
        print(f"[ERROR] 加载配置文件失败: {e}")
        return _get_default_framework()

def _get_default_framework() -> Dict[str, Any]:
    """默认分析框架"""
    return {
        "analysis_framework": [
            {
                "question": "公司基本情况概述",
                "prompt": "请简要介绍该公司的基本情况，包括主营业务、行业地位等基本信息。"
            },
            {
                "question": "估值水平分析", 
                "prompt": "基于以下估值数据（PE：{pe}，PB：{pb}，股息率：{dividend_yield}），请分析该股票当前估值水平是否合理，并说明理由。"
            },
            {
                "question": "行业对比评估",
                "prompt": "将该股票的估值数据与同行业平均水平进行对比，分析其在行业中的相对估值位置和竞争优势。"
            },
            {
                "question": "投资价值分析",
                "prompt": "从估值角度评估该股票的投资价值，包括潜在收益空间和主要风险因素。"
            },
            {
                "question": "综合投资建议",
                "prompt": "基于以上分析，给出具体的投资建议（买入/持有/卖出）并说明理由，同时提供风险提示。"
            }
        ],
        "report_template": {
            "title": "{stock_name}({stock_code})投资分析报告",
            "disclaimer": "本报告由AI生成，仅供研究参考，不构成投资建议。投资有风险，决策需谨慎。",
            "sections": ["摘要", "公司概况", "估值分析", "投资价值评估", "投资建议"]
        }
    }

def _build_prompt(stock_code: str, stock_name: str, fundamentals: Dict[str, Any]) -> str:
    """构建AI分析提示词"""
    config = _load_analysis_framework()
    framework = config.get("analysis_framework", [])
    
    # 准备基础数据
    pe = fundamentals.get("PE(TTM)估算", "N/A")
    pb = fundamentals.get("PB", "N/A")
    dividend_yield = fundamentals.get("股息率", "N/A")
    market_cap = fundamentals.get("总市值", "N/A")
    market_cap_billion = fundamentals.get("总市值(亿)", "N/A")
    roe = fundamentals.get("ROE(TTM)", "N/A")
    
    lines = []
    lines.append("你是一个专业的股票分析师，请基于以下信息对股票进行深度分析。")
    lines.append("")
    lines.append(f"**股票信息**: {stock_name}({stock_code})")
    lines.append("")
    lines.append("**估值数据**:")
    if fundamentals:
        for key, value in fundamentals.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- 暂未成功获取估值指标数据")
    lines.append("")
    
    # 构建逐次分析问题
    lines.append("**请按以下框架进行深度分析**:")
    for i, item in enumerate(framework, 1):
        question = item["question"]
        prompt_template = item["prompt"]
        
        # 格式化提示词（支持更多变量）
        formatted_prompt = prompt_template.format(
            pe=pe, 
            pb=pb, 
            dividend_yield=dividend_yield,
            market_cap=market_cap,
            market_cap_billion=market_cap_billion,
            roe=roe,
            stock_code=stock_code, 
            stock_name=stock_name
        )
        lines.append(f"{i}. **{question}**: {formatted_prompt}")
    
    lines.append("")
    lines.append("**输出要求**:")
    lines.append("1. 使用Markdown格式，结构清晰")
    lines.append("2. 分析要深入、专业，基于数据给出有依据的判断")
    lines.append("3. 包含风险提示和免责声明")
    
    return "\n".join(lines)


def _load_env_config() -> Dict[str, str]:
    """加载.env配置文件"""
    config = {}
    env_path = Path(__file__).parent / ".env"
    
    if env_path.exists():
        try:
            with open(env_path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
        except Exception as e:
            print(f"[WARN] 读取.env文件失败: {e}")
    
    return config

def _call_deepseek_api(prompt: str, max_retries: int = 3) -> Optional[str]:
    """调用DeepSeek API进行智能分析"""
    
    # 优先从.env文件读取API密钥
    env_config = _load_env_config()
    api_key = env_config.get("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    
    if not api_key:
        print("[ERROR] 未找到DEEPSEEK_API_KEY配置，请检查.env文件或环境变量")
        print(f"[INFO] .env文件路径: {Path(__file__).parent / '.env'}")
        return None
    
    # 创建OpenAI客户端（DeepSeek兼容OpenAI API）
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="deepseek-reasoner",
                extra_body={"thinking": {"type": "enabled"}},
                messages=[
                    {
                        "role": "system", 
                        "content": "你是一名资深证券价值投资大师，擅长基本面分析和投资建议。请提供深入、专业的分析，基于数据给出有依据的判断。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                # max_tokens=4000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"[ERROR] 第{attempt + 1}次API调用失败: {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(2)  # 等待2秒后重试
            else:
                print("[ERROR] API调用达到最大重试次数")
                return None

def _format_report_content(ai_response: str, stock_code: str, stock_name: str) -> str:
    """格式化AI分析结果为完整的报告"""
    config = _load_analysis_framework()
    template = config.get("report_template", {})
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    lines = []
    
    # 报告标题
    title = template.get("title", "{stock_name}({stock_code})投资分析报告")
    lines.append(f"# {title.format(stock_name=stock_name, stock_code=stock_code)}")
    lines.append("")
    
    # AI分析内容
    lines.append(ai_response)
    lines.append("")
    
    # 免责声明
    disclaimer = template.get("disclaimer", "本报告由AI生成，仅供研究参考，不构成投资建议。投资有风险，决策需谨慎。")
    lines.append("---")
    lines.append(f"**{disclaimer}**")
    lines.append("")
    
    # 报告信息
    lines.append(f"**报告生成时间**: {now}")
    lines.append(f"**数据来源**: 东方财富实时行情数据")
    lines.append(f"**AI模型**: DeepSeek")
    
    return "\n".join(lines)


def _fetch_indicator_snapshot(stock_code: str) -> Dict[str, Any]:
    """获取单只股票的基本面数据（优先使用理杏仁API）"""
    result: Dict[str, Any] = {}
    
    # 方法1：尝试使用理杏仁API获取基本面数据
    try:
        provider = get_fundamental_provider()
        df_lixinger = provider.get_fundamentals([stock_code])
        
        if df_lixinger is not None and not df_lixinger.empty:
            if stock_code in df_lixinger["代码"].values:
                stock_data = df_lixinger[df_lixinger["代码"] == stock_code].iloc[0]
                
                # 处理理杏仁数据
                if "PE(TTM)" in stock_data and stock_data["PE(TTM)"] not in [None, ""]:
                    try:
                        result["PE(TTM)估算"] = round(float(stock_data["PE(TTM)"]), 4)
                    except Exception:
                        pass
                
                if "PB" in stock_data and stock_data["PB"] not in [None, ""]:
                    try:
                        result["PB"] = round(float(stock_data["PB"]), 4)
                    except Exception:
                        pass
                
                if "股息率" in stock_data and stock_data["股息率"] not in [None, ""]:
                    try:
                        result["股息率"] = round(float(stock_data["股息率"]) * 100, 2)  # 转换为百分比
                    except Exception:
                        pass
                
                if "总市值" in stock_data and stock_data["总市值"] not in [None, ""]:
                    try:
                        mv = float(stock_data["总市值"])
                        result["总市值"] = round(mv, 2)
                        result["总市值(亿)"] = round(mv / 1e8, 2)
                    except Exception:
                        pass
                
                if "ROE(TTM)" in stock_data and stock_data["ROE(TTM)"] not in [None, ""]:
                    try:
                        result["ROE(TTM)"] = round(float(stock_data["ROE(TTM)"]) * 100, 2)  # 转换为百分比
                    except Exception:
                        pass
                
                if result:
                    print(f"[SUCCESS] 理杏仁API成功获取 {stock_code} 基本面数据")
                    return result
                    
    except Exception as e:
        print(f"[WARN] 理杏仁API调用失败: {e}")
    
    # 方法2：尝试东方财富API（备用方案）
    try:
        df = _fetch_eastmoney_a_spot()
    except Exception as e:
        print(f"[WARN] 从东财获取行情失败: {e}", file=sys.stderr)
        return {}

    if df is None or df.empty:
        print("[WARN] 东财接口返回空数据", file=sys.stderr)
        return {}

    if "代码" not in df.columns:
        print(f"[WARN] 行情数据中缺少代码列, 可用列: {list(df.columns)}", file=sys.stderr)
        return {}

    sub = df[df["代码"] == stock_code]
    if sub.empty:
        print(f"[WARN] 行情数据中未找到代码 {stock_code}", file=sys.stderr)
        return {}

    row = sub.iloc[0]

    if "PE" in row and row["PE"] not in [None, ""]:
        try:
            result["PE(TTM)估算"] = round(float(row["PE"]), 4)
        except Exception:
            pass

    if "PB" in row and row["PB"] not in [None, ""]:
        try:
            result["PB"] = round(float(row["PB"]), 4)
        except Exception:
            pass

    if "总市值" in row and row["总市值"] not in [None, ""]:
        try:
            mv = float(row["总市值"])
            if mv > 1e8:
                result["总市值(亿)"] = round(mv / 1e8, 4)
            else:
                result["总市值"] = round(mv, 4)
        except Exception:
            pass

    return result


def _generate_report_content(stock_code: str, stock_name: str) -> str:
    """生成AI分析报告内容"""
    # 获取基本面数据
    fundamentals = _fetch_indicator_snapshot(stock_code)
    
    # 判断是否应该使用备用模板
    use_template = False
    
    # 检查是否获取到了有效的估值数据
    if not fundamentals:
        print("[INFO] 未获取到估值数据，启用备用模板模式")
        use_template = True
    else:
        # 检查是否有关键的估值指标
        key_metrics = ['PE(TTM)估算', 'PB']
        missing_metrics = [metric for metric in key_metrics if metric not in fundamentals or fundamentals[metric] == 'N/A']
        if len(missing_metrics) >= 1:  # 如果缺少至少1个关键指标
            print(f"[INFO] 缺少关键估值指标 {missing_metrics}，启用备用模板模式")
            use_template = True
        
        # 额外检查：如果使用的是模拟数据（特定股票代码和特定PE/PB值），也启用断点模式
        # 模拟数据包含：平安银行(PE=8.5, PB=0.9), 贵州茅台(PE=28.0, PB=6.5), 宁德时代(PE=35.0, PB=5.2)
        dummy_stocks = {
            '000001': {'PE': 8.5, 'PB': 0.9},
            '600519': {'PE': 28.0, 'PB': 6.5},
            '300750': {'PE': 35.0, 'PB': 5.2}
        }
        
        if stock_code in dummy_stocks:
            dummy_data = dummy_stocks[stock_code]
            # 检查当前获取的数据是否与模拟数据完全匹配
            if (fundamentals.get('PE(TTM)估算') == dummy_data['PE'] and 
                fundamentals.get('PB') == dummy_data['PB']):
                print(f"[INFO] 检测到使用模拟数据，启用断点模式")
                use_template = True
    
    # 构建AI分析提示词
    prompt = _build_prompt(stock_code, stock_name, fundamentals)
    
    if use_template:
        # 直接使用本地模板，跳过DeepSeek API调用
        print(f"[INFO] 数据获取不完整/模拟数据，跳过DeepSeek API调用，使用本地模板")
        now = datetime.now().strftime("%Y-%m-%d")
        ai_response = f"""
# 分析报告 - 本地模板（数据获取不完整/模拟数据模式）

由于未能获取到真实的股票估值数据或检测到使用模拟数据，系统自动启用本地模板模式以节约资源。

## 获取到的数据概览
- PE: {fundamentals.get('PE(TTM)估算', 'N/A')}
- PB: {fundamentals.get('PB', 'N/A')}
- 总市值: {fundamentals.get('总市值(亿)', fundamentals.get('总市值', 'N/A'))}亿

## 数据状态说明
当前数据获取状态：{'模拟数据模式' if stock_code in dummy_stocks else '不完整（缺少关键指标）' if fundamentals else '完全失败'}

## 分析框架
1. **估值水平分析**: 需要完整的真实估值数据才能进行准确分析
2. **投资价值**: 数据不足或为模拟数据，无法进行有效评估
3. **风险提示**: 数据获取风险、分析准确性风险

**注意**: 本报告为模板内容，建议检查网络连接和数据源稳定性后重新运行分析。
"""
    else:
        # 调用DeepSeek API进行智能分析
        print(f"[INFO] 数据获取完整，开始DeepSeek AI分析 {stock_name}({stock_code})...")
        ai_response = _call_deepseek_api(prompt)
        
        if ai_response is None:
            # API调用失败，使用本地模板作为备用方案
            print("[WARN] AI分析失败，使用本地模板")
            now = datetime.now().strftime("%Y-%m-%d")
            ai_response = f"""
# 分析报告 - 本地模板（AI服务不可用）

由于AI服务暂时不可用，以下是基于标准分析框架的模板：

## 估值数据概览
- PE: {fundamentals.get('PE(TTM)估算', 'N/A')}
- PB: {fundamentals.get('PB', 'N/A')}
- 总市值: {fundamentals.get('总市值(亿)', fundamentals.get('总市值', 'N/A'))}亿

## 分析框架
1. **估值水平分析**: 需要结合行业平均水平和公司成长性评估
2. **投资价值**: 基于当前估值水平判断投资吸引力
3. **风险提示**: 市场风险、行业风险、公司特有风险

**注意**: 本报告为模板内容，建议等待AI服务恢复后重新生成详细分析。
"""
    
    # 格式化报告内容
    content = _format_report_content(ai_response, stock_code, stock_name)
    return content


def analyze_stock(stock_code: str, stock_name: str, output_dir: str) -> Optional[Dict[str, Any]]:
    """分析单只股票并生成报告"""
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            # 创建输出目录
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # 生成安全的文件名
            safe_name = f"{stock_code}_{stock_name}".replace(" ", "_").replace("/", "_")
            path = Path(output_dir) / f"{safe_name}.md"
            
            # 生成报告内容
            print(f"[INFO] 生成 {stock_name}({stock_code}) 分析报告...")
            content = _generate_report_content(stock_code, stock_name)
            
            # 保存报告
            path.write_text(content, encoding="utf-8")
            print(f"[SUCCESS] 报告已保存: {path}")
            
            return {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "report_path": str(path),
            }
            
        except Exception as e:
            print(f"[ERROR] 第{attempt + 1}次分析失败: {e}")
            if attempt < max_retries - 1:
                import time
                print(f"[INFO] 等待3秒后重试...")
                time.sleep(3)
            else:
                print(f"[ERROR] {stock_name}({stock_code}) 分析失败，达到最大重试次数")
                return None
