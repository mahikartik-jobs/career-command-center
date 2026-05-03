import streamlit as st
import requests
import pandas as pd
from groq import Groq
from supabase import create_client, Client
import time
import PyPDF2
import io

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Universal Career Command Center", page_icon="🎯", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #1a5f7a; color: white; }
    .cover-letter-box { background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #ddd; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }
    </style>
    """, unsafe_allow_html=True)

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

# --- PDF TEXT EXTRACTION ---
def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return None

# --- CORE LOGIC ---

def search_jobs_fuzzy(role_input, loc_input):
    role_variations = [role_input, role_input.replace("Programming", "Programmer")]
    seniority = ["Principal", "Associate Director", "Manager", "Lead"]
    hubs = [loc_input, "Remote", "New Jersey", "Boston", "California", "USA"]
    site_keywords = "careers apply jobs"
    
    all_results = {}
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': serper_key, 'Content-Type': 'application/json'}
    
    progress_bar = st.progress(0)
    total_combos = len(role_variations) * len(seniority) * len(hubs)
    count = 0

    for r in role_variations:
        for s in seniority:
            for h in hubs:
                query = f'{s} {r} {h} {site_keywords}'
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

def analyze_job(job_text, user_profile):
    try:
        prompt = f"Compare this Job Description with the Candidate Profile.\n\nCANDIDATE PROFILE:\n{user_profile}\n\nJOB:\n{job_text}\n\nFormat: Score [0-100]%, Reason [2 sentences], Key Missing [List]."
        completion = client_groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"AI Analysis unavailable: {e}"

def generate_cover_letter(job_title, job_snippet, user_profile):
    try:
        prompt = f"""
        Write a professional, human-sounding cover letter for {job_title}. 
        CANDIDATE PROFILE: {user_profile}
        JOB DETAILS: {job_snippet}
        
        CRITICAL INSTRUCTIONS:
        1. No corporate buzzwords. 
        2. Use an industry-peer tone.
        3. Focus on evidence-based achievements.
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
st.title("🎯 Universal Career Command Center")
st.markdown("### 🚀 Multi-Profile Job Discovery & AI Matching")

# INITIALIZE SESSION STATES
if 'jobs_df' not in st.session_state:
    st.session_state['jobs_df'] = None
if 'user_cv_text' not in st.session_state:
    st.session_state['user_cv_text'] = None

tab1, tab2, tab3, tab4 = st.tabs(["👤 Profile Settings", "📡 Discovery Radar", "🧠 AI Matcher & Letter", "📈 Application Tracker"])

with tab1:
    st.subheader("Your Professional Profile")
    uploaded_file = st.file_uploader("Upload your CV (PDF)", type="pdf")
    
    if uploaded_file:
        with st.spinner("Extracting experience..."):
            text = extract_text_from_pdf(uploaded_file)
            st.session_state['user_cv_text'] = text
            st.success("CV uploaded and parsed successfully!")
            with st.expander("View Extracted Text"):
                st.write(text)
    else:
        st.info("Please upload your CV to activate the AI Matcher.")

with tab2:
    col1, col2 = st.columns(2)
    with col1: target_role = st.text_input("Target Role", value="Statistical Programmer")
    with col2: target_loc = st.text_input("Target Location", value="Remote")

    if st.button("🚀 Scan for High-Value Roles"):
        with st.spinner("Executing Fuzzy Cluster Search..."):
            results = search_jobs_fuzzy(target_role, target_loc)
            if results:
                st.session_state['jobs_df'] = pd.DataFrame(results)
                st.success(f"Found {len(results)} unique roles!")
                st.dataframe(st.session_state['jobs_df'][["Title", "Link"]], 
                              column_config={"Link": st.column_config.LinkColumn("Apply Now ↗️")},
                              use_container_width=True)
            else:
                st.error("No roles found.")

with tab3:
    if st.session_state['user_cv_text'] is None:
        st.error("❌ Please upload your CV in the 'Profile Settings' tab first!")
    elif st.session_state['jobs_df'] is None or st.session_state['jobs_df'].empty:
        st.info("Run Discovery Radar first.")
    else:
        df = st.session_state['jobs_df']
        
        # FIX: We use the Title as the selection value instead of a range index.
        # This prevents the TypeError when the dataframe changes.
        job_titles = df['Title'].tolist()
        selected_title = st.selectbox("Select a Job to Analyze", options=job_titles)
        
        # Retrieve the full job data based on the selected title
        job = df[df['Title'] == selected_title].iloc[0]
        
        col_a, col_b = st.columns([1, 1])
        with col_a:
            if st.button("🧠 Analyze Match %"):
                with st.spinner("AI Analyzing..."):
                    analysis = analyze_job(job['Snippet'], st.session_state['user_cv_text'])
                    st.markdown(f"### AI Analysis\n{analysis}")
                    if st.button("✅ Mark as Applied"):
                        if save_to_tracker(job['Title'], job['Link']):
                            st.success("Saved to tracker!")

        with col_b:
            if st.button("📄 Generate Human Cover Letter"):
                with st.spinner("Drafting..."):
                    letter = generate_cover_letter(job['Title'], job['Snippet'], st.session_state['user_cv_text'])
                    st.markdown("### Your Tailored Letter")
                    st.markdown(f'<div class="cover-letter-box">{letter}</div>', unsafe_allow_html=True)

with tab4:
    st.subheader("My Application CRM")
    tracker_df = get_tracker_data()
    if not tracker_df.empty:
        st.data_editor(tracker_df, num_rows="dynamic")
    else:
        st.info("No jobs tracked yet.")
