import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import yfinance as yf
import pandas as pd
import plotly.express as px


st.set_page_config(page_title="日本消費紀錄", page_icon="💴", layout="centered")

# --- 1. 建立高階密碼鎖 (主畫面版) ---

# 初始化登入狀態
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# 如果仲未登入，就顯示呢個登入畫面
if not st.session_state.authenticated:
    st.title("🔒 旅費記帳 App 已上鎖")
    st.info("為咗保護你嘅財務資料，請先輸入密碼。")
    
    # 喺主畫面顯示密碼框
    pwd = st.text_input("請輸入通行密碼：", type="password")
    
    if st.button("解鎖 🔓", use_container_width=True):
        if pwd == "tokyo2026":  # 呢度換成你想要嘅密碼
            st.session_state.authenticated = True
            st.rerun()  # 密碼啱，即刻重新載入畫面
        else:
            st.error("密碼錯誤，請再試一次！")
            
    st.stop()  # ⚠️ 呢行好重要！未登入之前，程式會喺度停低，絕對唔會行下面嘅 Code

# 可以在右上角加個登出掣 (Optional)
col1, col2 = st.columns([8, 2])
with col1:
    st.title("🇯🇵 日本旅費隨手記")
with col2:
    if st.button("登出"):
        st.session_state.authenticated = False
        st.rerun()

st.success("✅ 成功解鎖！")

# 頁面設定
st.set_page_config(page_title="日本消費紀錄", page_icon="💴")
st.title("🇯🇵 日本旅費隨手記")

# 連接 Google Sheets 的設定
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def init_connection():
    # 從 Streamlit secrets 讀取密鑰
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPE
    )
    client = gspread.authorize(credentials)
    return client

@st.cache_data(ttl=900)  # TTL=3600 代表每 3600 秒 (1 小時) 重新抓取一次
def get_realtime_rate():
    try:
        # JPYHKD=X 係 Yahoo Finance 裡面日圓兌港幣嘅代號
        # 如果你想計台幣，可以轉做 JPYTWD=X
        ticker = yf.Ticker("JPYHKD=X")
        # 獲取最近一日嘅歷史數據，並抽出收盤價
        todays_data = ticker.history(period="1d")
        current_rate = todays_data['Close'].iloc[0]
        return float(current_rate)
    except Exception as e:
        # 如果因為網絡問題拎唔到，就用一個預設安全匯率頂住先
        st.warning("⚠️ 暫時無法獲取即時匯率，將使用預設匯率。")
        return 0.052

# 換成你自己的 Google Sheet 名稱
SHEET_NAME = "tokyo052026" 
EXCHANGE_RATE = get_realtime_rate()  # 假設匯率，可自行調整

# 你可以喺畫面上顯示埋俾自己睇
st.caption(f"📈 目前系統匯率：1 JPY = {EXCHANGE_RATE:.4f} HKD (每小時自動更新)")
try:
    client = init_connection()
    sheet = client.open(SHEET_NAME).sheet1
except Exception as e:
    st.error(f"無法連接 Google Sheets，請檢查設定: {e}")
    st.stop()

# --- 輸入表單 ---
with st.form("expense_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("日期", datetime.now())
        category = st.selectbox("類別", ["飲食", "交通", "住宿", "購物", "娛樂", "其他"])
    with col2:
        item = st.text_input("項目 (例: 松本城門票、東京車站便當)", placeholder="輸入消費項目")
        jpy_amount = st.number_input("日圓 (JPY)", min_value=0, step=100)
    
    note = st.text_area("備註 (選填)")
    submitted = st.form_submit_button("新增紀錄", use_container_width=True)
    
    if submitted:
        if jpy_amount == 0 or not item:
            st.warning("請填寫項目名稱同金額！")
        else:
            # 計算當地貨幣 (例如 TWD/HKD)
            local_amount = round(jpy_amount * EXCHANGE_RATE, 2)
            
            # 準備寫入的一行資料
            row_data = [
                date.strftime("%Y-%m-%d"), 
                category, 
                item, 
                jpy_amount, 
                local_amount, 
                note
            ]
            
            # 寫入 Google Sheets
            sheet.append_row(row_data)
            st.success(f"✅ 成功紀錄！【{item}】 ¥{jpy_amount} (約 ${local_amount})")

            st.balloons()

st.divider() # 加條分隔線
st.header("📊 旅費數據分析")

# 1. 從 Google Sheets 獲取所有資料
try:
    # get_all_records() 會將有表頭嘅資料自動轉成 List of Dictionaries
    records = sheet.get_all_records()
    
    if records:
        df = pd.DataFrame(records)
        
        # 確保金額欄位係數字格式
        df['JPY_Amount'] = pd.to_numeric(df['JPY_Amount'], errors='coerce')
        df['Local_Amount'] = pd.to_numeric(df['Local_Amount'], errors='coerce')
        
        # --- 顯示目前總花費 ---
        total_jpy = df['JPY_Amount'].sum()
        total_local = df['Local_Amount'].sum()
        
        # 用 st.metric 顯示超大字體嘅 KPI 數字
        col1, col2 = st.columns(2)
        col1.metric("目前總花費 (日圓 💴)", f"¥ {total_jpy:,.0f}")
        col2.metric("目前總花費 (約合港幣 🇭🇰)", f"$ {total_local:,.2f}")
        
        # --- 計算並顯示各類別百分比 (%) ---
        st.subheader("各類別消費佔比")
        
        # 用 Pandas Groupby 將各類別嘅日圓總數加埋
        category_sum = df.groupby('Category')['JPY_Amount'].sum().reset_index()
        
        # 用 Plotly 畫一個互動式圓餅圖 (Pie Chart)
        fig = px.pie(
            category_sum, 
            values='JPY_Amount', 
            names='Category',
            hole=0.4, # 變成甜甜圈圖，靚啲
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        
        # 隱藏圖表背景，配合 Streamlit 主題
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0)) 
        
        # 將圖表顯示喺網頁上
        st.plotly_chart(fig, use_container_width=True)
        
        # 如果你想睇埋每筆詳細紀錄，可以加個 Expander 隱藏住個 Table
        with st.expander("📝 查看所有詳細紀錄"):
            st.dataframe(df, use_container_width=True)
            
    else:
        st.info("目前仲未有任何消費紀錄，快啲記低第一筆啦！")
        
except Exception as e:
    st.error(f"無法讀取數據: {e}")



