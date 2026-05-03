import streamlit as st
import requests
import pandas as pd
from groq import Groq
from supabase import create_client, Client

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Principal Programmer Command Center", page_icon="🎯", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #1a5f7a; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- USER PROFILE ---
USER_PROFILE = """
Name: Mahidhar Miriyala
Role: Principal Statistical Programmer / TA Lead Manager
Experience: 16+ years in Pharma/Biotech.
Expertise: SDTM, ADaM, TLFs, Regulatory Submissions (FDA/PMDA), BLA, ISS/ISE, CDISC, Pinnacle 21.
"""

# --- SIDEBAR: API KEYS ---
st.sidebar.title("⚙️ System Settings")
serper_key = st.sidebar.text_input("Serper.dev API Key", type="password")
groq_key = st.sidebar.text_input("Groq API Key", type="password")
supa_url = st.sidebar.text_input("Supabase URL", type="password")
supa_key = st.sidebar.text_input("Supabase API Key", type="password")

if not all([serper_key, groq_key, supa_url, supa_key]):
    st.warning("⚠️ Please enter all 4 API keys in the sidebar to activate the Command Center.")
    st.stop()

# Initialize Clients
client_groq = Groq(api_key=groq_key)
supabase: Client = create_client(supa_url, supa_key)

# --- CORE FUNCTIONS ---

def search_jobs(role, location):
    try:
        url = "https://google.serper.dev/search"
        query = f'("Principal" OR "Associate Director" OR "Manager") "{role}" "{location}" (site:greenhouse.io OR site:lever.co OR site:workday.com OR site:myworkdayjobs.com)'
        payload = {"q": query, "num": 50} # 50 Results
        headers = {'X-API-KEY': serper_key, 'Content-Type': 'application/json'}
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        return response.json().get('organic', []) if response.status_code == 200 else []
    except Exception as e:
        st.error(f"Search Error: {e}")
        return []

def analyze_job(job_text):
    try:
        prompt = f"Compare this Job Description with the Candidate Profile.\n\nPROFILE:\n{USER_PROFILE}\n\nJOB:\n{job_text}\n\nFormat: Score [0-100]%, Reason [2 sentences], Key Missing [List]."
        completion = client_groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"AI Analysis unavailable: {e}"

def save_to_tracker(title, link):
    """Saves the job to the Supabase database permanently"""
    try:
        data = {"title": title, "link": link, "status": "Applied", "date": pd.Timestamp.now().strftime("%Y-%m-%d")}
        supabase.table("jobs_tracker").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Database Error: {e}")
        return False

def get_tracker_data():
    """Fetches all tracked jobs from Supabase"""
    try:
        response = supabase.table("jobs_tracker").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# --- APP UI ---
st.title("🎯 Principal Programmer Command Center")
st.markdown("### High-Precision Discovery & Permanent Application Tracking")

tab1, tab2, tab3 = st.tabs(["📡 Discovery Radar", "🧠 AI Matcher", "📈 Application Tracker"])

with tab1:
    col1, col2 = st.columns(2)
    with col1: target_role = st.text_input("Target Role", value="Statistical Programming")
    with col2: target_loc = st.text_input("Target Location", value="Remote")

    if st.button("🚀 Scan for High-Value Roles"):
        with st.spinner("Scanning..."):
            results = search_jobs(target_role, target_loc)
            if results:
                job_data = [{"Title": r.get('title'), "Snippet": r.get('snippet'), "Link": r.get('link')} for r in results]
                st.session_state['jobs_df'] = pd.DataFrame(job_data)
                st.success(f"Found {len(results)} roles!")
                st.table(st.session_state['jobs_df'])
            else:
                st.error("No roles found.")

with tab2:
    if 'jobs_df' not in st.session_state:
        st.info("Run Discovery Radar first.")
    else:
        df = st.session_state['jobs_df']
        selected_idx = st.selectbox("Select a Job", range(len(df)), format_func=lambda x: f"{df.iloc[x]['Title']}")
        job = df.iloc[selected_idx]
        
        if st.button("🧠 Analyze Match %"):
            with st.spinner("AI Analyzing..."):
                analysis = analyze_job(job['Snippet'])
                st.markdown(f"### AI Analysis\n{analysis}")
                if st.button("✅ Mark as Applied"):
                    if save_to_tracker(job['Title'], job['Link']):
                        st.success("Job saved to your permanent tracker!")

with tab3:
    st.subheader("My Application CRM")
    tracker_df = get_tracker_data()
    
    if not tracker_df.empty:
        # Display the tracker as an editable table
        edited_df = st.data_editor(tracker_df, num_rows="dynamic")
        if st.button("💾 Save Status Changes"):
            # In a full version, we would update the Supabase rows here
            st.info("Status updates are saved to your session. (Full DB sync requires unique IDs).")
    else:
        st.info("No jobs tracked yet. Use the AI Matcher tab to add jobs!")

