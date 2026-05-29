import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Pengaturan judul halaman web
st.set_page_config(page_title="POS Multi-Marketplace & Manajemen Harga", page_icon="🏪", layout="wide")

# Nama file database lokal (Sisa untuk Master & Harga agar tidak bentrok, Transaksi pindah ke Sheets)
DB_HARGA = "database_harga.csv"
DB_MASTER_PRODUK = "database_master_produk.csv"
DB_SESSION = "database_session.txt"

# ==========================================
# 🏪 KONEKSI GOOGLE SHEETS (ANTI-RESET)
# ==========================================
def connect_sheets():
    try:
        creds_dict = dict(st.secrets["gcp"]) 
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("Data_Transaksi_POS").sheet1
    except Exception as e:
        st.error(f"Gagal koneksi ke Google Sheets. Periksa Streamlit Secrets kamu! Error: {e}")
        return None

def muat_data_transaksi():
    try:
        sheet = connect_sheets()
        if sheet:
            data = sheet.get_all_records()
            return pd.DataFrame(data)
    except Exception as e:
        pass
    return pd.DataFrame(columns=["Waktu", "Tanggal", "Platform", "Toko", "Produk", "Harga Jual", "Harga Modal", "Jumlah", "Biaya Admin %", "Biaya Fix", "Biaya Lain", "Total Omset", "Total Profit"])

def simpan_transaksi(platform, toko, produk, harga_jual, harga_modal, jumlah, biaya_lain, tanggal_pilihan):
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
    
    row = [
        jam, tanggal_str, platform, toko, produk,
        harga_jual, harga_modal, jumlah,
        total_admin_persen, admin_fix_rate, total_biaya_lain,
        total_omset, total_profit
    ]
    
    try:
        sheet = connect_sheets()
        if sheet:
            sheet.append_row(row)
    except Exception as e:
        st.error(f"Gagal menyimpan data ke Google Sheets: {e}")

# ==========================================
# 🔔 FITUR POP-UP TOAST QUEUE
# ==========================================
if "pesan_toast" in st.session_state and st.session_state.pesan_toast:
    st.toast(st.session_state.pesan_toast, icon=st.session_state.get("icon_toast", "✅"))
    st.session_state.pesan_toast = None
    st.session_state.icon_toast = "✅"

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
            try: os.remove(nama_file)
            except Exception: pass

validasi_dan_shared_clean(DB_MASTER_PRODUK, ["Produk"])
validasi_dan_shared_clean(DB_HARGA, ["Produk", "Harga Jual", "Harga Modal"])

# DATA KONFIGURASI KASIR
AKUN_USER = {
    "owner": {"password": "owner123", "role": "Owner"},
    "admin": {"password": "admin123", "role": "Admin"}
}

PRODUK_DEFAULT = [
    "Ayam Kampung Omega", "Ayam Kampung Omega Grade A", "Ayam Negri", 
    "Ayam Negri Omega", "Ayam Kampung Kuning", "Ayam Kampung Kuning Grade A", 
    "Puyuh", "Bebek", "Bebek Asin", "Kampung Omega (30 butir)", "Kampung Omega Grade A (30 butir)"
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
    "TikTok Shop": ["Utama"], "Lazada": ["Utama"], "Offline / WA": ["Toko Offline"]
}

# --- FUNGSI PRODUK & HARGA ---
def muat_daftar_produk():
    if os.path.exists(DB_MASTER_PRODUK):
        try:
            df = pd.read_csv(DB_MASTER_PRODUK)
            if not df.empty and "Produk" in df.columns:
                list_prod = df["Produk"].dropna().astype(str).str.strip().unique().tolist()
                return [p for p in list_prod if p != ""]
        except Exception: pass
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
        except Exception: pass
    default_data = [{"Produk": p, "Harga Jual": 100000, "Harga Modal": 60000} for p in daftar_produk_aktif]
    df = pd.DataFrame(default_data)
    df.to_csv(DB_HARGA, index=False)
    return df

def simpan_database_harga(df_baru):
    try: df_baru.to_csv(DB_HARGA, index=False)
    except Exception as e: st.error(f"Gagal menyimpan harga: {e}")

