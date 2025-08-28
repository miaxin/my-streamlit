# pages/0_首頁.py 或 main.py
import streamlit as st

st.title("API Key 設定")

api_key_input = st.text_input("請輸入 Gemini API Key", type="password")

if api_key_input:
    st.session_state["GOOGLE_API_KEY"] = api_key_input
    st.success("API Key 已儲存，可跨頁使用")
    
if "GOOGLE_API_KEY" not in st.session_state:
    st.error("⚠️ 請先在首頁輸入 Gemini API Key")
    st.stop()
else:
    # 明確用 session_state 的 key 初始化
    genai.configure(api_key=st.session_state["GOOGLE_API_KEY"])
