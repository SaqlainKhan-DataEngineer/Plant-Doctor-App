import pyodbc
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
import bcrypt
import uuid
import os

app = FastAPI(title="Plant Doctor API - SQL Server")

# 🔥 SQL Server Connection - Windows Auth
SQL_SERVER_CONFIG = {
    "server": "DESKTOP-OO6VLOE\\SQLEXPRESS",
    "database": "PlantDoctor",
    "driver": "{ODBC Driver 17 for SQL Server}"
}

def get_db_connection():
    conn_str = (
        f"DRIVER={SQL_SERVER_CONFIG['driver']};"
        f"SERVER={SQL_SERVER_CONFIG['server']};"
        f"DATABASE={SQL_SERVER_CONFIG['database']};"
        f"Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)

# JWT Secret
SECRET_KEY = "your-secret-key-here"
security = HTTPBearer()

# Models
class UserRegister(BaseModel):
    full_name: str
    email: str
    password: str
    phone: str = None

class UserLogin(BaseModel):
    email: str
    password: str

# Helper: Hash password
def hash_password(password: str):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

# Helper: Verify token
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

# API 1: Register
@app.post("/api/auth/register")
def register(user: UserRegister):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE email = ?", user.email)
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email already exists")
    
    user_id = str(uuid.uuid4())
    password_hash = hash_password(user.password)
    
    cursor.execute("""
        INSERT INTO users (id, full_name, email, phone, password_hash, role)
        VALUES (?, ?, ?, ?, ?, ?)
    """, user_id, user.full_name, user.email, user.phone, password_hash, 'farmer')
    
    conn.commit()
    conn.close()
    return {"message": "User registered successfully"}

# API 2: Login
@app.post("/api/auth/login")
def login(user: UserLogin):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, password_hash, role FROM users WHERE email = ?
    """, user.email)
    
    db_user = cursor.fetchone()
    conn.close()
    
    if not db_user or not bcrypt.checkpw(user.password.encode(), db_user[1].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = jwt.encode({
        "user_id": str(db_user[0]),
        "role": db_user[2],
        "email": user.email
    }, SECRET_KEY, algorithm="HS256")
    
    return {"token": token, "role": db_user[2]}

# API 3: Save Scan
@app.post("/api/scans")
def save_scan(crop: str, disease: str, confidence: float, 
              image: UploadFile = File(...), user=Depends(verify_token)):
    
    os.makedirs(f"uploads/{user['user_id']}", exist_ok=True)
    image_path = f"uploads/{user['user_id']}/{image.filename}"
    with open(image_path, "wb") as f:
        f.write(image.file.read())
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    scan_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO scans (id, user_id, crop_type, image_url, predicted_disease, confidence)
        VALUES (?, ?, ?, ?, ?, ?)
    """, scan_id, user['user_id'], crop, image_path, disease, confidence)
    
    conn.commit()
    conn.close()
    
    return {"message": "Scan saved", "scan_id": scan_id}

# API 4: Get History
@app.get("/api/scans/history")
def get_history(user=Depends(verify_token)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, crop_type, image_url, predicted_disease, confidence, created_at 
        FROM scans WHERE user_id = ? ORDER BY created_at DESC
    """, user['user_id'])
    
    columns = [column[0] for column in cursor.description]
    scans = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    conn.close()
    return {"scans": scans}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 