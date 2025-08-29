# pages/2_💰_財務機器人.py
import os
import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="💰 財務機器人", layout="wide")
st.title("💰 AI 財務聊天機器人")

# --- 檢查首頁是否有輸入 API Key ---
if "GOOGLE_API_KEY" not in st.session_state or not st.session_state["GOOGLE_API_KEY"]:
    st.error("⚠️ 請先在首頁輸入 Gemini API Key")
    st.stop()

# --- 設定環境變數 & SDK ---
os.environ["GOOGLE_API_KEY"] = st.session_state["GOOGLE_API_KEY"]
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# --- 初始化對話紀錄 ---
if "finance_chat_history" not in st.session_state:
    st.session_state.finance_chat_history = []

# --- 側邊欄工具 ---
with st.sidebar:
    st.subheader("⚙️ 工具")
    if st.button("🧹 清除對話", use_container_width=True):
        st.session_state.finance_chat_history = []
        st.success("對話已清除，開始新的聊天吧！")

# --- 使用者輸入 ---
user_input = st.chat_input("輸入你的財務問題...")

if user_input:
    # 存使用者訊息
    st.session_state.finance_chat_history.append({"role": "user", "content": user_input})

    # 建立 Gemini 模型
    model = genai.GenerativeModel("gemini-2.5-flash")

    # 建立對話（含歷史）
    chat = model.start_chat(
        history=[
            {"role": msg["role"], "parts": [msg["content"]]}
            for msg in st.session_state.finance_chat_history
            if msg["role"] in ["user", "model"]
        ]
    )

    # 發送訊息並取得回覆
    response = chat.send_message(user_input)

    # 存 AI 回覆
    st.session_state.finance_chat_history.append({"role": "model", "content": response.text})

# --- 顯示對話紀錄 ---
for msg in st.session_state.finance_chat_history:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.write(msg["content"])
    else:
        with st.chat_message("assistant"):
            st.write(msg["content"])
