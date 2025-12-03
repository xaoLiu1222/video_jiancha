#!/usr/bin/env python3
"""
视频审核系统 - 使用 Google Gemini 2.0 Flash

基于 Gemini 多模态大模型的智能视频审核工具，支持原生视频理解。

使用方法：
    python gemini_review.py [视频目录路径]

示例：
    python gemini_review.py                    # 使用配置文件中的默认目录
    python gemini_review.py /media/usb/videos  # 指定 U 盘目录
"""

import os
import sys
import json
import shutil
import argparse
import warnings
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

import yaml

# 抑制警告
warnings.filterwarnings("ignore", category=UserWarning)

# Google Gemini SDK
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ 请安装 google-genai: pip install google-genai")


class Config:
    """配置管理类"""

    def __init__(self, config_path: str = "./config/config.yaml"):
        self.config_path = Path(config_path)

        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)
        else:
            self._config = {}
            print(f"⚠️ 配置文件不存在: {config_path}，使用默认配置")

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
        return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or self.get("gemini.api_key")

    @property
    def model(self) -> str:
        """获取模型名称"""
        return self.get("gemini.model", "gemini-2.0-flash")

    @property
    def video_dir(self) -> str:
        return self.get("paths.video_dir", "./data/to_review")

    @property
    def num_frames(self) -> int:
        return self.get("video.num_frames", 12)

    @property
    def video_formats(self) -> List[str]:
        return self.get("video.formats", [".mp4", ".avi", ".mov", ".ts", ".mkv", ".flv"])

    @property
    def min_duration(self) -> int:
        return self.get("video.min_duration", 120)

    @property
    def max_tokens(self) -> int:
        return self.get("model_params.max_tokens", 1024)

    @property
    def temperature(self) -> float:
        return self.get("model_params.temperature", 0.2)


