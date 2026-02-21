import streamlit as st
import google.generativeai as genai
import os
import random
import json

# --- 持久化設定 ---
SAVE_FILE = "novel_history.json"

def save_to_local():
    """將當前對話紀錄存入檔案"""
    data = {
        "messages": st.session_state.messages,
        "chat_history": [
            {"role": m.role, "parts": [p.text for p in m.parts]} 
            for m in st.session_state.chat_history
        ],
        "style_guide": st.session_state.style_guide
    }
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_from_local():
    """從檔案讀取舊紀錄"""
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                st.session_state.messages = data.get("messages", [])
                st.session_state.style_guide = data.get("style_guide", "")
                # 重新還原為 Gemini 可讀的格式
                st.session_state.chat_history = [
                    {"role": h["role"], "parts": h["parts"]} for h in data.get("chat_history", [])
                ]
                return True
        except: return False
    return False

# 1. 頁面配置
st.set_page_config(page_title="Gemini 韓漫風格助手", layout="wide")
st.title("🖋️ Gemini 小說助手 (紀錄自動保存版)")

# 2. 初始化 Session State (先嘗試讀取舊檔)
if "messages" not in st.session_state:
    if not load_from_local():
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.session_state.style_guide = ""

# --- 側邊欄：設定 ---
with st.sidebar:
    st.header("⚙️ 寫作設定")
    api_key = st.text_input("輸入 Gemini API Key", type="password")
    
    st.divider()
    # 新增：備份下載按鈕 (這是給手滑後的最後一道保險)
    if st.session_state.messages:
        history_json = json.dumps({
            "messages": st.session_state.messages,
            "style_guide": st.session_state.style_guide
        }, ensure_ascii=False)
        st.download_button(
            label="📥 下載對話備份 (以防雲端重置)",
            data=history_json,
            file_name="novel_backup.json",
            mime="application/json"
        )

    st.divider()
    novel_path = st.text_input("【我的草稿路徑】")
    ref_path = st.text_input("【海量參考路徑】")
    
    st.subheader("📝 韓式寫作風格指南")
    if st.button("🪄 從樣本提取風格基因"):
        if not api_key or not ref_path:
            st.error("請先輸入 API Key 與 參考路徑！")
        else:
            with st.spinner("正在分析樣本..."):
                genai.configure(api_key=api_key)
                temp_model = genai.GenerativeModel("gemini-1.5-flash") 
                
                def get_sample_for_analysis(path):
                    files = [f for f in os.listdir(path) if f.endswith(('.txt', '.md'))]
                    random.shuffle(files)
                    content = ""
                    for f in files[:5]:
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
        "你是一位『專屬故事架構助手』。你的唯一使命是幫助使用者將他喜愛的各種靈感碎片，串聯成一個邏輯自洽且完整的精彩故事。\n\n"
        "你的運作準則：\n"
        "1. **尊重創作者喜好**：使用者喜歡的元素就是最高指令。絕對不要以『讀者可能不喜歡』或『市場不流行』為由要求更動內容。你的任務是讓使用者的喜好在故事中顯得合理且更有魅力。\n"
        "2. **邏輯鏈條構建**：當使用者提供碎片場景時，請分析這些場景間的『因果空隙』。透過提問，引導使用者思考：『為了達成場景 B，場景 A 之後需要發生什麼？』\n"
        "3. **深度挖掘與擴張**：不要只給肯定，要給予『擴張性建議』。例如：『既然你喜歡這個設定，那這個設定在世界觀中會不會導致某種有趣的現象？』\n"
        "4. **保持風格，不改靈魂**：你可以利用參考資料中的『韓式敘事節奏』（如畫面感強、節奏快）來潤色文字，但絕對不要改變故事的核心意圖。\n"
        "5. **對話結構**：每次回覆請包含：\n"
        "   - 【靈感解析】：分析使用者剛才提到的元素中，最迷人的部分是什麼。\n"
        "   - 【邏輯橋樑】：提出 3 個能幫助這些碎片『黏合』在一起的關鍵問題。\n"
        "   - 【擴張想像】：基於目前的設定，推演出一個使用者可能會感興趣的後續可能性。"
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

                # --- 每回覆一次，就執行一次自動存檔 ---
                save_to_local()
            except Exception as e:
                st.error(f"發生錯誤：{str(e)}")



