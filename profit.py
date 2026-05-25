import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Pengaturan judul halaman web
st.set_page_config(page_title="POS Multi-Marketplace & Manajemen Harga", page_icon="🏪", layout="wide")

# Nama file database lokal
DB_FILE = "database_transaksi.csv"
DB_HARGA = "database_harga.csv"
DB_MASTER_PRODUK = "database_master_produk.csv"

# 1. DATA LOGIN AKUN
AKUN_USER = {
    "owner": {"password": "owner123", "role": "Owner"},
    "admin": {"password": "admin123", "role": "Admin"}
}

# 2. DAFTAR MASTER PRODUK BAWAAN (Otomatis dibuat jika sistem kosong)
PRODUK_DEFAULT = [
    "Ayam Kampung Omega", 
    "Ayam Kampung Omega Grade A", 
    "Ayam Negri", 
    "Ayam Negri Omega", 
    "Ayam Kampung Kuning", 
    "Ayam Kampung Kuning Grade A", 
    "Puyuh", 
    "Bebek", 
    "Bebek Asin", 
    "Kampung Omega (30 butir)", 
    "Kampung Omega Grade A (30 butir)"
]

# 3. DICTIONARY BIAYA ADMIN PER MARKETPLACE
KONS_MARKETPLACE = {
    "Shopee": {"persen": 12.50, "fix": 1250},
    "Tokopedia": {"persen": 16.97, "fix": 0},
    "TikTok Shop": {"persen": 8.00, "fix": 2000},
    "Lazada": {"persen": 7.00, "fix": 1000},
    "Offline / WA": {"persen": 0.00, "fix": 0}
}

# --- FUNGSI DETEKSI & MUAT DATABASE (ANTI-KOSONG AUTOMATION) ---
def muat_daftar_produk():
    """Memuat list produk. Jika file kosong/tidak ada, langsung diisi default otomatis"""
    if os.path.exists(DB_MASTER_PRODUK):
        try:
            df = pd.read_csv(DB_MASTER_PRODUK)
            if not df.empty and "Produk" in df.columns:
                return df["Produk"].dropna().tolist()
        except Exception:
            pass
            
    # Jika file rusak/kosong, buat baru dengan data default
    df = pd.DataFrame({"Produk": PRODUK_DEFAULT})
    df.to_csv(DB_MASTER_PRODUK, index=False)
    return PRODUK_DEFAULT

def muat_database_harga():
    """Memuat tabel harga modal & jual. Jika kosong, langsung disinkronkan otomatis"""
    daftar_produk_aktif = muat_daftar_produk()
    
    if os.path.exists(DB_HARGA):
        try:
            df = pd.read_csv(DB_HARGA)
            if not df.empty and "Produk" in df.columns:
                # Sinkronisasi: Buang produk yang sudah dihapus dari master
                df = df[df["Produk"].isin(daftar_produk_aktif)]
                # Sinkronisasi: Tambah produk baru yang belum ada di tabel harga
                missing_products = [p for p in daftar_produk_aktif if p not in df["Produk"].values]
                if missing_products:
                    new_rows = pd.DataFrame([{"Produk": p, "Harga Jual": 100000, "Harga Modal": 60000} for p in missing_products])
                    df = pd.concat([df, new_rows], ignore_index=True)
                    df.to_csv(DB_HARGA, index=False)
                return df
        except Exception:
            pass
            
    # Jika file harga kosong/rusak, generate ulang berdasarkan daftar produk aktif
    default_data = [{"Produk": p, "Harga Jual": 100000, "Harga Modal": 60000} for p in daftar_produk_aktif]
    df = pd.DataFrame(default_data)
    df.to_csv(DB_HARGA, index=False)
    return df

def simpan_database_harga(df_baru):
    df_baru.to_csv(DB_HARGA, index=False)

def tambah_produk_baru(nama_baru, h_jual, h_modal):
    daftar_produk = muat_daftar_produk()
    if nama_baru in daftar_produk:
        return False, "Nama produk sudah terdaftar di sistem!"
        
    df_master = pd.DataFrame({"Produk": daftar_produk + [nama_baru]})
    df_master.to_csv(DB_MASTER_PRODUK, index=False)
    
    df_harga = muat_database_harga()
    row_baru = pd.DataFrame([{"Produk": nama_baru, "Harga Jual": h_jual, "Harga Modal": h_modal}])
    df_harga = pd.concat([df_harga, row_baru], ignore_index=True)
    simpan_database_harga(df_harga)
    return True, f"Produk '{nama_baru}' sukses ditambahkan!"

