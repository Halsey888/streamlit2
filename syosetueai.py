import streamlit as st
import google.generativeai as genai
import os
import random

# 1. 頁面配置
st.set_page_config(page_title="Gemini 韓漫風格助手", layout="wide")
st.title("🖋️ Gemini 小說助手 (風格指南強化版)")

# 2. 初始化 Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "style_guide" not in st.session_state:
    st.session_state.style_guide = "" # 存放提取出的風格指南

# --- 側邊欄：設定 ---
with st.sidebar:
    st.header("⚙️ 寫作設定")
    api_key = st.text_input("輸入 Gemini API Key", type="password")
    
    st.divider()
    novel_path = st.text_input("【我的草稿路徑】")
    ref_path = st.text_input("【海量參考路徑】")
    
    # 風格指南區塊
    st.subheader("📝 韓式寫作風格指南")
    if st.button("🪄 從樣本提取風格基因"):
        if not api_key or not ref_path:
            st.error("請先輸入 API Key 與 參考路徑！")
        else:
            with st.spinner("正在分析 150 萬字樣本中的風格精華..."):
                # 這裡調用 AI 進行一次性分析
                genai.configure(api_key=api_key)
                temp_model = genai.GenerativeModel("gemini-2.5-flash") # 用 Flash 提取省錢又快
                
                # 抽樣讀取參考資料
                def get_sample_for_analysis(path):
                    files = [f for f in os.listdir(path) if f.endswith(('.txt', '.md'))]
                    random.shuffle(files)
                    content = ""
                    for f in files[:5]: # 抽 5 個檔
                        with open(os.path.join(path, f), 'r', encoding='utf-8') as file:
                            content += file.read()[:3000] + "\n"
                    return content
                
                analysis_sample = get_sample_for_analysis(ref_path)
                extract_prompt = f"""
                你是一位金牌編輯。請分析以下韓國網文範本，並整理出一份《寫作風格指南》。
                內容須包含：
                1. 敘事節奏與換行邏輯。
                2. 角色對話特徵（語氣、標點）。
                3. 內心獨白的處理方式。
                4. 如何營造懸念。
                範本內容：\n{analysis_sample}
                """
                response = temp_model.generate_content(extract_prompt)
                st.session_state.style_guide = response.text
                st.success("風格指南提取成功！")

    # 顯示並允許手動修改風格指南
    st.session_state.style_guide = st.text_area(
        "目前的風格指南 (可手動調整):", 
        value=st.session_state.style_guide, 
        height=300
    )
    
    st.divider()
    max_ref_chars = st.slider("每次對話參考字數上限", 10000, 200000, 50000)
    model_name = st.selectbox("選擇模型", ["gemini-2.5-pro", "gemini-2.5-flash"])
    
    if st.button("🚨 清除對話紀錄"):
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.rerun()

# --- 讀取工具 ---
def get_safe_content(path, max_chars=50000):
    if not path or not os.path.exists(path):
        return ""
    files = [f for f in os.listdir(path) if f.endswith(('.txt', '.md'))]
    random.shuffle(files)
    current_chars = 0
    context = ""
    for file in files:
        if current_chars > max_chars: break
        try:
            with open(os.path.join(path, file), 'r', encoding='utf-8') as f:
                text = f.read()
                context += f"\n\n--- [範例檔: {file}] ---\n{text[:3000]}\n"
                current_chars += len(text)
        except: pass
    return context

# --- 初始化 AI ---
if api_key:
    genai.configure(api_key=api_key)
    
    # 針對韓國網文風格優化的指令
    system_prompt = (
        "你是一位精通韓國網文（Naver Series/KakaoPage）的資深編輯。"
        "你的任務是根據『寫作風格指南』嚴格審核使用者的草稿。"
        "\n\n你的互動規則：\n"
        "1. **嚴師模式**：絕對不要一味稱讚。如果文字不夠『韓味』、節奏太慢、廢話太多，請直接給予精準的批評。\n"
        "2. **對標改寫**：每一次建議後，請附上一段符合風格指南的改寫示範。\n"
        "3. **保持指南精神**：對話中請時刻參考側邊欄定義的寫作特徵。"
    )
    # 建立模型與對話物件（將歷史紀錄傳入）
    model = genai.GenerativeModel(model_name=model_name, system_instruction=system_prompt)
    # 這裡使用 st.session_state.chat_history 來保持連貫性
    chat_session = model.start_chat(history=st.session_state.chat_history)

# --- 主介面 ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("輸入你想討論的段落..."):
    if not api_key:
        st.error("請先輸入 API Key！")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 組合 Context
        ref_sample = get_safe_content(ref_path, max_chars=max_ref_chars)
        my_draft = get_safe_content(novel_path, max_chars=30000)
        
        full_prompt = (
            f"【核心風格指南】(必須嚴格遵守):\n{st.session_state.style_guide}\n\n"
            f"【具體參考樣本】:\n{ref_sample}\n\n"
            f"【我的作品上下文】:\n{my_draft}\n\n"
            f"【當前任務】: {prompt}"
        )

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            try:
                response = chat_session.send_message(full_prompt, stream=True)
                for chunk in response:
                    full_response += chunk.text
                    response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(full_response)
                
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                st.session_state.chat_history = chat_session.history
            except Exception as e:
                st.error(f"發生錯誤：{str(e)}")
