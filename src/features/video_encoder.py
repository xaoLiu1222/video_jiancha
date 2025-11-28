"""
视频特征提取器
使用 CLIP 模型提取视频帧的视觉特征
"""

import torch
import numpy as np
import cv2
from pathlib import Path
from typing import List, Optional, Union
from dataclasses import dataclass

from transformers import CLIPModel, CLIPProcessor


@dataclass
class VideoMetadata:
    """视频元数据"""
    width: int
    height: int
    fps: float
    total_frames: int
    duration: float  # 秒
    is_vertical: bool  # 是否竖屏
    has_black_borders: bool  # 是否有黑边


class VideoFeatureExtractor:
    """
    视频特征提取器

    使用 CLIP 模型将视频帧编码为特征向量，
    通过平均池化聚合为单个视频级别的特征表示
    """

    def __init__(
        self,
        model_name: str = "openai/clip-vit-base-patch32",
        device: Optional[str] = None,
        num_frames: int = 16
    ):
        """
        初始化特征提取器

        Args:
            model_name: CLIP 模型名称
            device: 运行设备 ("cuda" / "cpu" / None=自动)
            num_frames: 每个视频采样的帧数
        """
        self.model_name = model_name
        self.num_frames = num_frames

        # 自动选择设备
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        print(f"[VideoEncoder] 初始化中，使用设备: {self.device}")

        # 加载模型
        self.model = CLIPModel.from_pretrained(model_name)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model = self.model.to(self.device)
        self.model.eval()

        # 获取特征维度
        self.feature_dim = self.model.config.projection_dim

        print(f"[VideoEncoder] 模型加载完成，特征维度: {self.feature_dim}")

    def get_video_metadata(self, video_path: Union[str, Path]) -> VideoMetadata:
        """
        获取视频元数据

        Args:
            video_path: 视频文件路径

        Returns:
            VideoMetadata 对象
        """
        video_path = str(video_path)
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"无法打开视频文件: {video_path}")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0

        # 检测竖屏
        is_vertical = height > width

        # 检测黑边 (采样第一帧)
        ret, frame = cap.read()
        has_black_borders = self._detect_black_borders(frame) if ret else False

        cap.release()

        return VideoMetadata(
            width=width,
            height=height,
            fps=fps,
            total_frames=total_frames,
            duration=duration,
            is_vertical=is_vertical,
            has_black_borders=has_black_borders
        )

    def _detect_black_borders(
        self,
        frame: np.ndarray,
        threshold: int = 20,
        border_ratio: float = 0.05
    ) -> bool:
        """
        检测视频帧是否有黑边

        Args:
            frame: BGR 格式的视频帧
            threshold: 黑色像素阈值
            border_ratio: 边缘检测区域占比

        Returns:
            是否有黑边
        """
        if frame is None:
            return False

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        border_h = int(h * border_ratio)
        border_w = int(w * border_ratio)

        # 检测四个边缘
        top = gray[:border_h, :]
        bottom = gray[-border_h:, :]
        left = gray[:, :border_w]
        right = gray[:, -border_w:]

        # 判断是否为黑色 (均值低于阈值)
        borders = [top, bottom, left, right]
        black_borders = sum(1 for b in borders if np.mean(b) < threshold)

        # 任意一边有黑边就返回 True
        return black_borders > 0

    def extract_frames(
        self,
        video_path: Union[str, Path],
        num_frames: Optional[int] = None
    ) -> List[np.ndarray]:
        """
        从视频中均匀采样帧

        Args:
            video_path: 视频文件路径
            num_frames: 采样帧数，None 则使用默认值

        Returns:
            RGB 格式的帧列表
        """
        video_path = str(video_path)
        num_frames = num_frames or self.num_frames

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频文件: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if total_frames == 0:
            cap.release()
            raise ValueError(f"视频帧数为0: {video_path}")

        # 均匀采样帧索引
        if total_frames <= num_frames:
            indices = list(range(total_frames))
        else:
            indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)

        frames = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                # BGR -> RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(frame)

        cap.release()

        if len(frames) == 0:
            raise ValueError(f"无法从视频中提取帧: {video_path}")

        return frames

    def encode_frames(self, frames: List[np.ndarray]) -> np.ndarray:
        """
        将帧列表编码为特征向量

        Args:
            frames: RGB 格式的帧列表

        Returns:
            聚合后的特征向量 (归一化)
        """
        # 预处理
        inputs = self.processor(images=frames, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # 提取特征
        with torch.no_grad():
            features = self.model.get_image_features(**inputs)

        # 聚合 (平均池化)
        video_feature = features.mean(dim=0).cpu().numpy()

        # L2 归一化
        video_feature = video_feature / (np.linalg.norm(video_feature) + 1e-8)

        return video_feature.astype(np.float32)

    def encode(self, video_path: Union[str, Path]) -> np.ndarray:
        """
        提取视频的特征向量 (主入口)

        Args:
            video_path: 视频文件路径

        Returns:
            归一化的特征向量
        """
        frames = self.extract_frames(video_path)
        return self.encode_frames(frames)

    def encode_batch(
        self,
        video_paths: List[Union[str, Path]],
        show_progress: bool = True
    ) -> List[np.ndarray]:
        """
        批量提取视频特征

        Args:
            video_paths: 视频路径列表
            show_progress: 是否显示进度

        Returns:
            特征向量列表
        """
        features = []
        total = len(video_paths)

        for i, path in enumerate(video_paths):
            if show_progress:
                print(f"[VideoEncoder] 处理进度: {i+1}/{total} - {Path(path).name}")

            try:
                feat = self.encode(path)
                features.append(feat)
            except Exception as e:
                print(f"[VideoEncoder] 处理失败: {path}, 错误: {e}")
                features.append(None)

        return features

    def get_gpu_memory_usage(self) -> dict:
        """获取 GPU 显存使用情况"""
        if self.device == "cuda":
            allocated = torch.cuda.memory_allocated() / 1024**3
            reserved = torch.cuda.memory_reserved() / 1024**3
            total = torch.cuda.get_device_properties(0).total_memory / 1024**3
            return {
                "allocated_gb": round(allocated, 2),
                "reserved_gb": round(reserved, 2),
                "total_gb": round(total, 2),
                "free_gb": round(total - allocated, 2)
            }
        return {"device": "cpu"}


if __name__ == "__main__":
    # 简单测试
    print("=" * 50)
    print("VideoFeatureExtractor 测试")
    print("=" * 50)

    extractor = VideoFeatureExtractor()
    print(f"\n显存使用: {extractor.get_gpu_memory_usage()}")
