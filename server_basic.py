from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
import os
import json
import requests
from pathlib import Path
import logging
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Literal

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Thread pool for parallel AI requests
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "2"))
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

app = FastAPI(title="AI Courtroom Simulator Backend")

# Ollama Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "127.0.0.1")
OLLAMA_PORT = os.getenv("OLLAMA_PORT", "11434")
OLLAMA_BASE = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"
OLLAMA_API_URL = f"{OLLAMA_BASE}/api/generate"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

# Enable CORS for Streamlit frontend - restrict origins in production
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# Data Models with validation
class StartSessionRequest(BaseModel):
    case_facts: str = Field(..., min_length=10, max_length=5000, description="Case facts (10-5000 characters)")
    user_role: Literal["defense", "prosecution", "judge"] = Field(..., description="User role in the courtroom")

class SimulateStepRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=8, pattern=r'^[a-f0-9]{8}$', description="8-character hex session ID")
    user_input: str = Field(..., min_length=1, max_length=1000, description="User input (1-1000 characters)")

# In-memory session storage
sessions = {}

# Sessions directory for persistence
SESSIONS_DIR = Path("sessions")
SESSIONS_DIR.mkdir(exist_ok=True)

def validate_session_id(session_id: str) -> bool:
    """Validate session ID to prevent path traversal"""
    return bool(re.match(r'^[a-f0-9]{8}$', session_id))

def load_session(session_id: str):
    """Load session from file if it exists - secure version"""
    if not validate_session_id(session_id):
        logger.warning(f"Invalid session ID format: {session_id}")
        return None
    
    session_file = SESSIONS_DIR / f"{session_id}.txt"
    if session_file.exists():
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                return json.loads(f.read())
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading session {session_id}: {e}")
            return None
    return None

def save_session(session_id: str, session_data: dict):
    """Save session to file - secure version"""
    if not validate_session_id(session_id):
        logger.warning(f"Invalid session ID format: {session_id}")
        return False
    
    session_file = SESSIONS_DIR / f"{session_id}.txt"
    try:
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, default=str)
        return True
    except IOError as e:
        logger.error(f"Error saving session {session_id}: {e}")
        return False

# Fallback response constants
JUDGE_FALLBACKS = [
    "I see. Let me review the evidence presented before making a decision.",
    "That is noted. Counsel, do you have additional evidence to support this claim?",
    "Interesting argument. However, I must consider the legal precedents.",
    "The court acknowledges your statement. Continue with your case."
]

COUNSEL_FALLBACKS = [
    "Your Honor, with respect, I must point out that the evidence presented is insufficient.",
    "I disagree with that characterization. The facts clearly show otherwise.",
    "Your Honor, my client maintains their innocence based on the following grounds...",
    "The prosecution has failed to establish a prima facie case against my client."
]

def is_relevant_to_case(user_input: str, case_facts: str) -> bool:
    """Check if user input is relevant to the legal case"""
    # Keywords that indicate irrelevant topics
    irrelevant_keywords = [
        'black hole', 'space', 'astronomy', 'physics', 'science', 'weather', 'food', 'sports',
        'movie', 'music', 'game', 'celebrity', 'technology', 'computer', 'programming',
        'recipe', 'travel', 'vacation', 'animal', 'plant', 'color', 'number', 'math',
        'history', 'geography', 'art', 'literature', 'philosophy', 'religion'
    ]
    
    # Legal keywords that should be present
    legal_keywords = [
        'evidence', 'witness', 'testimony', 'guilty', 'innocent', 'verdict', 'objection',
        'law', 'legal', 'court', 'case', 'crime', 'defendant', 'plaintiff', 'judge',
        'jury', 'trial', 'hearing', 'motion', 'appeal', 'sentence', 'fine', 'prison',
        'contract', 'agreement', 'liability', 'damages', 'rights', 'violation'
    ]
    
    user_lower = user_input.lower()
    case_lower = case_facts.lower()
    
    # Check for irrelevant keywords
    for keyword in irrelevant_keywords:
        if keyword in user_lower and keyword not in case_lower:
            return False
    
    # If input is very short, assume it's relevant
    if len(user_input.strip()) < 10:
        return True
    
    # Check for legal keywords or case-related terms
    has_legal_content = any(keyword in user_lower for keyword in legal_keywords)
    has_case_content = any(word in user_lower for word in case_lower.split() if len(word) > 3)
    
    return has_legal_content or has_case_content

