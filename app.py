# app.py
import streamlit as st
import pandas as pd

st.set_page_config(page_title="CSV 上傳與顯示", layout="wide")

st.title("📁 公開資料集 CSV 上傳與顯示")

# 上傳檔案
uploaded_file = st.file_uploader("請上傳 CSV 檔案", type=["csv"])

if uploaded_file is not None:
    try:
        # 嘗試自動偵測編碼（Big5 / UTF-8）
        try:
            df = pd.read_csv(uploaded_file, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(uploaded_file, encoding='big5')

        st.success("✅ 檔案上傳成功，總共 %d 筆資料。" % len(df))

        # 顯示欄位選單
        sort_col = st.selectbox("選擇要排序的欄位", df.columns)
        sort_order = st.radio("排序方式", ["升冪", "降冪"], horizontal=True)

        # 排序後的表格
        df_sorted = df.sort_values(by=sort_col, ascending=(sort_order == "升冪"))

        st.dataframe(df_sorted, use_container_width=True)

    except Exception as e:
        st.error(f"❌ 檔案處理失敗：{e}")
else:
    st.info("請先上傳 .csv 檔案以繼續。")
