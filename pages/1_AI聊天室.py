# pages/2_💰_財務機器人.py
import streamlit as st
import os
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="💰 財務機器人", layout="wide")
st.title("💰 AI 財務聊天機器人")

# --- API Key ---
if "GOOGLE_API_KEY" not in st.session_state or not st.session_state["GOOGLE_API_KEY"]:
    st.error("⚠️ 請先在首頁輸入 Gemini API Key")
    st.stop()

os.environ["GOOGLE_API_KEY"] = st.session_state["GOOGLE_API_KEY"]
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# --- CSV 檢查 ---
if "uploaded_df" not in st.session_state:
    st.warning("⚠️ 尚未上傳 CSV 檔案，請先到首頁上傳")
    st.stop()
else:
    df = st.session_state["uploaded_df"]

# --- 對話紀錄 ---
if "finance_chat_history" not in st.session_state:
    st.session_state.finance_chat_history = []

# --- 側邊欄工具 ---
with st.sidebar:
    st.subheader("⚙️ 工具")
    if st.button("🧹 清除對話"):
        st.session_state.finance_chat_history = []
        st.success("對話已清除")

# --- 使用者輸入 ---
user_input = st.chat_input("輸入你的財務問題...")

if user_input:
    st.session_state.finance_chat_history.append({"role": "user", "content": user_input})

    # 使用 Gemini 模型
    model = genai.GenerativeModel("gemini-2.5-flash")
    chat = model.start_chat(
        history=[{"role": msg["role"], "parts": [msg["content"]]}
                 for msg in st.session_state.finance_chat_history if msg["role"] in ["user", "model"]]
    )

    # 將 CSV 當成上下文（可轉成文字或摘要）
    csv_context = df.head(10).to_csv(index=False)  # 只取前 10 行，避免太大

    response = chat.send_message(f"以下是財務資料：\n{csv_context}\n使用者問題：{user_input}")

    st.session_state.finance_chat_history.append({"role": "model", "content": response.text})

# --- 顯示對話 ---
for msg in st.session_state.finance_chat_history:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.write(msg["content"])
    else:
        with st.chat_message("assistant"):
            st.write(msg["content"])
