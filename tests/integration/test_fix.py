"""测试技术分析器时间对齐修复效果"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from stock_analyzer.core.technical_analyzer import TechnicalAnalyzer
from datetime import datetime

def test_time_alignment():
    """测试时间对齐修复效果"""
    print('=== 测试技术分析器时间对齐修复 ===')
    
    ta = TechnicalAnalyzer()
    
    # 测试技术分析
    result = ta.analyze_stock_technical('000001', '平安银行')
    
    if result['status'] == 'success':
        tech_data = result['technical_data']
        
        print('[OK] 技术分析成功')
        print(f'数据源: {tech_data.get("data_source", "N/A")}')
        print(f'当前价格: {tech_data.get("current_price", "N/A"):.2f}')
        print(f'最新日期: {tech_data.get("latest_date", "N/A")}')
        print(f'数据周期: {tech_data.get("data_period", "N/A")}')
        
        # 检查时间对齐
        latest_date_str = tech_data.get('latest_date', '')
        if latest_date_str:
            try:
                latest_date = datetime.strptime(latest_date_str, '%Y-%m-%d').date()
                current_date = datetime.now().date()
                days_diff = (current_date - latest_date).days
                
                print(f'数据时效性: 相差{days_diff}天')
                
                if days_diff <= 7:
                    print('[OK] 时间对齐问题已修复！')
                else:
                    print(f'[WARN] 数据时效性仍有问题')
                    
            except Exception as e:
                print(f'时间解析错误: {e}')
        
        # 显示技术分析摘要
        summary = ta.get_technical_analysis_summary(result)
        print(f'技术分析摘要: {summary}')
        
    else:
        print('❌ 技术分析失败')
        print(f'错误信息: {result}')

if __name__ == "__main__":
    test_time_alignment()