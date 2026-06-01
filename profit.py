import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIG ---
st.set_page_config(page_title="POS Multi-Marketplace & Manajemen Harga", page_icon="🏪", layout="wide")

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
        # Buka dokumen utamanya dulu
        return client.open("Data_Transaksi_POS")
    except Exception as e:
        st.error(f"Gagal koneksi ke Google Drive/Sheets Cloud: {e}")
        return None

# --- DATABASE TRANSAKSI (TAB 1 & 2) ---
def muat_data_transaksi():
    try:
        doc = connect_sheets()
        if doc:
            # Panggil nama tab secara eksplisit di sini
            sheet = doc.worksheet("Transaksi")
            return pd.DataFrame(sheet.get_all_records())
    except: pass
    return pd.DataFrame(columns=["Waktu", "Tanggal", "Platform", "Toko", "Produk", "Harga Jual", "Harga Modal", "Jumlah", "Biaya Admin %", "Biaya Fix", "Biaya Lain", "Total Omset", "Total Profit"])

def simpan_transaksi(platform, toko, produk, harga_jual, harga_modal, jumlah, biaya_lain, tanggal_pilihan):
    jam = (datetime.utcnow() + timedelta(hours=7)).strftime("%H:%M:%S")
    tanggal_str = tanggal_pilihan.strftime("%Y-%m-%d")
    
    admin_persen_rate = KONS_MARKETPLACE[platform]["persen"]
    admin_fix_rate = KONS_MARKETPLACE[platform]["fix"]
    
    total_omset = harga_jual * jumlah
    total_modal = harga_modal * jumlah
    total_admin_persen = (admin_persen_rate / 100) * total_omset
    total_biaya_lain = biaya_lain * jumlah
    total_profit = total_omset - (total_modal + total_admin_persen + admin_fix_rate + total_biaya_lain)
    
    row = [jam, tanggal_str, platform, toko, produk, harga_jual, harga_modal, jumlah, total_admin_persen, admin_fix_rate, total_biaya_lain, total_omset, total_profit]
    try:
        doc = connect_sheets()
        if doc:
            doc.worksheet("Transaksi").append_row(row)
    except Exception as e: st.error(f"Gagal simpan transaksi ke Cloud: {e}")

# --- DATABASE PRODUK & HARGA CLOUD (TAB 3) ---
PRODUK_DEFAULT = ["Ayam Kampung Omega", "Ayam Kampung Omega Grade A", "Ayam Negri", "Ayam Negri Omega", "Ayam Kampung Kuning", "Ayam Kampung Kuning Grade A", "Puyuh", "Bebek", "Bebek Asin", "Kampung Omega (30 butir)", "Kampung Omega Grade A (30 butir)"]

def muat_daftar_produk():
    try:
        doc = connect_sheets()
        if doc:
            sheet = doc.worksheet("Master_Produk")
            df = pd.DataFrame(sheet.get_all_records())
            if not df.empty and "Produk" in df.columns:
                return df["Produk"].dropna().astype(str).str.strip().unique().tolist()
    except: pass
    return PRODUK_DEFAULT

def muat_database_harga():
    daftar_produk_aktif = muat_daftar_produk()
    try:
        doc = connect_sheets()
        if doc:
            sheet = doc.worksheet("Harga_Pasar")
            df = pd.DataFrame(sheet.get_all_records())
            if not df.empty and "Produk" in df.columns:
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
    except Exception as e: st.error(f"Gagal update harga ke Cloud: {e}")

def tambah_produk_baru(nama_baru, h_jual, h_modal):
    nama_clean = str(nama_baru).strip()
    daftar = muat_daftar_produk()
    if nama_clean.lower() in [p.lower() for p in daftar]:
        return False, "Produk sudah ada!"
        
    try:
        doc = connect_sheets()
        if doc:
            doc.worksheet("Master_Produk").append_row([nama_clean])
            doc.worksheet("Harga_Pasar").append_row([nama_clean, int(h_jual), int(h_modal)])
            return True, "Sukses"
    except Exception as e:
        return False, str(e)

# ==========================================
# 🔐 CONFIG & LOGIN SYSTEM
# ==========================================
AKUN_USER = {"owner": {"password": "owner123", "role": "Owner"}, "admin": {"password": "admin123", "role": "Admin"}}
KONS_MARKETPLACE = {"Shopee": {"persen": 12.50, "fix": 1250}, "Tokopedia": {"persen": 16.97, "fix": 0}, "TikTok Shop": {"persen": 8.00, "fix": 2000}, "Lazada": {"persen": 7.00, "fix": 1000}, "Offline / WA": {"persen": 0.00, "fix": 0}}
DAFTAR_TOKO_PLATFORM = {"Shopee": ["Sinar Bintang Telur", "EGGKU", "Astra Telur", "Telur88"], "Tokopedia": ["Sinar Bintang Telur", "SB Telur", "Astra Telur"], "TikTok Shop": ["Utama"], "Lazada": ["Utama"], "Offline / WA": ["Toko Offline"]}

