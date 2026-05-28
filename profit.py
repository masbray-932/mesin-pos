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

# 3. DICTIONARY BIAYA ADMIN PER MARKETPLACE
KONS_MARKETPLACE = {
    "Shopee": {"persen": 12.50, "fix": 1250},
    "Tokopedia": {"persen": 16.97, "fix": 0},
    "TikTok Shop": {"persen": 8.00, "fix": 2000},
    "Lazada": {"persen": 7.00, "fix": 1000},
    "Offline / WA": {"persen": 0.00, "fix": 0}
}

# 4. PEMETAAN DAFTAR TOKO SESUAI REVISI ANTONY
DAFTAR_TOKO_PLATFORM = {
    "Shopee": ["Sinar Bintang Telur", "EGGKU", "Astra Telur", "Telur88"],
    "Tokopedia": ["Sinar Bintang Telur", "SB Telur", "Astra Telur"],
    "TikTok Shop": ["Utama"],
    "Lazada": ["Utama"],
    "Offline / WA": ["Toko Offline"]
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
    kolom_wajib = ["Waktu", "Tanggal", "Platform", "Toko", "Produk", "Harga Jual", "Harga Modal", "Jumlah", "Biaya Admin %", "Biaya Fix", "Biaya Lain", "Total Omset", "Total Profit"]
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            if "Toko" not in df.columns:
                df["Toko"] = "Utama"
                df.to_csv(DB_FILE, index=False)
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=kolom_wajib)

def simpan_transaksi(platform, toko, produk, harga_jual, harga_modal, jumlah, biaya_lain, tanggal_pilihan):
    df = muat_data_transaksi()
    
    waktu_utc = datetime.utcnow()
    waktu_jakarta = waktu_utc + timedelta(hours=7)
    jam = waktu_jakarta.strftime("%H:%M:%S")
    tanggal_str = tanggal_pilihan.strftime("%Y-%m-%d")
    
    admin_persen_rate = KONS_MARKETPLACE[platform]["persen"]
    admin_fix_rate = KONS_MARKETPLACE[platform]["fix"]
    
    total_omset = harga_jual * jumlah
    total_modal = harga_modal * jumlah
    total_admin_persen = (admin_persen_rate / 100) * total_omset
    total_biaya_lain = biaya_lain * jumlah
    
    total_pengeluaran = total_modal + total_admin_persen + admin_fix_rate + total_biaya_lain
    total_profit = total_omset - total_pengeluaran
    
    data_baru = pd.DataFrame([{
        "Waktu": jam, "Tanggal": tanggal_str, "Platform": platform, "Toko": toko, "Produk": produk,
        "Harga Jual": harga_jual, "Harga Modal": harga_modal, "Jumlah": jumlah,
        "Biaya Admin %": total_admin_persen, "Biaya Fix": admin_fix_rate, "Biaya Lain": total_biaya_lain,
        "Total Omset": total_omset, "Total Profit": total_profit
    }])
    
    df = pd.concat([df, data_baru], ignore_index=True)
    df.to_csv(DB_FILE, index=False)

# ==========================================
# 🔐 LOGIKA SISTEM LOGIN PERMANEN
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

MASTER_PRODUK_AKTIF = muat_daftar_produk()

