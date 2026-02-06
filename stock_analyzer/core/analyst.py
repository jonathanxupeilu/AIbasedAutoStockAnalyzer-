from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List
import sys
import os
import yaml
from openai import OpenAI

from .screener import _fetch_eastmoney_a_spot
from ..api.lixinger_provider import get_fundamental_provider
from ..utils.news_formatter import StockNewsFormatter
from .technical_analyzer import TechnicalAnalyzer


def _load_analysis_framework() -> Dict[str, Any]:
    """加载分析框架配置文件"""
    config_path = Path(__file__).parent.parent.parent / "config" / "analysis_framework.yaml"
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
    lines.append("你是一个资深价值投资大师，请基于以下信息对公司基本面进行深度分析。")
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

def _call_deepseek_api_single_question(question_prompt: str, conversation_history: List[Dict] = None, max_retries: int = 3) -> Optional[str]:
    """调用DeepSeek API进行单问题智能分析"""
    
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
    
    # 构建消息历史
    messages = [
        {
            "role": "system", 
            "content": "你是一名资深证券价值投资大师，擅长基本面分析和投资建议。请提供深入、专业的分析，基于数据给出有依据的判断。"
        }
    ]
    
    # 添加对话历史（如果有）
    if conversation_history:
        messages.extend(conversation_history)
    
    # 添加当前问题
    messages.append({
        "role": "user",
        "content": question_prompt
    })
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="deepseek-reasoner",
                extra_body={"thinking": {"type": "enabled"}},
                messages=messages,
                temperature=0.7,
                # max_tokens=2000  # 每个问题限制token数
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


def _call_deepseek_api(prompt: str, max_retries: int = 3) -> Optional[str]:
    """调用DeepSeek API进行智能分析（兼容旧版本）"""
    return _call_deepseek_api_single_question(prompt, None, max_retries)

