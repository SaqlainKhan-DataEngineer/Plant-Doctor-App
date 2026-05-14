try:
    import pyodbc
except ImportError:
    pyodbc = None

from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
from contextlib import contextmanager
import jwt
import bcrypt
import uuid
import os
import datetime

# ==============================================================================
# APP SETUP
# ==============================================================================
app = FastAPI(
    title="Plant Doctor API",
    description="Pakistani Kisanon Ka AI Doctor — Backend API",
    version="2.0.0"
)

# CORS — Streamlit aur kisi bhi frontend se requests allow
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
import urllib.parse

# ==============================================================================
# DATABASE CONFIG — Supports Local SQL Server & Cloud MySQL
# ==============================================================================
DATABASE_URL = os.getenv("MYSQL_URL") or os.getenv("DATABASE_URL")

SQL_SERVER_CONFIG = {
    "server": "DESKTOP-OO6VLOE\\SQLEXPRESS",
    "database": "PlantDoctor",
    "driver": "{ODBC Driver 17 for SQL Server}"
}

SECRET_KEY = "plantdoctor-secret-key-2026-startup"
security = HTTPBearer()

class MySQLCursorWrapper:
    """Wrapper to automatically convert ? to %s for MySQL queries"""
    def __init__(self, cursor):
        self.cursor = cursor
    
    def execute(self, query, *args):
        # Convert ? to %s for PyMySQL
        mysql_query = query.replace("?", "%s")
        # In PyMySQL, execute expects args as a tuple
        return self.cursor.execute(mysql_query, args if args else None)
        
    def fetchone(self):
        return self.cursor.fetchone()
        
    def fetchall(self):
        return self.cursor.fetchall()
        
    def executemany(self, query, args):
        mysql_query = query.replace("?", "%s")
        return self.cursor.executemany(mysql_query, args)

# ==============================================================================
# DB CONNECTION — Context Manager (auto close, no leaks)
# ==============================================================================
@contextmanager
def get_db():
    """Database connection context manager — supports MySQL and SQL Server"""
    conn = None
    is_mysql = False
    try:
        if DATABASE_URL:
            # Connect to MySQL (Railway)
            import pymysql
            parsed = urllib.parse.urlparse(DATABASE_URL)
            conn = pymysql.connect(
                host=parsed.hostname,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path[1:], # remove leading slash
                port=parsed.port or 3306,
                autocommit=False
            )
            is_mysql = True
        else:
            # Connect to Local SQL Server
            conn_str = (
                f"DRIVER={SQL_SERVER_CONFIG['driver']};"
                f"SERVER={SQL_SERVER_CONFIG['server']};"
                f"DATABASE={SQL_SERVER_CONFIG['database']};"
                f"Trusted_Connection=yes;"
            )
            conn = pyodbc.connect(conn_str)
            
        # Yield connection with custom attribute or wrapper
        if is_mysql:
            class MySQLConnWrapper:
                def __init__(self, c):
                    self.conn = c
                    self._is_mysql = True
                def cursor(self):
                    return MySQLCursorWrapper(self.conn.cursor())
                def commit(self):
                    self.conn.commit()
                def close(self):
                    self.conn.close()
            yield MySQLConnWrapper(conn)
        else:
            conn._is_mysql = False
            yield conn
    finally:
        if conn:
            conn.close()

