#!/usr/bin/env python3
"""
视频审核系统 - 使用硅基流动 + Qwen3-VL

基于大模型的智能视频审核工具，自动识别不符合标准的音乐 MV。

功能特点：
- 支持从配置文件读取 API 密钥和设置
- 支持自定义视频目录（如 U 盘等外部存储）
- 自动将视频分类移动到对应目录
- 详细的审核报告和 token 使用统计

使用方法：
    python siliconflow_review.py [视频目录路径]

示例：
    python siliconflow_review.py                    # 使用配置文件中的默认目录
    python siliconflow_review.py /media/usb/videos  # 指定 U 盘目录
    python siliconflow_review.py ~/Desktop/mv       # 指定桌面目录

作者：Video Review System
版本：1.0.0
"""

import os
import sys
import json
import base64
import shutil
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

import cv2
import yaml
import requests


class Config:
    """配置管理类"""

    def __init__(self, config_path: str = "./config/config.yaml"):
        """加载配置文件"""
        self.config_path = Path(config_path)

        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)
        else:
            self._config = {}
            print(f"⚠️  配置文件不存在: {config_path}，使用默认配置")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的嵌套键"""
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value if value != "" else default

    @property
    def api_key(self) -> Optional[str]:
        """获取 API 密钥（环境变量优先）"""
        return os.getenv("SILICONFLOW_API_KEY") or self.get("siliconflow.api_key")

    @property
    def model(self) -> str:
        """获取模型名称"""
        return self.get("siliconflow.model", "Qwen/Qwen3-VL-72B-Instruct")

    @property
    def api_base(self) -> str:
        """获取 API 基础地址"""
        return self.get("siliconflow.api_base", "https://api.siliconflow.cn/v1")

    @property
    def timeout(self) -> int:
        """获取 API 超时时间"""
        return self.get("siliconflow.timeout", 180)

    @property
    def video_dir(self) -> str:
        """获取视频目录"""
        return self.get("paths.video_dir", "./data/to_review")

    @property
    def approved_dir(self) -> str:
        """获取通过视频目录"""
        return self.get("paths.approved_dir", "./data/approved")

    @property
    def rejected_dir(self) -> str:
        """获取拒绝视频目录"""
        return self.get("paths.rejected_dir", "./data/rejected")

    @property
    def manual_review_dir(self) -> str:
        """获取人工复核目录"""
        return self.get("paths.manual_review_dir", "./data/manual_review")

    @property
    def results_path(self) -> str:
        """获取结果保存路径"""
        return self.get("paths.results_path", "./data/results/review_results.json")

    @property
    def num_frames(self) -> int:
        """获取采样帧数"""
        return self.get("video.num_frames", 6)

    @property
    def video_formats(self) -> List[str]:
        """获取支持的视频格式"""
        return self.get("video.formats", [".mp4", ".avi", ".mov", ".ts", ".mkv", ".flv"])

    @property
    def min_duration(self) -> int:
        """获取最小视频时长"""
        return self.get("video.min_duration", 120)

    @property
    def image_max_size(self) -> int:
        """获取图片最大尺寸"""
        return self.get("image.max_size", 512)

    @property
    def image_quality(self) -> int:
        """获取图片压缩质量"""
        return self.get("image.quality", 75)

    @property
    def max_tokens(self) -> int:
        """获取最大输出 token 数"""
        return self.get("model_params.max_tokens", 512)

    @property
    def temperature(self) -> float:
        """获取温度参数"""
        return self.get("model_params.temperature", 0.3)


class VideoFeatureExtractor:
    """视频特征提取器 - 支持智能关键帧检测"""

    def __init__(self, scene_threshold: float = 30.0):
        """
        初始化特征提取器

        Args:
            scene_threshold: 场景变化检测阈值（帧差异度，越小越敏感）
        """
        self.scene_threshold = scene_threshold

    def _calculate_frame_difference(self, frame1, frame2) -> float:
        """计算两帧之间的差异度（基于直方图比较）"""
        # 转换为灰度图
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        # 计算直方图
        hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])

        # 归一化
        cv2.normalize(hist1, hist1)
        cv2.normalize(hist2, hist2)

        # 计算相关性（1 表示完全相同，-1 表示完全不同）
        correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

        # 转换为差异度（0-100）
        difference = (1 - correlation) * 100
        return difference

    def extract_frames_smart(self, video_path: str, num_frames: int = 12,
                             min_interval: int = 30) -> List:
        """
        智能提取关键帧（基于场景变化检测）

        Args:
            video_path: 视频路径
            num_frames: 目标帧数
            min_interval: 最小帧间隔（避免提取过于相近的帧）

        Returns:
            提取的关键帧列表
        """
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"无法打开视频: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        if total_frames == 0:
            raise ValueError(f"视频帧数为 0: {video_path}")

        # 第一阶段：检测所有场景变化点
        scene_changes = [0]  # 始终包含第一帧
        prev_frame = None

        # 采样间隔（每秒采样 2 次进行场景检测）
        sample_interval = max(1, int(fps / 2))

        for frame_idx in range(0, total_frames, sample_interval):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()

            if not ret:
                continue

            if prev_frame is not None:
                diff = self._calculate_frame_difference(prev_frame, frame)

                # 检测到场景变化
                if diff > self.scene_threshold:
                    # 确保与上一个关键帧有足够间隔
                    if frame_idx - scene_changes[-1] >= min_interval:
                        scene_changes.append(frame_idx)

            prev_frame = frame.copy()

        # 始终包含最后一帧
        if total_frames - 1 not in scene_changes:
            scene_changes.append(total_frames - 1)

        # 第二阶段：选择最终的关键帧
        if len(scene_changes) >= num_frames:
            # 场景变化点足够多，均匀选择
            step = len(scene_changes) / num_frames
            selected_indices = [scene_changes[int(i * step)] for i in range(num_frames)]
        else:
            # 场景变化点不够，补充均匀采样
            selected_indices = scene_changes.copy()
            remaining = num_frames - len(selected_indices)

            if remaining > 0:
                # 在已有关键帧之间均匀插入
                uniform_indices = [int(i * total_frames / (remaining + 1))
                                   for i in range(1, remaining + 1)]

                for idx in uniform_indices:
                    # 避免与已有帧太近
                    if all(abs(idx - s) >= min_interval for s in selected_indices):
                        selected_indices.append(idx)

                selected_indices = sorted(selected_indices)[:num_frames]

        # 第三阶段：提取选中的帧
        frames = []
        for idx in selected_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()

            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(frame_rgb)

        cap.release()
        return frames

    def extract_frames(self, video_path: str, num_frames: int = 6) -> List:
        """从视频中均匀提取帧（保留原方法作为备选）"""
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"无法打开视频: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if total_frames == 0:
            raise ValueError(f"视频帧数为 0: {video_path}")

        # 均匀采样
        indices = [int(i * total_frames / num_frames) for i in range(num_frames)]
        frames = []

        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()

            if ret:
                # BGR -> RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(frame_rgb)

        cap.release()
        return frames


class SiliconFlowReviewer:
    """硅基流动视频审核器"""

    def __init__(self, config: Config, video_dir: Optional[str] = None):
        """
        初始化审核器

        Args:
            config: 配置对象
            video_dir: 视频目录（可选，覆盖配置文件）
        """
        self.config = config
        self.video_dir = Path(video_dir) if video_dir else Path(config.video_dir)

        # 初始化特征提取器（使用配置中的场景阈值）
        scene_threshold = config.get("video.scene_threshold", 30.0)
        self.extractor = VideoFeatureExtractor(scene_threshold=scene_threshold)

        # 设置输出目录（跟随输入目录）
        self.approved_dir = self.video_dir / "approved"
        self.rejected_dir = self.video_dir / "rejected"
        self.manual_review_dir = self.video_dir / "manual_review"
        self.results_path = self.video_dir / "review_results.json"

        # 审核规则提示词（详细版，提升精准度）
        self.review_prompt = """你是专业的音乐MV内容审核员。请仔细分析提供的视频帧截图，判断该MV是否符合发布标准。

