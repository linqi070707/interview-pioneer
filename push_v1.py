import os
import subprocess

print("🚀 正在准备推送 v1.0.0 到 GitHub...")

# 1. 检查并更新 .gitignore，确保视频不被忽略
gitignore_content = """deepseek.txt
.env
.venv/
__pycache__/
*.pyc
"""
with open(".gitignore", "w", encoding="utf-8") as f:
    f.write(gitignore_content)

print("✅ 已检查 .gitignore，确保 assets 文件夹不会被忽略。")

# 2. 自动推送
try:
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "Release v1.0.0: 完整闭环，数字人上线，防呆解析器上线"], check=True)
    subprocess.run(["git", "push", "origin", "master"], check=True)
    print("\n🎉 成功推送 v1.0.0 到 GitHub！")
    print("👉 接下来请去 Streamlit Cloud 网页端，点击 'Manage app' -> 'Reboot app' 重新部署。")
    print("👉 部署完成后，务必在云端环境重新点击一次测试，确保视频能正常加载！")
except subprocess.CalledProcessError as e:
    print(f"\n❌ 推送失败，请检查网络或 Git 报错：{e}")
