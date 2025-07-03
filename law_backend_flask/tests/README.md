# RAGLEX API 接口测试框架

这是RAGLEX法律智能问答系统的API接口测试框架，提供了完整的API测试解决方案。

## 📁 目录结构

```
tests/
├── README.md              # 测试框架说明文档
├── requirements.txt       # 测试依赖包
├── pytest.ini           # pytest配置文件
├── run_tests.py          # 测试运行脚本
├── test_config.py        # 测试配置管理
├── base_test.py          # 测试基类
├── test_auth.py          # 认证API测试
├── test_cases.py         # 案件管理API测试
├── test_knowledge.py     # 知识库API测试
└── test_files.py         # 文件管理API测试
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# 进入测试目录
cd law_backend_flask/tests

# 安装测试依赖
pip install -r requirements.txt
```

### 2. 配置测试环境

设置环境变量（可选）：

```bash
# 测试服务器地址
export TEST_BASE_URL="http://localhost:5000"

# 测试环境类型
export TEST_ENV="development"  # development/staging/production

# 管理员账户（用于测试）
export TEST_ADMIN_USERNAME="admin"
export TEST_ADMIN_PASSWORD="admin123"
export TEST_ADMIN_EMAIL="admin@test.com"

# 测试超时时间
export TEST_TIMEOUT="30"

# 是否清理测试数据
export TEST_CLEANUP="true"
```

### 3. 启动后端服务

确保RAGLEX后端服务正在运行：

```bash
# 在项目根目录启动服务
cd ../
python app.py
```

### 4. 运行测试

#### 使用pytest运行（推荐）

```bash
# 运行所有测试
python run_tests.py --mode pytest

# 运行特定测试文件
python run_tests.py --mode pytest --files test_auth.py

# 运行测试并生成覆盖率报告
python run_tests.py --mode pytest --coverage

# 运行测试并生成HTML报告
python run_tests.py --mode pytest --coverage --html

# 直接使用pytest
pytest -v
pytest test_auth.py -v
pytest -k "test_login" -v
```

#### 使用手动模式运行

```bash
# 手动运行所有测试
python run_tests.py --mode manual

# 跳过环境检查
python run_tests.py --mode manual --skip-setup
```

## 📋 测试模块说明

### 1. 认证API测试 (`test_auth.py`)

测试用户认证相关功能：
- 用户注册（成功/失败场景）
- 用户登录（成功/失败场景）
- 用户资料管理
- Token验证
- 并发登录测试

### 2. 案件管理API测试 (`test_cases.py`)

测试案件管理功能：
- 案件创建、查询、更新、删除
- 案件搜索和筛选
- 案件分页
- 案件类型验证
- 案件编号唯一性

### 3. 知识库API测试 (`test_knowledge.py`)

测试知识库查询功能：
- 基本问答测试
- 参数验证
- 错误处理
- 性能测试
- 并发查询测试

### 4. 文件管理API测试 (`test_files.py`)

测试文件操作功能：
- 文件上传（各种文件类型）
- 文件下载
- 文件删除
- 文件元数据管理
- 文件搜索

## 🔧 配置说明

### 测试配置 (`test_config.py`)

配置文件包含以下配置项：

- **基础配置**：服务器地址、超时时间
- **用户配置**：测试用户信息
- **API端点**：各API的路径配置
- **测试数据**：预定义的测试数据
- **文件上传**：文件上传相关配置
- **性能测试**：并发和性能测试配置

### pytest配置 (`pytest.ini`)

- 测试发现规则
- 输出格式配置
- 标记定义
- 日志配置
- 警告过滤

## 🏷️ 测试标记

使用pytest标记来分类和筛选测试：

```bash
# 运行特定标记的测试
pytest -m "auth"          # 认证相关测试
pytest -m "api"           # API测试
pytest -m "slow"          # 慢速测试
pytest -m "smoke"         # 冒烟测试
pytest -m "not slow"      # 排除慢速测试
```

可用标记：
- `auth`: 认证相关测试
- `api`: API测试
- `files`: 文件操作测试
- `knowledge`: 知识库测试
- `cases`: 案件管理测试
- `slow`: 慢速测试
- `smoke`: 冒烟测试
- `integration`: 集成测试
- `unit`: 单元测试
- `performance`: 性能测试
- `security`: 安全测试

## 📊 测试报告

### 生成覆盖率报告

