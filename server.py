from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from datetime import datetime, timezone, timedelta
import uuid
import os
import json
import requests
from pathlib import Path
import logging
import re
import hashlib
import jwt
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Literal, Optional, List, Dict
import sqlite3
from contextlib import contextmanager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enhanced configuration
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
JWT_SECRET = os.getenv("JWT_SECRET", "courtroom_simulator_secret_key")
security = HTTPBearer()

app = FastAPI(
    title="AI Courtroom Simulator - Advanced Edition",
    description="Professional-grade courtroom simulation with AI judges, evidence management, and analytics",
    version="2.0.0"
)

# Ollama Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "127.0.0.1")
OLLAMA_PORT = os.getenv("OLLAMA_PORT", "11434")
OLLAMA_BASE = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"
OLLAMA_API_URL = f"{OLLAMA_BASE}/api/generate"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

# Enhanced CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PUT"],
    allow_headers=["*"],
)

# Enhanced Data Models
class CaseType(BaseModel):
    type: Literal["criminal", "civil", "family", "corporate", "constitutional"] = "criminal"
    severity: Literal["minor", "major", "felony"] = "minor"
    jurisdiction: Literal["district", "high", "supreme"] = "district"

class Evidence(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: Literal["document", "photo", "video", "audio", "witness"] = "document"
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    file_path: Optional[str] = None
    submitted_by: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class StartSessionRequest(BaseModel):
    case_facts: str = Field(..., min_length=10, max_length=5000)
    user_role: Literal["defense", "prosecution", "judge", "witness", "jury"] = "defense"
    case_type: CaseType = Field(default_factory=CaseType)
    case_title: str = Field(..., min_length=5, max_length=200)
    participants: List[str] = Field(default_factory=list)

class SimulateStepRequest(BaseModel):
    session_id: str = Field(..., pattern=r'^[a-f0-9]{8}$')
    user_input: str = Field(..., min_length=1, max_length=2000)
    action_type: Literal["argument", "objection", "evidence", "motion", "ruling"] = "argument"
    evidence_ids: List[str] = Field(default_factory=list)

class UserAuth(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    role: Literal["lawyer", "judge", "student", "admin"] = "student"

# Database setup
DB_PATH = Path("courtroom.db")

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_database():
    """Initialize SQLite database with tables"""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT
            );
            
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                case_type TEXT NOT NULL,
                user_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                verdict TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
            
            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                file_path TEXT,
                submitted_by TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            );
            
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY,
                session_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            );
        """)
        conn.commit()

# Initialize database on startup
init_database()

# Enhanced directories
SESSIONS_DIR = Path("sessions")
EVIDENCE_DIR = Path("evidence")
SESSIONS_DIR.mkdir(exist_ok=True)
EVIDENCE_DIR.mkdir(exist_ok=True)

# In-memory caches
sessions = {}
user_sessions = {}

# Enhanced legal knowledge base
LEGAL_PRECEDENTS = {
    "criminal": [
        "Presumption of innocence until proven guilty",
        "Burden of proof lies with prosecution",
        "Evidence must be beyond reasonable doubt",
        "Right to legal representation"
    ],
    "civil": [
        "Preponderance of evidence standard",
        "Plaintiff bears burden of proof",
        "Damages must be quantifiable",
        "Equitable remedies available"
    ],
    "constitutional": [
        "Fundamental rights are non-negotiable",
        "Due process must be followed",
        "Equal protection under law",
        "Judicial review principles"
    ]
}

OBJECTION_TYPES = [
    "Hearsay", "Leading question", "Argumentative", "Assumes facts not in evidence",
    "Irrelevant", "Speculation", "Compound question", "Asked and answered"
]

# Enhanced AI response system
def get_legal_context(case_type: str, action_type: str) -> str:
    """Get relevant legal context for AI responses"""
    precedents = LEGAL_PRECEDENTS.get(case_type, LEGAL_PRECEDENTS["criminal"])
    context = f"Legal precedents for {case_type} cases: " + "; ".join(precedents[:2])
    
    if action_type == "objection":
        context += f" Common objections: {', '.join(OBJECTION_TYPES[:3])}"
    
    return context

def generate_enhanced_ai_response(role: str, case_data: dict, transcript: list, user_input: str, action_type: str = "argument") -> str:
    """Enhanced AI response with legal knowledge and context"""
    
    # Check relevance first
    if not is_relevant_to_case(user_input, case_data.get("case_facts", "")):
        return get_irrelevance_response(role)
    
    try:
        # Enhanced context building
        case_type = case_data.get("case_type", {}).get("type", "criminal")
        legal_context = get_legal_context(case_type, action_type)
        recent_transcript = "\n".join([f"{entry['speaker']}: {entry['text']}" for entry in transcript[-6:]])
        
        # Role-specific enhanced prompts
        if role == "judge":
            prompt = f"""As a professional {case_data.get('case_type', {}).get('jurisdiction', 'district')} court judge in India, provide a judicial response (2-3 sentences):

