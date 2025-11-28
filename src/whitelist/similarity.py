"""
相似度计算模块
"""

import numpy as np
from typing import List, Tuple


class SimilarityCalculator:
    """相似度计算工具类"""

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """
        计算两个向量的余弦相似度

        Args:
            a: 向量 a
            b: 向量 b

        Returns:
            相似度 [-1, 1]
        """
        a = a.flatten()
        b = b.flatten()
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

    @staticmethod
    def batch_cosine_similarity(
        query: np.ndarray,
        features: np.ndarray
    ) -> np.ndarray:
        """
        批量计算余弦相似度

        Args:
            query: 查询向量 (D,)
            features: 特征矩阵 (N, D)

        Returns:
            相似度数组 (N,)
        """
        query = query.flatten()
        query_norm = query / (np.linalg.norm(query) + 1e-8)
        features_norm = features / (np.linalg.norm(features, axis=1, keepdims=True) + 1e-8)
        return np.dot(features_norm, query_norm)

    @staticmethod
    def euclidean_distance(a: np.ndarray, b: np.ndarray) -> float:
        """计算欧氏距离"""
        return float(np.linalg.norm(a.flatten() - b.flatten()))

    @staticmethod
    def normalize(vector: np.ndarray) -> np.ndarray:
        """L2 归一化"""
        norm = np.linalg.norm(vector)
        if norm < 1e-8:
            return vector
        return vector / norm
