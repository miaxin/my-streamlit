import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np # 用於處理可能的NaN值

st.set_page_config(page_title="財務分析儀表板", layout="wide")
st.title("📊 財務分析儀表板")
st.markdown("上傳一份包含多公司財務數據的 CSV 檔案，系統將自動偵測欄位並提供對應圖表分析。")
st.markdown("---")

uploaded_file = st.file_uploader("📤 上傳 CSV 檔案", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        # 清除欄位名稱的空白符
        df.columns = df.columns.str.strip()

        st.success("CSV 檔案上傳成功！正在處理數據...")

        # ----------------------------------------------------
        # 數據預處理與新增計算欄位
        # ----------------------------------------------------

        # 確保必要的名稱欄位存在
        if 'Name' not in df.columns and 'name' in df.columns:
            df.rename(columns={'name': 'Name'}, inplace=True)
        if 'Name' not in df.columns:
            st.error("CSV 檔案中缺少 'Name' (或 'name') 欄位，無法進行公司層級分析。請確保數據包含公司名稱。")
            st.stop()
        
        # 將部分常用數值欄位轉換為數字類型，錯誤值設為 NaN
        numeric_cols = [
            'Market Capitalization', 'Sales', 'Profit after tax', 'EPS', 'Debt', 'Balance sheet total',
            'Current assets', 'Current liabilities', 'Net block', 'Investments',
            'Sales last year', 'Profit after tax last year', 'EPS last year',
            'Sales preceding year', 'Profit after tax preceding year', 'EPS preceding year',
            'Return on equity', 'Return on capital employed', 'Price to Earning',
            'Equity capital', 'Reserves', 'Preference capital',
            'Cash from operations last year', 'Cash from investing last year', 'Cash from financing last year',
            'Free cash flow last year', 'Sales growth 3Years', 'Profit growth 3Years'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 預先計算可能用到的欄位
        if "Balance sheet total" in df.columns and "Debt" in df.columns:
            df["負債比率 (%)"] = df["Debt"] / df["Balance sheet total"] * 100
        
        if "Balance sheet total" in df.columns and "Debt" in df.columns:
            # 這裡假定 Equity = Balance sheet total - Debt (簡化處理，實際可能更複雜)
            df["Equity"] = df["Balance sheet total"] - df["Debt"] 
            
        if "Current assets" in df.columns and "Current liabilities" in df.columns:
            df["流動比率"] = df["Current assets"] / df["Current liabilities"]

        if 'Debt' in df.columns and 'Equity capital' in df.columns:
            df['Debt to Equity Ratio'] = df['Debt'] / df['Equity capital']
            df['Debt to Equity Ratio'].replace([np.inf, -np.inf], np.nan, inplace=True) # 處理除以零或無限大的情況

        # ----------------------------------------------------
        # 定義圖表需求 (基於欄位存在性)
        # ----------------------------------------------------
        chart_requirements = {
            "產業市值長條圖（前 8 名 + 其他）": {"Industry", "Market Capitalization"},
            "資產結構圓餅圖（單一公司）": {"Name", "Net block", "Current assets", "Investments"},
            "負債 vs 營運資金（散佈圖）": {"Debt", "Working capital", "Name"},
            "財務比率表格": {"負債比率 (%)", "流動比率", "Equity", "Balance sheet total", "Name"},
            "各年度營收趨勢圖（單一公司）": {"Name", "Sales", "Sales last year", "Sales preceding year"},
            "各年度淨利潤趨勢圖（單一公司）": {"Name", "Profit after tax", "Profit after tax last year", "Profit after tax preceding year"},
            "各年度EPS趨勢圖（單一公司）": {"Name", "EPS", "EPS last year", "EPS preceding year"},
            "ROE與ROCE趨勢圖（單一公司）": {"Name", "Return on equity", "Return on capital employed"}, # 假設這裡的ROE/ROCE是當前值，如果有多個年度需要調整數據結構
            "本益比與股東權益報酬率散佈圖": {"Price to Earning", "Return on equity", "Name"},
            "銷售額成長率排名（前20）": {"Name", "Sales growth 3Years"},
            "利潤成長率排名（前20）": {"Name", "Profit growth 3Years"},
            "負債權益比率長條圖（前20）": {"Name", "Debt to Equity Ratio"},
            "現金流量概覽圓餅圖（單一公司，最近一年）": {"Name", "Cash from operations last year", "Cash from investing last year", "Cash from financing last year"},
            "自由現金流趨勢圖（單一公司）": {"Name", "Free cash flow last year"},
        }

        # 只挑出能畫的圖
        available_charts = [
            chart for chart, required_cols in chart_requirements.items()
            if required_cols.issubset(df.columns)
        ]

        if available_charts:
            st.sidebar.header("📊 圖表選擇")
            chart_option = st.sidebar.selectbox("🔽 根據資料欄位選擇分析圖表：", available_charts)

            # ----------------------------------------------------
            # 圖表繪製區
            # ----------------------------------------------------

            if chart_option == "產業市值長條圖（前 8 名 + 其他）":
                st.subheader("🏭 各產業市值分佈")
                df_valid = df.dropna(subset=["Industry", "Market Capitalization"])
                if not df_valid.empty:
                    industry_market = df_valid.groupby("Industry", as_index=False)["Market Capitalization"].sum()
                    industry_market = industry_market.sort_values("Market Capitalization", ascending=False)

                    top_n = 8
                    top_industries = industry_market.head(top_n)
                    other_sum = industry_market.iloc[top_n:]["Market Capitalization"].sum()
                    
                    # 避免 '其他' 為 NaN 導致圖表問題
                    if other_sum > 0:
                        top_industries = pd.concat([
                            top_industries,
                            pd.DataFrame([{"Industry": "其他", "Market Capitalization": other_sum}])
                        ])
                    
                    fig = px.bar(top_industries,
                                 x="Industry", y="Market Capitalization",
                                 title="前 8 名產業市值 + 其他",
                                 text_auto=True,
                                 labels={"Market Capitalization": "市值 (單位)"}) # 添加單位，需根據實際數據填寫
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("沒有足夠的『產業』和『市值』數據來繪製此圖。")

            elif chart_option == "資產結構圓餅圖（單一公司）":
                st.subheader("🏢 公司資產結構")
                company_list = df["Name"].dropna().unique().tolist()
                if company_list:
                    selected_company = st.selectbox("請選擇公司", sorted(company_list))
                    company_data = df[df["Name"] == selected_company].iloc[0]

                    pie_cols = ["Net block", "Current assets", "Investments"]
                    # 過濾掉 NaN 值或零值
                    pie_data_raw = company_data[pie_cols].dropna()
                    pie_data = pie_data_raw[pie_data_raw > 0] # 只考慮正值

                    if not pie_data.empty:
                        fig = px.pie(values=pie_data.values,
                                     names=pie_data.index,
                                     title=f"{selected_company} 的資產結構",
                                     hole=0.3)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning(f"公司 {selected_company} 的『淨固定資產』、『流動資產』或『投資』數據不足或為零，無法繪製資產結構圖。")
                else:
                    st.warning("沒有可供選擇的公司來繪製資產結構圖。")

            elif chart_option == "負債 vs 營運資金（散佈圖）":
                st.subheader("📉 負債 vs 營運資金")
                df_valid = df.dropna(subset=["Debt", "Working capital", "Name"])
                if not df_valid.empty:
                    fig = px.scatter(df_valid,
                                     x="Debt", y="Working capital",
                                     hover_name="Name",
                                     title="負債與營運資金的關係",
                                     labels={"Debt": "負債 (單位)", "Working capital": "營運資金 (單位)"}) # 添加單位
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("沒有足夠的『負債』或『營運資金』數據來繪製此圖。")

            elif chart_option == "財務比率表格":
                st.subheader("📋 財務比率表格")
                show_cols = ["Name", "負債比率 (%)", "流動比率", "Equity", "Balance sheet total"]
                available_cols = [col for col in show_cols if col in df.columns]
                if available_cols:
                    st.dataframe(df[available_cols].round(2))
                else:
                    st.warning("無法顯示財務比率表格，因為缺少所需的計算欄位或原始欄位。")

            elif chart_option == "各年度營收趨勢圖（單一公司）":
                st.subheader("📈 各年度營收趨勢")
                company_list = df["Name"].dropna().unique().tolist()
                if company_list:
                    selected_company = st.selectbox("請選擇公司", sorted(company_list), key="sales_trend_company")
                    company_data = df[df["Name"] == selected_company]
                    
                    sales_data = {}
                    if "Sales" in company_data.columns: sales_data["最新年度營收"] = company_data["Sales"].iloc[0]
                    if "Sales last year" in company_data.columns: sales_data["去年營收"] = company_data["Sales last year"].iloc[0]
                    if "Sales preceding year" in company_data.columns: sales_data["前年營收"] = company_data["Sales preceding year"].iloc[0]

                    sales_df = pd.DataFrame(sales_data.items(), columns=['年度', '營收']).dropna()
                    
                    if not sales_df.empty:
                        fig = px.line(sales_df, x='年度', y='營收', 
                                      title=f"{selected_company} 年度營收趨勢",
                                      markers=True,
                                      labels={"營收": "營收 (單位)"}) # 添加單位
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning(f"公司 {selected_company} 沒有足夠的年度營收數據來繪製趨勢圖。")
                else:
                    st.warning("沒有可供選擇的公司來繪製營收趨勢圖。")

            elif chart_option == "各年度淨利潤趨勢圖（單一公司）":
                st.subheader("📈 各年度淨利潤趨勢")
                company_list = df["Name"].dropna().unique().tolist()
                if company_list:
                    selected_company = st.selectbox("請選擇公司", sorted(company_list), key="profit_trend_company")
                    company_data = df[df["Name"] == selected_company]

                    profit_data = {}
                    if "Profit after tax" in company_data.columns: profit_data["最新年度淨利潤"] = company_data["Profit after tax"].iloc[0]
                    if "Profit after tax last year" in company_data.columns: profit_data["去年淨利潤"] = company_data["Profit after tax last year"].iloc[0]
                    if "Profit after tax preceding year" in company_data.columns: profit_data["前年淨利潤"] = company_data["Profit after tax preceding year"].iloc[0]

                    profit_df = pd.DataFrame(profit_data.items(), columns=['年度', '淨利潤']).dropna()

                    if not profit_df.empty:
                        fig = px.line(profit_df, x='年度', y='淨利潤', 
                                      title=f"{selected_company} 年度淨利潤趨勢",
                                      markers=True,
                                      labels={"淨利潤": "淨利潤 (單位)"}) # 添加單位
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning(f"公司 {selected_company} 沒有足夠的年度淨利潤數據來繪製趨勢圖。")
                else:
                    st.warning("沒有可供選擇的公司來繪製淨利潤趨勢圖。")

            elif chart_option == "各年度EPS趨勢圖（單一公司）":
                st.subheader("📈 各年度EPS趨勢")
                company_list = df["Name"].dropna().unique().tolist()
                if company_list:
                    selected_company = st.selectbox("請選擇公司", sorted(company_list), key="eps_trend_company")
                    company_data = df[df["Name"] == selected_company]

                    eps_data = {}
                    if "EPS" in company_data.columns: eps_data["最新年度EPS"] = company_data["EPS"].iloc[0]
                    if "EPS last year" in company_data.columns: eps_data["去年EPS"] = company_data["EPS last year"].iloc[0]
                    if "EPS preceding year" in company_data.columns: eps_data["前年EPS"] = company_data["EPS preceding year"].iloc[0]

                    eps_df = pd.DataFrame(eps_data.items(), columns=['年度', 'EPS']).dropna()

                    if not eps_df.empty:
                        fig = px.line(eps_df, x='年度', y='EPS', 
                                      title=f"{selected_company} 年度EPS趨勢",
                                      markers=True)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning(f"公司 {selected_company} 沒有足夠的年度EPS數據來繪製趨勢圖。")
                else:
                    st.warning("沒有可供選擇的公司來繪製EPS趨勢圖。")

            elif chart_option == "ROE與ROCE趨勢圖（單一公司）":
                st.subheader("📈 ROE 與 ROCE 趨勢")
                company_list = df["Name"].dropna().unique().tolist()
                if company_list:
                    selected_company = st.selectbox("請選擇公司", sorted(company_list), key="roce_roe_trend_company")
                    company_data = df[df["Name"] == selected_company]

                    roce_roe_data = {}
                    if "Return on equity" in company_data.columns: roce_roe_data["Return on equity"] = company_data["Return on equity"].iloc[0]
                    if "Return on capital employed" in company_data.columns: roce_roe_data["Return on capital employed"] = company_data["Return on capital employed"].iloc[0]

                    # 注意：這裡假設只有最新年度的數據，如果CSV中有歷史數據，需要調整為長格式
                    # 如果只有一個數值，無法繪製趨勢，可以考慮顯示 Metric 或 Bar Chart
                    
                    if "Return on equity" in company_data.columns and "Return on capital employed" in company_data.columns:
                        metrics_df = pd.DataFrame({
                            '指標': ['股東權益報酬率 (ROE)', '資本運用報酬率 (ROCE)'],
                            '數值': [company_data["Return on equity"].iloc[0], company_data["Return on capital employed"].iloc[0]]
                        }).dropna()
                        if not metrics_df.empty:
                            fig = px.bar(metrics_df, x='指標', y='數值', 
                                         title=f"{selected_company} 股東權益報酬率與資本運用報酬率",
                                         text_auto=True)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning(f"公司 {selected_company} 沒有足夠的 ROE 或 ROCE 數據。")
                    else:
                        st.warning(f"公司 {selected_company} 沒有足夠的 ROE 或 ROCE 數據來繪製。")
                else:
                    st.warning("沒有可供選擇的公司來繪製 ROE/ROCE 圖。")

            elif chart_option == "本益比與股東權益報酬率散佈圖":
                st.subheader("💹 本益比與股東權益報酬率")
                df_valid = df.dropna(subset=["Price to Earning", "Return on equity", "Name"])
                if not df_valid.empty:
                    fig = px.scatter(df_valid,
                                     x="Price to Earning", y="Return on equity",
                                     hover_name="Name",
                                     title="本益比 (P/E) 與股東權益報酬率 (ROE) 的關係",
                                     labels={"Price to Earning": "本益比", "Return on equity": "股東權益報酬率 (%)"},
                                     color="Industry" if "Industry" in df.columns else None) # 如果有產業欄位，可以按產業區分顏色
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("沒有足夠的『本益比』或『股東權益報酬率』數據來繪製此圖。")

            elif chart_option == "銷售額成長率排名（前20）":
                st.subheader("🏆 銷售額成長率排名 (前 20 名)")
                df_valid = df.dropna(subset=["Name", "Sales growth 3Years"])
                if not df_valid.empty:
                    top_sales_growth = df_valid.sort_values("Sales growth 3Years", ascending=False).head(20)
                    fig = px.bar(top_sales_growth,
                                 x="Name", y="Sales growth 3Years",
                                 title="銷售額成長率 (3 年) 前 20 名公司",
                                 text_auto=True,
                                 labels={"Sales growth 3Years": "銷售額成長率 (%)"})
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("沒有足夠的『銷售額成長率 (3 年)』數據來進行排名。")

            elif chart_option == "利潤成長率排名（前20）":
                st.subheader("💰 利潤成長率排名 (前 20 名)")
                df_valid = df.dropna(subset=["Name", "Profit growth 3Years"])
                if not df_valid.empty:
                    top_profit_growth = df_valid.sort_values("Profit growth 3Years", ascending=False).head(20)
                    fig = px.bar(top_profit_growth,
                                 x="Name", y="Profit growth 3Years",
                                 title="利潤成長率 (3 年) 前 20 名公司",
                                 text_auto=True,
                                 labels={"Profit growth 3Years": "利潤成長率 (%)"})
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("沒有足夠的『利潤成長率 (3 年)』數據來進行排名。")
            
            elif chart_option == "負債權益比率長條圖（前20）":
                st.subheader("⚖️ 負債權益比率排名 (前 20 名)")
                df_valid = df.dropna(subset=["Name", "Debt to Equity Ratio"])
                if not df_valid.empty:
                    # 篩選出合理的比率，例如小於某个閾值以避免極端值影響可讀性
                    df_valid = df_valid[df_valid["Debt to Equity Ratio"] < 100] # 假設超過100為極端值，可調整
                    top_debt_equity = df_valid.sort_values("Debt to Equity Ratio", ascending=False).head(20)
                    fig = px.bar(top_debt_equity,
                                 x="Name", y="Debt to Equity Ratio",
                                 title="負債權益比率前 20 名公司 (值越高代表負債越高)",
                                 text_auto=True)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("沒有足夠的『負債權益比率』數據來進行排名。")

            elif chart_option == "現金流量概覽圓餅圖（單一公司，最近一年）":
                st.subheader("💸 現金流量概覽")
                company_list = df["Name"].dropna().unique().tolist()
                if company_list:
                    selected_company = st.selectbox("請選擇公司", sorted(company_list), key="cash_flow_pie_company")
                    company_data = df[df["Name"] == selected_company].iloc[0]

                    cash_flow_sources = {
                        "來自營運的現金": company_data.get("Cash from operations last year"),
                        "來自投資的現金": company_data.get("Cash from investing last year"),
                        "來自融資的現金": company_data.get("Cash from financing last year")
                    }
                    
                    # 轉換為 DataFrame 並去除 NaN
                    cash_flow_df = pd.DataFrame(list(cash_flow_sources.items()), columns=['來源', '金額']).dropna()
                    
                    if not cash_flow_df.empty:
                        fig = px.pie(cash_flow_df, values='金額', names='來源',
                                     title=f"{selected_company} 最近一年現金流量概覽",
                                     hole=0.3)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning(f"公司 {selected_company} 沒有足夠的現金流量數據來繪製概覽圖。")
                else:
                    st.warning("沒有可供選擇的公司來繪製現金流量概覽圖。")

            elif chart_option == "自由現金流趨勢圖（單一公司）":
                st.subheader("💰 自由現金流趨勢")
                company_list = df["Name"].dropna().unique().tolist()
                if company_list:
                    selected_company = st.selectbox("請選擇公司", sorted(company_list), key="fcf_trend_company")
                    company_data = df[df["Name"] == selected_company]

                    fcf_data = {}
                    if "Free cash flow last year" in company_data.columns: fcf_data["去年自由現金流"] = company_data["Free cash flow last year"].iloc[0]
                    if "Free cash flow preceding year" in company_data.columns: fcf_data["前年自由現金流"] = company_data["Free cash flow preceding year"].iloc[0]
                    if "Free cash flow 3years" in company_data.columns: fcf_data["3年前自由現金流"] = company_data["Free cash flow 3years"].iloc[0]
                    if "Free cash flow 5years" in company_data.columns: fcf_data["5年前自由現金流"] = company_data["Free cash flow 5years"].iloc[0]
                    if "Free cash flow 7years" in company_data.columns: fcf_data["7年前自由現金流"] = company_data["Free cash flow 7years"].iloc[0]
                    if "Free cash flow 10years" in company_data.columns: fcf_data["10年前自由現金流"] = company_data["Free cash flow 10years"].iloc[0]

                    fcf_df = pd.DataFrame(fcf_data.items(), columns=['年度', '自由現金流']).dropna()
                    fcf_df['年度'] = fcf_df['年度'].str.extract(r'(\d+年前|去年|前年)').fillna('最新年度') # 簡化年度標籤

                    if not fcf_df.empty:
                        # 嘗試將年度排序，確保趨勢正確
                        year_order = {'10年前':0, '7年前':1, '5年前':2, '3年前':3, '前年':4, '去年':5, '最新年度':6}
                        fcf_df['年度_排序'] = fcf_df['年度'].map(year_order)
                        fcf_df = fcf_df.sort_values('年度_排序')

                        fig = px.line(fcf_df, x='年度', y='自由現金流', 
                                      title=f"{selected_company} 自由現金流趨勢",
                                      markers=True,
                                      labels={"自由現金流": "自由現金流 (單位)"}) # 添加單位
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning(f"公司 {selected_company} 沒有足夠的自由現金流數據來繪製趨勢圖。")
                else:
                    st.warning("沒有可供選擇的公司來繪製自由現金流趨勢圖。")
                
        else:
            st.warning("目前上傳的資料缺少能繪製任何圖表所需的欄位。請確認 CSV 檔案內容或上傳包含更完整財務數據的檔案。")

        st.markdown("---")
        with st.expander("🔍 查看上傳資料的欄位"):
            st.write(list(df.columns))
        with st.expander("📊 查看前 5 行資料"):
            st.dataframe(df.head())

    except Exception as e:
        st.error(f"讀取或處理 CSV 檔案時發生錯誤：{e}")
        st.info("請確保您上傳的是有效的 CSV 檔案，並且數字欄位沒有不規範的字元。")

else:
    st.info("⬆️ 請上傳一個財務資料 CSV 檔案以開始分析。")

st.markdown("---")
st.caption("© 2025 財務分析儀表板. 所有數據分析結果僅供參考。")