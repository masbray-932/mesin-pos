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
DB_SESSION = "database_session.txt"

# ==========================================
# 🔔 FITUR POP-UP TOAST QUEUE
# ==========================================
if "pesan_toast" in st.session_state and st.session_state.pesan_toast:
    st.toast(st.session_state.pesan_toast, icon=st.session_state.get("icon_toast", "✅"))
    st.session_state.pesan_toast = None
    st.session_state.icon_toast = "✅"
# ==========================================

# ==========================================
# 🔥 PROTEKSI HARD RESET JIKA FILE CORRUPT
# ==========================================
def validasi_dan_shared_clean(nama_file, kolom_wajib):
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

validasi_dan_shared_clean(DB_MASTER_PRODUK, ["Produk"])
validasi_dan_shared_clean(DB_HARGA, ["Produk", "Harga Jual", "Harga Modal"])
# ==========================================

# 1. DATA LOGIN AKUN
AKUN_USER = {
    "owner": {"password": "owner123", "role": "Owner"},
    "admin": {"password": "admin123", "role": "Admin"}
}

# 2. DAFTAR MASTER PRODUK BAWAAN
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

# 3. DICTIONARY BIAYA ADMIN PER MARKETPLACE (Default Awal)
KONS_MARKETPLACE = {
    "Shopee": {"persen": 12.50, "fix": 1250},
    "Tokopedia": {"persen": 16.97, "fix": 0},
    "TikTok Shop": {"persen": 8.00, "fix": 2000},
    "Lazada": {"persen": 7.00, "fix": 1000},
    "Offline / WA": {"persen": 0.00, "fix": 0}
}

# --- FUNGSI DETEKSI & MUAT DATABASE ---
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

# ==========================================
# 🔐 LOGIKA SISTEM LOGIN FILE-LOCK PERMANEN
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.username = ""

if not st.session_state.logged_in and os.path.exists(DB_SESSION):
    try:
        with open(DB_SESSION, "r") as f:
            isi_file = f.read().strip().split(",")
            if len(isi_file) == 2:
                saved_user, saved_role = isi_file
                if saved_user in AKUN_USER:
                    st.session_state.logged_in = True
                    st.session_state.username = saved_user
                    st.session_state.user_role = saved_role
    except Exception:
        pass

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🔐 Login Sistem Kasir POS</h2>", unsafe_allow_html=True)
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        with st.form("form_login"):
            username_input = st.text_input("Username").strip().lower()
            password_input = st.text_input("Password", type="password")
            tetap_login = st.checkbox("Kunci Akun di Perangkat Ini (Ingat Saya / Auto-Login)", value=True)
            tombol_login = st.form_submit_button("Masuk ke Sistem", use_container_width=True)
            
            if tombol_login:
                if username_input in AKUN_USER and AKUN_USER[username_input]["password"] == password_input:
                    st.session_state.logged_in = True
                    st.session_state.user_role = AKUN_USER[username_input]["role"]
                    st.session_state.username = username_input
                    
                    if tetap_login:
                        with open(DB_SESSION, "w") as f:
                            f.write(f"{username_input},{AKUN_USER[username_input]['role']}")
                        
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
        if os.path.exists(DB_SESSION):
            try:
                os.remove(DB_SESSION)
            except Exception:
                pass
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.username = ""
        st.rerun()

st.title("🏪 MESIN POS MULTI-MARKETPLACE")
st.write(f"Selamat bekerja, **{st.session_state.user_role}**! Data tersinkronisasi otomatis.")

tab1, tab2, tab3, tab4 = st.tabs([
    "📥 Input Transaksi Baru", 
    "📈 Riwayat & Laporan Penjualan", 
    "⚙️ Kelola Manajemen Produk & Harga",
    "🧮 Kalkulator Simulasi Profit"
])

