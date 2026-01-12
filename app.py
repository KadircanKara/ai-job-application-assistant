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

# --- CACHING: PARSE CV ---
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

# --- SAFEGUARD: VALIDATION ---
def validate_job_data(job_data):
    if not job_data: return False, "No data extracted."
    role = job_data.get('job_title', '')
    desc = job_data.get('description_text', '')
    reqs = job_data.get('requirements', '')

    if not role or len(role) < 3: return False, "Job Title missing."
    if (len(desc or "") + len(reqs or "")) < 200: return False, "Content too short (Login wall?)."
    return True, "Valid"

# --- HELPER: PROCESS & DISPLAY ---
def process_and_display_job(job_details, cv_text, count):
    is_valid, reason = validate_job_data(job_details)
    if not is_valid:
        st.warning(f"⚠️ Skipping Job #{count}: {reason}")
        return False

    # Normalize data
    role = job_details.get('job_title', 'Unknown Role')
    company = job_details.get('company_name', 'Unknown Company')
    
    # Create a safe filename prefix (e.g., "Google_SeniorDev")
    safe_filename = f"{company}_{role}".replace(" ", "_").replace("/", "-")[:30]
    
    st.success(f"✅ Target Acquired: {role} at {company}")
    
    if job_details.get('application_url'):
        st.caption(f"🔗 Apply Here: {job_details.get('application_url')}")
    
    # Generate Content
    with st.spinner("✍️ Generating Assets..."):
        assets = ai_logic.generate_application_package(cv_text, job_details)
        
    # --- TABS WITH DOWNLOAD BUTTONS ---
    tab1, tab2, tab3 = st.tabs(["📄 Tailored CV", "✉️ Cover Letter", "📧 Cold Email"])
    
    with tab1:
        st.text_area(f"cv_view_{count}", assets['tailored_cv'], height=400)
        st.download_button(
            label="💾 Download CV (.md)",
            data=assets['tailored_cv'],
            file_name=f"{safe_filename}_CV.md",
            mime="text/markdown",
            key=f"btn_cv_{count}"
        )
        
    with tab2:
        st.text_area(f"cl_view_{count}", assets['cover_letter'], height=400)
        st.download_button(
            label="💾 Download Cover Letter (.txt)",
            data=assets['cover_letter'],
            file_name=f"{safe_filename}_CoverLetter.txt",
            mime="text/plain",
            key=f"btn_cl_{count}"
        )
        
    with tab3:
        st.text_area(f"email_view_{count}", assets['email'], height=250)
        st.download_button(
            label="💾 Download Email Draft (.txt)",
            data=assets['email'],
            file_name=f"{safe_filename}_Email.txt",
            mime="text/plain",
            key=f"btn_email_{count}"
        )
    
    return True

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
    num_jobs = st.slider("Max Jobs", 1, 100, 5)

# --- MAIN LOGIC ---
if st.button("🚀 Find & Apply"):
    if not FIRECRAWL_API_KEY or not OPENROUTER_API_KEY:
        st.error("❌ Missing API Keys in .env file.")
        st.stop()
    if not cv_text:
        st.error("Please provide your CV first!")
        st.stop()
    if not search_logic.check_searxng_status():
        st.error("🔴 SearXNG is offline. Run `docker compose up -d`.")
        st.stop()

    # SEARCH QUERY
    included = "(site:boards.greenhouse.io OR site:lever.co OR site:workable.com OR site:jobs.ashbyhq.com OR site:bamboohr.com)"
    loc_query = f'"{location}"' if location.strip() else ""
    final_query = f'"{role}" {loc_query} {included}'
    
    st.info(f"🔎 Query: `{final_query}`")
    
    with st.spinner("Searching..."):
        raw_results = search_logic.query_searxng(final_query, num_results=5)
    
    if not raw_results:
        st.warning("No results found.")
        st.stop()

    global_processed_count = 0
    
    # PROCESS LOOP
    for item in raw_results:
        if global_processed_count >= num_jobs: break
        
        url = item['url']
        
        with st.container():
            st.markdown(f"### 📄 Analyzing: [{item['title']}]({url})")
            
            try:
                with st.spinner("🔥 Extracting data..."):
                    extract_data = search_logic.scrape_with_firecrawl(url, FIRECRAWL_API_KEY, role)
                
                if not extract_data: continue

                page_type = extract_data.get('page_type')

                # CASE 1: SINGLE JOB
                if page_type == 'single_job' and extract_data.get('single_job'):
                    success = process_and_display_job(extract_data['single_job'], cv_text, global_processed_count + 1)
                    if success: global_processed_count += 1

                # CASE 2: JOB LIST
                elif page_type == 'job_list' and extract_data.get('jobs_list'):
                    jobs = extract_data['jobs_list']
                    st.info(f"📋 List Detected: Found {len(jobs)} jobs. Checking deep links...")
                    
                    for sub_job in jobs:
                        if global_processed_count >= num_jobs: break
                        
                        link_url = sub_job.get('url')
                        if not link_url: continue
                        
                        if not link_url.startswith("http"):
                            link_url = urljoin(url, link_url)
                            
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ **Deep Diving:** {sub_job.get('title')}")
                        
                        sub_data = search_logic.scrape_with_firecrawl(link_url, FIRECRAWL_API_KEY, role)
                        
                        if sub_data and sub_data.get('single_job'):
                            success = process_and_display_job(sub_data['single_job'], cv_text, global_processed_count + 1)
                            if success: global_processed_count += 1

            except Exception as e:
                st.error(f"⚠️ Error: {e}")
                continue
            
            st.divider()