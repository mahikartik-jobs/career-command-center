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
    .cover-letter-box { background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #ddd; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }
    </style>
    """, unsafe_allow_html=True)

# --- HUMAN-CENTRIC USER PROFILE ---
# I have changed this from a list to a narrative. This helps the AI sound more human.
USER_PROFILE = """
Mahidhar Miriyala is a seasoned Principal Statistical Programmer and TA Lead Manager with over 16 years of deep-trench experience in the Pharma and Biotech sectors. 
He doesn't just know the standards; he has lived them through multiple high-stakes FDA and PMDA regulatory submissions. 
His core strength is the end-to-end delivery of BLA and NDA packages, specifically the complex work involved in ISS and ISE. 
He is a subject matter expert in CDISC (SDTM, ADaM) and Pinnacle 21, with a proven track record of leading cross-functional teams and managing CRO vendors to ensure submission-readiness.
Expertise spans Oncology, Fibrosis, Cardiovascular, and Neuroscience.
"""

# --- SECRET MANAGEMENT ---
serper_key = st.secrets.get("SERPER_API_KEY", None)
groq_key = st.secrets.get("GROQ_API_KEY", None)
supa_url = st.secrets.get("SUPABASE_URL", None)
supa_key = st.secrets.get("SUPABASE_KEY", None)

if not all([serper_key, groq_key, supa_url, supa_key]):
    st.sidebar.title("⚙️ Manual Key Entry")
    serper_key = st.sidebar.text_input("Serper.dev API Key", type="password", value=serper_key)
    groq_key = st.sidebar.text_input("Groq API Key", type="password", value=groq_key)
    supa_url = st.sidebar.text_input("Supabase URL", type="password", value=supa_url)
    supa_key = st.sidebar.text_input("Supabase API Key", type="password", value=supa_key)

    if not all([serper_key, groq_key, supa_url, supa_key]):
        st.warning("⚠️ Please enter all API keys in the sidebar to activate.")
        st.stop()

client_groq = Groq(api_key=groq_key)
supabase: Client = create_client(supa_url, supa_key)

# --- CORE LOGIC ---

def search_jobs_fuzzy(role_input, loc_input):
    role_variations = [role_input, role_input.replace("Programming", "Programmer")]
    seniority = ["Principal", "Associate Director", "Manager", "Lead"]
    hubs = [loc_input, "Remote", "New Jersey", "Boston", "California", "USA"]
    site_keywords = ["careers", "apply", "job"]
    
    all_results = {}
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': serper_key, 'Content-Type': 'application/json'}
    
    progress_bar = st.progress(0)
    total_combos = len(role_variations) * len(seniority) * len(hubs)
    count = 0

    for r in role_variations:
        for s in seniority:
            for h in hubs:
                query = f'{s} {r} {h} {" ".join(site_keywords)}'
                try:
                    payload = {"q": query, "num": 50} 
                    response = requests.post(url, headers=headers, json=payload, timeout=15)
                    if response.status_code == 200:
                        organic = response.json().get('organic', [])
                        for job in organic:
                            link = job.get('link')
                            if link:
                                all_results[link] = {"Title": job.get('title'), "Snippet": job.get('snippet'), "Link": link}
                    count += 1
                    progress_bar.progress(count / total_combos)
                except Exception:
                    continue
    return list(all_results.values())

def analyze_job(job_text):
    try:
        prompt = f"""
        Act as a peer-level Statistical Programming Director. 
        Look at this job description and Mahidhar's profile. 
        Don't use corporate jargon. Tell me honestly: is this a match?
        
        CANDIDATE: {USER_PROFILE}
        JOB: {job_text}
        
        Format: 
        Score: [0-100]%
        Why: [1-2 sentences in natural, human language]
        Gap: [What's missing, or 'None']
        """
        completion = client_groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"AI Analysis unavailable: {e}"

def generate_cover_letter(job_title, job_snippet):
    try:
        prompt = f"""
        Write a cover letter for {job_title}. 
        USE THIS PROFILE: {USER_PROFILE}
        JOB DETAILS: {job_snippet}
        
        CRITICAL INSTRUCTIONS for a HUMAN tone:
        1. DO NOT use words like 'passionate', 'leverage', 'synergy', or 'thrilled'.
        2. Write it as a conversation between two experts. 
        3. Focus on evidence: instead of saying 'I am an expert in CDISC', say 'I've spent the last 16 years ensuring BLA and NDA packages are CDISC-compliant.'
        4. Keep it concise, confident, and avoid sounding like a template. 
        5. Use a natural, professional flow.
        """
        completion = client_groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Could not generate cover letter: {e}"

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
st.markdown("### 🚀 High-Precision Discovery & Human-Centric Applications")

tab1, tab2, tab3 = st.tabs(["📡 Discovery Radar", "🧠 AI Matcher & Letter", "📈 Application Tracker"])

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
                
                # --- CLICKABLE LINKS FIX ---
                # We use st.dataframe with column_config to make links clickable
                st.dataframe(
                    st.session_state['jobs_df'][["Title", "Link"]], 
                    column_config={"Link": st.column_config.LinkColumn("Click to Apply ↗️")},
                    use_container_width=True
                )
            else:
                st.error("No roles found.")

with tab2:
    if 'jobs_df' not in st.session_state:
        st.info("Run Discovery Radar first.")
    else:
        df = st.session_state['jobs_df']
        selected_idx = st.selectbox("Select a Job", range(len(df)), format_func=lambda x: f"{df.iloc[x]['Title']}")
        job = df.iloc[selected_idx]
        
        col_a, col_b = st.columns([1, 1])
        with col_a:
            if st.button("🧠 Analyze Match %"):
                with st.spinner("Thinking like a Director..."):
                    analysis = analyze_job(job['Snippet'])
                    st.markdown(f"### AI Analysis\n{analysis}")
                    if st.button("✅ Mark as Applied"):
                        if save_to_tracker(job['Title'], job['Link']):
                            st.success("Saved to tracker!")

        with col_b:
            if st.button("📄 Generate Human Cover Letter"):
                with st.spinner("Drafting..."):
                    letter = generate_cover_letter(job['Title'], job['Snippet'])
                    st.markdown("### Your Tailored Letter")
                    st.markdown(f'<div class="cover-letter-box">{letter}</div>', unsafe_allow_html=True)
                    st.info("💡 Pro Tip: Read through this and tweak one sentence to make it truly yours before sending.")

with tab3:
    st.subheader("My Application CRM")
    tracker_df = get_tracker_data()
    if not tracker_df.empty:
        st.data_editor(tracker_df, num_rows="dynamic")
    else:
        st.info("No jobs tracked yet.")
