import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import google.generativeai as genai
import os

# --- Gemini API Configuration ---
# Load API key from Streamlit secrets
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Gemini API key not found in .streamlit/secrets.toml. Please add it.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Initialize Gemini Pro model
try:
    gemini_model = genai.GenerativeModel('gemini-2.5-flash')
    # Initialize chat session for conversational AI
    if "chat" not in st.session_state:
        st.session_state.chat = gemini_model.start_chat(history=[])
except Exception as e:
    st.error(f"Failed to initialize Gemini model or chat: {e}")
    st.stop()


st.set_page_config(page_title="財務分析儀表板", layout="wide")
st.title("📊 企業財務洞察與AI輔助決策平台")
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
        for chart_name, details in chart_requirements.items():
            required_cols = details["required"]
            if required_cols.issubset(df.columns):
                available_charts.append(chart_name)

        # --- Streamlit Sidebar for Chart Selection ---
        st.sidebar.header("📊 圖表選擇")
        if available_charts:
            chart_option = st.sidebar.selectbox("🔽 根據資料欄位選擇分析圖表：", sorted(available_charts))
        else:
            chart_option = None
            st.sidebar.warning("當前上傳的檔案沒有足夠的數據來生成任何建議的圖表。")
            
        # --- AI Chatbot Toggle ---
        st.sidebar.markdown("---")
        st.sidebar.header("💬 AI 聊天機器人")
        enable_chatbot = st.sidebar.checkbox("啟用 AI 聊天機器人", key="enable_chatbot")

        if enable_chatbot:
            st.sidebar.write("有任何問題，儘管問我！")
            
            # Display chat history
            for message in st.session_state.chat.history:
                role = "user" if message.role == "user" else "assistant"
                st.sidebar.text_area(f"{role.capitalize()}:", value=message.parts[0].text, height=70, disabled=True, key=f"chat_hist_{message.timestamp}")

            user_query = st.sidebar.text_input("您的問題：", key="chatbot_input")

            if user_query:
                with st.spinner("AI 思考中..."):
                    try:
                        response = st.session_state.chat.send_message(user_query)
                        st.sidebar.text_area("AI 回覆：", value=response.text, height=150, disabled=True, key=f"chat_resp_{response.timestamp}")
                    except Exception as e:
                        st.sidebar.error(f"聊天機器人錯誤: {e}")
                # Clear the input box after sending
                st.session_state.chatbot_input = "" # This might not immediately clear if the state isn't reset correctly on submit


        # --- Main Content Area for Charts ---
        if chart_option:
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
                        returns_data["5年回報率 (%)"] = company_data["Return over 5years"] # Corrected to existing col
                    
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
                                     color="Industry" if "Industry" in df.columns else None, # 如果有產業欄位，可以按產業區分顏色
                                     size="Market Capitalization" if "Market Capitalization" in df.columns else None, # 以市值大小區分點大小
                                     hover_data=["Industry", "Market Capitalization"] if "Industry" in df.columns and "Market Capitalization" in df.columns else None
                                     )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("沒有足夠的『Sales』或『Net profit』數據來繪製此圖。")

            elif chart_option == "平均股東權益報酬率排名（前20）":
                st.subheader("📊 平均股東權益報酬率排名 (前 20 名)")
                df_valid = df.dropna(subset=["Name", "Average return on equity 5Years"])
                if not df_valid.empty:
                    top_roe = df_valid.sort_values("Average return on equity 5Years", ascending=False).head(20)
                    fig = px.bar(top_roe,
                                 x="Name", y="Average return on equity 5Years",
                                 title="平均股東權益報酬率 (5 年) 前 20 名公司",
                                 text_auto=True,
                                 labels={"Average return on equity 5Years": "平均股東權益報酬率 (%)"})
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("沒有足夠的『Average return on equity 5Years』數據來進行排名。")

            elif chart_option == "發起人持股比例分佈（圓餅圖）":
                st.subheader("🤝 發起人持股比例分佈")
                
                # 檢查是否有足夠的公司來選擇
                company_list = df["Name"].dropna().unique().tolist()
                
                if company_list:
                    # 選項：平均或單一公司
                    holding_view_option = st.radio(
                        "選擇視圖方式：",
                        ("所有公司平均", "單一公司"),
                        key="holding_view_option"
                    )

                    if holding_view_option == "所有公司平均":
                        # 計算平均持股比例
                        avg_holdings = {}
                        required_holding_cols = ["Promoter holding", "FII holding", "DII holding", "Public holding"]
                        
                        # 檢查所有必要欄位是否存在且非空
                        can_plot_avg = True
                        for col in required_holding_cols:
                            if col not in df.columns or df[col].dropna().empty:
                                can_plot_avg = False
                                st.warning(f"缺少『{col}』數據或數據為空，無法計算所有公司平均持股比例。")
                                break
                        
                        if can_plot_avg:
                            avg_holdings["發起人持股"] = df["Promoter holding"].mean()
                            avg_holdings["FII持股"] = df["FII holding"].mean()
                            avg_holdings["DII持股"] = df["DII holding"].mean()
                            avg_holdings["公眾持股"] = df["Public holding"].mean()

                            plot_data = pd.DataFrame(avg_holdings.items(), columns=['持股類型', '比例']).dropna()
                            plot_data = plot_data[plot_data['比例'] > 0] # 移除比例為零的項目

                            if not plot_data.empty:
                                fig = px.pie(plot_data, values='比例', names='持股類型',
                                             title="所有公司平均持股比例分佈",
                                             hole=0.3)
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.warning("無法繪製平均持股比例圓餅圖，因為平均數據均為零或空。")
                    
                    elif holding_view_option == "單一公司":
                        selected_company = st.selectbox("請選擇公司", sorted(company_list), key="holding_pie_company")
                        company_data = df[df["Name"] == selected_company].iloc[0]

                        holdings_data = {}
                        if "Promoter holding" in company_data and pd.notna(company_data["Promoter holding"]):
                            holdings_data["發起人持股"] = company_data["Promoter holding"]
                        if "FII holding" in company_data and pd.notna(company_data["FII holding"]):
                            holdings_data["FII持股"] = company_data["FII holding"]
                        if "DII holding" in company_data and pd.notna(company_data["DII holding"]):
                            holdings_data["DII持股"] = company_data["DII holding"]
                        if "Public holding" in company_data and pd.notna(company_data["Public holding"]):
                            holdings_data["公眾持股"] = company_data["Public holding"]

                        plot_data = pd.DataFrame(holdings_data.items(), columns=['持股類型', '比例']).dropna()
                        plot_data = plot_data[plot_data['比例'] > 0] # 移除比例為零的項目

                        if not plot_data.empty:
                            fig = px.pie(plot_data, values='比例', names='持股類型',
                                         title=f"{selected_company} 持股比例分佈",
                                         hole=0.3)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning(f"公司 {selected_company} 沒有足夠的持股比例數據來繪製圓餅圖。")
                else:
                    st.warning("沒有可供選擇的公司或足夠的持股數據來繪製持股比例分佈圖。")

            # --- AI 財務分析 ---
            st.markdown("---")
            st.header("🤖 AI 財務分析")

            # Get the current selected company or default to the first available if any
            current_company_name = None
            # Check if a company was selected from any of the single-company charts
            # We need to check session_state or the current 'selected_company' local variable
            if 'asset_pie_company' in st.session_state and st.session_state.asset_pie_company:
                current_company_name = st.session_state.asset_pie_company
            elif 'sales_trend_company' in st.session_state and st.session_state.sales_trend_company:
                current_company_name = st.session_state.sales_trend_company
            elif 'profit_trend_company' in st.session_state and st.session_state.profit_trend_company:
                current_company_name = st.session_state.profit_trend_company
            elif 'eps_trend_company' in st.session_state and st.session_state.eps_trend_company:
                current_company_name = st.session_state.eps_trend_company
            elif 'roce_roe_company' in st.session_state and st.session_state.roce_roe_company:
                current_company_name = st.session_state.roce_roe_company
            elif 'cash_flow_pie_company' in st.session_state and st.session_state.cash_flow_pie_company:
                current_company_name = st.session_state.cash_flow_pie_company
            elif 'fcf_trend_company' in st.session_state and st.session_state.fcf_trend_company:
                current_company_name = st.session_state.fcf_trend_company
            elif 'price_trend_company' in st.session_state and st.session_state.price_trend_company:
                current_company_name = st.session_state.price_trend_company
            elif 'holding_pie_company' in st.session_state and st.session_state.holding_pie_company:
                current_company_name = st.session_state.holding_pie_company
            
            # Fallback to the first company if no specific company was selected through a chart
            elif "Name" in df.columns and not df["Name"].dropna().empty:
                current_company_name = df["Name"].dropna().unique().tolist()[0]


            if current_company_name:
                ai_analysis_prompt_template = """
                請根據以下公司 {company_name} 的財務數據，提供一份簡潔的財務分析報告。
                
                特別關注：
                1. 公司的整體財務健康狀況 (例如：流動性、償債能力)。
                2. 盈利能力表現。
                3. 成長趨勢。
                4. 任何值得注意的優勢或劣勢。
                5. 對於數據中顯示的任何異常或亮點進行解釋。
                
                以下是 {company_name} 的財務數據 (請忽略 'Name' 欄位，它僅用於識別公司)：
                {company_financial_data}
                
                如果提供的數據不足以進行全面分析，請明確指出哪些方面信息不足。
                請避免使用過於技術性的術語，並以條列式或段落式清晰呈現。
                """

                # Filter data for the selected company for AI analysis
                company_ai_data = df[df["Name"] == current_company_name].drop(columns=["Name"], errors='ignore').iloc[0].to_dict()
                
                # Convert numeric values to appropriate strings, handle NaN
                formatted_company_ai_data = {}
                for k, v in company_ai_data.items():
                    if pd.isna(v):
                        formatted_company_ai_data[k] = "無數據"
                    elif isinstance(v, (int, float)):
                        formatted_company_ai_data[k] = f"{v:,.2f}" # Format numbers with commas and 2 decimal places
                    else:
                        formatted_company_ai_data[k] = str(v)

                company_financial_data_str = "\n".join([f"{k}: {v}" for k, v in formatted_company_ai_data.items()])
                
                ai_prompt = ai_analysis_prompt_template.format(
                    company_name=current_company_name,
                    company_financial_data=company_financial_data_str
                )

                if st.button(f"生成 {current_company_name} 的 AI 財務分析報告"):
                    with st.spinner("AI 正在分析中，請稍候..."):
                        try:
                            response = gemini_model.generate_content(ai_prompt)
                            if response and response.text:
                                st.subheader(f"✨ {current_company_name} 的 AI 財務分析報告")
                                st.write(response.text)
                            else:
                                st.warning("AI 無法生成分析報告，請檢查數據或稍後再試。")
                        except Exception as e:
                            st.error(f"調用 AI 服務時發生錯誤: {e}")
            else:
                st.info("請先上傳包含公司名稱的數據，才能啟用 AI 財務分析。")
            
    except Exception as e:
        st.error(f"讀取或處理檔案時發生錯誤：{e}")
        st.info("請確保您上傳的是有效的 CSV 檔案，並且數據格式符合預期。")
else:
    st.info("請上傳 CSV 檔案以開始分析。")