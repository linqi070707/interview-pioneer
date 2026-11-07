import os
import json
import re
import time
from openai import OpenAI

print("🚀 正在启动高频压测，模拟连续 10 次简历解析请求...")

# 1. 初始化
api_key = ""
if os.path.exists("deepseek.txt"):
    with open("deepseek.txt", "r", encoding="utf-8") as f:
        api_key = f.read().strip()
else:
    print("❌ 找不到 deepseek.txt，请确保在本目录下运行。")
    exit()

client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

# 2. 核心：从 app.py 原封不动搬过来的强力解析器
def robust_json_parse(text):
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    if start_idx != -1 and end_idx != -1:
        text = text[start_idx:end_idx+1]
        
    try:
        return json.loads(text), "原生解析成功"
    except json.JSONDecodeError:
        # 暴力修复1：转义未转义的换行符
        text_fixed = re.sub(r'(?<!\\)\n', '\\\\n', text)
        try:
            return json.loads(text_fixed), "暴力修复换行符成功"
        except:
            pass
        
        # 暴力修复2：终极兜底
        try:
            res = eval(text)
            return res, "终极 eval 兜底成功"
        except Exception as e:
            raise ValueError(f"JSON 彻底损坏无法解析: {e}")

# 3. 准备测试数据（使用那段哈工大的简历文本）
final_role = "产品经理"
resume_text = """
哈尔滨工业大学 数字媒体艺术 本科。
项目经历：
1. 低打扰颈肩健康管理APP：主导设计“养长颈鹿”情感化机制，将坐姿纠偏映射为陪伴成长。完成五区信息架构及高保真原型。
2. 儿童AI学习产品：基于费曼学习法构建“备课-讲述-测验”闭环，用SystemPrompt、结构化输出判断学习状态。
3. AR生态教育游戏：用Unity MCP开发，测试指标从33%提升至75%。
"""
prompt = f"""
你是一个资深的HR专家。请分析简历，目标岗位是【{final_role}】。
评分标准：90-100完全匹配；80-89基本匹配；70-79勉强匹配；60以下不匹配。
请严格输出 JSON 格式：
{{"profile": {{"核心技能": "...", "项目经历": "...", "优势": "..."}}, "match_analysis": {{"匹配得分": 85, "优势亮点": "...", "欠缺能力": "..."}}, "interview_questions": ["题目1", "题目2", "题目3"]}}
简历内容：\n{resume_text}

【重要提示】：请确保输出的 JSON 格式合法，内部文本不要使用英文双引号（"），请使用中文双引号（“”），以保证 JSON 结构不被破坏。
"""

# 4. 开始循环压测
success_count = 0
fail_count = 0

for i in range(1, 11):
    print(f"\n--- 第 {i}/10 次请求 ---")
    try:
        response = client.chat.completions.create(
            model="deepseek-flash", 
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}, 
            temperature=0.1
        )
        raw_content = response.choices[0].message.content
        
        # 尝试解析
        try:
            parsed_json, method = robust_json_parse(raw_content)
            print(f"✅ 测试通过！解析方式：{method}")
            success_count += 1
        except Exception as parse_e:
            print(f"❌ 解析崩溃！错误信息：{parse_e}")
            print(f"---- 崩溃的原始文本前 300 字 ----\n{raw_content[:300]}")
            fail_count += 1
            
    except Exception as api_e:
        print(f"❌ API 请求失败：{api_e}")
        fail_count += 1
        
    # 稍微等一下，防止请求过快被限流
    time.sleep(2)

print("\n==================================")
print(f"📊 压测结束！总计 10 次")
print(f"✅ 成功：{success_count} 次")
print(f"❌ 失败：{fail_count} 次")
print("==================================")
