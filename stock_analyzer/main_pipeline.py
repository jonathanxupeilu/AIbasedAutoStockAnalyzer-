import argparse
from pathlib import Path
from typing import Any, Dict, List

from .core.analyst import analyze_stock
from .core.screener import run_screener

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 系统配置参数
CONFIG: Dict[str, Any] = {
    "screening_criteria": {"pe_max": 25, "pb_max": 4},  # 量化筛选标准：PE最大25倍，PB最大4倍
    "candidate_list_file": str(PROJECT_ROOT / "data" / "candidate_stocks.md"),  # 候选股票池文件路径
    "report_output_dir": str(PROJECT_ROOT / "reports"),  # 报告输出目录
    "summary_report_file": str(PROJECT_ROOT / "reports" / "综合分析报告.md"),  # 综合分析报告文件路径
}


def generate_summary_report(results: List[Dict[str, Any]], output_path: str) -> None:
    """
    生成综合分析报告索引文件
    
    Args:
        results: 分析结果列表，包含股票代码、名称和报告路径
        output_path: 汇总报告输出路径
    """
    if not results:
        return

    lines: List[str] = []
    lines.append("# 综合分析报告索引")
    lines.append("")

    # 为每个分析结果生成Markdown格式的链接
    for item in results:
        code = item.get("stock_code", "")
        name = item.get("stock_name", "")
        report_path = item.get("report_path", "")
        rel_path = Path(report_path).as_posix()
        lines.append(f"- [{name} ({code})]({rel_path})")

    lines.append("")
    lines.append("本报告由系统自动生成，仅供研究参考，不构成投资建议。")

    # 写入汇总报告文件
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """
    主流程函数：执行完整的AI股票分析流水线
    步骤：1.量化筛选 → 2.股票分析 → 3.报告生成
    """
    # 步骤1：执行量化筛选，获取候选股票池
    candidate_df = run_screener(
        CONFIG["screening_criteria"],
        CONFIG["candidate_list_file"],
    )

    # 检查筛选结果，若无候选股则提前结束流程
    if candidate_df.empty:
        print("筛选未得到候选股，流程结束。")
        return

    # 显示筛选结果
    print("\n========== 量化筛选候选池 ==========")
    print(candidate_df.to_string(index=False))
    print("=====================================\n")

    # 步骤2：解析命令行参数，获取待分析股票代码
    parser = argparse.ArgumentParser(description="AI股票分析流水线")
    parser.add_argument(
        "--stock_codes",
        nargs="+",
        required=True,
        help="指定要分析的股票代码，例如: 000001 600519",
    )
    args = parser.parse_args()

    # 步骤3：逐个分析指定股票
    results: List[Dict[str, Any]] = []
    for stock_code in args.stock_codes:
        # 从候选池中查找股票名称：如果股票池中有对应公司则使用其名称，否则使用代码命名
        name_series = candidate_df.loc[
            candidate_df["代码"] == stock_code, "名称"
        ].values
        stock_name = name_series[0] if len(name_series) > 0 else f"Stock-{stock_code}"
        
        # 执行单只股票的深度分析
        report_info = analyze_stock(
            stock_code,
            stock_name,
            CONFIG["report_output_dir"],
        )
        
        # 收集分析结果
        if report_info:
            results.append(report_info)

    # 步骤4：生成综合分析报告索引
    if results:
        generate_summary_report(results, CONFIG["summary_report_file"])


if __name__ == "__main__":
    main()

