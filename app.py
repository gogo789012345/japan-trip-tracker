import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

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

# 換成你自己的 Google Sheet 名稱
SHEET_NAME = "Japan_Trip_2026" 
EXCHANGE_RATE = 0.21  # 假設匯率，可自行調整

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