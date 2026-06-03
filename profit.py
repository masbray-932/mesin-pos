import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os  # SAKTI: Kita tambahkan ini agar perintah os.path.exists tidak error lagi!
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIG ---
st.set_page_config(page_title="POS Multi-Marketplace", page_icon="🏪", layout="wide")

# File lokal sisa session login saja
DB_SESSION = "database_session.txt"

# ==========================================
# 🏪 KONEKSI GOOGLE SHEETS CORE (SUPER STABIL)
# ==========================================
def connect_sheets():
    try:
        creds_dict = dict(st.secrets["gcp"]) 
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("Data_Transaksi_POS")
    except Exception as e:
        st.error(f"Gagal koneksi ke Google Drive/Sheets Cloud: {e}")
        return None

# ==========================================
# 🔔 FITUR POP-UP TOAST QUEUE
# ==========================================
if "pesan_toast" in st.session_state and st.session_state.pesan_toast:
    st.toast(st.session_state.pesan_toast, icon=st.session_state.get("icon_toast", "✅"))
    st.session_state.pesan_toast = None
    st.session_state.icon_toast = "✅"

# --- KONFIGURASI DATA AKUN & MARKETPLACE ---
AKUN_USER = {
    "owner": {"password": "owner123", "role": "Owner"},
    "admin": {"password": "admin123", "role": "Admin"}
}

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

KONS_MARKETPLACE = {
    "Shopee": {"persen": 12.50, "fix": 1250},
    "Tokopedia": {"persen": 16.97, "fix": 0},
    "TikTok Shop": {"persen": 8.00, "fix": 2000},
    "Lazada": {"persen": 7.00, "fix": 1000},
    "Offline / WA": {"persen": 0.00, "fix": 0}
}

DAFTAR_TOKO_PLATFORM = {
    "Shopee": ["Sinar Bintang Telur", "EGGKU", "Astra Telur", "Telur88"],
    "Tokopedia": ["Sinar Bintang Telur", "SB Telur", "Astra Telur"],
    "TikTok Shop": ["Utama"], 
    "Lazada": ["Utama"], 
    "Offline / WA": ["Toko Offline"]
}

# ==========================================
# 🔄 FUNGSI PRODUK & HARGA (OPTIMIZED WITH CACHE)
# ==========================================
@st.cache_data(ttl=10) # <--- SAKTI: VPS mengingat data ini 10 detik, ketikan kasir jadi wus-wus!
def muat_daftar_produk():
    try:
        doc = connect_sheets()
        if doc:
            sheet = doc.worksheet("Master_Produk")
            df = pd.DataFrame(sheet.get_all_records())
            if not df.empty and "Produk" in df.columns:
                list_prod = df["Produk"].dropna().astype(str).str.strip().unique().tolist()
                return [p for p in list_prod if p != ""]
    except: pass
    return PRODUK_DEFAULT

@st.cache_data(ttl=10) # <--- SAKTI: Mengunci database harga di memori sementara agar tidak bikin delay
def muat_database_harga():
    daftar_produk_aktif = muat_daftar_produk()
    try:
        doc = connect_sheets()
        if doc:
            sheet = doc.worksheet("Harga_Pasar")
            df = pd.DataFrame(sheet.get_all_records())
            if not df.empty and "Produk" in df.columns:
                df["Produk"] = df["Produk"].astype(str).str.strip()
                
                missing_products = [p for p in daftar_produk_aktif if p not in df["Produk"].values]
                if missing_products:
                    # Jika ada produk baru di Master_Produk yang belum punya harga, buat baris default-nya
                    sheet_harga = doc.worksheet("Harga_Pasar")
                    for p in missing_products:
                        sheet_harga.append_row([p, 100000, 60000])
                    # Ambil ulang data terbaru setelah di-append
                    df = pd.DataFrame(sheet_harga.get_all_records())
                    df["Produk"] = df["Produk"].astype(str).str.strip()
                
                # SINKRONISASI AKHIR: Pastikan data yang keluar hanya produk yang aktif
                df = df[df["Produk"].isin(daftar_produk_aktif)]
                return df
    except: pass
    return pd.DataFrame([{"Produk": p, "Harga Jual": 100000, "Harga Modal": 60000} for p in daftar_produk_aktif])

def simpan_database_harga(df_baru):
    try:
        doc = connect_sheets()
        if doc:
            sheet = doc.worksheet("Harga_Pasar")
            sheet.clear()
            sheet.update([df_baru.columns.values.tolist()] + df_baru.values.tolist())
            st.cache_data.clear() # <--- SAKTI: Bersihkan cache agar perubahan harga langsung ter-refresh!
    except Exception as e: 
        st.error(f"Gagal menyimpan harga ke Cloud: {e}")

