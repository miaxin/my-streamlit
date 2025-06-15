import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="汽車銷售資料分析", layout="wide")
st.title("🚗 銷售資料分析儀表板")

uploaded_file = st.file_uploader("請上傳 CSV 檔案", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, encoding='utf-8', parse_dates=['Date'])
    except Exception as e:
        st.error(f"讀取檔案錯誤：{e}")
    else:
        df = df.dropna(subset=['Date', 'Price ($)'])
        df['Year'] = df['Date'].dt.year

        st.markdown("## 📊 資料總覽")
        st.write(f"總資料筆數：**{len(df):,} 筆**")
        st.write(f"欄位名稱：{list(df.columns)}")
        st.dataframe(df, use_container_width=True)  # 完整資料，支援滑動

        st.divider()
        st.markdown("## 🔍 選擇分析")

        selected_year = st.selectbox("選擇年份進行分析", sorted(df['Year'].unique(), reverse=True))
        filtered_df = df[df['Year'] == selected_year]

        analysis = st.radio(
            "請選擇分析類型",
            ("銷售趨勢圖", "品牌銷售排行", "經銷商銷售排行", "車型性別偏好", "價格分布")
        )

        if analysis == "銷售趨勢圖":
            st.markdown("### 📈 每日總銷售趨勢")
            trend = filtered_df.groupby("Date")["Price ($)"].sum()
            st.line_chart(trend)

        elif analysis == "品牌銷售排行":
            st.markdown("### 🏆 Top 10 品牌銷售額")
            top_brands = filtered_df.groupby("Company")["Price ($)"].sum().sort_values(ascending=False).head(10)
            st.bar_chart(top_brands)
            st.markdown(f"🔎 **{top_brands.idxmax()}** 銷售額最高，達 **${top_brands.max():,.0f}**")

        elif analysis == "經銷商銷售排行":
            st.markdown("### 🏪 Top 10 經銷商銷售額")
            top_dealers = filtered_df.groupby("Dealer_Name")["Price ($)"].sum().sort_values(ascending=False).head(10)
            st.bar_chart(top_dealers)
            st.markdown(f"🏬 銷售最好的經銷商為 **{top_dealers.idxmax()}**，總銷售金額為 **${top_dealers.max():,.0f}**")

        elif analysis == "車型性別偏好":
            if 'Gender' in df.columns and 'Model' in df.columns:
                st.markdown("### 👥 車型偏好分析（依性別）")
                pivot = filtered_df.pivot_table(index='Model', columns='Gender', values='Price ($)', aggfunc='sum').fillna(0)
                st.bar_chart(pivot)
                st.markdown("👫 顯示不同性別偏好的車型與消費結構。")
            else:
                st.warning("資料缺少 Gender 或 Model 欄位")

        elif analysis == "價格分布":
            st.markdown("### 💰 價格分布觀察")
            hist_df = pd.DataFrame({'Price': filtered_df['Price ($)']})
            chart = alt.Chart(hist_df).mark_bar().encode(
                alt.X("Price:Q", bin=alt.Bin(maxbins=20), title="價格區間"),
                alt.Y('count():Q', title='數量')
            ).properties(width=800, height=400)
            st.altair_chart(chart, use_container_width=True)
            st.markdown("📉 觀察各價格區間的熱門程度")

else:
    st.empty()
