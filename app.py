import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px

st.set_page_config(page_title="CSV 財務資料分析", layout="wide")
st.title("📊 自動化資料分析平台")
st.markdown("上傳一個 `csv` 檔案，系統會自動呈現資料分析。")

# 上傳 CSV
uploaded_file = st.file_uploader("請上傳你的 CSV 檔案", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    st.subheader("🔍 資料預覽")
    st.dataframe(df)

    # 數值欄位
    numeric_columns = df.select_dtypes(include=["float64", "int64"]).columns.tolist()

    # 基本統計
    st.subheader("📊 敘述統計")
    st.dataframe(df[numeric_columns].describe())

    # 相關性熱圖
    if len(numeric_columns) >= 2:
        st.subheader("📌 數值欄位相關性熱圖")
        corr = df[numeric_columns].corr()
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.heatmap(corr, annot=True, cmap="coolwarm", ax=ax)
        st.pyplot(fig)

    # 自動生成圖表（前 3 個欄位為例）
    st.subheader("📈 散佈圖視覺化（前三組欄位）")
    for i in range(min(3, len(numeric_columns)-1)):
        fig = px.scatter(df, x=numeric_columns[i], y=numeric_columns[i+1],
                         title=f"{numeric_columns[i]} vs {numeric_columns[i+1]}")
        st.plotly_chart(fig, use_container_width=True)

    # 長條圖（單欄位分佈）
    st.subheader("📊 數值欄位分佈（直方圖）")
    for col in numeric_columns[:3]:
        fig = px.histogram(df, x=col, nbins=30, title=f"{col} 分佈")
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("📁 請上傳一個 CSV 檔案以開始分析。")
