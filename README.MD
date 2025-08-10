# Prediksi Stok/Pejualaan Material – Aplikasi Streamlit

Aplikasi web untuk manajemen produk, pencatatan penjualan, dan prediksi penjualan material berbasis Streamlit + MySQL. Fokus utama: membantu toko/material mengelola data dan memproyeksikan kebutuhan stok secara praktis.

## Fitur Utama

- __Autentikasi pengguna__ (admin, staff, viewer)
- __Data Produk__: tambah, lihat, cari/filter produk
- __Data Penjualan__: tambah transaksi, filter berdasarkan tanggal/produk
- __Prediksi Penjualan__: proyeksi penjualan per produk secara harian/bulanan (fallback tersedia jika data minim)
- __Laporan__: ringkasan kinerja, visualisasi tren, ekspor CSV
- __Import Excel__: impor produk + penjualan dari file Excel terstruktur
- __Notifikasi Sukses__: toast saat tambah produk/penjualan berhasil
- __Mode Gelap__: tema default gelap via `.streamlit/config.toml`

## Arsitektur & Alur Halaman

- `app.py`
  - Inisialisasi DB (`DatabaseManager`) dan predictor (`SalesPredictor`)
  - Login → setelah berhasil, sidebar navigasi aktif
  - Routing halaman: `Dashboard`, `Data Produk`, `Data Penjualan`, `Prediksi Penjualan`, `Laporan`, `Kelola User` (khusus admin)

- `app_pages/`
  - `dashboard.py`: ringkasan metrik (opsional untuk diperluas)
  - `products.py`: 
    - Tab "Daftar Produk": tabel interaktif (AgGrid) + pencarian
    - Tab "Tambah Produk": form tambah produk → sukses memicu toast dan refresh
  - `sales.py`:
    - Tab "Data Penjualan": filter tanggal/produk, tabel interaktif, metrik total
    - Tab "Tambah Transaksi": form tambah transaksi → sukses memicu toast dan refresh
  - `prediction.py` (halaman): UI untuk memilih produk dan melihat hasil prediksi dari `SalesPredictor`
  - `reports.py`: ringkasan/visualisasi tren, opsi ekspor CSV

- `database.py`
  - Koneksi MySQL menggunakan konfigurasi dari `config.py`
  - Pembuatan database/tabel saat pertama jalan
  - CRUD: produk, penjualan, user, import Excel

- `prediction.py` (root)
  - `SalesPredictor`: pipeline pengambilan data penjualan per produk, pembersihan/fitur sederhana, dan prediksi (dengan beberapa fallback ketika data minim)

## Skema Database (MySQL)

- `users`
  - `id`, `username` (unik), `password_hash`, `role` (`admin|staff|viewer`), `created_at`
- `products`
  - `id`, `nama_produk`, `varian`, `jenis`, `harga`, `created_at`, `updated_at`
- `sales`
  - `id`, `tanggal`, `product_id` (FK → `products.id`), `jumlah`, `harga_satuan`, `total_harga`, `created_at`

Database dan tabel dibuat otomatis pada start aplikasi via `DatabaseManager.create_database_and_tables()`.

## Struktur Proyek

```
.
├── app.py
├── app_pages/
│   ├── __init__.py
│   ├── dashboard.py
│   ├── products.py
│   ├── sales.py
│   ├── prediction.py
│   └── reports.py
├── database.py
├── prediction.py              # SalesPredictor (logika prediksi)
├── config.py                  # Konfigurasi DB aktif
├── style.css                  # Styling kustom
├── .streamlit/
│   └── config.toml            # Tema (dark) dan opsi klien
├── requirements.txt
├── README.MD
└── archive/                   # Contoh data & util import awal
```

## Persyaratan

- Python 3.10+
- MySQL Server aktif dan kredensial sesuai `config.py`

## Instalasi & Menjalankan

1) Clone repo, lalu instal dependensi:

```bash
pip install -r requirements.txt
```

2) Konfigurasi database di `config.py`:

```python
DB_CONFIG = {
  'host': 'localhost',
  'user': 'root',
  'password': '<PASSWORD_ANDA>',
  'port': 3306,
  'database': 'stok_material_db'
}
ACTIVE_CONFIG = DB_CONFIG
```

3) Jalankan aplikasi:

```bash
streamlit run app.py
```

Pada run pertama, database & tabel akan dibuat otomatis. User default: `admin` / `admin123`.

## Konfigurasi Tema (Dark Mode)

File `/.streamlit/config.toml` sudah diisi untuk mode gelap default:

```toml
[theme]
base = "dark"
primaryColor = "#1E88E5"
backgroundColor = "#0E1117"
secondaryBackgroundColor = "#262730"
textColor = "#FAFAFA"
```

Catatan: `style.css` memiliki warna khusus untuk elemen tertentu. Jika ingin 100% mengikuti tema, sesuaikan warna yang hard-coded.

## Alur Kerja Utama

- __Login__ → masukkan `username` dan `password`
- __Dashboard__ → ringkasan (bisa dikembangkan)
- __Data Produk__
  - Lihat daftar produk (AgGrid), cari/filter
  - Tambah produk → jika sukses: muncul toast, data terbarui
- __Data Penjualan__
  - Lihat & filter transaksi
  - Tambah transaksi → jika sukses: muncul toast, data terbarui
- __Prediksi Penjualan__
  - Pilih produk → kalkulasi prediksi menggunakan `SalesPredictor`
  - Fallback disediakan jika data historis belum memadai
- __Laporan__
  - Visualisasi tren & ekspor CSV

## Detail Implementasi Penting

- __Inisialisasi DB__ (`app.py`):
  - `init_database()` memanggil `DatabaseManager()` → buat DB & tabel (jika belum ada)
  - Port MySQL kini diterapkan eksplisit saat koneksi (`database.py`)

- __Notifikasi Sukses__:
  - Produk: `app_pages/products.py` menggunakan `st.session_state["product_added_success"]` dan `st.toast(msg)` setelah rerun
  - Penjualan: `app_pages/sales.py` menggunakan `st.session_state["sale_added_success"]` dan `st.toast(msg)` setelah rerun

- __Import Excel__ (`database.py.import_excel_data`):
  - Membaca file Excel, cek produk, insert jika belum ada, lalu insert ke `sales`
  - Wajib kolom: `Tanggal, Produk, Varian, Jumlah, Jenis, Harga`

## Troubleshooting

- __Tidak bisa tambah produk/penjualan__:
  - Pastikan koneksi MySQL sesuai `config.py` (host, user, password, port, database)
  - Cek terminal/log untuk pesan error dari `database.py`

- __Mode gelap tidak aktif__:
  - Pastikan `.streamlit/config.toml` ada dan aplikasi direstart
  - `style.css` mungkin menimpa warna; sesuaikan jika perlu

## Roadmap Singkat

- Edit/Hapus data produk & transaksi
- Validasi/normalisasi input yang lebih ketat (hindari duplikat)
- Model prediksi yang lebih kaya (musiman, ARIMA/Prophet, dsb.)
- Peran pengguna lebih granular dan audit log
