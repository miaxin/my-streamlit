import streamlit as st
import openai  # 假設使用 OpenAI 或 Gemini API

# -----------------------------
# 1️⃣ 確認 API Key 是否已存於 session_state
# -----------------------------
if "GOOGLE_API_KEY" not in st.session_state:
    st.warning("請先在首頁輸入 API Key")
    st.stop()

api_key = st.session_state["GOOGLE_API_KEY"]

# -----------------------------
# 2️⃣ 頁面標題
# -----------------------------
st.title("📈 AI 專業經理人團隊整合分析")
st.markdown("模擬 CFO、COO、CEO 三位專家一次生成完整報告")

# -----------------------------
# 3️⃣ 商業問題輸入
# -----------------------------
business_question = st.text_area(
    "請輸入您的商業問題或分析需求",
    placeholder="例如：請分析新產品的投資回報與營運風險..."
)

# -----------------------------
# 4️⃣ 單次 API 請求生成報告
# -----------------------------
if st.button("生成整合報告") and business_question.strip():
    with st.spinner("AI 專業經理人團隊正在分析中..."):

        # 使用 API Key 呼叫模型
        openai.api_key = api_key
        prompt = f"""
        模擬一個由 CFO、COO、CEO 組成的專家團隊，針對以下商業問題生成完整整合報告：
        商業問題: {business_question}

        報告要求：
        1. 📊 CFO 分析: 財務指標、成本效益、投資回報。
        2. 🏭 COO 分析: 營運可行性、流程與風險。
        3. 👑 CEO 最終決策: 綜合以上觀點，提供戰略總結與後續行動建議。
        """

        response = openai.ChatCompletion.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "你是高階企業分析專家。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=1500
        )

        report = response.choices[0].message.content

    # -----------------------------
    # 5️⃣ 顯示報告
    # -----------------------------
    st.success("📈 AI 專業經理人團隊整合報告完成！")
    st.markdown(report)
