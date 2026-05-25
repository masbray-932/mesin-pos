import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Pengaturan judul halaman web
st.set_page_config(page_title="POS Multi-Marketplace & Manajemen Harga", page_icon="🏪", layout="wide")

# Nama file database lokal
DB_FILE = "database_transaksi.csv"
DB_HARGA = "database_harga.csv"

# 1. DATA LOGIN AKUN (Silakan ubah username & password tokomu di sini, Bestie)
AKUN_USER = {
    "owner": {"password": "owner123", "role": "Owner"},
    "admin": {"password": "admin123", "role": "Admin"}
}

# 2. DAFTAR MASTER PRODUK
MASTER_PRODUK = [
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

# --- FUNGSI DATABASE HARGA LOKAL ---
def muat_database_harga():
    if os.path.exists(DB_HARGA):
        df = pd.read_csv(DB_HARGA)
        missing_products = [p for p in MASTER_PRODUK if p not in df["Produk"].values]
        if missing_products:
            new_rows = pd.DataFrame([{"Produk": p, "Harga Jual": 100000, "Harga Modal": 60000} for p in missing_products])
            df = pd.concat([df, new_rows], ignore_index=True)
            df.to_csv(DB_HARGA, index=False)
        return df
    else:
        default_data = [{"Produk": p, "Harga Jual": 100000, "Harga Modal": 60000} for p in MASTER_PRODUK]
        df = pd.DataFrame(default_data)
        df.to_csv(DB_HARGA, index=False)
        return df

def simpan_database_harga(df_baru):
    df_baru.to_csv(DB_HARGA, index=False)

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
        "Waktu": jam,
        "Tanggal": tanggal,
        "Platform": platform,
        "Produk": produk,
        "Harga Jual": harga_jual,
        "Harga Modal": harga_modal,
        "Jumlah": jumlah,
        "Biaya Admin %": total_admin_persen,
        "Biaya Fix": admin_fix_rate,
        "Biaya Lain": total_biaya_lain,
        "Total Omset": total_omset,
        "Total Profit": total_profit
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

# JIKA BELUM LOGIN, TAMPILKAN HALAMAN LOGIN
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
    st.stop() # Menghentikan sisa kode di bawah agar tidak dimuat sebelum login sukses

# --- JIKA SUDAH LOGIN, TAMPILKAN HALAMAN KASIR UTAMA ---
df_harga_aktif = muat_database_harga()

# Membuat Sidebar untuk informasi akun & tombol Logout
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

# PENGATURAN TAB BERDASARKAN HAK AKSES ROLE
# Jika Owner: Muncul 3 Tab lengkap. Jika Admin: Cuma muncul 2 Tab awal
if st.session_state.user_role == "Owner":
    tab1, tab2, tab3 = st.tabs(["📥 Input Transaksi Baru", "📈 Riwayat & Laporan Penjualan", "⚙️ Atur Harga Modal & Jual Hari Ini"])
else:
    tab1, tab2 = st.tabs(["📥 Input Transaksi Baru", "📈 Riwayat & Laporan Penjualan"])

# --- TAB 1: INPUT TRANSAKSI (Bisa diakses Owner & Admin) ---
with tab1:
    st.subheader("Tambah Transaksi Baru")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🛍️ Detail Penjualan")
        platform_pilihan = st.selectbox("Pilih Platform Marketplace", options=list(KONS_MARKETPLACE.keys()))
        nama_produk = st.selectbox("Nama Produk / SKU", options=MASTER_PRODUK)
        
        info_produk = df_harga_aktif[df_harga_aktif["Produk"] == nama_produk].iloc[0]
        harga_jual_terkunci = int(info_produk["Harga Jual"])
        harga_modal_terkunci = int(info_produk["Harga Modal"])
        
        st.write(f"💵 **Harga Jual Hari Ini:** Rp {harga_jual_terkunci:,.0f}")
        
        # Sembunyikan informasi Harga Modal dari pandangan Admin (Hanya Owner yang bisa lihat)
        if st.session_state.user_role == "Owner":
            st.write(f"📉 **Harga Modal Hari Ini:** Rp {harga_modal_terkunci:,.0f}")
            
        jumlah_terjual = st.number_input("Jumlah Terjual (pcs/pack)", min_value=1, value=1, key="jumlah")

    with col2:
        st.markdown("### 💸 Biaya Tambahan")
        biaya_lainnya = st.number_input("Biaya Lain-lain per Produk (Rp)", min_value=0, value=2000, key="lain")
        
        p_persen = KONS_MARKETPLACE[platform_pilihan]["percent" if "percent" in KONS_MARKETPLACE[platform_pilihan] else "persen"]
        p_fix = KONS_MARKETPLACE[platform_pilihan]["fix"]
        
        # Sembunyikan skema potongan admin persen marketplace dari Admin agar mereka tidak bisa menebak profit bersih
        if st.session_state.user_role == "Owner":
            st.info(f"""
            **📋 Skema Potongan Admin Aktif ({platform_pilihan}):**
            * Biaya Admin Persen: **{p_persen}%** dari total omset.
            * Biaya Fix Transaksi: **Rp {p_fix:,.0f}** dipotong per transaksi.
            """)
        else:
            st.info(f"ℹ️ Sistem otomatis memotong biaya administrasi khusus untuk platform **{platform_pilihan}**.")

    if st.button("💾 Simpan Transaksi Ke Database", type="primary", use_container_width=True):
        simpan_transaksi(platform_pilihan, nama_produk, harga_jual_terkunci, harga_modal_terkunci, jumlah_terjual, biaya_lainnya)
        st.success(f"✅ Transaksi [{platform_pilihan}] untuk '{nama_produk}' berhasil disimpan!")
        st.rerun()

# --- TAB 2: RIWAYAT & LAPORAN (PROTEKSI PRIVASI PROFIT) ---
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
            opsi_filter_produk = ["Semua Produk"] + MASTER_PRODUK
            produk_terpilih = st.selectbox("Filter Berdasarkan Produk", options=opsi_filter_produk)
        
        if isinstance(rentang_tanggal, tuple) and len(rentang_tanggal) == 2:
            tgl_mulai, tgl_akhir = rentang_tanggal
            df_transaksi['Tanggal'] = pd.to_datetime(df_transaksi['Tanggal']).dt.date
            df_filtered = df_transaksi[(df_transaksi["Tanggal"] >= tgl_mulai) & (df_transaksi["Tanggal"] <= tgl_akhir)]
            
            if platform_terpilih != "Semua Platform":
                df_filtered = df_filtered[df_filtered["Platform"] == platform_terpilih]
            if produk_terpilih != "Semua Produk":
                df_filtered = df_filtered[df_filtered["Produk"] == produk_terpilih]
                
            if df_filtered.empty:
                st.warning(f"Tidak ada transaksi yang cocok pada filter terpilih.")
            else:
                # HITUNG RINGKASAN METRIK BERDASARKAN HAK AKSES ROLE
                total_omset = df_filtered["Total Omset"].sum()
                total_profit = df_filtered["Total Profit"].sum()
                total_barang_terjual = df_filtered["Jumlah"].sum()
                
                if st.session_state.user_role == "Owner":
                    # Tampilan Owner: Muncul 3 kartu lengkap beserta profit bersih
                    m1, m2, m3 = st.columns(3)
                    m1.metric(label="Total Omset Terfilter", value=f"Rp {total_omset:,.0f}")
                    m2.metric(label="Total Keuntungan Bersih (Profit)", value=f"Rp {total_profit:,.0f}")
                    m3.metric(label="Total Produk Terjual", value=f"{total_barang_terjual} pcs")
                else:
                    # Tampilan Admin: Cuma muncul 2 kartu saja (Keuntungan bersih disembunyikan!)
                    m1, m2 = st.columns(2)
                    m1.metric(label="Total Omset Terfilter", value=f"Rp {total_omset:,.0f}")
                    m2.metric(label="Total Produk Terjual", value=f"{total_barang_terjual} pcs")
                
                # FITUR KOREKSI / HAPUS DATA (Hanya boleh dioperasikan oleh Owner)
                st.markdown("---")
                if st.session_state.user_role == "Owner":
                    st.markdown("### ✏️ Koreksi / Hapus Transaksi")
                    id_hapus = st.number_input("Masukkan ID baris data:", min_value=0, step=1, value=0)
                    if st.button("❌ Hapus Baris Ini", type="secondary"):
                        if id_hapus in df_filtered.index:
                            if hapus_transaksi_by_index(id_hapus):
                                st.success(f"💥 Baris ID {id_hapus} berhasil dihapus!")
                                st.rerun()
                        else:
                            st.error(f"ID {id_hapus} tidak ditemukan!")
                    st.markdown("---")
                
                # FILTER TABEL PILIHAN YANG DITAMPILKAN KE KASIR/ADMIN
                if st.session_state.user_role == "Admin":
                    # Potong kolom rahasia sebelum tabel dilempar ke pandangan kasir
                    kolom_kasir = ["Waktu", "Tanggal", "Platform", "Produk", "Harga Jual", "Jumlah", "Biaya Lain", "Total Omset"]
                    df_tampilan_kasir = df_filtered[kolom_kasir]
                    st.dataframe(df_tampilan_kasir, use_container_width=True)
                else:
                    # Owner bebas melihat isi tabel mentah lengkap dengan HPP dan biaya potongan adminnya
                    st.dataframe(df_filtered, use_container_width=True)
                
                # Tombol Download Laporan (Bisa diakses Owner & Admin untuk arsip)
                if st.session_state.user_role == "Owner":
                    csv_data = df_filtered.to_csv(index=False).encode('utf-8')
                else:
                    csv_data = df_tampilan_kasir.to_csv(index=False).encode('utf-8')
                    
                st.download_button(
                    label="📥 Download & Ekspor Laporan Penjualan (CSV)",
                    data=csv_data,
                    file_name=f"laporan_pos_{st.session_state.user_role.lower()}.csv",
                    mime="text/csv",
                )

# --- TAB 3: ATUR HARGA (HANYA BISA DIAKSES OLEH OWNER) ---
if st.session_state.user_role == "Owner":
    with tab3:
        st.subheader("⚙️ Update Harga Modal & Jual Pasar Hari Ini")
        st.info("💡 Klik langsung pada angka, ubah nilainya, lalu klik tombol simpan di bawah.")
        
        df_editor = st.data_editor(
            df_harga_aktif, 
            disabled=["Produk"], 
            use_container_width=True,
            key="editor_harga",
            column_config={
                "Harga Jual": st.column_config.NumberColumn("Harga Jual (Rp)", min_value=0, format="%d"),
                "Harga Modal": st.column_config.NumberColumn("Harga Modal (Rp)", min_value=0, format="%d")
            }
        )
        
        if st.button("💾 Simpan Perubahan Harga", type="primary", use_container_width=True):
            simpan_database_harga(df_editor)
            st.success("🎉 Harga harian berhasil diperbarui ke dalam sistem!")
            st.rerun()
