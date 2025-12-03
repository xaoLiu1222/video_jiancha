[根目录](../../CLAUDE.md) > [src](../) > **features**

# 特征提取模块 - src/features/

## 变更记录 (Changelog)

### 2025-12-03
- 初始化模块文档

---

## 模块职责

使用 CLIP 多模态模型提取视频的视觉特征向量，用于本地白名单方案的相似度匹配。

**核心功能**：
- 视频帧均匀采样
- 视频元数据提取（分辨率、时长、竖屏检测、黑边检测）
- CLIP 模型编码（将视频帧转换为特征向量）
- 批量处理支持

**注意**：此模块为可选模块，主程序 `siliconflow_review.py` 不依赖此模块。

---

## 入口与启动

**主入口**：`video_encoder.py`

**使用示例**：
```python
from src.features.video_encoder import VideoFeatureExtractor

# 初始化提取器
extractor = VideoFeatureExtractor(
    model_name="openai/clip-vit-base-patch32",
    device="cuda",  # 或 "cpu"
    num_frames=16
)

# 提取单个视频特征
feature = extractor.encode("/path/to/video.mp4")
print(f"特征维度: {feature.shape}")  # (512,)

# 获取视频元数据
metadata = extractor.get_video_metadata("/path/to/video.mp4")
print(f"分辨率: {metadata.width}x{metadata.height}")
print(f"时长: {metadata.duration}秒")
print(f"竖屏: {metadata.is_vertical}")
print(f"黑边: {metadata.has_black_borders}")

# 批量处理
features = extractor.encode_batch([
    "/path/to/video1.mp4",
    "/path/to/video2.mp4"
])
```

---

## 对外接口

### VideoFeatureExtractor 类

**初始化参数**：
```python
VideoFeatureExtractor(
    model_name: str = "openai/clip-vit-base-patch32",  # CLIP 模型
    device: Optional[str] = None,                      # "cuda"/"cpu"/None
    num_frames: int = 16                               # 采样帧数
)
```

**主要方法**：

1. **encode(video_path) -> np.ndarray**
   - 提取视频特征向量（主入口）
   - 返回归一化的特征向量 (512,)

2. **get_video_metadata(video_path) -> VideoMetadata**
   - 获取视频元数据
   - 返回 VideoMetadata 对象

3. **extract_frames(video_path, num_frames) -> List[np.ndarray]**
   - 从视频中均匀采样帧
   - 返回 RGB 格式的帧列表

4. **encode_frames(frames) -> np.ndarray**
   - 将帧列表编码为特征向量
   - 使用平均池化聚合多帧特征

5. **encode_batch(video_paths, show_progress) -> List[np.ndarray]**
   - 批量提取视频特征
   - 支持进度显示

6. **get_gpu_memory_usage() -> dict**
   - 获取 GPU 显存使用情况

### VideoMetadata 数据类

```python
@dataclass
class VideoMetadata:
    width: int                  # 宽度
    height: int                 # 高度
    fps: float                  # 帧率
    total_frames: int           # 总帧数
    duration: float             # 时长（秒）
    is_vertical: bool           # 是否竖屏
    has_black_borders: bool     # 是否有黑边
```

---

## 关键依赖与配置

### 依赖
- `torch` - PyTorch 深度学习框架
- `transformers` - Hugging Face Transformers（CLIP 模型）
- `opencv-python` - 视频处理
- `numpy` - 数值计算

### 配置

**模型选择**：
- `openai/clip-vit-base-patch32` - 基础版（512 维，速度快）
- `openai/clip-vit-large-patch14` - 大模型（768 维，更准确）

**设备选择**：
- `cuda` - GPU 加速（需要 NVIDIA GPU）
- `cpu` - CPU 运行（较慢）
- `None` - 自动选择

**采样帧数**：
- 默认 16 帧
- 更多帧 → 更准确，但更慢
- 更少帧 → 更快，但可能不准确

---

## 数据模型

### 特征向量格式
- 类型：`np.ndarray`
- 形状：`(512,)` 或 `(768,)` 取决于模型
- 数据类型：`float32`
- 归一化：L2 归一化（模长为 1）

### 帧采样策略
```python
# 均匀采样
indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)

# 示例：100 帧视频，采样 16 帧
# indices = [0, 6, 13, 20, 26, 33, 40, 46, 53, 60, 66, 73, 80, 86, 93, 99]
```

### 黑边检测算法
```python
# 检测四个边缘区域（各占 5%）
border_ratio = 0.05
# 判断像素均值是否低于阈值（默认 20）
threshold = 20
# 任意一边有黑边即返回 True
```

---

## 测试与质量

### 单元测试

```python
# 测试特征提取
def test_encode():
    extractor = VideoFeatureExtractor()
    feature = extractor.encode("test_video.mp4")
    assert feature.shape == (512,)
    assert np.abs(np.linalg.norm(feature) - 1.0) < 1e-5  # 归一化检查

# 测试元数据提取
def test_metadata():
    extractor = VideoFeatureExtractor()
    metadata = extractor.get_video_metadata("test_video.mp4")
    assert metadata.width > 0
    assert metadata.height > 0
    assert metadata.duration > 0
```

### 性能测试

```bash
# 测试处理速度
python -c "
import time
from src.features.video_encoder import VideoFeatureExtractor

extractor = VideoFeatureExtractor()
start = time.time()
feature = extractor.encode('test.mp4')
print(f'处理时间: {time.time() - start:.2f}秒')
print(f'显存使用: {extractor.get_gpu_memory_usage()}')
"
```

---

## 常见问题 (FAQ)

### Q1: 如何选择合适的采样帧数？

- **短视频（<1分钟）**：8-12 帧
- **中等视频（1-5分钟）**：16-24 帧
- **长视频（>5分钟）**：24-32 帧

### Q2: GPU 显存不足怎么办？

```python
# 方案 1：使用 CPU
extractor = VideoFeatureExtractor(device="cpu")

# 方案 2：减少采样帧数
extractor = VideoFeatureExtractor(num_frames=8)

# 方案 3：使用小模型
extractor = VideoFeatureExtractor(
    model_name="openai/clip-vit-base-patch32"
)
```

### Q3: 如何提高特征提取准确率？

1. 增加采样帧数
2. 使用更大的模型
3. 确保视频质量良好

### Q4: 黑边检测不准确怎么办？

```python
# 调整检测参数
# 在 _detect_black_borders() 方法中：
threshold = 30        # 提高阈值（默认 20）
border_ratio = 0.08   # 增加检测区域（默认 0.05）
```

### Q5: 如何处理损坏的视频？

```python
try:
    feature = extractor.encode(video_path)
except Exception as e:
    print(f"视频处理失败: {e}")
    # 标记为需要人工检查
```

---

## 相关文件清单

```
src/features/
├── __init__.py              # 模块初始化
└── video_encoder.py         # 视频特征提取器（主文件）
```

---

**最后更新**: 2025-12-03
