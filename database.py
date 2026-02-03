import sqlite3
from sqlite3 import Error
import config_manager
from datetime import datetime

DB_VERSION = 30

def _add_column_if_not_exists(conn, table_name, column_name, column_def):
    """Añade una columna a una tabla si no existe."""
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    columns = [info[1] for info in cur.fetchall()]
    if column_name not in columns:
        try:
            cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
            print(f"Columna '{column_name}' añadida a la tabla '{table_name}'.")
        except Error as e:
            print(f"Error al añadir la columna '{column_name}': {e}")

def create_connection():
    """Crea una conexión a la base de datos SQLite."""
    conn = None
    try:
        conn = sqlite3.connect('database.db')
        return conn
    except Error as e:
        print(e)
    return conn

def create_table(conn, create_table_sql):
    """Crea una tabla a partir de la declaración create_table_sql."""
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)



def setup_database():
    """Crea y actualiza las tablas de la base de datos si es necesario."""
    conn = create_connection()
    if conn is None:
        print("Error! No se pudo crear la conexión a la base de datos.")
        return

    current_db_version = config_manager.get_db_version()

    if current_db_version < 2:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(issuers)")
        if cur.fetchone():
            cur.execute("PRAGMA index_list(issuers)")
            indexes = cur.fetchall()
            has_old_unique_constraint = False
            for index in indexes:
                index_name = index[1]
                unique = index[2]
                if unique:
                    cur.execute(f"PRAGMA index_info('{index_name}')")
                    index_info = cur.fetchall()
                    cols = sorted([info[2] for info in index_info])
                    if cols == sorted(["name"]) or cols == sorted(["name", "address"]):
                        has_old_unique_constraint = True
                        break
            
            if has_old_unique_constraint:
                print("Migrando esquema de la tabla 'issuers'...")
                cur.execute("ALTER TABLE issuers RENAME TO _issuers_old")
                create_table(conn, """ CREATE TABLE IF NOT EXISTS issuers (
                                                    id integer PRIMARY KEY,
                                                    name text NOT NULL,
                                                    ruc text,
                                                    address text,
                                                    UNIQUE(name, ruc, address)
                                                ); """)
                cur.execute("INSERT INTO issuers (id, name, ruc, address) SELECT id, name, ruc, address FROM _issuers_old")
                cur.execute("DROP TABLE _issuers_old")
                print("Migración de 'issuers' completada.")
        
        config_manager.set_db_version(2)

    create_table(conn, """ CREATE TABLE IF NOT EXISTS products (
                                        id integer PRIMARY KEY,
                                        name text NOT NULL UNIQUE,
                                        price real NOT NULL,
                                        stock real NOT NULL,
                                        code text,
                                        unit_of_measure text DEFAULT 'NIU'
                                    ); """)
    create_table(conn, """ CREATE TABLE IF NOT EXISTS issuers (
                                        id integer PRIMARY KEY,
                                        name text NOT NULL,
                                        ruc text,
                                        address text,
                                        commercial_name text,
                                        logo blob,
                                        bank_accounts text,
                                        initial_greeting text,
                                        final_greeting text,
                                        district text,
                                        province text,
                                        department text,
                                        urbanization text,
                                        ubigeo text,
                                        gmail_password text,
                                        UNIQUE(name, ruc, address)
                                    ); """)

    create_table(conn, """ CREATE TABLE IF NOT EXISTS inventory_movements (
                                        id integer PRIMARY KEY,
                                        movement_type text NOT NULL, -- 'INGRESO' or 'SALIDA'
                                        movement_number text NOT NULL, -- 'IN-1', 'SA-1'
                                        date_time text NOT NULL,
                                        reason text,
                                        issuer_id integer,
                                        issuer_address text,
                                        total_amount real,
                                        FOREIGN KEY (issuer_id) REFERENCES issuers (id)
                                    ); """)

    create_table(conn, """ CREATE TABLE IF NOT EXISTS inventory_movement_items (
                                        id integer PRIMARY KEY,
                                        movement_id integer NOT NULL,
                                        product_id integer NOT NULL,
                                        quantity real NOT NULL,
                                        unit_of_measure text,
                                        price real,
                                        subtotal real,
                                        FOREIGN KEY (movement_id) REFERENCES inventory_movements (id),
                                        FOREIGN KEY (product_id) REFERENCES products (id)
                                    ); """)
    create_table(conn, """ CREATE TABLE IF NOT EXISTS sales (
                                    id integer PRIMARY KEY,
                                    issuer_id integer,
                                    sale_date timestamp DEFAULT CURRENT_TIMESTAMP,
                                    total_amount real NOT NULL,
                                    customer_id integer,
                                    observations text,
                                    document_type text,
                                    document_number text,
                                    payment_method text DEFAULT 'EFECTIVO',
                                    amount_paid real,
                                    payment_destination text,
                                    customer_address text,
                                    payment_method2 text DEFAULT 'NINGUNO',
                                    amount_paid2 real DEFAULT 0.0,
                                    FOREIGN KEY (issuer_id) REFERENCES issuers (id)
                                ); """)
    create_table(conn, """ CREATE TABLE IF NOT EXISTS sale_details (
                                            id integer PRIMARY KEY,
                                            sale_id integer NOT NULL,
                                            product_id integer NOT NULL,
                                            quantity_sold real NOT NULL,
                                            price_per_unit real NOT NULL,
                                            subtotal real NOT NULL,
                                            original_price real DEFAULT 0.0,
                                            FOREIGN KEY (sale_id) REFERENCES sales (id),
                                            FOREIGN KEY (product_id) REFERENCES products (id)
                                        ); """)
    create_table(conn, """ CREATE TABLE IF NOT EXISTS customers (
                                        id integer PRIMARY KEY,
                                        doc_number text UNIQUE,
                                        name text NOT NULL,
                                        phone text,
                                        address text,
                                        type text DEFAULT 'Cliente' NOT NULL,
                                        alias text
                                    ); """)

    _add_column_if_not_exists(conn, "sales", "customer_id", "integer")
    _add_column_if_not_exists(conn, "sales", "observations", "text")
    _add_column_if_not_exists(conn, "sales", "document_type", "text")
    _add_column_if_not_exists(conn, "sales", "document_number", "text")

    create_table(conn, """ CREATE TABLE IF NOT EXISTS correlatives (
                                        id integer PRIMARY KEY,
                                        issuer_id integer NOT NULL,
                                        doc_type text NOT NULL,
                                        series text NOT NULL,
                                        current_number integer NOT NULL,
                                        FOREIGN KEY (issuer_id) REFERENCES issuers (id),
                                        UNIQUE(issuer_id, doc_type)
                                    ); """)
    
    if current_db_version < 3:
        _add_column_if_not_exists(conn, "customers", "address", "text")
        _add_column_if_not_exists(conn, "customers", "type", "text DEFAULT 'Cliente' NOT NULL")
        config_manager.set_db_version(3)

    if current_db_version < 4:
        _add_column_if_not_exists(conn, "customers", "alias", "text")
        config_manager.set_db_version(4)

    if current_db_version <= 5:
        _add_column_if_not_exists(conn, "products", "unit_of_measure", "TEXT DEFAULT 'NIU'")
        _add_column_if_not_exists(conn, "sales", "payment_method", "TEXT DEFAULT 'EFECTIVO'")
        _add_column_if_not_exists(conn, "sales", "amount_paid", "REAL")
        _add_column_if_not_exists(conn, "sales", "payment_destination", "TEXT")
        _add_column_if_not_exists(conn, "sales", "customer_address", "TEXT")
        _add_column_if_not_exists(conn, "issuers", "commercial_name", "TEXT")
        config_manager.set_db_version(5)

    if current_db_version <= 6:
        _add_column_if_not_exists(conn, "issuers", "gmail_password", "TEXT")
        config_manager.set_db_version(6)
        _add_column_if_not_exists(conn, "issuers", "logo", "BLOB")
        _add_column_if_not_exists(conn, "issuers", "bank_accounts", "TEXT")
        _add_column_if_not_exists(conn, "issuers", "initial_greeting", "TEXT")
        _add_column_if_not_exists(conn, "issuers", "final_greeting", "TEXT")
        config_manager.set_db_version(5)

    if current_db_version < 6:
        _add_column_if_not_exists(conn, "sales", "payment_method2", "TEXT DEFAULT 'NINGUNO'")
        _add_column_if_not_exists(conn, "sales", "amount_paid2", "REAL DEFAULT 0.0")
        config_manager.set_db_version(6)

    if current_db_version < 27:
        _add_column_if_not_exists(conn, "issuers", "gmail_password", "TEXT")
        config_manager.set_db_version(27)
    
    if current_db_version <= 6:
        # Migrar datos de CUSTOMER/SUPPLIER a Cliente/Proveedor
        try:
            cur = conn.cursor()
            cur.execute("UPDATE customers SET type = 'Cliente' WHERE type = 'CUSTOMER'")
            cur.execute("UPDATE customers SET type = 'Proveedor' WHERE type = 'SUPPLIER'")
            conn.commit()
            print("Migración de datos de clientes/proveedores completada.")
        except Exception as e:
            print(f"Error en migración de datos: {e}")
        config_manager.set_db_version(6)

    if current_db_version <= 6:
        print("Actualizando base de datos a versión 7...")
        _add_column_if_not_exists(conn, "issuers", "district", "TEXT")
        _add_column_if_not_exists(conn, "issuers", "province", "TEXT")
        _add_column_if_not_exists(conn, "issuers", "department", "TEXT")
        _add_column_if_not_exists(conn, "issuers", "ubigeo", "TEXT")
        config_manager.set_db_version(7)
        print("Base de datos actualizada a versión 7.")

    if current_db_version <= 7:
        print("Actualizando base de datos a versión 8...")
        _add_column_if_not_exists(conn, "issuers", "sol_user", "TEXT")
        _add_column_if_not_exists(conn, "issuers", "sol_pass", "TEXT")
        _add_column_if_not_exists(conn, "issuers", "certificate", "BLOB")
        _add_column_if_not_exists(conn, "issuers", "fe_url", "TEXT")
        _add_column_if_not_exists(conn, "issuers", "re_url", "TEXT")
        _add_column_if_not_exists(conn, "issuers", "guia_url_envio", "TEXT")
        _add_column_if_not_exists(conn, "issuers", "guia_url_consultar", "TEXT")
        _add_column_if_not_exists(conn, "issuers", "client_id", "TEXT")
        _add_column_if_not_exists(conn, "issuers", "client_secret", "TEXT")
        _add_column_if_not_exists(conn, "issuers", "validez_user", "TEXT")
        _add_column_if_not_exists(conn, "issuers", "validez_pass", "TEXT")
        config_manager.set_db_version(8)
        print("Base de datos actualizada a versión 8.")

    if current_db_version <= 8:
        print("Actualizando base de datos a versión 9...")
        _add_column_if_not_exists(conn, "issuers", "email", "TEXT")
        _add_column_if_not_exists(conn, "issuers", "phone", "TEXT")
        _add_column_if_not_exists(conn, "products", "operation_type", "TEXT DEFAULT 'Gravada'")
        config_manager.set_db_version(9)
        print("Base de datos actualizada a versión 9.")

    if current_db_version <= 9:
        print("Actualizando base de datos a versión 10...")
        _add_column_if_not_exists(conn, "issuers", "default_operation_type", "TEXT DEFAULT 'Gravada'")
        config_manager.set_db_version(10)
        print("Base de datos actualizada a versión 10.")
    
    if current_db_version <= 10:
        print("Actualizando base de datos a versión 11...")
        _add_column_if_not_exists(conn, "products", "issuer_name", "TEXT")
        _add_column_if_not_exists(conn, "products", "issuer_address", "TEXT")
        config_manager.set_db_version(11)
        print("Base de datos actualizada a versión 11.")
    
    if current_db_version <= 11:
        print("Actualizando base de datos a versión 12...")
        _add_column_if_not_exists(conn, "products", "is_active", "INTEGER DEFAULT 1")
        config_manager.set_db_version(12)
        print("Base de datos actualizada a versión 12.")

    if current_db_version <= 12:
        print("Actualizando base de datos a versión 13...")
        # Eliminar restricción UNIQUE(name, ruc, address) de issuers
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys=OFF")
            cur.execute("ALTER TABLE issuers RENAME TO _issuers_old_v13")
            
            # Recrear tabla sin la restricción UNIQUE
            create_table(conn, """ CREATE TABLE IF NOT EXISTS issuers (
                                        id integer PRIMARY KEY,
                                        name text NOT NULL,
                                        ruc text,
                                        address text,
                                        commercial_name text,
                                        logo blob,
                                        bank_accounts text,
                                        initial_greeting text,
                                        final_greeting text,
                                        district text,
                                        province text,
                                        department text,
                                        ubigeo text,
                                        sol_user text,
                                        sol_pass text,
                                        certificate blob,
                                        fe_url text,
                                        re_url text,
                                        guia_url_envio text,
                                        guia_url_consultar text,
                                        client_id text,
                                        client_secret text,
                                        validez_user text,
                                        validez_pass text,
                                        email text,
                                        phone text,
                                        default_operation_type text DEFAULT 'Gravada',
                                        gmail_password text
                                    ); """)
            
            # Copiar datos
            # Asegurarse de listar TODAS las columnas que existían en la v12
            # Nota: gmail_password se agrega con valor NULL para registros existentes
            columns_old = "id, name, ruc, address, commercial_name, logo, bank_accounts, initial_greeting, final_greeting, district, province, department, ubigeo, sol_user, sol_pass, certificate, fe_url, re_url, guia_url_envio, guia_url_consultar, client_id, client_secret, validez_user, validez_pass, email, phone, default_operation_type"
            cur.execute(f"INSERT INTO issuers ({columns_old}) SELECT {columns_old} FROM _issuers_old_v13")
            
            cur.execute("DROP TABLE _issuers_old_v13")
            cur.execute("PRAGMA foreign_keys=ON")
            config_manager.set_db_version(13)
            print("Base de datos actualizada a versión 13 (Restricción única eliminada).")
        except Exception as e:
            print(f"Error en migración v13: {e}")
            if conn:
                conn.rollback()

    if current_db_version <= 13:
        print("Actualizando base de datos a versión 14...")
        _add_column_if_not_exists(conn, "products", "category", "TEXT DEFAULT 'General'")
        _add_column_if_not_exists(conn, "sale_details", "original_price", "REAL DEFAULT 0.0")
        config_manager.set_db_version(14)
        print("Base de datos actualizada a versión 14.")

    if current_db_version <= 14:
        print("Actualizando base de datos a versión 15...")
        create_table(conn, """ CREATE TABLE IF NOT EXISTS users (
                                    id integer PRIMARY KEY,
                                    username text NOT NULL UNIQUE,
                                    password text NOT NULL,
                                    permissions text,
                                    is_active integer DEFAULT 1
                                ); """)
        
        # Seed default admin user if table is empty
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM users")
        if cur.fetchone()[0] == 0:
            # Password 'admin' hashed with SHA-256: 8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918
            # Using simple hashing for now as requested, or just plain text if not specified? 
            # User asked for "crea una contraseña que sea por defecto usuario:admin y contraseña:admin"
            # I will use SHA256 for security best practice even if simple.
            import hashlib
            default_pass = hashlib.sha256("admin".encode()).hexdigest()
            # Admin has all permissions (empty or specific keyword, let's use 'all' or just handle it in code)
            # Let's say 'admin' role or just all modules.
            # For now, let's store "admin" in permissions to signify superuser, or list all modules.
            # Simpler: "admin" keyword in permissions means everything.
            cur.execute("INSERT INTO users (username, password, permissions) VALUES (?, ?, ?)", ("admin", default_pass, "admin"))
            conn.commit()
            print("Usuario admin por defecto creado.")
            
        config_manager.set_db_version(15)
        print("Base de datos actualizada a versión 15.")

    if current_db_version <= 15:
        print("Actualizando base de datos a versión 16...")
        create_cash_counts_table(conn)
        config_manager.set_db_version(16)
        print("Base de datos actualizada a versión 16.")

    if current_db_version <= 16:
        print("Actualizando base de datos a versión 17...")
        # Migration for extended cash counts
        _add_column_if_not_exists(conn, "cash_counts", "initial_balance", "REAL DEFAULT 0.0")
        _add_column_if_not_exists(conn, "cash_counts", "system_cards", "REAL DEFAULT 0.0")
        _add_column_if_not_exists(conn, "cash_counts", "expenses", "REAL DEFAULT 0.0")
        _add_column_if_not_exists(conn, "cash_counts", "counted_cards", "REAL DEFAULT 0.0")
        _add_column_if_not_exists(conn, "cash_counts", "change_next_day", "REAL DEFAULT 0.0")
        _add_column_if_not_exists(conn, "cash_counts", "collected_total", "REAL DEFAULT 0.0")
        _add_column_if_not_exists(conn, "cash_counts", "details_json", "TEXT")
        config_manager.set_db_version(17)
        print("Base de datos actualizada a versión 17.")

    # Always check/create temp_expenses table to avoid missing table errors
    create_temp_expenses_table(conn)

    if current_db_version <= 18: 
        # Changed 17 to 18 to force upgrade/check or just ensuring it runs
        if current_db_version < 18:
             config_manager.set_db_version(18)

    if current_db_version <= 18:
        print("Actualizando base de datos a versión 19 (Notificaciones)...")
        _add_column_if_not_exists(conn, "issuers", "whatsapp_sender", "TEXT")
        _add_column_if_not_exists(conn, "issuers", "whatsapp_receivers", "TEXT")
        _add_column_if_not_exists(conn, "issuers", "gmail_sender", "TEXT")
        _add_column_if_not_exists(conn, "issuers", "gmail_receivers", "TEXT")
        config_manager.set_db_version(19)

    if current_db_version <= 20: 
        print("Actualizando base de datos a versión 21 (Campos Arqueo Fase 2)...")
        _add_column_if_not_exists(conn, "cash_counts", "opening_time", "TEXT")
        _add_column_if_not_exists(conn, "cash_counts", "accumulated_cash", "REAL DEFAULT 0.0")
        _add_column_if_not_exists(conn, "cash_counts", "stock_value", "REAL DEFAULT 0.0")
        _add_column_if_not_exists(conn, "cash_counts", "sales_cash", "REAL DEFAULT 0.0")
        _add_column_if_not_exists(conn, "cash_counts", "income_additional", "REAL DEFAULT 0.0")
        _add_column_if_not_exists(conn, "cash_counts", "purchases", "REAL DEFAULT 0.0")
        _add_column_if_not_exists(conn, "cash_counts", "anulados", "REAL DEFAULT 0.0")
        _add_column_if_not_exists(conn, "cash_counts", "returns", "REAL DEFAULT 0.0")
        _add_column_if_not_exists(conn, "cash_counts", "withdrawal", "REAL DEFAULT 0.0")
        config_manager.set_db_version(21)
        print("Base de datos actualizada a versión 19.")

    if current_db_version < 20:
        cur = conn.cursor()
        try:
            cur.execute("ALTER TABLE cash_counts ADD COLUMN accumulated_cash REAL DEFAULT 0.0")
            print("Columna 'accumulated_cash' añadida a 'cash_counts'.")
        except Error: pass
        
        try:
            cur.execute("ALTER TABLE cash_counts ADD COLUMN stock_value REAL DEFAULT 0.0")
            print("Columna 'stock_value' añadida a 'cash_counts'.")
        except Error: pass
        
        try:
            cur.execute("ALTER TABLE cash_counts ADD COLUMN opening_time TEXT")
            print("Columna 'opening_time' añadida a 'cash_counts'.")
        except Error: pass

        config_manager.set_db_version(20)
        print("Base de datos actualizada a versión 20.")
        
    if current_db_version <= 20:
        print("Actualizando base de datos a versión 21...")
         # Clean up previous failed attempt logic if needed, or leave blank/noop
        config_manager.set_db_version(21)
        print("Base de datos actualizada a versión 21.")
    
    # Asegurar tablas y columnas de gastos siempre
    create_expenses_history_table(conn)
    _add_column_if_not_exists(conn, "temp_expenses", "detail_2", "TEXT")

    if current_db_version <= 21:
        print("Actualizando base de datos a versión 22 (Gastos Históricos)...")
        config_manager.set_db_version(22)
        print("Base de datos actualizada a versión 22.")

    if current_db_version <= 22:
        print("Actualizando base de datos a versión 23 (Imágenes de Productos)...")
        _add_column_if_not_exists(conn, "products", "image", "BLOB")
        config_manager.set_db_version(23)
        print("Base de datos actualizada a versión 23.")

    if current_db_version <= 23:
        print("Actualizando base de datos a versión 24 (Código Establecimiento)...")
        _add_column_if_not_exists(conn, "issuers", "establishment_code", "TEXT DEFAULT '0000'")
        config_manager.set_db_version(24)
        print("Base de datos actualizada a versión 24.")

    if current_db_version <= 24:
        print("Actualizando base de datos a versión 25 (Contraseña Certificado)...")
        _add_column_if_not_exists(conn, "issuers", "cert_password", "TEXT")
        config_manager.set_db_version(25)
        print("Base de datos actualizada a versión 25.")

    if current_db_version <= 25:
        print("Actualizando base de datos a versión 26 (Status CPE & Alertas)...")
        _add_column_if_not_exists(conn, "issuers", "cpe_alert_receivers", "TEXT")
        _add_column_if_not_exists(conn, "sales", "sunat_status", "TEXT")
        _add_column_if_not_exists(conn, "sales", "sunat_note", "TEXT")
        _add_column_if_not_exists(conn, "sales", "cdr_path", "TEXT")

        config_manager.set_db_version(26)
        print("Base de datos actualizada a versión 26.")

    if current_db_version <= 26:
        print("Actualizando base de datos a versión 27 (Campo is_active en usuarios)...")
        _add_column_if_not_exists(conn, "users", "is_active", "INTEGER DEFAULT 1")
        config_manager.set_db_version(27)
        print("Base de datos actualizada a versión 27.")
        _add_column_if_not_exists(conn, "sale_details", "original_price", "REAL DEFAULT 0.0")
        config_manager.set_db_version(27)
        print("Base de datos actualizada a versión 27.")

    if current_db_version <= 27:
        print("Actualizando base de datos a versión 28 (Fix Unique Username)...")
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys=OFF")
            
            # 1. Rename old table
            cur.execute("ALTER TABLE users RENAME TO _users_old_v28")
            
            # 2. Create new table properly (WITHOUT UNIQUE on username inline)
            # Note: We keep ID, username, password, permissions, is_active
            create_table(conn, """ CREATE TABLE IF NOT EXISTS users (
                                        id integer PRIMARY KEY,
                                        username text NOT NULL,
                                        password text NOT NULL,
                                        permissions text,
                                        is_active integer DEFAULT 1
                                    ); """)
            
            # 3. Copy data
            # Check columns in old table to be safe
            cur.execute("PRAGMA table_info(_users_old_v28)")
            cols = [info[1] for info in cur.fetchall()]
            query_cols = "id, username, password, permissions, is_active"
            # If is_active didn't exist in older versions for some reason, we handle it? 
            # We just ensured is_active exists in v27.
            
            cur.execute(f"INSERT INTO users ({query_cols}) SELECT {query_cols} FROM _users_old_v28")
            
            # 4. Create Partial Index
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_active ON users(username) WHERE is_active = 1")
            
            # 5. Cleanup
            cur.execute("DROP TABLE _users_old_v28")
            cur.execute("PRAGMA foreign_keys=ON")
            
            config_manager.set_db_version(28)
            print("Base de datos actualizada a versión 28.")
        except Exception as e:
            print(f"Error en migración v28: {e}")
            if conn: conn.rollback()
    
    if current_db_version < 29:
        print("Actualizando base de datos a versión 29: Renombrando PROFORMA → NOTA DE VENTA...")
        try:
            cur = conn.cursor()
            # Update correlatives table
            cur.execute("UPDATE correlatives SET doc_type = 'NOTA DE VENTA' WHERE doc_type = 'PROFORMA'")
            
            # Update sales table
            cur.execute("UPDATE sales SET document_type = 'NOTA DE VENTA' WHERE document_type = 'PROFORMA'")
            
            conn.commit()
            config_manager.set_db_version(29)
            print("Base de datos actualizada: PROFORMA → NOTA DE VENTA")
        except Exception as e:
            print(f"Error en migración PROFORMA v29: {e}")
            if conn: conn.rollback()

    if current_db_version < 30:
        print("Actualizando base de datos a versión 30: Eliminando restricción UNIQUE en nombre de productos...")
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys=OFF")
            
            # 1. Rename old table
            cur.execute("ALTER TABLE products RENAME TO _products_old_v30")
            
            # 2. Create new table WITHOUT UNIQUE on name
            create_table(conn, """ CREATE TABLE IF NOT EXISTS products (
                                        id integer PRIMARY KEY,
                                        name text NOT NULL,
                                        price real NOT NULL,
                                        stock real NOT NULL,
                                        code text,
                                        unit_of_measure text DEFAULT 'NIU',
                                        operation_type text DEFAULT 'Gravada',
                                        issuer_name text,
                                        issuer_address text,
                                        category text DEFAULT 'General',
                                        image blob,
                                        is_active integer DEFAULT 1
                                    ); """)
            
            # 3. Copy all data from old table
            cur.execute("""INSERT INTO products 
                          (id, name, price, stock, code, unit_of_measure, operation_type, 
                           issuer_name, issuer_address, category, image, is_active)
                          SELECT id, name, price, stock, code, unit_of_measure, operation_type,
                                 issuer_name, issuer_address, category, image, is_active 
                          FROM _products_old_v30""")
            
            # 4. Drop old table
            cur.execute("DROP TABLE _products_old_v30")
            
            # 5. Create unique index for code per issuer/address (only for active products)
            cur.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_products_code_issuer 
                          ON products(code, issuer_name, issuer_address) 
                          WHERE code IS NOT NULL AND code != '' AND is_active = 1""")
            
            cur.execute("PRAGMA foreign_keys=ON")
            conn.commit()
            config_manager.set_db_version(30)
            print("Base de datos actualizada a versión 30: Restricción UNIQUE en nombre eliminada.")
        except Exception as e:
            print(f"Error en migración v30: {e}")
            if conn: conn.rollback()
            
    conn.close()

def add_user(username, password, permissions):
    conn = create_connection()
    sql = 'INSERT INTO users(username, password, permissions) VALUES(?,?,?)'
    cur = conn.cursor()
    try:
        cur.execute(sql, (username, password, permissions))
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_all_users():
    conn = create_connection()
    cur = conn.cursor()
    # Fetch password too (as 4th column)
    cur.execute("SELECT id, username, permissions, password FROM users WHERE is_active = 1 ORDER BY username")
    rows = cur.fetchall()
    print(f"DEBUG: get_all_users fetched {len(rows)} active users.")
    conn.close()
    return rows

def update_user(user_id, username, password, permissions):
    conn = create_connection()
    if password:
        sql = 'UPDATE users SET username = ?, password = ?, permissions = ? WHERE id = ?'
        params = (username, password, permissions, user_id)
    else:
        sql = 'UPDATE users SET username = ?, permissions = ? WHERE id = ?'
        params = (username, permissions, user_id)
        
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_user(user_id):
    conn = create_connection()
    # Soft delete
    sql = 'UPDATE users SET is_active = 0 WHERE id=?'
    try:
        cur = conn.cursor()
        cur.execute(sql, (user_id,))
        deleted = cur.rowcount
        conn.commit()
        print(f"DEBUG: Soft deleted user {user_id}, rowcount: {deleted}")
        return deleted > 0
    except Exception as e:
        print(f"ERROR deleting user {user_id}: {e}")
        return False
    finally:
        conn.close()

def get_user_by_credentials(username, password_hash):
    conn = create_connection()
    cur = conn.cursor()
    # Case insensitive username check
    cur.execute("SELECT id, username, permissions FROM users WHERE lower(username) = ? AND password = ? AND is_active = 1", (username.lower(), password_hash))
    return cur.fetchone()

def user_has_password(user_id):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE id = ? AND is_active = 1", (user_id,))
    row = cur.fetchone()
    if row and row[0]:
        # Check if hash represents empty string or None
        empty_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" # SHA256 of ""
        return row[0] != empty_hash
    return False

def check_user_password(user_id, password_input):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE id = ? AND is_active = 1", (user_id,))
    row = cur.fetchone()
    if row:
        stored_hash = row[0]
        input_hash = hashlib.sha256(password_input.encode()).hexdigest()
        return stored_hash == input_hash
    return False

def get_active_user_by_username(username):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, permissions, password FROM users WHERE lower(username) = ? AND is_active = 1", (username.lower(),))
    return cur.fetchone()

def get_users_by_permission(permission_name):
    """
    Returns a list of users (tuple: id, username, permissions) who have the specified permission.
    Permissions are stored as a CSV string.
    """
    conn = create_connection()
    cur = conn.cursor()
    # Fetch all active users and filter in python to avoid complex LIKE queries
    # Assuming volume is low.
    cur.execute("SELECT id, username, permissions, password FROM users WHERE is_active = 1")
    rows = cur.fetchall()
    conn.close()
    
    matching_users = []
    for row in rows:
        perms_str = row[2]
        if perms_str:
            perms_list = [p.strip() for p in perms_str.split(",")]
            if permission_name in perms_list:
                matching_users.append(row)
    
    return matching_users

def get_user_by_id(user_id):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, permissions, password FROM users WHERE id = ? AND is_active = 1", (user_id,))
    return cur.fetchone()


def add_product(name, price, stock, code, unit_of_measure, operation_type="Gravada", issuer_name=None, issuer_address=None, category="General", image=None):
    conn = create_connection()
    sql = 'INSERT INTO products(name, price, stock, code, unit_of_measure, operation_type, issuer_name, issuer_address, category, image) VALUES(?,?,?,?,?,?,?,?,?,?)'
    cur = conn.cursor()
    cur.execute(sql, (name, price, stock, code, unit_of_measure, operation_type, issuer_name, issuer_address, category, image))
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id

def get_all_products(issuer_name=None, issuer_address=None):
    conn = create_connection()
    cur = conn.cursor()
    
    query = "SELECT id, name, price, stock, code, unit_of_measure, operation_type, issuer_name, issuer_address, category, image, is_active FROM products"
    params = []
    filters = []
    
    if issuer_name and issuer_name != "Todas":
        filters.append("issuer_name = ?")
        params.append(issuer_name)
    
    if issuer_address and issuer_address != "Todas":
        filters.append("issuer_address = ?")
        params.append(issuer_address)
        
    if filters:
        query += " WHERE " + " AND ".join(filters)
        query += " AND is_active = 1"
    else:
        query += " WHERE is_active = 1"
        
    query += " ORDER BY name"
    
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows

def get_all_categories():
    """Obtiene todas las categorías únicas de los productos."""
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND category != '' ORDER BY category")
    rows = cur.fetchall()
    conn.close()
    return [row[0] for row in rows]

def update_product(product_id, name, price, stock, code, unit_of_measure, operation_type, issuer_name=None, issuer_address=None, category="General", image=None):
    conn = create_connection()
    # Update image only if provided? No, update_product usually replaces all.
    # The caller must provide existing image if no change. 
    # BUT to be safe/lazy: if image is None, we could NOT update it.
    # However user might want to remove image.
    # To support removing image, we would pass empty bytes or special flag.
    # If image is None (default), we assume NO CHANGE to image field.
    # If image IS provided (bytes), we update it.
    
    if image is not None:
        sql = 'UPDATE products SET name = ?, price = ?, stock = ?, code = ?, unit_of_measure = ?, operation_type = ?, issuer_name = ?, issuer_address = ?, category = ?, image = ? WHERE id = ?'
        params = (name, price, stock, code, unit_of_measure, operation_type, issuer_name, issuer_address, category, image, product_id)
    else:
        sql = 'UPDATE products SET name = ?, price = ?, stock = ?, code = ?, unit_of_measure = ?, operation_type = ?, issuer_name = ?, issuer_address = ?, category = ? WHERE id = ?'
        params = (name, price, stock, code, unit_of_measure, operation_type, issuer_name, issuer_address, category, product_id)
        
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    conn.close()

def delete_product(product_id):
    conn = create_connection()
    # Soft delete: mark as inactive instead of deleting
    sql = 'UPDATE products SET is_active = 0 WHERE id=?'
    cur = conn.cursor()
    cur.execute(sql, (product_id,))
    compiles = cur.rowcount > 0
    conn.commit()
    conn.close()
    return compiles

def decrease_product_stock(product_id, quantity):
    conn = create_connection()
    sql = 'UPDATE products SET stock = stock - ? WHERE id = ?'
    cur = conn.cursor()
    cur.execute(sql, (quantity, product_id))
    conn.commit()
    conn.close()

def user_has_password(user_id):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE id = ?", (user_id,))
    res = cur.fetchone()
    conn.close()
    if res:
        # Check if password is NOT the hash of empty string
        import hashlib
        empty_hash = hashlib.sha256(b"").hexdigest()
        return res[0] != empty_hash
    return False

def check_user_password(user_id, password_input):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE id = ?", (user_id,))
    res = cur.fetchone()
    conn.close()
    if res:
        import hashlib
        input_hash = hashlib.sha256(password_input.encode()).hexdigest()
        return res[0] == input_hash
    return False

def get_product_stock(product_id):
    """Obtiene el stock actual de un producto."""
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT stock FROM products WHERE id = ?", (product_id,))
    result = cur.fetchone()
    conn.close()
    if result:
        return result[0]
    return 0.0
def record_sale(issuer_id, customer_id, total_amount, cart_items, sale_date_str, observations, doc_type, document_number, payment_method, amount_paid, payment_method2, amount_paid2, payment_destination, customer_address):
    conn = create_connection()
    try:
        cur = conn.cursor()
        sql_sale = '''INSERT INTO sales (issuer_id, customer_id, total_amount, sale_date, observations, document_type, document_number, payment_method, amount_paid, payment_method2, amount_paid2, payment_destination, customer_address) 
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
        cur.execute(sql_sale, (issuer_id, customer_id, total_amount, sale_date_str, observations, doc_type, document_number, payment_method, amount_paid, payment_method2, amount_paid2, payment_destination, customer_address))
        sale_id = cur.lastrowid
        
        # Insertar detalles de la venta
        for item in cart_items:
            # item: {id, name, quantity, price, subtotal, unit_of_measure, original_price}
            original_price = item.get('original_price', item['price']) # Fallback to selling price if not set
            cur.execute("INSERT INTO sale_details (sale_id, product_id, quantity_sold, price_per_unit, subtotal, original_price) VALUES (?, ?, ?, ?, ?, ?)",
                        (sale_id, item['id'], item['quantity'], item['price'], item['subtotal'], original_price))

        conn.commit()
    except Error as e:
        conn.rollback()
        print(f"Error al registrar la venta: {e}")
        raise e
    finally:
        if conn:
            conn.close()

def add_issuer(name, ruc, address, commercial_name, logo, bank_accounts, initial_greeting, final_greeting, district, province, department, ubigeo, sol_user, sol_pass, certificate, fe_url, re_url, guia_url_envio, guia_url_consultar, client_id, client_secret, validez_user, validez_pass, email, phone, default_operation_type, establishment_code, cert_password, cpe_alert_receivers):
    """Añade un nuevo emisor a la base de datos."""
    conn = create_connection()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO issuers (name, ruc, address, commercial_name, logo, bank_accounts, initial_greeting, final_greeting, district, province, department, ubigeo, sol_user, sol_pass, certificate, fe_url, re_url, guia_url_envio, guia_url_consultar, client_id, client_secret, validez_user, validez_pass, email, phone, default_operation_type, establishment_code, cert_password, cpe_alert_receivers) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (name, ruc, address, commercial_name, logo, bank_accounts, initial_greeting, final_greeting, district, province, department, ubigeo, sol_user, sol_pass, certificate, fe_url, re_url, guia_url_envio, guia_url_consultar, client_id, client_secret, validez_user, validez_pass, email, phone, default_operation_type, establishment_code, cert_password, cpe_alert_receivers))
        conn.commit()
        return cur.lastrowid
    except Error as e:
        print(e)
    finally:
        if conn:
            conn.close()
    return None

def get_daily_sales_total(payment_method='EFECTIVO'):
    """Obtiene el total de ventas del día actual para un método de pago específico."""
    conn = create_connection()
    total = 0.0
    try:
        cur = conn.cursor()
        # Asumiendo formato de fecha YYYY-MM-DD HH:MM:SS
        today = datetime.now().strftime('%Y-%m-%d')
        # SQLite date function extracts YYYY-MM-DD from the datetime string
        sql = "SELECT SUM(total_amount) FROM sales WHERE payment_method = ? AND date(sale_date) = ?"
        cur.execute(sql, (payment_method, today))
        result = cur.fetchone()
        if result and result[0]:
            total = result[0]
            
        # Also check payment_method2
        sql2 = "SELECT SUM(amount_paid2) FROM sales WHERE payment_method2 = ? AND date(sale_date) = ?"
        cur.execute(sql2, (payment_method, today))
        result2 = cur.fetchone()
        if result2 and result2[0]:
            total += result2[0]
            
    except Error as e:
        print(f"Error al obtener total de ventas diarias: {e}")
    finally:
        if conn:
            conn.close()
    return total

    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, ruc, address, commercial_name, logo, bank_accounts, initial_greeting, final_greeting, district, province, department, ubigeo, sol_user, sol_pass, certificate, fe_url, re_url, guia_url_envio, guia_url_consultar, client_id, client_secret, validez_user, validez_pass, email, phone, default_operation_type, establishment_code, cert_password, cpe_alert_receivers FROM issuers WHERE id = ?", (issuer_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        # Convert to dict for easier usage
        columns = [column[0] for column in cur.description]
        return dict(zip(columns, row))
    return None

def get_all_issuers():
    """Obtiene todos los emisores."""
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, ruc, address, commercial_name, logo, bank_accounts, initial_greeting, final_greeting, district, province, department, ubigeo, sol_user, sol_pass, certificate, fe_url, re_url, guia_url_envio, guia_url_consultar, client_id, client_secret, validez_user, validez_pass, email, phone, default_operation_type, establishment_code, cert_password, cpe_alert_receivers FROM issuers ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows

def update_issuer(issuer_id, name, ruc, address, commercial_name, logo, bank_accounts, initial_greeting, final_greeting, district, province, department, ubigeo, sol_user, sol_pass, certificate, fe_url, re_url, guia_url_envio, guia_url_consultar, client_id, client_secret, validez_user, validez_pass, email, phone, default_operation_type, establishment_code, cert_password, cpe_alert_receivers):
    """Actualiza los datos de un emisor existente."""
    conn = create_connection()
    sql = ''' UPDATE issuers
              SET name = ?,
                  ruc = ?,
                  address = ?,
                  commercial_name = ?,
                  logo = ?,
                  bank_accounts = ?,
                  initial_greeting = ?,
                  final_greeting = ?,
                  district = ?,
                  province = ?,
                  department = ?,
                  ubigeo = ?,
                  sol_user = ?,
                  sol_pass = ?,
                  certificate = ?,
                  fe_url = ?,
                  re_url = ?,
                  guia_url_envio = ?,
                  guia_url_consultar = ?,
                  client_id = ?,
                  client_secret = ?,
                  validez_user = ?,
                  validez_pass = ?,
                  email = ?,
                  phone = ?,
                  default_operation_type = ?,
                  establishment_code = ?,
                  cert_password = ?,
                  cpe_alert_receivers = ?
              WHERE id = ?'''
    cur = conn.cursor()
    cur.execute(sql, (name, ruc, address, commercial_name, logo, bank_accounts, initial_greeting, final_greeting, district, province, department, ubigeo, sol_user, sol_pass, certificate, fe_url, re_url, guia_url_envio, guia_url_consultar, client_id, client_secret, validez_user, validez_pass, email, phone, default_operation_type, establishment_code, cert_password, cpe_alert_receivers, issuer_id))
    conn.commit()
    conn.close()

def delete_issuer(issuer_id):
    """Elimina un emisor de la base de datos."""
    conn = create_connection()
    sql = 'DELETE FROM issuers WHERE id=?'
    cur = conn.cursor()
    cur.execute(sql, (issuer_id,))
    conn.commit()
    conn.close()

def add_party(doc_number, name, phone, address, party_type, alias=""):
    conn = create_connection()
    sql = 'INSERT INTO customers (doc_number, name, phone, address, type, alias) VALUES (?,?,?,?,?,?)'
    cur = conn.cursor()
    cur.execute(sql, (doc_number, name, phone, address, party_type, alias))
    conn.commit()
    return cur.lastrowid

def get_all_parties(party_type=None):
    conn = create_connection()
    cur = conn.cursor()
    if party_type:
        cur.execute("SELECT id, type, doc_number, name, phone, address, alias FROM customers WHERE type = ? ORDER BY name", (party_type,))
    else:
        cur.execute("SELECT id, type, doc_number, name, phone, address, alias FROM customers ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows

def update_party(party_id, doc_number, name, phone, address, party_type, alias=""):
    conn = create_connection()
    sql = 'UPDATE customers SET doc_number = ?, name = ?, phone = ?, address = ?, type = ?, alias = ? WHERE id = ?'
    cur = conn.cursor()
    cur.execute(sql, (doc_number, name, phone, address, party_type, alias, party_id))
    conn.commit()

def delete_party(party_id):
    conn = create_connection()
    sql = 'DELETE FROM customers WHERE id=?'
    cur = conn.cursor()
    cur.execute(sql, (party_id,))
    conn.commit()

def get_or_create_customer(doc_number, name, phone, address):
    if not doc_number and not name:
        return None
    conn = create_connection()
    cur = conn.cursor()
    if doc_number:
        cur.execute("SELECT id, address FROM customers WHERE doc_number = ? AND type = 'Cliente'", (doc_number,))
    else:
        cur.execute("SELECT id, address FROM customers WHERE name = ? AND (doc_number IS NULL OR doc_number = '') AND type = 'Cliente'", (name,))
    data = cur.fetchone()
    if data:
        customer_id, db_address = data
        if not db_address and address:
            update_party(customer_id, doc_number, name, phone, address, "Cliente")
        return customer_id
    else:
        return add_party(doc_number, name, phone, address, "Cliente", "")

def get_all_sales():
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, strftime('%Y-%m-%d %H:%M:%S', sale_date), total_amount FROM sales ORDER BY sale_date DESC")
    return cur.fetchall()

def get_all_sales_with_customer_name(issuer_name=None, address=None, start_date=None, end_date=None):
    """Obtiene todas las ventas con el nombre del cliente, tipo y número de documento."""
    conn = create_connection()
    cur = conn.cursor()
    query = """
        SELECT
            s.id,
            s.document_type,
            s.document_number,
            strftime('%Y-%m-%d %H:%M:%S', s.sale_date),
            COALESCE(c.name, 'Cliente Varios'),
            s.total_amount,
            (SELECT SUM((sd.price_per_unit - COALESCE(sd.original_price, sd.price_per_unit)) * sd.quantity_sold) FROM sale_details sd WHERE sd.sale_id = s.id) as diff_amount,
            i.name as issuer_name,
            i.address as issuer_address,
            s.sunat_status,
            s.sunat_note
        FROM sales s
        LEFT JOIN customers c ON s.customer_id = c.id
        LEFT JOIN issuers i ON s.issuer_id = i.id
    """
    filters = []
    params = []
    if issuer_name:
        filters.append("i.name = ?")
        params.append(issuer_name)
    if address:
        filters.append("i.address = ?")
        params.append(address)
    
    if start_date:
        filters.append("date(s.sale_date) >= ?")
        params.append(start_date)
    if end_date:
        filters.append("date(s.sale_date) <= ?")
        params.append(end_date)
    
    if filters:
        query += " WHERE " + " AND ".join(filters)
        
    query += " ORDER BY s.sale_date DESC"
    
    cur.execute(query, params)
    return cur.fetchall()

def get_full_sale_data(sale_id):
    """Obtiene todos los datos de una venta para la vista previa del ticket."""
    conn = create_connection()
    cur = conn.cursor()
    
    # Datos de la venta, cliente y emisor
    cur.execute("""
        SELECT 
            s.sale_date, s.total_amount, s.observations, s.document_type, s.document_number,
            c.name as customer_name, c.doc_number as customer_doc,
            i.name as issuer_name, i.ruc as issuer_ruc, i.address as issuer_address,
            i.district, i.province, i.department,
            i.commercial_name, i.bank_accounts, i.initial_greeting, i.final_greeting, i.logo, i.email, i.phone,
            s.payment_method as payment_method1, s.amount_paid as amount_paid1, s.payment_method2, s.amount_paid2
        FROM sales s
        LEFT JOIN customers c ON s.customer_id = c.id
        LEFT JOIN issuers i ON s.issuer_id = i.id
        WHERE s.id = ?
    """, (sale_id,))
    sale_data = cur.fetchone()
    if not sale_data:
        return None

    # Detalles de la venta (productos)
    cur.execute("""
        SELECT p.name, sd.quantity_sold, sd.price_per_unit, sd.subtotal, p.unit_of_measure, p.operation_type, sd.original_price
        FROM sale_details sd
        JOIN products p ON sd.product_id = p.id
        WHERE sd.sale_id = ?
    """, (sale_id,))
    details = cur.fetchall()
    
    conn.close()
    
    return {"sale": sale_data, "details": details}


def get_sale_details_by_sale_id(sale_id):
    conn = create_connection()
    cur = conn.cursor()
    sql = "SELECT p.name, sd.quantity_sold, sd.price_per_unit, sd.subtotal, p.unit_of_measure, p.operation_type FROM sale_details sd JOIN products p ON sd.product_id = p.id WHERE sd.sale_id = ?"
    cur.execute(sql, (sale_id,))
    return cur.fetchall()

def get_correlative(issuer_id, doc_type):
    """Obtiene la serie y el número actual para un emisor y tipo de documento."""
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT series, current_number FROM correlatives WHERE issuer_id = ? AND doc_type = ?", (issuer_id, doc_type))
    row = cur.fetchone()
    conn.close()
    return row if row else (None, 0)

def set_correlative(issuer_id, doc_type, series, number):
    """Establece o actualiza el correlativo para un emisor y tipo de documento."""
    conn = create_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO correlatives (issuer_id, doc_type, series, current_number)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(issuer_id, doc_type) DO UPDATE SET
            series = excluded.series,
            current_number = excluded.current_number
        """, (issuer_id, doc_type, series, number))
        conn.commit()
    except Error as e:
        print(f"Error al establecer el correlativo: {e}")
    finally:
        conn.close()

