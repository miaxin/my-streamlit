# app.py 或 pages/2_整合式分析.py
import streamlit as st
import openai

st.set_page_config(page_title="📈 AI 專業經理人整合分析", layout="wide")
st.title("📈 AI 專業經理人團隊整合分析")
st.markdown("模擬 CFO、COO、CEO 三位專家生成完整報告")

# ------------------------------
# API Key 檢查（首頁輸入共用）
# ------------------------------
if "GOOGLE_API_KEY" not in st.session_state:
    st.session_state["GOOGLE_API_KEY"] = ""

st.sidebar.subheader("🔑 API Key 設定")
st.session_state["GOOGLE_API_KEY"] = st.sidebar.text_input(
    "請輸入您的 OpenAI API Key",
    type="password",
    value=st.session_state["GOOGLE_API_KEY"]
)

api_key = st.session_state.get("GOOGLE_API_KEY", "")
if not api_key:
    st.warning("⚠️ 請先在左側輸入 API Key 以使用本頁功能")
    st.stop()
else:
    st.sidebar.success("✅ API Key 已輸入")

openai.api_key = api_key

# ------------------------------
# 使用者輸入商業問題
# ------------------------------
business_question = st.text_area(
    "請輸入您的商業問題或分析需求",
    placeholder="例如：請分析新產品的投資回報與營運風險..."
)

mode = st.radio(
    "選擇分析模式",
    ["一次性整合分析 (Single API Call)", "分段式分析 (Step-by-Step)"]
)

# ------------------------------
# 一次請求模式
# ------------------------------
def single_call_analysis(question):
    prompt = f"""
    模擬一個由 CFO、COO、CEO 組成的專家團隊，針對以下商業問題生成完整整合報告：
    商業問題: {question}

    報告要求：
    1. 📊 CFO 分析: 財務指標、成本效益、投資回報。
    2. 🏭 COO 分析: 營運可行性、流程與風險。
    3. 👑 CEO 最終決策: 綜合以上觀點，提供戰略總結與後續行動建議。
    """

    response = openai.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": "你是高階企業分析專家。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
        max_tokens=2000
    )
    report = response.choices[0].message.content
    return report

# ------------------------------
# 分段式分析模式
# ------------------------------
def step_by_step_analysis(question):
    reports = {}

    # CFO
    st.info("📊 CFO 正在獨立分析...")
    cfo_prompt = f"請作為 CFO，分析以下商業問題的財務面：{question}"
    cfo_resp = openai.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": "你是財務長 (CFO)。"},
            {"role": "user", "content": cfo_prompt}
        ],
        temperature=0.5,
        max_tokens=1000
    )
    reports['CFO'] = cfo_resp.choices[0].message.content
    st.success("📊 CFO 分析完成！")
    st.markdown(reports['CFO'])

    # COO
    st.info("🏭 COO 正在分析...")
    coo_prompt = f"請作為 COO，分析以下商業問題的營運可行性及流程風險，並參考 CFO 的報告：{reports['CFO']}"
    coo_resp = openai.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": "你是營運長 (COO)。"},
            {"role": "user", "content": coo_prompt}
        ],
        temperature=0.5,
        max_tokens=1000
    )
    reports['COO'] = coo_resp.choices[0].message.content
    st.success("🏭 COO 分析完成！")
    st.markdown(reports['COO'])

    # CEO
    st.info("👑 CEO 正在總結...")
    ceo_prompt = f"請作為 CEO，基於 CFO 與 COO 的報告，對商業問題提供戰略總結及後續行動建議：CFO報告:{reports['CFO']} COO報告:{reports['COO']}"
    ceo_resp = openai.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": "你是執行長 (CEO)。"},
            {"role": "user", "content": ceo_prompt}
        ],
        temperature=0.5,
        max_tokens=1000
    )
    reports['CEO'] = ceo_resp.choices[0].message.content
    st.success("👑 CEO 總結完成！")
    st.markdown(reports['CEO'])

    return reports

# ------------------------------
# 按鈕觸發
# ------------------------------
if st.button("生成分析報告") and business_question.strip():
    with st.spinner("AI 專業經理人團隊正在分析中..."):
        if mode == "一次性整合分析 (Single API Call)":
            final_report = single_call_analysis(business_question)
            st.success("📈 AI 專業經理人團隊整合報告完成！")
            st.markdown(final_report)
        else:
            step_by_step_analysis(business_question)
