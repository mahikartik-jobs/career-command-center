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

# --- RESTORED AGGRESSIVE SEARCH LOGIC ---
def search_jobs_cluster(role_input, loc_input):
    """The la-script 'Cluster' logic: Multiple searches for maximum volume"""
    
    # Define the clusters we want to hunt in
    # We use the user's input as the base, but add high-value seniority keywords
    SENIORITY = ["Principal", "Associate Director", "Manager", "Lead"]
    # We use the user's location, but also add the Pharma hubs
    HUBS = [loc_input, "Remote", "New Jersey", "Boston", "California", "North Carolina"]
    
    # The sites we trust for high-quality direct applications
    SITES = ['site:greenhouse.io', 'site:lever.co', 'site:myworkdayjobs.com', 'site:workday.com']
    
    all_results = {} # Use dictionary to prevent duplicate links
    
    # We will perform multiple searches to cast a huge net
    # To keep the app fast, we'll do 10-15 high-impact combinations
    search_combinations = []
    for s in SENIORITY:
        for h in HUBS:
            # Create a query for each combo
            # Example: site:greenhouse.io "Principal" "Statistical Programming" "Remote"
            for site in SITES:
                search_combinations.append(f'{site} "{s}" "{role_input}" "{h}"')

    # To prevent the app from timing out, we limit to the top 20 most effective combos
    # and ask for 100 results per query.
    selected_queries = search_combinations[:20] 
    
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': serper_key, 'Content-Type': 'application/json'}
    
    progress_bar = st.progress(0)
    
    for i, query in enumerate(selected_queries):
        try:
            # num: 100 is the maximum results Serper can return per request
            payload = {"q": query, "num": 100} 
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
            
            # Update progress bar
            progress_bar.progress((i + 1) / len(selected_queries))
            
        except Exception as e:
            continue # Keep moving even if one query fails

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
st.markdown("### 🚀 High-Volume Discovery & Permanent Tracking")

tab1, tab2, tab3 = st.tabs(["📡 Discovery Radar", "🧠 AI Matcher", "📈 Application Tracker"])

with tab1:
    col1, col2 = st.columns(2)
    with col1: target_role = st.text_input("Target Role", value="Statistical Programming")
    with col2: target_loc = st.text_input("Target Location", value="Remote")

    if st.button("🚀 Scan for High-Value Roles"):
        with st.spinner("Executing Aggressive Cluster Search..."):
            results = search_jobs_cluster(target_role, target_loc)
            if results:
                st.session_state['jobs_df'] = pd.DataFrame(results)
                st.success(f"Found {len(results)} unique roles across all clusters!")
                st.table(st.session_state['jobs_df'])
            else:
                st.error("No roles found. Try a slightly broader role name.")

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
