[根目录](../../CLAUDE.md) > [src](../) > **pipeline**

# 审核流程模块 - src/pipeline/

## 变更记录 (Changelog)

### 2025-12-03
- 初始化模块文档

---

## 模块职责

整合特征提取、白名单匹配、决策判断等功能，提供完整的视频审核流水线。

**核心功能**：
- 白名单管理（添加/删除已审核视频）
- 视频审核决策（基于相似度匹配）
- 批量审核处理
- 结果持久化
- 反馈学习（人工审核结果加入白名单）

**注意**：此模块为可选模块，提供本地白名单方案，主程序不依赖此模块。

---

## 入口与启动

**主入口**：`review_pipeline.py`

**使用示例**：
```python
from src.pipeline.review_pipeline import VideoReviewPipeline

# 初始化流水线
pipeline = VideoReviewPipeline(
    storage_path="./data/features",
    auto_pass_threshold=0.90,
    auto_reject_threshold=0.60
)

# 建立白名单
pipeline.ingest_approved_videos([
    {"id": "v1", "path": "/path/to/approved1.mp4"},
    {"id": "v2", "path": "/path/to/approved2.mp4"},
])

# 审核新视频
result = pipeline.review("/path/to/new_video.mp4")
print(f"决策: {result.decision.value}")
print(f"原因: {result.reason}")
print(f"置信度: {result.confidence}")

# 批量审核
results, summary = pipeline.review_batch([
    "/path/to/video1.mp4",
    "/path/to/video2.mp4"
])

# 人工反馈（将通过的视频加入白名单）
pipeline.feedback_approved("/path/to/approved_video.mp4")

# 保存白名单
pipeline.save()
```

---

## 对外接口

### VideoReviewPipeline 类

**初始化参数**：
```python
VideoReviewPipeline(
    storage_path: Optional[str] = None,              # 特征库存储路径
    model_name: str = "openai/clip-vit-base-patch32", # CLIP 模型
    device: Optional[str] = None,                     # 运行设备
    auto_pass_threshold: float = 0.90,                # 自动通过阈值
    auto_reject_threshold: float = 0.60,              # 自动拒绝阈值
    enable_format_check: bool = True                  # 是否启用格式检查
)
```

**白名单管理方法**：

1. **ingest_approved_video(video_path, video_id, metadata) -> bool**
   - 将已审核通过的视频加入白名单
   - 返回是否添加成功

2. **ingest_approved_videos(videos, show_progress) -> dict**
   - 批量添加已审核通过的视频
   - 返回统计结果 `{"success": int, "failed": int}`

3. **remove_from_whitelist(video_id) -> bool**
   - 从白名单移除视频

**审核方法**：

4. **review(video_path) -> ReviewResult**
   - 审核单个视频
   - 返回审核结果对象

5. **review_batch(video_paths, show_progress, save_results) -> (List[ReviewResult], BatchReviewSummary)**
   - 批量审核视频
   - 返回结果列表和统计摘要

**反馈学习方法**：

6. **feedback_approved(video_path, video_id) -> bool**
   - 人工确认通过的视频，加入白名单

**持久化方法**：

7. **save(path) / load(path)**
   - 保存/加载特征库

**配置与统计方法**：

8. **get_statistics() -> dict**
   - 获取系统统计信息

9. **update_thresholds(auto_pass, auto_reject)**
   - 更新审核阈值

### ReviewResult 数据类

```python
@dataclass
class ReviewResult:
    decision: ReviewDecision        # 决策类型
    confidence: float               # 置信度
    reason: str                     # 原因说明
    similar_videos: List[dict]      # 相似视频列表
    metadata: VideoMetadata         # 视频元数据
    flags: List[str]                # 触发的规则标记
```

### ReviewDecision 枚举

```python
class ReviewDecision(Enum):
    APPROVED = "approved"           # 自动通过
    REJECTED = "rejected"           # 自动拒绝
    MANUAL_REVIEW = "manual_review" # 需人工复核
```

### BatchReviewSummary 数据类

```python
@dataclass
class BatchReviewSummary:
    total: int                      # 总数
    approved: int                   # 通过数
    rejected: int                   # 拒绝数
    manual_review: int              # 待复核数
    failed: int                     # 失败数
    duration_seconds: float         # 耗时（秒）
```

---

## 关键依赖与配置

### 依赖模块
- `src.features.video_encoder` - 特征提取
- `src.whitelist.feature_store` - 特征存储
- `src.pipeline.decision` - 决策逻辑

### 决策逻辑

