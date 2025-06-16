import streamlit as st
import pandas as pd
import altair as alt

# 自動找欄位名稱函式（關鍵字模糊匹配）
def find_column(df, keywords):
    cols = df.columns.str.lower()
    for col in df.columns:
        low_col = col.lower()
        if all(k in low_col for k in keywords):
            return col
    for col in df.columns:
        low_col = col.lower()
        if any(k in low_col for k in keywords):
            return col
    return None

# 計算財務比率
def calc_ratios(df):
    net_income_col = find_column(df, ['net', 'income'])
    revenue_col = find_column(df, ['revenue'])
    gross_profit_col = find_column(df, ['gross', 'profit'])
    equity_col = find_column(df, ['equity'])
    debt_col = find_column(df, ['debt'])
    current_assets_col = find_column(df, ['current', 'asset'])
    current_liabilities_col = find_column(df, ['current', 'liabilit'])
    eps_col = find_column(df, ['eps'])

    missing_cols = [col is None for col in [net_income_col, revenue_col, gross_profit_col, equity_col, debt_col, current_assets_col, current_liabilities_col]]
    if any(missing_cols):
        st.error("找不到部分必要欄位，請確認資料欄位名稱")
        st.write("目前欄位:", df.columns.tolist())
        st.stop()

    df['NetProfitMargin'] = df[net_income_col] / df[revenue_col]
    df['ROE'] = df[net_income_col] / df[equity_col]
    df['ROA'] = df[net_income_col] / (df[equity_col] + df[debt_col])
    df['ROI'] = df['ROA']  # 若有更好的投資報酬率欄位，可改寫
    df['DebtEquityRatio'] = df[debt_col] / df[equity_col]
    df['CurrentRatio'] = df[current_assets_col] / df[current_liabilities_col]
    df['GrossMargin'] = df[gross_profit_col] / df[revenue_col]
    df['OperatingMargin'] = df[net_income_col] / df[revenue_col]
    if eps_col is not None:
        df['EPS'] = df[eps_col]

    return df

# 主程式
def main():
    st.title("上市公司財務資料分析與視覺化")

    uploaded_file = st.file_uploader("請上傳財務資料 CSV 檔", type=['csv'])
    if uploaded_file is None:
        st.info("請先上傳包含財務欄位的 CSV 檔案")
        return

    df = pd.read_csv(uploaded_file)
    st.write("資料欄位清單：", df.columns.tolist())

    # 計算財務比率
    df = calc_ratios(df)

    # 讓使用者選公司及年度欄位名稱
    company_col = st.selectbox("選擇公司欄位", df.columns)
    year_col = st.selectbox("選擇年度欄位", df.columns)

    selected_company = st.selectbox("選擇要分析的公司", df[company_col].unique())

    # 篩選該公司資料
    df_company = df[df[company_col] == selected_company]

    # 年度排序
    df_company = df_company.sort_values(by=year_col)

    st.subheader(f"{selected_company} 財務趨勢")

    # 畫圖範例：市值、市營收、淨利、EPS 折線圖（有欄位才畫）
    base = alt.Chart(df_company).encode(x=year_col)

    charts = []

    for col, label in [('MarketCap', '市值'), ('Revenue', '營收'), ('NetIncome', '淨利'), ('EPS', '每股盈餘')]:
        col_real = find_column(df_company, [c.lower() for c in col.split()])
        if col_real and col_real in df_company.columns:
            line = base.mark_line(point=True).encode(
                y=alt.Y(col_real, title=label)
            ).properties(width=600, height=300, title=f"{label} 年度趨勢")
            st.altair_chart(line)
            charts.append(line)

    # 財務比率雷達圖(用 Altair 近似)
    st.subheader(f"{selected_company} 財務比率（最新年度）")
    latest_year = df_company[year_col].max()
    df_latest = df_company[df_company[year_col] == latest_year]

    radar_data = {
        '項目': ['淨利率', 'ROE', 'ROA', '負債比', '流動比率', '毛利率', '營業利益率'],
        '數值': [
            df_latest['NetProfitMargin'].values[0],
            df_latest['ROE'].values[0],
            df_latest['ROA'].values[0],
            df_latest['DebtEquityRatio'].values[0],
            df_latest['CurrentRatio'].values[0],
            df_latest['GrossMargin'].values[0],
            df_latest['OperatingMargin'].values[0]
        ]
    }

    radar_df = pd.DataFrame(radar_data)

    radar_chart = alt.Chart(radar_df).mark_line(point=True).encode(
        theta=alt.Theta("項目:N", sort=None),
        radius=alt.Radius("數值:Q", scale=alt.Scale(type="linear", zero=True, domain=(0, radar_df['數值'].max()*1.2))),
        color=alt.value("steelblue")
    ).properties(width=400, height=400, title=f"{selected_company} {latest_year} 財務比率雷達圖")

    st.altair_chart(radar_chart)

if __name__ == "__main__":
    main()
