import streamlit as st
import pandas as pd
import altair as alt

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
    df['ROI'] = df['ROA']
    df['DebtEquityRatio'] = df[debt_col] / df[equity_col]
    df['CurrentRatio'] = df[current_assets_col] / df[current_liabilities_col]
    df['GrossMargin'] = df[gross_profit_col] / df[revenue_col]
    df['OperatingMargin'] = df[net_income_col] / df[revenue_col]
    if eps_col is not None:
        df['EPS'] = df[eps_col]

    return df, net_income_col, revenue_col, eps_col

def main():
    st.title("上市公司財務資料自動分析")

    uploaded_file = st.file_uploader("請上傳財務資料 CSV 檔", type=['csv'])
    if uploaded_file is None:
        st.info("請先上傳 CSV 檔")
        return

    df = pd.read_csv(uploaded_file)
    st.write("資料欄位清單：", df.columns.tolist())

    company_col = st.selectbox("選擇公司欄位", df.columns)
    year_col = st.selectbox("選擇年度欄位", df.columns)

    df, net_income_col, revenue_col, eps_col = calc_ratios(df)

    # 總覽：公司數量、行業（如果有）、營收淨利總趨勢
    st.subheader("公司與年度總覽")
    st.write(f"共 {df[company_col].nunique()} 家公司，{df[year_col].nunique()} 年度資料。")

    # 全公司年度營收與淨利總和趨勢
    df_yearly = df.groupby(year_col).agg(
        TotalRevenue = (revenue_col, 'sum'),
        TotalNetIncome = (net_income_col, 'sum')
    ).reset_index()

    base = alt.Chart(df_yearly).encode(x=year_col)

    rev_line = base.mark_line(color='blue').encode(y='TotalRevenue', tooltip=[year_col, 'TotalRevenue'])
    net_line = base.mark_line(color='red').encode(y='TotalNetIncome', tooltip=[year_col, 'TotalNetIncome'])

    st.altair_chart((rev_line + net_line).properties(width=700, height=400, title="全體年度營收（藍）與淨利（紅）總和趨勢"))

    # 每家公司折線圖（市值、營收、淨利、EPS）
    st.subheader("各公司年度財務趨勢")

    marketcap_col = find_column(df, ['market', 'cap'])

    for company in df[company_col].unique():
        st.markdown(f"### 公司：{company}")
        df_c = df[df[company_col] == company].sort_values(year_col)

        base = alt.Chart(df_c).encode(x=year_col)

        charts = []
        for col, label, color in [
            (marketcap_col, '市值', 'orange'),
            (revenue_col, '營收', 'blue'),
            (net_income_col, '淨利', 'red'),
            (eps_col, 'EPS', 'green')
        ]:
            if col and col in df_c.columns:
                line = base.mark_line(point=True, color=color).encode(
                    y=alt.Y(col, title=label),
                    tooltip=[year_col, col]
                ).properties(width=600, height=300, title=f"{label} 年度趨勢")
                st.altair_chart(line)

    # 最新年度雷達圖（全部公司）
    st.subheader("最新年度各公司財務比率雷達圖（堆疊展示）")
    latest_year = df[year_col].max()
    df_latest = df[df[year_col] == latest_year]

    radar_data = []
    ratio_cols = ['NetProfitMargin', 'ROE', 'ROA', 'DebtEquityRatio', 'CurrentRatio', 'GrossMargin', 'OperatingMargin']

    for idx, row in df_latest.iterrows():
        for ratio in ratio_cols:
            radar_data.append({
                '公司': row[company_col],
                '比率': ratio,
                '數值': row[ratio]
            })

    radar_df = pd.DataFrame(radar_data)

    radar_chart = alt.Chart(radar_df).mark_line(point=True).encode(
        theta=alt.Theta("比率:N", sort=None),
        radius=alt.Radius("數值:Q", scale=alt.Scale(type="linear", zero=True)),
        color=alt.Color("公司:N")
    ).properties(width=600, height=600, title=f"{latest_year} 年度公司財務比率雷達圖")

    st.altair_chart(radar_chart)

if __name__ == "__main__":
    main()