if "logged_in" not in st.session_state: st.session_state.update({"logged_in": False, "user_role": None, "username": ""})
if not st.session_state.logged_in:
    with st.form("form_login"):
        u = st.text_input("Username").strip().lower()
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Masuk", use_container_width=True):
            if u in AKUN_USER and AKUN_USER[u]["password"] == p:
                st.session_state.update({"logged_in": True, "user_role": AKUN_USER[u]["role"], "username": u}); st.rerun()
            else: st.error("❌ Akun salah!")
    st.stop()

# --- SIDEBAR & POP-UP TOAST ---
if "pesan_toast" in st.session_state and st.session_state.pesan_toast:
    st.toast(st.session_state.pesan_toast, icon="✅")
    st.session_state.pesan_toast = None

with st.sidebar:
    st.write(f"👤 **{st.session_state.username}** ({st.session_state.user_role})")
    if st.button("🚪 Keluar", use_container_width=True):
        st.session_state.update({"logged_in": False}); st.rerun()

st.title("🏪 MESIN POS MULTI-MARKETPLACE (PURE CLOUD)")
MASTER_PRODUK_AKTIF = muat_daftar_produk()
tab1, tab2, tab3, tab4 = st.tabs(["📥 Input Transaksi Baru", "📈 Riwayat & Laporan Penjualan", "⚙️ Kelola Manajemen Produk & Harga", "🧮 Kalkulator Simulasi Profit"])

# --- TAB 1: INPUT TRANSAKSI ---
with tab1:
    st.subheader("Tambah Transaksi Baru")
    col1, col2 = st.columns(2)
    with col1:
        input_tanggal_manual = st.date_input("Pilih Tanggal", value=(datetime.utcnow() + timedelta(hours=7)).date())
        platform_pilihan = st.selectbox("Pilih Platform", options=list(KONS_MARKETPLACE.keys()))
        toko_pilihan = st.selectbox("Pilih Cabang", options=DAFTAR_TOKO_PLATFORM[platform_pilihan])
        nama_produk = st.selectbox("Nama Produk / SKU", options=MASTER_PRODUK_AKTIF)
        
        df_harga_terbaru = muat_database_harga()
        info_produk = df_harga_terbaru[df_harga_terbaru["Produk"] == nama_produk].iloc[0] if nama_produk in df_harga_terbaru["Produk"].values else {"Harga Jual": 100000, "Harga Modal": 60000}
        harga_jual_default, harga_modal_final = int(info_produk["Harga Jual"]), int(info_produk["Harga Modal"])
        
        if platform_pilihan == "Offline / WA":
            harga_jual_final = st.number_input("Harga Jual Khusus (Rp)", min_value=0, value=harga_jual_default, step=1000)
        else:
            harga_jual_final = harga_jual_default
            st.write(f"💵 **Harga Jual Terkunci:** Rp {harga_jual_final:,.0f}")
        st.write(f"📉 **Harga Modal Terkunci:** Rp {harga_modal_final:,.0f}")
        jumlah_terjual = st.number_input("Jumlah Terjual", min_value=1, value=1)
    with col2:
        biaya_lainnya = st.number_input("Biaya Lain-lain per Produk (Rp)", min_value=0, value=0)
        st.info(f"Potongan Admin {platform_pilihan}: {KONS_MARKETPLACE[platform_pilihan]['persen']}% + Rp {KONS_MARKETPLACE[platform_pilihan]['fix']}")

    if st.button("💾 Simpan Transaksi Ke Cloud", type="primary", use_container_width=True):
        simpan_transaksi(platform_pilihan, toko_pilihan, nama_produk, harga_jual_final, harga_modal_final, jumlah_terjual, biaya_lainnya, input_tanggal_manual)
        st.session_state.pesan_toast = "🎉 Sukses tersimpan di Cloud Google Sheets!"
        st.rerun()

