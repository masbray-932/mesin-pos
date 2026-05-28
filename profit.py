import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# Pengaturan judul halaman web
st.set_page_config(page_title="POS Multi-Marketplace & Manajemen Harga", page_icon="🏪", layout="wide")

# Nama file database lokal
DB_FILE = "database_transaksi.csv"
DB_HARGA = "database_harga.csv"
DB_MASTER_PRODUK = "database_master_produk.csv"
DB_SESSION = "database_session.txt"

# 1. DATA LOGIN AKUN
AKUN_USER = {
    "owner": {"password": "owner123", "role": "Owner"},
    "admin": {"password": "admin123", "role": "Admin"}
}

# 2. DAFTAR MASTER PRODUK BAWAAN
PRODUK_DEFAULT = [
    "Ayam Kampung Omega", "Ayam Kampung Omega Grade A", "Ayam Negri", 
    "Ayam Negri Omega", "Ayam Kampung Kuning", "Ayam Kampung Kuning Grade A", 
    "Puyuh", "Bebek", "Bebek Asin", "Kampung Omega (30 butir)", "Kampung Omega Grade A (30 butir)"
]

# 3. DICTIONARY BIAYA ADMIN PER MARKETPLACE
KONS_MARKETPLACE = {
    "Shopee": {"persen": 12.50, "fix": 1250},
    "Tokopedia": {"persen": 16.97, "fix": 0},
    "TikTok Shop": {"persen": 8.00, "fix": 2000},
    "Lazada": {"persen": 7.00, "fix": 1000},
    "Offline / WA": {"persen": 0.00, "fix": 0}
}

# 4. PEMETAAN DAFTAR TOKO
DAFTAR_TOKO_PLATFORM = {
    "Shopee": ["Sinar Bintang Telur", "EGGKU", "Astra Telur", "Telur88"],
    "Tokopedia": ["Sinar Bintang Telur", "SB Telur", "Astra Telur"],
    "TikTok Shop": ["Utama"],
    "Lazada": ["Utama"],
    "Offline / WA": ["Toko Offline"]
}

# --- FUNGSI DATABASE ---
def muat_daftar_produk():
    if os.path.exists(DB_MASTER_PRODUK):
        try:
            df = pd.read_csv(DB_MASTER_PRODUK)
            return df["Produk"].dropna().astype(str).str.strip().unique().tolist()
        except: pass
    df = pd.DataFrame({"Produk": PRODUK_DEFAULT})
    df.to_csv(DB_MASTER_PRODUK, index=False)
    return PRODUK_DEFAULT

def muat_database_harga():
    daftar = muat_daftar_produk()
    if os.path.exists(DB_HARGA):
        try:
            df = pd.read_csv(DB_HARGA)
            return df
        except: pass
    df = pd.DataFrame([{"Produk": p, "Harga Jual": 100000, "Harga Modal": 60000} for p in daftar])
    df.to_csv(DB_HARGA, index=False)
    return df

def muat_data_transaksi():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["Waktu", "Tanggal", "Platform", "Toko", "Produk", "Harga Jual", "Harga Modal", "Jumlah", "Biaya Admin %", "Biaya Fix", "Biaya Lain", "Total Omset", "Total Profit"])

def simpan_transaksi(platform, toko, produk, harga_jual, harga_modal, jumlah, biaya_lain, tanggal_pilihan):
    df = muat_data_transaksi()
    waktu_jkt = datetime.utcnow() + timedelta(hours=7)
    
    data_baru = pd.DataFrame([{
        "Waktu": waktu_jkt.strftime("%H:%M:%S"), 
        "Tanggal": tanggal_pilihan.strftime("%Y-%m-%d"), 
        "Platform": platform, "Toko": toko, "Produk": produk,
        "Harga Jual": harga_jual, "Harga Modal": harga_modal, "Jumlah": jumlah,
        "Biaya Admin %": (KONS_MARKETPLACE[platform]["persen"]/100) * (harga_jual*jumlah), 
        "Biaya Fix": KONS_MARKETPLACE[platform]["fix"], 
        "Biaya Lain": biaya_lain * jumlah,
        "Total Omset": harga_jual * jumlah, 
        "Total Profit": (harga_jual * jumlah) - ((harga_modal * jumlah) + ((KONS_MARKETPLACE[platform]["persen"]/100)*(harga_jual*jumlah)) + KONS_MARKETPLACE[platform]["fix"] + (biaya_lain * jumlah))
    }])
    df = pd.concat([df, data_baru], ignore_index=True)
    df.to_csv(DB_FILE, index=False)

