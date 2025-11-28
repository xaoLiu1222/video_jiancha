# GitHub 上传指南

本文档提供将项目上传到 GitHub 的完整流程。

## 📋 准备工作

### 1. 安装 Git

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install git
```

**macOS:**
```bash
brew install git
```

**Windows:**
下载并安装 [Git for Windows](https://git-scm.com/download/win)

### 2. 配置 Git

```bash
# 设置用户名
git config --global user.name "你的用户名"

# 设置邮箱
git config --global user.email "你的邮箱@example.com"

# 验证配置
git config --list
```

### 3. 创建 GitHub 账号

访问 [GitHub](https://github.com) 注册账号（如果还没有）

---

## 🚀 上传流程

### 方式一：通过 GitHub 网页创建仓库（推荐新手）

#### 步骤 1: 在 GitHub 创建新仓库

1. 登录 GitHub
2. 点击右上角 `+` → `New repository`
3. 填写仓库信息：
   - **Repository name**: `video_jiancha`
   - **Description**: `基于 Qwen3-VL 的智能视频内容审核系统`
   - **Public/Private**: 选择 `Public`（公开）或 `Private`（私有）
   - **不要勾选** "Initialize this repository with a README"
4. 点击 `Create repository`

#### 步骤 2: 初始化本地仓库

```bash
# 进入项目目录
cd /home/nano/桌面/myProject/video_jiancha

# 初始化 Git 仓库
git init

# 添加所有文件
git add .

# 创建首次提交
git commit -m "Initial commit: 视频审核系统首次提交"
```

#### 步骤 3: 关联远程仓库并推送

```bash
# 关联远程仓库（替换为你的 GitHub 用户名）
git remote add origin https://github.com/你的用户名/video_jiancha.git

# 推送到 GitHub（首次推送）
git branch -M main
git push -u origin main
```

**如果遇到认证问题**，使用 Personal Access Token：

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token → 勾选 `repo` 权限
3. 复制生成的 token
4. 推送时使用 token 作为密码

---

### 方式二：使用 SSH 密钥（推荐熟练用户）

#### 步骤 1: 生成 SSH 密钥

```bash
# 生成 SSH 密钥
ssh-keygen -t ed25519 -C "你的邮箱@example.com"

# 启动 ssh-agent
eval "$(ssh-agent -s)"

# 添加密钥
ssh-add ~/.ssh/id_ed25519

# 查看公钥
cat ~/.ssh/id_ed25519.pub
```

#### 步骤 2: 添加 SSH 密钥到 GitHub

1. 复制公钥内容
2. GitHub → Settings → SSH and GPG keys → New SSH key
3. 粘贴公钥，点击 Add SSH key

#### 步骤 3: 推送代码

```bash
# 初始化仓库
git init
git add .
git commit -m "Initial commit: 视频审核系统首次提交"

# 关联远程仓库（使用 SSH 地址）
git remote add origin git@github.com:你的用户名/video_jiancha.git

# 推送
git branch -M main
git push -u origin main
```

---

## 📝 后续更新流程

### 日常提交流程

```bash
# 1. 查看修改状态
git status

# 2. 添加修改的文件
git add .

# 3. 提交修改
git commit -m "描述你的修改内容"

# 4. 推送到 GitHub
git push
```

### 常用 Git 命令

```bash
# 查看提交历史
git log --oneline

# 查看文件差异
git diff

# 撤销未提交的修改
git checkout -- 文件名

# 创建新分支
git checkout -b 新分支名

# 切换分支
git checkout 分支名

# 合并分支
git merge 分支名

# 拉取远程更新
git pull
```

---

## ⚠️ 注意事项

### 1. 保护敏感信息

**在上传前务必检查：**

```bash
# 确保 .gitignore 正确配置
cat .gitignore

# 检查是否有敏感文件被追踪
git status
```

**重要：不要提交以下内容**
- ❌ API Key（`config/config.yaml` 中的 `api_key`）
- ❌ 个人视频文件
- ❌ 审核结果数据
- ❌ 虚拟环境目录（`venv/`）

**已提供配置文件模板：**
- ✅ `config/config.example.yaml` - 配置文件示例（不含密钥）
- ✅ `config/config.yaml` - 实际配置（已在 .gitignore 中，不会上传）

### 2. 首次推送前的检查清单

- [ ] 已删除临时文件和 `__pycache__`
- [ ] `.gitignore` 配置正确
- [ ] `config/config.yaml` 中的 API Key 已清空或使用示例值
- [ ] `README.md` 中的 GitHub 链接已更新为你的仓库地址
- [ ] 所有文档已更新完善

### 3. 如果不小心提交了敏感信息

```bash
# 从历史记录中删除文件
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch config/config.yaml" \
  --prune-empty --tag-name-filter cat -- --all

# 强制推送（危险操作，谨慎使用）
git push origin --force --all

# 更安全的方法：使用 BFG Repo-Cleaner
# https://rtyley.github.io/bfg-repo-cleaner/
```

**更好的做法：**
1. 立即在 GitHub 上删除仓库
2. 重新创建仓库
3. 清理本地敏感信息后重新推送

---

## 🎯 推荐的提交信息格式

使用清晰的提交信息有助于项目维护：

```bash
# 功能添加
git commit -m "feat: 添加视频时长检测功能"

# Bug 修复
git commit -m "fix: 修复 API 超时问题"

# 文档更新
git commit -m "docs: 更新使用说明文档"

# 代码重构
git commit -m "refactor: 优化视频帧提取逻辑"

# 性能优化
git commit -m "perf: 减少 token 消耗"

# 测试相关
git commit -m "test: 添加单元测试"
```

---

## 📚 参考资源

- [Git 官方文档](https://git-scm.com/doc)
- [GitHub 官方指南](https://docs.github.com)
- [Git 简明指南](https://rogerdudler.github.io/git-guide/index.zh.html)
- [GitHub 中文社区](https://github.com/github)

---

## 🆘 常见问题

### Q: 推送时提示 "Permission denied"

**A:** 检查 SSH 密钥配置或使用 HTTPS + Personal Access Token

### Q: 推送时提示 "rejected"

**A:** 先拉取远程更新：
```bash
git pull origin main --rebase
git push
```

### Q: 如何删除远程仓库中的文件

**A:**
```bash
git rm 文件名
git commit -m "删除文件"
git push
```

### Q: 如何撤销最后一次提交

**A:**
```bash
# 保留修改
git reset --soft HEAD~1

# 不保留修改
git reset --hard HEAD~1
```

---

**祝上传顺利！** 🎉

如有问题，欢迎在 GitHub Issues 中提问。
