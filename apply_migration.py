import database

if __name__ == "__main__":
    print("Applying database migration...")
    database.setup_database()
    print("Migration applied.")
