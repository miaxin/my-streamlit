import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import google.generativeai as genai # Import Gemini library

# --- Gemini API Configuration ---
# Load API key from Streamlit secrets
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Gemini API key not found in .streamlit/secrets.toml. Please add it.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Initialize Gemini Pro model
# You can choose other models like 'gemini-pro-vision' for image-related tasks
try:
    gemini_model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    st.error(f"Failed to initialize Gemini model: {e}")
    st.stop()


st.set_page_config(page_title="財務分析儀表板", layout="wide")
st.title("📊 財務分析儀表板與AI洞察")
st.markdown("---")
st.markdown(""" **請上傳CSV 檔案**。 """)

st.markdown("---")

uploaded_file = st.file_uploader("📤 上傳您的合併財務 CSV 檔案", type=["csv"])

# Function to robustly convert columns to numeric
@st.cache_data # Cache this function to avoid re-running on every interaction
def convert_df_to_numeric(df_input):
    df_output = df_input.copy() # Work on a copy
    for col in df_output.columns:
        try:
            temp_series = pd.to_numeric(df_output[col], errors='coerce')
            original_non_null_count = df_output[col].count()
            converted_non_null_count = temp_series.count()
            
            # Heuristic: if a significant portion (e.g., > 70%) converted to numeric, assume it's numeric
            # And make sure it wasn't originally a purely object/boolean column unless it has actual numbers
            if original_non_null_count > 0 and converted_non_null_count / original_non_null_count > 0.7:
                if not pd.api.types.is_bool_dtype(df_output[col]) and (pd.api.types.is_numeric_dtype(df_output[col]) or pd.api.types.is_object_dtype(df_output[col])):
                    df_output[col] = temp_series
                    df_output[col].replace([np.inf, -np.inf], np.nan, inplace=True)
        except Exception:
            pass # Skip if conversion attempt fails for some unexpected reason
    return df_output

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = df.columns.str.strip()

        st.success("CSV 檔案上傳成功！正在處理數據...")

        # Use the automatic numeric conversion function
        df = convert_df_to_numeric(df)

        # 確保必要的名稱欄位存在，且是字符串類型
        if 'Name' not in df.columns and 'name' in df.columns:
            df.rename(columns={'name': 'Name'}, inplace=True)
        if 'Name' in df.columns:
            df['Name'] = df['Name'].astype(str).str.strip()
        else:
            st.error("CSV 檔案中缺少 'Name' (或 'name') 欄位，無法進行公司層級分析。請確保數據包含公司名稱。")
            st.stop()
        
        # 預先計算可能用到的欄位
        if "Balance sheet total" in df.columns and "Debt" in df.columns and df["Balance sheet total"].sum() != 0:
            df["負債比率 (%)"] = (df["Debt"] / df["Balance sheet total"]) * 100
            df["負債比率 (%)"].replace([np.inf, -np.inf], np.nan, inplace=True)
        else:
            df["負債比率 (%)"] = np.nan # 如果欄位不存在或總和為零，則為 NaN
        
        if all(col in df.columns for col in ["Equity capital", "Reserves", "Preference capital"]):
            df["總股東權益"] = df["Equity capital"] + df["Reserves"] + df["Preference capital"]
        elif "Balance sheet total" in df.columns and "Debt" in df.columns:
            df["總股東權益"] = df["Balance sheet total"] - df["Debt"]
        else:
            df["總股東權益"] = np.nan

        if "Current assets" in df.columns and "Current liabilities" in df.columns and df["Current liabilities"].sum() != 0:
            df["流動比率"] = df["Current assets"] / df["Current liabilities"]
            df["流動比率"].replace([np.inf, -np.inf], np.nan, inplace=True)
        else:
            df["流動比率"] = np.nan

        if 'Debt' in df.columns and 'Equity capital' in df.columns and df['Equity capital'].sum() != 0:
            df['Debt to Equity Ratio'] = df['Debt'] / df['Equity capital']
            df['Debt to Equity Ratio'].replace([np.inf, -np.inf], np.nan, inplace=True)
        else:
            df['Debt to Equity Ratio'] = np.nan

        # ----------------------------------------------------
        # 定義圖表需求 (基於欄位存在性)
        # ----------------------------------------------------
        chart_requirements = {
            "產業市值長條圖（前 8 名 + 其他）": {
                "required": {"Industry", "Market Capitalization"},
                "description": "展示各產業的總市值分佈。數據來源：`Annual_P_L_1_final.csv`, `cleaned_combined_data.csv` 或已合併的數據。"
            },
            "資產結構圓餅圖（單一公司）": {
                "required": {"Name", "Net block", "Current assets", "Investments"},
                "description": "顯示單一公司的淨固定資產、流動資產和投資在總資產中的佔比。數據來源：`Balance_Sheet_final.csv` 或已合併的數據。"
            },
            "負債 vs 營運資金（散佈圖）": {
                "required": {"Debt", "Working capital", "Name"},
                "description": "分析負債與營運資金之間的關係，並識別特定公司。數據來源：`Balance_Sheet_final.csv` 或已合併的數據。"
            },
            "財務比率表格": {
                "required": {"Name", "負債比率 (%)", "流動比率", "總股東權益", "Balance sheet total"},
                "description": "顯示計算後的關鍵財務比率和基本資產負債數據。數據來源：`Balance_Sheet_final.csv` 及計算所得。"
            },
            "各年度營收趨勢圖（單一公司）": {
                "required": {"Name", "Sales", "Sales last year", "Sales preceding year"},
                "description": "追蹤單一公司在過去三個會計年度的營收變化。數據來源：`Annual_P_L_1_final.csv`, `cleaned_combined_data.csv` 或已合併的數據。"
            },
            "各年度淨利潤趨勢圖（單一公司）": {
                "required": {"Name", "Profit after tax", "Profit after tax last year", "Profit after tax preceding year"},
                "description": "追蹤單一公司在過去三個會計年度的淨利潤變化。數據來源：`Annual_P_L_1_final.csv`, `cleaned_combined_data.csv` 或已合併的數據。"
            },
            "各年度EPS趨勢圖（單一公司）": {
                "required": {"Name", "EPS", "EPS last year", "EPS preceding year"},
                "description": "追蹤單一公司在過去三個會計年度的每股盈餘 (EPS) 變化。數據來源：`Annual_P_L_1_final.csv`, `cleaned_combined_data.csv` 或已合併的數據。"
            },
            "ROE與ROCE比較圖（單一公司，最新年度）": {
                "required": {"Name", "Return on equity", "Return on capital employed"},
                "description": "比較單一公司最新年度的股東權益報酬率 (ROE) 和資本運用報酬率 (ROCE)。數據來源：`ratios_1_final.csv`, `cleaned_combined_data.csv` 或已合併的數據。"
            },
            "本益比與股東權益報酬率散佈圖": {
                "required": {"Price to Earning", "Return on equity", "Name"},
                "description": "分析所有公司在本益比和股東權益報酬率之間的關係，有助於投資者評估。數據來源：`ratios_1_final.csv`, `cleaned_combined_data.csv` 或已合併的數據。"
            },
            "銷售額成長率排名（前20）": {
                "required": {"Name", "Sales growth 3Years"},
                "description": "列出過去三年銷售額成長最快的前 20 家公司。數據來源：`Annual_P_L_2_final.csv`, `cleaned_combined_data.csv` 或已合併的數據。"
            },
            "利潤成長率排名（前20）": {
                "required": {"Name", "Profit growth 3Years"},
                "description": "列出過去三年利潤成長最快的前 20 家公司。數據來源：`Annual_P_L_2_final.csv`, `cleaned_combined_data.csv` 或已合併的數據。"
            },
            "負債權益比率長條圖（前20）": {
                "required": {"Name", "Debt to Equity Ratio"},
                "description": "顯示負債權益比率最高的 20 家公司。數據來源：`ratios_1_final.csv`, `Balance_Sheet_final.csv` 及計算所得。"
            },
            "現金流量概覽圓餅圖（單一公司，最近一年）": {
                "required": {"Name", "Cash from operations last year", "Cash from investing last year", "Cash from financing last year"},
                "description": "展示單一公司最近一個會計年度的營運、投資和融資現金流分佈。數據來源：`cash_flow_statments_final.csv`, `cleaned_combined_data.csv` 或已合併的數據。"
            },
            "自由現金流趨勢圖（單一公司）": {
                "required": {"Name", "Free cash flow last year", "Free cash flow preceding year", "Free cash flow 3years", "Free cash flow 5years", "Free cash flow 7years", "Free cash flow 10years"},
                "description": "追蹤單一公司過去多年的自由現金流趨勢。數據來源：`cash_flow_statments_final.csv`, `cleaned_combined_data.csv` 或已合併的數據。"
            },
             "股價相對表現趨勢圖（單一公司）": {
                "required": {"Name", "Current Price", "t_1_price", "Return over 1year", "Return over 3years", "Return over 5years"},
                "description": "展示單一公司在不同時間段的股價回報率。數據來源：`price_final.csv`, `t1_prices.csv` 或已合併的數據。"
            },
            "市值分佈直方圖": {
                "required": {"Market Capitalization"},
                "description": "顯示市場資本化的分佈情況。數據來源：多個檔案中均有此欄位。"
            },
            "銷售額與淨利潤關係散佈圖": {
                "required": {"Sales", "Net profit", "Name"},
                "description": "分析公司銷售額與淨利潤之間的關係。數據來源：`Annual_P_L_1_final.csv`, `cleaned_combined_data.csv` 或已合併的數據。"
            },
            "平均股東權益報酬率排名（前20）": {
                "required": {"Name", "Average return on equity 5Years"},
                "description": "列出過去五年平均股東權益報酬率最高的前 20 家公司。數據來源：`ratios_2_final.csv`, `cleaned_combined_data.csv` 或已合併的數據。"
            },
            "發起人持股比例分佈（圓餅圖）": {
                "required": {"Promoter holding", "FII holding", "DII holding", "Public holding"},
                "description": "顯示所有公司平均或單一公司發起人、外資、本土機構和公眾持股比例。數據來源：`ratios_1_final.csv`, `cleaned_combined_data.csv` 或已合併的數據。"
            }
        }

        # 只挑出能畫的圖
        available_charts = []
        unavailable_charts = []
        
        for chart_name, details in chart_requirements.items():
            required_cols = details["required"]
            if required_cols.issubset(df.columns):
                available_charts.append(chart_name)
            else:
                missing_cols = required_cols - set(df.columns)
                unavailable_charts.append(f"- {chart_name}: 缺少欄位 {', '.join(missing_cols)}")

        # --- Streamlit Sidebar for Chart Selection ---
        if available_charts:
            st.sidebar.header("📊 圖表選擇")
            chart_option = st.sidebar.selectbox("🔽 根據資料欄位選擇分析圖表：", sorted(available_charts))

            # ----------------------------------------------------
            # 圖表繪製區 (這部分程式碼與您之前提供的完全相同，為簡潔這裡省略，您應將其放在這裡)
            # 因為這部分非常長，如果貼上會佔用大量空間，請確保您將其複製到此處
            # 從 "if chart_option == "產業市值長條圖（前 8 名 + 其他）":" 開始
            # 直到 "elif chart_option == "發起人持股比例分佈（圓餅圖）":" 的結尾
            # ----------------------------------------------------

            # --- Start of Chart Plotting Section (Copy and Paste your full chart plotting code here) ---
            # ... (Your existing chart plotting code goes here) ...
            if chart_option == "產業市值長條圖（前 8 名 + 其他）":
                st.subheader("🏭 各產業市值分佈")
                df_valid = df.dropna(subset=["Industry", "Market Capitalization"])
                if not df_valid.empty:
                    industry_market = df_valid.groupby("Industry", as_index=False)["Market Capitalization"].sum()
                    industry_market = industry_market.sort_values("Market Capitalization", ascending=False)

                    top_n = 8
                    top_industries = industry_market.head(top_n).copy() 
                    other_sum = industry_market.iloc[top_n:]["Market Capitalization"].sum()
                    
                    if other_sum > 0:
                        top_industries = pd.concat([
                            top_industries,
                            pd.DataFrame([{"Industry": "其他", "Market Capitalization": other_sum}])
                        ])
                    
                    fig = px.bar(top_industries,
                                 x="Industry", y="Market Capitalization",
                                 title="前 8 名產業市值 + 其他",
                                 text_auto=True,
                                 labels={"Market Capitalization": "市值"})
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("沒有足夠的『Industry』和『Market Capitalization』數據來繪製此圖。")

            elif chart_option == "資產結構圓餅圖（單一公司）":
                st.subheader("🏢 公司資產結構")
                company_list = df["Name"].dropna().unique().tolist()
                if company_list:
                    selected_company = st.selectbox("請選擇公司", sorted(company_list), key="asset_pie_company")
                    company_data = df[df["Name"] == selected_company].iloc[0]

                    pie_cols = {"Net block": "淨固定資產", "Current assets": "流動資產", "Investments": "投資"}
                    plot_data = pd.DataFrame([
                        {'資產類型': display_name, '金額': company_data[col]}
                        for col, display_name in pie_cols.items()
                        if col in company_data and pd.notna(company_data[col]) and company_data[col] > 0
                    ])

                    if not plot_data.empty:
                        fig = px.pie(plot_data,
                                     values='金額',
                                     names='資產類型',
                                     title=f"{selected_company} 的資產結構",
                                     hole=0.3)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning(f"公司 {selected_company} 沒有足夠的『淨固定資產』、『流動資產』或『投資』數據（或數據為零/負數）來繪製資產結構圖。")
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
                                     labels={"Debt": "負債", "Working capital": "營運資金"},
                                     color="Industry" if "Industry" in df_valid.columns else None,
                                     trendline="ols" if len(df_valid) > 2 else None)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("沒有足夠的『Debt』或『Working capital』數據來繪製此圖。")

            elif chart_option == "財務比率表格":
                st.subheader("📋 財務比率表格")
                show_cols = ["Name", "負債比率 (%)", "流動比率", "總股東權益", "Balance sheet total"]
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
                    company_data = df[df["Name"] == selected_company].iloc[0]

                    sales_series = {}
                    if "Sales" in company_data and pd.notna(company_data["Sales"]): sales_series["最新年度"] = company_data["Sales"]
                    if "Sales last year" in company_data and pd.notna(company_data["Sales last year"]): sales_series["去年"] = company_data["Sales last year"]
                    if "Sales preceding year" in company_data and pd.notna(company_data["Sales preceding year"]): sales_series["前年"] = company_data["Sales preceding year"]

                    sales_df = pd.DataFrame(sales_series.items(), columns=['年度', '營收']).dropna()
                    
                    if not sales_df.empty:
                        year_order = {"前年": 0, "去年": 1, "最新年度": 2}
                        sales_df["_sort_key"] = sales_df["年度"].map(year_order)
                        sales_df = sales_df.sort_values("_sort_key").drop(columns="_sort_key")

                        fig = px.line(sales_df, x='年度', y='營收',
                                      title=f"{selected_company} 年度營收趨勢",
                                      markers=True,
                                      labels={"營收": "營收"})
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
                    company_data = df[df["Name"] == selected_company].iloc[0]

                    profit_series = {}
                    if "Profit after tax" in company_data and pd.notna(company_data["Profit after tax"]): profit_series["最新年度"] = company_data["Profit after tax"]
                    if "Profit after tax last year" in company_data and pd.notna(company_data["Profit after tax last year"]): profit_series["去年"] = company_data["Profit after tax last year"]
                    if "Profit after tax preceding year" in company_data and pd.notna(company_data["Profit after tax preceding year"]): profit_series["前年"] = company_data["Profit after tax preceding year"]

                    profit_df = pd.DataFrame(profit_series.items(), columns=['年度', '淨利潤']).dropna()

                    if not profit_df.empty:
                        year_order = {"前年": 0, "去年": 1, "最新年度": 2}
                        profit_df["_sort_key"] = profit_df["年度"].map(year_order)
                        profit_df = profit_df.sort_values("_sort_key").drop(columns="_sort_key")

                        fig = px.line(profit_df, x='年度', y='淨利潤',
                                      title=f"{selected_company} 年度淨利潤趨勢",
                                      markers=True,
                                      labels={"淨利潤": "淨利潤"})
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
                    company_data = df[df["Name"] == selected_company].iloc[0]

                    eps_series = {}
                    if "EPS" in company_data and pd.notna(company_data["EPS"]): eps_series["最新年度"] = company_data["EPS"]
                    if "EPS last year" in company_data and pd.notna(company_data["EPS last year"]): eps_series["去年"] = company_data["EPS last year"]
                    if "EPS preceding year" in company_data and pd.notna(company_data["EPS preceding year"]): eps_series["前年"] = company_data["EPS preceding year"]

                    eps_df = pd.DataFrame(eps_series.items(), columns=['年度', 'EPS']).dropna()

                    if not eps_df.empty:
                        year_order = {"前年": 0, "去年": 1, "最新年度": 2}
                        eps_df["_sort_key"] = eps_df["年度"].map(year_order)
                        eps_df = eps_df.sort_values("_sort_key").drop(columns="_sort_key")

                        fig = px.line(eps_df, x='年度', y='EPS',
                                      title=f"{selected_company} 年度EPS趨勢",
                                      markers=True)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning(f"公司 {selected_company} 沒有足夠的年度EPS數據來繪製趨勢圖。")
                else:
                    st.warning("沒有可供選擇的公司來繪製EPS趨勢圖。")

            elif chart_option == "ROE與ROCE比較圖（單一公司，最新年度）":
                st.subheader("📈 ROE 與 ROCE 比較")
                company_list = df["Name"].dropna().unique().tolist()
                if company_list:
                    selected_company = st.selectbox("請選擇公司", sorted(company_list), key="roce_roe_company")
                    company_data = df[df["Name"] == selected_company].iloc[0]

                    metrics_data = {}
                    if "Return on equity" in company_data and pd.notna(company_data["Return on equity"]):
                        metrics_data["股東權益報酬率 (ROE)"] = company_data["Return on equity"]
                    if "Return on capital employed" in company_data and pd.notna(company_data["Return on capital employed"]):
                        metrics_data["資本運用報酬率 (ROCE)"] = company_data["Return on capital employed"]
                    
                    metrics_df = pd.DataFrame(metrics_data.items(), columns=['指標', '數值']).dropna()

                    if not metrics_df.empty:
                        fig = px.bar(metrics_df, x='指標', y='數值',
                                     title=f"{selected_company} 股東權益報酬率與資本運用報酬率 (最新年度)",
                                     text_auto=True,
                                     labels={"數值": "百分比 (%)"})
                        st.plotly_chart(fig, use_container_width=True)
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
                                     color="Industry" if "Industry" in df.columns else None, # 如果有產業欄位，可以按產業區分顏色
                                     size="Market Capitalization" if "Market Capitalization" in df.columns else None, # 以市值大小區分點大小
                                     hover_data=["Industry", "Market Capitalization"] if "Industry" in df.columns and "Market Capitalization" in df.columns else None
                                     )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("沒有足夠的『Price to Earning』或『Return on equity』數據來繪製此圖。")

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
                    st.warning("沒有足夠的『Sales growth 3Years』數據來進行排名。")

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
                    st.warning("沒有足夠的『Profit growth 3Years』數據來進行排名。")
            
            elif chart_option == "負債權益比率長條圖（前20）":
                st.subheader("⚖️ 負債權益比率排名 (前 20 名)")
                df_valid = df.dropna(subset=["Name", "Debt to Equity Ratio"])
                if not df_valid.empty:
                    df_valid_filtered = df_valid[df_valid["Debt to Equity Ratio"] < 1000] # Filter out extreme values
                    top_debt_equity = df_valid_filtered.sort_values("Debt to Equity Ratio", ascending=False).head(20)
                    
                    if not top_debt_equity.empty:
                        fig = px.bar(top_debt_equity,
                                     x="Name", y="Debt to Equity Ratio",
                                     title="負債權益比率前 20 名公司 (值越高代表負債越高)",
                                     text_auto=True)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("在篩選合理範圍後，沒有足夠的『負債權益比率』數據來進行排名。")
                else:
                    st.warning("沒有足夠的『Debt to Equity Ratio』數據來進行排名。")

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
                    
                    cash_flow_df = pd.DataFrame(list(cash_flow_sources.items()), columns=['來源', '金額'])
                    cash_flow_df['金額'] = pd.to_numeric(cash_flow_df['金額'], errors='coerce') 
                    cash_flow_df = cash_flow_df.dropna()
                    cash_flow_df = cash_flow_df[cash_flow_df['金額'] != 0] 

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
                    company_data = df[df["Name"] == selected_company].iloc[0]

                    fcf_data = {}
                    fcf_years_map = {
                        "10年前": "Free cash flow 10years", "7年前": "Free cash flow 7years",
                        "5年前": "Free cash flow 5years", "3年前": "Free cash flow 3years",
                        "前年": "Free cash flow preceding year", "去年": "Free cash flow last year",
                        "最新年度": "Free cash flow"
                    }
                    
                    for year_label, col_name in fcf_years_map.items():
                        if col_name in company_data and pd.notna(company_data[col_name]):
                            fcf_data[year_label] = company_data[col_name]

                    fcf_df = pd.DataFrame(fcf_data.items(), columns=['年度', '自由現金流']).dropna()
                    
                    if not fcf_df.empty:
                        year_order_keys = list(fcf_years_map.keys())
                        fcf_df['年度_排序'] = fcf_df['年度'].apply(lambda x: year_order_keys.index(x))
                        fcf_df = fcf_df.sort_values('年度_排序').drop(columns='年度_排序')

                        fig = px.line(fcf_df, x='年度', y='自由現金流',
                                      title=f"{selected_company} 自由現金流趨勢",
                                      markers=True,
                                      labels={"自由現金流": "自由現金流"})
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning(f"公司 {selected_company} 沒有足夠的自由現金流數據來繪製趨勢圖。")
                else:
                    st.warning("沒有可供選擇的公司來繪製自由現金流趨勢圖。")
            
            elif chart_option == "股價相對表現趨勢圖（單一公司）":
                st.subheader("📈 股價相對表現趨勢")
                company_list = df["Name"].dropna().unique().tolist()
                if company_list:
                    selected_company = st.selectbox("請選擇公司", sorted(company_list), key="price_trend_company")
                    company_data = df[df["Name"] == selected_company].iloc[0]

                    returns_data = {}
                    if "Current Price" in company_data and pd.notna(company_data["Current Price"]):
                        returns_data["最新股價"] = company_data["Current Price"]
                    if "t_1_price" in company_data and pd.notna(company_data["t_1_price"]):
                        returns_data["前一個交易日價格"] = company_data["t_1_price"]
                    if "Return over 1year" in company_data and pd.notna(company_data["Return over 1year"]):
                        returns_data["1年回報率 (%)"] = company_data["Return over 1year"]
                    if "Return over 3years" in company_data and pd.notna(company_data["Return over 3years"]):
                        returns_data["3年回報率 (%)"] = company_data["Return over 3years"]
                    if "Return over 5years" in company_data and pd.notna(company_data["Return over 5years"]):
                        returns_data["5年回報率 (%)"] = company_data["5年回報率 (%)"] # Corrected to existing col
                    
                    if returns_data:
                        returns_df = pd.DataFrame([
                            {'期間': k, '數值': v} for k, v in returns_data.items()
                        ]).dropna()

                        if len(returns_df) <= 2 and "最新股價" in returns_data:
                            st.metric(label=f"{selected_company} 當前股價", value=f"{returns_data['最新股價']:.2f}")
                            if "前一個交易日價格" in returns_data:
                                st.metric(label=f"{selected_company} 前一個交易日價格", value=f"{returns_data['前一個交易日價格']:.2f}")
                            st.info("僅有少量股價數據，無法繪製有意義的趨勢圖。已顯示關鍵價格指標。")
                        elif not returns_df.empty:
                            returns_filtered_df = returns_df[returns_df['期間'].str.contains('回報率')]
                            if not returns_filtered_df.empty:
                                fig = px.bar(returns_filtered_df, x='期間', y='數值',
                                             title=f"{selected_company} 股價回報率 (%)",
                                             text_auto=True,
                                             labels={"數值": "回報率 (%)"})
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.warning(f"公司 {selected_company} 沒有足夠的股價回報率數據來繪製圖表。")
                        else:
                            st.warning(f"公司 {selected_company} 沒有足夠的股價數據來繪製趨勢圖。")
                    else:
                        st.warning(f"公司 {selected_company} 沒有足夠的股價或回報率數據來繪製趨勢圖。")
                else:
                    st.warning("沒有可供選擇的公司來繪製股價相對表現趨勢圖。")

            elif chart_option == "市值分佈直方圖":
                st.subheader("📈 市值分佈")
                df_valid = df.dropna(subset=["Market Capitalization"])
                if not df_valid.empty:
                    fig = px.histogram(df_valid, x="Market Capitalization",
                                       title="公司市值分佈",
                                       labels={"Market Capitalization": "市值"},
                                       nbins=20)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("沒有足夠的『Market Capitalization』數據來繪製市值分佈直方圖。")

            elif chart_option == "銷售額與淨利潤關係散佈圖":
                st.subheader("💹 銷售額與淨利潤關係")
                df_valid = df.dropna(subset=["Sales", "Net profit", "Name"])
                if not df_valid.empty:
                    fig = px.scatter(df_valid,
                                     x="Sales", y="Net profit",
                                     hover_name="Name",
                                     title="公司銷售額與淨利潤的關係",
                                     labels={"Sales": "銷售額", "Net profit": "淨利潤"},
                                     color="Industry" if "Industry" in df_valid.columns else None,
                                     size="Market Capitalization" if "Market Capitalization" in df_valid.columns else None
                                     )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("沒有足夠的『Sales』或『Net profit』數據來繪製此圖。")

            elif chart_option == "平均股東權益報酬率排名（前20）":
                st.subheader("💰 平均股東權益報酬率排名 (前 20 名)")
                df_valid = df.dropna(subset=["Name", "Average return on equity 5Years"])
                if not df_valid.empty:
                    top_roe_avg = df_valid.sort_values("Average return on equity 5Years", ascending=False).head(20)
                    fig = px.bar(top_roe_avg,
                                 x="Name", y="Average return on equity 5Years",
                                 title="平均股東權益報酬率 (5 年) 前 20 名公司",
                                 text_auto=True,
                                 labels={"Average return on equity 5Years": "平均股東權益報酬率 (%)"})
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("沒有足夠的『Average return on equity 5Years』數據來進行排名。")

            elif chart_option == "發起人持股比例分佈（圓餅圖）":
                st.subheader("👥 發起人持股比例分佈")
                
                analysis_scope = st.radio("分析範圍", ["所有公司平均", "單一公司"], key="holding_scope")

                if analysis_scope == "所有公司平均":
                    holding_cols = ["Promoter holding", "FII holding", "DII holding", "Public holding"]
                    
                    valid_holding_cols = [col for col in holding_cols if col in df.columns and df[col].dropna().any()]

                    if len(valid_holding_cols) >= 2:
                        avg_holdings = df[valid_holding_cols].mean().dropna()

                        if not avg_holdings.empty:
                            fig = px.pie(values=avg_holdings.values,
                                         names=avg_holdings.index,
                                         title="所有公司平均持股比例分佈",
                                         hole=0.3)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("沒有足夠的平均持股數據（發起人、FII、DII、公眾持股）來繪製圓餅圖。")
                    else:
                        st.warning("缺少繪製發起人持股比例分佈圓餅圖所需至少兩個持股類型欄位 (如 Promoter holding, FII holding 等)。")

                elif analysis_scope == "單一公司":
                    company_list = df["Name"].dropna().unique().tolist()
                    if company_list:
                        selected_company = st.selectbox("請選擇公司", sorted(company_list), key="holding_company")
                        company_data = df[df["Name"] == selected_company].iloc[0]

                        holding_cols = ["Promoter holding", "FII holding", "DII holding", "Public holding"]
                        
                        single_company_holdings = {
                            name: company_data[name] for name in holding_cols
                            if name in company_data and pd.notna(company_data[name])
                        }
                        
                        holding_df = pd.DataFrame(single_company_holdings.items(), columns=['持股類型', '比例']).dropna()
                        holding_df['比例'] = pd.to_numeric(holding_df['比例'], errors='coerce')
                        holding_df = holding_df[holding_df['比例'] > 0]

                        if not holding_df.empty:
                            fig = px.pie(holding_df, values='比例', names='持股類型',
                                         title=f"{selected_company} 的持股比例分佈",
                                         hole=0.3)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning(f"公司 {selected_company} 沒有足夠的持股數據（發起人、FII、DII、公眾持股）來繪製圓餅圖。")
                    else:
                        st.warning("沒有可供選擇的公司來繪製單一公司持股比例分佈圖。")
            # --- End of Chart Plotting Section ---


        else: # If no charts are available
            st.warning("目前上傳的資料缺少能繪製任何圖表所需的欄位。請確認 CSV 檔案內容。")
            if unavailable_charts:
                st.info("以下圖表因為缺少必要欄位而無法顯示：")
                for chart_info in unavailable_charts:
                    st.markdown(chart_info)
                st.markdown("請參考上方**『💡 溫馨提示』**，將多個財務數據檔案合併後再上傳，以獲得更全面的分析。")

        st.markdown("---")
        with st.expander("🔍 查看上傳資料的欄位"):
            st.write(list(df.columns))
        with st.expander("📊 查看前 5 行資料"):
            st.dataframe(df.head())

        # --- Gemini AI Chat Section ---
        st.markdown("---")
        st.header("🤖 AI 洞察分析 (Gemini)")
        st.info("您可以向 AI 提問關於上傳數據的問題，例如：\n- 『幫我分析一下銷售額和淨利潤的關係。』\n- 『市場市值最高的公司是哪家？它的主要財務指標是什麼？』\n- 『解釋一下流動比率的意義。』")

        user_query = st.text_input("💬 輸入您的問題：", key="gemini_query")

        if user_query:
            with st.spinner("AI 正在思考中..."):
                try:
                    # Construct a prompt for Gemini
                    # This is crucial: provide context about the data
                    # For simplicity, we'll provide column names and a sample of data
                    # For more complex queries, you might want to extract specific company data or aggregate statistics.
                    
                    data_summary = df.head().to_markdown(index=False) # Provide first 5 rows as context
                    column_info = ", ".join(df.columns.tolist()) # Provide all column names

                    prompt = f"""
                    你是一個專業的財務分析助理，請根據我提供的財務數據回答問題。
                    以下是你可用的數據的欄位名稱：
                    {column_info}

                    以下是數據的前幾行範例（用於理解數據格式，可能不包含回答所有問題所需的所有數據）：
                    ```
                    {data_summary}
                    ```

                    請根據上述信息，嘗試回答我的問題。如果數據中沒有直接的信息，請說明並給出合理的財務見解。
                    我的問題是："{user_query}"
                    """
                    
                    # If the query is about a specific company, try to extract that company's data
                    # This is a simple heuristic, can be improved.
                    relevant_company_name = None
                    for company in df['Name'].dropna().unique():
                        if company.lower() in user_query.lower():
                            relevant_company_name = company
                            break
                    
                    if relevant_company_name and 'Name' in df.columns:
                        company_data_str = df[df['Name'] == relevant_company_name].iloc[0].dropna().to_string()
                        prompt = f"""
                        你是一個專業的財務分析助理，請根據我提供的財務數據回答問題。
                        以下是你可用的數據的欄位名稱：
                        {column_info}

                        針對公司 '{relevant_company_name}'，其詳細財務數據如下：
                        ```
                        {company_data_str}
                        ```

                        請根據上述信息，嘗試回答我的問題。如果數據中沒有直接的信息，請說明並給出合理的財務見解。
                        我的問題是："{user_query}"
                        """

                    response = gemini_model.generate_content(prompt)
                    st.markdown("#### 🤖 Gemini 的回應：")
                    st.write(response.text)

                except Exception as e:
                    st.error(f"與 Gemini API 通訊時發生錯誤：{e}")
                    st.warning("請檢查您的 API 金鑰是否正確，並確認問題是否過於複雜或需要超出提供數據範圍的上下文。")

    except Exception as e:
        st.error(f"讀取或處理 CSV 檔案時發生錯誤：{e}")
        st.info("請確保您上傳的是有效的 CSV 檔案，並且數字欄位沒有不規範的字元。")

else:
    st.info("⬆️ 請上傳一個財務資料 CSV 檔案以開始分析。")

st.markdown("---")
st.caption("© 2025 財務分析儀表板. 所有數據分析結果僅供參考。")