def tambah_produk_baru(nama_baru, h_jual, h_modal):
    nama_baru_clean = str(nama_baru).strip()
    daftar_produk = muat_daftar_produk()
    if nama_baru_clean.lower() in [p.lower() for p in daftar_produk]:
        return False, "Nama produk tersebut sudah terdaftar di sistem!"
    daftar_produk_baru = daftar_produk + [nama_baru_clean]
    pd.DataFrame({"Produk": daftar_produk_baru}).to_csv(DB_MASTER_PRODUK, index=False)
    df_harga = pd.read_csv(DB_HARGA) if os.path.exists(DB_HARGA) else pd.DataFrame(columns=["Produk", "Harga Jual", "Harga Modal"])
    df_harga = df_harga[df_harga["Produk"].str.lower() != nama_baru_clean.lower()]
    row_baru = pd.DataFrame([{"Produk": nama_baru_clean, "Harga Jual": int(h_jual), "Harga Modal": int(h_modal)}])
    pd.concat([df_harga, row_baru], ignore_index=True).to_csv(DB_HARGA, index=False)
    return True, f"Produk '{nama_baru_clean}' sukses terdaftar!"

def hapus_produk_by_name(nama_hapus):
    nama_hapus_clean = str(nama_hapus).strip()
    daftar_produk = muat_daftar_produk()
    if nama_hapus_clean not in daftar_produk: return False
    daftar_produk.remove(nama_hapus_clean)
    pd.DataFrame({"Produk": daftar_produk}).to_csv(DB_MASTER_PRODUK, index=False)
    if os.path.exists(DB_HARGA):
        df_harga = pd.read_csv(DB_HARGA)
        df_harga[df_harga["Produk"].str.lower() != nama_hapus_clean.lower()].to_csv(DB_HARGA, index=False)
    return True

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
                    st.session_state.update({"logged_in": True, "username": saved_user, "user_role": saved_role})
    except Exception: pass

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🔐 Login Sistem Kasir POS</h2>", unsafe_allow_html=True)
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        with st.form("form_login"):
            username_input = st.text_input("Username").strip().lower()
            password_input = st.text_input("Password", type="password")
            tetap_login = st.checkbox("Kunci Akun di Perangkat Ini (Ingat Saya / Auto-Login)", value=True)
            if st.form_submit_button("Masuk ke Sistem", use_container_width=True):
                if username_input in AKUN_USER and AKUN_USER[username_input]["password"] == password_input:
                    st.session_state.update({"logged_in": True, "user_role": AKUN_USER[username_input]["role"], "username": username_input})
                    if tetap_login:
                        with open(DB_SESSION, "w") as f: f.write(f"{username_input},{AKUN_USER[username_input]['role']}")
                    st.success(f"🎉 Login Berhasil sebagai {st.session_state.user_role}!")
                    st.rerun()
                else: st.error("❌ Username atau Password salah!")
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
        st.session_state.update({"logged_in": False, "user_role": None, "username": ""})
        st.rerun()

st.title("🏪 MESIN POS MULTI-MARKETPLACE")
st.write(f"Selamat bekerja, **{st.session_state.user_role}**! Data tersinkronisasi otomatis ke Google Sheets.")

tab1, tab2, tab3, tab4 = st.tabs([
    "📥 Input Transaksi Baru", "📈 Riwayat & Laporan Penjualan", 
    "⚙️ Kelola Manajemen Produk & Harga", "🧮 Kalkulator Simulasi Profit"
])

