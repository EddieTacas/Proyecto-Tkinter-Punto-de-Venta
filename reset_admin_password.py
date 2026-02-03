import sqlite3
import hashlib
import os

def reset_password():
    db_file = 'database.db'
    if not os.path.exists(db_file):
        print(f"Error: {db_file} not found.")
        return

    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    
    username = "admin"
    new_password = "admin"
    password_hash = hashlib.sha256(new_password.encode()).hexdigest()
    
    # Check if admin exists
    cur.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = cur.fetchone()
    
    if user:
        cur.execute("UPDATE users SET password = ? WHERE username = ?", (password_hash, username))
        print(f"Password for user '{username}' has been reset to '{new_password}'.")
    else:
        # Create admin if not exists
        print(f"User '{username}' not found. Creating new admin user.")
        cur.execute("INSERT INTO users (username, password, permissions) VALUES (?, ?, ?)", (username, password_hash, "admin"))
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    reset_password()
