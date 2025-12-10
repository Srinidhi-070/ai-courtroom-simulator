import streamlit as st
import requests
import json
from datetime import datetime

# Simple Configuration
API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="AI Courtroom Simulator",
    page_icon="⚖️",
    layout="centered"
)

st.title("⚖️ AI Courtroom Simulator")
st.write("Professional Legal Education Platform")

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "transcript" not in st.session_state:
    st.session_state.transcript = []

# Check backend connection
def check_backend():
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

# Simple case setup
st.subheader("🏛️ Start a New Case")

if not check_backend():
    st.error("❌ Backend server not running! Please start the backend first.")
    st.info("Run: python server_simple.py")
    st.stop()

case_title = st.text_input("📝 Case Title", placeholder="e.g., State vs. John Doe - Theft Case")
case_facts = st.text_area("📄 Case Facts", height=150, 
                         placeholder="Describe the case details, evidence, and circumstances...")
user_role = st.selectbox("Your Role", ["defense", "prosecution", "judge"])

if st.button("🚀 Start Court Session", type="primary"):
    if case_title and case_facts:
        try:
            response = requests.post(
                f"{API_URL}/start_session",
                json={
                    "case_title": case_title,
                    "case_facts": case_facts,
                    "user_role": user_role
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                st.session_state.session_id = data["session_id"]
                st.session_state.transcript = data["transcript"]
                st.success("🎉 Court session started!")
                st.rerun()
            else:
                st.error(f"Error: {response.status_code}")
        except Exception as e:
            st.error(f"Connection error: {str(e)}")
    else:
        st.warning("Please fill in case title and facts")

# Show active session
if st.session_state.session_id:
    st.subheader("📜 Court Transcript")
    
    # Display transcript
    for entry in st.session_state.transcript:
        speaker = entry.get('speaker', 'Unknown')
        text = entry.get('text', '')
        
        if 'judge' in speaker.lower():
            st.info(f"**{speaker}:** {text}")
        elif 'defense' in speaker.lower():
            st.success(f"**{speaker}:** {text}")
        elif 'prosecution' in speaker.lower():
            st.error(f"**{speaker}:** {text}")
        else:
            st.write(f"**{speaker}:** {text}")
    
    st.markdown("---")
    
    # User input
    user_input = st.text_area("💬 Your Argument:", height=100)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("⚡ Submit Argument", type="primary"):
            if user_input.strip():
                try:
                    response = requests.post(
                        f"{API_URL}/simulate_step",
                        json={
                            "session_id": st.session_state.session_id,
                            "user_input": user_input
                        },
                        timeout=15
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.transcript = data["transcript"]
                        st.rerun()
                    else:
                        st.error("Error processing argument")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            else:
                st.warning("Please enter your argument")
    
    with col2:
        if st.button("🔄 New Case"):
            st.session_state.session_id = None
            st.session_state.transcript = []
            st.rerun()

st.markdown("---")
st.write("🎓 AI Courtroom Simulator - Educational Tool")