import streamlit as st
import requests
import pandas as pd
from groq import Groq # Switching to the FREE, faster AI engine

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Principal Programmer Command Center", page_icon="🎯", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #2e7d32; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- USER PROFILE (Embedded) ---
USER_PROFILE = """
Name: Mahidhar Miriyala
Role: Principal Statistical Programmer / TA Lead Manager
Experience: 16+ years in Pharma/Biotech.
Expertise: SDTM, ADaM, TLFs, Regulatory Submissions (FDA/PMDA), BLA, ISS/ISE, CDISC, Pinnacle 21.
"""

# --- SIDEBAR: API KEYS ---
st.sidebar.title("⚙️ System Settings")
serper_key = st.sidebar.text_input("Serper.dev API Key (Free)", type="password")
groq_key = st.sidebar.text_input("Groq API Key (Free)", type="password")

if not serper_key or not groq_key:
    st.warning("⚠️ Please enter both FREE API keys in the sidebar to activate the Command Center.")
    st.stop()

# Initialize Groq Client
client = Groq(api_key=groq_key)

# --- CORE FUNCTIONS ---

def search_jobs(role, location):
    """Robust search using Serper.dev"""
    try:
        url = "https://google.serper.dev/search"
        query = f'("Principal" OR "Associate Director" OR "Manager") "{role}" "{location}" (site:greenhouse.io OR site:lever.co OR site:workday.com)'
        payload = {"q": query}
        headers = {'X-API-KEY': serper_key, 'Content-Type': 'application/json'}
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json().get('organic', [])
        return []
    except Exception as e:
        st.error(f"Search Engine Error: {e}")
        return []

def analyze_job(job_text):
    """Free AI Matcher using Llama 3 via Groq"""
    try:
        prompt = f"Compare this Job Description with the Candidate Profile.\n\nPROFILE:\n{USER_PROFILE}\n\nJOB:\n{job_text}\n\nFormat: Score [0-100]%, Reason [2 sentences], Key Missing [List]."
        
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant", # Using the high-speed free model
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"AI Analysis unavailable: {e}"

def generate_pitch(job_title, company):
    """Free Pitch Generator using Llama 3"""
    try:
        prompt = f"Write a 3-sentence professional LinkedIn message for {job_title} at {company} for Mahidhar (16+ years exp, Principal Programmer, CDISC expert)."
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Could not generate pitch: {e}"

# --- APP UI ---
st.title("🎯 Principal Programmer Command Center")
st.markdown("### 🚀 Robust, Free, and AI-Powered Job Discovery")

# Use session state to keep jobs after refresh
if 'jobs_df' not in st.session_state:
    st.session_state['jobs_df'] = None

tab1, tab2 = st.tabs(["📡 Discovery Radar", "🧠 AI Matcher & Pitch"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        target_role = st.text_input("Target Role", value="Statistical Programming")
    with col2:
        target_loc = st.text_input("Target Location/Hub", value="Remote")

    if st.button("🚀 Scan for High-Value Roles"):
        with st.spinner("Scanning professional databases..."):
            results = search_jobs(target_role, target_loc)
            if results:
                job_data = [{"Title": r.get('title'), "Snippet": r.get('snippet'), "Link": r.get('link')} for r in results]
                st.session_state['jobs_df'] = pd.DataFrame(job_data)
                st.success(f"Found {len(results)} roles!")
                st.table(st.session_state['jobs_df'])
            else:
                st.error("No roles found. Try changing the role or location.")

with tab2:
    if st.session_state['jobs_df'] is None:
        st.info("Please run the Discovery Radar first.")
    else:
        df = st.session_state['jobs_df']
        selected_job_index = st.selectbox("Select a Job to Analyze", range(len(df)), 
                                         format_func=lambda x: f"{df.iloc[x]['Title']}")
        
        job_link = df.iloc[selected_job_index]['Link']
        job_snippet = df.iloc[selected_job_index]['Snippet']
        job_title = df.iloc[selected_job_index]['Title']
        
        if st.button("🧠 Analyze Match %"):
            with st.spinner("Analyzing..."):
                analysis = analyze_job(job_snippet)
                st.markdown(f"### AI Analysis\n{analysis}")
                
                if "Score: 8" in analysis or "Score: 9" in analysis or "Score: 10" in analysis:
                    st.success("🔥 HIGH MATCH!")
                    if st.button("✍️ Generate Executive Pitch"):
                        st.markdown(f"**Suggested Message:**\n\n{generate_pitch(job_title, 'the company')}")
