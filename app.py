import streamlit as st
import requests
import pandas as pd
from openai import OpenAI

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Principal Programmer Command Center", page_icon="🎯", layout="wide")

# --- CUSTOM CSS FOR PROFESSIONAL LOOK ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .match-high { color: green; font-weight: bold; }
    .match-med { color: orange; font-weight: bold; }
    .match-low { color: red; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- USER PROFILE (Embedded for the AI) ---
USER_PROFILE = """
Name: Mahidhar Miriyala
Role: Principal Statistical Programmer / TA Lead Manager
Experience: 16+ years in Pharmaceutical and Biotech industries.
Key Expertise: 
- End-to-end statistical programming (SDTM, ADaM, TLFs).
- Regulatory Submissions: FDA, PMDA, BLA, ISS/ISE packages.
- Standards: CDISC (SDTM, ADaM, CDASH), Pinnacle 21, Define.xml.
- Leadership: TA Lead (GCDS), Vendor/CRO Oversight, Team Mentoring.
- Therapeutic Areas: Oncology, Fibrosis, Cardiovascular, Neuroscience, etc.
- Tools: SAS (Base, Stat, Graph, Macro, SQL), R, Medidata Rave, Veeva Vault.
"""

# --- SIDEBAR: API KEYS ---
st.sidebar.title("⚙️ System Settings")
serper_key = st.sidebar.text_input("Serper.dev API Key", type="password")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password")

if not serper_key or not openai_key:
    st.warning("⚠️ Please enter both API keys in the sidebar to activate the Command Center.")
    st.stop()

client = OpenAI(api_key=openai_key)

# --- CORE FUNCTIONS ---

def search_jobs(role, location):
    """Professional search using Serper.dev API"""
    url = "https://google.serper.dev/search"
    # We use the "Dorking" strategy to find direct ATS links
    query = f'("Principal" OR "Associate Director" OR "Manager") "{role}" "{location}" (site:greenhouse.io OR site:lever.co OR site:workday.com OR site:myworkdayjobs.com)'
    
    payload = {"q": query}
    headers = {'X-API-KEY': serper_key, 'Content-Type': 'application/json'}
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json().get('organic', [])
    else:
        st.error(f"Search Error: {response.status_code}")
        return []

def analyze_job(job_text):
    """AI Matcher: Grades the job against Mahidhar's profile"""
    prompt = f"""
    You are an expert Executive Recruiter in the Pharma/Biotech industry.
    Compare the following Job Description with the Candidate Profile.
    
    CANDIDATE PROFILE:
    {USER_PROFILE}
    
    JOB DESCRIPTION:
    {job_text}
    
    Provide the following in a strict format:
    Score: [0-100]%
    Reason: [2 sentences why this is or isn't a match]
    Key Missing: [List any missing skills or 'None']
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "You are a precise clinical trial recruitment expert."},
                  {"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def generate_pitch(job_title, company):
    """AI Pitch Generator: Creates a high-impact intro message"""
    prompt = f"""
    Write a professional, high-impact 3-sentence LinkedIn message to a recruiter for the role of {job_title} at {company}.
    The candidate is Mahidhar, a Principal Statistical Programmer with 16+ years of experience, expert in CDISC, BLA, and FDA submissions.
    The tone should be confident, executive, and concise.
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "You are a professional career coach."},
                  {"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# --- APP UI ---
st.title("🎯 Principal Programmer Command Center")
st.markdown("### High-Precision Job Discovery & AI Matching")

tab1, tab2 = st.tabs(["📡 Discovery Radar", "🧠 AI Matcher & Pitch"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        target_role = st.text_input("Target Role", value="Statistical Programming")
    with col2:
        target_loc = st.text_input("Target Location/Hub", value="Remote")

    if st.button("🚀 Scan for High-Value Roles"):
        with st.spinner("Searching professional databases..."):
            results = search_jobs(target_role, target_loc)
            if results:
                job_data = []
                for res in results:
                    job_data.append({
                        "Title": res.get('title'),
                        "Snippet": res.get('snippet'),
                        "Link": res.get('link')
                    })
                df = pd.DataFrame(job_data)
                st.session_state['jobs_df'] = df
                st.success(f"Found {len(results)} potential roles!")
                st.table(df)
            else:
                st.error("No roles found. Try broadening the location or role.")

with tab2:
    if 'jobs_df' not in st.session_state:
        st.info("Please run the Discovery Radar first to find jobs.")
    else:
        df = st.session_state['jobs_df']
        selected_job_index = st.selectbox("Select a Job to Analyze", range(len(df)), 
                                         format_func=lambda x: f"{df.iloc[x]['Title']}")
        
        job_link = df.iloc[selected_job_index]['Link']
        job_snippet = df.iloc[selected_job_index]['Snippet']
        job_title = df.iloc[selected_job_index]['Title']
        
        if st.button("🧠 Analyze Match %"):
            with st.spinner("AI is analyzing your CV against this role..."):
                analysis = analyze_job(job_snippet)
                st.markdown(f"### AI Analysis\n{analysis}")
                
                if "Score: 8" in analysis or "Score: 9" in analysis or "Score: 10" in analysis:
                    st.success("🔥 HIGH MATCH: You should apply to this immediately!")
                    if st.button("✍️ Generate Executive Pitch"):
                        pitch = generate_pitch(job_title, "the company")
                        st.markdown(f"**Suggested Message:**\n\n{pitch}")
                else:
                    st.warning("Moderate or Low Match. Proceed with caution.")