Case Type: {case_type.title()} Law
Legal Context: {legal_context}
Case Facts: {case_data.get('case_facts', '')[:150]}
Recent Proceedings: {recent_transcript[-300:]}
Current Action: {action_type.title()}
User Statement: {user_input[:150]}

Provide a measured judicial response considering legal precedents and courtroom procedure:"""

        elif role == "opposing_counsel":
            prompt = f"""As an experienced {case_type} law attorney, respond professionally (2-3 sentences):

Case Type: {case_type.title()} Law
Legal Context: {legal_context}
Case Facts: {case_data.get('case_facts', '')[:150]}
Recent Arguments: {recent_transcript[-300:]}
Opponent's Action: {action_type.title()}
Opponent Said: {user_input[:150]}

Provide a strategic legal counter-argument or response:"""

        else:  # witness, jury, etc.
            prompt = f"""As a {role} in a {case_type} case, respond appropriately (1-2 sentences):

Case Context: {case_data.get('case_facts', '')[:100]}
Current Situation: {recent_transcript[-200:]}
Question/Statement: {user_input[:100]}

Respond as a {role} would in court:"""

        # Enhanced API call
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.7,
                "num_predict": 80,
                "top_p": 0.9,
            },
            timeout=20
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_text = result.get("response", "").strip()
            # Enhanced cleanup
            sentences = ai_text.split(". ")
            if len(sentences) > 3:
                ai_text = ". ".join(sentences[:3]) + "."
            return ai_text[:400]
        else:
            logger.warning(f"Ollama API error: {response.status_code}")
            return get_enhanced_fallback_response(role, action_type)
            
    except Exception as e:
        logger.error(f"Error generating AI response: {str(e)}")
        return get_enhanced_fallback_response(role, action_type)

def get_enhanced_fallback_response(role: str, action_type: str = "argument") -> str:
    """Enhanced fallback responses based on role and action"""
    import random
    
    if role == "judge":
        if action_type == "objection":
            responses = ["Objection noted. Please rephrase your question.", "Sustained. Counsel, please proceed differently."]
        else:
            responses = JUDGE_FALLBACKS
    elif role == "opposing_counsel":
        if action_type == "objection":
            responses = ["Your Honor, I object to that line of questioning.", "Objection! That's leading the witness."]
        else:
            responses = COUNSEL_FALLBACKS
    else:
        responses = [f"As a {role}, I must focus on the facts of this case.", "I can only speak to what I know about this matter."]
    
    return random.choice(responses)

# Authentication functions
def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == hashed

def create_jwt_token(user_data: dict) -> str:
    """Create JWT token for user"""
    payload = {
        "user_id": user_data["id"],
        "username": user_data["username"],
        "role": user_data["role"],
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_jwt_token(token: str) -> dict:
    """Verify JWT token and return user data"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    return verify_jwt_token(credentials.credentials)

# Enhanced utility functions
def is_relevant_to_case(user_input: str, case_facts: str) -> bool:
    """Enhanced relevance checking with legal context"""
    irrelevant_keywords = [
        'black hole', 'space', 'astronomy', 'physics', 'weather', 'food', 'sports',
        'movie', 'music', 'game', 'celebrity', 'programming', 'recipe', 'travel'
    ]
    
    legal_keywords = [
        'evidence', 'witness', 'testimony', 'guilty', 'innocent', 'verdict', 'objection',
        'law', 'legal', 'court', 'case', 'crime', 'defendant', 'plaintiff', 'judge',
        'jury', 'trial', 'hearing', 'motion', 'appeal', 'sentence', 'liability',
        'contract', 'agreement', 'damages', 'rights', 'violation', 'precedent'
    ]
    
    user_lower = user_input.lower()
    case_lower = case_facts.lower()
    
    # Enhanced checking
    for keyword in irrelevant_keywords:
        if keyword in user_lower and keyword not in case_lower:
            return False
    
    if len(user_input.strip()) < 8:
        return True
    
    has_legal_content = any(keyword in user_lower for keyword in legal_keywords)
    has_case_content = any(word in user_lower for word in case_lower.split() if len(word) > 3)
    
    return has_legal_content or has_case_content

