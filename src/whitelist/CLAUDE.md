[根目录](../../CLAUDE.md) > [src](../) > **whitelist**

# 白名单模块 - src/whitelist/

## 变更记录 (Changelog)

### 2025-12-03
- 初始化模块文档

---

## 模块职责

管理已审核通过视频的特征库，提供高效的向量存储和相似度检索功能。

**核心功能**：
- 特征向量存储（基于 FAISS 或 Numpy）
- 相似度快速检索（余弦相似度）
- 视频记录管理（添加/删除/查询）
- 持久化存储和加载
- 相似度计算工具

**注意**：此模块为可选模块，用于本地白名单方案。

---

## 入口与启动

**主入口**：`feature_store.py`

**使用示例**：
```python
from src.whitelist.feature_store import FeatureStore
import numpy as np

# 初始化特征库
store = FeatureStore(
    dimension=512,
    index_type="flat",
    storage_path="./data/features"
)

# 添加视频特征
feature = np.random.randn(512).astype(np.float32)
store.add(
    video_id="video_001",
    feature=feature,
    video_path="/path/to/video.mp4",
    metadata={"category": "music_mv"}
)

# 搜索相似视频
query_feature = np.random.randn(512).astype(np.float32)
results = store.search(query_feature, top_k=5)
for r in results:
    print(f"{r['video_id']}: {r['similarity']:.4f}")

# 保存特征库
store.save()

# 加载特征库
store.load()
```

---

## 对外接口

### FeatureStore 类

**初始化参数**：
```python
FeatureStore(
    dimension: int = 512,                    # 特征向量维度
    index_type: str = "flat",                # 索引类型 ("flat"/"ivf")
    storage_path: Optional[str] = None       # 持久化存储路径
)
```

**主要方法**：

1. **add(video_id, feature, video_path, metadata, overwrite) -> bool**
   - 添加视频特征到库中
   - 自动归一化特征向量
   - 返回是否添加成功

2. **remove(video_id) -> bool**
   - 从库中删除视频记录
   - 注意：FAISS flat 索引不支持真正删除，仅标记删除

3. **search(query_feature, top_k) -> List[dict]**
   - 搜索最相似的视频
   - 返回相似视频列表（按相似度降序）

4. **get_record(video_id) -> Optional[VideoRecord]**
   - 获取指定视频的记录

5. **list_all() -> List[VideoRecord]**
   - 列出所有视频记录

6. **save(path) / load(path)**
   - 保存/加载特征库到文件

7. **get_statistics() -> dict**
   - 获取统计信息

**属性**：
- `size` - 存储的视频数量

### VideoRecord 数据类

```python
@dataclass
class VideoRecord:
    video_id: str                           # 视频唯一标识
    video_path: str                         # 视频文件路径
    added_time: str                         # 添加时间（ISO 格式）
    metadata: Optional[Dict[str, Any]]      # 附加元数据
```

### SimilarityCalculator 工具类

**静态方法**：

1. **cosine_similarity(a, b) -> float**
   - 计算两个向量的余弦相似度
   - 返回值范围 [-1, 1]

2. **batch_cosine_similarity(query, features) -> np.ndarray**
   - 批量计算余弦相似度
   - query: (D,), features: (N, D)
   - 返回: (N,)

3. **euclidean_distance(a, b) -> float**
   - 计算欧氏距离

4. **normalize(vector) -> np.ndarray**
   - L2 归一化

---

## 关键依赖与配置

### 依赖
- `faiss-cpu` 或 `faiss-gpu` - 向量检索（可选）
- `numpy` - 数值计算

### 索引类型

**flat 索引**（默认）：
- 精确搜索，100% 准确
- 适合小规模数据（<10万条）
- 内存占用：dimension × size × 4 bytes

**ivf 索引**：
- 近似搜索，速度更快
- 适合大规模数据（>10万条）
- 需要训练（至少 100 条数据）

### FAISS 可用性

