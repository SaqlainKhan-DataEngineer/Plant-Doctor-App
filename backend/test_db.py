import pyodbc

# Try Windows Auth first
try:
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=DESKTOP-OO6VLOE\\SQLEXPRESS;"
        "DATABASE=PlantDoctor;"
        "Trusted_Connection=yes;"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT @@VERSION")
    row = cursor.fetchone()
    print("✅ WINDOWS AUTH SUCCESS!")
    print(f"SQL Server Version: {row[0]}")
    conn.close()
except Exception as e:
    print(f"❌ Windows Auth Failed: {e}") 