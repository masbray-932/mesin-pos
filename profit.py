import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIG ---
st.set_page_config(page_title="POS Multi-Marketplace", page_icon="🏪", layout="wide")

# --- KONEKSI GOOGLE SHEETS ---
def connect_sheets():
    creds_dict = dict(st.secrets["gcp"]) 
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    # Sesuaikan dengan nama Google Sheet kamu
    return client.open("Data_Transaksi_POS").sheet1

def muat_data(nama_sheet):
    try:
        sheet = connect_sheets()
        # Jika ingin muat database harga atau produk, sesuaikan nama sheet-nya
        return pd.DataFrame(sheet.get_all_records())
    except:
        return pd.DataFrame()

# --- LOGIKA INPUT ---
def simpan_transaksi(platform, toko, produk, harga_jual, harga_modal, jumlah, biaya_lain, tgl):
    # Logika perhitungan
    admin_rate = KONS_MARKETPLACE[platform]["persen"]
    admin_fix = KONS_MARKETPLACE[platform]["fix"]
    omset = harga_jual * jumlah
    admin_total = (admin_rate/100 * omset) + admin_fix
    profit = omset - ((harga_modal * jumlah) + admin_total + (biaya_lain * jumlah))
    
    row = [datetime.now().strftime("%H:%M:%S"), tgl.strftime("%Y-%m-%d"), platform, toko, produk, 
           harga_jual, harga_modal, jumlah, admin_total, admin_fix, biaya_lain*jumlah, omset, profit]
    connect_sheets().append_row(row)

# --- KONFIGURASI ---
KONS_MARKETPLACE = {"Shopee": {"persen": 12.5, "fix": 1250}, "Tokopedia": {"persen": 16.97, "fix": 0}, "TikTok Shop": {"persen": 8.0, "fix": 2000}, "Lazada": {"persen": 7.0, "fix": 1000}, "Offline / WA": {"persen": 0.0, "fix": 0}}
DAFTAR_TOKO = {"Shopee": ["Sinar Bintang Telur", "EGGKU", "Astra Telur", "Telur88"], "Tokopedia": ["Sinar Bintang Telur", "SB Telur", "Astra Telur"], "TikTok Shop": ["Utama"], "Lazada": ["Utama"], "Offline / WA": ["Toko Offline"]}
AKUN = {"owner": {"password": "owner123", "role": "Owner"}, "admin": {"password": "admin123", "role": "Admin"}}

# --- SISTEM LOGIN ---
if "login" not in st.session_state: st.session_state.login = False
if not st.session_state.login:
    u = st.text_input("Username").lower()
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u in AKUN and AKUN[u]["password"] == p:
            st.session_state.update({"login": True, "role": AKUN[u]["role"]}); st.rerun()
    st.stop()

# --- TAB APLIKASI ---
t1, t2 = st.tabs(["📥 Input", "📈 Riwayat"])

with t1:
    plat = st.selectbox("Platform", list(KONS_MARKETPLACE.keys()))
    toko = st.selectbox("Toko", DAFTAR_TOKO[plat])
    prod = st.text_input("Produk")
    hrg = st.number_input("Harga Jual", value=100000)
    qty = st.number_input("Jumlah", value=1)
    if st.button("Simpan"):
        simpan_transaksi(plat, toko, prod, hrg, 60000, qty, 0, datetime.now())
        st.success("Tersimpan di Google Sheets!")

with t2:
    df = muat_data_transaksi()
    if not df.empty:
        df.insert(0, "Hapus", False)
        editor = st.data_editor(df, use_container_width=True, hide_index=True, column_config={"Hapus": st.column_config.CheckboxColumn()})
        if st.button("❌ Hapus Terpilih"):
            hapus_list = [i for i, row in editor.iterrows() if row["Hapus"]]
            sheet = connect_sheets()
            for i in sorted(hapus_list, reverse=True): sheet.delete_rows(i + 2)
            st.rerun()
