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
    """视频特征提取器"""

    def extract_frames(self, video_path: str, num_frames: int = 6) -> List:
        """从视频中均匀提取帧"""
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
        self.extractor = VideoFeatureExtractor()

        # 审核规则提示词
        self.review_prompt = """审核音乐MV，返回JSON格式结果。

拒绝条件：
1.林夕作品 2.竖屏 3.上下黑边 4.左右黑边超一半 5.马赛克遮挡 6.画面模糊 7.暴露/导向问题 8.纯风景无人物 9.风景超一半时长 10.广告 11.吸毒画面

返回格式：{"decision":"approved或rejected","reason":"原因","confidence":0.95,"flags":[]}"""

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
        print(f"\n[1/4] 检查视频时长...")
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

        # 提取视频帧
        print(f"\n[2/4] 提取视频关键帧 ({self.config.num_frames} 帧)...")

        try:
            frames = self.extractor.extract_frames(video_path, num_frames=self.config.num_frames)
            print(f"  ✓ 成功提取 {len(frames)} 帧")
        except Exception as e:
            return {
                "decision": "rejected",
                "reason": f"无法读取视频: {e}",
                "confidence": 1.0,
                "error": str(e)
            }

        # 保存帧为临时文件
        print(f"\n[3/4] 准备图片数据...")
        temp_dir = Path("./temp_frames")
        temp_dir.mkdir(exist_ok=True)

        frame_paths = []

        for i, frame in enumerate(frames):
            frame_path = temp_dir / f"frame_{i}.jpg"
            cv2.imwrite(str(frame_path), cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            frame_paths.append(frame_path)

        # 调用 API
        print(f"\n[4/4] 调用 {self.config.model} 模型...")

        try:
            result = self._call_api(frame_paths)
            print(f"  ✓ API 调用成功")

            # 清理临时文件
            for fp in frame_paths:
                fp.unlink()

            return result

        except Exception as e:
            print(f"  ✗ API 调用失败: {e}")

            return {
                "decision": "manual_review",
                "reason": f"API 调用失败: {e}",
                "confidence": 0.0,
                "error": str(e)
            }

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

    def _move_video_to_category(self, video_path: str, decision: str):
        """将视频移动到对应分类目录"""
        video_path = Path(video_path)

        if decision == "approved":
            target_dir = Path(self.config.approved_dir)
        elif decision == "rejected":
            target_dir = Path(self.config.rejected_dir)
        else:
            target_dir = Path(self.config.manual_review_dir)

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

        results_path = Path(self.config.results_path)
        results_path.parent.mkdir(parents=True, exist_ok=True)

        with open(results_path, "w", encoding="utf-8") as f:
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
        print(f"📄 结果已保存: {results_path}")
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
