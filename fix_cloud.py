import os
import subprocess

print("🚀 开始修复云端部署环境...")

# 1. 自动生成 packages.txt
with open("packages.txt", "w", encoding="utf-8") as f:
    f.write("libgl1\n")
print("✅ 已生成 packages.txt，包含系统级依赖 libgl1")

# 2. 自动更新 requirements.txt
req_content = """streamlit
openai
pandas
pymupdf
rapidocr_onnxruntime
plotly
opencv-python-headless
"""
with open("requirements.txt", "w", encoding="utf-8") as f:
    f.write(req_content)
print("✅ 已更新 requirements.txt，替换为 opencv-python-headless")

# 3. 自动执行 Git 提交和推送
print("\n正在自动推送到 GitHub...")
try:
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "Fix libGL and opencv-headless for cloud deployment"], check=True)
    subprocess.run(["git", "push", "origin", "master"], check=True)
    print("\n🎉 全部完成！代码已成功推送到 GitHub。")
    print("👉 现在请回到 Streamlit 网页，点击右下角终端的 'Reboot app' 重启应用。")
except subprocess.CalledProcessError as e:
    print(f"\n❌ Git 执行出错：{e}")
    print("请检查是否有网络问题或 Git 冲突。")
