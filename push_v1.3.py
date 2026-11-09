import subprocess

print("🚀 正在推送 v1.3.1 到 GitHub...")

try:
    subprocess.run(["git", "add", "."], check=True)
    try:
        subprocess.run(["git", "commit", "-m", "Release v1.3.1: 增加语音交互，历史存档，极速云端加载"], check=True)
        print("✅ 本地提交成功。")
    except subprocess.CalledProcessError:
        print("✅ 本地没有新的修改需要提交。")
        
    subprocess.run(["git", "push", "origin", "master"], check=True)
    print("\n🎉 成功推送到 GitHub！")
    print("👉 接下来请去 Streamlit Cloud 网页端点击 'Reboot app'。")
    
except subprocess.CalledProcessError as e:
    print(f"\n❌ Git 执行出错（请检查是否挂上了 VPN）：{e}")
