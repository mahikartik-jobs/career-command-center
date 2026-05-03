import streamlit as st
import requests
import pandas as pd
from groq import Groq
from supabase import create_client, Client
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Principal Programmer Command Center", page_icon="🎯", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #1a5f7a; color: white; }
    </style>
    """, unsafe_allow_html=True)

USER_PROFILE = """
Name: Mahidhar Miriyala
Role: Principal Statistical Programmer / TA Lead Manager
Experience: 16+ years in Pharma/Biotech.
Expertise: SDTM, ADaM, TLFs, Regulatory Submissions (FDA/PMDA), BLA, ISS/ISE, CDISC, Pinnacle 21.
"""

# --- SIDEBAR ---
st.sidebar.title("⚙️ System Settings")
serper_key = st.sidebar.text_input("Serper.dev API Key", type="password")
groq_key = st.sidebar.text_input("Groq API Key", type="password")
supa_url = st.sidebar.text_input("Supabase URL", type="password")
supa_key = st.sidebar.text_input("Supabase API Key", type="password")

if not all([serper_key, groq_key, supa_url, supa_key]):
    st.warning("⚠️ Please enter all 4 API keys in the sidebar to activate the Command Center.")
    st.stop()

client_groq = Groq(api_key=groq_key)
supabase: Client = create_client(supa_url, supa_key)

# --- FUZZY CLUSTER SEARCH LOGIC ---
def search_jobs_fuzzy(role_input, loc_input):
    """Human-like fuzzy search: removing strict quotes to find more variations"""
    
    # 1. Role Variations: We search for both 'Programming' and 'Programmer'
    role_variations = [role_input, role_input.replace("Programming", "Programmer")]
    
    # 2. Seniority keywords (No quotes = Fuzzy match)
    seniority = ["Principal", "Associate Director", "Manager", "Lead"]
    
    # 3. Expanded Hubs
    hubs = [loc_input, "Remote", "New Jersey", "Boston", "California", "USA"]
    
    # 4. Site-specific and General searches
    # We remove the 'site:' requirement from the main query to avoid missing roles
    # but we keep the keywords to ensure they are on career pages
    site_keywords = ["careers", "apply", "job", "greenhouse", "lever", "workday"]
    
    all_results = {}
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': serper_key, 'Content-Type': 'application/json'}
    
    progress_bar = st.progress(0)
    total_combos = len(role_variations) * len(seniority) * len(hubs)
    count = 0

    for r in role_variations:
        for s in seniority:
            for h in hubs:
                # BUILD A FUZZY QUERY
                # Example: Principal Statistical Programmer Remote careers
                # No quotes means Google will find "Principal Lead Statistical Programmer" too.
                query = f'{s} {r} {h} {" ".join(site_keywords[:2])}'
                
                try:
                    payload = {"q": query, "num": 50} 
                    response = requests.post(url, headers=headers, json=payload, timeout=15)
                    
                    if response.status_code == 200:
                        organic = response.json().get('organic', [])
                        for job in organic:
                            link = job.get('link')
                            if link:
                                all_results[link] = {
                                    "Title": job.get('title'),
                                    "Snippet": job.get('snippet'),
                                    "Link": link
                                }
                    
                    count += 1
                    progress_bar.progress(count / total_combos)
                    
                except Exception as e:
                    continue

    return list(all_results.values())

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
    try:
        data = {"title": title, "link": link, "status": "Applied", "date": pd.Timestamp.now().strftime("%Y-%m-%d")}
        supabase.table("jobs_tracker").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Database Error: {e}")
        return False

def get_tracker_data():
    try:
        response = supabase.table("jobs_tracker").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# --- APP UI ---
st.title("🎯 Principal Programmer Command Center")
st.markdown("### 🚀 Fuzzy-Discovery & Permanent Tracking")

tab1, tab2, tab3 = st.tabs(["📡 Discovery Radar", "🧠 AI Matcher", "📈 Application Tracker"])

with tab1:
    col1, col2 = st.columns(2)
    with col1: target_role = st.text_input("Target Role", value="Statistical Programmer")
    with col2: target_loc = st.text_input("Target Location", value="Remote")

    if st.button("🚀 Scan for High-Value Roles"):
        with st.spinner("Executing Fuzzy Cluster Search..."):
            results = search_jobs_fuzzy(target_role, target_loc)
            if results:
                st.session_state['jobs_df'] = pd.DataFrame(results)
                st.success(f"Found {len(results)} unique roles!")
                st.table(st.session_state['jobs_df'])
            else:
                st.error("No roles found. Try a simpler role name like 'Statistical Programmer'.")

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
        st.data_editor(tracker_df, num_rows="dynamic")
    else:
        st.info("No jobs tracked yet.")