# ==============================================================================
# AUTO-CREATE TABLES ON STARTUP
# ==============================================================================
@app.on_event("startup")
def create_tables():
    """Server start hote hi tables auto-create (agar nahi hain)"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            is_mysql = getattr(conn, "_is_mysql", False)
            
            if is_mysql:
                # ================= MYSQL SCHEMA =================
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id VARCHAR(36) PRIMARY KEY,
                        full_name VARCHAR(100) NOT NULL,
                        email VARCHAR(100) UNIQUE NOT NULL,
                        phone VARCHAR(20),
                        password_hash VARCHAR(255) NOT NULL,
                        role VARCHAR(20) DEFAULT 'farmer',
                        location VARCHAR(100),
                        is_active BOOLEAN DEFAULT 1,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS scans (
                        id VARCHAR(36) PRIMARY KEY,
                        user_id VARCHAR(36),
                        crop_type VARCHAR(50),
                        image_url VARCHAR(500),
                        predicted_disease VARCHAR(100),
                        confidence FLOAT,
                        ai_advice TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS consultations (
                        id VARCHAR(36) PRIMARY KEY,
                        scan_id VARCHAR(36),
                        farmer_id VARCHAR(36),
                        expert_id VARCHAR(36) NULL,
                        status VARCHAR(20) DEFAULT 'pending',
                        message TEXT,
                        expert_reply TEXT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        resolved_at DATETIME NULL,
                        FOREIGN KEY (scan_id) REFERENCES scans(id),
                        FOREIGN KEY (farmer_id) REFERENCES users(id),
                        FOREIGN KEY (expert_id) REFERENCES users(id)
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS diseases (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        crop VARCHAR(50),
                        disease_name VARCHAR(100),
                        symptoms TEXT,
                        causes TEXT,
                        chemical_treatment TEXT,
                        organic_treatment TEXT,
                        prevention TEXT,
                        severity_level INT DEFAULT 3
                    )
                """)
            else:
                # ================= SQL SERVER SCHEMA =================
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
                    CREATE TABLE users (
                        id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
                        full_name NVARCHAR(100) NOT NULL,
                        email NVARCHAR(100) UNIQUE NOT NULL,
                        phone NVARCHAR(20),
                        password_hash NVARCHAR(255) NOT NULL,
                        role NVARCHAR(20) DEFAULT 'farmer',
                        location NVARCHAR(100),
                        is_active BIT DEFAULT 1,
                        created_at DATETIME DEFAULT GETDATE()
                    )
                """)
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='scans' AND xtype='U')
                    CREATE TABLE scans (
                        id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
                        user_id UNIQUEIDENTIFIER,
                        crop_type NVARCHAR(50),
                        image_url NVARCHAR(500),
                        predicted_disease NVARCHAR(100),
                        confidence FLOAT,
                        ai_advice NVARCHAR(MAX),
                        created_at DATETIME DEFAULT GETDATE(),
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """)
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='consultations' AND xtype='U')
                    CREATE TABLE consultations (
                        id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
                        scan_id UNIQUEIDENTIFIER,
                        farmer_id UNIQUEIDENTIFIER,
                        expert_id UNIQUEIDENTIFIER NULL,
                        status NVARCHAR(20) DEFAULT 'pending',
                        message NVARCHAR(MAX),
                        expert_reply NVARCHAR(MAX) NULL,
                        created_at DATETIME DEFAULT GETDATE(),
                        resolved_at DATETIME NULL,
                        FOREIGN KEY (scan_id) REFERENCES scans(id),
                        FOREIGN KEY (farmer_id) REFERENCES users(id),
                        FOREIGN KEY (expert_id) REFERENCES users(id)
                    )
                """)
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='diseases' AND xtype='U')
                    CREATE TABLE diseases (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        crop NVARCHAR(50),
                        disease_name NVARCHAR(100),
                        symptoms NVARCHAR(MAX),
                        causes NVARCHAR(MAX),
                        chemical_treatment NVARCHAR(MAX),
                        organic_treatment NVARCHAR(MAX),
                        prevention NVARCHAR(MAX),
                        severity_level INT DEFAULT 3
                    )
                """)

            # --------------------------------------------------------------------------
            # SEED DISEASE KNOWLEDGE BASE (18 DISEASES)
            # --------------------------------------------------------------------------
            cursor.execute("SELECT COUNT(*) FROM diseases")
            if cursor.fetchone()[0] == 0:
                print("[INFO] Populating Disease Knowledge Base...")
                diseases_data = [
                    # POTATO
                    ("potato", "Late Blight", "Pattay par bhooray dhabay, safed phaphundi", "Phytophthora infestans fungus", "Fungicide (Mancozeb, Metalaxyl) ka spray karein", "Neem oil spray, khet mein hawa ka guzar rakhein", "Beemar pauday hata dein, beej certified use karein", 5),
                    ("potato", "Early Blight", "Pattay par gol nishan (target board jaise)", "Alternaria solani fungus", "Chlorothalonil ya Copper based fungicide", "Crop rotation karein, kheton ki safai rakhein", "Paudhon ke darmiyan fasla rakhein", 4),
                    ("potato", "Healthy", "Paudha hara bhara aur saaf hai", "N/A", "N/A", "N/A", "Waqt par pani aur khad dein", 1),
                    
                    # TOMATO
                    ("tomato", "Bacterial Spot", "Pattay par chhote kalay dhabay, peelapan", "Xanthomonas bacteria", "Copper fungicide aur Mancozeb ka spray", "Beej ko garam pani se treat karein", "Khet mein humidity kam rakhein", 4),
                    ("tomato", "Early Blight", "Pattay par gol bhooray dhabay", "Alternaria solani", "Fungicide (Chlorothalonil) spray", "Purane pattay hata dein", "Crop rotation (3 saal)", 4),
                    ("tomato", "Late Blight", "Bade bhooray dhabay, safed phaphundi", "Phytophthora infestans", "Fungicide (Metalaxyl) spray", "Neem oil, hawa ka guzar", "Beemar pauday fauran jalayein", 5),
                    ("tomato", "Leaf Mold", "Pattay ke neechay olive-green phaphundi", "Passalora fulva", "Fungicide spray", "Greenhouse mein hawa ka guzar behtar banayein", "Humidity kam rakhein", 3),
                    ("tomato", "Septoria Leaf Spot", "Chhote gol dhabay jin ke darmiyan safed hota hai", "Septoria lycopersici fungus", "Chlorothalonil fungicide spray", "Khet ki safai, weed control", "Crop rotation karein", 3),
                    ("tomato", "Spider Mites", "Pattay par peele dhabay, baarik jaale", "Tetranychus urticae", "Miticide (Abamectin) spray", "Neem oil spray karein", "Khet ko khushk na hone dein", 4),
                    ("tomato", "Target Spot", "Bhooray dhabay jin mein rings hon", "Corynespora cassiicola", "Fungicide spray", "Hawa ka guzar", "Paudhon ke darmiyan fasla", 3),
                    ("tomato", "Yellow Leaf Curl Virus", "Pattay peele aur upar ki taraf mud jate hain", "Begomovirus (Whitefly se phailta hai)", "Whitefly control (Imidacloprid spray)", "Yellow sticky traps lagayein", "Beemar pauday fauran ukharein", 5),
                    ("tomato", "Mosaic Virus", "Pattay par peele aur hare dhabay (mosaic pattern)", "Tobacco Mosaic Virus (TMV)", "Iska koi chemical ilaj nahi hai", "Tools ko sanitize karein", "Resistant beej use karein, haath dho kar kaam karein", 5),
                    ("tomato", "Healthy", "Paudha hara bhara aur saaf hai", "N/A", "N/A", "N/A", "Waqt par pani aur khad dein", 1),
                    
                    # PEPPER
                    ("pepper", "Bacterial Spot", "Pattay par chhote kalay dhabay, peelapan", "Xanthomonas bacteria", "Copper based fungicide ka spray", "Beej ko treat karein", "Khet mein humidity kam rakhein", 4),
                    ("pepper", "Healthy", "Paudha hara bhara aur saaf hai", "N/A", "N/A", "N/A", "Waqt par pani aur khad dein", 1),
                    
                    # CORN
                    ("corn", "Common Rust", "Pattay par lal-bhooray zang jaise dhabay", "Puccinia sorghi fungus", "Fungicide (Pyraclostrobin) ka spray", "Resistant varieties lagayein", "Khet ki safai", 3),
                    ("corn", "Gray Leaf Spot", "Pattay par lambay bhooray dhabay", "Cercospora zeae-maydis", "Fungicide (Azoxystrobin) spray", "Crop rotation, tilling", "Beemar residue zameen mein daba dein", 4),
                    ("corn", "Northern Leaf Blight", "Pattay par lambay cigar shape ke dhabay", "Exserohilum turcicum", "Fungicide spray", "Resistant varieties", "Crop rotation", 4),
                    ("corn", "Healthy", "Paudha hara bhara aur saaf hai", "N/A", "N/A", "N/A", "Waqt par pani aur khad dein", 1)
                ]
                
                cursor.executemany("""
                    INSERT INTO diseases (crop, disease_name, symptoms, causes, chemical_treatment, organic_treatment, prevention, severity_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, diseases_data)
                
            conn.commit()
            print("[SUCCESS] Database tables ready & seeded!")
    except Exception as e:
        print(f"[WARNING] Database setup warning: {e}")
        print("   Make sure SQL Server is running and PlantDoctor database exists.")

# ==============================================================================
# PYDANTIC MODELS (Request/Response)
# ==============================================================================
class UserRegister(BaseModel):
    full_name: str
    email: str
    password: str
    phone: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

class RoleUpdate(BaseModel):
    role: str  # farmer, expert, admin

class ConsultationCreate(BaseModel):
    scan_id: str
    message: str

class ConsultationReply(BaseModel):
    reply: str

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(user_id: str, role: str, email: str) -> str:
    return jwt.encode(
        {"user_id": user_id, "role": role, "email": email},
        SECRET_KEY,
        algorithm="HS256"
    )

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_admin(user=Depends(verify_token)):
    """Admin-only guard — non-admin ko reject karo"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# ==============================================================================
# AUTH APIs
# ==============================================================================

@app.post("/api/auth/register")
def register(user: UserRegister):
    """New user registration"""
    # Validation
    if len(user.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if not user.full_name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    if "@" not in user.email:
        raise HTTPException(status_code=400, detail="Invalid email format")

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Check duplicate email
            cursor.execute("SELECT id FROM users WHERE email = ?", user.email.lower().strip())
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Email already registered")

            # Insert user
            user_id = str(uuid.uuid4())
            password_hash = hash_password(user.password)

            cursor.execute("""
                INSERT INTO users (id, full_name, email, phone, password_hash, role)
                VALUES (?, ?, ?, ?, ?, ?)
            """, user_id, user.full_name.strip(), user.email.lower().strip(),
                 user.phone, password_hash, 'farmer')

            conn.commit()

        return {"message": "User registered successfully", "user_id": user_id}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print("REGISTER ERROR:", error_details)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/login")
def login(user: UserLogin):
    """User login — returns JWT token"""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, password_hash, role, full_name FROM users 
            WHERE email = ? AND is_active = 1
        """, user.email.lower().strip())

        db_user = cursor.fetchone()

    if not db_user or not verify_password(user.password, db_user[1]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(str(db_user[0]), db_user[2], user.email.lower().strip())

    return {
        "token": token,
        "role": db_user[2],
        "full_name": db_user[3],
        "email": user.email.lower().strip()
    }


@app.get("/api/auth/me")
def get_current_user(user=Depends(verify_token)):
    """Current logged-in user ki info"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, full_name, email, phone, role, location, created_at
            FROM users WHERE id = ?
        """, user["user_id"])
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": str(row[0]),
        "full_name": row[1],
        "email": row[2],
        "phone": row[3],
        "role": row[4],
        "location": row[5],
        "created_at": str(row[6]) if row[6] else None
    }


@app.put("/api/auth/profile")
def update_profile(profile: ProfileUpdate, user=Depends(verify_token)):
    """Profile update — name, phone, location"""
    with get_db() as conn:
        cursor = conn.cursor()

        updates = []
        params = []
        if profile.full_name is not None:
            updates.append("full_name = ?")
            params.append(profile.full_name.strip())
        if profile.phone is not None:
            updates.append("phone = ?")
            params.append(profile.phone)
        if profile.location is not None:
            updates.append("location = ?")
            params.append(profile.location)

        if not updates:
            raise HTTPException(status_code=400, detail="Nothing to update")

        params.append(user["user_id"])
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, *params)
        conn.commit()

    return {"message": "Profile updated successfully"}


@app.put("/api/auth/password")
def change_password(data: PasswordChange, user=Depends(verify_token)):
    """Password change — old password verify ke baad"""
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE id = ?", user["user_id"])
        row = cursor.fetchone()

        if not row or not verify_password(data.old_password, row[0]):
            raise HTTPException(status_code=401, detail="Current password is incorrect")

        new_hash = hash_password(data.new_password)
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                       new_hash, user["user_id"])
        conn.commit()

    return {"message": "Password changed successfully"}


# ==============================================================================
# SCAN APIs
# ==============================================================================

@app.post("/api/scans")
def save_scan(crop: str, disease: str, confidence: float,
              image: UploadFile = File(...), user=Depends(verify_token)):
    """Scan result save karo database mein"""
    # Ensure uploads directory exists
    user_dir = f"uploads/{user['user_id']}"
    os.makedirs(user_dir, exist_ok=True)

    # Save image
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{crop}_{timestamp}_{image.filename}"
    image_path = f"{user_dir}/{filename}"
    with open(image_path, "wb") as f:
        f.write(image.file.read())

    # Save to database
    scan_id = str(uuid.uuid4())
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scans (id, user_id, crop_type, image_url, predicted_disease, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        """, scan_id, user['user_id'], crop, image_path, disease, confidence)
        conn.commit()

    return {"message": "Scan saved", "scan_id": scan_id}


@app.get("/api/scans/history")
def get_history(user=Depends(verify_token)):
    """Current user ki scan history"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, crop_type, image_url, predicted_disease, confidence, created_at
            FROM scans WHERE user_id = ? ORDER BY created_at DESC
        """, user['user_id'])

        columns = [column[0] for column in cursor.description]
        scans = []
        for row in cursor.fetchall():
            scan = dict(zip(columns, row))
            # Convert UUID and datetime to strings
            scan['id'] = str(scan['id'])
            scan['created_at'] = str(scan['created_at']) if scan['created_at'] else None
            scans.append(scan)

    return {"scans": scans}


