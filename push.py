import subprocess

print("🚀 正在推送最终完美版 v1.3.6 到 GitHub...")

try:
    subprocess.run(["git", "add", "."], check=True)
    try:
        subprocess.run(["git", "commit", "-m", "Release v1.3.6: 完美版，包含语音输入/输出、断点续传、DeepSeek视觉解析"], check=True)
        print("✅ 本地提交成功。")
    except subprocess.CalledProcessError:
        print("✅ 本地没有新的修改需要提交。")
        
    subprocess.run(["git", "push", "origin", "master"], check=True)
    print("\n🎉 成功推送到 GitHub！")
    
except subprocess.CalledProcessError as e:
    print(f"\n❌ Git 执行出错（请检查是否挂上了 VPN 或网络）：{e}")