def _generate_analysis_sequentially(stock_code: str, stock_name: str, fundamentals: Dict[str, Any]) -> Optional[str]:
    """使用逐次提问方式生成AI分析报告（集成新闻数据）"""
    config = _load_analysis_framework()
    framework = config.get("analysis_framework", [])
    
    # 准备基础数据
    pe = fundamentals.get("PE(TTM)估算", "N/A")
    pb = fundamentals.get("PB", "N/A")
    dividend_yield = fundamentals.get("股息率", "N/A")
    market_cap = fundamentals.get("总市值", "N/A")
    market_cap_billion = fundamentals.get("总市值(亿)", "N/A")
    roe = fundamentals.get("ROE(TTM)", "N/A")
    
    # 初始化新闻格式化器和技术分析器
    news_formatter = StockNewsFormatter()
    technical_analyzer = TechnicalAnalyzer()
    
    # 安全获取技术分析数据（采用B+C方案：模块化集成 + 智能降级）
    print(f"[INFO] 正在获取{stock_name}的技术指标数据...")
    technical_data = _get_enhanced_technical_analysis(technical_analyzer, stock_code, stock_name)
    
    # 根据技术分析质量决定集成深度
    integration_level = _determine_integration_level(technical_data)
    print(f"[INFO] 技术分析集成级别：{integration_level}")
    
    # 构建股票基本信息提示词
    stock_info_prompt = f"""
股票基本信息：
- 股票名称：{stock_name}
- 股票代码：{stock_code}
- 估值数据：
"""
    
    if fundamentals:
        for key, value in fundamentals.items():
            stock_info_prompt += f"  - {key}: {value}\n"
    else:
        stock_info_prompt += "  - 暂未成功获取估值指标数据\n"
    
    # 添加技术分析摘要（根据集成级别智能调整）
    technical_summary = _get_technical_summary_for_integration(technical_data, integration_level)
    stock_info_prompt += f"\n- 技术指标概览：\n{technical_summary}"
    
    # 对话历史记录
    conversation_history = []
    
    # 添加股票基本信息到对话历史
    conversation_history.append({
        "role": "user",
        "content": stock_info_prompt
    })
    
    # 逐次处理每个分析问题
    analysis_results = []
    
    for i, item in enumerate(framework, 1):
        question = item["question"]
        prompt_template = item["prompt"]
        
        # 检查是否为技术指标分析步骤
        if question == "技术指标分析":
            print(f"[INFO] 正在准备{stock_name}的技术指标分析数据...")
            
            # 根据集成级别智能调整技术分析数据
            technical_prompt = _get_technical_prompt_for_analysis(technical_data, integration_level)
            
            # 格式化提示词，包含技术分析数据
            formatted_prompt = prompt_template.format(
                pe=pe, 
                pb=pb, 
                dividend_yield=dividend_yield,
                market_cap=market_cap,
                market_cap_billion=market_cap_billion,
                roe=roe,
                stock_code=stock_code, 
                stock_name=stock_name,
                technical_analysis=technical_prompt
            )
        # 检查是否为综合投资建议步骤，如果是则添加新闻数据和技术分析结论
        elif question == "综合投资建议":
            print(f"[INFO] 正在获取{stock_name}的最新新闻数据...")
            news_data = news_formatter.format_news_for_analysis(stock_code, stock_name)
            news_summary = news_formatter.get_news_summary(stock_code, stock_name)
            
            print(f"[INFO] 成功获取到 {news_summary['news_count']} 条新闻")
            if news_summary['latest_news_time']:
                print(f"[INFO] 最新新闻时间: {news_summary['latest_news_time']}")
            
            # 根据集成级别获取技术分析结论摘要
            technical_conclusion = _get_technical_conclusion_for_investment(technical_data, integration_level)
            
            # 格式化提示词，包含新闻数据和技术分析结论
            formatted_prompt = prompt_template.format(
                pe=pe, 
                pb=pb, 
                dividend_yield=dividend_yield,
                market_cap=market_cap,
                market_cap_billion=market_cap_billion,
                roe=roe,
                stock_code=stock_code, 
                stock_name=stock_name,
                news_data=news_data,
                technical_conclusion=technical_conclusion
            )
        else:
            # 其他步骤使用标准格式化
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
        
        print(f"[INFO] 正在分析第{i}/{len(framework)}个问题: {question}")
        
        # 调用API获取单个问题的分析结果
        response = _call_deepseek_api_single_question(formatted_prompt, conversation_history)
        
        if response is None:
            print(f"[ERROR] 第{i}个问题分析失败，跳过该问题")
            analysis_results.append(f"### {question}\n\n*分析失败，请重试*\n")
            continue
        
        # 将问题和分析结果添加到对话历史
        conversation_history.append({
            "role": "user",
            "content": formatted_prompt
        })
        conversation_history.append({
            "role": "assistant",
            "content": response
        })
        
        # 将分析结果添加到结果列表
        analysis_results.append(f"### {question}\n\n{response}\n")
        
        # 添加延迟，避免API调用过于频繁
        import time
        time.sleep(1)
    
    # 组合所有分析结果
    if analysis_results:
        combined_analysis = f"# {stock_name}({stock_code})投资分析报告\n\n"
        combined_analysis += "## 综合分析结果\n\n"
        combined_analysis += "\n".join(analysis_results)
        
        # 添加新闻数据摘要
        news_summary = news_formatter.get_news_summary(stock_code, stock_name)
        if news_summary['news_count'] > 0:
            combined_analysis += f"\n## 新闻数据摘要\n\n"
            combined_analysis += f"- **新闻数量**: {news_summary['news_count']}条\n"
            combined_analysis += f"- **最新新闻时间**: {news_summary['latest_news_time'] or '未知'}\n"
            combined_analysis += f"- **新闻来源**: {', '.join(news_summary['sources'])}\n"
            if news_summary['keywords']:
                combined_analysis += f"- **关键词**: {', '.join(news_summary['keywords'][:5])}\n"
        
        return combined_analysis
    else:
        return None


def _format_report_content(ai_response: str, stock_code: str, stock_name: str) -> str:
    """格式化AI分析结果为完整的报告（增强版：提取并显示交易信号）"""
    config = _load_analysis_framework()
    template = config.get("report_template", {})
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    lines = []
    
    # 报告标题
    title = template.get("title", "{stock_name}({stock_code})投资分析报告")
    lines.append(f"# {title.format(stock_name=stock_name, stock_code=stock_code)}")
    lines.append("")
    
    # 尝试提取量化交易信号（从AI响应中）
    trading_signal_section = _extract_trading_signal_section(ai_response)
    if trading_signal_section:
        lines.append(trading_signal_section)
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
    lines.append(f"**数据来源**: 东方财富实时行情数据 + 理杏仁API")
    lines.append(f"**AI模型**: DeepSeek")
    lines.append(f"**技术分析**: 7大技术指标综合分析（RSI/MACD/布林带/趋势/成交量/随机指标/ADX）")
    
    return "\n".join(lines)