def get_next_correlative(issuer_id, doc_type):
    """
    Obtiene el siguiente número de correlativo para un tipo de documento y emisor,
    y lo incrementa en la base de datos de forma atómica.
    """
    conn = create_connection()
    cur = conn.cursor()
    next_number = -1
    series = ""
    try:
        conn.isolation_level = 'EXCLUSIVE'
        conn.execute('BEGIN EXCLUSIVE')

        cur.execute("SELECT series, current_number FROM correlatives WHERE issuer_id = ? AND doc_type = ?", (issuer_id, doc_type))
        row = cur.fetchone()

        if row:
            series, current_number = row
            next_number = current_number + 1
            cur.execute("UPDATE correlatives SET current_number = ? WHERE issuer_id = ? AND doc_type = ?", (next_number, issuer_id, doc_type))
            conn.commit()
            with open("debug_log.txt", "a") as f: f.write(f"DB NEXT: Updated {doc_type} to {next_number} (Series {series})\n")
        else:
            conn.rollback()
            return None, -1
            
    except Error as e:
        print(f"Error al obtener el siguiente correlativo: {e}")
        if conn:
            conn.rollback()
        return None, -1
    finally:
        if conn:
            conn.close()
            
    return series, next_number

def get_last_issued_correlative(issuer_id, doc_type):
    """Obtiene el último número de documento emitido para un emisor y tipo de documento."""
    return 0 

