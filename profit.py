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

# 2. DAFTAR MASTER PRODUK BAWAAN (Hanya dibuat jika file belum ada)
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

# --- FUNGSI UTAMA DATABASE MASTER PRODUK & HARGA ---
def muat_daftar_produk():
    """Memuat list produk saja dari file master"""
    if os.path.exists(DB_MASTER_PRODUK):
        df = pd.read_csv(DB_MASTER_PRODUK)
        return df["Produk"].tolist()
    else:
        df = pd.DataFrame({"Produk": PRODUK_DEFAULT})
        df.to_csv(DB_MASTER_PRODUK, index=False)
        return PRODUK_DEFAULT

def muat_database_harga():
    """Memuat tabel harga modal & jual berdasarkan master produk aktif"""
    daftar_produk_aktif = muat_daftar_produk()
    
    if os.path.exists(DB_HARGA):
        df = pd.read_csv(DB_HARGA)
        # Hapus produk di tabel harga jika sudah dihapus dari master produk
        df = df[df["Produk"].isin(daftar_produk_aktif)]
        # Tambah produk baru ke tabel harga jika belum terdaftar
        missing_products = [p for p in daftar_produk_aktif if p not in df["Produk"].values]
        if missing_products:
            new_rows = pd.DataFrame([{"Produk": p, "Harga Jual": 100000, "Harga Modal": 60000} for p in missing_products])
            df = pd.concat([df, new_rows], ignore_index=True)
            df.to_csv(DB_HARGA, index=False)
        return df
    else:
        default_data = [{"Produk": p, "Harga Jual": 100000, "Harga Modal": 60000} for p in daftar_produk_aktif]
        df = pd.DataFrame(default_data)
        df.to_csv(DB_HARGA, index=False)
        return df

def simpan_database_harga(df_baru):
    df_baru.to_csv(DB_HARGA, index=False)

def tambah_produk_baru(nama_baru, h_jual, h_modal):
    """Menambahkan produk baru ke file master dan mengeset harga awalnya"""
    daftar_produk = muat_daftar_produk()
    if nama_baru in daftar_produk:
        return False, "Nama produk sudah terdaftar di sistem!"
        
    # 1. Tambah ke master produk
    df_master = pd.DataFrame({"Produk": daftar_produk + [nama_baru]})
    df_master.to_csv(DB_MASTER_PRODUK, index=False)
    
    # 2. Tambah ke database harga
    df_harga = muat_database_harga()
    row_baru = pd.DataFrame([{"Produk": nama_baru, "Harga Jual": h_jual, "Harga Modal": h_modal}])
    df_harga = pd.concat([df_harga, row_baru], ignore_index=True)
    simpan_database_harga(df_harga)
    return True, f"Produk '{nama_baru}' sukses ditambahkan!"

def hapus_produk_by_name(nama_hapus):
    """Menghapus produk dari sistem master"""
    daftar_produk = muat_daftar_produk()
    if nama_hapus not in daftar_produk:
        return False
        
    daftar_produk.remove(nama_hapus)
    df_master = pd.DataFrame({"Produk": daftar_produk})
    df_master.to_csv(DB_MASTER_PRODUK, index=False)
    
    # Update tabel harga agar otomatis memotong baris produk tersebut
    muat_database_harga()
    return True

# --- FUNGSI DATABASE TRANSAKSI LOKAL ---
def muat_data_transaksi():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    else:
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

# --- RUNNING UTAMA ---
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
        st.warning("⚠️ Belum ada daftar produk di sistem. Silakan minta Owner untuk menambahkan produk terlebih dahulu di Tab 3.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🛍️ Detail Penjualan")
            platform_pilihan = st.selectbox("Pilih Platform Marketplace", options=list(KONS_MARKETPLACE.keys()))
            nama_produk = st.selectbox("Nama Produk / SKU", options=MASTER_PRODUK_AKTIF)
            
            info_produk = df_harga_aktif[df_harga_aktif["Produk"] == nama_produk].iloc[0]
            harga_jual_terkunci = int(info_produk["Harga Jual"])
            harga_modal_terkunci = int(info_produk["Harga Modal"])
            
            st.write(f"💵 **Harga Jual Hari Ini:** Rp {harga_jual_terkunci:,.0f}")
            st.write(f"📉 **Harga Modal Hari Ini:** Rp {harga_modal_terkunci:,.0f}")
            jumlah_terjual = st.number_input("Jumlah Terjual (pcs/pack)", min_value=1, value=1, key="jumlah")

        with col2:
            st.markdown("### 💸 Biaya Tambahan")
            biaya_lainnya = st.number_input("Biaya Lain-lain per Produk (Rp)", min_value=0, value=2000, key="lain")
            p_persen = KONS_MARKETPLACE[platform_pilihan]["persen"]
            p_fix = KONS_MARKETPLACE[platform_pilihan]["fix"]
            
            st.info(f"""
            **📋 Skema Potongan Admin Aktif ({platform_pilihan}):**
            * Biaya Admin Persen: **{p_persen}%** dari total omset.
            * Biaya Fix Transaksi: **Rp {p_fix:,.0f}** dipotong per transaksi.
            """)

        if st.button("💾 Simpan Transaksi Ke Database", type="primary", use_container_width=True):
            simpan_transaksi(platform_pilihan, nama_produk, harga_jual_terkunci, harga_modal_terkunci, jumlah_terjual, biaya_lainnya)
            st.success(f"✅ Transaksi [{platform_pilihan}] untuk '{nama_produk}' berhasil disimpan!")
            st.rerun()

# --- TAB 2: RIWAYAT & LAPORAN ---
with tab2:
    st.subheader("Riwayat & Analisis Penjualan")
    df_transaksi = muat_data_transaksi()
    
    if df_transaksi.empty:
        st.info("Belum ada data transaksi yang disimpan.")
    else:
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            hari_ini = datetime.now().date()
            rentang_tanggal = st.date_input("Pilih Rentang Tanggal Laporan", value=(hari_ini, hari_ini))
        with col_f2:
            opsi_filter_platform = ["Semua Platform"] + list(KONS_MARKETPLACE.keys())
            platform_terpilih = st.selectbox("Filter Berdasarkan Platform", options=opsi_filter_platform)
        with col_f3:
            opsi_filter_produk = ["Semua Produk"] + MASTER_PRODUK_AKTIF
            produk_terpilih = st.selectbox("Filter Berdasarkan Produk", options=opsi_filter_produk)
        
        if isinstance(rentang_tanggal, tuple) and len(rentang_tanggal) == 2:
            tgl_mulai, tgl_akhir = rentang_tanggal
            df_transaksi['Tanggal'] = pd.to_datetime(df_transaksi['Tanggal']).dt.date
            df_filtered = df_transaksi[(df_transaksi["Tanggal"] >= tgl_mulai) & (df_transaksi["Tanggal"] <= tgl_akhir)]
            
            if platform_terpilih != "Semua Platform":
                df_filtered = df_filtered[df_filtered["Platform"] == platform_terpilih]
