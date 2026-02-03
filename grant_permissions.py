import sqlite3
import os

def grant_permissions():
    db_file = 'database.db'
    if not os.path.exists(db_file):
        print(f"Error: {db_file} not found.")
        return

    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    
    username = "admin"
    new_permissions = "admin"
    
    # Update permissions
    cur.execute("UPDATE users SET permissions = ? WHERE username = ?", (new_permissions, username))
    
    if cur.rowcount > 0:
        print(f"Permissions for user '{username}' have been set to '{new_permissions}'.")
    else:
        print(f"User '{username}' not found.")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    grant_permissions()
