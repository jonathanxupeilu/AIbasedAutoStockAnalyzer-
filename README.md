# AI股票深度分析系统

基于AI的自动化股票分析系统，使用DeepSeek大模型进行专业股票估值分析和投资建议。

## 功能特性

- 🔍 **智能分析**: 基于DeepSeek大模型的深度股票分析
- 📊 **多维度评估**: 估值分析、行业对比、投资建议
- 📈 **实时数据**: 东方财富API获取实时估值数据
- 📋 **配置化框架**: YAML配置分析问题和报告模板
- 🔒 **环境隔离**: 独立的Python虚拟环境
- 📥 **灵活导入**: 支持CSV格式股票池导入，用户可手动筛选
- ⚖️ **资产配置**: 可选的大类资产配置建议模块
- 🎯 **智能评分**: 多规则评分引擎，支持自定义评分策略

## 快速开始

### 方式一：使用启动脚本（推荐）

#### Windows用户
```bash
# 激活虚拟环境
venv\Scripts\activate

# 运行分析
python run_from_package.py --stock_codes 000001 600519
```

#### Linux/Mac用户
```bash
# 激活虚拟环境
source venv/bin/activate

# 运行分析
python run_from_package.py --stock_codes 000001 600519
```

### 方式二：手动设置

1. **创建虚拟环境**
```bash
python -m venv venv
```

2. **激活虚拟环境**
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置API密钥**
```bash
# 复制配置文件
cp .env.example .env

# 编辑.env文件，添加DeepSeek API密钥
# DEEPSEEK_API_KEY=your_api_key_here
```

5. **运行分析**
```bash
python run_from_package.py --stock_codes 000001 600519
```

## 项目结构

```
AIbasedAutoStockAnalyzer/
├── venv/                          # Python虚拟环境
├── stock_analyzer/                 # 核心代码包
│   ├── core/                      # 核心业务逻辑
│   │   ├── analyst.py            # AI分析核心模块
│   │   ├── screener.py           # 股票筛选器
│   │   ├── technical_analyzer.py # 技术分析器
│   │   └── stock_pool_manager.py # 股票池管理器（支持CSV导入）
│   ├── api/                       # 接口定义层
│   │   └── lixinger_provider.py  # 理杏仁数据提供器
│   ├── utils/                     # 工具模块
│   │   └── news_formatter.py     # 新闻格式化器
│   └── main_pipeline.py          # 主程序入口（支持资产配置模块）
├── config/                        # 配置文件
│   └── analysis_framework.yaml    # 分析框架配置
├── data/                          # 数据文件
│   ├── stock_pool.md             # 统一股票池（合并量化筛选和自选股）
│   ├── watch_list.yaml           # 自选股配置文件
│   ├── quant_screened.json       # 量化筛选结果缓存
│   └── candidate_stocks.md       # 候选股票列表（兼容旧版本）
├── tests/                         # 测试目录
│   ├── integration/              # 集成测试
│   └── unit/                     # 单元测试
├── bin/                           # 可执行脚本
│   ├── activate_venv.bat          # Windows虚拟环境激活脚本
│   └── activate_venv.sh           # Linux/Mac虚拟环境激活脚本
├── scripts/                       # 辅助脚本
├── docs/                          # 文档目录
├── reports/                       # 分析报告输出目录
├── run_from_package.py            # 主启动脚本
├── requirements.txt               # Python依赖包
├── pyproject.toml                 # 项目配置
└── README.md                      # 项目说明
```

## 配置说明

### 分析框架配置 (analysis_framework.yaml)

编辑此文件可以自定义分析问题和报告模板：

```yaml
analysis_framework:
  - question: "估值水平分析"
    prompt: "基于PE：{pe}，PB：{pb}，分析估值合理性"
  
report_template:
  title: "{stock_name}投资分析报告"
  disclaimer: "本报告由AI生成，仅供研究参考"
```

### 环境变量配置 (.env)

从 [DeepSeek平台](https://platform.deepseek.com/) 获取API密钥：

```bash
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

## 使用示例

### 分析单只股票
```bash
python run_from_package.py --stock_codes 000001
```

### 分析多只股票
```bash
python run_from_package.py --stock_codes 000001 600519 300750
```

### 查看帮助
```bash
python run_from_package.py --help
```

## 输出结果

分析完成后，系统会生成：
- **个股分析报告**: `reports/股票代码_股票名称.md`
- **综合分析索引**: `综合分析报告.md`

报告包含专业的估值分析、行业对比和投资建议。

## 注意事项

1. **API密钥**: 必须配置有效的DeepSeek API密钥
2. **网络连接**: 需要稳定的网络连接获取实时数据
3. **免责声明**: 报告仅供研究参考，不构成投资建议
4. **数据源**: 使用东方财富免费API，可能存在数据延迟

## 技术支持

如有问题，请检查：
- 虚拟环境是否正确激活
- API密钥是否有效
- 网络连接是否正常
- 依赖包是否安装完整

---

*本系统基于Python 3.8+开发，建议使用最新稳定版本。*