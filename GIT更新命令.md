# GitHub 更新命令

本次更新内容：优化输出目录逻辑，使审核结果跟随输入目录

## 🚀 快速更新命令

```bash
# 进入项目目录
cd /home/nano/桌面/myProject/video_jiancha

# 查看修改状态
git status

# 添加所有修改的文件
git add siliconflow_review.py README.md 使用说明.md 更新日志.md

# 提交修改
git commit -m "feat: 优化输出目录逻辑，审核结果跟随输入目录

- 修改视频分类逻辑，输出目录现在跟随输入目录
- 审核 U 盘视频时，结果直接保存在 U 盘，节省本地硬盘空间
- 更新 README.md 和使用说明.md 文档
- 添加更新日志"

# 推送到 GitHub
git push
```

---

## 📋 详细步骤说明

### 1. 查看修改内容

```bash
# 查看修改了哪些文件
git status

# 查看具体修改内容
git diff siliconflow_review.py
```

### 2. 添加文件到暂存区

```bash
# 方式一：添加所有修改（推荐）
git add .

# 方式二：逐个添加文件
git add siliconflow_review.py
git add README.md
git add 使用说明.md
git add 更新日志.md
```

### 3. 提交修改

```bash
# 使用详细的提交信息
git commit -m "feat: 优化输出目录逻辑，审核结果跟随输入目录

- 修改视频分类逻辑，输出目录现在跟随输入目录
- 审核 U 盘视频时，结果直接保存在 U 盘，节省本地硬盘空间
- 更新 README.md 和使用说明.md 文档
- 添加更新日志"
```

### 4. 推送到 GitHub

```bash
# 推送到远程仓库
git push

# 如果遇到认证问题，使用 Personal Access Token
# 用户名：xaoLiu1222
# 密码：你的 GitHub Personal Access Token
```

---

## 🔍 验证更新

推送成功后，访问你的 GitHub 仓库：
```
https://github.com/xaoLiu1222/video_jiancha
```

检查：
- ✅ 提交记录是否显示
- ✅ 文件内容是否更新
- ✅ README.md 显示是否正确

---

## 📝 本次修改的文件清单

| 文件 | 修改内容 |
|------|----------|
| `siliconflow_review.py` | 修改输出目录逻辑，使其跟随输入目录 |
| `README.md` | 更新项目结构和审核结果说明 |
| `使用说明.md` | 更新审核流程和常见问题说明 |
| `更新日志.md` | 新增，记录版本更新内容 |
| `GIT更新命令.md` | 新增，本文件 |

---

## ⚠️ 注意事项

1. **确保 API Key 已清空**
   ```bash
   # 检查配置文件
   grep "sk-" config/config.yaml
   ```

2. **不要提交敏感信息**
   - API Key
   - 个人视频文件
   - 审核结果数据

3. **提交前检查**
   ```bash
   # 查看将要提交的内容
   git diff --cached
   ```

---

## 🎯 后续维护

### 日常更新流程

```bash
# 1. 修改代码
# 2. 测试功能
# 3. 提交更新
git add .
git commit -m "描述你的修改"
git push
```

### 查看提交历史

```bash
# 查看提交记录
git log --oneline

# 查看详细提交信息
git log
```

### 回退到之前的版本（谨慎使用）

```bash
# 查看提交历史
git log --oneline

# 回退到指定版本（不删除修改）
git reset --soft <commit-id>

# 回退到指定版本（删除修改）
git reset --hard <commit-id>
```

---

**准备好了就执行上面的快速更新命令吧！** 🚀
