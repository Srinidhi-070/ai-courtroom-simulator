import streamlit as st
import requests

# --------------------------
# CONFIG
# --------------------------

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="AI Courtroom Simulator",
    page_icon="⚖️",
    layout="centered"
)

st.title("⚖️ AI Courtroom Simulation")
st.write("Interact with a simulated judge and opposing counsel using Generative AI.")

# --------------------------
# SESSION MANAGEMENT
# --------------------------

if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "transcript" not in st.session_state:
    st.session_state.transcript = []

# --------------------------
# START SESSION
# --------------------------

st.subheader("Start a New Case")

case_facts = st.text_area("Enter the case details:", height=150)
user_role = st.selectbox("Choose your role:", ["defense", "prosecution", "judge"])

if st.button("Start Court Session"):
    if not case_facts.strip():
        st.error("Please enter case facts before starting.")
    else:
        try:
            with requests.post(
                f"{API_URL}/start_session",
                json={"case_facts": case_facts, "user_role": user_role},
                timeout=10
            ) as response:
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.session_id = data["session_id"]
                    st.session_state.transcript = data["transcript"]
                    st.success("Court session started!")
                else:
                    st.error(f"Error starting session: {response.status_code}")
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to backend server. Make sure the backend is running on http://127.0.0.1:8000")
        except requests.exceptions.Timeout:
            st.error("⏱️ Backend server took too long to respond")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# --------------------------
# SHOW TRANSCRIPT IF SESSION ACTIVE
# --------------------------

if st.session_state.session_id:
    st.subheader("📜 Court Transcript")

    for entry in st.session_state.transcript:
        st.markdown(f"**{entry['speaker']}:** {entry['text']}")

    st.markdown("---")
    st.subheader("Your Move")

    user_input = st.text_input("Enter your argument/question:")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Next Step"):
            if not user_input.strip():
                st.warning("Please enter an argument or question.")
            else:
                try:
                    payload = {
                        "session_id": st.session_state.session_id,
                        "user_input": user_input
                    }
                    with requests.post(f"{API_URL}/simulate_step", json=payload, timeout=10) as response:
                        if response.status_code == 200:
                            data = response.json()
                            st.session_state.transcript = data["session"]["transcript"]
                            st.rerun()
                        else:
                            st.error("Error processing your step.")
                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to backend server")
                except requests.exceptions.Timeout:
                    st.error("⏱️ Server took too long to respond")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

    with col2:
        if st.button("Refresh Transcript"):
            try:
                with requests.get(f"{API_URL}/session/{st.session_state.session_id}", timeout=10) as r:
                    if r.status_code == 200:
                        st.session_state.transcript = r.json()["transcript"]
                        st.rerun()
                    else:
                        st.error("Could not refresh session.")
            except requests.exceptions.ConnectionError:
                st.error("❌ Cannot connect to backend server")
            except requests.exceptions.Timeout:
                st.error("⏱️ Server took too long to respond")
            except Exception as e:
                st.error(f"Error refreshing: {str(e)}")

# --------------------------
# END UI
# --------------------------
st.markdown("---")
st.write("Created for your Gen AI Project — AI Courtroom Simulation ⚖️")