## 审核规则（必须严格执行）

### 一、格式问题（自动拒绝）
1. **竖屏视频**：画面宽度小于高度（9:16等竖屏比例）
2. **上下黑边**：画面上方和下方存在明显黑色边框（信箱模式）
3. **左右黑边过大**：左右两侧黑边占据画面宽度超过50%

### 二、画质问题（自动拒绝）
4. **画面模糊**：整体画面不清晰，无法辨认人物面部或文字
5. **马赛克遮挡**：画面中存在明显的马赛克/模糊处理区域

### 三、内容问题（自动拒绝）
6. **林夕作品**：画面中出现"林夕"字样（作词人署名）
7. **暴露内容**：过度暴露的穿着、性暗示动作或画面
8. **导向问题**：涉及政治敏感、宗教极端、暴力血腥内容
9. **纯风景无人物**：整个视频只有风景画面，完全没有人物出现
10. **风景占比过高**：风景画面占据视频时长超过50%（根据提供的帧判断）
11. **广告内容**：包含商业广告、品牌植入、二维码、购买链接等
12. **吸毒画面**：出现吸食毒品、注射器、毒品相关道具等

## 审核要求

1. **逐帧分析**：仔细查看每一帧图片，不要遗漏任何问题
2. **综合判断**：结合所有帧的内容做出整体判断
3. **宁严勿松**：如有疑虑，倾向于拒绝或标记为需人工复核
4. **详细说明**：在reason中清楚说明发现的问题

