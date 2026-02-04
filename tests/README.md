# 测试目录说明

## 目录结构

```
tests/
├── __init__.py
├── README.md
├── api/                    # API接口测试
│   ├── __init__.py
│   └── test_stock_news.py  # 个股新闻API测试
├── unit/                   # 单元测试
│   ├── __init__.py
│   └── test_analyst.py     # 分析师模块测试
└── integration/            # 集成测试
    ├── __init__.py
    └── test_pipeline.py    # 主流程集成测试
```

## 测试分类说明

### API测试 (`tests/api/`)
测试外部数据源API接口，包括：
- 东方财富个股新闻接口 (`stock_news_em`)
- 理杏仁API接口
- 其他数据源接口

### 单元测试 (`tests/unit/`)
测试独立功能模块，包括：
- 分析师模块 (`analyst.py`)
- 筛选器模块 (`screener.py`)
- 数据提供者模块 (`lixinger_provider.py`)

### 集成测试 (`tests/integration/`)
测试多模块协同工作，包括：
- 主流程测试 (`main_pipeline.py`)
- 端到端数据流测试

## 运行测试

### 运行所有测试
```bash
python -m unittest discover tests
```

### 运行特定模块测试
```bash
# API测试
python -m unittest tests.api.test_stock_news

# 单元测试
python -m unittest tests.unit.test_analyst

# 集成测试
python -m unittest tests.integration.test_pipeline
```

### 运行单个测试文件
```bash
python tests/api/test_stock_news.py
```

## 测试规范

1. **命名规范**: 测试文件以 `test_` 开头
2. **类命名**: 测试类继承 `unittest.TestCase`
3. **方法命名**: 测试方法以 `test_` 开头
4. **文档字符串**: 每个测试方法应有清晰的文档说明
