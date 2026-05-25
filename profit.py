import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Pengaturan judul halaman web
st.set_page_config(page_title="POS Multi-Marketplace & Manajemen Harga Harian", page_icon="🏪", layout="wide")

# --- KONEKSI GOOGLE SHEETS ---
# ⚠️ PASTIKAN KAMU MENEMPELKAN URL GOOGLE SHEETS KAMU DI BAWAH INI DAN AKSESNYA SUDAH "ANYONE WITH LINK AS EDITOR"
URL_GOOGLE_SHEETS = "PASTE_LINK_GOOGLE_SHEETS_KAMU_DI_SINI"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("Gagal menghubungkan ke Google Sheets. Pastikan library streamlit-gsheets-connection sudah terinstall.")

# 1. DAFTAR MASTER PRODUK (Sebagai Acuan Cadangan)
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

# 2. DICTIONARY BIAYA ADMIN PER MARKETPLACE
KONS_MARKETPLACE = {
    "Shopee": {"persen": 12.50, "fix": 1250},
    "Tokopedia": {"persen": 16.97, "fix": 0},
    "TikTok Shop": {"persen": 8.00, "fix": 2000},
    "Lazada": {"persen": 7.00, "fix": 1000},
    "Offline / WA": {"persen": 0.00, "fix": 0}
}

# --- FUNGSI MUAT & SIMPAN DATA VIA CLOUD (VERSI PERBAIKAN ANTI-ERROR) ---
def muat_semua_data():
    try:
        # Membaca langsung dari Google Sheets yang sudah diisi manual di Langkah 1
        df_transaksi = conn.read(spreadsheet=URL_GOOGLE_SHEETS, worksheet="Sheet1", ttl=0)
        df_harga = conn.read(spreadsheet=URL_GOOGLE_SHEETS, worksheet="Sheet2", ttl=0)
        
        # Bersihkan dari baris kosong (jika ada pembacaan berlebih dari Google Sheets)
        df_transaksi = df_transaksi.dropna(how='all')
        df_harga = df_harga.dropna(how='all')
    except Exception as e:
        st.error(f"Error membaca spreadsheet: {e}. Pastikan nama worksheet adalah Sheet1 dan Sheet2.")
        df_transaksi = pd.DataFrame(columns=["Waktu", "Tanggal", "Platform", "Produk", "Harga Jual", "Harga Modal", "Jumlah", "Biaya Admin %", "Biaya Fix", "Biaya Lain", "Total Omset", "Total Profit"])
        df_harga = pd.DataFrame([{"Produk": p, "Harga Jual": 100000, "Harga Modal": 60000} for p in MASTER_PRODUK])
        
    # Pastikan struktur kolom bersih dari penamaan otomatis pandas yang rusak
    df_transaksi = df_transaksi.loc[:, ~df_transaksi.columns.str.contains('^Unnamed')]
    df_harga = df_harga.loc[:, ~df_harga.columns.str.contains('^Unnamed')]
    return df_transaksi, df_harga

# Ambil data awal dari Cloud
df_transaksi_aktif, df_harga_aktif = muat_semua_data()

def simpan_transaksi_cloud(platform, produk, harga_jual, harga_modal, jumlah, biaya_lain):
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
    
    df_total = pd.concat([df_transaksi_aktif, data_baru], ignore_index=True)
    conn.update(spreadsheet=URL_GOOGLE_SHEETS, worksheet="Sheet1", data=df_total)

def hapus_transaksi_cloud(index_yang_dihapus):
    if index_yang_dihapus in df_transaksi_aktif.index:
        df_baru = df_transaksi_aktif.drop(index_yang_dihapus)
        conn.update(spreadsheet=URL_GOOGLE_SHEETS, worksheet="Sheet1", data=df_baru)
        return True
    return False

# --- TAMPILAN UTAMA ---
st.title("🏪 ONLINE POS Multi-Marketplace & Google Sheets Cloud")
st.write("Sistem Kasir Cloud — Data Tersimpan Aman Langsung di Google Sheets.")

# Membuat 3 Tab
tab1, tab2, tab3 = st.tabs(["📥 Input Transaksi Baru", "📈 Riwayat & Laporan Penjualan", "⚙️ Atur Harga Modal & Jual Hari Ini"])

