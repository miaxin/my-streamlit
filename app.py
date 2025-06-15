import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="汽車銷售分析儀表板", layout="wide")
st.title("🚗 銷售資料分析儀表板")

uploaded_file = st.file_uploader("請上傳汽車銷售 CSV 檔案", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, encoding='utf-8')

        st.markdown("## 🔍 欄位對應")
        # 自動偵測欄位或讓使用者指定
        date_col = st.selectbox("選擇日期欄位", df.columns, index=0)
        price_col = st.selectbox("選擇價格欄位", df.columns, index=df.columns.get_loc("Price ($)") if "Price ($)" in df.columns else 0)

        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col, price_col])
        df['Year'] = df[date_col].dt.year

        st.markdown("## 📄 資料預覽（可滑動）")
        st.dataframe(df, use_container_width=True)

        selected_year = st.selectbox("📅 選擇年份篩選", sorted(df['Year'].dropna().unique(), reverse=True))
        filtered_df = df[df['Year'] == selected_year]

        # KPI 區塊
        col1, col2, col3 = st.columns(3)
        col1.metric("平均單價", f"${filtered_df[price_col].mean():,.0f}")
        col2.metric("最高單價", f"${filtered_df[price_col].max():,.0f}")
        top_brand = filtered_df['Company'].value_counts().idxmax() if 'Company' in df.columns else '未知'
        col3.metric("銷售最佳品牌", top_brand)

        st.markdown("### 📈 銷售趨勢圖")
        trend = filtered_df.groupby(date_col)[price_col].sum()
        st.line_chart(trend)

        if 'Company' in df.columns:
            st.markdown("### 🏆 Top 10 品牌銷售")
            brand_sales = filtered_df.groupby('Company')[price_col].sum().sort_values(ascending=False).head(10)
            st.bar_chart(brand_sales)

        if 'Dealer_Name' in df.columns:
            st.markdown("### 🏪 Top 10 經銷商")
            dealer_sales = filtered_df.groupby('Dealer_Name')[price_col].sum().sort_values(ascending=False).head(10)
            st.bar_chart(dealer_sales)

        if 'Model' in df.columns and 'Gender' in df.columns:
            st.markdown("### 👤 性別 vs 車型 銷售分析")
            pivot = filtered_df.pivot_table(index='Model', columns='Gender', values=price_col, aggfunc='sum').fillna(0)
            st.bar_chart(pivot)

        st.markdown("### 💰 價格分布")
        st.bar_chart(filtered_df[price_col].value_counts(bins=20).sort_index())

        # 匯出按鈕
        st.markdown("### ⬇️ 下載目前篩選的資料")
        def to_excel(dataframe):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                dataframe.to_excel(writer, index=False, sheet_name='分析資料')
            return output.getvalue()

        excel_data = to_excel(filtered_df)
        st.download_button(
            label="下載 Excel 報告",
            data=excel_data,
            file_name=f"sales_analysis_{selected_year}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"❌ 錯誤：{e}")
else:
    st.info("請上傳含有日期與價格等欄位的 CSV 檔案。")