class GeminiReviewer:
    """Google Gemini 视频审核器"""

    def __init__(self, config: Config, video_dir: Optional[str] = None):
        self.config = config
        self.video_dir = Path(video_dir) if video_dir else Path(config.video_dir)

        # 初始化 Gemini 客户端
        if not GEMINI_AVAILABLE:
            raise RuntimeError("google-genai 未安装")

        if not config.api_key:
            raise ValueError("未设置 Gemini API Key")

        self.client = genai.Client(api_key=config.api_key)

        # 设置输出目录（跟随输入目录）
        self.approved_dir = self.video_dir / "approved"
        self.rejected_dir = self.video_dir / "rejected"
        self.manual_review_dir = self.video_dir / "manual_review"
        self.results_path = self.video_dir / "review_results.json"

        # 审核规则提示词
        self.review_prompt = """你是专业的音乐MV内容审核员。请仔细分析这个视频，判断是否符合发布标准。

## 审核规则（必须严格执行）

### 一、格式问题（自动拒绝）
1. **竖屏视频**：画面宽度小于高度（9:16等竖屏比例）
2. **上下黑边**：画面上方和下方存在明显黑色边框
3. **左右黑边过大**：左右两侧黑边占据画面宽度超过50%

### 二、画质问题（自动拒绝）
4. **画面模糊**：整体画面不清晰，无法辨认人物面部或文字
5. **马赛克遮挡**：画面中存在明显的马赛克/模糊处理区域

### 三、内容问题（自动拒绝）
6. **林夕作品**：画面中出现"林夕"字样（作词人署名）
7. **暴露内容**：过度暴露的穿着、性暗示动作或画面
8. **导向问题**：涉及政治敏感、宗教极端、暴力血腥内容
9. **纯风景无人物**：整个视频只有风景画面，完全没有人物出现
10. **风景占比过高**：风景画面占据视频时长超过50%
11. **广告内容**：包含商业广告、品牌植入、二维码、购买链接等
12. **吸毒画面**：出现吸食毒品、注射器、毒品相关道具等

## 审核要求

1. **全面分析**：仔细观看整个视频，不要遗漏任何问题
2. **综合判断**：结合视频全部内容做出整体判断
3. **宁严勿松**：如有疑虑，倾向于拒绝或标记为需人工复核
4. **详细说明**：在reason中清楚说明发现的问题

## 返回格式（严格JSON，不要包含其他内容）

```json
{
    "decision": "approved/rejected/manual_review",
    "reason": "详细说明判断依据",
    "confidence": 0.95,
    "flags": ["问题标签"],
    "video_analysis": "简要描述视频内容"
}
```

### decision 说明：
- **approved**：完全符合标准，可以发布
- **rejected**：存在明确违规内容，不可发布
- **manual_review**：存在疑虑但不确定，需人工复核

### flags 可选值：
vertical, black_border_top_bottom, black_border_left_right, blurry, mosaic, linxi_work, explicit_content, political_sensitive, no_person, too_much_scenery, advertisement, drug_related

请开始审核这个视频："""

    def _get_video_duration(self, video_path: str) -> float:
        """获取视频时长（秒）"""
        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            cap.release()
            return duration
        except Exception:
            return 0

    def review_video(self, video_path: str) -> Dict[str, Any]:
        """审核单个视频"""
        print(f"\n{'='*60}")
        print(f"审核视频: {Path(video_path).name}")
        print(f"{'='*60}")

        # 检查视频时长
        print(f"\n[1/3] 检查视频时长...")
        duration = self._get_video_duration(video_path)
        print(f"  视频时长: {duration:.1f} 秒 ({duration/60:.1f} 分钟)")

        if duration > 0 and duration < self.config.min_duration:
            return {
                "decision": "rejected",
                "reason": f"视频时长不足 {self.config.min_duration // 60} 分钟 (仅 {duration:.1f} 秒)",
                "confidence": 1.0,
                "flags": ["too_short"]
            }

        # 上传视频到 Gemini
        print(f"\n[2/3] 上传视频到 Gemini...")
        try:
            original_path = Path(video_path)

            # 获取 MIME 类型
            mime_types = {
                ".mp4": "video/mp4",
                ".avi": "video/x-msvideo",
                ".mov": "video/quicktime",
                ".ts": "video/mp2t",
                ".mkv": "video/x-matroska",
                ".flv": "video/x-flv",
                ".webm": "video/webm",
                ".wmv": "video/x-ms-wmv",
            }
            mime_type = mime_types.get(original_path.suffix.lower(), "video/mp4")

            # 读取文件内容并上传（避免中文路径问题）
            with open(video_path, "rb") as f:
                video_data = f.read()

            video_file = self.client.files.upload(
                file=video_data,
                config={"mime_type": mime_type}
            )
            print(f"  ✓ 上传成功: {video_file.name}")

            # 等待视频处理完成
            while video_file.state.name == "PROCESSING":
                print("  ⏳ 视频处理中...")
                time.sleep(2)
                video_file = self.client.files.get(name=video_file.name)

            if video_file.state.name == "FAILED":
                raise Exception("视频处理失败")

            print(f"  ✓ 视频处理完成")

        except Exception as e:
            print(f"  ✗ 上传失败: {e}")
            return {
                "decision": "manual_review",
                "reason": f"视频上传失败: {e}",
                "confidence": 0.0,
                "error": str(e)
            }

        # 调用 Gemini API 审核
        print(f"\n[3/3] 调用 {self.config.model} 模型审核...")
        try:
            response = self.client.models.generate_content(
                model=self.config.model,
                contents=[video_file, self.review_prompt],
                config=types.GenerateContentConfig(
                    max_output_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                )
            )

            content_text = response.text
            print(f"  ✓ API 调用成功")

            # 删除上传的视频文件
            try:
                self.client.files.delete(name=video_file.name)
            except Exception:
                pass

            # 解析 JSON 结果
            if "```json" in content_text:
                content_text = content_text.split("```json")[1].split("```")[0].strip()
            elif "```" in content_text:
                content_text = content_text.split("```")[1].split("```")[0].strip()

            try:
                result = json.loads(content_text)
            except json.JSONDecodeError:
                result = {
                    "decision": "manual_review",
                    "reason": content_text,
                    "confidence": 0.5
                }

            # 添加 token 使用信息
            if hasattr(response, 'usage_metadata'):
                result["tokens_used"] = {
                    "prompt_tokens": getattr(response.usage_metadata, 'prompt_token_count', 0),
                    "completion_tokens": getattr(response.usage_metadata, 'candidates_token_count', 0),
                    "total_tokens": getattr(response.usage_metadata, 'total_token_count', 0)
                }

            return result

        except Exception as e:
            print(f"  ✗ API 调用失败: {e}")
            return {
                "decision": "manual_review",
                "reason": f"API 调用失败: {e}",
                "confidence": 0.0,
                "error": str(e)
            }

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
            print(f"   📁 已移动到: {target_dir.name}/")
        except Exception as e:
            print(f"   ⚠️ 移动失败: {e}")

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

            print(f"\n{icon} {result['decision']}: {result.get('reason', 'N/A')}")

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
        description="视频审核系统 - 使用 Google Gemini",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python gemini_review.py                      使用配置文件默认目录
    python gemini_review.py /media/usb/videos   审核 U 盘中的视频
    python gemini_review.py F:\\videos          Windows 指定目录

配置文件: config/config.yaml
API 密钥: 环境变量 GEMINI_API_KEY 或 GOOGLE_API_KEY
        """
    )
    parser.add_argument(
        "video_dir",
        nargs="?",
        help="视频目录路径（可选）"
    )
    parser.add_argument(
        "-c", "--config",
        default="./config/config.yaml",
        help="配置文件路径"
    )

    args = parser.parse_args()

    # 加载配置
    config = Config(args.config)

    # 检查 API Key
    if not config.api_key:
        print("❌ 未设置 API 密钥!")
        print("\n设置方式（二选一）：")
        print("1. 设置环境变量: export GEMINI_API_KEY='your-api-key'")
        print("2. 在配置文件 config/config.yaml 中设置 gemini.api_key")
        print("\n获取 API Key: https://aistudio.google.com/apikey")
        sys.exit(1)

    # 确定视频目录
    video_dir = args.video_dir or config.video_dir
    video_dir = Path(video_dir)

    if not video_dir.exists():
        print(f"❌ 视频目录不存在: {video_dir}")
        sys.exit(1)

    # 初始化审核器
    reviewer = GeminiReviewer(config=config, video_dir=str(video_dir))

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
    print("视频审核系统 - Google Gemini")
    print("="*60)
    print(f"📁 视频目录: {video_dir.absolute()}")
    print(f"🤖 使用模型: {config.model}")
    print(f"📊 找到 {len(video_paths)} 个视频文件")
    print("="*60)

    # 开始审核
    reviewer.review_batch(video_paths)


if __name__ == "__main__":
    main()