```python
# 如果 FAISS 未安装，自动降级到 Numpy 实现
if not FAISS_AVAILABLE:
    print("[警告] faiss 未安装，将使用简单的 numpy 实现")
    # 功能相同，但性能较低
```

---

## 数据模型

### 存储结构

```
storage_path/
├── features.index           # FAISS 索引文件（或 features.npy）
└── metadata.json            # 元数据文件
```

### metadata.json 格式

```json
{
  "dimension": 512,
  "index_type": "flat",
  "records": {
    "video_001": {
      "video_id": "video_001",
      "video_path": "/path/to/video.mp4",
      "added_time": "2025-12-03T10:30:00",
      "metadata": {"category": "music_mv"}
    }
  },
  "id_to_idx": {
    "video_001": 0
  },
  "idx_to_id": {
    "0": "video_001"
  }
}
```

### 特征向量要求
- 类型：`np.ndarray`
- 数据类型：`float32`
- 形状：`(dimension,)`
- 归一化：自动进行 L2 归一化

---

## 测试与质量

### 单元测试

```python
def test_feature_store():
    store = FeatureStore(dimension=512)

    # 测试添加
    feature = np.random.randn(512).astype(np.float32)
    assert store.add("v1", feature, "/path/v1.mp4")
    assert store.size == 1

    # 测试搜索
    query = np.random.randn(512).astype(np.float32)
    results = store.search(query, top_k=1)
    assert len(results) == 1
    assert results[0]["video_id"] == "v1"

    # 测试删除
    assert store.remove("v1")
    assert store.size == 0
```

### 性能测试

```python
import time
import numpy as np
from src.whitelist.feature_store import FeatureStore

# 测试大规模数据
store = FeatureStore(dimension=512)

# 添加 10000 条数据
start = time.time()
for i in range(10000):
    feature = np.random.randn(512).astype(np.float32)
    store.add(f"video_{i}", feature, f"/path/{i}.mp4")
print(f"添加耗时: {time.time() - start:.2f}秒")

# 搜索测试
query = np.random.randn(512).astype(np.float32)
start = time.time()
results = store.search(query, top_k=10)
print(f"搜索耗时: {time.time() - start:.4f}秒")
```

---

## 常见问题 (FAQ)

### Q1: 如何选择索引类型？

- **数据量 < 10万**：使用 `flat`（精确搜索）
- **数据量 > 10万**：使用 `ivf`（近似搜索）

```python
# Flat 索引
store = FeatureStore(dimension=512, index_type="flat")

# IVF 索引
store = FeatureStore(dimension=512, index_type="ivf")
```

### Q2: FAISS 未安装怎么办？

系统会自动降级到 Numpy 实现，功能相同但性能较低。

```bash
# 安装 FAISS
pip install faiss-cpu  # CPU 版本
pip install faiss-gpu  # GPU 版本（需要 CUDA）
```

### Q3: 如何处理重复视频？

```python
# 方案 1：覆盖旧记录
store.add(video_id, feature, path, overwrite=True)

# 方案 2：先删除再添加
store.remove(video_id)
store.add(video_id, feature, path)
```

### Q4: 如何备份特征库？

```python
# 保存到指定路径
store.save("./backup/features_20251203")

# 从备份恢复
store.load("./backup/features_20251203")
```

### Q5: 搜索结果为空怎么办？

```python
# 检查特征库是否为空
if store.size == 0:
    print("特征库为空，需要先添加视频")

# 检查特征向量维度是否匹配
assert query_feature.shape == (store.dimension,)
```

### Q6: 如何查看存储占用？

```python
import os
from pathlib import Path

storage_path = Path("./data/features")
if storage_path.exists():
    total_size = sum(
        f.stat().st_size for f in storage_path.rglob("*") if f.is_file()
    )
    print(f"存储占用: {total_size / 1024 / 1024:.2f} MB")
```

---

## 相关文件清单

```
src/whitelist/
├── __init__.py              # 模块初始化
├── feature_store.py         # 特征存储（主文件）
└── similarity.py            # 相似度计算工具
```

---

**最后更新**: 2025-12-03
