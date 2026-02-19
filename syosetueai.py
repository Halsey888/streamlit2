import streamlit as st
import google.generativeai as genai
import os

# 頁面配置
st.set_page_config(page_title="Gemini 小說創作軍師", layout="wide")
st.title("🖋️ Gemini 小說創作軍師：冷酷編輯模式")

# --- 側邊欄：設定 ---
with st.sidebar:
    st.header("⚙️ 寫作設定")
    api_key = st.text_input("輸入 Gemini API Key", type="password")
    
    st.divider()
    novel_path = st.text_input("【我的作品】路徑 (你的草稿檔)")
    # 新增參考資料路徑
    ref_path = st.text_input("【風格參考】路徑 (存放你喜歡的韓國網文翻譯)")
    
    model_name = st.selectbox("選擇模型", ["gemini-2.5-pro", "gemini-2.5-flash"])
    clear_chat = st.button("清空對話紀錄")

# --- 讀取工具 (通用) ---
def get_folder_content(path, label="內容"):
    content = ""
    if not path or not os.path.exists(path):
        return ""
    valid_extensions = ('.txt', '.md')
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(valid_extensions):
                try:
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        content += f"\n\n--- [{label}] 檔案: {file} ---\n{f.read()}\n"
                except: pass
    return content

# --- 初始化 AI ---
if api_key:
    genai.configure(api_key=api_key)
    
    # 針對韓國網文風格優化的指令
    system_prompt = (
        "你是一位精通韓國網文（Naver Series/KakaoPage 風格）的資深編輯。"
        "你會分析使用者提供的『風格參考資料』，學習其敘事節奏、文字張力與角色互動方式。"
        "\n\n你的任務規則：\n"
        "1. **風格一致性**：當我寫作時，請確保建議的文字符合韓國網文那種『快節奏、畫面感強、情感強烈』的特徵。\n"
        "2. **拒絕平庸**：如果我的描述太過溫吞，請模仿參考資料中的張力進行毒舌批評並改寫。\n"
        "3. **專有名詞與語氣**：注意參考資料中的翻譯語氣，在改寫範例中保持一致。"
    )
    if "chat" not in st.session_state or clear_chat:
        model = genai.GenerativeModel(model_name=model_name, system_instruction=system_prompt)
        st.session_state.chat = model.start_chat(history=[])
        st.session_state.messages = []

# --- 讀取小說文本工具 ---
def get_novel_context(path):
    context = ""
    if not path or not os.path.exists(path):
        return ""
    
    # 只讀取常見的文本檔案
    valid_extensions = ('.txt', '.md', '.markdown')
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(valid_extensions):
                try:
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        # 標註檔名，讓 AI 知道這是哪一章或哪個設定檔
                        context += f"\n\n--- 檔案內容: {file} ---\n{f.read()}\n"
                except: pass
    return context

# --- 主介面：顯示對話 ---
if "messages" in st.session_state:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- 主邏輯：發送訊息 ---
if prompt := st.chat_input("請描述你的問題..."):
    # ... (省略)
    
    # 組合三種 Context：參考資料 + 我的草稿 + 當前問題
    my_draft = get_folder_content(novel_path, label="我的草稿")
    ref_style = get_folder_content(ref_path, label="韓國網文風格參考")
    
    full_prompt = (
        f"【風格參考基準】(請學習此類文字的節奏與語氣):\n{ref_style}\n\n"
        f"【我的目前作品內容】:\n{my_draft}\n\n"
        f"【當前任務】:\n{prompt}"
    )
    # 呼叫 Gemini 並顯示回覆
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
            
        try:
            response = st.session_state.chat.send_message(full_prompt, stream=True)
            for chunk in response:
                full_response += chunk.text
                response_placeholder.markdown(full_response + "▌")
            response_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
        except Exception as e:
            st.error(f"發生錯誤：{str(e)}")