```bash
# 生成终端覆盖率报告
pytest --cov=../app --cov-report=term-missing

# 生成HTML覆盖率报告
pytest --cov=../app --cov-report=html
```

### 生成测试报告

```bash
# 生成HTML测试报告
pytest --html=report.html --self-contained-html

# 生成JSON报告
pytest --json-report --json-report-file=report.json
```

## 🔍 调试测试

### 运行单个测试

```bash
# 运行特定测试方法
pytest test_auth.py::TestAuthAPI::test_user_login_success -v

# 运行特定测试类
pytest test_auth.py::TestAuthAPI -v
```

### 调试失败的测试

```bash
# 显示详细错误信息
pytest --tb=long

# 在第一个失败处停止
pytest -x

# 显示最慢的10个测试
pytest --durations=10
```

### 使用pdb调试

```bash
# 在失败处进入调试器
pytest --pdb

# 在测试开始时进入调试器
pytest --pdb-trace
```

## 🚀 性能测试

### 并发测试

```bash
# 使用多进程运行测试
pytest -n 4  # 使用4个进程

# 自动检测CPU核心数
pytest -n auto
```

### 性能基准测试

在测试中使用性能断言：

```python
def test_api_performance(self):
    start_time = time.time()
    response = self.make_request('GET', '/api/knowledge')
    duration = time.time() - start_time
    
    assert duration < 2.0, f"API响应时间过长: {duration}秒"
```

## 🔒 安全测试

### SQL注入测试

```python
def test_sql_injection_protection(self):
    malicious_input = "'; DROP TABLE users; --"
    response = self.make_request('POST', '/api/cases', {
        'case_title': malicious_input
    })
    # 验证系统正确处理了恶意输入
```

### XSS测试

```python
def test_xss_protection(self):
    xss_payload = "<script>alert('xss')</script>"
    response = self.make_request('POST', '/api/cases', {
        'case_description': xss_payload
    })
    # 验证输出被正确转义
```

## 📝 编写新测试

### 1. 继承基类

```python
from .base_test import BaseAPITest

class TestNewAPI(BaseAPITest):
    def setup_method(self):
        self.login_admin()
    
    def test_new_feature(self):
        response = self.make_request('GET', '/api/new-endpoint')
        self.assert_response(response, 200, ['success', 'data'])
```

### 2. 使用测试标记

```python
import pytest

@pytest.mark.slow
@pytest.mark.integration
def test_complex_workflow(self):
    # 复杂的集成测试
    pass
```

### 3. 参数化测试

```python
@pytest.mark.parametrize("input_data,expected_status", [
    ({'valid': 'data'}, 200),
    ({'invalid': 'data'}, 400),
    ({}, 422),
])
def test_input_validation(self, input_data, expected_status):
    response = self.make_request('POST', '/api/endpoint', input_data)
    assert response.status_code == expected_status
```

## 🐛 常见问题

### 1. 连接错误

```
ConnectionError: Failed to establish a new connection
```

**解决方案**：
- 确保后端服务正在运行
- 检查`TEST_BASE_URL`配置
- 验证端口是否正确

### 2. 认证失败

```
AssertionError: Expected status 200, got 401
```

**解决方案**：
- 检查管理员账户配置
- 确保用户已在数据库中创建
- 验证密码是否正确

### 3. 测试数据冲突

```
IntegrityError: Duplicate entry
```

**解决方案**：
- 启用测试数据清理
- 使用唯一的测试数据
- 检查`teardown_method`是否正确执行

## 📚 最佳实践

1. **测试隔离**：每个测试应该独立，不依赖其他测试的结果
2. **数据清理**：测试后清理创建的数据，避免影响其他测试
3. **错误处理**：测试各种错误场景，不仅仅是成功路径
4. **性能考虑**：避免在测试中进行不必要的等待
5. **文档更新**：添加新测试时更新相关文档
6. **代码复用**：使用基类和工具方法减少重复代码
7. **持续集成**：将测试集成到CI/CD流程中

## 🤝 贡献指南

1. 添加新的API测试时，请遵循现有的命名约定
2. 确保新测试包含适当的错误处理和边界条件测试
3. 添加必要的测试标记和文档
4. 运行完整的测试套件确保没有破坏现有功能
5. 更新README文档说明新增的测试功能

## 📞 支持

如果在使用测试框架时遇到问题，请：

1. 查看本文档的常见问题部分
2. 检查测试日志输出
3. 验证环境配置是否正确
4. 联系开发团队获取支持