# --- SISTEM LOGIN ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in and os.path.exists(DB_SESSION):
    try:
        with open(DB_SESSION, "r") as f:
            user, role = f.read().split(",")
            st.session_state.update({"logged_in": True, "username": user, "user_role": role})
    except: pass

if not st.session_state.logged_in:
    with st.form("login"):
        user = st.text_input("Username").lower()
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Masuk"):
            if user in AKUN_USER and AKUN_USER[user]["password"] == pwd:
                st.session_state.update({"logged_in": True, "username": user, "user_role": AKUN_USER[user]["role"]})
                with open(DB_SESSION, "w") as f: f.write(f"{user},{AKUN_USER[user]['role']}")
                st.rerun()
    st.stop()

# --- SIDEBAR & TABS ---
with st.sidebar:
    st.write(f"User: {st.session_state.username} ({st.session_state.user_role})")
    if st.button("Logout"):
        if os.path.exists(DB_SESSION): os.remove(DB_SESSION)
        st.rerun()

t1, t2, t3, t4 = st.tabs(["📥 Input", "📈 Riwayat", "⚙️ Produk", "🧮 Kalkulator"])

with t1:
    col1, col2 = st.columns(2)
    with col1:
        tgl = st.date_input("Tanggal", datetime.utcnow() + timedelta(hours=7))
        plat = st.selectbox("Platform", list(KONS_MARKETPLACE.keys()))
        toko = st.selectbox("Toko", DAFTAR_TOKO_PLATFORM[plat])
        prod = st.selectbox("Produk", muat_daftar_produk())
        h_jual = st.number_input("Harga Jual", value=100000, step=1000)
        h_modal = st.number_input("Harga Modal", value=60000, step=1000)
        qty = st.number_input("Qty", value=1)
    with col2:
        lain = st.number_input("Biaya Lain per Pcs", value=0)
    if st.button("Simpan Transaksi"):
        simpan_transaksi(plat, toko, prod, h_jual, h_modal, qty, lain, tgl)
        st.success("Tersimpan!")

with t2:
    df = muat_data_transaksi()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else: st.info("Belum ada data.")

with t3:
    st.write("Gunakan menu Kelola Produk di versi sebelumnya untuk edit harga modal/jual.")
    st.dataframe(muat_database_harga(), use_container_width=True)

with t4:
    st.subheader("Kalkulator Profit Massal")
    plat_k = st.selectbox("Platform Simulasi", list(KONS_MARKETPLACE.keys()))
    df_sim = muat_database_harga()
    df_sim["Qty"] = 1
    df_sim["Admin %"] = float(KONS_MARKETPLACE[plat_k]["persen"])
    df_sim["Packing"] = 0
    df_sim["Lain-lain"] = 0
    
    edited = st.data_editor(df_sim, disabled=["Produk", "Harga Modal"], use_container_width=True)
    
    # Perhitungan Live
    omset = edited["Harga Jual"] * edited["Qty"]
    admin = (edited["Admin %"]/100) * omset
    total_peng = (edited["Harga Modal"] * edited["Qty"]) + admin + (edited["Packing"] * edited["Qty"]) + (edited["Lain-lain"] * edited["Qty"])
    profit = omset - total_peng
    
    res = pd.DataFrame({
        "Produk": edited["Produk"],
        "Omset": omset,
        "Profit": profit,
        "Margin (%)": (profit/omset)*100
    })
    st.dataframe(res, use_container_width=True)
