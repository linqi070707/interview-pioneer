import subprocess

print("🚀 正在将最新代码推送到 GitHub...")

try:
    # 1. 将所有修改添加到暂存区
    subprocess.run(["git", "add", "."], check=True)
    
    # 2. 提交更改
    commit_msg = "Update: Add search bar, custom roles, and fix UI issues"
    result = subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, text=True)
    
    if "nothing to commit" in result.stdout:
        print("✅ 本地代码没有新的修改，已经是最新版。")
    else:
        print("✅ 已生成本地提交。")
        
    # 3. 推送到 GitHub
    subprocess.run(["git", "push", "origin", "master"], check=True)
    print("\n🎉 推送成功！所有最新代码已上传到 GitHub。")
    print("👉 接下来请回到 Streamlit 网页，点击 'Manage app' -> 'Reboot app'，云端会自动拉取最新代码重新部署。")

except subprocess.CalledProcessError as e:
    print(f"\n❌ Git 执行出错：{e}")
    print("如果有红色的报错信息，请截图发给我。")
