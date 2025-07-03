# GPU内存管理指南

## 概述

为了解决 `receive_data.py` 进程占用大量GPU内存的问题，我们实现了以下GPU内存管理机制：

## 问题分析

原始代码存在以下问题：
1. **重复加载模型**：每次调用重排序函数都会创建新的 `FlagReranker` 实例
2. **缺乏内存清理**：模型使用后没有及时释放GPU内存
3. **Embedding模型常驻**：BGE embedding模型一直占用GPU内存

## 解决方案

### 1. 自动内存清理

所有重排序函数现在都包含自动内存清理机制：

```python
# 重排序函数示例
def rerank_documents(question: str, initial_top_n: int = 15, top_n: int = 3):
    reranker = FlagReranker(str(config.RERANKER_PATH))
    try:
        scores = reranker.compute_score(sentence_pairs)
        # ... 处理结果
        return result
    finally:
        # 自动清理reranker模型和GPU内存
        del reranker
        clear_gpu_memory()
```

### 2. Embedding模型单例模式

BGE embedding模型现在使用单例模式，避免重复加载：

```python
# 全局变量存储embedding模型实例
_global_embedder = None

def get_embedder_bge():
    global _global_embedder
    if _global_embedder is None:
        _global_embedder = HuggingFaceBgeEmbeddings(...)
        print("BGE Embedding模型已加载到GPU")
    return _global_embedder
```

### 3. 内存管理函数

#### 基础内存清理
```python
from utils import clear_gpu_memory
clear_gpu_memory()  # 清理GPU缓存
```

#### 获取内存信息
```python
from utils import get_gpu_memory_info
get_gpu_memory_info()  # 显示GPU内存使用状态
```

#### 清理Embedding模型
```python
from utils import clear_embedder
clear_embedder()  # 清理BGE embedding模型
```

#### 强制清理所有内存
```python
from utils import force_clear_all_gpu_memory
force_clear_all_gpu_memory()  # 清理所有GPU内存
```

## 使用建议

### 1. 日常使用
- 重排序函数会自动清理内存，无需手动干预
- 定期调用 `get_gpu_memory_info()` 监控内存使用

### 2. 内存不足时
```python
# 方法1：清理GPU缓存
clear_gpu_memory()

# 方法2：清理embedding模型（会在下次使用时重新加载）
clear_embedder()

# 方法3：强制清理所有内存
force_clear_all_gpu_memory()
```

### 3. 长时间运行的服务
建议在适当的时机（如请求间隔）调用内存清理函数：

```python
# 在处理完一批请求后
if request_count % 10 == 0:  # 每10个请求清理一次
    clear_gpu_memory()

# 或者基于内存使用率
memory_info = get_gpu_memory_info()
if memory_info and memory_info['allocated'] > 10.0:  # 超过10GB时清理
    force_clear_all_gpu_memory()
```

## 测试

运行测试脚本验证内存管理功能：

```bash
python test_memory_cleanup.py
```

## 性能影响

### 优化效果
- **内存占用降低**：重排序后立即释放模型内存
- **避免重复加载**：Embedding模型使用单例模式
- **可控的内存使用**：提供手动清理选项

### 潜在开销
- **首次加载**：Embedding模型首次加载时间不变
- **重排序开销**：每次重排序仍需加载FlagReranker（但会立即清理）
- **清理时间**：内存清理操作需要少量时间

## 监控建议

1. **定期检查**：使用 `get_gpu_memory_info()` 监控内存使用
2. **设置阈值**：当内存使用超过阈值时自动清理
3. **日志记录**：记录内存清理操作的时间和效果

## 故障排除

### 内存仍然过高
1. 检查是否有其他进程使用GPU
2. 调用 `force_clear_all_gpu_memory()` 强制清理
3. 重启Python进程

### 性能下降
1. 减少重排序频率
2. 降低 `initial_top_n` 和 `top_n` 参数
3. 考虑使用CPU进行重排序（修改config中的device设置）

## 配置优化

可以在 `config.py` 中添加以下配置来进一步优化：

```python
# GPU内存管理配置
GPU_MEMORY_THRESHOLD = 10.0  # GB，超过此值时自动清理
AUTO_CLEANUP_INTERVAL = 10   # 每N个请求自动清理一次
USE_CPU_FOR_RERANK = False   # 是否使用CPU进行重排序
```