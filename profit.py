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

# ==========================================
# 🔥 PROTEKSI HARD RESET JIKA FILE CORRUPT
# ==========================================
def validasi_dan_bersihkan_file(nama_file, kolom_wajib):
    if os.path.exists(nama_file):
        try:
            df = pd.read_csv(nama_file)
            if df.empty or not all(k in df.columns for k in kolom_wajib):
                os.remove(nama_file)
        except Exception:
            try:
                os.remove(nama_file)
            except Exception:
                pass

validasi_dan_bersihkan_file(DB_MASTER_PRODUK, ["Produk"])
validasi_dan_bersihkan_file(DB_HARGA, ["Produk", "Harga Jual", "Harga Modal"])
# ==========================================

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

# --- FUNGSI DETEKSI & MUAT DATABASE PRO LEVEL ---
def muat_daftar_produk():
    if os.path.exists(DB_MASTER_PRODUK):
        try:
            df = pd.read_csv(DB_MASTER_PRODUK)
            if not df.empty and "Produk" in df.columns:
                list_prod = df["Produk"].dropna().astype(str).str.strip().unique().tolist()
                return [p for p in list_prod if p != ""]
        except Exception:
            pass
    df = pd.DataFrame({"Produk": PRODUK_DEFAULT})
    df.to_csv(DB_MASTER_PRODUK, index=False)
    return PRODUK_DEFAULT

def muat_database_harga():
    daftar_produk_aktif = muat_daftar_produk()
    if os.path.exists(DB_HARGA):
        try:
            df = pd.read_csv(DB_HARGA)
            if not df.empty and "Produk" in df.columns:
                df["Produk"] = df["Produk"].astype(str).str.strip()
                df = df[df["Produk"].isin(daftar_produk_aktif)]
                
                missing_products = [p for p in daftar_produk_aktif if p not in df["Produk"].values]
                if missing_products:
                    new_rows = pd.DataFrame([{"Produk": p, "Harga Jual": 100000, "Harga Modal": 60000} for p in missing_products])
                    df = pd.concat([df, new_rows], ignore_index=True)
                    df.to_csv(DB_HARGA, index=False)
                return df
        except Exception:
            pass
    default_data = [{"Produk": p, "Harga Jual": 100000, "Harga Modal": 60000} for p in daftar_produk_aktif]
    df = pd.DataFrame(default_data)
    df.to_csv(DB_HARGA, index=False)
    return df

def simpan_database_harga(df_baru):
    try:
        df_baru.to_csv(DB_HARGA, index=False)
    except Exception as e:
        st.error(f"Gagal menyimpan harga: {e}")

def tambah_produk_baru(nama_baru, h_jual, h_modal):
    nama_baru_clean = str(nama_baru).strip()
    daftar_produk = muat_daftar_produk()
    
    daftar_produk_lower = [p.lower() for p in daftar_produk]
    if nama_baru_clean.lower() in daftar_produk_lower:
        return False, "Nama produk tersebut sudah terdaftar di sistem!"
        
    daftar_produk_baru = daftar_produk + [nama_baru_clean]
    df_master = pd.DataFrame({"Produk": daftar_produk_baru})
    df_master.to_csv(DB_MASTER_PRODUK, index=False)
    
    try:
        if os.path.exists(DB_HARGA):
            df_harga = pd.read_csv(DB_HARGA)
            df_harga["Produk"] = df_harga["Produk"].astype(str).str.strip()
        else:
            df_harga = pd.DataFrame(columns=["Produk", "Harga Jual", "Harga Modal"])
    except Exception:
        df_harga = pd.DataFrame(columns=["Produk", "Harga Jual", "Harga Modal"])
        
    df_harga = df_harga[df_harga["Produk"].str.lower() != nama_baru_clean.lower()]
    row_baru = pd.DataFrame([{"Produk": nama_baru_clean, "Harga Jual": int(h_jual), "Harga Modal": int(h_modal)}])
    df_harga = pd.concat([df_harga, row_baru], ignore_index=True)
    df_harga.to_csv(DB_HARGA, index=False)
    return True, f"Produk '{nama_baru_clean}' sukses terdaftar tunggal!"

