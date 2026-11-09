import subprocess

print("🚀 正在推送最终完美版 v1.3.7 到 GitHub...")

try:
    # 1. 添加所有更改
    subprocess.run(["git", "add", "."], check=True)
    
    # 2. 提交更改
    try:
        subprocess.run(["git", "commit", "-m", "Release v1.3.7: 优化视觉解析提示时间，恢复极简录音组件"], check=True)
        print("✅ 本地提交成功。")
    except subprocess.CalledProcessError:
        print("✅ 本地没有新的修改需要提交。")
        
    # 3. 推送到 GitHub
    subprocess.run(["git", "push", "origin", "master"], check=True)
    print("\n🎉 成功推送到 GitHub！")
    print("👉 接下来请去 Streamlit Cloud 网页端点击 'Reboot app'。")
    
except subprocess.CalledProcessError as e:
    print(f"\n❌ Git 执行出错（请检查是否挂上了 VPN 或网络连接）：{e}")
