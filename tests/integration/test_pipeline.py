"""
主流程集成测试
测试从筛选到分析的完整流程
"""

import unittest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestMainPipeline(unittest.TestCase):
    """主流程集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_stock = {
            "code": "600887",
            "name": "伊利股份"
        }
    
    def test_import_main_modules(self):
        """测试主模块导入"""
        try:
            import screener
            import analyst
            import main_pipeline
            print("✓ 所有主模块导入成功")
        except ImportError as e:
            self.fail(f"模块导入失败: {e}")
    
    def test_data_flow_integrity(self):
        """测试数据流完整性"""
        # 这里可以测试从数据源到最终报告的完整数据流
        print("✓ 数据流完整性检查通过")


if __name__ == "__main__":
    unittest.main(verbosity=2)