def _extract_trading_signal_section(ai_response: str) -> Optional[str]:
    """
    从AI响应中提取量化交易信号章节
    
    Args:
        ai_response: AI分析响应文本
        
    Returns:
        提取的交易信号章节，如果不存在则返回None
    """
    # 检查是否包含量化交易信号章节
    signal_markers = [
        "## 量化交易信号分析",
        "【量化交易信号】",
        "量化信号："
    ]
    
    has_signal = any(marker in ai_response for marker in signal_markers)
    
    if not has_signal:
        return None
    
    # 如果AI响应中已经有格式化的交易信号章节，提取它
    if "## 量化交易信号分析" in ai_response:
        lines = ai_response.split('\n')
        signal_lines = []
        in_signal_section = False
        
        for line in lines:
            if "## 量化交易信号分析" in line:
                in_signal_section = True
                signal_lines.append(line)
            elif in_signal_section:
                if line.startswith("## ") and "## 量化交易信号分析" not in line:
                    break
                signal_lines.append(line)
        
        if signal_lines:
            return '\n'.join(signal_lines)
    
    # 否则，尝试提取信号信息并格式化
    signal_info = []
    
    # 尝试提取综合信号
    if "综合信号" in ai_response:
        for line in ai_response.split('\n'):
            if "综合信号" in line:
                signal_info.append(line.strip())
            if len(signal_info) >= 2:  # 提取综合信号和置信度
                break
    
    # 尝试提取风险管理建议
    if "风险管理建议" in ai_response:
        in_risk_section = False
        for line in ai_response.split('\n'):
            if "风险管理建议" in line:
                in_risk_section = True
            elif in_risk_section:
                if line.startswith("-") or line.startswith("*"):
                    signal_info.append(line.strip())
                elif not line.strip():
                    continue
                else:
                    break
            if len(signal_info) >= 6:  # 限制提取的行数
                break
    
    if signal_info:
        return "## 量化交易信号摘要\n" + "\n".join(signal_info)
    
    return None


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
        # 使用逐次提问的方式进行DeepSeek AI分析
        print(f"[INFO] 数据获取完整，开始DeepSeek AI逐次分析 {stock_name}({stock_code})...")
        ai_response = _generate_analysis_sequentially(stock_code, stock_name, fundamentals)
        
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


def _get_enhanced_technical_analysis(technical_analyzer, stock_code: str, stock_name: str) -> Dict[str, Any]:
    """
    增强版技术分析数据获取（B+C方案：模块化集成 + 智能降级）
    
    Args:
        technical_analyzer: 技术分析器实例
        stock_code: 股票代码
        stock_name: 股票名称
        
    Returns:
        Dict: 包含技术分析数据、状态和元数据的字典
    """
    try:
        print(f"[INFO] 开始获取{stock_name}({stock_code})的技术分析数据...")
        
        # 获取基础技术分析
        technical_analysis = technical_analyzer.analyze_stock_technical(stock_code, stock_name)
        
        # 获取技术分析摘要
        technical_summary = technical_analyzer.get_technical_analysis_summary(technical_analysis)
        
        # 评估数据质量
        data_status = _evaluate_technical_data_quality(technical_analysis)
        
        # 获取数据时效性信息
        data_freshness = _get_data_freshness(technical_analysis)
        
        return {
            'raw_data': technical_analysis,
            'summary': technical_summary,
            'status': data_status,
            'freshness': data_freshness,
            'stock_code': stock_code,
            'stock_name': stock_name,
            'timestamp': datetime.now().isoformat(),
            'metadata': {
                'data_source': technical_analysis.get('technical_data', {}).get('data_source', 'unknown'),
                'data_period': technical_analysis.get('technical_data', {}).get('data_period', 'unknown'),
                'data_quality': technical_analysis.get('data_quality', 'unknown'),
                'integration_level': technical_analysis.get('integration_level', 'unknown'),
                'has_technical_prompt': 'technical_prompt' in technical_analysis
            }
        }
        
    except Exception as e:
        print(f"[WARN] 技术分析获取失败: {e}")
        return {
            'error': f'技术分析失败: {str(e)}',
            'status': 'error',
            'fallback_data': '技术分析数据暂不可用，建议专注于基本面分析',
            'recommendation': '后续可重新尝试获取技术分析数据',
            'timestamp': datetime.now().isoformat()
        }


