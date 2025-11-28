#!/bin/bash

echo "=========================================="
echo "  视频审核系统 - GitHub 上传脚本"
echo "=========================================="
echo ""

# 检查是否已初始化 Git
if [ ! -d ".git" ]; then
    echo "📦 初始化 Git 仓库..."
    git init
    echo "✅ Git 仓库初始化完成"
    echo ""
fi

# 检查配置文件
if grep -q "sk-" config/config.yaml 2>/dev/null; then
    echo "⚠️  警告: config/config.yaml 中可能包含 API Key！"
    echo "   建议先清空 API Key 再上传"
    read -p "   是否继续？(y/n): " confirm
    if [ "$confirm" != "y" ]; then
        echo "❌ 已取消上传"
        exit 1
    fi
fi

# 添加所有文件
echo "📝 添加文件到 Git..."
git add .

# 查看状态
echo ""
echo "📊 将要提交的文件:"
git status --short

# 确认提交
echo ""
read -p "📝 请输入提交信息 (默认: Initial commit): " commit_msg
commit_msg=${commit_msg:-"Initial commit: 视频审核系统首次提交"}

git commit -m "$commit_msg"
echo "✅ 提交完成"
echo ""

# 询问远程仓库地址
read -p "🔗 请输入 GitHub 仓库地址 (https://github.com/用户名/video_jiancha.git): " repo_url

if [ -z "$repo_url" ]; then
    echo "❌ 未输入仓库地址，已取消上传"
    exit 1
fi

# 检查是否已添加远程仓库
if git remote | grep -q "origin"; then
    echo "🔄 更新远程仓库地址..."
    git remote set-url origin "$repo_url"
else
    echo "🔗 添加远程仓库..."
    git remote add origin "$repo_url"
fi

# 推送到 GitHub
echo ""
echo "🚀 推送到 GitHub..."
git branch -M main
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "  ✅ 上传成功！"
    echo "=========================================="
    echo ""
    echo "🎉 项目已成功上传到 GitHub！"
    echo "📍 仓库地址: $repo_url"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "  ❌ 上传失败"
    echo "=========================================="
    echo ""
    echo "可能的原因："
    echo "1. 网络连接问题"
    echo "2. 认证失败（需要 Personal Access Token）"
    echo "3. 仓库地址错误"
    echo ""
    echo "请参考 GITHUB上传指南.md 解决问题"
fi