def get_irrelevance_response(role: str) -> str:
    """Response when user asks irrelevant questions"""
    if role == "judge":
        responses = [
            "Order in the court! Please keep your statements relevant to the case at hand.",
            "Counsel, that question is not pertinent to this legal matter. Please proceed with case-related arguments.",
            "I must remind you to focus on the legal issues before this court."
        ]
    else:
        responses = [
            "Your Honor, I object. That question is irrelevant to the case we're discussing.",
            "With respect, that topic is not related to the legal matter at hand.",
            "I must focus on the case facts and legal arguments relevant to this proceeding."
        ]
    
    import random
    return random.choice(responses)

def get_fallback_response(role: str) -> str:
    """Fallback responses if Ollama is not available"""
    import random
    if role == "judge":
        return random.choice(JUDGE_FALLBACKS)
    else:
        return random.choice(COUNSEL_FALLBACKS)

def generate_ai_response(role: str, case_facts: str, transcript: list, user_input: str) -> str:
    """Generate AI response using Ollama model"""
    # Check if user input is relevant to the case
    if not is_relevant_to_case(user_input, case_facts):
        return get_irrelevance_response(role)
    
    try:
        # Build context from transcript (shorter for faster processing)
        transcript_text = "\n".join([f"{entry['speaker']}: {entry['text']}" for entry in transcript[-4:]])
        
        # Create role-specific prompts (shorter = faster)
        if role == "judge":
            prompt = f"""As an Indian High Court Judge, respond briefly (1-2 sentences) ONLY about this legal case. If asked about unrelated topics, redirect to the case:

Case: {case_facts[:100]}
Recent: {transcript_text[-200:]}
User said: {user_input[:100]}

Judicial response:"""
            
        else:  # opposing counsel
            prompt = f"""As a defense lawyer, respond briefly (1-2 sentences) ONLY about this legal case. If asked about unrelated topics, object or redirect:

Case: {case_facts[:100]}
Recent: {transcript_text[-200:]}
User said: {user_input[:100]}

Legal response:"""
        
        # Call Ollama API with optimized settings
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.6,
                "num_predict": 50,  # Limit output tokens
                "top_p": 0.9,
            },
            timeout=15  # Reduced timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_text = result.get("response", "").strip()
            # Clean up response
            ai_text = ai_text.split("\n")[0] if ai_text else "Proceed with your argument."
            return ai_text[:300]  # Limit to 300 chars
        else:
            logger.warning(f"Ollama API error: {response.status_code}")
            return "Please continue with your case."
            
    except requests.exceptions.ConnectionError:
        logger.warning("Ollama not available, using fallback responses")
        return get_fallback_response(role)
    except requests.exceptions.Timeout:
        logger.warning("Ollama request timed out, using fallback")
        return get_fallback_response(role)
    except requests.exceptions.RequestException as e:
        logger.error(f"Ollama request error: {str(e)}")
        return get_fallback_response(role)
    except Exception as e:
        logger.error(f"Unexpected error generating AI response: {str(e)}")
        return get_fallback_response(role)

@app.get("/")
def read_root():
    return {"message": "AI Courtroom Simulator Backend is running"}

@app.get("/health")
def health_check():
    """Check if Ollama is available"""
    try:
        response = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        ollama_available = response.status_code == 200
    except:
        ollama_available = False
    
    return {
        "status": "healthy",
        "ollama_available": ollama_available,
        "model": OLLAMA_MODEL if ollama_available else "fallback_mode"
    }

