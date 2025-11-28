"""
审核决策模块
基于白名单特征库进行视频审核决策
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import numpy as np

from ..features.video_encoder import VideoFeatureExtractor, VideoMetadata
from ..whitelist.feature_store import FeatureStore


class ReviewDecision(Enum):
    """审核决策类型"""
    APPROVED = "approved"           # 自动通过
    REJECTED = "rejected"           # 自动拒绝
    MANUAL_REVIEW = "manual_review" # 需人工复核


@dataclass
class ReviewResult:
    """审核结果"""
    decision: ReviewDecision
    confidence: float
    reason: str
    similar_videos: List[Dict[str, Any]]
    metadata: Optional[VideoMetadata] = None
    flags: Optional[List[str]] = None  # 触发的规则标记

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "confidence": round(self.confidence, 4),
            "reason": self.reason,
            "similar_videos": [
                {"video_id": v["video_id"], "similarity": round(v["similarity"], 4)}
                for v in self.similar_videos
            ],
            "metadata": {
                "width": self.metadata.width,
                "height": self.metadata.height,
                "duration": round(self.metadata.duration, 2),
                "is_vertical": self.metadata.is_vertical,
                "has_black_borders": self.metadata.has_black_borders
            } if self.metadata else None,
            "flags": self.flags
        }


class ReviewDecisionMaker:
    """
    审核决策器

    基于视频特征与白名单库的相似度进行决策，
    同时检查基础规则（竖屏、黑边等）
    """

    def __init__(
        self,
        feature_store: FeatureStore,
        extractor: VideoFeatureExtractor,
        auto_pass_threshold: float = 0.90,
        auto_reject_threshold: float = 0.60,
        enable_format_check: bool = True
    ):
        """
        初始化决策器

        Args:
            feature_store: 特征库
            extractor: 特征提取器
            auto_pass_threshold: 自动通过阈值 (相似度高于此值)
            auto_reject_threshold: 自动拒绝阈值 (相似度低于此值)
            enable_format_check: 是否启用格式检查（竖屏、黑边）
        """
        self.store = feature_store
        self.extractor = extractor
        self.auto_pass_threshold = auto_pass_threshold
        self.auto_reject_threshold = auto_reject_threshold
        self.enable_format_check = enable_format_check

    def review(self, video_path: str, top_k: int = 5) -> ReviewResult:
        """
        审核视频

        Args:
            video_path: 视频文件路径
            top_k: 返回的相似视频数量

        Returns:
            审核结果
        """
        flags = []

        # 1. 获取视频元数据并检查格式
        try:
            metadata = self.extractor.get_video_metadata(video_path)
        except Exception as e:
            return ReviewResult(
                decision=ReviewDecision.REJECTED,
                confidence=1.0,
                reason=f"无法读取视频文件: {e}",
                similar_videos=[],
                metadata=None,
                flags=["read_error"]
            )

        # 格式检查
        if self.enable_format_check:
            if metadata.is_vertical:
                flags.append("vertical_video")
            if metadata.has_black_borders:
                flags.append("black_borders")

            # 如果格式不符合要求，直接拒绝
            if flags:
                return ReviewResult(
                    decision=ReviewDecision.REJECTED,
                    confidence=1.0,
                    reason=f"视频格式不符合要求: {', '.join(flags)}",
                    similar_videos=[],
                    metadata=metadata,
                    flags=flags
                )

        # 2. 提取特征
        try:
            feature = self.extractor.encode(video_path)
        except Exception as e:
            return ReviewResult(
                decision=ReviewDecision.REJECTED,
                confidence=1.0,
                reason=f"特征提取失败: {e}",
                similar_videos=[],
                metadata=metadata,
                flags=["extraction_error"]
            )

        # 3. 搜索相似视频
        if self.store.size == 0:
            return ReviewResult(
                decision=ReviewDecision.MANUAL_REVIEW,
                confidence=0.0,
                reason="特征库为空，需要人工审核建立初始白名单",
                similar_videos=[],
                metadata=metadata,
                flags=["empty_store"]
            )

        similar_videos = self.store.search(feature, top_k=top_k)

        if not similar_videos:
            return ReviewResult(
                decision=ReviewDecision.MANUAL_REVIEW,
                confidence=0.0,
                reason="未找到相似视频",
                similar_videos=[],
                metadata=metadata,
                flags=["no_match"]
            )

        # 4. 基于相似度决策
        max_similarity = similar_videos[0]["similarity"]

        if max_similarity >= self.auto_pass_threshold:
            decision = ReviewDecision.APPROVED
            reason = f"与已通过视频高度相似 ({max_similarity:.2%})"
        elif max_similarity <= self.auto_reject_threshold:
            decision = ReviewDecision.REJECTED
            reason = f"与已通过视频差异较大 ({max_similarity:.2%})"
            flags.append("low_similarity")
        else:
            decision = ReviewDecision.MANUAL_REVIEW
            reason = f"相似度中等 ({max_similarity:.2%})，建议人工复核"

        return ReviewResult(
            decision=decision,
            confidence=max_similarity,
            reason=reason,
            similar_videos=similar_videos,
            metadata=metadata,
            flags=flags if flags else None
        )

    def update_thresholds(
        self,
        auto_pass: Optional[float] = None,
        auto_reject: Optional[float] = None
    ):
        """动态更新阈值"""
        if auto_pass is not None:
            self.auto_pass_threshold = auto_pass
        if auto_reject is not None:
            self.auto_reject_threshold = auto_reject

    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return {
            "auto_pass_threshold": self.auto_pass_threshold,
            "auto_reject_threshold": self.auto_reject_threshold,
            "enable_format_check": self.enable_format_check,
            "feature_store_size": self.store.size
        }
