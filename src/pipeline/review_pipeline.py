"""
视频审核流水线
整合所有模块的主流程
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime

from ..features.video_encoder import VideoFeatureExtractor
from ..whitelist.feature_store import FeatureStore
from .decision import ReviewDecisionMaker, ReviewResult, ReviewDecision


@dataclass
class BatchReviewSummary:
    """批量审核结果摘要"""
    total: int
    approved: int
    rejected: int
    manual_review: int
    failed: int
    duration_seconds: float


class VideoReviewPipeline:
    """
    视频审核流水线

    提供完整的视频审核流程：
    1. 初始化：建立白名单特征库
    2. 审核：基于白名单进行相似度匹配
    3. 反馈：将人工审核结果加入白名单

    使用示例:
        ```python
        pipeline = VideoReviewPipeline(storage_path="./data/features")

        # 建立白名单
        pipeline.ingest_approved_videos([
            {"id": "v1", "path": "/path/to/video1.mp4"},
            {"id": "v2", "path": "/path/to/video2.mp4"},
        ])

        # 审核新视频
        result = pipeline.review("/path/to/new_video.mp4")
        print(result.to_dict())
        ```
    """

    def __init__(
        self,
        storage_path: Optional[Union[str, Path]] = None,
        model_name: str = "openai/clip-vit-base-patch32",
        device: Optional[str] = None,
        auto_pass_threshold: float = 0.90,
        auto_reject_threshold: float = 0.60,
        enable_format_check: bool = True
    ):
        """
        初始化审核流水线

        Args:
            storage_path: 特征库存储路径
            model_name: CLIP 模型名称
            device: 运行设备
            auto_pass_threshold: 自动通过阈值
            auto_reject_threshold: 自动拒绝阈值
            enable_format_check: 是否启用格式检查
        """
        self.storage_path = Path(storage_path) if storage_path else None

        print("=" * 60)
        print("视频审核流水线初始化中...")
        print("=" * 60)

        # 初始化特征提取器
        print("\n[1/3] 加载特征提取模型...")
        self.extractor = VideoFeatureExtractor(
            model_name=model_name,
            device=device
        )

        # 初始化特征库
        print("\n[2/3] 初始化特征库...")
        self.store = FeatureStore(
            dimension=self.extractor.feature_dim,
            storage_path=self.storage_path
        )

        # 初始化决策器
        print("\n[3/3] 初始化决策引擎...")
        self.decision_maker = ReviewDecisionMaker(
            feature_store=self.store,
            extractor=self.extractor,
            auto_pass_threshold=auto_pass_threshold,
            auto_reject_threshold=auto_reject_threshold,
            enable_format_check=enable_format_check
        )

        print("\n" + "=" * 60)
        print("初始化完成!")
        print(f"  - 特征维度: {self.extractor.feature_dim}")
        print(f"  - 白名单视频数: {self.store.size}")
        print(f"  - 显存使用: {self.extractor.get_gpu_memory_usage()}")
        print("=" * 60 + "\n")

    # ==================== 白名单管理 ====================

    def ingest_approved_video(
        self,
        video_path: Union[str, Path],
        video_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        将已审核通过的视频加入白名单

        Args:
            video_path: 视频文件路径
            video_id: 视频唯一标识（默认使用文件名）
            metadata: 附加元数据

        Returns:
            是否添加成功
        """
        video_path = Path(video_path)

        if not video_path.exists():
            print(f"[错误] 视频文件不存在: {video_path}")
            return False

        if video_id is None:
            video_id = video_path.stem

        try:
            # 提取特征
            feature = self.extractor.encode(str(video_path))

            # 添加到特征库
            success = self.store.add(
                video_id=video_id,
                feature=feature,
                video_path=str(video_path),
                metadata=metadata
            )

            if success:
                print(f"[白名单] 已添加: {video_id}")

            return success

        except Exception as e:
            print(f"[错误] 添加失败 ({video_id}): {e}")
            return False

    def ingest_approved_videos(
        self,
        videos: List[Dict[str, Any]],
        show_progress: bool = True
    ) -> Dict[str, int]:
        """
        批量添加已审核通过的视频

        Args:
            videos: 视频列表 [{"id": str, "path": str, "metadata": dict}, ...]
            show_progress: 是否显示进度

        Returns:
            统计结果 {"success": int, "failed": int}
        """
        success_count = 0
        failed_count = 0
        total = len(videos)

        for i, video in enumerate(videos):
            if show_progress:
                print(f"[进度] {i+1}/{total}")

            video_id = video.get("id")
            video_path = video.get("path")
            metadata = video.get("metadata")

            if self.ingest_approved_video(video_path, video_id, metadata):
                success_count += 1
            else:
                failed_count += 1

        # 自动保存
        if self.storage_path:
            self.save()

        return {"success": success_count, "failed": failed_count}

    def remove_from_whitelist(self, video_id: str) -> bool:
        """从白名单移除视频"""
        success = self.store.remove(video_id)
        if success:
            print(f"[白名单] 已移除: {video_id}")
        return success

    # ==================== 视频审核 ====================

    def review(self, video_path: Union[str, Path]) -> ReviewResult:
        """
        审核单个视频

        Args:
            video_path: 视频文件路径

        Returns:
            审核结果
        """
        return self.decision_maker.review(str(video_path))

    def review_batch(
        self,
        video_paths: List[Union[str, Path]],
        show_progress: bool = True,
        save_results: Optional[Union[str, Path]] = None
    ) -> tuple[List[ReviewResult], BatchReviewSummary]:
        """
        批量审核视频

        Args:
            video_paths: 视频路径列表
            show_progress: 是否显示进度
            save_results: 结果保存路径（JSON）

        Returns:
            (审核结果列表, 统计摘要)
        """
        import time
        start_time = time.time()

        results = []
        approved = rejected = manual_review = failed = 0
        total = len(video_paths)

        for i, path in enumerate(video_paths):
            if show_progress:
                print(f"\n[审核进度] {i+1}/{total}: {Path(path).name}")

            try:
                result = self.review(path)
                results.append(result)

                # 统计
                if result.decision == ReviewDecision.APPROVED:
                    approved += 1
                    status = "✓ 通过"
                elif result.decision == ReviewDecision.REJECTED:
                    rejected += 1
                    status = "✗ 拒绝"
                else:
                    manual_review += 1
                    status = "? 待复核"

                if show_progress:
                    print(f"  {status} | 相似度: {result.confidence:.2%} | {result.reason}")

            except Exception as e:
                failed += 1
                print(f"  [错误] {e}")
                results.append(None)

        duration = time.time() - start_time

        summary = BatchReviewSummary(
            total=total,
            approved=approved,
            rejected=rejected,
            manual_review=manual_review,
            failed=failed,
            duration_seconds=round(duration, 2)
        )

        # 保存结果
        if save_results:
            self._save_batch_results(video_paths, results, summary, save_results)

        # 打印统计
        print("\n" + "=" * 50)
        print("批量审核完成!")
        print(f"  总计: {total}")
        print(f"  通过: {approved} ({approved/total*100:.1f}%)")
        print(f"  拒绝: {rejected} ({rejected/total*100:.1f}%)")
        print(f"  待复核: {manual_review} ({manual_review/total*100:.1f}%)")
        print(f"  失败: {failed}")
        print(f"  耗时: {duration:.1f}秒 ({duration/total:.2f}秒/视频)")
        print("=" * 50)

        return results, summary

    def _save_batch_results(
        self,
        video_paths: List[Union[str, Path]],
        results: List[Optional[ReviewResult]],
        summary: BatchReviewSummary,
        save_path: Union[str, Path]
    ):
        """保存批量审核结果"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": summary.total,
                "approved": summary.approved,
                "rejected": summary.rejected,
                "manual_review": summary.manual_review,
                "failed": summary.failed,
                "duration_seconds": summary.duration_seconds
            },
            "results": []
        }

        for path, result in zip(video_paths, results):
            if result:
                item = result.to_dict()
                item["video_path"] = str(path)
            else:
                item = {"video_path": str(path), "error": "处理失败"}
            data["results"].append(item)

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n[保存] 结果已保存到: {save_path}")

    # ==================== 反馈学习 ====================

    def feedback_approved(
        self,
        video_path: Union[str, Path],
        video_id: Optional[str] = None
    ) -> bool:
        """
        人工确认通过的视频，加入白名单（增量学习）

        Args:
            video_path: 视频路径
            video_id: 视频ID

        Returns:
            是否成功
        """
        return self.ingest_approved_video(video_path, video_id)

    # ==================== 持久化 ====================

    def save(self, path: Optional[Union[str, Path]] = None):
        """保存特征库"""
        save_path = path or self.storage_path
        if save_path:
            self.store.save(save_path)

    def load(self, path: Optional[Union[str, Path]] = None):
        """加载特征库"""
        load_path = path or self.storage_path
        if load_path:
            self.store.load(load_path)

    # ==================== 配置与统计 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        return {
            "whitelist_size": self.store.size,
            "feature_dimension": self.extractor.feature_dim,
            "gpu_memory": self.extractor.get_gpu_memory_usage(),
            "decision_config": self.decision_maker.get_config(),
            "storage_path": str(self.storage_path) if self.storage_path else None
        }

    def update_thresholds(
        self,
        auto_pass: Optional[float] = None,
        auto_reject: Optional[float] = None
    ):
        """更新审核阈值"""
        self.decision_maker.update_thresholds(auto_pass, auto_reject)
        print(f"[配置] 阈值已更新: 通过>{auto_pass}, 拒绝<{auto_reject}")
