import streamlit as st
import google.generativeai as genai
import pandas as pd
import os

# --- Gemini API Configuration ---
# 確保 API key 已配置
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Gemini API key not found in .streamlit/secrets.toml. 請確保您的主應用程式檔案已配置 API key。")
    st.stop()
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# 初始化 Gemini Pro 模型和聊天會話
# 使用 st.cache_resource 來快取模型，避免每次頁面重新運行時都重新初始化
@st.cache_resource(ttl="30min")
def get_gemini_model():
    try:
        return genai.GenerativeModel('gemini-2.5-flash')
    except Exception as e:
        st.error(f"未能初始化 Gemini 模型: {e}")
        st.stop()

gemini_model = get_gemini_model()

# 初始化聊天會話，並將歷史記錄儲存在 session_state 中
# 這裡修改了初始化的 history，給予AI一個通用的角色提示
if "chat" not in st.session_state:
    st.session_state.chat = gemini_model.start_chat(history=[
        {"role": "user", "parts": ["你是一個多功能AI助手，可以回答各種主題的問題，不限於特定領域。"]},
        {"role": "model", "parts": ["好的，我明白了。我會盡力回答您的各種問題。請問有什麼可以幫助您的嗎？"]}
    ])

st.title("💬 AI 聊天機器人 (通用型)") # 修改標題，讓用戶知道這是通用型
st.markdown("---")
st.write("您好！我是您的 AI 助理。您可以問我任何問題，不論是財務相關還是其他主題，我都會盡力為您提供幫助。")
st.write("請輸入您的問題，我會盡力為您提供幫助。")

# 顯示聊天歷史記錄
for message in st.session_state.chat.history:
    role = "user" if message.role == "user" else "assistant"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# 聊天輸入框
user_query = st.chat_input("請輸入您的問題...")

if user_query:
    # 將用戶消息添加到聊天歷史並顯示
    with st.chat_message("user"):
        st.markdown(user_query)
    
    # 獲取 AI 回覆
    with st.chat_message("assistant"):
        with st.spinner("AI 思考中..."):
            try:
                # 準備財務數據上下文，但以更中立的方式傳遞
                processed_df_context = ""
                if 'processed_df' in st.session_state and not st.session_state['processed_df'].empty:
                    df_summary = st.session_state['processed_df'].head(5).to_markdown(index=False)
                    # 這裡將財務數據描述為「可參考的資訊」，而不是主要分析對象
                    processed_df_context = f"\n\n[參考資訊：這裡有一份您上傳的財務數據摘要，如果我的問題與財務相關，請參考這些數據進行回答：\n{df_summary}\n]\n"
                
                # 組合最終傳給 AI 的提示詞
                # 我們已經在 start_chat 時設定了通用角色，這裡只需傳遞用戶問題和可能的數據上下文
                full_prompt = f"{user_query}{processed_df_context}\n請用繁體中文回答。"
                
                response = st.session_state.chat.send_message(full_prompt)
                
                if response and response.text:
                    st.markdown(response.text)
                else:
                    st.warning("AI 無法生成回覆，請稍後再試。")
            except Exception as e:
                st.error(f"聊天機器人錯誤: {e}")