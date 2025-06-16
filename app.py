import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="汽車銷售資料分析", layout="wide")
st.title("🚗 銷售資料分析儀表板")

uploaded_file = st.file_uploader("請上傳 CSV 檔案", type=["csv"])

def detect_date_column(df):
    for col in df.columns:
        if 'date' in col.lower():
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                if df[col].notna().sum() > 0:
                    return col
            except:
                continue
    for col in df.select_dtypes(include=['object', 'datetime']):
        try:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            if df[col].notna().sum() > 0:
                return col
        except:
            continue
    return None

def detect_price_column(df):
    for col in df.columns:
        if 'price' in col.lower():
            if pd.api.types.is_numeric_dtype(df[col]):
                return col
    numeric_cols = df.select_dtypes(include=['number']).columns
    for col in numeric_cols:
        if df[col].mean() > 100:  # 假設價格通常不會太小
            return col
    return None

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"讀取檔案錯誤：{e}")
        st.stop()

    # 自動偵測欄位
    date_col = detect_date_column(df)
    price_col = detect_price_column(df)

    if not date_col or not price_col:
        st.error(f"無法自動偵測欄位：{'缺少日期欄位' if not date_col else ''} {'與' if not date_col and not price_col else ''} {'缺少價格欄位' if not price_col else ''}")
        st.stop()

    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.rename(columns={date_col: "Date", price_col: "Price ($)"})
    df = df.dropna(subset=["Date", "Price ($)"])
    df["Year"] = df["Date"].dt.year

    st.markdown("## 📊 資料總覽")
    st.write(f"總資料筆數：**{len(df):,} 筆**")
    st.dataframe(df, use_container_width=True)

    st.divider()
    st.markdown("## 🔍 分析類型")

    selected_year = st.selectbox("選擇年份進行分析", sorted(df["Year"].unique(), reverse=True))
    filtered_df = df[df["Year"] == selected_year]

    tabs = st.tabs([
        "📈 銷售趨勢",
        "🏆 品牌排行",
        "🏪 經銷商排行",
        "👥 車型性別偏好",
        "💰 價格分布"
    ])

    with tabs[0]:
        st.markdown("### 📈 每日總銷售趨勢")
        trend = filtered_df.groupby("Date")["Price ($)"].sum()
        st.line_chart(trend)

    with tabs[1]:
        st.markdown("### 🏆 Top 10 品牌銷售額")
        if "Company" in df.columns:
            top_brands = filtered_df.groupby("Company")["Price ($)"].sum().sort_values(ascending=False).head(10)
            st.bar_chart(top_brands)
            st.markdown(f"🔎 **{top_brands.idxmax()}** 銷售額最高，達 **${top_brands.max():,.0f}**")
        else:
            st.warning("資料中沒有 'Company' 欄位")

    with tabs[2]:
        st.markdown("### 🏪 Top 10 經銷商銷售額")
        if "Dealer_Name" in df.columns:
            top_dealers = filtered_df.groupby("Dealer_Name")["Price ($)"].sum().sort_values(ascending=False).head(10)
            st.bar_chart(top_dealers)
            st.markdown(f"🏬 銷售最好的經銷商為 **{top_dealers.idxmax()}**，總銷售金額為 **${top_dealers.max():,.0f}**")
        else:
            st.warning("資料中沒有 'Dealer_Name' 欄位")

    with tabs[3]:
        st.markdown("### 👥 車型偏好分析（依性別）")
        if "Gender" in df.columns and "Model" in df.columns:
            pivot = filtered_df.pivot_table(index="Model", columns="Gender", values="Price ($)", aggfunc="sum").fillna(0)
            st.bar_chart(pivot)
            st.markdown("👫 顯示不同性別偏好的車型與消費結構。")
        else:
            st.warning("資料缺少 'Gender' 或 'Model' 欄位")

    with tabs[4]:
        st.markdown("### 💰 價格分布觀察")
        hist_df = pd.DataFrame({"Price": filtered_df["Price ($)"]})
        chart = alt.Chart(hist_df).mark_bar().encode(
            alt.X("Price:Q", bin=alt.Bin(maxbins=20), title="價格區間"),
            alt.Y("count():Q", title="數量")
        ).properties(width=800, height=400)
        st.altair_chart(chart, use_container_width=True)
        st.markdown("📉 觀察各價格區間的熱門程度")

else:
    st.info("請上傳 CSV 檔案以開始分析。")
