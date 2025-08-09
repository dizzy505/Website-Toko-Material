import streamlit as st
from database import DatabaseManager
from prediction import SalesPredictor as StockPredictor
from app_pages import dashboard as page_dashboard, products as page_products, sales as page_sales, prediction as page_prediction, reports as page_reports
from app_pages import users as page_users

#Page config
st.set_page_config(
    page_title="Prediksi Stok Material",
    layout="wide",
    initial_sidebar_state="expanded"
)

#custom CSS
def load_css():
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

try:
    load_css()
except:
    pass

DB_CACHE_VERSION = 2

@st.cache_resource
def init_database(_version: int = DB_CACHE_VERSION):
    db = DatabaseManager()
    db.create_database_and_tables()
    return db

@st.cache_resource
def init_predictor(_db):
    return StockPredictor(_db)

db = init_database(DB_CACHE_VERSION)
predictor = init_predictor(db)

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'Dashboard'

def login_page():
    st.markdown("""
    <style>
        :root {
            --background-color: #0E1117; 
        }
        @media (prefers-color-scheme: light) {
            :root {
                --background-color: #FFFFFF;  
            }
        }
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            background-color: var(--background-color);
        }
        .login-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .login-header h2 {
            color: white;
            margin-bottom: 0.5rem;
        }
        .login-header p {
            color: #666;
            margin-top: 0;
        }
        .stTextInput>div>div>input {
            padding: 10px;
            border-radius: 5px;
            border: 1px solid #ddd;
        }
        .stButton>button {
            width: 100%;
            padding: 0.75rem;
            border-radius: 5px;
            background-color: #1E88E5;
            color: white;
            font-weight: 500;
            border: none;
            transition: background-color 0.3s;
        }
        .stButton>button:hover {
            background-color: #1565C0;
        }
    </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            with st.form("login_form"):
                st.markdown("""
                <div class="login-container">
                    <div class="login-header">
                        <h2>Login</h2>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                username = st.text_input("Username", placeholder="Masukkan username")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                
                submitted = st.form_submit_button("Masuk", use_container_width=True)
                
                st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
                
            if submitted:
                if username and password:
                    user = db.authenticate_user(username, password)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user = user
                        st.success("Login berhasil!")
                        st.rerun()
                    else:
                        st.error("Username atau password salah!")
                else:
                    st.warning("Mohon isi username dan password!")
    
def logout():
    st.session_state.logged_in = False
    st.session_state.user = None
    st.rerun()

def dashboard_page():
    page_dashboard.render(db)

def products_page():
    page_products.render(db)

def sales_page():
    page_sales.render(db)

def prediction_page():
    page_prediction.render(db, predictor)

def reports_page():
    page_reports.render(db)

def settings_page():
    st.header("Pengaturan")
    
    tab1, tab2 = st.tabs(["Import Data", "Pengaturan Sistem"])
    
    with tab1:
        st.subheader("Import Data dari Excel")
        
        uploaded_file = st.file_uploader(
            "Pilih file Excel",
            type=['xlsx', 'xls'],
            help="Upload file Excel dengan kolom: Tanggal, Produk, Varian, Jumlah, Jenis, Harga"
        )
        
        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file)
                st.subheader("Preview Data:")
                st.dataframe(df.head())
                
                required_columns = ['Tanggal', 'Produk', 'Varian', 'Jumlah', 'Jenis', 'Harga']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    st.error(f"Kolom yang hilang: {missing_columns}")
                else:
                    if st.button("Import Data"):
                        with st.spinner("Mengimport data..."):
                            if db.import_excel_data(uploaded_file):
                                st.success("Data berhasil diimport!")
                                st.rerun()
                            else:
                                st.error("Gagal mengimport data!")
            
            except Exception as e:
                st.error(f"Error membaca file: {str(e)}")
    
    with tab2:
        st.subheader("Pengaturan Sistem")
        
        st.info("Database: MySQL - stok_material_db")
        st.info("Default Admin: username: admin, password: admin123")
        
        if st.session_state.user and st.session_state.user['role'] == 'admin':
            st.warning("Admin Functions")
            
            if st.button("Reset Semua Data", type="secondary"):
                st.warning("Fitur ini akan menghapus semua data. Implementasi dapat ditambahkan sesuai kebutuhan.")

def main():    
    if not st.session_state.logged_in:
        login_page()
        return
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem; color: white;">
            <h3>Selamat datang</h3>
            <p><strong>{st.session_state.user['username']}</strong></p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.markdown("<h4 style='text-align: center;'>Menu Navigasi</h4>", unsafe_allow_html=True)
        
        nav_options = [
            ("Dashboard", "Dashboard"),
            ("Data Produk", "Data Produk"),
            ("Data Penjualan", "Data Penjualan"),
            ("Prediksi Penjualan", "Prediksi Penjualan"),
            ("Laporan", "Laporan"),
        ]
        if st.session_state.user and st.session_state.user.get('role') == 'admin':
            nav_options.append(("Kelola User", "Kelola User"))
        
        for icon, option in nav_options:
            if st.sidebar.button(
                option,
                key=f"nav_{option}",
                use_container_width=True,
                type="primary" if st.session_state.get('current_page') == option else "secondary"
            ):
                st.session_state.current_page = option
                st.rerun()
        
        st.markdown("---")
        
        if st.button("Logout", use_container_width=True, type="primary"):
            logout()
    
    if st.session_state.current_page == "Dashboard":
        page_dashboard.render(db)
    elif st.session_state.current_page == "Data Produk":
        page_products.render(db)
    elif st.session_state.current_page == "Data Penjualan":
        page_sales.render(db)
    elif st.session_state.current_page == "Prediksi Penjualan":
        page_prediction.render(db, predictor)
    elif st.session_state.current_page == "Kelola User":
        page_users.render(db)
    elif st.session_state.current_page == "Laporan":
        page_reports.render(db)

if __name__ == "__main__":
    main()
