import streamlit as st
import requests
import pandas as pd
from groq import Groq
from supabase import create_client, Client
import time
import PyPDF2
import io

# --- MOBILE-FIRST CONFIGURATION ---
st.set_page_config(page_title="Universal Career Command Center", page_icon="🎯", layout="wide")

# Custom CSS to make it look like a Mobile App
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    /* Make buttons full width and larger for thumbs */
    .stButton>button { 
        width: 100% !important; 
        border-radius: 12px !important; 
        height: 3em !important; 
        background-color: #1a5f7a !important; 
        color: white !important; 
        font-size: 18px !important;
    }
    /* Professional Letter Box */
    .cover-letter-box { 
        background-color: white; 
        padding: 20px; 
        border-radius: 15px; 
        border: 1px solid #ddd; 
        font-family: 'Segoe UI', Tahoma, sans-serif; 
        line-height: 1.6; 
        color: #333; 
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }
    /* Fix for mobile table overflow */
    .stDataFrame {
        overflow-x: auto;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SECRET MANAGEMENT ---
serper_key = st.secrets.get("SERPER_API_KEY", None)
groq_key = st.secrets.get("GROQ_API_KEY", None)
supa_url = st.secrets.get("SUPABASE_URL", None)
supa_key = st.secrets.get("SUPABASE_KEY", None)

if not all([serper_key, groq_key, supa_url, supa_key]):
    st.sidebar.title("⚙️ System Settings")
    serper_key = st.sidebar.text_input("Serper.dev API Key", type="password", value=serper_key)
    groq_key = st.sidebar.text_input("Groq API Key", type="password", value=groq_key)
    supa_url = st.sidebar.text_input("Supabase URL", type="password", value=supa_url)
    supa_key = st.sidebar.text_input("Supabase API Key", type="password", value=supa_key)
    if not all([serper_key, groq_key, supa_url, supa_key]):
        st.warning("⚠️ API Keys required.")
        st.stop()

client_groq = Groq(api_key=groq_key)
supabase: Client = create_client(supa_url, supa_key)

# --- CORE LOGIC (Kept the same for robustness) ---
def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
        text = "".join([page.extract_text() for page in pdf_reader.pages])
        return text
    except Exception as e:
        st.error(f"PDF Error: {e}")
        return None

def search_jobs_fuzzy(role_input, loc_input):
    role_variations = [role_input, role_input.replace("Programming", "Programmer")]
    seniority = ["Principal", "Associate Director", "Manager", "Lead"]
    hubs = [loc_input, "Remote", "New Jersey", "Boston", "California", "USA"]
    site_keywords = "careers apply jobs"
    all_results = {}
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': serper_key, 'Content-Type': 'application/json'}
    
    progress_bar = st.progress(0)
    total = len(role_variations) * len(seniority) * len(hubs)
    count = 0
    for r in role_variations:
        for s in seniority:
            for h in hubs:
                query = f'{s} {r} {h} {site_keywords}'
                try:
                    res = requests.post(url, headers=headers, json={"q": query, "num": 50}, timeout=15)
                    if res.status_code == 200:
                        for job in res.json().get('organic', []):
                            link = job.get('link')
                            if link: all_results[link] = {"Title": job.get('title'), "Snippet": job.get('snippet'), "Link": link}
                    count += 1
                    progress_bar.progress(count / total)
                except Exception: continue
    return list(all_results.values())

def analyze_job(job_text, user_profile):
    try:
        prompt = f"Compare this JD with Candidate Profile.\n\nPROFILE:\n{user_profile}\n\nJOB:\n{job_text}\n\nFormat: Score [0-100]%, Reason [2 sentences], Key Missing [List]."
        return client_groq.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}]).choices[0].message.content
    except Exception as e: return f"Error: {e}"

def generate_cover_letter(job_title, job_snippet, user_profile):
    try:
        prompt = f"Write a human-sounding cover letter for {job_title}. PROFILE: {user_profile} JOB: {job_snippet}. No corporate buzzwords."
        return client_groq.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}]).choices[0].message.content
    except Exception as e: return f"Error: {e}"

def save_to_tracker(title, link):
    try:
        supabase.table("jobs_tracker").insert({"title": title, "link": link, "status": "Applied", "date": pd.Timestamp.now().strftime("%Y-%m-%d")}).execute()
        return True
    except Exception as e: return False

def get_tracker_data():
    try:
        return pd.DataFrame(supabase.table("jobs_tracker").select("*").execute().data)
    except Exception: return pd.DataFrame()

# --- APP UI (MOBILE-FIRST) ---
st.title("🎯 Career Command Center")

if 'jobs_df' not in st.session_state: st.session_state['jobs_df'] = None
if 'user_cv_text' not in st.session_state: st.session_state['user_cv_text'] = None

tab1, tab2, tab3, tab4 = st.tabs(["👤 Profile", "📡 Radar", "🧠 AI Match", "📈 Tracker"])

with tab1:
    st.subheader("Upload CV")
    uploaded_file = st.file_uploader("PDF CV", type="pdf")
    if uploaded_file:
        text = extract_text_from_pdf(uploaded_file)
        st.session_state['user_cv_text'] = text
        st.success("CV Loaded!")

with tab2:
    # Mobile-friendly: Inputs are stacked, not in columns
    target_role = st.text_input("Target Role", value="Statistical Programmer")
    target_loc = st.text_input("Target Location", value="Remote")
    if st.button("🚀 Scan for Roles"):
        with st.spinner("Searching..."):
            results = search_jobs_fuzzy(target_role, target_loc)
            if results:
                st.session_state['jobs_df'] = pd.DataFrame(results)
                st.success(f"Found {len(results)} roles!")
                st.dataframe(st.session_state['jobs_df'][["Title", "Link"]], column_config={"Link": st.column_config.LinkColumn("Apply ↗️")}, use_container_width=True)
            else:
                st.error("No roles found.")

with tab3:
    if st.session_state['user_cv_text'] is None:
        st.error("Upload CV first!")
    elif st.session_state['jobs_df'] is None:
        st.info("Scan for jobs first.")
    else:
        df = st.session_state['jobs_df']
        selected_title = st.selectbox("Select Job", options=df['Title'].tolist())
        job = df[df['Title'] == selected_title].iloc[0]
        
        # Mobile-friendly: Buttons are stacked vertically
        if st.button("🧠 Analyze Match %"):
            analysis = analyze_job(job['Snippet'], st.session_state['user_cv_text'])
            st.markdown(f"### AI Analysis\n{analysis}")
            if st.button("✅ Mark as Applied"):
                if save_to_tracker(job['Title'], job['Link']): st.success("Saved!")

        if st.button("📄 Generate Cover Letter"):
            letter = generate_cover_letter(job['Title'], job['Snippet'], st.session_state['user_cv_text'])
            st.markdown(f'<div class="cover-letter-box">{letter}</div>', unsafe_allow_html=True)

with tab4:
    st.subheader("My Applications")
    tracker_df = get_tracker_data()
    if not tracker_df.empty:
        st.data_editor(tracker_df, num_rows="dynamic")
    else:
        st.info("No jobs tracked yet.")
