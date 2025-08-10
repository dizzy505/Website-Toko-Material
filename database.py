import mysql.connector
from mysql.connector import Error
import pandas as pd
import bcrypt
from datetime import datetime
from config import ACTIVE_CONFIG

class DatabaseManager:
    def __init__(self):
        self.host = ACTIVE_CONFIG['host']
        self.database = ACTIVE_CONFIG['database']
        self.user = ACTIVE_CONFIG['user']
        self.password = ACTIVE_CONFIG['password']
        self.port = ACTIVE_CONFIG.get('port', 3306)
        
    def create_connection(self):
        try:
            connection = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port
            )
            return connection
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return None
    
    def create_database_and_tables(self):
        try:
            connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                port=self.port
            )
            cursor = connection.cursor()
            
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            cursor.execute(f"USE {self.database}")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role ENUM('admin', 'staff', 'viewer') DEFAULT 'staff',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nama_produk VARCHAR(100) NOT NULL,
                    varian VARCHAR(100),
                    jenis VARCHAR(50),
                    harga INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sales (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    tanggal DATE NOT NULL,
                    product_id INT,
                    jumlah FLOAT NOT NULL,
                    harga_satuan INT NOT NULL,
                    total_harga INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                )
            """)
            
            self.create_default_admin(cursor)
            
            connection.commit()
            print("Database and tables created successfully!")
            
        except Error as e:
            print(f"Error creating database: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def create_default_admin(self, cursor):
        try:
            cursor.execute("SELECT id FROM users WHERE username = 'admin'")
            if cursor.fetchone() is None:
                password = "admin123"
                hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                
                cursor.execute("""
                    INSERT INTO users (username, password_hash, role) 
                    VALUES (%s, %s, %s)
                """, ('admin', hashed.decode('utf-8'), 'admin'))
                print("Default admin user created (username: admin, password: admin123)")
        except Error as e:
            print(f"Error creating admin user: {e}")
    
    def authenticate_user(self, username, password):
        connection = self.create_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("""
                    SELECT id, username, password_hash, role 
                    FROM users WHERE username = %s
                """, (username,))
                user = cursor.fetchone()
                
                if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
                    return {
                        'id': user[0],
                        'username': user[1],
                        'role': user[3]
                    }
                return None
            except Error as e:
                print(f"Authentication error: {e}")
                return None
            finally:
                cursor.close()
                connection.close()
        return None
    
    def get_products(self):
        connection = self.create_connection()
        if connection:
            try:
                df = pd.read_sql("""
                    SELECT *
                    FROM products
                    ORDER BY nama_produk
                """, connection)
                return df
            except Error as e:
                print(f"Error fetching products: {e}")
                return pd.DataFrame()
            finally:
                connection.close()
        return pd.DataFrame()
    
    def add_product(self, nama_produk, varian, jenis, harga):
        connection = self.create_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("""
                    INSERT INTO products (nama_produk, varian, jenis, harga)
                    VALUES (%s, %s, %s, %s)
                """, (nama_produk, varian, jenis, harga))
                
                connection.commit()
                return True
            except Error as e:
                print(f"Error adding product: {e}")
                return False
            finally:
                cursor.close()
                connection.close()
        return False

    def get_users(self):
        connection = self.create_connection()
        if connection:
            try:
                df = pd.read_sql(
                    """
                    SELECT id, username, role, created_at
                    FROM users
                    ORDER BY created_at DESC
                    """,
                    connection,
                )
                return df
            except Error as e:
                print(f"Error fetching users: {e}")
                return pd.DataFrame()
            finally:
                connection.close()
        return pd.DataFrame()

    def add_user(self, username: str, password: str, role: str = 'staff'):
        connection = self.create_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                if cursor.fetchone():
                    return False, "Username sudah digunakan."

                hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                cursor.execute(
                    """
                    INSERT INTO users (username, password_hash, role)
                    VALUES (%s, %s, %s)
                    """,
                    (username, hashed, role),
                )
                connection.commit()
                return True, "OK"
            except Error as e:
                print(f"Error adding user: {e}")
                return False, "Gagal menambah user"
            finally:
                cursor.close()
                connection.close()
        return False, "Koneksi database gagal"

    def update_user_role(self, user_id: int, role: str) -> bool:
        connection = self.create_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute(
                    "UPDATE users SET role = %s WHERE id = %s",
                    (role, user_id),
                )
                connection.commit()
                return True
            except Error as e:
                print(f"Error updating user role: {e}")
                return False

    def update_user_password(self, user_id: int, new_password: str) -> bool:
        connection = self.create_connection()
        if connection:
            try:
                cursor = connection.cursor()
                hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE id = %s",
                    (hashed, user_id),
                )
                connection.commit()
                return True
            except Error as e:
                print(f"Error updating user password: {e}")
                return False
            finally:
                cursor.close()
                connection.close()
        return False

    def delete_user(self, user_id: int) -> bool:
        connection = self.create_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                connection.commit()
                return True
            except Error as e:
                print(f"Error deleting user: {e}")
                return False
            finally:
                cursor.close()
                connection.close()
        return False
    
    def get_sales_data(self):
        connection = self.create_connection()
        if connection:
            try:
                df = pd.read_sql("""
                    SELECT s.*, p.nama_produk, p.varian, p.jenis
                    FROM sales s
                    JOIN products p ON s.product_id = p.id
                    ORDER BY s.tanggal DESC
                """, connection)
                return df
            except Error as e:
                print(f"Error fetching sales data: {e}")
                return pd.DataFrame()
            finally:
                connection.close()
        return pd.DataFrame()
    
    def add_sale(self, tanggal, product_id, jumlah, harga_satuan):
        connection = self.create_connection()
        if connection:
            try:
                cursor = connection.cursor()
                total_harga = int(jumlah * harga_satuan)
                
                cursor.execute("""
                    INSERT INTO sales (tanggal, product_id, jumlah, harga_satuan, total_harga)
                    VALUES (%s, %s, %s, %s, %s)
                """, (tanggal, product_id, jumlah, harga_satuan, total_harga))
                
                connection.commit()
                return True
            except Error as e:
                print(f"Error adding sale: {e}")
                return False
            finally:
                cursor.close()
                connection.close()
        return False
    
    def import_excel_data(self, excel_file):
        try:
            df = pd.read_excel(excel_file)
            connection = self.create_connection()
            
            if connection:
                cursor = connection.cursor()
                
                for _, row in df.iterrows():
                    cursor.execute("""
                        SELECT id FROM products 
                        WHERE nama_produk = %s AND varian = %s
                    """, (row['Produk'], row['Varian']))
                    
                    product = cursor.fetchone()
                    
                    if not product:
                        cursor.execute("""
                            INSERT INTO products (nama_produk, varian, jenis, harga)
                            VALUES (%s, %s, %s, %s)
                        """, (row['Produk'], row['Varian'], row['Jenis'], row['Harga']))
                        product_id = cursor.lastrowid
                    else:
                        product_id = product[0]
                    
                    total_harga = int(row['Jumlah'] * row['Harga'])
                    cursor.execute("""
                        INSERT INTO sales (tanggal, product_id, jumlah, harga_satuan, total_harga)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (row['Tanggal'], product_id, row['Jumlah'], row['Harga'], total_harga))
                
                connection.commit()
                return True
                
        except Exception as e:
            print(f"Error importing Excel data: {e}")
            return False
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()
        
        return False