def _determine_integration_level(technical_data: Dict[str, Any]) -> str:
    """
    根据技术分析质量决定集成深度（智能降级策略）

    Args:
        technical_data: 技术分析数据

    Returns:
        str: 集成级别（'deep'/'moderate'/'basic'/'fallback'）
    """
    # 优先使用TechnicalAnalyzer返回的integration_level
    metadata = technical_data.get('metadata', {})
    analyzer_integration_level = metadata.get('integration_level')
    if analyzer_integration_level:
        return analyzer_integration_level

    # 降级：根据数据质量评估
    if technical_data.get('status') == 'error':
        return 'fallback'

    status = technical_data.get('status', 'unknown')
    has_technical_prompt = metadata.get('has_technical_prompt', False)

    # 检查数据时效性
    freshness = technical_data.get('freshness', 'unknown')

    # 集成级别决策逻辑
    if status == 'excellent' and has_technical_prompt and freshness in ['fresh', 'recent']:
        return 'deep'  # 深度集成

    elif status in ['good', 'excellent'] and has_technical_prompt:
        return 'moderate'  # 适度集成

    elif status in ['warning', 'simulated']:
        return 'basic'  # 基础集成

    else:
        return 'fallback'  # 降级模式


def _get_technical_summary_for_integration(technical_data: Dict[str, Any], integration_level: str) -> str:
    """
    根据集成级别生成相应的技术分析摘要（增强版：包含交易信号）
    
    Args:
        technical_data: 技术分析数据
        integration_level: 集成级别
        
    Returns:
        str: 格式化后的技术分析摘要
    """
    if integration_level == 'fallback':
        return technical_data.get('fallback_data', '技术分析数据暂不可用')
    
    raw_data = technical_data.get('raw_data', {})
    trading_signal = raw_data.get('trading_signal', {})
    
    # 构建基础摘要
    base_summary = raw_data.get('technical_data', {}).get('summary', '')
    
    # 如果有交易信号，添加到摘要中
    if trading_signal:
        signal = trading_signal.get('signal', '未知')
        confidence = trading_signal.get('confidence', 0)
        price = trading_signal.get('price', 0)
        
        signal_summary = f"\n【量化交易信号】{signal}（置信度{confidence:.1f}%，价格{price:.2f}元）"
        
        if trading_signal.get('stop_loss'):
            stop_loss = trading_signal.get('stop_loss')
            take_profit = trading_signal.get('take_profit')
            signal_summary += f"\n  - 止损位：{stop_loss:.2f}元 | 止盈位：{take_profit:.2f}元"
    else:
        signal_summary = ""
    
    if integration_level == 'basic':
        return (base_summary or '技术分析数据有限') + signal_summary
    
    elif integration_level in ['moderate', 'deep']:
        metadata = technical_data.get('metadata', {})
        data_source = metadata.get('data_source', '未知')
        data_quality = metadata.get('data_quality', 'unknown')
        
        summary_parts = [base_summary or '技术分析数据']
        summary_parts.append(f"数据来源: {data_source} | 数据质量: {data_quality}")
        summary_parts.append(signal_summary)
        
        return "\n".join(summary_parts)
    
    else:
        return '技术分析数据准备中'


def _evaluate_technical_data_quality(technical_analysis: Dict[str, Any]) -> str:
    """
    评估技术分析数据质量

    Args:
        technical_analysis: 技术分析原始数据

    Returns:
        str: 质量评级（'excellent'/'good'/'warning'/'error'）
    """
    try:
        # 直接使用TechnicalAnalyzer返回的data_quality字段
        if 'data_quality' in technical_analysis:
            return technical_analysis['data_quality']

        # 兼容旧版本：检查technical_data中的data_status
        tech_data = technical_analysis.get('technical_data', {})

        # 检查是否有有效数据
        if not tech_data:
            return 'error'

        # 使用data_status字段评估
        data_status = tech_data.get('data_status', 'unknown')
        if data_status in ['excellent', 'good', 'warning', 'error', 'simulated']:
            return data_status

        # 检查数据完整性
        required_fields = ['current_price', 'data_status']
        missing_fields = [field for field in required_fields if field not in tech_data]

        if missing_fields:
            return 'warning'

        # 检查数据新鲜度
        freshness_days = tech_data.get('data_freshness_days', 999)
        if freshness_days <= 1:
            return 'excellent'
        elif freshness_days <= 3:
            return 'good'
        elif freshness_days <= 7:
            return 'warning'
        else:
            return 'warning'

    except Exception as e:
        print(f"[WARN] 数据质量评估异常: {e}")
        return 'error'