# --- TAB 1: INPUT TRANSAKSI ---
with tab1:
    st.subheader("Tambah Transaksi Baru")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🛍️ Detail Penjualan")
        platform_pilihan = st.selectbox("Pilih Platform Marketplace", options=list(KONS_MARKETPLACE.keys()))
        
        # Ambil daftar produk langsung dari Sheet2 Google Sheets agar dinamis
        opsi_produk_cloud = df_harga_aktif["Produk"].tolist() if not df_harga_aktif.empty else MASTER_PRODUK
        nama_produk = st.selectbox("Nama Produk / SKU", options=opsi_produk_cloud)
        
        if not df_harga_aktif.empty and nama_produk in df_harga_aktif["Produk"].values:
            info_produk = df_harga_aktif[df_harga_aktif["Produk"] == nama_produk].iloc[0]
            harga_jual_terkunci = int(info_produk["Harga Jual"])
            harga_modal_terkunci = int(info_produk["Harga Modal"])
        else:
            harga_jual_terkunci = 100000
            harga_modal_terkunci = 60000
        
        st.write(f"💵 **Harga Jual Hari Ini:** Rp {harga_jual_terkunci:,.0f}")
        st.write(f"📉 **Harga Modal Hari Ini:** Rp {harga_modal_terkunci:,.0f}")
        jumlah_terjual = st.number_input("Jumlah Terjual (pcs/pack)", min_value=1, value=1, key="jumlah")

    with col2:
        st.markdown("### 💸 Biaya Tambahan & Perhitungan")
        biaya_lainnya = st.number_input("Biaya Lain-lain per Produk (Rp)", min_value=0, value=2000, key="lain")
        p_persen = KONS_MARKETPLACE[platform_pilihan]["persen"]
        p_fix = KONS_MARKETPLACE[platform_pilihan]["fix"]
        
        st.info(f"""
        **📋 Skema Potongan Admin Aktif ({platform_pilihan}):**
        * Biaya Admin Persen: **{p_persen}%** dari total omset.
        * Biaya Fix Transaksi: **Rp {p_fix:,.0f}** dipotong per transaksi.
        """)

    if st.button("💾 Simpan Transaksi ke Google Sheets Cloud", type="primary", use_container_width=True):
        simpan_transaksi_cloud(platform_pilihan, nama_produk, harga_jual_terkunci, harga_modal_terkunci, jumlah_terjual, biaya_lainnya)
        st.success(f"🎉 Sukses! Transaksi berhasil tercatat di Google Sheets Cloud Anda.")
        st.rerun()

# --- TAB 2: RIWAYAT & LAPORAN ---
with tab2:
    st.subheader("Riwayat & Analisis Penjualan")
    if df_transaksi_aktif.empty:
        st.info("Belum ada data transaksi yang disimpan di Google Sheets.")
    else:
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            hari_ini = datetime.now().date()
            rentang_tanggal = st.date_input("Pilih Rentang Tanggal Laporan", value=(hari_ini, hari_ini))
        with col_f2:
            opsi_filter_platform = ["Semua Platform"] + list(KONS_MARKETPLACE.keys())
            platform_terpilih = st.selectbox("Filter Berdasarkan Platform", options=opsi_filter_platform)
        with col_f3:
            opsi_filter_produk = ["Semua Produk"] + (df_harga_aktif["Produk"].tolist() if not df_harga_aktif.empty else MASTER_PRODUK)
            produk_terpilih = st.selectbox("Filter Berdasarkan Produk", options=opsi_filter_produk)
        
        if isinstance(rentang_tanggal, tuple) and len(rentang_tanggal) == 2:
            tgl_mulai, tgl_akhir = rentang_tanggal
            df_transaksi_aktif['Tanggal'] = pd.to_datetime(df_transaksi_aktif['Tanggal']).dt.date
            df_filtered = df_transaksi_aktif[(df_transaksi_aktif["Tanggal"] >= tgl_mulai) & (df_transaksi_aktif["Tanggal"] <= tgl_akhir)]
            
            if platform_terpilih != "Semua Platform":
                df_filtered = df_filtered[df_filtered["Platform"] == platform_terpilih]
            if producto_terpilih := produk_terpilih != "Semua Produk":
                df_filtered = df_filtered[df_filtered["Produk"] == produk_terpilih]
                
            if df_filtered.empty:
                st.warning(f"Tidak ada transaksi yang cocok pada filter terpilih.")
            else:
                total_omset_hari_ini = df_filtered["Total Omset"].sum()
                total_profit_hari_ini = df_filtered["Total Profit"].sum()
                total_barang_terjual = df_filtered["Jumlah"].sum()
                
                m1, m2, m3 = st.columns(3)
                m1.metric(label="Total Omset Terfilter", value=f"Rp {total_omset_hari_ini:,.0f}")
                m2.metric(label="Total Keuntungan Bersih", value=f"Rp {total_profit_hari_ini:,.0f}")
                m3.metric(label="Total Produk Terjual", value=f"{total_barang_terjual} pcs")
                
                st.markdown("---")
                st.markdown("### ✏️ Koreksi / Hapus Transaksi")
                col_del1, col_del2 = st.columns([1, 3])
                with col_del1:
                    id_hapus = st.number_input("Masukkan ID baris data:", min_value=0, step=1, value=0)
                with col_del2:
                    st.write("") ; st.write("")
                    if st.button("❌ Hapus Baris Ini", type="secondary"):
                        if id_hapus in df_filtered.index:
                            if hapus_transaksi_cloud(id_hapus):
                                st.success(f"💥 Baris ID {id_hapus} berhasil dihapus dari Cloud!")
                                st.rerun()
                        else:
                            st.error(f"ID {id_hapus} tidak ditemukan!")

                st.markdown("---")
                st.dataframe(df_filtered, use_container_width=True)

# --- TAB 3: ATUR HARGA ---
with tab3:
    st.subheader("⚙️ Update Harga Modal & Jual Pasar Hari Ini")
    st.info("💡 Ubah harga, lalu klik tombol simpan di bawah untuk menyinkronkan ke Google Sheets Cloud.")
    
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
    
    if st.button("💾 Simpan Perubahan Harga ke Cloud", type="primary", use_container_width=True):
        conn.update(spreadsheet=URL_GOOGLE_SHEETS, worksheet="Sheet2", data=df_editor)
        st.success("🎉 Harga harian berhasil diperbarui di server cloud Google Sheets!")
        st.rerun()
