def muat_database_harga():
    """Memuat tabel harga modal & jual berdasarkan master produk"""
    daftar_produk_aktif = muat_daftar_produk()
    
    if os.path.exists(DB_HARGA):
        try:
            df = pd.read_csv(DB_HARGA)
            if not df.empty and "Produk" in df.columns:
                # 1. Bersihkan produk yang sudah dihapus dari master produk aktif
                df = df[df["Produk"].isin(daftar_produk_aktif)]
                
                # 2. Tambah produk baru jika benar-benar belum terdaftar sama sekali
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

def tambah_produk_baru(nama_baru, h_jual, h_modal):
    """Menambahkan produk baru secara bersih langsung dengan harga pilihan owner"""
    daftar_produk = muat_daftar_produk()
    if nama_baru in daftar_produk:
        return False, "Nama produk sudah terdaftar di sistem!"
        
    # 1. Masukkan ke file master produk terlebih dahulu
    df_master = pd.DataFrame({"Produk": daftar_produk + [nama_baru]})
    df_master.to_csv(DB_MASTER_PRODUK, index=False)
    
    # 2. Baca database harga saat ini, atau buat baru jika kosong
    if os.path.exists(DB_HARGA):
        try:
            df_harga = pd.read_csv(DB_HARGA)
        except Exception:
            df_harga = pd.DataFrame(columns=["Produk", "Harga Jual", "Harga Modal"])
    else:
        df_harga = pd.DataFrame(columns=["Produk", "Harga Jual", "Harga Modal"])
        
    # 3. Langsung suntikkan produk baru beserta HARGA INPUTAN OWNER (bukan default)
    row_baru = pd.DataFrame([{"Produk": nama_baru, "Harga Jual": int(h_jual), "Harga Modal": int(h_modal)}])
    df_harga = pd.concat([df_harga, row_baru], ignore_index=True)
    
    # 4. Simpan hasil final ke file database harga
    df_harga.to_csv(DB_HARGA, index=False)
    return True, f"Produk '{nama_baru}' sukses ditambahkan dengan harga pilihan Anda!"
