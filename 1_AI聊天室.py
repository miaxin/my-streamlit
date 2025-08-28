# pages/1_🤖_AI_聊天室.py
import streamlit as st
import google.generativeai as genai

# --- Gemini API Configuration ---
st.sidebar.subheader("🔑 Gemini API 設定")
api_key = st.sidebar.text_input("輸入 Gemini API Key", type="password")

if api_key:
    st.session_state["GOOGLE_API_KEY"] = api_key

if "GOOGLE_API_KEY" not in st.session_state:
    st.error("❌ 請先在側邊欄輸入 Gemini API Key")
    st.stop()
else:
    genai.configure(api_key=st.session_state["GOOGLE_API_KEY"])

# --- 初始化 Gemini 模型 ---
@st.cache_resource(ttl="30min")
def get_gemini_model():
    return genai.GenerativeModel("gemini-2.5-flash")

gemini_model = get_gemini_model()

# --- 初始化聊天 ---
if "chat" not in st.session_state:
    st.session_state.chat = gemini_model.start_chat(history=[])

st.title("💬 AI 財務聊天機器人")
st.markdown("---")
st.write("您好！我是您的 AI 財務分析助理。")
st.write("您可以問我任何關於財務分析、市場趨勢或您上傳數據中公司的問題。")

# --- 顯示歷史訊息 ---
for message in st.session_state.chat.history:
    role = "user" if message.role == "user" else "assistant"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# --- 聊天輸入 ---
user_query = st.chat_input("請輸入您的問題...")

if user_query:
    # 顯示使用者訊息
    with st.chat_message("user"):
        st.markdown(user_query)

    # 加上 CSV 數據摘要 (如果有上傳)
    processed_df_str = ""
    if "processed_df" in st.session_state:
        df_summary = st.session_state["processed_df"].head().to_markdown(index=False)
        processed_df_str = f"\n\n以下是您上傳的數據摘要 (前 5 筆)：\n{df_summary}\n\n"

    # 組合完整 prompt
    full_prompt = f"{user_query}{processed_df_str}\n請用中文回答。"

    # AI 回覆
    with st.chat_message("assistant"):
        with st.spinner("AI 思考中..."):
            try:
                response = st.session_state.chat.send_message(full_prompt)
                if response and response.text:
                    st.markdown(response.text)
                else:
                    st.warning("⚠️ AI 無法生成回覆，請稍後再試。")
            except Exception as e:
                st.error(f"聊天機器人錯誤: {e}")
