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
            df_harga["Produk"] =