def tambah_produk_baru(nama_baru, h_jual, h_modal):
    nama_baru_clean = str(nama_baru).strip()
    daftar_produk = muat_daftar_produk()
    
    if nama_baru_clean.lower() in [p.lower() for p in daftar_produk]:
        return False, "Nama produk tersebut sudah terdaftar di sistem!"
        
    try:
        doc = connect_sheets()
        if doc:
            doc.worksheet("Master_Produk").append_row([nama_baru_clean])
            doc.worksheet("Harga_Pasar").append_row([nama_baru_clean, int(h_jual), int(h_modal)])
            st.cache_data.clear() # <--- SAKTI: Bersihkan cache agar produk baru langsung masuk pilihan kasir
            return True, f"Produk '{nama_baru_clean}' sukses terdaftar tunggal!"
    except Exception as e:
        return False, f"Gagal menambahkan ke Cloud: {e}"

def hapus_produk_by_name(nama_hapus):
    nama_hapus_clean = str(nama_hapus).strip()
    try:
        doc = connect_sheets()
        if doc:
            # Hapus dari tab Master_Produk
            sh_master = doc.worksheet("Master_Produk")
            df_m = pd.DataFrame(sh_master.get_all_records())
            if not df_m.empty:
                idx_m = df_m[df_m["Produk"].str.lower() == nama_hapus_clean.lower()].index
                for i in sorted(idx_m, reverse=True):
                    sh_master.delete_rows(int(i) + 2)
            
            # Hapus dari tab Harga_Pasar
            sh_harga = doc.worksheet("Harga_Pasar")
            df_h = pd.DataFrame(sh_harga.get_all_records())
            if not df_h.empty:
                idx_h = df_h[df_h["Produk"].str.lower() == nama_hapus_clean.lower()].index
                for i in sorted(idx_h, reverse=True):
                    sh_harga.delete_rows(int(i) + 2)
            st.cache_data.clear() # <--- SAKTI: Bersihkan cache setelah produk dihapus
            return True
    except: pass
    return False

# --- FUNGSI TRANSAKSI ---
def muat_data_transaksi():
    try:
        doc = connect_sheets()
        if doc:
            sheet = doc.worksheet("Transaksi")
            data = sheet.get_all_records()
            return pd.DataFrame(data)
    except Exception as e:
        pass
    return pd.DataFrame(columns=["Waktu", "Tanggal", "Platform", "Toko", "Produk", "Harga Jual", "Harga Modal", "Jumlah", "Biaya Admin %", "Biaya Fix", "Biaya Lain", "Total Omset", "Total Profit"])

def simpan_transaksi(platform, toko, produk, harga_jual, harga_modal, jumlah, biaya_lain, tanggal_pilihan):
    waktu_jakarta = datetime.utcnow() + timedelta(hours=7)
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
    
    row = [
        jam, tanggal_str, platform, toko, produk, harga_jual, harga_modal, jumlah, 
        total_admin_persen, admin_fix_rate, total_biaya_lain, total_omset, total_profit
    ]
    
    try:
        doc = connect_sheets()
        if doc:
            doc.worksheet("Transaksi").append_row(row)
    except Exception as e:
        st.error(f"Gagal menyimpan transaksi ke Cloud: {e}")

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
    except Exception: pass

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
                        with open(DB_SESSION, "w") as f: f.write(f"{username_input},{AKUN_USER[username_input]['role']}")
                        
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
            try: os.remove(DB_SESSION)
            except Exception: pass
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.username = ""
        st.rerun()

st.title("🏪 MESIN POS MULTI-MARKETPLACE")
st.write(f"Selamat bekerja, **{st.session_state.user_role}**! Data tersinkronisasi otomatis ke Cloud Google Sheets.")

tab1, tab2, tab3, tab4 = st.tabs([
    "📥 Input Transaksi Baru", 
    "📈 Riwayat & Laporan Penjualan", 
    "⚙️ Kelola Manajemen Produk & Harga",
    "🧮 Kalkulator Simulasi Profit"
])