# --- TAB 1: INPUT TRANSAKSI ---
with tab1:
    st.subheader("Tambah Transaksi Baru")
    if not MASTER_PRODUK_AKTIF: st.warning("⚠️ Belum ada daftar produk di sistem.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🛍️ Detail Penjualan")
            waktu_jkt_now = datetime.utcnow() + timedelta(hours=7)
            input_tanggal_manual = st.date_input("Pilih Tanggal Transaksi", value=waktu_jkt_now.date(), key="input_tgl")
            platform_pilihan = st.selectbox("Pilih Platform Marketplace", options=list(KONS_MARKETPLACE.keys()))
            toko_pilihan = st.selectbox("Pilih Cabang Toko Anda", options=DAFTAR_TOKO_PLATFORM[platform_pilihan], key="pilih_toko_trx")
            nama_produk = st.selectbox("Nama Produk / SKU", options=MASTER_PRODUK_AKTIF)
            
            df_harga_terbaru = muat_database_harga()
            info_produk = df_harga_terbaru[df_harga_terbaru["Produk"] == nama_produk].iloc[0]
            harga_jual_default = int(info_produk["Harga Jual"])
            harga_modal_final = int(info_produk["Harga Modal"])
            
            if platform_pilihan == "Offline / WA":
                st.info("💡 Mode Offline Active: Kamu bebas mengubah angka harga jual khusus!")
                harga_jual_final = st.number_input("Harga Jual Khusus (Rp)", min_value=0, value=harga_jual_default, step=1000)
            else:
                harga_jual_final = harga_jual_default
                st.write(f"💵 **Harga Jual Terkunci ({platform_pilihan}):** Rp {harga_jual_final:,.0f}")
            st.write(f"📉 **Harga Modal Terkunci:** Rp {harga_modal_final:,.0f}")
            jumlah_terjual = st.number_input("Jumlah Terjual (pcs/pack)", min_value=1, value=1, key="jumlah")

        with col2:
            st.markdown("### 💸 Biaya Tambahan")
            biaya_lainnya = st.number_input("Biaya Lain-lain per Produk (Rp)", min_value=0, value=0, key="lain")
            p_persen = KONS_MARKETPLACE[platform_pilihan]["persen"]
            p_fix = KONS_MARKETPLACE[platform_pilihan]["fix"]
            st.info(f"**📋 Skema Potongan Admin ({platform_pilihan}):**\n* Admin Persen: **{p_persen}%**\n* Biaya Fix: **Rp {p_fix:,.0f}**")

        if st.button("💾 Simpan Transaksi Ke Database (Cloud)", type="primary", use_container_width=True):
            simpan_transaksi(platform_pilihan, toko_pilihan, nama_produk, harga_jual_final, harga_modal_final, jumlah_terjual, biaya_lainnya, input_tanggal_manual)
            st.session_state.pesan_toast = f"🎉 Sukses masuk ke Google Sheets untuk Toko [{toko_pilihan}]!"
            st.rerun()

# --- TAB 2: RIWAYAT & LAPORAN ---
with tab2:
    st.subheader("Riwayat & Analisis Penjualan")
    df_transaksi = muat_data_transaksi()
    
    if df_transaksi.empty: st.info("Belum ada data transaksi yang disimpan di Google Sheets.")
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
                
            if df_filtered.empty: st.warning("Data tidak ditemukan pada filter ini.")
            else:
                m1, m2 = st.columns(2)
                m1.metric("Total Omset", f"Rp {df_filtered['Total Omset'].sum():,.0f}")
                m2.metric("Total Terjual", f"{df_filtered['Jumlah'].sum()} pcs")
                
                st.markdown("### ✏️ Data Transaksi (Centang untuk Hapus - Admin & Owner)")
                df_tampilan = df_filtered.copy()
                df_tampilan.insert(0, "Pilih", False)
                df_tampilan["ID Asli"] = df_filtered.index
                
                df_edit = st.data_editor(
                    df_tampilan, hide_index=True, use_container_width=True,
                    disabled=[col for col in df_tampilan.columns if col != "Pilih"],
                    column_config={"Pilih": st.column_config.CheckboxColumn("Pilih", default=False)},
                    key="editor_transaksi_global"
                )
                
                perubahan = st.session_state.editor_transaksi_global.get("edited_rows", {})
                list_id_hapus = [df_tampilan.iloc[int(idx)]["ID Asli"] for idx, status in perubahan.items() if status.get("Pilih") == True]
                
                if list_id_hapus and st.button(f"❌ Hapus ({len(list_id_hapus)}) Transaksi Terpilih Dari Cloud"):
                    sheet = connect_sheets()
                    if sheet:
                        for idx in sorted(list_id_hapus, reverse=True):
                            sheet.delete_rows(idx + 2) # +2 karena header gsheet & 0-index dataframe
                        st.session_state.pesan_toast = "🗑️ Sukses menghapus data dari Google Sheets!"
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
                if st.form_submit_button("Tambahkan ke Sistem", use_container_width=True):
                    if input_nama_baru == "": st.error("Nama tidak boleh kosong!")
                    else:
                        sukses, pesan = tambah_produk_baru(input_nama_baru, input_harga_jual, input_harga_modal)
                        if sukses: st.session_state.pesan_toast = f"📥 Berhasil menambah {input_nama_baru}!"; st.rerun()
                        else: st.error(pesan)
        with col_del:
            st.markdown("### 🗑️ Hapus Menu Produk")
            if MASTER_PRODUK_AKTIF:
                df_hapus_prod = pd.DataFrame({"Pilih": [False] * len(MASTER_PRODUK_AKTIF), "Produk": MASTER_PRODUK_AKTIF})
                df_hapus_prod_centang = st.data_editor(df_hapus_prod, hide_index=True, use_container_width=True, disabled=["Produk"], column_config={"Pilih": st.column_config.CheckboxColumn("Pilih", default=False)}, key="editor_produk_hapus_centang")
                perubahan_prod = st.session_state.editor_produk_hapus_centang.get("edited_rows", {})
                list_prod_hapus = [df_hapus_prod.iloc[int(idx)]["Produk"] for idx, status in perubahan_prod.items() if status.get("Pilih") == True]
                if list_prod_hapus and st.button(f"❌ Hapus {len(list_prod_hapus)} Produk"):
                    for p_nama in list_prod_hapus: hapus_produk_by_name(p_nama)
                    st.rerun()
    
    st.markdown("## ⚙️ Update Harga Modal & Jual Pasar Hari Ini")
    if MASTER_PRODUK_AKTIF:
        df_editor = st.data_editor(df_harga_aktif, disabled=["Produk"], use_container_width=True, key="editor_harga", column_config={"Harga Jual": st.column_config.NumberColumn("Harga Jual (Rp)", format="%d"), "Harga Modal": st.column_config.NumberColumn("Harga Modal (Rp)", format="%d")})
        if st.button("💾 Simpan Perubahan Harga Hari Ini", type="primary", use_container_width=True):
            perubahan = st.session_state.editor_harga.get("edited_rows", {})
            for baris, kolom in perubahan.items():
                idx = int(baris)
                if "Harga Jual" in kolom: df_harga_aktif.at[idx, "Harga Jual"] = int(kolom["Harga Jual"])
                if "Harga Modal" in kolom: df_harga_aktif.at[idx, "Harga Modal"] = int(kolom["Harga Modal"])
            simpan_database_harga(df_harga_aktif)
            st.session_state.pesan_toast = "🚀 Sukses update harga hari ini!"; st.rerun()

