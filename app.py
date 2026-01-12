import os
import streamlit as st
from pypdf import PdfReader
from dotenv import load_dotenv
from urllib.parse import urljoin
import search_logic
import ai_logic

load_dotenv()
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

st.set_page_config(page_title="Fast AI Job Agent", layout="wide")
st.title("⚡ AI Job Agent")

# --- 1. SESSION STATE SETUP ---
if "jobs_queue" not in st.session_state:
    st.session_state.jobs_queue = []

# --- CACHING ---
@st.cache_data
def parse_cv_pdf(file):
    try:
        text = ""
        reader = PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        return None

# --- VALIDATION ---
def validate_job_data(job_data):
    """
    Ensures the extracted data actually looks like a job.
    """
    if not job_data: return False, "No data extracted."
    
    role = job_data.get('job_title', '')
    company = job_data.get('company_name', '')
    desc = job_data.get('description_text', '')
    reqs = job_data.get('requirements', '')
    
    # 1. Critical Fields Check
    if not role or len(role) < 3: 
        return False, "Job Title missing."
    if not company or len(company) < 2:
        return False, "Company Name missing (likely a blog post)."
        
    # 2. Content Length Check (Login wall / Empty page detector)
    if (len(desc or "") + len(reqs or "")) < 200: 
        return False, "Content too short (Login wall?)"
        
    return True, "Valid"

# --- HELPER: ADD TO STATE (FAST VERSION) ---
def add_job_to_state(job_details, source_url):
    """
    Validates and adds job to queue. 
    does NOT generate assets yet (saves time).
    """
    is_valid, reason = validate_job_data(job_details)
    
    if not is_valid:
        st.caption(f"⚠️ Skipping invalid: {reason}")
        return False

    role = job_details.get('job_title', 'Unknown Role')
    company = job_details.get('company_name', 'Unknown Company')
    
    # Save Raw Data
    job_package = {
        "id": len(st.session_state.jobs_queue),
        "role": role,
        "company": company,
        "job_details": job_details, # Store raw data for later generation
        "apply_link": job_details.get('application_url') or source_url,
        "assets": None # Empty initially
    }
    
    st.session_state.jobs_queue.append(job_package)
    return True

# --- HELPER: GENERATE ASSETS (SLOW VERSION) ---
def generate_single_job_assets(job_package, cv_text):
    """
    Runs the AI generation for a specific job package
    """
    with st.spinner(f"✍️ Writing application for {job_package['company']}..."):
        assets = ai_logic.generate_application_package(cv_text, job_package['job_details'])
        job_package['assets'] = assets
        st.toast(f"Generated for {job_package['company']}!", icon="✅")

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Your Info")
    input_method = st.radio("CV Input Method:", ["Upload PDF", "Paste Text"])
    
    cv_text = ""
    if input_method == "Upload PDF":
        uploaded_file = st.file_uploader("Upload CV", type="pdf")
        if uploaded_file:
            cv_text = parse_cv_pdf(uploaded_file)
            if cv_text: st.success("✅ CV Loaded")
    else:
        cv_text = st.text_area("Paste CV Text Here", height=200)
        if cv_text: st.success("✅ Text Ready")

    st.divider()
    st.header("2. Search Strategy")
    role = st.text_input("Target Role", "Python Developer")
    location = st.text_input("Target Location", "Remote")
    num_jobs = st.slider("Target Jobs to Find", 1, 20, 5)

    if st.button("Clear Results"):
        st.session_state.jobs_queue = []
        st.rerun()

# --- MAIN LOGIC ---

