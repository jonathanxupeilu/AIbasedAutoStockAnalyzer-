# 项目目录结构说明

## 概述

本项目采用Google风格的目录结构，遵循明确的分层架构原则，确保代码可维护性和可扩展性。

## 目录结构

```
AIbasedAutoStockAnalyzer/
├── bin/                           # 可执行脚本
│   ├── activate_venv.bat          # Windows虚拟环境激活脚本
│   ├── activate_venv.sh            # Linux/Mac虚拟环境激活脚本
│   ├── run_analysis.bat            # Windows分析运行脚本
│   ├── run_analysis.sh             # Linux/Mac分析运行脚本
│   └── check_env.py               # 环境检查脚本
│
├── stock_analyzer/                # 核心代码包
│   ├── __init__.py
│   ├── main_pipeline.py            # 主流程入口（支持资产配置模块）
│   ├── api/                       # API接口层
│   │   ├── __init__.py
│   │   └── lixinger_provider.py   # 理杏仁API数据提供者
│   ├── core/                      # 核心业务逻辑
│   │   ├── __init__.py
│   │   ├── analyst.py             # AI分析核心逻辑
│   │   ├── screener.py            # 股票筛选器
│   │   ├── technical_analyzer.py  # 技术分析器（B+C方案实现）
│   │   └── stock_pool_manager.py  # 股票池管理器（支持CSV导入）
│   └── utils/                     # 通用工具
│       ├── __init__.py
│       └── news_formatter.py      # 新闻格式化工具
│
├── tests/                        # 测试目录
│   ├── __init__.py
│   ├── README.md                  # 测试说明
│   ├── unit/                      # 单元测试
│   │   ├── __init__.py
│   │   └── test_analyst.py
│   ├── integration/               # 集成测试
│   │   ├── __init__.py
│   │   ├── test_b_plan_verification.py
│   │   ├── test_cache_fix.py
│   │   ├── test_fix.py
│   │   ├── test_lixinger.py
│   │   ├── test_lixinger_api.py
│   │   ├── test_news_integration.py
│   │   ├── test_sequential_analysis.py
│   │   ├── test_technical_integration.py
│   │   ├── test_timezone_fix.py
│   │   └── test_valuation_api.py
│   └── api/                      # API层测试
│       ├── __init__.py
│       └── test_stock_news.py
│
├── scripts/                      # 临时调试脚本
│   ├── akshare_debug.py
│   ├── debug_simulated_data.py
│   ├── debug_technical.py
│   └── fix_cache_issue.py
│
├── docs/                         # 文档目录
│   ├── PRD.md                    # 产品需求文档
│   ├── B方案技术分析器测试报告.md
│   ├── 综合分析报告.md
│   ├── test_candidates.md
│   └── PROJECT_STRUCTURE.md      # 本文件
│
├── config/                       # 配置文件
│   ├── analysis_framework.yaml   # 分析框架配置
│   └── tushare_token.txt       # Tushare API令牌
│
├── data/                         # 数据文件
│   ├── stock_pool.md           # 统一股票池（合并量化筛选和自选股）
│   ├── watch_list.yaml         # 自选股配置文件
│   ├── quant_screened.json     # 量化筛选结果缓存
│   └── candidate_stocks.md     # 候选股票列表（兼容旧版本）
│
├── reports/                      # 生产报告输出目录
│   ├── 000001_平安银行.md
│   ├── 600519_Stock-600519.md
│   └── ...
│
├── test_reports/                  # 测试报告输出目录
│   └── 000001_平安银行.md
│
├── .cache/                       # 缓存目录
│   ├── kline_*.json              # K线数据缓存
│   └── lixinger_data_*.json     # 理杏仁数据缓存
│
├── .codebuddy/                   # CodeBuddy配置
│   └── skills/                   # 技能定义
│
├── venv/                         # Python虚拟环境
│
├── .env                          # 环境变量
├── .env.example                  # 环境变量示例
├── .gitignore                    # Git忽略文件
├── pyproject.toml               # 项目配置（依赖、构建）
├── requirements.txt              # Python依赖列表
├── run_from_package.py          # 包方式启动脚本
└── README.md                    # 项目说明文档
```

## 架构设计原则

### 1. 分层架构
- **api层**: 对外接口，负责与外部服务（如理杏仁API）交互
- **core层**: 核心业务逻辑，包含分析、筛选、技术分析等主要功能
- **utils层**: 通用工具函数，可被各层复用