# --- TAB 1: INPUT TRANSAKSI ---
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
            
            df_harga_terbaru = muat_database_harga()
            info_produk = df_harga_terbaru[df_harga_terbaru["Produk"] == nama_produk].iloc[0]
            harga_jual_default = int(info_produk["Harga Jual"])
            harga_modal_final = int(info_produk["Harga Modal"])
            
            if platform_pilihan == "Offline / WA":
                st.info("💡 Mode Offline Active: Kamu bebas mengubah angka harga jual khusus di bawah ini!")
                harga_jual_final = st.number_input("Harga Jual Khusus (Rp)", min_value=0, value=harga_jual_default, step=1000)
                st.write(f"📉 **Harga Modal Terkunci (Sistem):** Rp {harga_modal_final:,.0f}")
            else:
                harga_jual_final = harga_jual_default
                st.write(f"💵 **Harga Jual Terkunci ({platform_pilihan}):** Rp {harga_jual_final:,.0f}")
                st.write(f"📉 **Harga Modal Terkunci ({platform_pilihan}):** Rp {harga_modal_final:,.0f}")
            
            jumlah_terjual = st.number_input("Jumlah Terjual (pcs/pack)", min_value=1, value=1, key="jumlah")

        with col2:
            st.markdown("### 💸 Biaya Tambahan")
            biaya_lainnya = st.number_input("Biaya Lain-lain per Produk (Rp)", min_value=0, value=0, key="lain")
            p_persen = KONS_MARKETPLACE[platform_pilihan]["persen"]
            p_fix = KONS_MARKETPLACE[platform_pilihan]["fix"]
            
            st.info(f"""
            **📋 Skema Potongan Admin ({platform_pilihan}):**
            * Biaya Admin Persen: **{p_persen}%** dari total omset.
            * Biaya Fix Transaksi: **Rp {p_fix:,.0f}** dipotong per transaksi.
            """)

        if st.button("💾 Simpan Transaksi Ke Database", type="primary", use_container_width=True):
            simpan_transaksi(platform_pilihan, nama_produk, harga_jual_final, harga_modal_final, jumlah_terjual, biaya_lainnya)
            st.session_state.pesan_toast = f"🎉 Kamu berhasil menginput transaksi {platform_pilihan} untuk '{nama_produk}'!"
            st.session_state.icon_toast = "✅"
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
            df_filtered = df_transaksi[(df_transaksi["Tanggal"] >= tgl_mulai) & (df_transaksi["Tanggal"] <= tgl_akhir)].copy()
            
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
                
                if st.session_state.user_role == "Admin":
                    kolom_kasir = ["Waktu", "Tanggal", "Platform", "Produk", "Harga Jual", "Jumlah", "Biaya Lain", "Total Omset"]
                    df_tampilan_tabel = df_filtered[kolom_kasir].copy()
                    st.dataframe(df_tampilan_tabel, hide_index=True, use_container_width=True)
                else:
                    df_tampilan_tabel = df_filtered.copy()
                    df_tampilan_tabel.insert(0, "Pilih", False)
                    df_tampilan_tabel["ID Asli"] = df_tampilan_tabel.index
                    
                    st.markdown("### ✏️ Koreksi / Hapus Transaksi (Centang Baris di Tabel)")
                    df_dengan_centang = st.data_editor(
                        df_tampilan_tabel,
                        hide_index=True,
                        use_container_width=True,
                        disabled=[col for col in df_tampilan_tabel.columns if col != "Pilih"],
                        column_config={
                            "Pilih": st.column_config.CheckboxColumn("Pilih", default=False)
                        },
                        key="editor_transaksi_centang"
                    )
                    
                    if "editor_transaksi_centang" in st.session_state and "edited_rows" in st.session_state.editor_transaksi_centang:
                        perubahan_centang = st.session_state.editor_transaksi_centang["edited_rows"]
                        list_id_hapus = [df_tampilan_tabel.iloc[int(idx)]["ID Asli"] for idx, status in perubahan_centang.items() if status.get("Pilih") == True]
                        
                        if list_id_hapus:
                            st.write("")
                            if st.button(f"❌ Hapus ({len(list_id_hapus)}) Transaksi Terpilih Selamanya", type="secondary", use_container_width=True):
                                df_master_transaksi = muat_data_transaksi()
                                df_master_transaksi = df_master_transaksi.drop(list_id_hapus)
                                df_master_transaksi.to_csv(DB_FILE, index=False)
                                
                                st.session_state.pesan_toast = f"💥 Sukses! Berhasil menghapus {len(list_id_hapus)} transaksi!"
                                st.session_state.icon_toast = "🗑️"
                                st.rerun()
                
                st.markdown("---")
                csv_data = df_filtered.to_csv(index=False).encode('utf-8')
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
                            st.session_state.pesan_toast = f"📦 Sukses! Produk '{input_nama_baru}' berhasil terdaftar di sistem!"
                            st.session_state.icon_toast = "📥"
                            st.rerun()
                        else:
                            st.error(pesan)
                            
        with col_del:
            st.markdown("### 🗑️ Hapus Menu Produk (Sistem Centang)")
            if not MASTER_PRODUK_AKTIF:
                st.info("Belum ada produk aktif yang bisa dihapus.")
            else:
                df_hapus_prod = pd.DataFrame({"Pilih": [False] * len(MASTER_PRODUK_AKTIF), "Produk": MASTER_PRODUK_AKTIF})
                
                df_hapus_prod_centang = st.data_editor(
                    df_hapus_prod,
                    hide_index=True,
                    use_container_width=True,
                    disabled=["Produk"],
                    column_config={
                        "Pilih": st.column_config.CheckboxColumn("Pilih", default=False)
                    },
                    key="editor_produk_hapus_centang"
                )
                
                if "editor_produk_hapus_centang" in st.session_state and "edited_rows" in st.session_state.editor_produk_hapus_centang:
                    perubahan_prod = st.session_state.editor_produk_hapus_centang["edited_rows"]
                    list_prod_hapus = [df_hapus_prod.iloc[int(idx)]["Produk"] for idx, status in perubahan_prod.items() if status.get("Pilih") == True]
                    
                    if list_prod_hapus:
                        if st.button(f"❌ Hapus ({len(list_prod_hapus)}) Produk Tercentang", type="secondary", use_container_width=True):
                            for p_nama in list_prod_hapus:
                                hapus_produk_by_name(p_nama)
                                
                            st.session_state.pesan_toast = f"🗑️ Sukses! Berhasil membuang {len(list_prod_hapus)} menu produk!"
                            st.session_state.icon_toast = "💥"
                            st.rerun()
        st.markdown("---")

    st.markdown("## ⚙️ Update Harga Modal & Jual Pasar Hari Ini")
    if not MASTER_PRODUK_AKTIF:
        st.info("Belum ada produk terdaftar untuk diatur harganya.")
    else:
        st.info("💡 Klik langsung pada angka di tabel, ubah nilainya, lalu klik tombol simpan di bawah.")
        
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
            st.session_state.pesan_toast = "🚀 Sukses! Kamu berhasil mengupdate modal dan harga jual pasar terbaru!"
            st.session_state.icon_toast = "💾"
            st.rerun()