# Sidebar
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
            
            waktu_utc_now = datetime.utcnow()
            waktu_jkt_now = waktu_utc_now + timedelta(hours=7)
            hari_ini_wib = waktu_jkt_now.date()
            
            input_tanggal_manual = st.date_input("Pilih Tanggal Transaksi", value=hari_ini_wib, key="input_tgl")
            platform_pilihan = st.selectbox("Pilih Platform Marketplace", options=list(KONS_MARKETPLACE.keys()))
            
            list_toko_tersedia = DAFTAR_TOKO_PLATFORM[platform_pilihan]
            toko_pilihan = st.selectbox("Pilih Cabang Toko Anda", options=list_toko_tersedia, key="pilih_toko_trx")
            
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
            **📋 Skema Potongan Admin ({platform_pilihan} - {toko_pilihan}):**
            * Biaya Admin Persen: **{p_persen}%** dari total omset.
            * Biaya Fix Transaksi: **Rp {p_fix:,.0f}** dipotong per transaksi.
            """)

        if st.button("💾 Simpan Transaksi Ke Database", type="primary", use_container_width=True):
            simpan_transaksi(platform_pilihan, toko_pilihan, nama_produk, harga_jual_final, harga_modal_final, jumlah_terjual, biaya_lainnya, input_tanggal_manual)
            st.session_state.pesan_toast = f"🎉 Sukses menginput transaksi Toko [{toko_pilihan}] untuk '{nama_produk}'!"
            st.session_state.icon_toast = "✅"
            st.rerun()

# --- TAB 2: RIWAYAT & LAPORAN ---
with tab2:
    st.subheader("Riwayat & Analisis Penjualan")
    df_transaksi = muat_data_transaksi()
    
    if df_transaksi.empty:
        st.info("Belum ada data transaksi yang disimpan.")
    else:
        col_f1, col_f2, col_f2_b, col_f3 = st.columns(4)
        with col_f1:
            waktu_utc_now = datetime.utcnow()
            waktu_jkt_now = waktu_utc_now + timedelta(hours=7)
            hari_ini = waktu_jkt_now.date()
            rentang_tanggal = st.date_input("Pilih Rentang Tanggal Laporan", value=(hari_ini, hari_ini))
        with col_f2:
            opsi_filter_platform = ["Semua Platform"] + list(KONS_MARKETPLACE.keys())
            platform_terpilih = st.selectbox("Filter Berdasarkan Platform", options=opsi_filter_platform)
        with col_f2_b:
            list_toko_filter = ["Semua Cabang Toko"] + sorted(df_transaksi["Toko"].dropna().unique().tolist())
            toko_terpilih = st.selectbox("Filter Berdasarkan Toko Spesifik", options=list_toko_filter)
        with col_f3:
            opsi_filter_produk = ["Semua Produk"] + MASTER_PRODUK_AKTIF
            produk_terpilih = st.selectbox("Filter Berdasarkan Produk", options=opsi_filter_produk)
        
        if isinstance(rentang_tanggal, tuple) and len(rentang_tanggal) == 2:
            tgl_mulai, tgl_akhir = rentang_tanggal
            df_transaksi['Tanggal'] = pd.to_datetime(df_transaksi['Tanggal']).dt.date
            df_filtered = df_transaksi[(df_transaksi["Tanggal"] >= tgl_mulai) & (df_transaksi["Tanggal"] <= tgl_akhir)].copy()
            
            if platform_terpilih != "Semua Platform":
                df_filtered = df_filtered[df_filtered["Platform"] == platform_terpilih]
            if toko_terpilih != "Semua Cabang Toko":
                df_filtered = df_filtered[df_filtered["Toko"] == toko_terpilih]
            if produk_terpilih != "Semua Produk":
                df_filtered = df_filtered[df_filtered["Produk"] == produk_terpilih]
                
            if df_filtered.empty:
                st.warning(f"Tidak ada transaksi yang cocok pada filter terpilih.")
            else:
                total_omset = df_filtered["Total Omset"].sum()
                total_profit = df_filtered["Total Profit"].sum()
                # 🔥 FIX: Di sini tadinya tertulis "Interior", sudah saya ganti jadi "Jumlah"
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
                
                # Definisi kolom agar muncul rapi
                kolom_owner_urut = ["Waktu", "Tanggal", "Platform", "Toko", "Produk", "Harga Jual", "Harga Modal", "Jumlah", "Biaya Admin %", "Biaya Fix", "Biaya Lain", "Total Omset", "Total Profit"]
                
                if st.session_state.user_role == "Admin":
                    kolom_tampil = ["Waktu", "Tanggal", "Platform", "Toko", "Produk", "Harga Jual", "Jumlah", "Biaya Lain", "Total Omset"]
                    df_tampilan_tabel = df_filtered[kolom_tampil].copy()
                    st.dataframe(df_tampilan_tabel, hide_index=True, use_container_width=True)
                else:
                    df_tampilan_tabel = df_filtered[kolom_owner_urut].copy()
                    df_tampilan_tabel.insert(0, "Pilih", False)
                    df_tampilan_tabel["ID Asli"] = df_tampilan_tabel.index
                    
                    # Edit tabel
                    df_dengan_centang = st.data_editor(
                        df_tampilan_tabel,
                        hide_index=True,
                        use_container_width=True,
                        disabled=[col for col in df_tampilan_tabel.columns if col != "Pilih"],
                        column_config={
                            "Pilih": st.column_config.CheckboxColumn("Pilih", default=False),
                            "Toko": st.column_config.TextColumn("Nama Toko")
                        },
                        key="editor_transaksi_centang"
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
# Tambahkan ini di bagian Sidebar atau Tab 3 untuk Admin/Owner
with st.sidebar:
    st.markdown("---")
    st.subheader("⚠️ Manajemen Database")
    if st.button("Hapus Semua Data Transaksi (Reset)"):
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
            st.success("Database transaksi berhasil dihapus!")
            st.rerun()
# --- TAB 4: KALKULATOR SIMULASI PROFIT MASSAL ---
with tab4:
    st.subheader("🧮 Tabel Simulasi Profit Massal Semua Produk")
    st.write("Pilih marketplace target terlebih dahulu, lalu edit parameter angka langsung di dalam tabel untuk melihat simulasi profit secara instan!")

    if not MASTER_PRODUK_AKTIF:
        st.info("Belum ada produk aktif untuk disimulasikan.")
    else:
        platform_calc = st.selectbox("Target Platform Marketplace", options=list(KONS_MARKETPLACE.keys()), key="tab4_plat")
        admin_persen_def = KONS_MARKETPLACE[platform_calc]["persen"]
        st.info(f"💡 Kolom **Biaya Admin %** otomatis terisi standar {platform_calc} ({admin_persen_def}%). Kolom **Harga Modal** dikunci agar sinkron dengan manajemen harga!")

        df_base_harga = muat_database_harga()
        
        df_simulasi = pd.DataFrame()
        df_simulasi["Produk"] = df_base_harga["Produk"]
        df_simulasi["Harga Jual (Rp)"] = df_base_harga["Harga Jual"]
        df_simulasi["Harga Modal (Rp)"] = df_base_harga["Harga Modal"]
        df_simulasi["Qty (Pcs)"] = 1
        df_simulasi["Admin (%)"] = float(admin_persen_def)
        df_simulasi["Packing (Rp)"] = 0
        df_simulasi["Lain-lain (Rp)"] = 0

        if "tabel_sim_state" not in st.session_state or st.session_state.get("prev_plat") != platform_calc:
            st.session_state.tabel_sim_state = df_simulasi.copy()
            st.session_state.prev_plat = platform_calc

        df_kerja = st.session_state.tabel_sim_state.copy()

        df_hasil_edit = st.data_editor(
            df_kerja,
            disabled=["Produk", "Harga Modal (Rp)"], 
            use_container_width=True,
            key="kalkulator_massal_editor",
            column_config={
                "Harga Jual (Rp)": st.column_config.NumberColumn("Harga Jual (Rp)", min_value=0, format="%d"),
                "Harga Modal (Rp)": st.column_config.NumberColumn("Harga Modal (Rp)", min_value=0, format="%d"),
                "Qty (Pcs)": st.column_config.NumberColumn("Qty (Pcs)", min_value=1, format="%d"),
                "Admin (%)": st.column_config.NumberColumn("Admin (%)", min_value=0.0, format="%.2f"),
                "Packing (Rp)": st.column_config.NumberColumn("Packing (Rp)", min_value=0, format="%d"),
                "Lain-lain (Rp)": st.column_config.NumberColumn("Lain-lain (Rp)", min_value=0, format="%d"),
            }
        )

        if "kalkulator_massal_editor" in st.session_state and "edited_rows" in st.session_state.kalkulator_massal_editor:
            perubahan_kalkulator = st.session_state.kalkulator_massal_editor["edited_rows"]
            for r_idx_str, cols_changed in perubahan_kalkulator.items():
                r_idx = int(r_idx_str)
                for c_name, new_val in cols_changed.items():
                    df_hasil_edit.at[r_idx, c_name] = new_val
            st.session_state.tabel_sim_state = df_hasil_edit.copy()

        st.markdown("### 📊 Live Hasil Perhitungan Profit Bersih")
        
        omset_kotor = df_hasil_edit["Harga Jual (Rp)"] * df_hasil_edit["Qty (Pcs)"]
        biaya_admin_total = (df_hasil_edit["Admin (%)"] / 100) * omset_kotor
        biaya_packing_total = df_hasil_edit["Packing (Rp)"] * df_hasil_edit["Qty (Pcs)"]
        biaya_lain_total = df_hasil_edit["Lain-lain (Rp)"] * df_hasil_edit["Qty (Pcs)"]
        modal_total = df_hasil_edit["Harga Modal (Rp)"] * df_hasil_edit["Qty (Pcs)"]
        
        pengeluaran_total = modal_total + biaya_admin_total + biaya_packing_total + biaya_lain_total
        profit_total_bersih = omset_kotor - pengeluaran_total
        margin_persen_total = (profit_total_bersih / omset_kotor * 100).fillna(0.0)

        df_laporan_hasil = pd.DataFrame()
        df_laporan_hasil["Nama Produk"] = df_hasil_edit["Produk"]
        df_laporan_hasil["Total Omset Kotor"] = omset_kotor.map(lambda x: f"Rp {x:,.0f}")
        df_laporan_hasil["Total Potongan Admin"] = biaya_admin_total.map(lambda x: f"Rp {x:,.0f}")
        df_laporan_hasil["Total Pengeluaran"] = pengeluaran_total.map(lambda x: f"Rp {x:,.0f}")
        df_laporan_hasil["PROFIT BERSIH"] = profit_total_bersih.map(lambda x: f"Rp {x:,.0f}")
        df_laporan_hasil["Margin (%)"] = margin_persen_total.map(lambda x: f"{x:.2f} %")

        st.dataframe(df_laporan_hasil, use_container_width=True, hide_index=True)
        
        if st.button("🔄 Reset Angka Simulasi", type="secondary", use_container_width=True):
            if "tabel_sim_state" in st.session_state:
                del st.session_state.tabel_sim_state
            st.rerun()
