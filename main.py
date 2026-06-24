from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid
import sqlite3
import jwt
import bcrypt
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from agents.skills.math_deconstruction import execute_socratic_step

app = FastAPI(title="Socratic Tutor Engine")

DB_FILE = "tutor_sessions.db"
JWT_SECRET = "SUPER_SECRET_SIGNING_KEY_CHANGE_THIS_IN_PRODUCTION"
ALGORITHM = "HS256"

# Security utilities
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def init_db():
    """Initializes the local database with multi-tenant relational tables."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Create Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL
        )
    """)
    
    # 2. Create Sessions Table linked to Users
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            current_step INTEGER,
            problem TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Pydantic Schemas
class UserAuth(BaseModel):
    email: EmailStr
    password: str

class HomeworkRequest(BaseModel):
    problem: str
    grade_level: str = "High School"
    session_id: Optional[str] = None
    student_attempt: Optional[str] = None


# --- STEP 2: SECURITY HELPERS ---
def get_password_hash(password: str) -> str:
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    plain_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_bytes, hashed_bytes)

def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=12)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)

def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payloads.")
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials.")


# --- STEP 3: AUTHENTICATION ENDPOINTS ---


# Mount our visual UI asset layer
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_frontend():
    """Serves our visual chat platform directly on the root web address."""
    return FileResponse("static/index.html")
    
@app.post("/auth/register", status_code=201)
def register_user(user: UserAuth):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE email = ?", (user.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered.")
        
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user.password)
    
    cursor.execute("INSERT INTO users (id, email, hashed_password) VALUES (?, ?, ?)", (user_id, user.email, hashed_password))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "User account built successfully!"}

@app.post("/auth/login")
def login_user(user: UserAuth):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, hashed_password FROM users WHERE email = ?", (user.email,))
    user_record = cursor.fetchone()
    conn.close()
    
    if not user_record or not verify_password(user.password, user_record[1]):
        raise HTTPException(status_code=400, detail="Incorrect email or password.")
        
    access_token = create_access_token(data={"sub": user_record[0]})
    return {"access_token": access_token, "token_type": "bearer"}


# --- STEP 4: CORE TUTOR ROUTE ---
@app.post("/tutor/solve")
async def process_homework(request: HomeworkRequest, user_id: str = Depends(get_current_user_id)):
    try:
        active_session = request.session_id
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        existing_session = None
        if active_session:
            cursor.execute(
                "SELECT current_step, problem FROM sessions WHERE session_id = ? AND user_id = ?", 
                (active_session, user_id)
            )
            existing_session = cursor.fetchone()
        
        if not active_session or not existing_session:
            active_session = str(uuid.uuid4())
            current_step = 1
            problem_text = request.problem
            
            cursor.execute(
                "INSERT INTO sessions (session_id, user_id, current_step, problem) VALUES (?, ?, ?, ?)",
                (active_session, user_id, current_step, problem_text)
            )
            conn.commit()
            
        elif existing_session[1] != request.problem:
            current_step = 1
            problem_text = request.problem
            
            cursor.execute(
                "UPDATE sessions SET current_step = ?, problem = ? WHERE session_id = ? AND user_id = ?",
                (current_step, problem_text, active_session, user_id)
            )
            conn.commit()
            
        else:
            current_step = existing_session[0]
            problem_text = existing_session[1]
        
        socratic_response = execute_socratic_step(
            problem=problem_text,
            grade_level=request.grade_level,
            current_step=current_step,
            student_attempt=request.student_attempt
        )
        
        if request.student_attempt:
            current_step += 1
            cursor.execute(
                "UPDATE sessions SET current_step = ? WHERE session_id = ? AND user_id = ?", 
                (current_step, active_session, user_id)
            )
            conn.commit()
            
        conn.close()
            
        return {
            "status": "success",
            "session_id": active_session,
            "data": {
                "response": socratic_response,
                "current_step": current_step
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy"}