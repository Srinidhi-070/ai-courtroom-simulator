import streamlit as st
import requests
import json
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Enhanced Configuration
API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="AI Courtroom Simulator - Professional Edition",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional look
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .case-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #007bff;
        margin: 1rem 0;
    }
    .evidence-item {
        background: #fff3cd;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.5rem 0;
        border-left: 3px solid #ffc107;
    }
    .transcript-entry {
        margin: 0.5rem 0;
        padding: 0.5rem;
        border-radius: 5px;
    }
    .judge-entry { background: #e7f3ff; border-left: 3px solid #0066cc; }
    .defense-entry { background: #f0f8e7; border-left: 3px solid #28a745; }
    .prosecution-entry { background: #ffe7e7; border-left: 3px solid #dc3545; }
    .system-entry { background: #f8f9fa; border-left: 3px solid #6c757d; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    defaults = {
        'authenticated': False,
        'user_token': None,
        'user_data': None,
        'session_id': None,
        'transcript': [],
        'evidence_list': [],
        'case_data': {},
        'analytics_data': {},
        'current_page': 'login'
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# Authentication functions
def authenticate_user(username, password, action="login"):
    """Authenticate user with backend"""
    try:
        endpoint = f"{API_URL}/auth/{action}"
        response = requests.post(endpoint, json={
            "username": username,
            "password": password,
            "role": "student" if action == "register" else "student"
        }, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if action == "login":
                st.session_state.authenticated = True
                st.session_state.user_token = data["access_token"]
                st.session_state.user_data = data["user"]
            return True, data.get("message", "Success")
        else:
            return False, response.json().get("detail", "Authentication failed")
    except Exception as e:
        return False, f"Connection error: {str(e)}"

def get_auth_headers():
    """Get authentication headers for API requests"""
    if st.session_state.user_token:
        return {"Authorization": f"Bearer {st.session_state.user_token}"}
    return {}

# Enhanced UI Components
def render_header():
    """Render professional header"""
    st.markdown("""
    <div class="main-header">
        <h1>⚖️ AI Courtroom Simulator - Professional Edition</h1>
        <p>Advanced Legal Simulation with AI Judges, Evidence Management & Analytics</p>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar():
    """Render enhanced sidebar with navigation"""
    with st.sidebar:
        st.image("https://via.placeholder.com/200x100/1e3c72/ffffff?text=COURTROOM", width=200)
        
        if st.session_state.authenticated:
            st.success(f"👤 Welcome, {st.session_state.user_data['username']}")
            st.info(f"🎭 Role: {st.session_state.user_data['role'].title()}")
            
            # Navigation
            st.markdown("### 📋 Navigation")
            pages = {
                "🏛️ Courtroom": "courtroom",
                "📊 Analytics": "analytics", 
                "📁 Case History": "history",
                "⚙️ Settings": "settings"
            }
            
            for label, page in pages.items():
                if st.button(label, key=f"nav_{page}"):
                    st.session_state.current_page = page
                    st.rerun()
            
            st.markdown("---")
            if st.button("🚪 Logout"):
                for key in ['authenticated', 'user_token', 'user_data', 'session_id']:
                    st.session_state[key] = None if key != 'authenticated' else False
                st.session_state.current_page = 'login'
                st.rerun()
        else:
            st.warning("Please login to access the courtroom")

def render_login_page():
    """Render login/register page"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Authentication")
        
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                
                if st.form_submit_button("🚀 Login", use_container_width=True):
                    if username and password:
                        success, message = authenticate_user(username, password, "login")
                        if success:
                            st.success("Login successful!")
                            st.session_state.current_page = 'courtroom'
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.warning("Please enter both username and password")
        
        with tab2:
            with st.form("register_form"):
                new_username = st.text_input("Choose Username")
                new_password = st.text_input("Choose Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                
                if st.form_submit_button("📝 Register", use_container_width=True):
                    if new_username and new_password and confirm_password:
                        if new_password == confirm_password:
                            success, message = authenticate_user(new_username, new_password, "register")
                            if success:
                                st.success("Registration successful! Please login.")
                            else:
                                st.error(message)
                        else:
                            st.error("Passwords don't match")
                    else:
                        st.warning("Please fill all fields")

def render_case_setup():
    """Render enhanced case setup form"""
    st.markdown("### 📋 Case Setup")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        case_title = st.text_input("📝 Case Title", placeholder="e.g., State vs. John Doe - Theft Case")
        case_facts = st.text_area("📄 Case Facts & Background", height=150, 
                                 placeholder="Describe the case details, evidence, and circumstances...")
    
    with col2:
        st.markdown("#### ⚖️ Case Configuration")
        case_type = st.selectbox("Case Type", ["criminal", "civil", "family", "corporate", "constitutional"])
        severity = st.selectbox("Severity", ["minor", "major", "felony"])
        jurisdiction = st.selectbox("Court Level", ["district", "high", "supreme"])
        user_role = st.selectbox("Your Role", ["defense", "prosecution", "judge", "witness"])
    
    participants = st.text_input("👥 Additional Participants (comma-separated)", 
                                placeholder="witness1, expert2, etc.")
    
    if st.button("🚀 Start Court Session", type="primary", use_container_width=True):
        if case_title and case_facts:
            try:
                response = requests.post(
                    f"{API_URL}/sessions/start",
                    json={
                        "case_title": case_title,
                        "case_facts": case_facts,
                        "user_role": user_role,
                        "case_type": {
                            "type": case_type,
                            "severity": severity,
                            "jurisdiction": jurisdiction
                        },
                        "participants": [p.strip() for p in participants.split(",") if p.strip()]
                    },
                    headers=get_auth_headers(),
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.session_id = data["session_id"]
                    st.session_state.transcript = data["transcript"]
                    st.session_state.case_data = {
                        "title": case_title,
                        "facts": case_facts,
                        "type": case_type,
                        "role": user_role
                    }
                    st.success("🎉 Court session started successfully!")
                    st.rerun()
                else:
                    st.error(f"Failed to start session: {response.status_code}")
            except Exception as e:
                st.error(f"Connection error: {str(e)}")
        else:
            st.warning("Please fill in case title and facts")

def render_active_session():
    """Render active courtroom session"""
    if not st.session_state.session_id:
        render_case_setup()
        return
    
    # Session header
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"### 🏛️ {st.session_state.case_data.get('title', 'Active Session')}")
    with col2:
        st.metric("Session ID", st.session_state.session_id)
    with col3:
        if st.button("🔄 New Case"):
            st.session_state.session_id = None
            st.session_state.transcript = []
            st.rerun()
    
    # Main courtroom interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Transcript display
        st.markdown("#### 📜 Court Transcript")
        transcript_container = st.container()
        
        with transcript_container:
            for entry in st.session_state.transcript:
                speaker = entry.get('speaker', 'Unknown')
                text = entry.get('text', '')
                action_type = entry.get('action_type', 'argument')
                
                # Style based on speaker
                if 'judge' in speaker.lower():
                    css_class = "judge-entry"
                elif 'defense' in speaker.lower():
                    css_class = "defense-entry"
                elif 'prosecution' in speaker.lower():
                    css_class = "prosecution-entry"
                else:
                    css_class = "system-entry"
                
                st.markdown(f"""
                <div class="transcript-entry {css_class}">
                    <strong>{speaker}:</strong> {text}
                    <small style="color: #666; float: right;">{action_type}</small>
                </div>
                """, unsafe_allow_html=True)
        
        # Input section
        st.markdown("#### 💬 Your Move")
        
        input_col1, input_col2 = st.columns([3, 1])
        with input_col1:
            user_input = st.text_area("Enter your argument, objection, or statement:", height=100)
        with input_col2:
            action_type = st.selectbox("Action Type", ["argument", "objection", "evidence", "motion", "ruling"])
            
        if st.button("⚡ Submit", type="primary", use_container_width=True):
            if user_input.strip():
                # Process the input (simplified for demo)
                st.session_state.transcript.append({
                    "speaker": st.session_state.case_data.get('role', 'User').title(),
                    "text": user_input,
                    "action_type": action_type,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Add AI responses (simplified)
                st.session_state.transcript.append({
                    "speaker": "Judge",
                    "text": "Thank you for that argument. I will consider it carefully.",
                    "action_type": "response",
                    "timestamp": datetime.now().isoformat()
                })
                
                st.rerun()
            else:
                st.warning("Please enter your statement")
    
    with col2:
        # Case information panel
        st.markdown("#### 📋 Case Information")
        st.markdown(f"""
        <div class="case-card">
            <strong>Type:</strong> {st.session_state.case_data.get('type', 'N/A').title()}<br>
            <strong>Your Role:</strong> {st.session_state.case_data.get('role', 'N/A').title()}<br>
            <strong>Status:</strong> Active<br>
            <strong>Entries:</strong> {len(st.session_state.transcript)}
        </div>
        """, unsafe_allow_html=True)
        
        # Evidence section
        st.markdown("#### 📁 Evidence")
        if st.button("➕ Add Evidence"):
            st.info("Evidence management feature - Coming soon!")
        
        # Quick actions
        st.markdown("#### ⚡ Quick Actions")
        if st.button("🚫 Object"):
            st.session_state.transcript.append({
                "speaker": st.session_state.case_data.get('role', 'User').title(),
                "text": "Objection, Your Honor!",
                "action_type": "objection",
                "timestamp": datetime.now().isoformat()
            })
            st.rerun()
        
        if st.button("📋 Motion"):
            st.info("Motion filing feature - Coming soon!")

def render_analytics_page():
    """Render analytics dashboard"""
    st.markdown("### 📊 Analytics Dashboard")
    
    # Sample analytics data
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Cases", "47", "+5")
    with col2:
        st.metric("Win Rate", "73%", "+2%")
    with col3:
        st.metric("Avg Session Time", "24 min", "-3 min")
    with col4:
        st.metric("Evidence Submitted", "156", "+12")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Case types distribution
        case_data = pd.DataFrame({
            'Case Type': ['Criminal', 'Civil', 'Family', 'Corporate'],
            'Count': [25, 12, 7, 3]
        })
        fig = px.pie(case_data, values='Count', names='Case Type', title="Case Types Distribution")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Performance over time
        performance_data = pd.DataFrame({
            'Date': pd.date_range('2024-01-01', periods=30, freq='D'),
            'Cases Won': [2, 1, 3, 2, 1, 4, 2, 3, 1, 2, 3, 4, 2, 1, 3, 2, 4, 1, 3, 2, 1, 3, 2, 4, 1, 2, 3, 1, 2, 3]
        })
        fig = px.line(performance_data, x='Date', y='Cases Won', title="Performance Trend")
        st.plotly_chart(fig, use_container_width=True)

def render_history_page():
    """Render case history page"""
    st.markdown("### 📁 Case History")
    
    # Sample case history
    cases = [
        {"id": "a1b2c3d4", "title": "State vs. Smith - Theft", "date": "2024-12-07", "status": "Won", "type": "Criminal"},
        {"id": "e5f6g7h8", "title": "Johnson vs. Corp Inc", "date": "2024-12-06", "status": "Lost", "type": "Civil"},
        {"id": "i9j0k1l2", "title": "Family Matter - Custody", "date": "2024-12-05", "status": "Settled", "type": "Family"},
    ]
    
    for case in cases:
        with st.expander(f"📋 {case['title']} - {case['date']}"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Type:** {case['type']}")
            with col2:
                st.write(f"**Status:** {case['status']}")
            with col3:
                if st.button(f"View Details", key=f"view_{case['id']}"):
                    st.info("Case details feature - Coming soon!")

def render_settings_page():
    """Render settings page"""
    st.markdown("### ⚙️ Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🎨 Appearance")
        theme = st.selectbox("Theme", ["Professional", "Dark", "Light"])
        language = st.selectbox("Language", ["English", "Hindi", "Tamil"])
        
        st.markdown("#### 🔔 Notifications")
        email_notifications = st.checkbox("Email Notifications", value=True)
        case_reminders = st.checkbox("Case Reminders", value=True)
    
    with col2:
        st.markdown("#### 🤖 AI Settings")
        ai_model = st.selectbox("AI Model", ["Mistral", "Llama2", "GPT-4"])
        response_length = st.slider("Response Length", 50, 500, 200)
        
        st.markdown("#### 🔒 Privacy")
        data_retention = st.selectbox("Data Retention", ["30 days", "90 days", "1 year"])
        anonymous_mode = st.checkbox("Anonymous Mode")
    
    if st.button("💾 Save Settings", type="primary"):
        st.success("Settings saved successfully!")

# Main application logic
def main():
    render_header()
    render_sidebar()
    
    if not st.session_state.authenticated:
        render_login_page()
    else:
        page = st.session_state.current_page
        
        if page == 'courtroom':
            render_active_session()
        elif page == 'analytics':
            render_analytics_page()
        elif page == 'history':
            render_history_page()
        elif page == 'settings':
            render_settings_page()
        else:
            render_active_session()

if __name__ == "__main__":
    main()