**阈值配置**：
- `auto_pass_threshold = 0.90` - 相似度 ≥ 90% 自动通过
- `auto_reject_threshold = 0.60` - 相似度 ≤ 60% 自动拒绝
- 中间区域 → 人工复核

**决策流程**：
```
1. 格式检查（竖屏、黑边）→ 不符合直接拒绝
2. 提取特征向量
3. 搜索白名单中最相似的视频
4. 基于相似度决策：
   - ≥ 90% → 通过
   - ≤ 60% → 拒绝
   - 60%-90% → 人工复核
```

---

## 数据模型

### 审核结果 JSON 格式

```json
{
  "timestamp": "2025-12-03T10:30:00",
  "summary": {
    "total": 10,
    "approved": 7,
    "rejected": 2,
    "manual_review": 1,
    "failed": 0,
    "duration_seconds": 45.2
  },
  "results": [
    {
      "video_path": "/path/to/video.mp4",
      "decision": "approved",
      "confidence": 0.95,
      "reason": "与已通过视频高度相似 (95%)",
      "similar_videos": [
        {"video_id": "v1", "similarity": 0.95},
        {"video_id": "v2", "similarity": 0.88}
      ],
      "metadata": {
        "width": 1920,
        "height": 1080,
        "duration": 180.5,
        "is_vertical": false,
        "has_black_borders": false
      },
      "flags": null
    }
  ]
}
```

---

## 测试与质量

### 集成测试

```python
def test_pipeline():
    # 初始化
    pipeline = VideoReviewPipeline(storage_path="./test_features")

    # 建立白名单
    pipeline.ingest_approved_videos([
        {"id": "approved1", "path": "test_data/approved1.mp4"},
        {"id": "approved2", "path": "test_data/approved2.mp4"}
    ])

    # 审核测试视频
    result = pipeline.review("test_data/test_video.mp4")

    # 验证结果
    assert result.decision in [
        ReviewDecision.APPROVED,
        ReviewDecision.REJECTED,
        ReviewDecision.MANUAL_REVIEW
    ]
    assert 0 <= result.confidence <= 1

    # 清理
    import shutil
    shutil.rmtree("./test_features")
```

### 性能测试

```bash
# 测试批量审核性能
python -c "
from src.pipeline.review_pipeline import VideoReviewPipeline
import time

pipeline = VideoReviewPipeline()
video_paths = ['test1.mp4', 'test2.mp4', 'test3.mp4']

start = time.time()
results, summary = pipeline.review_batch(video_paths)
print(f'总耗时: {time.time() - start:.2f}秒')
print(f'平均: {summary.duration_seconds / summary.total:.2f}秒/视频')
"
```

---

## 常见问题 (FAQ)

### Q1: 如何调整审核阈值？

```python
# 初始化时设置
pipeline = VideoReviewPipeline(
    auto_pass_threshold=0.85,  # 降低通过阈值
    auto_reject_threshold=0.70  # 提高拒绝阈值
)

# 运行时更新
pipeline.update_thresholds(auto_pass=0.85, auto_reject=0.70)
```

### Q2: 白名单为空时会怎样？

返回 `MANUAL_REVIEW` 决策，提示需要建立初始白名单。

### Q3: 如何处理格式检查？

```python
# 禁用格式检查
pipeline = VideoReviewPipeline(enable_format_check=False)

# 启用格式检查（默认）
# 会自动拒绝竖屏视频和有黑边的视频
```

### Q4: 如何实现增量学习？

```python
# 方案 1：人工审核后添加
result = pipeline.review("video.mp4")
if result.decision == ReviewDecision.MANUAL_REVIEW:
    # 人工确认通过后
    pipeline.feedback_approved("video.mp4", "video_id")
    pipeline.save()  # 保存更新

# 方案 2：批量添加新的已审核视频
pipeline.ingest_approved_videos([
    {"id": "new1", "path": "approved/new1.mp4"},
    {"id": "new2", "path": "approved/new2.mp4"}
])
pipeline.save()
```

### Q5: 如何查看白名单统计？

```python
stats = pipeline.get_statistics()
print(f"白名单视频数: {stats['whitelist_size']}")
print(f"特征维度: {stats['feature_dimension']}")
print(f"显存使用: {stats['gpu_memory']}")
```

---

## 相关文件清单

```
src/pipeline/
├── __init__.py              # 模块初始化
├── decision.py              # 决策逻辑（ReviewDecisionMaker）
└── review_pipeline.py       # 审核流水线（主文件）
```

---

**最后更新**: 2025-12-03
