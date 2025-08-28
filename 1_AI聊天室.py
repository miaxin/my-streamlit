import streamlit as st
import google.generativeai as genai
import os

# --- Gemini API Configuration ---
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Gemini API key not found in .streamlit/secrets.toml. 請確保您的主應用程式檔案已配置 API key。")
    st.stop()
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# 初始化 Gemini Pro 模型
@st.cache_resource(ttl="30min") 
def get_gemini_model():
    try:
        return genai.GenerativeModel('gemini-2.5-flash')
    except Exception as e:
        st.error(f"未能初始化 Gemini 模型: {e}")
        st.stop()

gemini_model = get_gemini_model()

# --- 初始化聊天會話，保留歷史記錄 ---
if "chat" not in st.session_state:
    st.session_state.chat = gemini_model.start_chat(history=[])

st.title("💬 AI 財務聊天機器人")
st.markdown("---")
st.write("您好！我是您的 AI 財務分析助理，能根據您上傳的 CSV 分析數據進行問答。")

# --- 顯示聊天歷史 ---
for message in st.session_state.chat.history:
    role = "user" if message.role == "user" else "assistant"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# --- 聊天輸入框 ---
user_query = st.chat_input("請輸入您的問題...")

if user_query:
    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant"):
        with st.spinner("AI 正在分析中..."):
            try:
                # 讀取另一個頁面存的 CSV 資料
                processed_df_str = ""
                if 'processed_df' in st.session_state:
                    df = st.session_state['processed_df']

                    # 只傳遞前 5 筆資料當摘要
                    df_summary = df.head().to_markdown(index=False)
                    processed_df_str = f"\n\n以下是您上傳的數據摘要：\n{df_summary}\n\n"

                # 建立完整 Prompt
                full_prompt = f"{user_query}{processed_df_str}\n請用中文回答。"

                # 送到 Gemini
                response = st.session_state.chat.send_message(full_prompt)

                if response and response.text:
                    st.markdown(response.text)
                else:
                    st.warning("AI 無法生成回覆，請稍後再試。")
            except Exception as e:
                st.error(f"聊天機器人錯誤: {e}")