## 返回格式（严格JSON）

```json
{
    "decision": "approved/rejected/manual_review",
    "reason": "详细说明判断依据，如发现问题请具体描述在哪一帧、什么内容",
    "confidence": 0.95,
    "flags": ["问题标签1", "问题标签2"],
    "frame_analysis": "简要描述各帧内容"
}
```

### decision 说明：
- **approved**：完全符合标准，可以发布
- **rejected**：存在明确违规内容，不可发布
- **manual_review**：存在疑虑但不确定，需人工复核

### flags 可选值：
vertical, black_border_top_bottom, black_border_left_right, blurry, mosaic, linxi_work, explicit_content, political_sensitive, no_person, too_much_scenery, advertisement, drug_related

请开始审核："""

    def encode_image_base64(self, image_path: str) -> str:
        """将图片压缩后编码为 base64"""
        img = cv2.imread(image_path)

        if img is None:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")

        # 计算缩放比例
        h, w = img.shape[:2]
        max_size = self.config.image_max_size

        if max(h, w) > max_size:
            scale = max_size / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # 压缩为 JPEG
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.config.image_quality]
        _, buffer = cv2.imencode('.jpg', img, encode_param)

        return base64.b64encode(buffer).decode("utf-8")

    def review_video(self, video_path: str) -> Dict[str, Any]:
        """审核单个视频"""
        print(f"\n{'='*60}")
        print(f"审核视频: {Path(video_path).name}")
        print(f"{'='*60}")

        # 检查视频时长
        print(f"\n[1/5] 检查视频时长...")
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        cap.release()

        print(f"  视频时长: {duration:.1f} 秒 ({duration/60:.1f} 分钟)")

        if duration < self.config.min_duration:
            return {
                "decision": "rejected",
                "reason": f"视频时长不足 {self.config.min_duration // 60} 分钟 (仅 {duration:.1f} 秒)",
                "confidence": 1.0,
                "flags": ["too_short"]
            }

        # 提取视频帧（使用智能关键帧检测）
        use_smart_extraction = self.config.get("video.smart_extraction", True)
        num_frames = self.config.num_frames

        if use_smart_extraction:
            print(f"\n[2/5] 智能提取关键帧 ({num_frames} 帧)...")
            try:
                frames = self.extractor.extract_frames_smart(
                    video_path,
                    num_frames=num_frames,
                    min_interval=self.config.get("video.min_frame_interval", 30)
                )
                print(f"  ✓ 智能提取 {len(frames)} 个关键帧（基于场景变化）")
            except Exception as e:
                print(f"  ⚠️ 智能提取失败，回退到均匀采样: {e}")
                frames = self.extractor.extract_frames(video_path, num_frames=num_frames)
                print(f"  ✓ 均匀采样 {len(frames)} 帧")
        else:
            print(f"\n[2/5] 均匀提取视频帧 ({num_frames} 帧)...")
            try:
                frames = self.extractor.extract_frames(video_path, num_frames=num_frames)
                print(f"  ✓ 成功提取 {len(frames)} 帧")
            except Exception as e:
                return {
                    "decision": "rejected",
                    "reason": f"无法读取视频: {e}",
                    "confidence": 1.0,
                    "error": str(e)
                }

        if not frames:
            return {
                "decision": "rejected",
                "reason": "无法从视频中提取帧",
                "confidence": 1.0,
                "error": "frame_extraction_failed"
            }

        # 保存帧为临时文件
        print(f"\n[3/5] 准备图片数据...")
        temp_dir = Path("./temp_frames")
        temp_dir.mkdir(exist_ok=True)

        frame_paths = []

        for i, frame in enumerate(frames):
            frame_path = temp_dir / f"frame_{i}.jpg"
            cv2.imwrite(str(frame_path), cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            frame_paths.append(frame_path)

        # 调用 API（第一轮审核）
        print(f"\n[4/5] 调用 {self.config.model} 模型...")

        try:
            result = self._call_api(frame_paths)
            print(f"  ✓ API 调用成功")
        except Exception as e:
            print(f"  ✗ API 调用失败: {e}")
            # 清理临时文件
            for fp in frame_paths:
                fp.unlink()
            return {
                "decision": "manual_review",
                "reason": f"API 调用失败: {e}",
                "confidence": 0.0,
                "error": str(e)
            }

        # 多轮审核机制：对低置信度结果进行二次确认
        confidence_threshold = self.config.get("review.confidence_threshold", 0.8)
        enable_double_check = self.config.get("review.enable_double_check", True)

        if enable_double_check and result.get("confidence", 1.0) < confidence_threshold:
            print(f"\n[5/5] 置信度较低 ({result.get('confidence', 0):.2f})，进行二次审核...")
            try:
                second_result = self._call_api_double_check(frame_paths, result)
                print(f"  ✓ 二次审核完成")

                # 综合两次结果
                result = self._merge_review_results(result, second_result)
            except Exception as e:
                print(f"  ⚠️ 二次审核失败: {e}")
                # 保持第一次结果，但标记需要人工复核
                if result.get("decision") != "rejected":
                    result["decision"] = "manual_review"
                    result["reason"] = f"二次审核失败，建议人工复核。原因: {result.get('reason', '')}"
        else:
            print(f"\n[5/5] 置信度足够 ({result.get('confidence', 1.0):.2f})，跳过二次审核")

        # 清理临时文件
        for fp in frame_paths:
            fp.unlink()

        return result

    def _call_api(self, frame_paths: List[Path]) -> Dict[str, Any]:
        """调用硅基流动 API"""
        content = [{"type": "text", "text": self.review_prompt}]

        for frame_path in frame_paths:
            image_base64 = self.encode_image_base64(str(frame_path))
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
            })

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature
        }

        response = requests.post(
            f"{self.config.api_base}/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.config.timeout
        )

        if response.status_code != 200:
            raise Exception(f"API 返回错误: {response.status_code} - {response.text}")

        result = response.json()
        content_text = result["choices"][0]["message"]["content"]

        # 提取 JSON
        if "```json" in content_text:
            content_text = content_text.split("```json")[1].split("```")[0].strip()
        elif "```" in content_text:
            content_text = content_text.split("```")[1].split("```")[0].strip()

        try:
            review_result = json.loads(content_text)
        except json.JSONDecodeError:
            review_result = {
                "decision": "manual_review",
                "reason": content_text,
                "confidence": 0.5
            }

        review_result["tokens_used"] = result.get("usage", {})

        return review_result

    def _call_api_double_check(self, frame_paths: List[Path], first_result: Dict[str, Any]) -> Dict[str, Any]:
        """二次审核 API 调用（针对低置信度结果）"""
        double_check_prompt = f"""你是专业的音乐MV内容审核员，正在进行二次复核。

