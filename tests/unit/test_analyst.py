"""
分析师模块单元测试
测试analyst.py中的核心功能
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from analyst import (
    _load_analysis_framework,
    _get_default_framework,
    _build_prompt,
    _format_report_content
)


class TestAnalystModule(unittest.TestCase):
    """分析师模块测试"""
    
    def test_load_analysis_framework(self):
        """测试加载分析框架配置"""
        config = _load_analysis_framework()
        self.assertIn("analysis_framework", config)
        self.assertIn("report_template", config)
        print("✓ 分析框架配置加载成功")
    
    def test_default_framework_structure(self):
        """测试默认框架结构"""
        default = _get_default_framework()
        framework = default.get("analysis_framework", [])
        self.assertIsInstance(framework, list)
        self.assertGreater(len(framework), 0)
        
        # 检查每个问题项的结构
        for item in framework:
            self.assertIn("question", item)
            self.assertIn("prompt", item)
        
        print(f"✓ 默认框架包含 {len(framework)} 个分析问题")
    
    def test_build_prompt(self):
        """测试提示词构建"""
        stock_code = "600887"
        stock_name = "伊利股份"
        fundamentals = {
            "PE(TTM)估算": 18.5,
            "PB": 3.2,
            "股息率": 3.5
        }
        
        prompt = _build_prompt(stock_code, stock_name, fundamentals)
        
        # 验证提示词包含关键信息
        self.assertIn(stock_code, prompt)
        self.assertIn(stock_name, prompt)
        self.assertIn("PE", prompt)
        self.assertIn("PB", prompt)
        
        print("✓ 提示词构建成功")
    
    def test_format_report_content(self):
        """测试报告格式化"""
        ai_response = "## 测试分析内容\n这是AI分析结果"
        stock_code = "000001"
        stock_name = "平安银行"
        
        report = _format_report_content(ai_response, stock_code, stock_name)
        
        # 验证报告包含必要元素
        self.assertIn(stock_code, report)
        self.assertIn(stock_name, report)
        self.assertIn(ai_response, report)
        self.assertIn("免责声明", report)
        
        print("✓ 报告格式化成功")


if __name__ == "__main__":
    unittest.main(verbosity=2)