# PART 1: SEARCH & SCOUT (Fast)
if st.button("🚀 Find Jobs (Scout Mode)"):
    if not FIRECRAWL_API_KEY or not OPENROUTER_API_KEY:
        st.error("❌ Missing API Keys in .env file.")
        st.stop()
    if not cv_text:
        st.error("Please provide your CV first!")
        st.stop()
    if not search_logic.check_searxng_status():
        st.error("🔴 SearXNG is offline. Run `docker compose up -d`.")
        st.stop()

    st.session_state.jobs_queue = []

    included = "(site:boards.greenhouse.io OR site:lever.co OR site:workable.com OR site:jobs.ashbyhq.com OR site:bamboohr.com)"
    loc_query = f'"{location}"' if location.strip() else ""
    # final_query = f'"{role}" {loc_query} {included}'
    final_query = f'"{role}" {loc_query}'
    
    st.info(f"🔎 Query: `{final_query}`")
    
    global_processed_count = 0
    current_page = 1
    MAX_PAGES = 10
    processed_urls = set()

    progress_bar = st.progress(0)
    status_text = st.empty()

    while global_processed_count < num_jobs and current_page <= MAX_PAGES:
        status_text.write(f"🔄 Searching Page {current_page}... (Found {global_processed_count}/{num_jobs})")
        
        raw_results = search_logic.query_searxng(final_query, page=current_page)
        if not raw_results: break
            
        for item in raw_results:
            if global_processed_count >= num_jobs: break
            url = item['url']
            if url in processed_urls: continue
            processed_urls.add(url)
            
            with st.container():
                st.write(f"🔍 Checking: **{item['title']}**")
                try:
                    extract_data = search_logic.scrape_with_firecrawl(url, FIRECRAWL_API_KEY, role)
                    if not extract_data: continue

                    page_type = extract_data.get('page_type')

                    # Single Job
                    if page_type == 'single_job' and extract_data.get('single_job'):
                        success = add_job_to_state(extract_data['single_job'], url)
                        if success: 
                            global_processed_count += 1
                            progress_bar.progress(global_processed_count / num_jobs)

                    # Job List
                    elif page_type == 'job_list' and extract_data.get('jobs_list'):
                        jobs = extract_data['jobs_list']
                        st.caption(f"📋 Found list with {len(jobs)} jobs. Scanning sub-links...")
                        
                        for sub_job in jobs:
                            if global_processed_count >= num_jobs: break
                            link_url = sub_job.get('url')
                            if not link_url or link_url in processed_urls: continue
                            processed_urls.add(link_url)
                            
                            if not link_url.startswith("http"):
                                link_url = urljoin(url, link_url)
                                
                            sub_data = search_logic.scrape_with_firecrawl(link_url, FIRECRAWL_API_KEY, role)
                            if sub_data and sub_data.get('single_job'):
                                success = add_job_to_state(sub_data['single_job'], link_url)
                                if success: 
                                    global_processed_count += 1
                                    progress_bar.progress(global_processed_count / num_jobs)

                except Exception as e:
                    continue
        current_page += 1
    
    status_text.empty()
    progress_bar.empty()
    
    if global_processed_count > 0:
        st.success(f"🎯 Found {global_processed_count} relevant jobs! Review and Generate below.")
    else:
        st.error("No valid jobs found.")

# PART 2: RENDERING & GENERATION
if st.session_state.jobs_queue:
    st.divider()
    
    # "Generate All" Button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"✅ Job Queue ({len(st.session_state.jobs_queue)})")
    with col2:
        if st.button("⚡ Generate ALL Assets"):
            progress_bar = st.progress(0)
            for i, job in enumerate(st.session_state.jobs_queue):
                if not job['assets']:
                    generate_single_job_assets(job, cv_text)
                progress_bar.progress((i + 1) / len(st.session_state.jobs_queue))
            st.rerun()

    for i, job in enumerate(st.session_state.jobs_queue):
        with st.expander(f"📄 {job['role']} @ {job['company']}", expanded=(job['assets'] is None)):
            
            # Show Links
            if job['apply_link']:
                st.markdown(f"🔗 **[Apply Here]({job['apply_link']})**")
            
            # State: Assets NOT Generated
            if job['assets'] is None:
                st.info("Job data extracted. Ready to write application.")
                if st.button(f"✍️ Generate Application", key=f"gen_{i}"):
                    generate_single_job_assets(job, cv_text)
                    st.rerun()
            
            # State: Assets GENERATED
            else:
                assets = job['assets']
                safe_filename = f"{job['company']}_{job['role']}".replace(" ", "_")[:20]
                
                tab1, tab2, tab3 = st.tabs(["Tailored CV", "Cover Letter", "Cold Email"])
                
                with tab1:
                    st.text_area("CV Content", assets['tailored_cv'], height=300, key=f"cv_{i}")
                    st.download_button("💾 Download CV", assets['tailored_cv'], f"{safe_filename}_CV.md", "text/markdown", key=f"btn_cv_{i}")
                    
                with tab2:
                    st.text_area("CL Content", assets['cover_letter'], height=300, key=f"cl_{i}")
                    st.download_button("💾 Download CL", assets['cover_letter'], f"{safe_filename}_CL.txt", "text/plain", key=f"btn_cl_{i}")
                    
                with tab3:
                    st.text_area("Email Content", assets['email'], height=200, key=f"em_{i}")
                    st.download_button("💾 Download Email", assets['email'], f"{safe_filename}_Email.txt", "text/plain", key=f"btn_em_{i}")