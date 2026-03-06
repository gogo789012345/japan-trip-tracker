import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import yfinance as yf

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

@st.cache_data(ttl=3600)  # TTL=3600 代表每 3600 秒 (1 小時) 重新抓取一次
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