# --- TAB 2: RIWAYAT & LAPORAN ---
with tab2:
    st.subheader("Riwayat Penjualan Cloud")
    df_transaksi = muat_data_transaksi()
    if df_transaksi.empty: st.info("Belum ada data di Google Sheets.")
    else:
        m1, m2 = st.columns(2)
        m1.metric("Total Omset", f"Rp {df_transaksi['Total Omset'].sum():,.0f}")
        m2.metric("Total Terjual", f"{df_transaksi['Jumlah'].sum()} pcs")
        
        df_tampilan = df_transaksi.copy()
        df_tampilan.insert(0, "Pilih", False)
        df_edit = st.data_editor(df_tampilan, hide_index=True, use_container_width=True, disabled=[col for col in df_tampilan.columns if col != "Pilih"], key="editor_transaksi_global")
        
        perubahan = st.session_state.editor_transaksi_global.get("edited_rows", {})
        list_id_hapus = [int(idx) for idx, status in perubahan.items() if status.get("Pilih") == True]
        if list_id_hapus and st.button(f"❌ Hapus ({len(list_id_hapus)}) Data Terpilih"):
            doc = connect_sheets()
            if doc:
                sheet = doc.worksheet("Transaksi")
                for idx in sorted(list_id_hapus, reverse=True): sheet.delete_rows(int(idx) + 2)
                st.rerun()

# --- TAB 3: MANAJEMEN PRODUK & HARGA CLOUD ---
with tab3:
    df_harga_aktif = muat_database_harga()
    if st.session_state.user_role == "Owner":
        st.markdown("## 🛠️ Menu Manajemen Produk (Khusus Owner)")
        with st.form("form_tambah_produk", clear_on_submit=True):
            input_nama_baru = st.text_input("Nama Produk Baru / SKU").strip()
            input_harga_jual = st.number_input("Harga Jual Awal (Rp)", min_value=0, value=100000)
            input_harga_modal = st.number_input("Harga Modal Awal (Rp)", min_value=0, value=60000)
            if st.form_submit_button("Tambahkan ke Cloud", use_container_width=True):
                if input_nama_baru:
                    sukses, pesan = tambah_produk_baru(input_nama_baru, input_harga_jual, input_harga_modal)
                    if sukses: st.rerun()
                    else: st.error(pesan)
    
    st.markdown("## ⚙️ Update Harga Pasar Hari Ini (Simpan ke Cloud)")
    if not df_harga_aktif.empty:
        df_editor = st.data_editor(df_harga_aktif, disabled=["Produk"], use_container_width=True, key="editor_harga")
        if st.button("💾 Simpan Perubahan Harga Hari Ini", type="primary", use_container_width=True):
            perubahan = st.session_state.editor_harga.get("edited_rows", {})
            for baris, kolom in perubahan.items():
                idx = int(baris)
                if "Harga Jual" in kolom: df_harga_aktif.at[idx, "Harga Jual"] = int(kolom["Harga Jual"])
                if "Harga Modal" in kolom: df_harga_aktif.at[idx, "Harga Modal"] = int(kolom["Harga Modal"])
            simpan_database_harga(df_harga_aktif)
            st.rerun()

# --- TAB 4: KALKULATOR SIMULASI ---
with tab4:
    st.subheader("🧮 Tabel Simulasi Profit Massal Semua Produk")
    platform_calc = st.selectbox("Target Platform Marketplace", options=list(KONS_MARKETPLACE.keys()), key="tab4_plat")
    admin_persen_def = KONS_MARKETPLACE[platform_calc]["persen"]
    
    df_simulasi = pd.DataFrame({"Produk": df_harga_aktif["Produk"], "Harga Jual (Rp)": df_harga_aktif["Harga Jual"], "Harga Modal (Rp)": df_harga_aktif["Harga Modal"], "Qty (Pcs)": 1, "Admin (%)": float(admin_persen_def), "Packing (Rp)": 0, "Lain-lain (Rp)": 0})
    df_hasil_edit = st.data_editor(df_simulasi, disabled=["Produk", "Harga Modal (Rp)"], use_container_width=True)
    
    omset_kotor = df_hasil_edit["Harga Jual (Rp)"] * df_hasil_edit["Qty (Pcs)"]
    biaya_admin_total = (df_hasil_edit["Admin (%)"] / 100) * omset_kotor
    pengeluaran_total = (df_hasil_edit["Harga Modal (Rp)"] * df_hasil_edit["Qty (Pcs)"]) + biaya_admin_total + (df_hasil_edit["Packing (Rp)"] * df_hasil_edit["Qty (Pcs)"]) + (df_hasil_edit["Lain-lain (Rp)"] * df_hasil_edit["Qty (Pcs)"])
    profit_total_bersih = omset_kotor - pengeluaran_total
    
    df_laporan_hasil = pd.DataFrame({"Nama Produk": df_hasil_edit["Produk"], "Total Omset Kotor": omset_kotor.map(lambda x: f"Rp {x:,.0f}"), "PROFIT BERSIH": profit_total_bersih.map(lambda x: f"Rp {x:,.0f}")})
    st.dataframe(df_laporan_hasil, use_container_width=True, hide_index=True)
