import json
import streamlit as st
import os
import bcrypt  # Sistem keamanan password standar industri

# ==================== SETTINGAN AWAL FOLDER GAMBAR ====================
if not os.path.exists("img"):
    os.makedirs("img")

# ==================== FUNGSI UTILITY KEAMANAN (BCRYPT) ====================
def hash_password(password):
    """Mengubah teks password menjadi kode hash bcrypt dengan salt otomatis."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def check_password(password_input, password_database):
    """Memverifikasi apakah password input cocok dengan password di database."""
    return bcrypt.checkpw(password_input.encode('utf-8'), password_database.encode('utf-8'))

# ==================== FUNGSI UTILITY DATA ====================
def load_users():
    try:
        with open("users.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        # Akun master admin otomatis dibuat dengan bcrypt
        return {"admin": {"password": hash_password("123"), "role": "admin"}}

def save_users(users):
    with open("users.json", "w") as file:
        json.dump(users, file, indent=4)

def load_produk():
    try:
        with open("produk.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return [
            {"nama": "Kaos", "harga": 50000, "stok": 10, "foto": None},
            {"nama": "Celana", "harga": 100000, "stok": 5, "foto": None},
            {"nama": "Sepatu", "harga": 250000, "stok": 3, "foto": None}
        ]

def save_produk(produk):
    with open("produk.json", "w") as file:
        json.dump(produk, file, indent=4)


# ==================== INISIALISASI SESSION STATE ====================
if "login" not in st.session_state:
    st.session_state.login = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""

# Memastikan produk hanya di-load dari file JSON sekali saja di awal
if "produk" not in st.session_state:
    st.session_state.produk = load_produk()

if "keranjang" not in st.session_state:
    st.session_state.keranjang = []

# ==================== SIDEBAR NAVIGATION ====================
st.sidebar.title("Navigation")

if not st.session_state.login:
    menu = st.sidebar.selectbox("Menu Auth", ["Login", "Register"])
else:
    st.sidebar.write(f"Logged in as: **{st.session_state.username}** ({st.session_state.role})")
    
    list_menu = ["Belanja", "Keranjang & Checkout"]
    if st.session_state.role == "admin":
        list_menu.append("Admin Panel")
        
    menu = st.sidebar.radio("Pilih Halaman", list_menu)
    
    if st.sidebar.button("Logout"):
        st.session_state.login = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.session_state.keranjang = [] 
        st.rerun()

# ==================== HALAMAN AUTH (BELUM LOGIN) ====================
if not st.session_state.login:
    if menu == "Register":
        st.title("📝 Register Akun Baru")
        reg_username = st.text_input("Username Baru", key="reg_user")
        reg_password = st.text_input("Password Baru", type="password", key="reg_pass")
        konfirmasi = st.text_input("Konfirmasi Password", type="password", key="reg_konf")

        if st.button("Register"):
            users = load_users()
            if not reg_username:
                st.error("Username tidak boleh kosong!")
            elif reg_username in users:
                st.error("Username sudah terdaftar!")
            elif reg_password != konfirmasi:
                st.error("Konfirmasi password tidak cocok!")
            else:
                users[reg_username] = {
                    "password": hash_password(reg_password), 
                    "role": "user"
                }
                save_users(users)
                st.success("Register berhasil! Silakan pindah ke menu Login.")

    elif menu == "Login":
        st.title("🔐 Login Toko")
        login_username = st.text_input("Username", key="log_user")
        login_password = st.text_input("Password", type="password", key="log_pass")

        if st.button("Login"):
            users = load_users()
            
            if login_username in users:
                database_password_hash = users[login_username]["password"]
                
                # Memverifikasi kecocokan hash inputan vs database
                if check_password(login_password, database_password_hash):
                    st.session_state.login = True
                    st.session_state.username = login_username
                    st.session_state.role = users[login_username]["role"]
                    st.success("Login Berhasil!")
                    st.rerun()
                else:
                    st.error("Username atau password salah")
            else:
                st.error("Username atau password salah")

# ==================== HALAMAN TOKO (SUDAH LOGIN) ====================
else:
    # --- 1. HALAMAN BELANJA ---
    if menu == "Belanja":
        st.title("🛒 Toko Online Saya")
        
        # Fitur Pencarian Produk
        search_query = st.text_input("🔍 Cari produk yang kamu inginkan...", placeholder="Ketik nama produk di sini...")

        st.subheader("Daftar Produk Tersedia")

        # Proses Filter Pencarian
        if search_query:
            produk_ditampilkan = [
                p for p in st.session_state.produk 
                if search_query.lower() in p["nama"].lower()
            ]
        else:
            produk_ditampilkan = st.session_state.produk

        if not produk_ditampilkan:
            st.info(f"Produk dengan kata kunci '{search_query}' tidak ditemukan. Silakan cari produk lain!")
        
        # Render produk hasil saringan ke UI
        for item in produk_ditampilkan:
            jumlah_di_keranjang = sum(k["jumlah"] for k in st.session_state.keranjang if k["nama"] == item["nama"])
            stok_tampilan = item["stok"] - jumlah_di_keranjang

            col_foto, col_detail = st.columns([1, 2])

            with col_foto:
                if item.get("foto") and os.path.exists(item["foto"]):
                    st.image(item["foto"], use_container_width=True)
                else:
                    st.image("https://via.placeholder.com/150?text=No+Image", use_container_width=True)

            with col_detail:
                st.write(f"### {item['nama']}")
                st.write(f"Harga: **Rp{item['harga']}** | Stok Gudang: {item['stok']} *(Tersedia: {stok_tampilan})*")

                # Key tombol dinamis berdasarkan nama produk (aman dari bug indeks)
                clean_key = "".join(x for x in item["nama"] if x.isalnum())

                if stok_tampilan > 0:
                    if st.button(f"Tambah ke Keranjang ({item['nama']})", key=f"beli_{clean_key}"):
                        ada_di_keranjang = False
                        for k_item in st.session_state.keranjang:
                            if k_item["nama"] == item["nama"]:
                                k_item["jumlah"] += 1
                                ada_di_keranjang = True
                                break
                        
                        if not ada_di_keranjang:
                            st.session_state.keranjang.append({
                                "nama": item["nama"],
                                "harga": item["harga"],
                                "jumlah": 1
                            })

                        st.toast(f"{item['nama']} dimasukkan ke keranjang!")
                        st.rerun()
                else:
                    st.warning("Stok Terbatas / Sudah Penuh di Keranjang")
                    st.button(f"Beli {item['nama']}", disabled=True, key=f"habis_{clean_key}")
            st.divider()

    # --- 2. HALAMAN KERANJANG & CHECKOUT ---
    elif menu == "Keranjang & Checkout":
        st.title("🛍️ Keranjang Belanja Anda")

        if len(st.session_state.keranjang) == 0:
            st.info("Keranjang Anda masih kosong. Yuk belanja dulu!")
        else:
            total = 0
            
            col_h1, col_h2, col_h3, col_h4 = st.columns([3, 1, 1, 2])
            col_h1.write("**Nama Barang**")
            col_h2.write("**Aksi**")
            col_h3.write("**Qty**")
            col_h4.write("**Subtotal**")
            st.divider()

            for index, item in enumerate(list(st.session_state.keranjang)):
                col1, col2, col3, col4 = st.columns([3, 1, 1, 2])

                stok_asli_gudang = next((p["stok"] for p in st.session_state.produk if p["nama"] == item["nama"]), 0)

                with col1:
                    st.write(item["nama"])
                    st.caption(f"Harga: Rp{item['harga']}")

                with col2:
                    if st.button("➖", key=f"minus_{index}"):
                        if item["jumlah"] > 1:
                            item["jumlah"] -= 1
                        else:
                            st.session_state.keranjang.pop(index)
                        st.rerun()

                with col3:
                    st.write(f"**{item['jumlah']}**")

                subtotal = item["harga"] * item["jumlah"]
                total += subtotal

                with col4:
                    st.write(f"Rp{subtotal}")
                    if st.button("➕", key=f"plus_{index}"):
                        if item["jumlah"] < stok_asli_gudang:
                            item["jumlah"] += 1
                            st.rerun()
                        else:
                            st.error("Tidak bisa menambah barang, stok di gudang tidak mencukupi!")

                st.divider()

            diskon = 0
            if total >= 200000:
                diskon = total * 0.1
            total_akhir = total - diskon

            st.write(f"### Total Kotor: Rp{total}")
            if diskon > 0:
                st.write(f"### 🔥 Diskon Promo (10%): -Rp{int(diskon)}")
            st.write(f"## Total Akhir: Rp{int(total_akhir)}")

            if st.button("Selesaikan Pembayaran (Checkout)", type="primary"):
                gagal_checkout = False
                
                for k_item in st.session_state.keranjang:
                    for p in st.session_state.produk:
                        if p["nama"] == k_item["nama"]:
                            if p["stok"] < k_item["jumlah"]:
                                gagal_checkout = True
                                st.error(f"Maaf, stok {p['nama']} tiba-tiba habis/berkurang. Silakan sesuaikan keranjang.")
                
                if not gagal_checkout:
                    for k_item in st.session_state.keranjang:
                        for p in st.session_state.produk:
                            if p["nama"] == k_item["nama"]:
                                p["stok"] -= k_item["jumlah"]
                    
                    save_produk(st.session_state.produk)

                    with open("transaksi.txt", "a") as file:
                        file.write(f"Pembeli: {st.session_state.username} | Total Akhir: Rp{int(total_akhir)}\n")

                    st.session_state.keranjang = []
                    st.success("Checkout Berhasil! Stok resmi dikurangi gudang dan struk disimpan ke transaksi.txt 🎉")
                    st.balloons()
                    st.rerun()

    # --- 3. HALAMAN PANEL ADMIN ---
    elif menu == "Admin Panel" and st.session_state.role == "admin":
        st.title("⚙️ Admin Dashboard")
        
        tab1, tab2, tab3, tab4 = st.tabs(["➕ Tambah Produk", "✏️ Edit Stok", "🗑️ Hapus Menu Produk", "📝 Koreksi Transaksi"])
        
        with tab1:
            st.subheader("Tambah Produk Baru")
            new_nama = st.text_input("Nama Produk")
            new_harga = st.number_input("Harga (Rp)", min_value=0, step=1000)
            new_stok = st.number_input("Jumlah Stok Awal", min_value=0, step=1)
            
            uploaded_file = st.file_uploader("Upload Foto Produk", type=["jpg", "jpeg", "png"])
            
            if st.button("Simpan Produk Baru"):
                if new_nama:
                    saved_image_path = None
                    
                    if uploaded_file is not None:
                        file_extension = uploaded_file.name.split(".")[-1]
                        clean_nama = "".join(x for x in new_nama if x.isalnum())
                        saved_image_path = f"img/{clean_nama}.{file_extension}"
                        
                        with open(saved_image_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                    
                    st.session_state.produk.append({
                        "nama": new_nama, 
                        "harga": int(new_harga), 
                        "stok": int(new_stok),
                        "foto": saved_image_path
                    })
                    
                    save_produk(st.session_state.produk)
                    st.success(f"Produk {new_nama} berhasil ditambahkan!")
                    st.rerun()
                else:
                    st.error("Nama produk tidak boleh kosong!")

        with tab2:
            st.subheader("Ubah Stok Produk")
            list_nama_produk = [p["nama"] for p in st.session_state.produk]
            
            if list_nama_produk:
                pilih_produk = st.selectbox("Pilih produk yang mau diedit", list_nama_produk)
                
                stok_sekarang = 0
                for p in st.session_state.produk:
                    if p["nama"] == pilih_produk:
                        stok_sekarang = p["stok"]
                        break
                
                stok_baru = st.number_input("Set Stok Baru", min_value=0, value=stok_sekarang, step=1)
                
                if st.button("Update Stok"):
                    for p in st.session_state.produk:
                        if p["nama"] == pilih_produk:
                            p["stok"] = int(stok_baru)
                            break
                    
                    save_produk(st.session_state.produk)
                    st.success(f"Stok {pilih_produk} berhasil diubah menjadi {stok_baru}!")
                    st.rerun()
            else:
                st.write("Belum ada produk di toko.")

        # [UPGRADE CHECKBOX]: Tab Hapus Menu Produk (Ganti Dropdown ke Checkbox Multi-Delete)
        with tab3:
            st.subheader("🗑️ Hapus Menu Produk")

            if st.session_state.produk:
                st.write("Centang produk yang akan dibuang dari toko:")
                
                produk_dipilih = {}
                for p in st.session_state.produk:
                    label_produk = f"📦 {p['nama']} — (Harga: Rp{p['harga']} | Stok: {p['stok']})"
                    produk_dipilih[p["nama"]] = st.checkbox(label_produk, key=f"del_prod_chk_{p['nama']}")
                
                st.divider()
                list_nama_hapus = [nama for nama, dicentang in produk_dipilih.items() if dicentang]
                
                if list_nama_hapus:
                    st.warning(f"Kamu memilih **{len(list_nama_hapus)}** produk untuk dihapus dari toko.")
                    if st.button("❌ Hapus Produk Terpilih Selamanya", type="primary", key="btn_hapus_prod"):
                        for p in st.session_state.produk:
                            if p["nama"] in list_nama_hapus and p.get("foto") and os.path.exists(p["foto"]):
                                try:
                                    os.remove(p["foto"])
                                except:
                                    pass
                        
                        st.session_state.produk = [p for p in st.session_state.produk if p["nama"] not in list_nama_hapus]
                        save_produk(st.session_state.produk)
                        st.success(f"Produk terpilih berhasil dihapus!")
                        st.rerun()
                else:
                    st.button("Hapus Produk Terpilih Selamanya", disabled=True, key="btn_prod_disabled")
            else:
                st.info("Tidak ada produk di toko yang bisa dihapus.")

        # [UPGRADE CHECKBOX]: Tab Koreksi / Hapus Transaksi (Ganti Input Angka ID ke Checkbox Multi-Delete)
        with tab4:
            st.subheader("📝 Koreksi / Hapus Transaksi")

            if os.path.exists("transaksi.txt"):
                with open("transaksi.txt", "r") as file:
                    baris_transaksi = file.readlines()
                
                baris_transaksi = [b for b in baris_transaksi if b.strip()]

                if baris_transaksi:
                    st.write("Centang baris transaksi yang ingin dihapus:")
                    
                    transaksi_dipilih = {}
                    for idx, baris in enumerate(baris_transaksi):
                        transaksi_dipilih[idx] = st.checkbox(f"{baris.strip()}", key=f"tx_chk_{idx}")
                    
                    st.divider()
                    indeks_hapus = [idx for idx, dicentang in transaksi_dipilih.items() if dicentang]
                    
                    if indeks_hapus:
                        st.warning(f"Kamu memilih **{len(indeks_hapus)}** baris transaksi untuk dihapus.")
                        if st.button("🚨 Hapus Baris Terpilih", type="primary", key="btn_hapus_tx"):
                            sisa_transaksi = [baris for idx, baris in enumerate(baris_transaksi) if idx not in indeks_hapus]
                            
                            with open("transaksi.txt", "w") as file:
                                file.writelines(sisa_transaksi)
                            
                            st.success("Baris transaksi terpilih berhasil dihapus!")
                            st.rerun()
                    else:
                        st.button("Hapus Baris Terpilih", disabled=True, key="btn_tx_disabled")
                else:
                    st.info("Belum ada data transaksi di dalam file.")
            else:
                st.info("File transaksi.txt belum terbentuk.")