def hapus_produk_by_name(nama_hapus):
    nama_hapus_clean = str(nama_hapus).strip()
    daftar_produk = muat_daftar_produk()
    if nama_hapus_clean not in daftar_produk:
        return False
        
    daftar_produk.remove(nama_hapus_clean)
    df_master = pd.DataFrame({"Produk": daftar_produk})
    df_master.to_csv(DB_MASTER_PRODUK, index=False)
    
    if os.path.exists(DB_HARGA):
        try:
            df_harga = pd.read_csv(DB_HARGA)
            df_harga["Produk"] = df_harga["Produk"].astype(str).str.strip()
            df_harga = df_harga[df_harga["Produk"].str.lower() != nama_hapus_clean.lower()]
            df_harga.to_csv(DB_HARGA, index=False)
        except Exception:
            pass
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

# 🔥 FIX: SINTAKS DITUTUP SEMPURNA DENGAN )
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

# --- AMBIL DATA MASTER PRODUK AKTIF ---
MASTER_PRODUK_AKTIF = muat_daftar_produk()

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

# --- TAB 1: INPUT TRANSAKSI (🔥 FIX: REAL-TIME PRICE FETCHING) ---
with tab1:
    st.subheader("Tambah Transaksi Baru")
    if not MASTER_PRODUK_AKTIF:
        st.warning("⚠️ Belum ada daftar produk di sistem.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🛍️ Detail Penjualan")
            platform_pilihan = st.selectbox("Pilih Platform Marketplace", options=list(KONS_MARKETPLACE.keys()))
            nama_produk = st.selectbox("Nama Produk / SKU", options=MASTER_PRODUK_AKTIF)
            
            # 🔥 Mengambil database harga paling fresh real-time
            df_harga_terbaru = muat_database_harga()
            info_produk = df_harga_terbaru[df_harga_terbaru["Produk"] == nama_produk].iloc[0]
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
            
            # 🔥 POP-UP TOAST TRANSAKSI SUKSES
            st.toast(f"🎉 Kamu berhasil menginput transaksi {platform_pilihan} untuk '{nama_produk}'!", icon="✅")
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
            if produk_terpilih != "Semua Produk":
                df_filtered = df_filtered[df_filtered["Produk"] == produk_terpilih]
                
            if df_filtered.empty:
                st.warning(f"Tidak ada transaksi yang cocok pada filter terpilih.")
            else:
                total_omset = df_filtered["Total Omset"].sum()
                total_profit = df_filtered["Total Profit"].sum()
                total_barang_terjual = df_filtered["Jumlah"].sum()
                
                if st.session_state.user_role == "Owner":
                    m1, m2, m3 = st.columns(3)
                    m1.metric(label="Total Omset Terfilter", value=f"Rp {total_omset:,.0f}")
                    m2.metric(label="Total Keuntungan Bersih (Profit)", value=f"Rp {total_profit:,.0f}")
                    m3.metric(label="Total Produk Terjual", value=f"{total_barang_terjual} pcs")
                else:
                    m1, m2 = st.columns(2)
                    m1.metric(label="Total Omset Terfilter", value=f"Rp {total_omset:,.0f}")
                    m2.metric(label="Total Produk Terjual", value=f"{total_barang_terjual} pcs")
                
                st.markdown("---")
                if st.session_state.user_role == "Owner":
                    st.markdown("### ✏️ Koreksi / Hapus Transaksi")
                    id_hapus = st.number_input("Masukkan ID baris data:", min_value=0, step=1, value=0)
                    if st.button("❌ Hapus Baris Ini", type="secondary"):
                        if id_hapus in df_filtered.index:
                            if hapus_transaksi_by_index(id_hapus):
                                st.toast(f"💥 Sukses! Baris transaksi ID {id_hapus} berhasil dihapus!", icon="🗑️")
                                st.rerun()
                        else:
                            st.error(f"ID {id_hapus} tidak ditemukan!")
                    st.markdown("---")
                
                if st.session_state.user_role == "Admin":
                    kolom_kasir = ["Waktu", "Tanggal", "Platform", "Produk", "Harga Jual", "Jumlah", "Biaya Lain", "Total Omset"]
                    df_tampilan_tabel = df_filtered[kolom_kasir]
                else:
                    df_tampilan_tabel = df_filtered
                
                st.dataframe(df_tampilan_tabel, use_container_width=True)
                
                csv_data = df_tampilan_tabel.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download & Ekspor Laporan Penjualan (CSV)",
                    data=csv_data,
                    file_name=f"laporan_pos_{st.session_state.user_role.lower()}.csv",
                    mime="text/csv",
                )

