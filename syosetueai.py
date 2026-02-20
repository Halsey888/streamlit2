import streamlit as st
import google.generativeai as genai
import os
import random

# 1. 頁面配置
st.set_page_config(page_title="Gemini 韓漫風格助手", layout="wide")
st.title("🖋️ Gemini 小說助手 (海量參考最佳化版)")

# 2. 初始化 Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- 側邊欄：設定 ---
with st.sidebar:
    st.header("⚙️ 寫作設定")
    api_key = st.text_input("輸入 Gemini API Key", type="password")
    
    st.divider()
    novel_path = st.text_input("【我的草稿路徑】")
    ref_path = st.text_input("【海量參考路徑】")
    
    # 增加安全限制設定
    max_ref_chars = st.slider("參考資料字數上限 (建議 20萬字內)", 10000, 500000, 100000)
    read_mode = st.radio("參考資料讀取模式", ["隨機抽樣 (推薦)", "讀取前幾檔"])
    
    model_name = st.selectbox("選擇模型", ["gemini-2.5-pro", "gemini-2.5-flash"])
    
    if st.button("🚨 清除對話紀錄"):
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.rerun()

# --- 優化後的讀取工具 ---
def get_safe_content(path, max_chars=100000, mode="隨機抽樣 (推薦)"):
    all_content = []
    if not path or not os.path.exists(path):
        return ""
    
    files = [f for f in os.listdir(path) if f.endswith(('.txt', '.md'))]
    
    if mode == "隨機抽樣 (推薦)":
        random.shuffle(files) # 打亂順序，讓 AI 看到不同章節的風格
        
    current_chars = 0
    context = ""
    for file in files:
        if current_chars > max_chars:
            break
        try:
            with open(os.path.join(path, file), 'r', encoding='utf-8') as f:
                text = f.read()
                context += f"\n\n--- [參考檔: {file}] ---\n{text[:5000]}\n" # 每個檔案取精華部分
                current_chars += len(text)
        except: pass
    return context

# --- 初始化 AI ---
if api_key:
    genai.configure(api_key=api_key)
    
    # 針對韓國網文風格優化的指令
    system_prompt = (
        "你是一位精通韓國網文（Naver Series/KakaoPage 風格）的資深編輯。"
        "你會分析使用者提供的『風格參考資料』，學習其敘事節奏、文字張力與角色互動方式。"
        "\n\n你的任務規則：\n"
        "1. **風格一致性**：當我寫作時，請確保建議的文字符合韓國網文那種『畫面感強、角色情感描寫細膩、頻繁換行』的特徵。\n"
        "2. **專業分析**：如果我的描述太過溫吞，請模仿參考資料中的張力進行適當批評並改寫。\n"
        "3. **專有名詞與語氣**：注意參考資料中的翻譯語氣，在改寫範例中保持一致。"
        "4. **內部思考**：回答前先分析角色動機與節奏感。"
    )
    # 建立模型與對話物件（將歷史紀錄傳入）
    model = genai.GenerativeModel(model_name=model_name, system_instruction=system_prompt)
    # 這裡使用 st.session_state.chat_history 來保持連貫性
    chat_session = model.start_chat(history=st.session_state.chat_history)

# --- 主介面：顯示歷史訊息 ---
# 每次畫面重新整理時，都會從 session_state 抓出來重新畫一次
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 使用者輸入 ---
if prompt := st.chat_input("輸入你想討論的段落..."):
    if not api_key:
        st.error("請先輸入 API Key！")
    else:
        # 1. 顯示並儲存使用者訊息
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 這裡使用安全讀取機制，避免爆 Token
        ref_style = get_safe_content(ref_path, max_chars=max_ref_chars, mode=read_mode)
        my_draft = get_safe_content(novel_path, max_chars=50000) # 草稿限制
        
        full_prompt = (
            f"【風格參考基準】:\n{ref_style}\n\n"
            f"【我的作品上下文】:\n{my_draft}\n\n"
            f"【使用者問題】: {prompt}"
        )

        # 3. 呼叫 Gemini 並顯示流式回覆
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            
            try:
                # 注意：這裡使用 chat_session.send_message，它會自動處理歷史紀錄
                response = chat_session.send_message(full_prompt, stream=True)
                for chunk in response:
                    full_response += chunk.text
                    response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(full_response)
                
                # 4. 重要：更新 session_state 裡的紀錄
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                # 同步更新 chat_session 的歷史回 st.session_state
                st.session_state.chat_history = chat_session.history
                
            except Exception as e:
                st.error(f"發生錯誤：{str(e)}")
