import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="財務報表分析儀表板", layout="wide")
st.title("📈 財務報表視覺化分析平台")
st.markdown("上傳一個 `csv` 財報資料，進行自動化視覺分析。")

uploaded_file = st.file_uploader("📤 請上傳 CSV 財務報表", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    st.subheader("🔍 原始資料預覽")
    st.dataframe(df)

    st.subheader("📌 基本財務指標卡片")
    col1, col2, col3, col4 = st.columns(4)
    if "總資產" in df.columns:
        col1.metric("總資產", f"{df['總資產'].iloc[-1]:,.0f}")
    if "總負債" in df.columns:
        col2.metric("總負債", f"{df['總負債'].iloc[-1]:,.0f}")
    if "股東權益" in df.columns:
        col3.metric("股東權益", f"{df['股東權益'].iloc[-1]:,.0f}")
    if "營業收入" in df.columns:
        col4.metric("營業收入", f"{df['營業收入'].iloc[-1]:,.0f}")

    st.subheader("📊 資產結構分析（圓餅圖）")
    asset_cols = [col for col in df.columns if "資產" in col and col != "總資產"]
    if len(asset_cols) > 1:
        asset_data = df[asset_cols].iloc[-1]
        fig = px.pie(values=asset_data.values, names=asset_data.index, title="資產結構")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📊 負債結構分析（圓餅圖）")
    debt_cols = [col for col in df.columns if "負債" in col and col != "總負債"]
    if len(debt_cols) > 1:
        debt_data = df[debt_cols].iloc[-1]
        fig = px.pie(values=debt_data.values, names=debt_data.index, title="負債結構")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📈 資產與負債變化趨勢圖")
    if "年度" in df.columns and "總資產" in df.columns and "總負債" in df.columns:
        fig = px.line(df, x="年度", y=["總資產", "總負債", "股東權益"],
                      markers=True, title="年度資產與負債趨勢")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📉 財務比率分析（長條圖）")
    if "總資產" in df.columns and "總負債" in df.columns:
        df["負債比率"] = df["總負債"] / df["總資產"] * 100
        fig = px.bar(df, x="年度", y="負債比率", title="年度負債比率 (%)")
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("⬆️ 請先上傳你的財務資料 CSV 檔案。")