## 第一次审核结果
- 决定：{first_result.get('decision', 'unknown')}
- 原因：{first_result.get('reason', '未知')}
- 置信度：{first_result.get('confidence', 0)}
- 标记：{first_result.get('flags', [])}

## 二次审核要求

请重新仔细审核这些视频帧，特别关注：
1. 第一次审核提到的问题是否确实存在
2. 是否有遗漏的其他问题
3. 如果第一次判断为 rejected，确认是否真的需要拒绝
4. 如果第一次判断为 approved，确认是否真的没有问题

## 审核规则（与第一次相同）

### 格式问题：竖屏、���下黑边、左右黑边过大
### 画质问题：画面模糊、马赛克遮挡
### 内容问题：林夕作品、暴露/导向问题、纯风景无人物、风景占比过高、广告、吸毒画面

## 返回格式

```json
{{
    "decision": "approved/rejected/manual_review",
    "reason": "二次审核的详细判断依据",
    "confidence": 0.95,
    "flags": [],
    "agrees_with_first": true/false,
    "disagreement_reason": "如果不同意第一次结果，说明原因"
}}
```

请开始二次审核："""

        content = [{"type": "text", "text": double_check_prompt}]

        for frame_path in frame_paths:
            image_base64 = self.encode_image_base64(str(frame_path))
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
            })

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        # 二次审核使用更低的温度以获得更稳定的结果
        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": self.config.max_tokens,
            "temperature": 0.1  # 更低的温度
        }

        response = requests.post(
            f"{self.config.api_base}/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.config.timeout
        )

        if response.status_code != 200:
            raise Exception(f"API 返回错误: {response.status_code} - {response.text}")

        result = response.json()
        content_text = result["choices"][0]["message"]["content"]

        # 提取 JSON
        if "```json" in content_text:
            content_text = content_text.split("```json")[1].split("```")[0].strip()
        elif "```" in content_text:
            content_text = content_text.split("```")[1].split("```")[0].strip()

        try:
            review_result = json.loads(content_text)
        except json.JSONDecodeError:
            review_result = {
                "decision": "manual_review",
                "reason": content_text,
                "confidence": 0.5
            }

        review_result["tokens_used"] = result.get("usage", {})

        return review_result

    def _merge_review_results(self, first: Dict[str, Any], second: Dict[str, Any]) -> Dict[str, Any]:
        """合并两次审核结果"""
        first_decision = first.get("decision", "manual_review")
        second_decision = second.get("decision", "manual_review")
        first_confidence = first.get("confidence", 0.5)
        second_confidence = second.get("confidence", 0.5)

        # 合并 token 使用量
        first_tokens = first.get("tokens_used", {})
        second_tokens = second.get("tokens_used", {})
        total_tokens = {
            "prompt_tokens": first_tokens.get("prompt_tokens", 0) + second_tokens.get("prompt_tokens", 0),
            "completion_tokens": first_tokens.get("completion_tokens", 0) + second_tokens.get("completion_tokens", 0),
            "total_tokens": first_tokens.get("total_tokens", 0) + second_tokens.get("total_tokens", 0)
        }

        # 决策逻辑
        if first_decision == second_decision:
            # 两次结果一致，提高置信度
            merged = {
                "decision": first_decision,
                "reason": f"[一致] {first.get('reason', '')}",
                "confidence": min(1.0, (first_confidence + second_confidence) / 2 + 0.1),
                "flags": list(set(first.get("flags", []) + second.get("flags", []))),
                "double_checked": True,
                "first_result": first_decision,
                "second_result": second_decision
            }
        elif first_decision == "rejected" or second_decision == "rejected":
            # 任一次判断为拒绝，倾向于拒绝（宁严勿松）
            rejected_result = first if first_decision == "rejected" else second
            merged = {
                "decision": "rejected",
                "reason": f"[二次确认拒绝] {rejected_result.get('reason', '')}",
                "confidence": max(first_confidence, second_confidence),
                "flags": list(set(first.get("flags", []) + second.get("flags", []))),
                "double_checked": True,
                "first_result": first_decision,
                "second_result": second_decision
            }
        else:
            # 结果不一致且都不是拒绝，标记为人工复核
            merged = {
                "decision": "manual_review",
                "reason": f"[结果不一致] 第一次: {first.get('reason', '')} | 第二次: {second.get('reason', '')}",
                "confidence": (first_confidence + second_confidence) / 2,
                "flags": list(set(first.get("flags", []) + second.get("flags", []))),
                "double_checked": True,
                "first_result": first_decision,
                "second_result": second_decision
            }

        merged["tokens_used"] = total_tokens
        return merged

    def _move_video_to_category(self, video_path: str, decision: str):
        """将视频移动到对应分类目录"""
        video_path = Path(video_path)

        if decision == "approved":
            target_dir = self.approved_dir
        elif decision == "rejected":
            target_dir = self.rejected_dir
        else:
            target_dir = self.manual_review_dir

        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / video_path.name

        try:
            shutil.move(str(video_path), str(target_path))
            print(f"   📁 已移动到: {target_dir}/")
        except Exception as e:
            print(f"   ⚠️  移动失败: {e}")

    def review_batch(self, video_paths: List[str]) -> Dict[str, Any]:
        """批量审核视频"""
        results = []
        approved = rejected = manual_review = 0
        total_tokens = 0

        for i, path in enumerate(video_paths):
            print(f"\n{'='*60}")
            print(f"进度: {i+1}/{len(video_paths)}")
            print(f"{'='*60}")

            result = self.review_video(path)
            result["video_path"] = path

            if result["decision"] == "approved":
                approved += 1
                icon = "✅"
            elif result["decision"] == "rejected":
                rejected += 1
                icon = "❌"
            else:
                manual_review += 1
                icon = "❓"

            print(f"\n{icon} {result['decision']}: {result['reason']}")

            if "tokens_used" in result:
                tokens = result["tokens_used"].get("total_tokens", 0)
                total_tokens += tokens
                print(f"   Token 使用: {tokens}")

            self._move_video_to_category(path, result["decision"])
            results.append(result)

        # 保存结果
        summary = {
            "total": len(video_paths),
            "approved": approved,
            "rejected": rejected,
            "manual_review": manual_review,
            "total_tokens": total_tokens,
            "model": self.config.model,
            "results": results
        }

        with open(self.results_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        # 打印统计
        print("\n" + "="*60)
        print("批量审核完成")
        print("="*60)
        print(f"模型: {self.config.model}")
        print(f"总计: {len(video_paths)}")
        print(f"✅ 通过: {approved} ({approved/len(video_paths)*100:.1f}%)")
        print(f"❌ 拒绝: {rejected} ({rejected/len(video_paths)*100:.1f}%)")
        print(f"❓ 待复核: {manual_review} ({manual_review/len(video_paths)*100:.1f}%)")
        print(f"📊 Token 使用: {total_tokens:,}")
        print(f"📄 结果已保存: {self.results_path}")
        print("="*60)

        return summary


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="视频审核系统 - 使用硅基流动 + Qwen3-VL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python siliconflow_review.py                      使用配置文件默认目录
    python siliconflow_review.py /media/usb/videos   审核 U 盘中的视频
    python siliconflow_review.py ~/Desktop/mv        审核桌面目录中的视频

配置文件: config/config.yaml
API 密钥: 可在配置文件中设置，或通过环境变量 SILICONFLOW_API_KEY 设置
        """
    )
    parser.add_argument(
        "video_dir",
        nargs="?",
        help="视频目录路径（可选，默认使用配置文件中的路径）"
    )
    parser.add_argument(
        "-c", "--config",
        default="./config/config.yaml",
        help="配置文件路径（默认: ./config/config.yaml）"
    )

    args = parser.parse_args()

    # 加载配置
    config = Config(args.config)

    # 检查 API Key
    if not config.api_key:
        print("❌ 未设置 API 密钥!")
        print("\n设置方式（二选一）：")
        print("1. 在配置文件 config/config.yaml 中设置 siliconflow.api_key")
        print("2. 设置环境变量: export SILICONFLOW_API_KEY='your-api-key'")
        print("\n获取 API Key: https://siliconflow.cn")
        sys.exit(1)

    # 确定视频目录
    video_dir = args.video_dir or config.video_dir
    video_dir = Path(video_dir)

    if not video_dir.exists():
        print(f"❌ 视频目录不存在: {video_dir}")
        sys.exit(1)

    # 初始化审核器
    reviewer = SiliconFlowReviewer(config=config, video_dir=str(video_dir))

    # 查找视频文件
    video_paths = []

    for fmt in config.video_formats:
        video_paths.extend([str(f) for f in video_dir.glob(f"*{fmt}")])

    if not video_paths:
        print(f"❌ 目录中没有视频文件: {video_dir}")
        print(f"   支持的格式: {', '.join(config.video_formats)}")
        sys.exit(1)

    # 打印信息
    print("="*60)
    print("视频审核系统")
    print("="*60)
    print(f"📁 视频目录: {video_dir.absolute()}")
    print(f"🤖 使用模型: {config.model}")
    print(f"📊 找到 {len(video_paths)} 个视频文件")
    print("="*60)

    # 开始审核
    reviewer.review_batch(video_paths)


if __name__ == "__main__":
    main()
