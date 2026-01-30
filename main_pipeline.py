import argparse
from pathlib import Path
from typing import Any, Dict, List

from analyst import analyze_stock
from screener import run_screener


CONFIG: Dict[str, Any] = {
    "screening_criteria": {"pe_max": 25, "pb_max": 4},
    "candidate_list_file": "candidate_stocks.md",
    "report_output_dir": "reports",
    "summary_report_file": "综合分析报告.md",
}


def generate_summary_report(results: List[Dict[str, Any]], output_path: str) -> None:
    if not results:
        return

    lines: List[str] = []
    lines.append("# 综合分析报告索引")
    lines.append("")

    for item in results:
        code = item.get("stock_code", "")
        name = item.get("stock_name", "")
        report_path = item.get("report_path", "")
        rel_path = Path(report_path).as_posix()
        lines.append(f"- [{name} ({code})]({rel_path})")

    lines.append("")
    lines.append("本报告由系统自动生成，仅供研究参考，不构成投资建议。")

    Path(output_path).write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    candidate_df = run_screener(
        CONFIG["screening_criteria"],
        CONFIG["candidate_list_file"],
    )

    if candidate_df.empty:
        print("筛选未得到候选股，流程结束。")
        return

    print("\n========== 量化筛选候选池 ==========")
    print(candidate_df.to_string(index=False))
    print("=====================================\n")

    parser = argparse.ArgumentParser(description="AI股票分析流水线")
    parser.add_argument(
        "--stock_codes",
        nargs="+",
        required=True,
        help="指定要分析的股票代码，例如: 000001 600519",
    )
    args = parser.parse_args()

    results: List[Dict[str, Any]] = []
    for stock_code in args.stock_codes:
        name_series = candidate_df.loc[
            candidate_df["代码"] == stock_code, "名称"
        ].values
        stock_name = name_series[0] if len(name_series) > 0 else f"Stock-{stock_code}"
        report_info = analyze_stock(
            stock_code,
            stock_name,
            CONFIG["report_output_dir"],
        )
        if report_info:
            results.append(report_info)

    if results:
        generate_summary_report(results, CONFIG["summary_report_file"])


if __name__ == "__main__":
    main()

