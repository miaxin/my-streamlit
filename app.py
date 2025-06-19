import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="財務分析儀表板", layout="wide")
st.title("📊 財務分析儀表板")
st.markdown("上傳一份財務 CSV，並選擇你想看的圖表分析類型")

uploaded_file = st.file_uploader("📤 上傳 CSV 檔案", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip()

    # 做好財務比率欄位（可被多個圖表使用）
    if "Balance sheet total" in df.columns and "Debt" in df.columns:
        df["負債比率 (%)"] = df["Debt"] / df["Balance sheet total"] * 100
    if "Current assets" in df.columns and "Current liabilities" in df.columns:
        df["流動比率"] = df["Current assets"] / df["Current liabilities"]
    if "Balance sheet total" in df.columns and "Debt" in df.columns:
        df["Equity"] = df["Balance sheet total"] - df["Debt"]

    # 分析圖表選單
    chart_option = st.selectbox("🔽 請選擇你要顯示的分析圖：", [
        "產業市值長條圖（前 8 名 + 其他）",
        "資產結構圓餅圖（單一公司）",
        "負債 vs 營運資金（散佈圖）",
        "財務比率表格"
    ])

    # -- 圖表 1: 產業市值長條圖 --
    if chart_option == "產業市值長條圖（前 8 名 + 其他）":
        st.subheader("🏭 各產業市值分佈（前 8 名 + 其他）")
        top_n = 8
        df_valid = df.dropna(subset=["Industry", "Market Capitalization"])
        industry_market = df_valid.groupby("Industry", as_index=False)["Market Capitalization"].sum()
        industry_market = industry_market.sort_values("Market Capitalization", ascending=False)

        top_industries = industry_market.head(top_n)
        other_sum = industry_market.iloc[top_n:]["Market Capitalization"].sum()
        top_industries = pd.concat([
            top_industries,
            pd.DataFrame([{"Industry": "其他", "Market Capitalization": other_sum}])
        ])

        fig = px.bar(top_industries,
                     x="Industry", y="Market Capitalization",
                     title="前 8 名產業市值 + 其他",
                     text_auto=True)
        st.plotly_chart(fig, use_container_width=True)

    # -- 圖表 2: 資產結構圓餅圖 --
    elif chart_option == "資產結構圓餅圖（單一公司）":
        st.subheader("🏢 選擇公司查看資產結構")
        company_list = df["Name"].dropna().unique().tolist()
        selected_company = st.selectbox("請選擇公司", sorted(company_list))
        company_data = df[df["Name"] == selected_company].iloc[0]

        if {"Net block", "Current assets", "Investments"}.issubset(df.columns):
            pie_data = company_data[["Net block", "Current assets", "Investments"]]
            fig = px.pie(values=pie_data.values,
                         names=pie_data.index,
                         title=f"{selected_company} 的資產結構")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("缺少資產結構欄位，無法畫出圖表。")

    # -- 圖表 3: 散佈圖 --
    elif chart_option == "負債 vs 營運資金（散佈圖）":
        st.subheader("📉 散佈圖：負債 vs 營運資金")
        if "Debt" in df.columns and "Working capital" in df.columns:
            fig = px.scatter(df,
                             x="Debt", y="Working capital",
                             hover_name="Name",
                             title="負債與營運資金的關係")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("缺少欄位：Debt 或 Working capital")

    # -- 圖表 4: 財務比率表格 --
    elif chart_option == "財務比率表格":
        st.subheader("📋 財務比率表格")
        ratio_cols = ["Name", "負債比率 (%)", "流動比率", "Equity", "Balance sheet total"]
        available_cols = [col for col in ratio_cols if col in df.columns]
        if len(available_cols) >= 2:
            st.dataframe(df[available_cols].round(2))
        else:
            st.warning("缺少必要欄位，無法呈現財務比率。")

else:
    st.info("請上傳一個財務資料 CSV 檔案以開始分析。")