def hapus_produk_by_name(nama_hapus):
    daftar_produk = muat_daftar_produk()
    if nama_hapus not in daftar_produk:
        return False
        
    daftar_produk.remove(nama_hapus)
    df_master = pd.DataFrame({"Produk": daftar_produk})
    df_master.to_csv(DB_MASTER_PRODUK, index=False)
    
    # Generate ulang tabel harga agar baris produk terhapus langsung hilang
    df_harga = muat_database_harga()
    df_harga = df_harga[df_harga["Produk"] != nama_hapus]
    simpan_database_harga(df_harga)
    return True

# --- FUNGSI DATABASE TRANSAKSI LOKAL ---
def muat_data_transaksi():
    if os.path.exists(DB_FILE):
        try:
            return pd.read_csv(DB_FILE)
        except Exception:
            pass
    return pd.DataFrame(columns=["Waktu", "Tanggal", "Platform", "Produk", "Harga Jual", "Harga Modal", "Jumlah", "Biaya Admin %", "Biaya Fix", "Biaya Lain", "Total Omset", "Total Profit"])

def simpan_transaksi(platform, produk, harga_jual, harga_modal, jumlah, biaya_lain):
    df = muat_data_transaksi()
    waktu_sekarang = datetime.now()
    tanggal = waktu_sekarang.strftime("%Y-%m-%d")
    jam = waktu_sekarang.strftime("%H:%M:%S")
    
    admin_persen_rate = KONS_MARKETPLACE[platform]["persen"]
    admin_fix_rate = KONS_MARKETPLACE[platform]["fix"]
    
    total_omset = harga_jual * jumlah
    total_modal = harga_modal * jumlah
    total_admin_persen = (admin_persen_rate / 100) * total_omset
    total_biaya_lain = biaya_lain * jumlah
    
    total_pengeluaran = total_modal + total_admin_persen + admin_fix_rate + total_biaya_lain
    total_profit = total_omset - total_pengeluaran
    
    data_baru = pd.DataFrame([{
        "Waktu": jam, "Tanggal": tanggal, "Platform": platform, "Produk": produk,
        "Harga Jual": harga_jual, "Harga Modal": harga_modal, "Jumlah": jumlah,
        "Biaya Admin %": total_admin_persen, "Biaya Fix": admin_fix_rate, "Biaya Lain": total_biaya_lain,
        "Total Omset": total_omset, "Total Profit": total_profit
    }])
    
    df = pd.concat([df, data_baru], ignore_index=True)
    df.to_csv(DB_FILE, index=False)

def hapus_transaksi_by_index(index_yang_dihapus):
    df = muat_data_transaksi()
    if index_yang_dihapus in df.index:
        df = df.drop(index_yang_dihapus)
        df.to_csv(DB_FILE, index=False)
        return True
    return False

# --- LOGIKA SISTEM LOGIN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🔐 Login Sistem Kasir POS</h2>", unsafe_allow_html=True)
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        with st.form("form_login"):
            username_input = st.text_input("Username").strip().lower()
            password_input = st.text_input("Password", type="password")
            tombol_login = st.form_submit_button("Masuk ke Sistem", use_container_width=True)
            
            if tombol_login:
                if username_input in AKUN_USER and AKUN_USER[username_input]["password"] == password_input:
                    st.session_state.logged_in = True
                    st.session_state.user_role = AKUN_USER[username_input]["role"]
                    st.session_state.username = username_input
                    st.success(f"🎉 Login Berhasil sebagai {st.session_state.user_role}!")
                    st.rerun()
                else:
                    st.error("❌ Username atau Password salah, silakan cek kembali!")
    st.stop()

# --- AMBIL DATA AKTIF (AUTO REPAIR JIKA KOSONG) ---
MASTER_PRODUK_AKTIF = muat_daftar_produk()
df_harga_aktif = muat_database_harga()

# Membuat Sidebar
with st.sidebar:
    st.markdown(f"### 👤 Akun Aktif")
    st.write(f"**Username:** `{st.session_state.username}`")
    st.info(f"**Akses Jaringan:** {st.session_state.user_role}")
    st.markdown("---")
    if st.button("🚪 Keluar / Logout", type="secondary", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.username = ""
        st.rerun()

st.title("🏪 MESIN POS MULTI-MARKETPLACE")
st.write(f"Selamat bekerja, **{st.session_state.user_role}**! Data tersinkronisasi otomatis.")

tab1, tab2, tab3 = st.tabs(["📥 Input Transaksi Baru", "📈 Riwayat & Laporan Penjualan", "⚙️ Kelola Manajemen Produk & Harga"])

# --- TAB 1: INPUT TRANSAKSI ---
with tab1:
    st.subheader("Tambah Transaksi Baru")
    if not MASTER_PRODUK_AKTIF:
        st.warning("⚠️ Belum ada daftar produk di sistem.")
    else:
        col1, col2 = st.columns(2)
