import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import io

# --- 頁面配置 ---
st.set_page_config(page_title="財務分析儀表板", layout="wide")
st.title("📊 企業財務洞察平台")
st.markdown("---")

# --- 側邊欄 API Key 設定 ---
st.sidebar.subheader("🔑 Gemini API 設定")
api_key = st.sidebar.text_input("輸入 Gemini API Key", type="password")
if api_key:
    st.session_state["GOOGLE_API_KEY"] = api_key
if "GOOGLE_API_KEY" not in st.session_state:
    st.warning("⚠️ 請在左側欄輸入 API Key 以繼續使用系統。")

# --- 側邊欄 CSV 上傳 ---
st.sidebar.subheader("📂 上傳財務報表 CSV")
uploaded_file = st.sidebar.file_uploader("選擇 CSV 檔案", type=["csv"])

# --- 數值轉換函數（避免讀取錯誤） ---
@st.cache_data
def convert_df_to_numeric(df):
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="ignore")
    return df

# --- CSV 上傳與處理 ---
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df = convert_df_to_numeric(df)

    # 若缺少公司名稱欄位，則自動補上
    if "公司名稱" not in df.columns:
        df.insert(0, "公司名稱", [f"公司{i+1}" for i in range(len(df))])

    st.session_state["df"] = df
    st.success("✅ 檔案上傳成功！")

# --- 確認 DataFrame 已存在 ---
if "df" in st.session_state:
    df = st.session_state["df"]

    # --- 可視化功能選單 ---
    st.sidebar.subheader("📊 選擇要顯示的圖表")

    chart_requirements = {
        "產業市值前N名": ["公司名稱", "Market Cap"],
        "年度營收趨勢": ["Year", "Revenue"],
        "年度淨利潤趨勢": ["Year", "Net Profit"],
        "EPS 趨勢": ["Year", "EPS"],
        "ROE / ROCE 比較": ["Year", "ROE", "ROCE"],
        "自由現金流分析": ["Year", "Free Cash Flow"],
        "股價表現": ["Year", "Stock Price"]
    }

    available_charts = [chart for chart, req_cols in chart_requirements.items() if all(col in df.columns for col in req_cols)]
    selected_charts = st.sidebar.multiselect("選擇要顯示的圖表", available_charts, default=available_charts)

    st.markdown("### 📈 自動生成圖表")

    # --- Top N 控制 ---
    if "產業市值前N名" in selected_charts:
        top_n = st.slider("選擇要顯示的前 N 名 (依市值排序)", 3, 20, 8)
        fig = px.bar(df.nlargest(top_n, "Market Cap"), x="公司名稱", y="Market Cap", title=f"產業市值前 {top_n} 名")
        st.plotly_chart(fig, use_container_width=True)

    # --- 年度營收趨勢 ---
    if "年度營收趨勢" in selected_charts:
        fig = px.line(df, x="Year", y="Revenue", color="公司名稱", title="年度營收趨勢")
        st.plotly_chart(fig, use_container_width=True)

    # --- 年度淨利潤趨勢 ---
    if "年度淨利潤趨勢" in selected_charts:
        fig = px.line(df, x="Year", y="Net Profit", color="公司名稱", title="年度淨利潤趨勢")
        st.plotly_chart(fig, use_container_width=True)

    # --- EPS 趨勢 ---
    if "EPS 趨勢" in selected_charts:
        fig = px.line(df, x="Year", y="EPS", color="公司名稱", title="EPS 趨勢")
        st.plotly_chart(fig, use_container_width=True)

    # --- ROE / ROCE 比較 ---
    if "ROE / ROCE 比較" in selected_charts:
        melted = df.melt(id_vars=["Year", "公司名稱"], value_vars=["ROE", "ROCE"], var_name="指標", value_name="數值")
        fig = px.line(melted, x="Year", y="數值", color="指標", facet_col="公司名稱", title="ROE vs ROCE")
        st.plotly_chart(fig, use_container_width=True)

    # --- 自由現金流分析 ---
    if "自由現金流分析" in selected_charts:
        fig = px.bar(df, x="Year", y="Free Cash Flow", color="公司名稱", title="自由現金流分析")
        st.plotly_chart(fig, use_container_width=True)

    # --- 股價表現 ---
    if "股價表現" in selected_charts:
        fig = px.line(df, x="Year", y="Stock Price", color="公司名稱", title="股價表現")
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("📂 請先在左側上傳 CSV 檔案後開始分析")
