import subprocess

print("🚀 正在推送到 GitHub (v1.0.2)...")

try:
    # 1. 添加所有文件（包含新增的 demo_resume.pdf）
    subprocess.run(["git", "add", "."], check=True)
    
    # 2. 提交更改（如果没东西提交，这里会报错，我们用 try-except 绕过）
    try:
        subprocess.run(["git", "commit", "-m", "Release v1.0.2: 增加示例简历下载，修复表单嵌套下载报错"], check=True)
        print("✅ 本地提交成功。")
    except subprocess.CalledProcessError:
        print("✅ 本地没有新的修改需要提交。")
        
    # 3. 推送到 GitHub
    subprocess.run(["git", "push", "origin", "master"], check=True)
    print("\n🎉 成功推送到 GitHub！")
    print("👉 接下来请去 Streamlit Cloud 网页端点击 'Reboot app'。")
    
except subprocess.CalledProcessError as e:
    print(f"\n❌ Git 执行出错：{e}")