@app.get("/api/scans/stats")
def get_user_stats(user=Depends(verify_token)):
    """Current user ke scan statistics"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Total scans
        cursor.execute("SELECT COUNT(*) FROM scans WHERE user_id = ?", user['user_id'])
        total_scans = cursor.fetchone()[0]

        # Crop-wise breakdown
        cursor.execute("""
            SELECT crop_type, COUNT(*) as count
            FROM scans WHERE user_id = ?
            GROUP BY crop_type
        """, user['user_id'])
        crop_breakdown = {row[0]: row[1] for row in cursor.fetchall()}

        # Disease count (excluding healthy)
        cursor.execute("""
            SELECT COUNT(*) FROM scans 
            WHERE user_id = ? AND predicted_disease NOT LIKE '%Healthy%'
        """, user['user_id'])
        disease_count = cursor.fetchone()[0]

        # Recent 7 days scan count
        cursor.execute("""
            SELECT COUNT(*) FROM scans 
            WHERE user_id = ? AND created_at >= DATEADD(day, -7, GETDATE())
        """, user['user_id'])
        weekly_scans = cursor.fetchone()[0]

        # Average confidence
        cursor.execute("SELECT AVG(confidence) FROM scans WHERE user_id = ?", user['user_id'])
        avg_conf = cursor.fetchone()[0]

    return {
        "total_scans": total_scans,
        "crop_breakdown": crop_breakdown,
        "disease_count": disease_count,
        "healthy_count": total_scans - disease_count,
        "weekly_scans": weekly_scans,
        "avg_confidence": round(float(avg_conf), 1) if avg_conf else 0
    }


# ==============================================================================
# CONSULTATION APIs
# ==============================================================================

@app.post("/api/consultations")
def create_consultation(data: ConsultationCreate, user=Depends(verify_token)):
    """Farmer expert se consultation request karega"""
    consult_id = str(uuid.uuid4())
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO consultations (id, scan_id, farmer_id, message, status)
            VALUES (?, ?, ?, ?, 'pending')
        """, consult_id, data.scan_id, user['user_id'], data.message)
        conn.commit()

    return {"message": "Consultation request sent", "consultation_id": consult_id}