def get_correlative(issuer_id, doc_type):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT series, current_number FROM correlatives WHERE issuer_id = ? AND doc_type = ?", (issuer_id, doc_type))
    row = cur.fetchone()
    conn.close()
    if row:
        with open("debug_log.txt", "a") as f: f.write(f"DB READ: {doc_type} -> {row[1]} (Series {row[0]})\n")
        return row[0], row[1]
    return None, -1
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT MAX(CAST(SUBSTR(document_number, INSTR(document_number, '-') + 1) AS INTEGER))
        FROM sales
        WHERE issuer_id = ? AND document_type = ?
    """, (issuer_id, doc_type))
    row = cur.fetchone()
    conn.close()
    return row[0] if row and row[0] is not None else 0

def is_code_unique(code, issuer_name=None, issuer_address=None):
    """Verifica si un código de producto es único dentro de la misma empresa/dirección."""
    conn = create_connection()
    cur = conn.cursor()
    # Check uniqueness only within the same issuer_name AND issuer_address
    cur.execute(
        "SELECT id FROM products WHERE code = ? AND issuer_name = ? AND issuer_address = ? AND is_active = 1",
        (code, issuer_name, issuer_address)
    )
    row = cur.fetchone()
    conn.close()
    return row is None

def get_customer_by_alias(alias):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE alias LIKE ?", ('%' + alias + '%',))
    return cur.fetchall()

def search_customers_general(query):
    conn = create_connection()
    cur = conn.cursor()
    search_term = f"%{query}%"
    cur.execute("""
        SELECT * FROM customers 
        WHERE name LIKE ? OR alias LIKE ? OR doc_number LIKE ?
        ORDER BY name
        LIMIT 20
    """, (search_term, search_term, search_term))
    return cur.fetchall()

if __name__ == '__main__':
    setup_database()
def get_next_movement_number(movement_type):
    """Obtiene el siguiente número correlativo para un tipo de movimiento (INGRESO/SALIDA)."""
    conn = create_connection()
    cur = conn.cursor()
    
    prefix = "IN" if movement_type == "INGRESO" else ("AN" if movement_type == "ANULADO" else "SA")
    
    # Buscar el último número usado para este tipo
    cur.execute("SELECT movement_number FROM inventory_movements WHERE movement_type = ? ORDER BY id DESC LIMIT 1", (movement_type,))
    last_row = cur.fetchone()
    
    if last_row:
        last_number_str = last_row[0] # Ej: "IN-5"
        try:
            last_seq = int(last_number_str.split('-')[1])
            next_seq = last_seq + 1
        except (IndexError, ValueError):
            next_seq = 1
    else:
        next_seq = 1
        
    return f"{prefix}-{next_seq}"

def record_movement(movement_type, reason, issuer_id, issuer_address, items, total_amount, date_time):
    """Registra un movimiento de inventario y actualiza el stock."""
    conn = create_connection()
    try:
        cur = conn.cursor()
        
        # 1. Obtener número correlativo
        movement_number = get_next_movement_number(movement_type) # Note: This is slightly risky for concurrency but acceptable for single-user
        
        # 2. Insertar movimiento cabecera
        sql_movement = ''' INSERT INTO inventory_movements(movement_type, movement_number, date_time, reason, issuer_id, issuer_address, total_amount)
                           VALUES(?,?,?,?,?,?,?) '''
        cur.execute(sql_movement, (movement_type, movement_number, date_time, reason, issuer_id, issuer_address, total_amount))
        movement_id = cur.lastrowid
        
        # 3. Insertar items y actualizar stock
        sql_item = ''' INSERT INTO inventory_movement_items(movement_id, product_id, quantity, unit_of_measure, price, subtotal)
                       VALUES(?,?,?,?,?,?) '''
                       
        for item in items:
            # item: {id, quantity, price, subtotal, unit_of_measure}
            cur.execute(sql_item, (movement_id, item['id'], item['quantity'], item['unit_of_measure'], item['price'], item['subtotal']))
            
            # Actualizar Stock
            if movement_type == "INGRESO":
                sql_update_stock = "UPDATE products SET stock = stock + ? WHERE id = ?"
            elif movement_type in ["SALIDA", "ANULADO"]: # Both subtract stock?
                # User scenario: "Anulado" in Sales usually means Sale Voided (Stock Returns).
                # But here in "Movements" context (Ingresos/Salidas), "Anulado" is often used as "Baja/Merma".
                # If the user selects "ANULADO" via the button "Anulado" in Sales View...
                # Wait. The "Anulado" button in Sales View is for "Registrar Anulado" (voiding a current attempt? or recording a past void?).
                # If I am in Sales View, I haven't sold it yet (it's in cart).
                # If I click "Anulado", I am opening a dialog to register a movement.
                # If I register products there, what does it mean?
                # Usually "Anulado" means "Item Damaged/Voided". So Stock goes DOWN.
                # If I wanted to return stock, I would do "Ingreso".
                # So "ANULADO" behaving like "SALIDA" (Decreasing Stock) is safer default for "Merma".
                sql_update_stock = "UPDATE products SET stock = stock - ? WHERE id = ?"
            else:
                 sql_update_stock = "UPDATE products SET stock = stock - ? WHERE id = ?" # Default to substract
                
            cur.execute(sql_update_stock, (item['quantity'], item['id']))
            
        conn.commit()
        return movement_number
    except Error as e:
        conn.rollback()
        print(f"Error recording movement: {e}")
        raise
    finally:
        conn.close()

def get_movements(filter_type="TODOS", start_date=None, end_date=None, issuer_id=None, address=None):
    """Obtiene el historial de movimientos."""
    conn = create_connection()
    cur = conn.cursor()
    
    sql = "SELECT id, movement_type, movement_number, date_time, reason, total_amount, issuer_id, issuer_address FROM inventory_movements"
    conditions = []
    params = []
    
    if filter_type != "TODOS":
        conditions.append("movement_type = ?")
        params.append(filter_type)
        
    if start_date and end_date:
        # Asumiendo que date_time es 'YYYY-MM-DD HH:MM:SS'
        conditions.append("date(date_time) BETWEEN ? AND ?")
        params.append(start_date)
        params.append(end_date)

    if issuer_id is not None:
        conditions.append("issuer_id = ?")
        params.append(issuer_id)
        
    if address and address != "TODOS":
        conditions.append("issuer_address = ?")
        params.append(address)
        
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
        
    sql += " ORDER BY id DESC"
    
    cur.execute(sql, params)
    return cur.fetchall()

def get_movement_items(movement_id):
    """Obtiene los detalles de un movimiento."""
    conn = create_connection()
    cur = conn.cursor()
    
    sql = """
        SELECT p.name, i.quantity, i.unit_of_measure, i.price, i.subtotal
        FROM inventory_movement_items i
        JOIN products p ON i.product_id = p.id
        WHERE i.movement_id = ?
    """
    cur.execute(sql, (movement_id,))
    return cur.fetchall()

def get_movement_full_data(movement_id):
    """Obtiene todos los datos de un movimiento para la vista previa del ticket."""
    conn = create_connection()
    cur = conn.cursor()
    
    # Datos del movimiento y emisor
    cur.execute("""
        SELECT 
            m.id, m.movement_type, m.movement_number, m.date_time, m.reason, m.total_amount,
            i.name as issuer_name, i.ruc as issuer_ruc, i.address as issuer_address,
            i.district, i.province, i.department,
            i.commercial_name, i.bank_accounts, i.initial_greeting, i.final_greeting, i.logo, i.email, i.phone
        FROM inventory_movements m
        LEFT JOIN issuers i ON m.issuer_id = i.id
        WHERE m.id = ?
    """, (movement_id,))
    movement_data = cur.fetchone()
    
    if not movement_data:
        conn.close()
        return None

    # Detalles del movimiento (productos)
    cur.execute("""
        SELECT p.name, i.quantity, i.unit_of_measure, i.price, i.subtotal
        FROM inventory_movement_items i
        JOIN products p ON i.product_id = p.id
        WHERE i.movement_id = ?
    """, (movement_id,))
    details = cur.fetchall()
    
    conn.close()
    
    return {"movement": movement_data, "details": details}

def get_daily_sales_total(payment_method='EFECTIVO'):
    """Calcula el total de ventas del día actual para un método de pago específico."""
    conn = create_connection()
    cur = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    sql = """
        SELECT SUM(total_amount) 
        FROM sales 
        WHERE date(sale_date) = ? AND payment_method = ?
    """
    
    cur.execute(sql, (today, payment_method))
    result = cur.fetchone()[0]
    conn.close()
    
    return result if result else 0.0

# --- Arqueo de Caja Functions ---

def create_cash_counts_table(conn):
    """Crea la tabla de arqueos de caja."""
    create_table(conn, """ CREATE TABLE IF NOT EXISTS cash_counts (
                                        id integer PRIMARY KEY,
                                        caja_id text NOT NULL,
                                        start_time text,
                                        end_time text,
                                        user_id text,
                                        system_cash real,
                                        counted_cash real,
                                        difference real,
                                        correlative text,
                                        initial_balance real DEFAULT 0.0,
                                        system_cards real DEFAULT 0.0,
                                        expenses real DEFAULT 0.0,
                                        counted_cards real DEFAULT 0.0,
                                        change_next_day real DEFAULT 0.0,
                                        collected_total real DEFAULT 0.0,
                                        details_json text
                                    ); """)

def get_last_closure(caja_id):
    """Obtiene el último cierre de caja para una caja específica."""
    conn = create_connection()
    cur = conn.cursor()
    
    sql = "SELECT * FROM cash_counts WHERE caja_id = ? ORDER BY id DESC LIMIT 1"
    cur.execute(sql, (caja_id,))
    row = cur.fetchone()
    conn.close()
    return row

def save_cash_count(data):
    """Guarda un nuevo arqueo de caja."""
    conn = create_connection()
    try:
        cur = conn.cursor()
        sql = """ INSERT INTO cash_counts(caja_id, start_time, end_time, user_id, system_cash, counted_cash, difference, correlative,
                                          initial_balance, system_cards, expenses, counted_cards, change_next_day, collected_total, details_json,
                                          opening_time, accumulated_cash, stock_value, sales_cash, income_additional, purchases, anulados, returns, withdrawal)
                  VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) """
        cur.execute(sql, (data['caja_id'], data['start_time'], data['end_time'], data['user_id'], 
                          data['system_cash'], data['counted_cash'], data['difference'], data['correlative'],
                          data.get('initial_balance', 0.0), data.get('system_cards', 0.0), data.get('expenses', 0.0),
                          data.get('counted_cards', 0.0), data.get('change_next_day', 0.0), data.get('collected_total', 0.0),
                          data.get('details_json', '{}'),
                          data.get('opening_time', ''),
                          data.get('accumulated_cash', 0.0),
                          data.get('stock_value', 0.0),
                          data.get('sales_cash', 0.0),
                          data.get('income_additional', 0.0),
                          data.get('purchases', 0.0),
                          data.get('anulados', 0.0),
                          data.get('returns', 0.0),
                          data.get('withdrawal', 0.0)))
        conn.commit()
        
        # Transfer temp expenses to history
        if cur.lastrowid:
            transfer_temp_to_history(data['caja_id'], cur.lastrowid)
            
        return cur.lastrowid
    except Error as e:
        print(e)
        return None
    finally:
        conn.close()

def get_cash_counts_history(caja_id):
    """Obtiene el historial de arqueos para una caja."""
    conn = create_connection()
    cur = conn.cursor()
    
    sql = "SELECT id, end_time, user_id, correlative, difference FROM cash_counts WHERE caja_id = ? ORDER BY id DESC"
    cur.execute(sql, (caja_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_cash_count_by_id(record_id):
    conn = create_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    sql = "SELECT * FROM cash_counts WHERE id = ?"
    cur.execute(sql, (record_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_sales_total_in_range(start_time, end_time, caja_id, payment_method='EFECTIVO'):
    """Calcula el total de ventas en un rango de fechas."""
    conn = create_connection()
    cur = conn.cursor()
    
    # Note: We might want to filter by caja_id if sales are per-caja, but currently sales table doesn't seem to have caja_id?
    # Checking sales table schema... It has user_id but maybe not caja_id?
    # Assuming for now we count ALL sales or we need to add caja_id to sales?
    # The user requirement implies "ventas de esos rangos".
    # If sales don't have caja_id, we count global sales.
    
    sql = """
        SELECT SUM(total_amount) 
        FROM sales 
        WHERE sale_date > ? AND sale_date <= ? AND payment_method = ?
    """
    
    cur.execute(sql, (start_time, end_time, payment_method))
    result = cur.fetchone()[0]
    conn.close()
    
    return result if result else 0.0

def create_temp_expenses_table(conn):
    create_table(conn, """ CREATE TABLE IF NOT EXISTS temp_expenses (
                                        id integer PRIMARY KEY,
                                        caja_id integer NOT NULL,
                                        expense_date text,
                                        detail text,
                                        detail_2 text,
                                        amount real
                                    ); """)

def add_temp_expense(caja_id, expense_date, detail, amount, detail_2=""):
    conn = create_connection()
    # Check if detail_2 column exists (handled by migration, but query needs to match schema)
    # We assume migration runs first.
    sql = 'INSERT INTO temp_expenses(caja_id, expense_date, detail, amount, detail_2) VALUES(?,?,?,?,?)'
    cur = conn.cursor()
    cur.execute(sql, (caja_id, expense_date, detail, amount, detail_2))
    conn.commit()
    conn.close()

def get_temp_expenses(caja_id):
    conn = create_connection()
    cur = conn.cursor()
    # Check if detail_2 exists to avoid error if migration failed? 
    # Optimistic: assume it exists.
    try:
        cur.execute("SELECT id, expense_date, detail, amount, detail_2 FROM temp_expenses WHERE caja_id = ? ORDER BY id", (caja_id,))
    except:
        # Fallback for old schema if something weird happens (shouldn't if setup runs)
        cur.execute("SELECT id, expense_date, detail, amount FROM temp_expenses WHERE caja_id = ? ORDER BY id", (caja_id,))
        # Pad results
        rows = cur.fetchall()
        # Adapt rows to include empty detail_2
        return [(r[0], r[1], r[2], r[3], "") for r in rows]

    return cur.fetchall()

def delete_temp_expense(expense_id):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM temp_expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()

def clear_temp_expenses(caja_id):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM temp_expenses WHERE caja_id = ?", (caja_id,))
    conn.commit()
    conn.close()

# --- Expenses History ---

def create_expenses_history_table(conn):
    create_table(conn, """ CREATE TABLE IF NOT EXISTS expenses_history (
                                        id integer PRIMARY KEY,
                                        caja_id text NOT NULL,
                                        cash_count_id integer,
                                        expense_date text,
                                        detail text,
                                        detail_2 text,
                                        amount real,
                                        FOREIGN KEY (cash_count_id) REFERENCES cash_counts (id)
                                    ); """)

def transfer_temp_to_history(caja_id, cash_count_id):
    """Mueve los gastos temporales al histórico al cerrar caja."""
    conn = create_connection()
    cur = conn.cursor()
    
    # Get temps
    temps = get_temp_expenses(caja_id)
    
    # Insert into history
    sql = "INSERT INTO expenses_history(caja_id, cash_count_id, expense_date, detail, detail_2, amount) VALUES (?, ?, ?, ?, ?, ?)"
    for t in temps:
        # t: id, date, detail, amount, detail_2 
        # Note: get_temp_expenses returns specific columns.
        # If it returns 5 cols: id(0), date(1), detail(2), amount(3), detail_2(4)
        detail_2 = t[4] if len(t) > 4 else ""
        cur.execute(sql, (caja_id, cash_count_id, t[1], t[2], detail_2, t[3]))
        
    conn.commit()
    conn.close()

def get_expenses_history(filter_text=None):
    """Obtiene el historial de gastos con filtro opcional."""
    conn = create_connection()
    cur = conn.cursor()
    
    sql = "SELECT expense_date, detail, detail_2, amount FROM expenses_history"
    
    # Order by date desc
    
    if filter_text and filter_text.strip():
        term = f"%{filter_text.strip()}%"
        sql += " WHERE detail LIKE ? OR detail_2 LIKE ? OR amount LIKE ? OR expense_date LIKE ?"
        params = (term, term, term, term)
        sql += " ORDER BY id DESC" # Assuming ID correlates with time or add date sort
        cur.execute(sql, params)
    else:
        sql += " ORDER BY id DESC"
        cur.execute(sql)
        
    return cur.fetchall()

def get_unique_expense_details():
    """Obtiene una lista de detalles únicos (detalle 1) del histórico de gastos."""
    conn = create_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT DISTINCT detail FROM expenses_history ORDER BY detail")
        rows = cur.fetchall()
        return [row[0] for row in rows if row[0]]
    except Exception as e:
        print(f"Error fetching unique details: {e}")
        return []
    finally:
        conn.close()


def get_movement_totals_by_type_in_range(start_time, end_time):
    """Obtiene los totales por tipo de movimiento en un rango de fechas."""
    conn = create_connection()
    cur = conn.cursor()
    
    sql = """
        SELECT movement_type, SUM(total_amount)
        FROM inventory_movements
        WHERE date_time >= ? AND date_time <= ?
        GROUP BY movement_type
    """
    
    cur.execute(sql, (start_time, end_time))
    rows = cur.fetchall()
    conn.close()
    
    totals = {}
    for row in rows:
        # Standard types: INGRESO, SALIDA. "ANULADO" if exists.
        totals[row[0]] = row[1] if row[1] else 0.0
        
    return totals


def get_product_ranking_in_range(start_time, end_time):
    """Obtiene el ranking de productos más vendidos en un rango."""
    conn = create_connection()
    cur = conn.cursor()
    
    sql = """
        SELECT p.name, SUM(d.quantity_sold) as total_qty
        FROM sale_details d
        JOIN sales s ON d.sale_id = s.id
        JOIN products p ON d.product_id = p.id
        WHERE s.sale_date > ? AND s.sale_date <= ?
        GROUP BY p.name
        ORDER BY total_qty DESC
    """
    
    cur.execute(sql, (start_time, end_time))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_discount_details_in_range(start_time, end_time):
    """Obtiene detalles de productos con descuento (original_price > price_per_unit)."""
    conn = create_connection()
    cur = conn.cursor()
    
    # We want: Name, Discount Amount (Total or Unit?), Qty, Unit Price (Sold), Subtotal (Sold)
    # User asked cols: DESC., CANT., UNIT., SUBT.
    # DESC probably means Discount Amount?
    # Logic: Unit Discount = Original - Price. Total Desc = Unit Desc * Qty.
    
    sql = """
        SELECT p.name, (d.original_price - d.price_per_unit) as unit_discount, d.quantity_sold, d.price_per_unit, d.subtotal
        FROM sale_details d
        JOIN sales s ON d.sale_id = s.id
        JOIN products p ON d.product_id = p.id
        WHERE s.sale_date > ? AND s.sale_date <= ?
        AND d.original_price > d.price_per_unit
    """
    
    cur.execute(sql, (start_time, end_time))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_documents_summary_in_range(start_time, end_time):
    """Obtiene resumen de documentos emitidos."""
    conn = create_connection()
    cur = conn.cursor()
    
    sql = """
        SELECT document_type, COUNT(*), SUM(total_amount)
        FROM sales
        WHERE sale_date > ? AND sale_date <= ?
        GROUP BY document_type
    """
    
    cur.execute(sql, (start_time, end_time))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_pending_invoices_for_retry():
    """Obtiene facturas pendientes de validación con más de 2 días de antigüedad o error de conexión."""
    conn = create_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # Selección de facturas PENDIENTE con > 2 días o ERROR_CONEXION (cualquier fecha)
    # Nota: datetime('now', '-2 days') calcula la fecha límite
    query = """
        SELECT id, document_type, document_number, issuer_id, sunat_status 
        FROM sales 
        WHERE 
            (sunat_status = 'PENDIENTE' AND sale_date <= datetime('now', '-2 days'))
            OR 
            (sunat_status = 'ERROR_CONEXION')
    """
    cur.execute(query)
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_issuer_by_id(issuer_id):
    """Obtiene un emisor por su ID como diccionario."""
    conn = create_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM issuers WHERE id = ?", (issuer_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None
