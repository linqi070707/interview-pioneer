import os
import shutil
import subprocess

print("1. 正在清理本地废弃测试文件...")
files_to_remove = ["cloudflared.exe", ".env", "init.py", "check_model.py", "test_api.py", "read_excel.py"]
for f in files_to_remove:
    if os.path.exists(f):
        os.remove(f)
        print(f"  - 已删除: {f}")

print("\n2. 正在更新 .gitignore...")
gitignore_content = """deepseek.txt
.env
init.py
.venv/
__pycache__/
*.pyc
*.exe
"""
with open(".gitignore", "w", encoding="utf-8") as f:
    f.write(gitignore_content)

print("\n3. 正在销毁旧的 Git 历史并重新初始化...")
if os.path.exists(".git"):
    shutil.rmtree(".git", ignore_errors=True)

try:
    subprocess.run(["git", "init"], check=True)
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "Clean commit without secrets"], check=True)
    print("\n✅ 本地清理完毕，代码已重新打包！")
    print("👉 请继续在终端执行以下两条命令重新推送到 GitHub：")
    print("   git remote add origin https://github.com/linqi070707/interview-pioneer.git")
    print("   git push -u origin master")
except Exception as e:
    print(f"\n❌ 执行出错：{e}")
