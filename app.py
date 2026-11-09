import streamlit as st
import streamlit.components.v1 as components
import os
import pandas as pd
import json
import fitz  # PyMuPDF
from rapidocr_onnxruntime import RapidOCR
from openai import OpenAI
import plotly.graph_objects as go
from datetime import datetime
import re
import base64
import asyncio
import edge_tts

APP_VERSION = "v1.3.2"

# 1. 初始化
api_key = ""
siliconflow_key = ""

if os.path.exists("deepseek.txt"):
    with open("deepseek.txt", "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
        if len(lines) >= 1: api_key = lines[0]
        if len(lines) >= 2: siliconflow_key = lines[1]
elif "DEEPSEEK_API_KEY" in st.secrets:
    api_key = st.secrets["DEEPSEEK_API_KEY"]
    siliconflow_key = st.secrets.get("SILICONFLOW_API_KEY", "")

if not api_key:
    st.error("未找到 DeepSeek API Key")
    st.stop()

client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
asr_client = OpenAI(api_key=siliconflow_key, base_url="https://api.siliconflow.cn/v1") if siliconflow_key else None

st.set_page_config(page_title="面试先锋", page_icon="🎙️", layout="wide")

# ==========================================
# 注入 UI 样式 (保持不变)
# ==========================================
st.markdown("""
<style>
    :root {
        --bg-body: #f4f6fa; --bg-card: #ffffff; --text-primary: #1e2b3c;
        --accent: #2d7ff9; --accent-hover: #1a5fcc; --border-input: #dde5f0;
    }
    .stApp { background-color: var(--bg-body) !important; color: var(--text-primary) !important; font-family: system-ui, sans-serif; }
    h1, h2, h3, h4 { color: var(--text-primary) !important; font-weight: 700 !important; }
    
    header[data-testid="stHeader"] { background: transparent !important; height: 0 !important; }
    .block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; }
    
    div[data-baseweb="input"], div[data-baseweb="textarea"] { border-radius: 12px !important; background-color: #fafcff !important; }
    [data-testid="stFileUploader"] section { border: 1.5px dashed var(--border-input) !important; background-color: #ffffff !important; border-radius: 12px !important; }
    [data-testid="stChatInput"] { border: 1.5px solid var(--border-input) !important; border-radius: 12px !important; background-color: #ffffff !important; }

    .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
        background: #ffffff !important; color: var(--text-primary) !important;
        border: 1.5px solid var(--border-input) !important; border-radius: 12px !important; font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover, .stDownloadButton > button:hover {
        border-color: var(--accent) !important; color: var(--accent) !important; background-color: #f0f7ff !important;
    }
    .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
        background: var(--accent) !important; color: #ffffff !important; border: none !important;
    }
    .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {
        background: var(--accent-hover) !important; box-shadow: 0 4px 12px rgba(45,127,249,0.3) !important;
    }
    .stButton > button:active, .stFormSubmitButton > button:active { transform: translateY(1px) !important; }

    .stChatMessage { background-color: var(--bg-card) !important; border: 1px solid var(--border-input) !important; border-radius: 12px !important; padding: 16px !important; margin-bottom: 12px !important; }
    .stChatMessage p { font-size: 16px !important; line-height: 1.6 !important; }
    .version-tag { position: fixed; bottom: 10px; right: 15px; color: #888; font-size: 12px; }

    .report-card { background: #ffffff; border: 1px solid var(--border-input); border-radius: 12px; padding: 24px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }
    .report-card-title { font-size: 18px; font-weight: 700; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
    
    video::-webkit-media-controls { display: none !important; }
    [data-testid="stAudioInput"] { margin-top: -15px; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

st.title("🎙️ 面试先锋")

def robust_json_parse(text):
    text = text.strip()
    if text.startswith("```json"): text = text[7:]
    if text.endswith("```"): text = text[:-3]
    text = text.strip()
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    if start_idx != -1 and end_idx != -1: text = text[start_idx:end_idx+1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        text_fixed = re.sub(r'(?<!\\)\n', '\\\\n', text)
        try: return json.loads(text_fixed)
        except: pass
        try: return eval(text)
        except Exception as e: raise ValueError(f"JSON 解析失败: {e}")

async def generate_audio(text, filename):
    voice = "zh-CN-XiaoxiaoNeural" 
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(filename)

def transcribe_audio(audio_bytes):
    if not asr_client: return ""
    try:
        with open("temp_user_audio.wav", "wb") as f:
            f.write(audio_bytes)
        with open("temp_user_audio.wav", "rb") as f:
            response = asr_client.audio.transcriptions.create(
                model="FunAudioLLM/SenseVoiceSmall",
                file=f
            )
        # 用完即删，释放空间
        if os.path.exists("temp_user_audio.wav"):
            os.remove("temp_user_audio.wav")
        return response.text
    except Exception:
        return ""

@st.cache_resource
def load_ocr(): return RapidOCR()
ocr_engine = load_ocr()

@st.cache_data
def load_data(): return pd.read_excel('data.xlsx', sheet_name='题库')
df = load_data()

# 2. 状态管理
if 'stage' not in st.session_state: st.session_state.stage = 'input'
if 'messages' not in st.session_state: st.session_state.messages = []
if 'analysis_result' not in st.session_state: st.session_state.analysis_result = None
if 'resume_text' not in st.session_state: st.session_state.resume_text = ""
if 'target_role' not in st.session_state: st.session_state.target_role = ""
if 'question_list' not in st.session_state: st.session_state.question_list = []
if 'strictness' not in st.session_state: st.session_state.strictness = 3
if 'report_data' not in st.session_state: st.session_state.report_data = None
if 'current_emotion' not in st.session_state: st.session_state.current_emotion = "neutral"
if 'last_audio' not in st.session_state: st.session_state.last_audio = None
if 'last_audio_processed' not in st.session_state: st.session_state.last_audio_processed = None

# ==========================================
# 阶段一：简历上传与诊断
# ==========================================
if st.session_state.stage == 'input':
    st.subheader("第一步：简历诊断与人岗匹配")
    col1, col2 = st.columns([1, 1])
    with col1:
        with st.expander("📂 读取历史存档（断点续传）", expanded=False):
            uploaded_history = st.file_uploader("上传之前导出的 .json 存档文件", type=["json"])
            if uploaded_history is not None:
                try:
                    history_data = json.loads(uploaded_history.read().decode("utf-8"))
                    st.session_state.messages = history_data.get("messages", [])
                    st.session_state.analysis_result = history_data.get("analysis_result", {})
                    st.session_state.resume_text = history_data.get("resume_text", "")
                    st.session_state.target_role = history_data.get("target_role", "")
                    st.session_state.question_list = history_data.get("question_list", [])
                    st.session_state.strictness = history_data.get("strictness", 3)
                    st.session_state.current_emotion = history_data.get("current_emotion", "neutral")
                    st.session_state.last_audio = None
                    st.session_state.stage = 'interview'
                    st.success("✅ 存档读取成功，正在恢复现场...")
                    st.rerun()
                except Exception as e:
                    st.error(f"存档解析失败：{e}")

        st.write("**🎯 岗位检索与选择**")
        search_keyword = st.text_input("输入关键词快速过滤（如：产品、运营）", "", placeholder="输入后自动过滤下方岗位...")
        role_list = df['岗位'].unique().tolist()
        if search_keyword: role_list = [r for r in role_list if search_keyword in r]
        role_list.append("其他（自定义输入）")
        target_role_input = st.selectbox("请选择目标岗位", role_list)
        
        custom_role = ""
        if target_role_input == "其他（自定义输入）":
            custom_role = st.text_input("请输入你的目标岗位（如：法务、建筑设计师）")
            st.warning("⚠️ 提示：自定义岗位缺乏专属知识库，专业深度可能不及预设岗位。")

        with st.form("upload_form"):
            uploaded_file = st.file_uploader("上传简历 (支持文本型/图片型 PDF)", type=["pdf"])
            manual_text = st.text_area("或者直接粘贴简历文本", height=150)
            submit_btn = st.form_submit_button("🚀 开始诊断并生成题单", type="primary", use_container_width=True)

        if os.path.exists("demo_resume.pdf"):
            with open("demo_resume.pdf", "rb") as pdf_file:
                demo_pdf_bytes = pdf_file.read()
            st.download_button(label="📥 没有现成简历？点击下载测试用示例 PDF", data=demo_pdf_bytes, file_name="示例简历_产品经理.pdf", mime="application/pdf", use_container_width=True)

        if submit_btn:
            final_role = custom_role.strip() if target_role_input == "其他（自定义输入）" else target_role_input
            if not final_role:
                st.error("请填写自定义岗位名称！")
            else:
                resume_text = ""
                if manual_text.strip(): 
                    resume_text = manual_text
                    st.markdown("<div style='color:#31a24c;font-size:14px;margin-bottom:10px;'>✅ 简历文本读取成功</div>", unsafe_allow_html=True)
                elif uploaded_file is not None:
                    uploaded_file.seek(0)
                    try:
                        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                        extracted_text = ""
                        for page in doc: extracted_text += page.get_text()
                        if len(extracted_text.strip()) < 50:
                            with st.spinner("检测到图片型 PDF，启动 OCR... (预计 5 - 15 秒)"):
                                ocr_text = ""
                                for page in doc:
                                    # 【核心修复】将 2, 2 降为 1.5, 1.5，大幅提升云端速度
                                    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)) 
                                    result, _ = ocr_engine(pix.tobytes("png"))
                                    if result:
                                        for line in result: ocr_text += line[1] + "\n"
                                extracted_text = ocr_text
                            st.markdown("<div style='color:#31a24c;font-size:14px;margin-bottom:10px;'>✅ OCR 识别成功</div>", unsafe_allow_html=True)
                        else:
                            st.markdown("<div style='color:#31a24c;font-size:14px;margin-bottom:10px;'>✅ 简历文本提取成功</div>", unsafe_allow_html=True)
                        resume_text = extracted_text
                    except Exception as e:
                        st.error(f"PDF 解析出错：{e}")

                if not resume_text.strip():
                    st.warning("请先上传或粘贴简历内容！")
                else:
                    st.session_state.analysis_result = None
                    with st.spinner("AI 正在深度解析... (预计 5 - 15 秒)"):
                        prompt = f"""
                        你是一个资深的HR专家。请分析简历，目标岗位是【{final_role}】。
                        评分标准：90-100完全匹配；80-89基本匹配；70-79勉强匹配；60以下不匹配。
                        请严格输出 JSON 格式：
                        {{"profile": {{"核心技能": "...", "项目经历": "...", "优势": "..."}}, "match_analysis": {{"匹配得分": 85, "优势亮点": "...", "欠缺能力": "..."}}, "interview_questions": ["题目1", "题目2", "题目3"]}}
                        简历内容：\n{resume_text}
                        
                        【重要提示】：请确保输出的 JSON 格式合法，内部文本不要使用英文双引号（"），请使用中文双引号（“”），以保证 JSON 结构不被破坏。
                        """
                        try:
                            response = client.chat.completions.create(
                                model="deepseek-flash", messages=[{"role": "user", "content": prompt}],
                                response_format={"type": "json_object"}, temperature=0.1
                            )
                            raw_content = response.choices[0].message.content
                            parsed_json = robust_json_parse(raw_content)
                            st.session_state.analysis_result = parsed_json
                            st.session_state.resume_text = resume_text
                            st.session_state.target_role = final_role
                            st.session_state.question_list = parsed_json.get('interview_questions', [])
                            st.markdown("<div style='color:#31a24c;font-size:14px;margin-bottom:10px;'>✅ AI 深度解析成功</div>", unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"解析失败：{e}")
                            st.code(raw_content)

        if st.session_state.analysis_result:
            with st.expander("📝 定制化面试题单", expanded=True):
                for i, q in enumerate(st.session_state.question_list):
                    st.write(f"**Q{i+1}.** {q}")

    with col2:
        if st.session_state.analysis_result:
            res = st.session_state.analysis_result
            match_data = res.get('match_analysis', {})
            profile_data = res.get('profile', {})
            st.markdown(f"""
            <div style="margin-top: -60px;">
                <div style="font-size: 16px; color: #8b9cb0; margin-bottom: 4px;">与【{st.session_state.target_role}】的匹配度得分</div>
                <div style="font-size: 48px; font-weight: 700; color: #1e2b3c; line-height: 1; margin-bottom: 20px;">
                    {match_data.get('匹配得分', 0)} <span style="font-size: 20px; font-weight: 500;">分</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            with st.expander("👤 求职能力画像", expanded=True):
                st.markdown(f"<div style='color: #2d7ff9; font-weight: 700; font-size: 16px; margin-bottom: 4px;'>核心技能：</div>\n{profile_data.get('核心技能', '')}", unsafe_allow_html=True)
                st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
                st.markdown(f"<div style='color: #31a24c; font-weight: 700; font-size: 16px; margin-bottom: 4px;'>优势：</div>\n{profile_data.get('优势', '')}", unsafe_allow_html=True)
            with st.expander("🎯 人岗匹配分析 **（点击展开）**", expanded=False):
                st.success(f"**优势亮点**：\n{match_data.get('优势亮点', '')}")
                st.error(f"**欠缺能力**：\n{match_data.get('欠缺能力', '')}")

            st.divider()
            st.write("🎛️ **面试官严厉度调节**")
            strictness_input = st.slider("3 = 温和型 HR（推荐） | 7 = 严厉型主管（推荐）", 0, 10, st.session_state.strictness)
            if strictness_input <= 3: st.info("当前模式：温和型 HR")
            elif strictness_input <= 7: st.warning("当前模式：严厉型主管")
            else: st.error("当前模式：地狱压力面")

            if st.button("🎙️ 进入模拟面试环节", type="primary", use_container_width=True):
                st.session_state.stage = 'interview'
                st.session_state.strictness = strictness_input
                first_q = st.session_state.question_list[0] if st.session_state.question_list else "请简单介绍一下你自己"
                st.session_state.current_emotion = "neutral"
                
                base_control = """【角色铁律】：你正在与候选人进行“面对面”的语音面试对话。你不是导师，你是面试官！
【行为禁令】：
1. 绝对禁止代替候选人回答问题，绝不给出标准答案或长篇大论的理论分析。
2. 单次回复严格限制在 150 字以内！直接抛出问题，或者给出最简短的一句话反馈后立刻接下一个问题。
3. 绝对禁止使用 Markdown 列表（如 1. 2. 3. ）、禁止大段加粗。
4. 口语化交流，你只需要提问和追问，把思考和答题的压力给到候选人。
5. 【强指令】：你必须在每条回复的第一个字符就输出隐藏情绪标签，绝不能放在结尾！
格式：`[Emotion: 状态]` 加上你的回复。
状态只能是：neutral（平静提问）, thinking（质疑审视）, satisfied（满意赞许）, guiding（鼓励引导）。
例如：`[Emotion: thinking] 嗯，那你这个数据是怎么算出来的？`
    """
                if strictness_input <= 3: control_prompt = base_control + "\n【温和设定】：语气友善。如果候选人回答较浅，不要过度深挖，直接给个台阶进入下一题。"
                elif strictness_input <= 7: control_prompt = base_control + "\n【严厉设定】：针对逻辑漏洞最多追问2次。候选人承认不足后，立刻切题。"
                else: control_prompt = base_control + "\n【压力设定】：连续深挖逻辑死角，最多追问3次。然后强制切题。"

                questions_context = "\n".join([f"第{i+1}题: {q}" for i, q in enumerate(st.session_state.question_list)])
                system_content = f"""{control_prompt}
                
                当前面试岗位：{st.session_state.target_role}。
                候选人简历摘要：{st.session_state.resume_text[:300]}。
                你的题库清单：
                {questions_context}
                
                请用简短的一句话开场，并直接抛出题库中的第一题（当前提问：{first_q}）。"""

                first_reply_text = f"你好，我是今天的面试官。我们开始吧。\n\n第一题：{first_q}"
                st.session_state.messages = [
                    {"role": "system", "content": system_content},
                    {"role": "assistant", "content": f"[Emotion: neutral] {first_reply_text}"}
                ]
                try:
                    tts_text = first_reply_text.replace("**", "").replace("\n", " ").replace("*", "")
                    audio_file = "temp_voice.mp3"
                    asyncio.run(generate_audio(tts_text, audio_file))
                    with open(audio_file, "rb") as f:
                        st.session_state.last_audio = base64.b64encode(f.read()).decode("utf-8")
                except Exception:
                    st.session_state.last_audio = None
                st.rerun()

# ==========================================
# 阶段二：模拟面试
# ==========================================
elif st.session_state.stage == 'interview':
    col_avatar, col_chat = st.columns([1, 2.5])
    
    with col_avatar:
        video_path = f"assets/{st.session_state.current_emotion}.mp4"
        if os.path.exists(video_path):
            st.video(video_path, autoplay=True, loop=True, muted=True)
        else:
            st.error("视频文件缺失")
        
        st.caption(f"岗位：{st.session_state.target_role} | 严厉度：{st.session_state.strictness}/10")
        st.write("")
        progress_data = {
            "messages": st.session_state.messages,
            "analysis_result": st.session_state.analysis_result,
            "resume_text": st.session_state.resume_text,
            "target_role": st.session_state.target_role,
            "question_list": st.session_state.question_list,
            "strictness": st.session_state.strictness,
            "current_emotion": st.session_state.current_emotion
        }
        st.download_button(label="💾 保存当前面试进度 (JSON存档)", data=json.dumps(progress_data, ensure_ascii=False, indent=2), file_name=f"面试存档_{st.session_state.target_role}_{datetime.now().strftime('%m%d_%H%M')}.json", mime="application/json", use_container_width=True)

    with col_chat:
        if st.session_state.last_audio:
            audio_html = f"""
                <audio autoplay>
                    <source src="data:audio/mp3;base64,{st.session_state.last_audio}" type="audio/mp3">
                </audio>
                <script>
                    var aud = document.getElementsByTagName("audio")[0];
                    aud.play().catch(e => console.log("浏览器拦截了自动播放"));
                </script>
            """
            components.html(audio_html, height=0)

        for msg in st.session_state.messages:
            if msg["role"] != "system":
                display_content = re.sub(r'\[Emotion:\s*\w+\]\s*', '', msg["content"], flags=re.IGNORECASE)
                with st.chat_message(msg["role"], avatar="🧑‍💼" if msg["role"] == "assistant" else "🧑‍🎓"):
                    st.markdown(display_content)

        def process_user_input(text_input, is_voice=False):
            display_text = "🎙️ [语音消息]" if is_voice else text_input
            
            with st.chat_message("user", avatar="🧑‍🎓"): 
                st.markdown(display_text)
            st.session_state.messages.append({"role": "user", "content": text_input})

            with st.chat_message("assistant", avatar="🧑‍💼"):
                with st.spinner("面试官正在思考... (预计 3 - 5 秒)"):
                    response = client.chat.completions.create(
                        model="deepseek-flash", messages=st.session_state.messages, temperature=0.3
                    )
                    raw_reply = response.choices[0].message.content
                    
                    reply_lower = raw_reply.lower()
                    if "thinking" in reply_lower: st.session_state.current_emotion = "thinking"
                    elif "satisfied" in reply_lower: st.session_state.current_emotion = "satisfied"
                    elif "guiding" in reply_lower: st.session_state.current_emotion = "guiding"
                    else: st.session_state.current_emotion = "neutral"
                    
                    display_reply = raw_reply.replace("[Emotion: thinking]", "").replace("[Emotion: satisfied]", "").replace("[Emotion: guiding]", "").replace("[Emotion: neutral]", "")
                    display_reply = display_reply.replace("[emotion: thinking]", "").replace("[emotion: satisfied]", "").replace("[emotion: guiding]", "").replace("[emotion: neutral]", "")
                    st.markdown(display_reply)
                    
                    try:
                        tts_text = display_reply.replace("**", "").replace("\n", " ").replace("*", "")
                        audio_file = "temp_voice.mp3"
                        asyncio.run(generate_audio(tts_text, audio_file))
                        with open(audio_file, "rb") as f:
                            st.session_state.last_audio = base64.b64encode(f.read()).decode("utf-8")
                    except Exception:
                        st.session_state.last_audio = None
                    
            st.session_state.messages.append({"role": "assistant", "content": raw_reply})
            st.rerun()

        if asr_client:
            st.write("🎙️ **语音输入（点击麦克风录音）**")
            audio_value = st.audio_input("Record a voice message", label_visibility="collapsed")
            
            if audio_value is not None:
                audio_hash = hash(audio_value.getvalue())
                if st.session_state.last_audio_processed != audio_hash:
                    st.session_state.last_audio_processed = audio_hash
                    with st.spinner("正在识别语音..."):
                        user_text = transcribe_audio(audio_value.getvalue())
                        clean_text = re.sub(r'[^\w\u4e00-\u9fa5]', '', user_text)
                        if len(clean_text) >= 2:
                            process_user_input(user_text, is_voice=True)
                        else:
                            st.warning("⚠️ 没听清，可能是麦克风兼容问题或环境嘈杂，请重试或使用下方文本输入。")
        else:
            st.info("💡 想要体验语音对话？请在 deepseek.txt 第二行填入 SiliconFlow API Key。")

        st.write("---")
        st.write("⌨️ **或 文本输入**")
        if user_input := st.chat_input("请输入你的回答..."):
            process_user_input(user_input, is_voice=False)

        st.divider()
        col_a, col_b = st.columns([1, 1])
        with col_a:
            if st.button("🛑 结束面试并生成复盘报告", type="primary", use_container_width=True):
                st.session_state.stage = 'report'
                st.rerun()
        with col_b:
            if st.button("🔄 放弃面试，返回首页", use_container_width=True):
                st.session_state.stage = 'input'
                st.session_state.messages = []
                st.session_state.last_audio = None
                st.rerun()

# ==========================================
# 阶段三：复盘报告
# ==========================================
elif st.session_state.stage == 'report':
    st.subheader("📊 面试复盘与进阶报告")
    if st.session_state.report_data is None:
        with st.spinner("导师 Agent 正在深度分析你的面试表现... (预计 5 - 15 秒)"):
            chat_history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages if m['role'] != 'system'])
            prompt = f"""
            你是一个资深导师。根据对话记录输出 JSON 复盘报告。
            岗位：{st.session_state.target_role}。严厉度：{st.session_state.strictness}/10
            对话：{chat_history}
            
            请严格输出 JSON 格式，用第二人称“你”：
            {{
                "scores": {{"逻辑表达": 85, "专业深度": 70, "抗压能力": 90}},
                "highlights": "【教练赋能评语】先肯定候选人的具体表现，赋予职场意义。",
                "weaknesses": "【职场避坑指南】指出候选人回答中的漏洞，并给出反向应对策略。",
                "interaction_feedback": "【沟通交互反馈】客观评估候选人是否顺着面试官的节奏作答。",
                "suggestions": "【下一步行动】给出三条具体的、可执行的提升建议。"
            }}
            """
            try:
                response = client.chat.completions.create(
                    model="deepseek-flash", messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}, temperature=0.4
                )
                parsed_json = robust_json_parse(response.choices[0].message.content)
                st.session_state.report_data = parsed_json
                st.markdown("<div style='color:#31a24c;font-size:14px;margin-bottom:10px;'>✅ 复盘报告生成成功</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"报告生成失败：{e}")

    if st.session_state.report_data:
        report_data = st.session_state.report_data
        scores = report_data.get("scores", {})
        col_chart, col_metrics = st.columns([1.2, 1])
        with col_chart:
            categories = list(scores.keys())
            values = list(scores.values())
            fig = go.Figure(data=go.Scatterpolar(
                r=values + [values[0]], theta=categories + [categories[0]],
                fill='toself', line_color='#2d7ff9', fillcolor='rgba(45,127,249,0.15)',
                mode='lines+markers+text', text=values + [values[0]], textposition='top center',
                textfont=dict(size=13, color='#1e2b3c')
            ))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100], showticklabels=False)),
                showlegend=False, margin=dict(l=40, r=40, t=40, b=40), height=320,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        with col_metrics:
            st.write("### 能力得分")
            for k, v in scores.items():
                st.metric(label=k, value=f"{v} 分")
        st.divider()
        def clean_text(text): return str(text).replace('\n', '<br>').replace('\r', '')
        st.markdown(f"""
        <div class="report-card" style="border-left: 4px solid #31a24c;"><div class="report-card-title">🌟 教练赋能评语</div><div style="color: #1e2b3c; line-height: 1.7; font-size: 15px;">{clean_text(report_data.get('highlights', ''))}</div></div>
        <div class="report-card" style="border-left: 4px solid #e53935;"><div class="report-card-title">🛡️ 职场避坑指南</div><div style="color: #1e2b3c; line-height: 1.7; font-size: 15px;">{clean_text(report_data.get('weaknesses', ''))}</div></div>
        <div class="report-card" style="border-left: 4px solid #f59e0b;"><div class="report-card-title">🗣️ 沟通交互反馈</div><div style="color: #1e2b3c; line-height: 1.7; font-size: 15px;">{clean_text(report_data.get('interaction_feedback', '暂无反馈'))}</div></div>
        <div class="report-card" style="border-left: 4px solid #2d7ff9;"><div class="report-card-title">🚀 下一步行动建议</div><div style="color: #1e2b3c; line-height: 1.7; font-size: 15px;">{clean_text(report_data.get('suggestions', ''))}</div></div>
        """, unsafe_allow_html=True)
        st.write("") 
        md_content = f"# 面试复盘报告\n\n**教练赋能评语**\n{report_data.get('highlights', '')}\n\n**职场避坑指南**\n{report_data.get('weaknesses', '')}\n\n**沟通交互反馈**\n{report_data.get('interaction_feedback', '')}\n\n**下一步行动建议**\n{report_data.get('suggestions', '')}\n"
        st.download_button(label="📥 下载复盘报告 (Markdown)", data=md_content, file_name=f"面试复盘报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md", mime="text/markdown", type="primary", use_container_width=True)
    st.divider()
    if st.button("🏠 返回首页，开始新一轮练习", use_container_width=True):
        st.session_state.stage = 'input'
        st.session_state.messages = []
        st.session_state.resume_text = ""
        st.session_state.analysis_result = None
        st.session_state.report_data = None
        st.session_state.last_audio = None
        st.rerun()

st.markdown(f"<div class='version-tag'>面试先锋 {APP_VERSION}</div>", unsafe_allow_html=True)