# --- TAB 4: KALKULATOR SIMULASI PROFIT MASSAL ---
with tab4:
    st.subheader("🧮 Tabel Simulasi Profit Massal Semua Produk")
    if MASTER_PRODUK_AKTIF:
        platform_calc = st.selectbox("Target Platform Marketplace", options=list(KONS_MARKETPLACE.keys()), key="tab4_plat")
        admin_persen_def = KONS_MARKETPLACE[platform_calc]["persen"]
        df_base_harga = muat_database_harga()
        
        df_simulasi = pd.DataFrame({
            "Produk": df_base_harga["Produk"], "Harga Jual (Rp)": df_base_harga["Harga Jual"],
            "Harga Modal (Rp)": df_base_harga["Harga Modal"], "Qty (Pcs)": 1,
            "Admin (%)": float(admin_persen_def), "Packing (Rp)": 0, "Lain-lain (Rp)": 0
        })
        
        if "tabel_sim_state" not in st.session_state or st.session_state.get("prev_plat") != platform_calc:
            st.session_state.tabel_sim_state = df_simulasi.copy()
            st.session_state.prev_plat = platform_calc
            
        df_hasil_edit = st.data_editor(st.session_state.tabel_sim_state, disabled=["Produk", "Harga Modal (Rp)"], use_container_width=True, key="kalkulator_massal_editor")
        
        perubahan_kalkulator = st.session_state.kalkulator_massal_editor.get("edited_rows", {})
        for r_idx_str, cols_changed in perubahan_kalkulator.items():
            for c_name, new_val in cols_changed.items(): df_hasil_edit.at[int(r_idx_str), c_name] = new_val
        st.session_state.tabel_sim_state = df_hasil_edit.copy()
        
        st.markdown("### 📊 Live Hasil Perhitungan Profit Bersih")
        omset_kotor = df_hasil_edit["Harga Jual (Rp)"] * df_hasil_edit["Qty (Pcs)"]
        biaya_admin_total = (df_hasil_edit["Admin (%)"] / 100) * omset_kotor
        pengeluaran_total = (df_hasil_edit["Harga` Modal (Rp)"] * df_hasil_edit["Qty (Pcs)"]) + biaya_admin_total + (df_hasil_edit["Packing (Rp)"] * df_hasil_edit["Qty (Pcs)"]) + (df_hasil_edit["Lain-lain (Rp)"] * df_hasil_edit["Qty (Pcs)"])
        profit_total_bersih = omset_kotor - pengeluaran_total
        
        df_laporan_hasil = pd.DataFrame({
            "Nama Produk": df_hasil_edit["Produk"], "Total Omset Kotor": omset_kotor.map(lambda x: f"Rp {x:,.0f}"),
            "PROFIT BERSIH": profit_total_bersih.map(lambda x: f"Rp {x:,.0f}")
        })
        st.dataframe(df_laporan_hasil, use_container_width=True, hide_index=True)