@app.get("/api/consultations")
def get_consultations(user=Depends(verify_token)):
    """Consultations list — farmer apni dekhega, expert pending dekhega"""
    with get_db() as conn:
        cursor = conn.cursor()

        if user['role'] == 'expert':
            # Expert ko pending consultations dikhao
            cursor.execute("""
                SELECT c.id, c.scan_id, c.farmer_id, c.message, c.status, c.created_at,
                       u.full_name as farmer_name, s.crop_type, s.predicted_disease
                FROM consultations c
                JOIN users u ON c.farmer_id = u.id
                JOIN scans s ON c.scan_id = s.id
                WHERE c.status = 'pending' OR c.expert_id = ?
                ORDER BY c.created_at DESC
            """, user['user_id'])
        else:
            # Farmer apni consultations dekhega
            cursor.execute("""
                SELECT c.id, c.scan_id, c.message, c.expert_reply, c.status, c.created_at,
                       s.crop_type, s.predicted_disease
                FROM consultations c
                JOIN scans s ON c.scan_id = s.id
                WHERE c.farmer_id = ?
                ORDER BY c.created_at DESC
            """, user['user_id'])

        columns = [col[0] for col in cursor.description]
        results = []
        for row in cursor.fetchall():
            item = dict(zip(columns, row))
            # Convert types
            for k, v in item.items():
                if isinstance(v, uuid.UUID):
                    item[k] = str(v)
                elif isinstance(v, datetime.datetime):
                    item[k] = str(v)
            results.append(item)

    return {"consultations": results}


