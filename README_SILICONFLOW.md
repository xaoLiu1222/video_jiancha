# 硅基流动视频审核方案 🚀

使用硅基流动的 Qwen2-VL 多模态模型进行视频审核，**完全免费**！

---

## 📋 方案优势

✅ **完全免费** - 2000万 tokens 免费额度
✅ **准确率高** - Qwen2-VL-72B 大模型，理解能力强
✅ **支持视频** - 直接分析视频帧内容
✅ **无需训练** - 开箱即用
✅ **国内访问** - 速度快，无需翻墙

---

## 🎯 使用步骤

### 第一步：获取 API Key

1. 访问 https://siliconflow.cn
2. 注册并登录账号
3. 进入控制台 → API 密钥
4. 创建新的 API Key（sk-开头）

### 第二步：设置环境变量

```bash
# Linux/Mac
export SILICONFLOW_API_KEY='sk-xxxxxxxxxxxxxxxx'

# 或者写入 ~/.bashrc 永久保存
echo 'export SILICONFLOW_API_KEY="sk-xxxxxxxxxxxxxxxx"' >> ~/.bashrc
source ~/.bashrc
```

### 第三步：安装依赖

```bash
cd ~/桌面/myProject/video_jiancha
source venv/bin/activate
pip install requests
```

### 第四步：运行审核

```bash
# 审核单个视频
python siliconflow_review.py

# 或者在代码中使用
python
>>> from siliconflow_review import SiliconFlowReviewer
>>> reviewer = SiliconFlowReviewer(api_key="sk-xxx")
>>> result = reviewer.review_video("/path/to/video.mp4")
>>> print(result)
```

---

## 💻 代码示例

```python
from siliconflow_review import SiliconFlowReviewer

# 初始化
reviewer = SiliconFlowReviewer(api_key="sk-xxxxxxxx")

# 审核单个视频
result = reviewer.review_video("/path/to/video.mp4")

print(f"决策: {result['decision']}")
print(f"原因: {result['reason']}")
print(f"置信度: {result['confidence']}")

# 批量审核
video_paths = [
    "/path/to/video1.mp4",
    "/path/to/video2.mp4",
    "/path/to/video3.mp4",
]
summary = reviewer.review_batch(video_paths)
```

---

## 📊 审核结果说明

```json
{
  "decision": "approved",  // approved / rejected / manual_review
  "reason": "内容健康，有人物表演，无违规内容",
  "confidence": 0.95,
  "flags": [],  // 触发的问题标签
  "tokens_used": {
    "prompt_tokens": 1234,
    "completion_tokens": 56,
    "total_tokens": 1290
  }
}
```

---

## 💰 成本估算

### 免费额度
- **2000万 tokens** 免费
- 每个视频约消耗 **1000-2000 tokens**
- 可以审核 **10,000-20,000 个视频**

### 超出免费额度后
- 按量付费，价格远低于阿里云/腾讯云
- Qwen2-VL-72B: 约 0.0006元/1K tokens
- 每个视频成本: **0.001-0.002 元**

---

## 🆚 方案对比

| 方案 | 成本 | 准确率 | 速度 | 推荐度 |
|------|------|--------|------|--------|
| **硅基流动** | 免费 💰 | 很高 ⭐⭐⭐⭐⭐ | 快 ⚡⚡⚡ | ⭐⭐⭐⭐⭐ |
| 阿里云 | 0.1元/分钟 | 高 | 快 | ⭐⭐⭐⭐ |
| 本地系统 | 免费 | 中等 | 快 | ⭐⭐⭐ |

---

## 🔧 高级配置

### 调整提取帧数

```python
# 提取更多帧，审核更准确（但消耗更多 tokens）
result = reviewer.review_video("/path/to/video.mp4", num_frames=16)
```

### 自定义审核规则

修改 `siliconflow_review.py` 中的 `review_prompt` 变量：

```python
self.review_prompt = """
你是一个专业的视频审核员。

❌ 不通过的情况：
1. 你的自定义规则1
2. 你的自定义规则2
...

请返回 JSON 格式...
"""
```

---

## 📝 注意事项

1. **API Key 安全**
   - 不要将 API Key 提交到 Git
   - 使用环境变量存储

2. **免费额度**
   - 2000万 tokens 用完后需要充值
   - 可以在控制台查看使用情况

3. **速度优化**
   - 减少提取帧数可以加快速度
   - 批量审核时建议 8 帧/视频

---

## 🎉 开始使用

```bash
# 1. 设置 API Key
export SILICONFLOW_API_KEY='sk-xxxxxxxx'

# 2. 准备视频
mkdir -p data/to_review
cp /path/to/videos/*.mp4 data/to_review/

# 3. 运行审核
python siliconflow_review.py

# 4. 查看结果
cat data/results/siliconflow_review.json
```

---

## 🆘 常见问题

**Q: API Key 在哪里获取？**
A: https://siliconflow.cn → 控制台 → API 密钥

**Q: 免费额度够用吗？**
A: 2000万 tokens 可以审核 1-2 万个视频，足够测试和小规模使用

**Q: 准确率如何？**
A: Qwen2-VL-72B 是目前最强的开源多模态模型之一，准确率很高

**Q: 支持哪些视频格式？**
A: 支持常见格式：mp4, avi, mov, mkv 等

---

主人，现在就可以开始使用了喵～ ฅ(^ω^ฅ)
