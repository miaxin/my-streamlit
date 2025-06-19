import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="公司財報視覺化", layout="wide")
st.title("🏦 公司財務分析平台")
st.markdown("上傳一份財務報表 CSV，系統將自動進行商業圖表分析")

uploaded_file = st.file_uploader("📤 上傳 CSV 檔案", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip()

    st.subheader("🧾 資料預覽")
    st.dataframe(df.head(10))

    # 基本財務卡片
    st.subheader("📌 財務總覽卡片")
    sample = df.dropna(subset=["Balance sheet total", "Debt", "Market Capitalization"])
    company = sample.iloc[0]  # 取第一家公司為例

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("資產總額", f"{company['Balance sheet total']:,.0f}")
    col2.metric("負債總額", f"{company['Debt']:,.0f}")
    col3.metric("淨值（資產-負債）", f"{company['Balance sheet total'] - company['Debt']:,.0f}")
    col4.metric("市值", f"{company['Market Capitalization']:,.0f}")

    # 圓餅圖：資產結構
    st.subheader("🥧 資產結構（固定資產、流動資產、投資）")
    if set(['Net block', 'Current assets', 'Investments']).issubset(df.columns):
        pie_data = company[['Net block', 'Current assets', 'Investments']]
        fig = px.pie(values=pie_data.values,
                     names=pie_data.index,
                     title=f"{company['Name']} 資產結構")
        st.plotly_chart(fig, use_container_width=True)

    # 長條圖：各產業市值比較
    st.subheader("🏭 各產業市值分佈")
    if 'Industry' in df.columns:
        industry_market = df.groupby('Industry', as_index=False)['Market Capitalization'].sum()
        fig = px.bar(industry_market.sort_values('Market Capitalization', ascending=False),
                     x="Industry", y="Market Capitalization",
                     title="各產業總市值", labels={"Market Capitalization": "市值"})
        st.plotly_chart(fig, use_container_width=True)

    # 散佈圖：負債與營運資金比較
    st.subheader("📉 負債與營運資金散佈圖")
    if set(['Debt', 'Working capital']).issubset(df.columns):
        fig = px.scatter(df,
                         x="Debt", y="Working capital",
                         hover_name="Name",
                         title="負債 vs 營運資金")
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("⬆️ 請上傳包含財務欄位的 CSV 檔案以開始分析。")