# --- TAB 1: INPUT TRANSAKSI (SUPER REVOLUTIONARY SPEED) ---
with tab1:
    st.subheader("Tambah Transaksi Baru")
    if not MASTER_PRODUK_AKTIF:
        st.warning("⚠️ Belum ada daftar produk di sistem.")
    else:
        # BUNGKUS DENGAN FORM: Mengunci semua inputan agar ketikan kasir 0 detik tanpa delay!
        with st.form("kontainer_input_kasir", clear_on_submit=False):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 🛍️ Detail Penjualan")
                hari_ini_wib = (datetime.utcnow() + timedelta(hours=7)).date()
                
                input_tanggal_manual = st.date_input("Pilih Tanggal Transaksi", value=hari_ini_wib, key="input_tgl")
                platform_pilihan = st.selectbox("Pilih Platform Marketplace", options=list(KONS_MARKETPLACE.keys()))
                
                list_toko_tersedia = DAFTAR_TOKO_PLATFORM[platform_pilihan]
                toko_pilihan = st.selectbox("Pilih Cabang Toko Anda", options=list_toko_tersedia, key="pilih_toko_trx")
                nama_produk = st.selectbox("Nama Produk / SKU", options=MASTER_PRODUK_AKTIF)
                
                df_harga_terbaru = muat_database_harga()
                info_produk = df_harga_terbaru[df_harga_terbaru["Produk"] == nama_produk].iloc[0] if nama_produk in df_harga_terbaru["Produk"].values else {"Harga Jual": 100000, "Harga Modal": 60000}
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

            # Tombol submit khusus form
            tombol_simpan_form = st.form_submit_button("💾 Simpan Transaksi Ke Database", type="primary", use_container_width=True)

        # Logika eksekusi HANYA berjalan setelah tombol diklik
        if tombol_simpan_form:
            with st.spinner("⏳ Sedang menyinkronkan data ke Cloud Google Sheets..."):
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
            waktu_jkt = datetime.utcnow() + timedelta(hours=7)
            rentang_tanggal = st.date_input("Pilih Rentang Tanggal", value=(waktu_jkt.date(), waktu_jkt.date()))
        with col_f2:
            platform_terpilih = st.selectbox("Filter Platform", options=["Semua Platform"] + list(KONS_MARKETPLACE.keys()))
        with col_f2_b:
            list_toko = ["Semua Cabang Toko"] + sorted(df_transaksi["Toko"].dropna().unique().tolist())
            toko_terpilih = st.selectbox("Filter Toko", options=list_toko)
        with col_f3:
            produk_terpilih = st.selectbox("Filter Produk", options=["Semua Produk"] + MASTER_PRODUK_AKTIF)
        
        if isinstance(rentang_tanggal, tuple) and len(rentang_tanggal) == 2:
            tgl_mulai, tgl_akhir = rentang_tanggal
            df_transaksi['Tanggal'] = pd.to_datetime(df_transaksi['Tanggal']).dt.date
            df_filtered = df_transaksi[(df_transaksi["Tanggal"] >= tgl_mulai) & (df_transaksi["Tanggal"] <= tgl_akhir)].copy()
            if platform_terpilih != "Semua Platform": df_filtered = df_filtered[df_filtered["Platform"] == platform_terpilih]
            if toko_terpilih != "Semua Cabang Toko": df_filtered = df_filtered[df_filtered["Toko"] == toko_terpilih]
            if produk_terpilih != "Semua Produk": df_filtered = df_filtered[df_filtered["Produk"] == produk_terpilih]
                
            if df_filtered.empty:
                st.warning("Data tidak ditemukan.")
            else:
                m1, m2 = st.columns(2)
                m1.metric("Total Omset", f"Rp {df_filtered['Total Omset'].sum():,.0f}")
                m2.metric("Total Terjual", f"{df_filtered['Jumlah'].sum()} pcs")
                
                st.markdown("### ✏️ Data Transaksi (Centang untuk Hapus)")
                df_tampilan = df_filtered.copy()
                df_tampilan.insert(0, "Pilih", False)
                df_tampilan["ID Asli"] = df_filtered.index
                
                df_edit = st.data_editor(
                    df_tampilan,
                    hide_index=True,
                    use_container_width=True,
                    disabled=[col for col in df_tampilan.columns if col != "Pilih"],
                    column_config={"Pilih": st.column_config.CheckboxColumn("Pilih", default=False)},
                    key="editor_transaksi_global"
                )
                
                perubahan = st.session_state.editor_transaksi_global.get("edited_rows", {})
                list_id_hapus = [int(df_tampilan.iloc[int(idx)]["ID Asli"]) for idx, status in perubahan.items() if status.get("Pilih") == True]
                
                if list_id_hapus:
                    if st.button(f"❌ Hapus ({len(list_id_hapus)}) Transaksi Terpilih"):
                        doc = connect_sheets()
                        if doc:
                            sheet = doc.worksheet("Transaksi")
                            for idx in sorted(list_id_hapus, reverse=True):
                                sheet.delete_rows(int(idx) + 2)
                            st.success("Berhasil dihapus dari Cloud Sheets!")
                            st.rerun()

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
                    column_config={"Pilih": st.column_config.CheckboxColumn("Pilih", default=False)},
                    key="editor_produk_hapus_centang"
                )
                
                perubahan_prod = st.session_state.editor_produk_hapus_centang.get("edited_rows", {})
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
    if not df_harga_aktif.empty:
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
            perubahan_harga = st.session_state.editor_harga.get("edited_rows", {})
            for indeks_baris, kolom_berubah in perubahan_harga.items():
                idx = int(indeks_baris)
                if "Harga Jual" in kolom_berubah:
                    df_harga_aktif.at[idx, "Harga Jual"] = int(kolom_berubah["Harga Jual"])
                if "Harga Modal" in kolom_berubah:
                    df_harga_aktif.at[idx, "Harga Modal"] = int(kolom_berubah["Harga Modal"])
            
            simpan_database_harga(df_harga_aktif)
            st.session_state.pesan_toast = "🚀 Sukses! Kamu berhasil mengupdate modal dan harga jual pasar terbaru di Cloud!"
            st.session_state.icon_toast = "💾"
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