def get_irrelevance_response(role: str) -> str:
    """Enhanced irrelevance responses"""
    if role == "judge":
        responses = [
            "Order in the court! Please keep your statements relevant to the legal matter at hand.",
            "Counsel, that question is not pertinent to this case. Please focus on the legal issues.",
            "I must remind all parties to maintain focus on the case before this court."
        ]
    else:
        responses = [
            "Your Honor, I object. That question is irrelevant to the case we're discussing.",
            "With respect, that topic is not related to the legal matter at hand.",
            "I must focus on the case facts and legal arguments relevant to this proceeding."
        ]
    
    import random
    return random.choice(responses)

def log_analytics_event(session_id: str, event_type: str, event_data: dict):
    """Log analytics events to database"""
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO analytics (session_id, event_type, event_data, timestamp) VALUES (?, ?, ?, ?)",
                (session_id, event_type, json.dumps(event_data), datetime.now(timezone.utc).isoformat())
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to log analytics: {e}")

# API Endpoints
@app.post("/auth/register")
async def register_user(user_data: UserAuth):
    """Register a new user"""
    try:
        with get_db() as conn:
            password_hash = hash_password(user_data.password)
            conn.execute(
                "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                (user_data.username, password_hash, user_data.role, datetime.now(timezone.utc).isoformat())
            )
            conn.commit()
            return {"message": "User registered successfully"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")

@app.post("/auth/login")
async def login_user(user_data: UserAuth):
    """Login user and return JWT token"""
    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (user_data.username,)
        ).fetchone()
        
        if not user or not verify_password(user_data.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Update last login
        conn.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), user["id"])
        )
        conn.commit()
        
        token = create_jwt_token(dict(user))
        return {"access_token": token, "token_type": "bearer", "user": {"username": user["username"], "role": user["role"]}}

@app.get("/")
def read_root():
    return {"message": "AI Courtroom Simulator - Advanced Edition", "version": "2.0.0"}

@app.get("/health")
def health_check():
    """Enhanced health check with system status"""
    try:
        ollama_response = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        ollama_available = ollama_response.status_code == 200
        models = ollama_response.json().get("models", []) if ollama_available else []
    except:
        ollama_available = False
        models = []
    
    with get_db() as conn:
        user_count = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()["count"]
        session_count = conn.execute("SELECT COUNT(*) as count FROM sessions").fetchone()["count"]
    
    return {
        "status": "healthy",
        "version": "2.0.0",
        "ollama_available": ollama_available,
        "available_models": [m["name"] for m in models],
        "active_sessions": len(sessions),
        "total_users": user_count,
        "total_sessions": session_count,
        "features": ["authentication", "evidence_management", "analytics", "multi_case_types"]
    }

@app.post("/sessions/start")
async def start_enhanced_session(request: StartSessionRequest, current_user: dict = Depends(get_current_user)):
    """Start an enhanced court session with full features"""
    session_id = str(uuid.uuid4())[:8]
    
    # Enhanced transcript initialization
    transcript = [
        {
            "speaker": "Court Clerk",
            "text": f"Case {session_id}: {request.case_title}. {request.case_type.jurisdiction.title()} Court is now in session.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action_type": "system"
        },
        {
            "speaker": "Judge",
            "text": f"Good morning. We are here for a {request.case_type.type} matter: {request.case_title}. {request.case_facts[:100]}...",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action_type": "opening"
        },
        {
            "speaker": "Bailiff",
            "text": f"The {request.user_role} has entered the courtroom and is ready to proceed.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action_type": "system"
        }
    ]
    
    # Enhanced session data
    session_data = {
        "session_id": session_id,
        "title": request.case_title,
        "case_facts": request.case_facts,
        "user_role": request.user_role,
        "case_type": request.case_type.dict(),
        "participants": request.participants,
        "transcript": transcript,
        "evidence": [],
        "motions": [],
        "objections": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
        "user_id": current_user["user_id"]
    }
    
    # Save to database and cache
    with get_db() as conn:
        conn.execute(
            "INSERT INTO sessions (id, title, case_type, user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, request.case_title, request.case_type.type, current_user["user_id"], 
             session_data["created_at"], session_data["updated_at"])
        )
        conn.commit()
    
    sessions[session_id] = session_data
    
    # Log analytics
    log_analytics_event(session_id, "session_started", {
        "case_type": request.case_type.type,
        "user_role": request.user_role,
        "user_id": current_user["user_id"]
    })
    
    return {
        "session_id": session_id,
        "transcript": transcript,
        "case_type": request.case_type,
        "status": "Session started successfully"
    }

if __name__ == "__main__":
    import uvicorn
    print("Starting Enhanced AI Courtroom Simulator on http://127.0.0.1:8000")
    print("Features: Authentication, Evidence Management, Analytics, Multi-Case Types")
    uvicorn.run(app, host="127.0.0.1", port=8000)