def _get_data_freshness(technical_analysis: Dict[str, Any]) -> str:
    """
    评估技术分析数据的新鲜度
    
    Args:
        technical_analysis: 技术分析原始数据
        
    Returns:
        str: 新鲜度评级（'fresh'/'recent'/'acceptable'/'stale'）
    """
    try:
        tech_data = technical_analysis.get('technical_data', {})
        data_timestamp = tech_data.get('last_update')
        
        if not data_timestamp:
            return 'unknown'
        
        # 转换为datetime对象进行比较
        if isinstance(data_timestamp, str):
            from datetime import datetime
            data_time = datetime.fromisoformat(data_timestamp.replace('Z', '+00:00'))
        else:
            data_time = data_timestamp
        
        current_time = datetime.now()
        time_diff = current_time - data_time
        
        if time_diff.total_seconds() < 3600:  # 1小时内
            return 'fresh'
        elif time_diff.total_seconds() < 86400:  # 24小时内
            return 'recent'
        elif time_diff.total_seconds() < 604800:  # 7天内
            return 'acceptable'
        else:
            return 'stale'
            
    except Exception:
        return 'unknown'


def _get_technical_prompt_for_analysis(technical_data: Dict[str, Any], integration_level: str) -> str:
    """
    根据集成级别生成技术分析提示词（增强版：直接使用TechnicalAnalyzer生成的prompt）
    
    Args:
        technical_data: 技术分析数据
        integration_level: 集成级别
        
    Returns:
        str: 格式化后的技术分析提示词
    """
    if integration_level == 'fallback':
        return '技术分析数据暂不可用，建议专注于基本面分析'
    
    raw_data = technical_data.get('raw_data', {})
    
    # 直接使用TechnicalAnalyzer生成的technical_prompt（已包含交易信号）
    technical_prompt = raw_data.get('technical_prompt', '')
    
    if integration_level == 'basic':
        return technical_prompt or '技术分析数据有限'
    
    elif integration_level in ['moderate', 'deep']:
        # TechnicalAnalyzer的prompt已经包含了数据质量和交易信号信息
        return technical_prompt
    
    else:
        return '技术分析数据准备中'


def _get_technical_conclusion_for_investment(technical_data: Dict[str, Any], integration_level: str) -> str:
    """
    根据集成级别生成投资建议中的技术分析结论（增强版：包含量化交易信号）
    
    Args:
        technical_data: 技术分析数据
        integration_level: 集成级别
        
    Returns:
        str: 格式化后的技术分析结论
    """
    if integration_level == 'fallback':
        return '技术面分析数据有限，建议谨慎参考'
    
    raw_data = technical_data.get('raw_data', {})
    tech_data = raw_data.get('technical_data', {})
    trading_signal = raw_data.get('trading_signal', {})
    
    if integration_level == 'basic':
        current_price = tech_data.get('current_price', 'N/A')
        data_period = tech_data.get('data_period', '未知')
        conclusion = f"技术指标显示：当前价格{current_price}，数据周期{data_period}"
        
        # 添加交易信号（如果有）
        if trading_signal:
            signal = trading_signal.get('signal', '未知')
            conclusion += f"\n量化信号：{signal}"
        
        return conclusion
    
    elif integration_level == 'moderate':
        current_price = tech_data.get('current_price', 'N/A')
        data_period = tech_data.get('data_period', '未知')
        trend = tech_data.get('trend', '未知')
        conclusion = f"技术面分析：当前价格{current_price}，趋势{trend}，数据周期{data_period}"
        
        # 添加交易信号（如果有）
        if trading_signal:
            signal = trading_signal.get('signal', '未知')
            confidence = trading_signal.get('confidence', 0)
            conclusion += f"\n量化信号：{signal}（置信度{confidence:.1f}%）"
        
        return conclusion
    
    elif integration_level == 'deep':
        current_price = tech_data.get('current_price', 'N/A')
        data_period = tech_data.get('data_period', '未知')
        trend = tech_data.get('trend', '未知')
        support_level = tech_data.get('support', 'N/A')
        resistance_level = tech_data.get('resistance', 'N/A')
        
        conclusion_parts = [
            f"当前价格: {current_price}",
            f"技术趋势: {trend}",
            f"支撑位: {support_level}",
            f"阻力位: {resistance_level}",
            f"数据周期: {data_period}"
        ]
        
        # 添加量化交易信号（如果有）
        if trading_signal:
            signal = trading_signal.get('signal', '未知')
            confidence = trading_signal.get('confidence', 0)
            conclusion_parts.append(f"量化信号: {signal}（置信度{confidence:.1f}%）")
            
            # 添加风险管理建议
            if trading_signal.get('stop_loss'):
                stop_loss = trading_signal.get('stop_loss')
                take_profit = trading_signal.get('take_profit')
                risk_reward = trading_signal.get('risk_reward')
                conclusion_parts.append(f"风险管理: 止损{stop_loss:.2f} | 止盈{take_profit:.2f} | 风险回报比1:{risk_reward:.1f}")
        
        return "技术指标综合分析：" + " | ".join(conclusion_parts)
    
    else:
        return '技术面分析数据准备中'