@app.post("/start_session")
def start_session(request: StartSessionRequest):
    """Start a new court session"""
    session_id = str(uuid.uuid4())[:8]
    
    # Initialize transcript with opening statements
    transcript = [
        {
            "speaker": "Judge",
            "text": f"Court is now in session. I understand we have a case to discuss. {request.case_facts[:100]}..."
        },
        {
            "speaker": "Bailiff",
            "text": f"The {request.user_role} has entered the courtroom."
        }
    ]
    
    # Store session
    session_data = {
        "session_id": session_id,
        "case_facts": request.case_facts,
        "user_role": request.user_role,
        "transcript": transcript,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    sessions[session_id] = session_data
    if not save_session(session_id, session_data):
        logger.error(f"Failed to save session {session_id} to disk")
    
    return {
        "session_id": session_id,
        "transcript": transcript,
        "status": "Session started"
    }

@app.post("/simulate_step")
def simulate_step(request: SimulateStepRequest):
    """Process a step in the court simulation"""
    session_id = request.session_id
    user_input = request.user_input
    
    # Load session with caching
    if session_id in sessions:
        session = sessions[session_id]
    else:
        session = load_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        # Cache loaded session in memory
        sessions[session_id] = session
    
    # Check relevance before processing
    if not is_relevant_to_case(user_input, session["case_facts"]):
        # Add user input but mark as irrelevant
        session["transcript"].append({
            "speaker": session["user_role"].capitalize(),
            "text": user_input
        })
        
        # Add judge's response about relevance
        session["transcript"].append({
            "speaker": "Judge",
            "text": "Order in the court! Please keep your statements relevant to the case at hand."
        })
        
        # Save and return without AI processing
        sessions[session_id] = session
        if not save_session(session_id, session):
            logger.error(f"Failed to save updated session {session_id}")
        
        return {
            "session": session,
            "status": "Irrelevant input - redirected to case"
        }
    
    # Add user's input to transcript
    session["transcript"].append({
        "speaker": session["user_role"].capitalize(),
        "text": user_input
    })
    
    # Generate AI responses in parallel (much faster)
    judge_future = executor.submit(
        generate_ai_response,
        "judge",
        session["case_facts"],
        session["transcript"],
        user_input
    )
    
    opposing_future = executor.submit(
        generate_ai_response,
        "opposing_counsel",
        session["case_facts"],
        session["transcript"],
        user_input
    )
    
    # Wait for both to complete with proper error handling
    try:
        judge_response = judge_future.result(timeout=15)
    except (TimeoutError, Exception) as e:
        logger.warning(f"Judge response timeout/error: {e}")
        judge_response = get_fallback_response("judge")
    
    try:
        opposing_response = opposing_future.result(timeout=15)
    except (TimeoutError, Exception) as e:
        logger.warning(f"Opposing counsel response timeout/error: {e}")
        opposing_response = get_fallback_response("opposing_counsel")
    
    # Add AI responses to transcript
    session["transcript"].append({
        "speaker": "Judge",
        "text": judge_response
    })
    
    session["transcript"].append({
        "speaker": "Opposing Counsel",
        "text": opposing_response
    })
    
    # Save updated session
    sessions[session_id] = session
    if not save_session(session_id, session):
        logger.error(f"Failed to save updated session {session_id}")
    
    return {
        "session": session,
        "status": "Step completed"
    }

@app.get("/session/{session_id}")
def get_session(session_id: str):
    """Get current session data"""
    if session_id in sessions:
        session = sessions[session_id]
    else:
        session = load_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        # Cache loaded session in memory
        sessions[session_id] = session
    
    return session

@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    """Delete a session"""
    if not validate_session_id(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    
    if session_id in sessions:
        del sessions[session_id]
    
    session_file = SESSIONS_DIR / f"{session_id}.txt"
    if session_file.exists():
        try:
            session_file.unlink()
        except OSError as e:
            logger.error(f"Error deleting session file {session_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete session file")
    
    return {"status": "Session deleted"}

if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI server on http://127.0.0.1:8000")
    print("API docs available at http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="127.0.0.1", port=8000)