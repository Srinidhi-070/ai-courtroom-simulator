from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import uuid
import os
import json
import requests
from pathlib import Path
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Courtroom Simulator - Simple Edition")

# Ollama Configuration
OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = "11434"
OLLAMA_BASE = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"
OLLAMA_API_URL = f"{OLLAMA_BASE}/api/generate"
OLLAMA_MODEL = "mistral"

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple Data Models
class StartSessionRequest(BaseModel):
    case_title: str
    case_facts: str
    user_role: str

class SimulateStepRequest(BaseModel):
    session_id: str
    user_input: str

# In-memory session storage
sessions = {}

# Sessions directory
SESSIONS_DIR = Path("sessions")
SESSIONS_DIR.mkdir(exist_ok=True)

def is_relevant_to_case(user_input: str, case_facts: str) -> bool:
    """Check if user input is relevant to the legal case"""
    irrelevant_keywords = [
        'black hole', 'space', 'astronomy', 'physics', 'weather', 'food', 'sports',
        'movie', 'music', 'game', 'celebrity', 'programming', 'recipe', 'travel'
    ]
    
    legal_keywords = [
        'evidence', 'witness', 'testimony', 'guilty', 'innocent', 'verdict', 'objection',
        'law', 'legal', 'court', 'case', 'crime', 'defendant', 'plaintiff', 'judge'
    ]
    
    user_lower = user_input.lower()
    case_lower = case_facts.lower()
    
    # Check for irrelevant keywords
    for keyword in irrelevant_keywords:
        if keyword in user_lower and keyword not in case_lower:
            return False
    
    if len(user_input.strip()) < 8:
        return True
    
    # Check for legal keywords or case-related terms
    has_legal_content = any(keyword in user_lower for keyword in legal_keywords)
    has_case_content = any(word in user_lower for word in case_lower.split() if len(word) > 3)
    
    return has_legal_content or has_case_content

def get_irrelevance_response(role: str) -> str:
    """Response when user asks irrelevant questions"""
    if role == "judge":
        return "Order in the court! Please keep your statements relevant to the case at hand."
    else:
        return "Your Honor, I object. That question is irrelevant to the case we're discussing."

def generate_ai_response(role: str, case_facts: str, transcript: list, user_input: str) -> str:
    """Generate AI response using Ollama or fallback"""
    
    # Check relevance first
    if not is_relevant_to_case(user_input, case_facts):
        return get_irrelevance_response(role)
    
    try:
        # Build context
        recent_transcript = "\n".join([f"{entry['speaker']}: {entry['text']}" for entry in transcript[-3:]])
        
        # Create prompt
        if role == "judge":
            prompt = f"""As a judge, respond briefly (1-2 sentences):
Case: {case_facts[:150]}
Recent: {recent_transcript[-200:]}
User: {user_input[:100]}
Judicial response:"""
        else:
            prompt = f"""As opposing counsel, respond briefly (1-2 sentences):
Case: {case_facts[:150]}
Recent: {recent_transcript[-200:]}
User: {user_input[:100]}
Legal response:"""
        
        # Try Ollama API
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.7,
                "num_predict": 60
            },
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_text = result.get("response", "").strip()
            return ai_text[:300] if ai_text else "Please continue with your argument."
        else:
            return get_fallback_response(role)
            
    except Exception as e:
        logger.warning(f"AI generation failed: {e}")
        return get_fallback_response(role)

def get_fallback_response(role: str) -> str:
    """Fallback responses when AI is not available"""
    import random
    
    if role == "judge":
        responses = [
            "I see. Let me review the evidence presented.",
            "That is noted. Please continue with your case.",
            "Interesting argument. I will consider the legal precedents.",
            "The court acknowledges your statement."
        ]
    else:
        responses = [
            "Your Honor, I must point out that the evidence is insufficient.",
            "I disagree with that characterization.",
            "Your Honor, my client maintains their innocence.",
            "The prosecution has failed to establish their case."
        ]
    
    return random.choice(responses)

@app.get("/")
def read_root():
    return {"message": "AI Courtroom Simulator - Simple Edition", "status": "running"}

@app.get("/health")
def health_check():
    """Check system health"""
    try:
        ollama_response = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=3)
        ollama_available = ollama_response.status_code == 200
    except:
        ollama_available = False
    
    return {
        "status": "healthy",
        "ollama_available": ollama_available,
        "active_sessions": len(sessions)
    }

@app.post("/start_session")
def start_session(request: StartSessionRequest):
    """Start a new court session"""
    session_id = str(uuid.uuid4())[:8]
    
    # Initialize transcript
    transcript = [
        {
            "speaker": "Judge",
            "text": f"Court is now in session for {request.case_title}. {request.case_facts[:100]}...",
            "timestamp": datetime.now().isoformat()
        },
        {
            "speaker": "Bailiff",
            "text": f"The {request.user_role} has entered the courtroom.",
            "timestamp": datetime.now().isoformat()
        }
    ]
    
    # Store session
    session_data = {
        "session_id": session_id,
        "case_title": request.case_title,
        "case_facts": request.case_facts,
        "user_role": request.user_role,
        "transcript": transcript,
        "created_at": datetime.now().isoformat()
    }
    
    sessions[session_id] = session_data
    
    # Save to file
    try:
        with open(SESSIONS_DIR / f"{session_id}.json", 'w') as f:
            json.dump(session_data, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save session: {e}")
    
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
    
    # Get session
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    # Add user input
    session["transcript"].append({
        "speaker": session["user_role"].title(),
        "text": user_input,
        "timestamp": datetime.now().isoformat()
    })
    
    # Generate AI responses
    judge_response = generate_ai_response("judge", session["case_facts"], session["transcript"], user_input)
    counsel_response = generate_ai_response("opposing_counsel", session["case_facts"], session["transcript"], user_input)
    
    # Add AI responses
    session["transcript"].append({
        "speaker": "Judge",
        "text": judge_response,
        "timestamp": datetime.now().isoformat()
    })
    
    session["transcript"].append({
        "speaker": "Opposing Counsel",
        "text": counsel_response,
        "timestamp": datetime.now().isoformat()
    })
    
    # Update session
    sessions[session_id] = session
    
    return {
        "transcript": session["transcript"],
        "status": "Step completed"
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting AI Courtroom Simulator - Simple Edition")
    print("📍 Backend: http://127.0.0.1:8000")
    print("📍 Health: http://127.0.0.1:8000/health")
    uvicorn.run(app, host="127.0.0.1", port=8000)