# --- 🔥 TAB 4: KALKULATOR SIMULASI PROFIT VERSI HORIZONTAL (MANUAL INPUT) ---
with tab4:
    st.subheader("🧮 Perbandingan Simulasi Profit Antar Marketplace")
    st.write("Silakan pilih produk dasar untuk mengambil acuan modal harian, lalu sesuaikan atau ketik manual parameter di bawah ini:")

    if not MASTER_PRODUK_AKTIF:
        st.info("Belum ada produk aktif untuk disimulasikan.")
    else:
        # Pilih Produk Utama untuk Acuan Awal
        calc_produk_pilihan = st.selectbox("Acuan Harga Dasar Produk", options=MASTER_PRODUK_AKTIF, key="new_calc_prod")
        
        df_harga_fresh = muat_database_harga()
        info_fresh = df_harga_fresh[df_harga_fresh["Produk"] == calc_produk_pilihan].iloc[0]
        modal_baku = int(info_fresh["Harga Modal"])
        jual_baku = int(info_fresh["Harga Jual"])
        
        st.markdown(f"**💡 Acuan Sistem Hari Ini ->** Modal Asli: `Rp {modal_baku:,.0f}` | Harga Jual Standar: `Rp {jual_baku:,.0f}`")
        st.markdown("---")
        
        # MEMBUAT KOLOM INPUT BERJEJER HORIZONTAL SESUAI SCREENSHOT
        list_platform = ["Shopee", "Tokopedia", "TikTok Shop", "Lazada", "Offline / WA"]
        
        # Dictionary untuk menampung hasil input pengguna per platform
        input_data = {}
        
        # Kita bagi layout halaman menjadi 5 kolom (1 kolom untuk 1 platform)
        cols = st.columns(5)
        
        for i, plat in enumerate(list_platform):
            with cols[i]:
                st.markdown(f"### 🏪 {plat}")
                
                # Ambil nilai default bawaan sistem untuk mempermudah user
                def_persen = KONS_MARKETPLACE[plat]["persen"]
                def_fix = KONS_MARKETPLACE[plat]["fix"]
                
                # Pembuatan Form Input Manual Per Baris Kolom
                p_jual = st.number_input(f"Harga Jual ({plat})", min_value=0, value=jual_baku, step=1000, key=f"jual_{plat}")
                p_modal = st.number_input(f"Harga Modal ({plat})", min_value=0, value=modal_baku, step=1000, key=f"modal_{plat}")
                p_qty = st.number_input(f"Qty / Jumlah ({plat})", min_value=1, value=1, key=f"qty_{plat}")
                p_persen = st.number_input(f"Biaya Admin % ({plat})", min_value=0.0, value=float(def_persen), step=0.1, key=f"persen_{plat}")
                p_fix = st.number_input(f"Biaya Admin Fix Rp ({plat})", min_value=0, value=int(def_fix), step=500, key=f"fix_{plat}")
                p_pack = st.number_input(f"Biaya Packing Rp ({plat})", min_value=0, value=0, step=500, key=f"pack_{plat}")
                p_lain = st.number_input(f"Biaya Lain-lain Rp ({plat})", min_value=0, value=0, step=500, key=f"lain_{plat}")
                
                # RUMUS LOGIKA MATEMATIKA HITUNG PROFIT
                omset_kotor = p_jual * p_qty
                biaya_admin_total = ((p_persen / 100) * omset_kotor) + (p_fix * p_qty)
                pengeluaran_total = (p_modal * p_qty) + biaya_admin_total + (p_pack * p_qty) + (p_lain * p_qty)
                profit_bersih = omset_kotor - pengeluaran_total
                margin_persen = (profit_bersih / omset_kotor * 100) if omset_kotor > 0 else 0.0
                
                # Simpan hasil kalkulasi ke dictionary
                input_data[plat] = {
                    "omset": omset_kotor,
                    "admin": biaya_admin_total,
                    "pengeluaran": pengeluaran_total,
                    "profit": profit_bersih,
                    "margin": margin_persen
                }
                
        st.markdown("---")
        st.markdown("## 📊 Tabel Hasil Analisis Perbandingan Profit")
        
        # KITA STRUKTURKAN MENJADI TABEL HORIZONTAL PERSIS SEPERTI GAMBAR CONTOH
        baris_nama = [
            "Total Omset Kotor", 
            "Total Biaya Admin Marketplace", 
            "Total Pengeluaran Keseluruhan", 
            "Keuntungan Bersih (Profit)", 
            "Persentase Margin (%)"
        ]
        
        tabel_final = []
        for komponen in baris_nama:
            row_cells = {"Komponen Analisis": komponen}
            for plat in list_platform:
                data_plat = input_data[plat]
                if komponen == "Total Omset Kotor":
                    row_cells[plat] = f"Rp {data_plat['omset']:,.0f}"
                elif komponen == "Total Biaya Admin Marketplace":
                    row_cells[plat] = f"Rp {data_plat['admin']:,.0f}"
                elif komponen == "Total Pengeluaran Keseluruhan":
                    row_cells[plat] = f"Rp {data_plat['pengeluaran']:,.0f}"
                elif komponen == "Keuntungan Bersih (Profit)":
                    row_cells[plat] = f"Rp {data_plat['profit']:,.0f}"
                elif komponen == "Persentase Margin (%)":
                    row_cells[plat] = f"{data_plat['margin']:.2f} %"
            tabel_final.append(row_cells)
            
        df_hasil_tabel = pd.DataFrame(tabel_final)
        
        # Tampilkan tabel statis dengan kustomisasi visual sederhana di Streamlit
        st.dataframe(df_hasil_tabel, use_container_width=True, hide_index=True)
        
        # MEMBERIKAN HIGHLIGHT WARNA COMPACT BOX DI BAWAHNYA AGAR MAKIN CANTIK & MUDAH DIBACA
        st.markdown("### 🎯 Ringkasan Status Cuan Bersih:")
        summary_cols = st.columns(5)
        for idx, plat in enumerate(list_platform):
            with summary_cols[idx]:
                cuan = input_data[plat]['profit']
                margin = input_data[plat]['margin']
                if cuan > 0:
                    st.markdown(f"<div style='background-color:#d4edda; padding:10px; border-radius:5px; text-align:center; border: 1px solid #c3e6cb;'><b style='color:#155724;'>🟢 {plat} Profit</b><br><span style='color:#155724; font-size:15px; font-weight:bold;'>Rp {cuan:,.0f}</span><br><small style='color:#155724;'>Margin: {margin:.2f}%</small></div>", unsafe_allow_html=True)
                elif cuan == 0:
                    st.markdown(f"<div style='background-color:#fff3cd; padding:10px; border-radius:5px; text-align:center; border: 1px solid #ffeeba;'><b style='color:#856404;'>🟡 {plat} BEP</b><br><span style='color:#856404; font-size:15px; font-weight:bold;'>Rp 0</span></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='background-color:#f8d7da; padding:10px; border-radius:5px; text-align:center; border: 1px solid #f5c6cb;'><b style='color:#721c24;'>🔴 {plat} BONCOS!</b><br><span style='color:#721c24; font-size:15px; font-weight:bold;'>Rp {cuan:,.0f}</span><br><small style='color:#721c24;'>Margin: {margin:.2f}%</small></div>", unsafe_allow_html=True)