### 2. 依赖注入
所有依赖通过清晰的模块导入可见，避免隐式全局变量。

### 3. 最小化公共接口
只暴露必要的API接口，内部实现通过下划线前缀或内部包隐藏。

### 4. 测试分离
- 单元测试：测试单个函数/类的功能
- 集成测试：测试多个模块协同工作
- API测试：测试外部API接口

## 使用说明

### 安装依赖
```bash
pip install -r requirements.txt
```

### 激活虚拟环境
```bash
# Windows
bin\activate_venv.bat

# Linux/Mac
bin/activate_venv.sh
```

### 运行分析
```bash
# 方式1：直接运行主流程
python run_from_package.py --stock_codes 000001 600519

# 方式2：使用包方式运行
python -m stock_analyzer.main_pipeline --stock_codes 000001 600519

# 方式3：使用传统脚本（已移动到bin）
bin\run_analysis.bat --stock_codes 000001 600519
```

### 运行测试
```bash
# 运行所有测试
python -m pytest tests/

# 运行集成测试
python -m pytest tests/integration/

# 运行特定测试
python -m pytest tests/integration/test_b_plan_verification.py -v
```

## 配置文件说明

1. **analysis_framework.yaml**: 定义AI分析的问题框架
2. **tushare_token.txt**: 存储Tushare API访问令牌
3. **.env**: 环境变量配置（API密钥等）

## 迁移说明

本次目录重构将原有的扁平结构改为分层结构，主要变更：

### 代码文件移动
- `analyst.py` → `stock_analyzer/core/`
- `screener.py` → `stock_analyzer/core/`
- `technical_analyzer.py` → `stock_analyzer/core/`
- `lixinger_provider.py` → `stock_analyzer/api/`
- `news_formatter.py` → `stock_analyzer/utils/`
- `main_pipeline.py` → `stock_analyzer/`

### 测试文件移动
- 所有`test_*.py` → `tests/integration/`

### 脚本文件移动
- `activate_venv.*`, `run_analysis.*`, `check_env.py` → `bin/`
- `debug_*.py`, `fix_*.py` → `scripts/`

### 文档文件移动
- `PRD.md`, `B方案*.md`, `综合分析报告.md` → `docs/`

### 配置文件移动
- `analysis_framework.yaml`, `tushare_token.txt` → `config/`
- `candidate_stocks.md` → `data/`

### Import路径更新
所有内部导入已更新为相对导入：
- `from analyst import` → `from .core.analyst import`
- `from lixinger_provider import` → `from ..api.lixinger_provider import`

## B+C方案实现

技术分析器（`technical_analyzer.py`）实现了完整的B+C方案：

- **B方案（模块化集成）**: 独立的技术分析模块，可与主流程解耦
- **C方案（智能降级）**: 多级数据源降级策略
  - 缓存 → 理杏仁API → AKShare → 模拟数据
  - 数据质量评估系统（excellent/good/warning/critical）
  - 集成级别决策（deep/moderate/basic/fallback）

## 新功能模块说明

### 股票池管理模块 (Stock Pool Manager)
- **位置**: `stock_analyzer/core/stock_pool_manager.py`
- **功能**: 统一管理股票池，支持CSV导入和自选股管理
- **数据文件**: 
  - `data/stock_pool.md`: 统一股票池（Markdown格式）
  - `data/watch_list.yaml`: 自选股配置文件
  - `data/quant_screened.json`: 量化筛选结果缓存
- **特点**: 支持用户手动筛选股票池，替代原有的API量化筛选

### 资产配置模块 (Asset Allocation Module)
- **位置**: 可选的独立模块（暂未实现）
- **功能**: 提供大类资产配置建议，支持OCR持仓解析
- **特点**: 
  - 完全独立模块，可选择是否启用
  - 文本输出格式，不影响主流程
  - 基于专业资产配置理论

### 评分引擎模块 (Scoring Engine)
- **位置**: 可配置的评分规则系统
- **功能**: 多规则综合评分，支持自定义评分策略
- **特点**:
  - 支持多套评分规则配置
  - 可配置权重和阈值
  - 用户可自定义评分策略

## 未来扩展

根据Google工程实践，未来可考虑：

1. 添加`internal/`目录存放内部工具
2. 将`technical_analyzer.py`进一步拆分为独立子模块
3. 添加性能监控和日志系统
4. 实现更完善的单元测试覆盖
5. 完善资产配置模块和评分引擎模块的实现