# --- TAB 3: MANAJEMEN PRODUK & HARGA ---
with tab3:
    df_harga_aktif = muat_database_harga()
    if st.session_state.user_role == "Owner":
        st.markdown("## 🛠️ Menu Manajemen Produk (Khusus Owner)")
        col_add, col_del = st.columns(2)
        
        with col_add:
            st.markdown("### ➕ Tambah Menu Produk Baru")
            with st.form("form_tambah_produk", clear_on_submit=True):
                input_nama_baru = st.text_input("Nama Produk Baru / SKU").strip()
                input_harga_jual = st.number_input("Harga Jual Awal (Rp)", min_value=0, value=100000, step=1000)
                input_harga_modal = st.number_input("Harga Modal Awal (Rp)", min_value=0, value=60000, step=1000)
                tombol_submit_produk = st.form_submit_button("Tambahkan ke Sistem", use_container_width=True)
                
                if tombol_submit_produk:
                    if input_nama_baru == "":
                        st.error("Nama produk tidak boleh kosong!")
                    else:
                        sukses, pesan = tambah_produk_baru(input_nama_baru, input_harga_jual, input_harga_modal)
                        if sukses:
                            # 🔥 POP-UP TOAST TAMBAH PRODUK SUKSES
                            st.toast(f"📦 Sukses! Produk '{input_nama_baru}' berhasil terdaftar di sistem!", icon="📥")
                            st.rerun()
                        else:
                            st.error(pesan)
                            
        with col_del:
            st.markdown("### 🗑️ Hapus Menu Produk")
            if not MASTER_PRODUK_AKTIF:
                st.info("Belum ada produk aktif yang bisa dihapus.")
            else:
                produk_mau_dihapus = st.selectbox("Pilih Produk yang Akan Dibuang", options=MASTER_PRODUK_AKTIF)
                if st.button("❌ Hapus Produk Terpilih Selamanya", type="secondary", use_container_width=True):
                    if hapus_produk_by_name(produk_mau_dihapus):
                        st.toast(f"🗑️ Sukses! Produk '{produk_mau_dihapus}' telah dihapus dari jualan!", icon="💥")
                        st.rerun()
        st.markdown("---")

    st.markdown("## ⚙️ Update Harga Modal & Jual Pasar Hari Ini")
    st.info("💡 Klik langsung pada angka di tabel, ubah nilainya, lalu klik tombol simpan di bawah.")
    
    # Tabel Editor Utama
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
    
    # 🔥 FIX: Tombol Simpan dipaksa membaca revisi data langsung dari session_state
    if st.button("💾 Simpan Perubahan Harga Hari Ini", type="primary", use_container_width=True):
        if "editor_harga" in st.session_state and "edited_rows" in st.session_state.editor_harga:
            perubahan = st.session_state.editor_harga["edited_rows"]
            for indeks_baris, kolom_berubah in perubahan.items():
                idx = int(indeks_baris)
                if "Harga Jual" in kolom_berubah:
                    df_harga_aktif.at[idx, "Harga Jual"] = int(kolom_berubah["Harga Jual"])
                if "Harga Modal" in kolom_berubah:
                    df_harga_aktif.at[idx, "Harga Modal"] = int(kolom_berubah["Harga Modal"])
        
        simpan_database_harga(df_harga_aktif)
        
        # 🔥 POP-UP TOAST UPDATE MODAL & HARGA JUAL SUKSES
        st.toast("🚀 Sukses! Kamu berhasil mengupdate modal dan harga jual pasar terbaru!", icon="💾")
        st.rerun()
