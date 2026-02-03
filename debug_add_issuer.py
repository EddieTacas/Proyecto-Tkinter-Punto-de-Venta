import database
import traceback

def debug_add():
    print("Debugging add_issuer...")
    try:
        # Dummy data matching the expected arguments
        # name, ruc, address, commercial_name, logo, bank_accounts, initial_greeting, final_greeting, district, province, department, ubigeo, sol_user, sol_pass, certificate, fe_url, re_url, guia_url_envio, guia_url_consultar, client_id, client_secret, validez_user, validez_pass, email, phone, default_operation_type
        
        args = [
            "DEBUG EMPRESA", "10101010101", "DEBUG ADDRESS", "DEBUG COMERCIAL", b"", 
            "CUENTAS", "HOLA", "CHAU", "LIMA", "LIMA", "LIMA", "150101",
            "SOLUSER", "SOLPASS", b"", "URL1", "URL2", "URL3", "URL4",
            "ID", "SECRET", "VALUSER", "VALPASS", "email@test.com", "999999999", "Gravada"
        ]
        
        print(f"Calling add_issuer with {len(args)} args")
        rowid = database.add_issuer(*args)
        print(f"Success! Row ID: {rowid}")
        
        # Clean up
        import sqlite3
        conn = sqlite3.connect('c:/Users/USUARIO/Mi unidad (eddiejhersson1@gmail.com)/Proyecto tkinter/database.db')
        conn.execute("DELETE FROM issuers WHERE ruc = '10101010101'")
        conn.commit()
        conn.close()
        
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    debug_add()
