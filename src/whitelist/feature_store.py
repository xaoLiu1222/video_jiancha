"""
特征存储模块
使用 FAISS 进行高效的向量存储和相似度搜索
"""

import json
import pickle
import numpy as np
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("[警告] faiss 未安装，将使用简单的 numpy 实现")


@dataclass
class VideoRecord:
    """视频记录"""
    video_id: str
    video_path: str
    added_time: str
    metadata: Optional[Dict[str, Any]] = None


class FeatureStore:
    """
    特征向量存储

    支持:
    - 添加/删除视频特征
    - 基于相似度的快速检索
    - 持久化存储和加载
    """

    def __init__(
        self,
        dimension: int = 512,
        index_type: str = "flat",
        storage_path: Optional[Union[str, Path]] = None
    ):
        """
        初始化特征库

        Args:
            dimension: 特征向量维度
            index_type: 索引类型 ("flat" / "ivf")
            storage_path: 持久化存储路径
        """
        self.dimension = dimension
        self.index_type = index_type
        self.storage_path = Path(storage_path) if storage_path else None

        # 视频记录 (video_id -> VideoRecord)
        self.records: Dict[str, VideoRecord] = {}
        # ID 到索引位置的映射
        self.id_to_idx: Dict[str, int] = {}
        # 索引位置到 ID 的映射
        self.idx_to_id: Dict[int, str] = {}

        # 初始化索引
        self._init_index()

        # 如果指定了存储路径且文件存在，则加载
        if self.storage_path and self.storage_path.exists():
            self.load()

        print(f"[FeatureStore] 初始化完成，维度: {dimension}, 类型: {index_type}")

    def _init_index(self):
        """初始化 FAISS 索引"""
        if FAISS_AVAILABLE:
            if self.index_type == "flat":
                # 使用内积 (对于归一化向量等同于余弦相似度)
                self.index = faiss.IndexFlatIP(self.dimension)
            elif self.index_type == "ivf":
                # IVF 索引，适合大规模数据
                quantizer = faiss.IndexFlatIP(self.dimension)
                self.index = faiss.IndexIVFFlat(
                    quantizer, self.dimension, 100, faiss.METRIC_INNER_PRODUCT
                )
            else:
                raise ValueError(f"不支持的索引类型: {self.index_type}")
        else:
            # 简单的 numpy 实现
            self.features_matrix = np.zeros((0, self.dimension), dtype=np.float32)

    @property
    def size(self) -> int:
        """返回存储的视频数量"""
        return len(self.records)

    def add(
        self,
        video_id: str,
        feature: np.ndarray,
        video_path: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        overwrite: bool = False
    ) -> bool:
        """
        添加视频特征

        Args:
            video_id: 视频唯一标识
            feature: 特征向量
            video_path: 视频文件路径
            metadata: 附加元数据
            overwrite: 是否覆盖已存在的记录

        Returns:
            是否添加成功
        """
        # 检查是否已存在
        if video_id in self.records:
            if not overwrite:
                print(f"[FeatureStore] 视频已存在: {video_id}")
                return False
            else:
                # 删除旧记录
                self.remove(video_id)

        # 确保特征维度正确
        feature = np.asarray(feature, dtype=np.float32)
        if feature.shape != (self.dimension,):
            raise ValueError(f"特征维度不匹配: 期望 {self.dimension}, 实际 {feature.shape}")

        # 归一化 (确保余弦相似度计算正确)
        feature = feature / (np.linalg.norm(feature) + 1e-8)
        feature = feature.reshape(1, -1)

        # 添加到索引
        if FAISS_AVAILABLE:
            self.index.add(feature)
            idx = self.index.ntotal - 1
        else:
            self.features_matrix = np.vstack([self.features_matrix, feature])
            idx = len(self.features_matrix) - 1

        # 创建记录
        record = VideoRecord(
            video_id=video_id,
            video_path=video_path,
            added_time=datetime.now().isoformat(),
            metadata=metadata
        )
        self.records[video_id] = record
        self.id_to_idx[video_id] = idx
        self.idx_to_id[idx] = video_id

        return True

    def remove(self, video_id: str) -> bool:
        """
        删除视频记录

        注意: FAISS 的 flat 索引不支持真正的删除，这里只是标记删除

        Args:
            video_id: 视频唯一标识

        Returns:
            是否删除成功
        """
        if video_id not in self.records:
            return False

        idx = self.id_to_idx[video_id]
        del self.records[video_id]
        del self.id_to_idx[video_id]
        del self.idx_to_id[idx]

        # 注意: 实际的特征向量没有从索引中删除
        # 在 search 时会过滤掉已删除的结果

        return True

    def search(
        self,
        query_feature: np.ndarray,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        搜索最相似的视频

        Args:
            query_feature: 查询特征向量
            top_k: 返回结果数量

        Returns:
            相似视频列表 [{"video_id": str, "similarity": float, "record": VideoRecord}, ...]
        """
        if self.size == 0:
            return []

        # 预处理查询向量
        query_feature = np.asarray(query_feature, dtype=np.float32)
        query_feature = query_feature / (np.linalg.norm(query_feature) + 1e-8)
        query_feature = query_feature.reshape(1, -1)

        # 搜索
        if FAISS_AVAILABLE:
            # 多取一些结果，以防有被删除的
            k = min(top_k * 2, self.index.ntotal)
            scores, indices = self.index.search(query_feature, k)
            scores = scores[0]
            indices = indices[0]
        else:
            # Numpy 实现
            scores = np.dot(self.features_matrix, query_feature.T).flatten()
            indices = np.argsort(scores)[::-1][:top_k * 2]
            scores = scores[indices]

        # 过滤已删除的记录并构建结果
        results = []
        for score, idx in zip(scores, indices):
            if idx in self.idx_to_id:
                video_id = self.idx_to_id[idx]
                record = self.records[video_id]
                results.append({
                    "video_id": video_id,
                    "similarity": float(score),
                    "record": record
                })
                if len(results) >= top_k:
                    break

        return results

    def get_record(self, video_id: str) -> Optional[VideoRecord]:
        """获取视频记录"""
        return self.records.get(video_id)

    def list_all(self) -> List[VideoRecord]:
        """列出所有视频记录"""
        return list(self.records.values())

    def save(self, path: Optional[Union[str, Path]] = None):
        """
        保存特征库到文件

        Args:
            path: 存储路径，None 则使用初始化时的路径
        """
        save_path = Path(path) if path else self.storage_path
        if save_path is None:
            raise ValueError("未指定存储路径")

        save_path.mkdir(parents=True, exist_ok=True)

        # 保存索引
        if FAISS_AVAILABLE:
            faiss.write_index(self.index, str(save_path / "features.index"))
        else:
            np.save(save_path / "features.npy", self.features_matrix)

        # 保存元数据
        meta = {
            "dimension": self.dimension,
            "index_type": self.index_type,
            "records": {k: asdict(v) for k, v in self.records.items()},
            "id_to_idx": self.id_to_idx,
            "idx_to_id": {int(k): v for k, v in self.idx_to_id.items()}
        }
        with open(save_path / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        print(f"[FeatureStore] 已保存到: {save_path}, 共 {self.size} 条记录")

    def load(self, path: Optional[Union[str, Path]] = None):
        """
        从文件加载特征库

        Args:
            path: 存储路径，None 则使用初始化时的路径
        """
        load_path = Path(path) if path else self.storage_path
        if load_path is None:
            raise ValueError("未指定存储路径")

        if not load_path.exists():
            print(f"[FeatureStore] 路径不存在: {load_path}")
            return

        # 加载元数据
        meta_file = load_path / "metadata.json"
        if not meta_file.exists():
            print(f"[FeatureStore] 元数据文件不存在: {meta_file}")
            return

        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        self.dimension = meta["dimension"]
        self.index_type = meta["index_type"]
        self.records = {
            k: VideoRecord(**v) for k, v in meta["records"].items()
        }
        self.id_to_idx = meta["id_to_idx"]
        self.idx_to_id = {int(k): v for k, v in meta["idx_to_id"].items()}

        # 加载索引
        if FAISS_AVAILABLE:
            index_file = load_path / "features.index"
            if index_file.exists():
                self.index = faiss.read_index(str(index_file))
        else:
            npy_file = load_path / "features.npy"
            if npy_file.exists():
                self.features_matrix = np.load(npy_file)

        print(f"[FeatureStore] 已加载: {load_path}, 共 {self.size} 条记录")

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_videos": self.size,
            "dimension": self.dimension,
            "index_type": self.index_type,
            "faiss_available": FAISS_AVAILABLE,
            "storage_path": str(self.storage_path) if self.storage_path else None
        }


class SimilarityCalculator:
    """相似度计算工具类"""

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """计算余弦相似度"""
        a = a.flatten()
        b = b.flatten()
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

    @staticmethod
    def batch_cosine_similarity(
        query: np.ndarray,
        features: np.ndarray
    ) -> np.ndarray:
        """批量计算余弦相似度"""
        query = query.flatten()
        query_norm = query / (np.linalg.norm(query) + 1e-8)
        features_norm = features / (np.linalg.norm(features, axis=1, keepdims=True) + 1e-8)
        return np.dot(features_norm, query_norm)


if __name__ == "__main__":
    # 简单测试
    print("=" * 50)
    print("FeatureStore 测试")
    print("=" * 50)

    store = FeatureStore(dimension=512)

    # 添加测试数据
    for i in range(5):
        feat = np.random.randn(512).astype(np.float32)
        store.add(f"video_{i}", feat, f"/path/to/video_{i}.mp4")

    print(f"\n统计信息: {store.get_statistics()}")

    # 搜索测试
    query = np.random.randn(512).astype(np.float32)
    results = store.search(query, top_k=3)
    print(f"\n搜索结果:")
    for r in results:
        print(f"  - {r['video_id']}: {r['similarity']:.4f}")
