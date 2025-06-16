import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="📊 財務報表視覺化分析", layout="wide")
st.title("📈 公司財務指標分析儀表板")

uploaded_file = st.file_uploader("請上傳財務報表 CSV 檔", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # 標準化欄位名稱（移除空格與括號內容）
    df.columns = df.columns.str.replace(r"（.*?）|\(.*?\)", "", regex=True).str.strip()

    # 建立欄位對應表
    mapping = {
        "年": "Year",
        "公司": "Company",
        "類別": "Category",
        "市值": "MarketCap",
        "收入": "Revenue",
        "毛利": "GrossProfit",
        "淨利": "NetIncome",
        "每股收益": "EPS",
        "每股盈餘": "EPS",
        "息稅折舊攤提前利潤": "EBITDA",
        "股東權益": "Equity",
        "本益比": "PE",
        "市銷率": "PS",
        "市淨率": "PB",
    }

    # 應用欄位對應
    df.rename(columns={k: v for k, v in mapping.items() if k in df.columns}, inplace=True)

    # 檢查關鍵欄位
    if "Year" not in df.columns or "Company" not in df.columns:
        st.error("❗ 缺少 '年' 或 '公司' 欄位，無法進行分析")
    else:
        df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
        df = df.dropna(subset=['Year'])

        st.markdown("## 🗂 資料預覽")
        st.dataframe(df)

        st.markdown("## 📊 年度趨勢圖")

        col1, col2 = st.columns(2)

        with col1:
            if 'MarketCap' in df.columns:
                cap_trend = df.groupby("Year")["MarketCap"].sum().reset_index()
                st.altair_chart(
                    alt.Chart(cap_trend).mark_line(point=True).encode(
                        x="Year:O", y="MarketCap:Q"
                    ).properties(title="📈 市值總額趨勢", width=400, height=300)
                )

            if 'Revenue' in df.columns and 'NetIncome' in df.columns:
                rev_net = df.groupby("Year")[['Revenue', 'NetIncome']].sum().reset_index()
                st.altair_chart(
                    alt.Chart(rev_net).transform_fold(
                        ['Revenue', 'NetIncome'], as_=['指標', '金額']
                    ).mark_line(point=True).encode(
                        x='Year:O', y='金額:Q', color='指標:N'
                    ).properties(title="💰 營收 vs 淨利", width=400, height=300)
                )

        with col2:
            if 'EPS' in df.columns:
                eps_trend = df.groupby("Year")["EPS"].mean().reset_index()
                st.altair_chart(
                    alt.Chart(eps_trend).mark_line(point=True).encode(
                        x="Year:O", y="EPS:Q"
                    ).properties(title="📘 每股盈餘變化", width=400, height=300)
                )

            if 'GrossProfit' in df.columns and 'Revenue' in df.columns:
                df['GrossMargin'] = df['GrossProfit'] / df['Revenue']
                margin = df.groupby("Year")["GrossMargin"].mean().reset_index()
                st.altair_chart(
                    alt.Chart(margin).mark_line(point=True).encode(
                        x="Year:O", y=alt.Y("GrossMargin:Q", axis=alt.Axis(format='%'))
                    ).properties(title="📊 毛利率變化", width=400, height=300)
                )

        st.markdown("## 🏆 公司排名")

        metric = st.selectbox("選擇財務指標排行", ['MarketCap', 'Revenue', 'NetIncome', 'EPS'], index=0)
        if metric in df.columns:
            latest_year = int(df['Year'].max())
            top_df = df[df['Year'] == latest_year].nlargest(10, metric)
            st.altair_chart(
                alt.Chart(top_df).mark_bar().encode(
                    x=alt.X(f"{metric}:Q", title=metric),
                    y=alt.Y("Company:N", sort='-x')
                ).properties(title=f"{latest_year} 年 Top 10 公司（{metric}）", width=700)
            )
        else:
            st.warning(f"無法找到欄位：{metric}")

        st.markdown("## 🏭 不同產業指標分佈")

        if "Category" in df.columns:
            cat_metric = st.selectbox("選擇要比較的指標", ['MarketCap', 'Revenue', 'NetIncome', 'EPS'])
            if cat_metric in df.columns:
                box = alt.Chart(df).mark_boxplot(extent='min-max').encode(
                    x="Category:N", y=cat_metric
                ).properties(width=800, height=400)
                st.altair_chart(box)

else:
    st.info("請上傳包含公司財務資料的 CSV 檔案")