@app.put("/api/consultations/{consult_id}/reply")
def reply_consultation(consult_id: str, data: ConsultationReply, user=Depends(verify_token)):
    """Expert consultation ka jawab dega"""
    if user['role'] not in ['expert', 'admin']:
        raise HTTPException(status_code=403, detail="Only experts can reply")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE consultations 
            SET expert_reply = ?, expert_id = ?, status = 'resolved', resolved_at = GETDATE()
            WHERE id = ?
        """, data.reply, user['user_id'], consult_id)
        conn.commit()

    return {"message": "Reply sent successfully"}


# ==============================================================================
# ADMIN APIs (admin role only)
# ==============================================================================

@app.get("/api/admin/stats")
def admin_stats(user=Depends(require_admin)):
    """Admin dashboard — overall platform stats"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Total users
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        # Total scans
        cursor.execute("SELECT COUNT(*) FROM scans")
        total_scans = cursor.fetchone()[0]

        # Today's scans
        cursor.execute("""
            SELECT COUNT(*) FROM scans 
            WHERE CAST(created_at AS DATE) = CAST(GETDATE() AS DATE)
        """)
        today_scans = cursor.fetchone()[0]

        # Users by role
        cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
        roles = {row[0]: row[1] for row in cursor.fetchall()}

        # Scans by crop
        cursor.execute("SELECT crop_type, COUNT(*) FROM scans GROUP BY crop_type")
        crops = {row[0]: row[1] for row in cursor.fetchall()}

        # Top diseases
        cursor.execute("""
            SELECT TOP 5 predicted_disease, COUNT(*) as cnt 
            FROM scans 
            WHERE predicted_disease NOT LIKE '%Healthy%'
            GROUP BY predicted_disease 
            ORDER BY cnt DESC
        """)
        top_diseases = {row[0]: row[1] for row in cursor.fetchall()}

        # Weekly new users
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE created_at >= DATEADD(day, -7, GETDATE())
        """)
        weekly_users = cursor.fetchone()[0]

        # Pending consultations
        cursor.execute("SELECT COUNT(*) FROM consultations WHERE status = 'pending'")
        pending_consults = cursor.fetchone()[0]

    return {
        "total_users": total_users,
        "total_scans": total_scans,
        "today_scans": today_scans,
        "weekly_new_users": weekly_users,
        "users_by_role": roles,
        "scans_by_crop": crops,
        "top_diseases": top_diseases,
        "pending_consultations": pending_consults
    }


@app.get("/api/admin/users")
def admin_get_users(user=Depends(require_admin)):
    """All users list for admin"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.full_name, u.email, u.phone, u.role, u.is_active, u.created_at,
                   (SELECT COUNT(*) FROM scans WHERE user_id = u.id) as scan_count
            FROM users u
            ORDER BY u.created_at DESC
        """)
        columns = [col[0] for col in cursor.description]
        users = []
        for row in cursor.fetchall():
            u = dict(zip(columns, row))
            u['id'] = str(u['id'])
            u['created_at'] = str(u['created_at']) if u['created_at'] else None
            users.append(u)

    return {"users": users}


@app.put("/api/admin/users/{user_id}/role")
def admin_change_role(user_id: str, data: RoleUpdate, admin=Depends(require_admin)):
    """User ka role change karo (farmer → expert → admin)"""
    if data.role not in ['farmer', 'expert', 'admin']:
        raise HTTPException(status_code=400, detail="Role must be: farmer, expert, or admin")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = ? WHERE id = ?", data.role, user_id)
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
        conn.commit()

    return {"message": f"User role updated to {data.role}"}


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: str, admin=Depends(require_admin)):
    """User delete (soft delete — is_active = 0)"""
    if user_id == admin['user_id']:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", user_id)
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
        conn.commit()

    return {"message": "User deactivated"}


@app.get("/api/admin/scans")
def admin_get_scans(
    crop: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    admin=Depends(require_admin)
):
    """All scans for admin — with optional crop filter"""
    with get_db() as conn:
        cursor = conn.cursor()

        if crop:
            cursor.execute(f"""
                SELECT TOP {limit} s.id, s.crop_type, s.predicted_disease, s.confidence, 
                       s.created_at, u.full_name, u.email
                FROM scans s
                JOIN users u ON s.user_id = u.id
                WHERE s.crop_type = ?
                ORDER BY s.created_at DESC
            """, crop)
        else:
            cursor.execute(f"""
                SELECT TOP {limit} s.id, s.crop_type, s.predicted_disease, s.confidence,
                       s.created_at, u.full_name, u.email
                FROM scans s
                JOIN users u ON s.user_id = u.id
                ORDER BY s.created_at DESC
            """)

        columns = [col[0] for col in cursor.description]
        scans = []
        for row in cursor.fetchall():
            scan = dict(zip(columns, row))
            scan['id'] = str(scan['id'])
            scan['created_at'] = str(scan['created_at']) if scan['created_at'] else None
            scans.append(scan)

    return {"scans": scans}


# ==============================================================================
# HEALTH CHECK
# ==============================================================================
@app.get("/api/health")
def health_check():
    """Server health check"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
        db_status = "connected"
    except:
        db_status = "disconnected"

    return {
        "status": "running",
        "database": db_status,
        "version": "2.0.0",
        "timestamp": str(datetime.datetime.now())
    }


# ==============================================================================
# RUN SERVER
# ==============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)