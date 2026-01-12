import os
import streamlit as st
import pdfplumber
from dotenv import load_dotenv
from urllib.parse import urljoin
import search_logic
import ai_logic

load_dotenv()
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
print("FIRECRAWL KEY:", FIRECRAWL_API_KEY)

print('FIRECRAWL_API_KEY' in os.environ) # True of False
print(os.environ['FIRECRAWL_API_KEY']) # Print contents of variable
print(os.environ.get('FIRECRAWL_API_KEY')) # Its better when variable not existed


st.set_page_config(page_title="Deep Research Job Agent", layout="wide")
st.title("🔥 AI Job Agent (Recursive Edition)")

# --- HELPER: GENERATOR FUNCTION ---
def process_single_job_data(job_data, cv_text, processed_count):
    """
    This function takes the EXTRACTED data (from the AI) and runs the GENERATION step.
    """
    st.success(f"✅ Target Acquired: {job_data.get('role')} at {job_data.get('company')}")
    
    # col1, col2 = st.columns(2)
    # with col1:
    #     # Research Manager
    #     manager = ai_logic.research_hiring_manager(job_data.get('hiring_manager_name'), job_data.get('company'))
    #     st.caption(f"Contact: {manager}")
    # with col2:
    #     # Research News
    #     news = ai_logic.research_company_news(job_data.get('company'))
    #     st.caption(f"News: {news[:100]}...")

    with st.spinner("✍️ Writing Application Assets..."):
        # GENERATE CV & COVER LETTER
        cl, email = ai_logic.generate_application_package(cv=cv_text, job_data=job_data)
    
    tab1, tab2 = st.tabs(["Cover Letter", "Cold Email"])
    with tab1: st.text_area(f"CL_{processed_count}", cl, height=300)
    with tab2: st.text_area(f"Email_{processed_count}", email, height=150)

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Upload CV")
    uploaded_file = st.file_uploader("Master CV (PDF)", type="pdf")
    cv_text = ""
    if uploaded_file:
        with pdfplumber.open(uploaded_file) as pdf:
            cv_text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        st.success("CV Loaded")
        
    st.divider()
    st.header("2. Search Strategy")
    role = st.text_input("Target Role", "Python Developer")
    num_jobs = st.slider("Max Jobs to Generate", 1, 10, 3)

# --- MAIN LOGIC ---
if st.button("🚀 Find & Apply"):
    if not FIRECRAWL_API_KEY:
        st.error("❌ FIRECRAWL_API_KEY missing in .env file.")
        st.stop()
    if not cv_text:
        st.error("Upload CV first!")
        st.stop()
    if not search_logic.check_searxng_status():
        st.error("🔴 SearXNG is offline. Run `docker compose up -d`.")
        st.stop()

    # 1. SEARCH
    excluded = "-site:linkedin.com -site:indeed.com -site:glassdoor.com"
    included = "(site:boards.greenhouse.io OR site:lever.co OR site:workable.com OR site:jobs.ashbyhq.com OR site:angel.co)"
    final_query = f'"{role}" {included}'
    st.info(f"🔎 Query: `{final_query}`")
    
    raw_results = search_logic.query_searxng(final_query, num_results=5)
    if not raw_results:
        st.warning("No results found.")
        st.stop()

    global_processed_count = 0
    
    # 2. OUTER LOOP (Iterate Search Results)
    for item in raw_results:
        if global_processed_count >= num_jobs:
            break
            
        url = item['url']
        
        with st.container():
            st.markdown(f"### 📄 Analyzing Search Result: [{item['title']}]({url})")
            
            # --- STEP A: SCRAPE THE SEARCH RESULT and GET JOB DETAILS JSON ---
            try:
                with st.spinner("🔥 Scraping link..."):
                    doc = search_logic.scrape_with_firecrawl(url=url, api_key=FIRECRAWL_API_KEY, target_role=role)
                    md = doc.markdown
                    jobs = doc.json
                    if not jobs: raise ValueError("Empty content")
                with st.spinner("Analyzing jobs..."):
                    for job in jobs["jobs"]:
                        # Scrape application links
                        job_details = search_logic.scrape_with_firecrawl(url=job.get('application_link', ''), api_key=FIRECRAWL_API_KEY, target_role=role)

                        job_text = f"""
                        Job Title: {job_details.get('job_title', '')}
                        Company Name: {job_details.get('company_name', '')}
                        Location: {job_details.get('location', '')}
                        Job Description: {job_details.get('job_description', '')}
                        Requirements: {job_details.get('requirements', '')}
                        Salary: {job_details.get('salary', '')}
                        Hiring Person: {job_details.get('hiring_person', '')}
                        Application Link: {job_details.get('application_link', '')}
                        """
                        
                        # job_data = ai_logic.extract_job_details(job_text, target_role=role)
                        
                        if job_data and (job_data.get('type') == 'job_post' or job_data.get('valid_job')):
                            global_processed_count += 1
                            process_single_job_data(job_data, cv_text, global_processed_count)
                            
                            if global_processed_count >= num_jobs:
                                break


            except Exception as e:
                st.error(f"⚠️ Scrape failed: {e}")
                continue 

            # --- STEP B: FIRST AI INVOKE (Classify & Extract) ---
            # The AI decides: Is this a Single Job? Or a List of Jobs?
            job_data = ai_logic.extract_job_details(job_text, target_role=role)
            
            if not job_data:
                st.warning("AI failed to parse content.")
                continue

            # --- BRANCH 1: IT IS ALREADY A SINGLE JOB ---
            if job_data.get('type') == 'job_post' or job_data.get('valid_job'):
                global_processed_count += 1
                # We already have the details, so we generate immediately
                process_single_job_data(job_data, cv_text, global_processed_count)

            # --- BRANCH 2: IT IS A LIST PAGE (RECURSIVE LOOP) ---
            elif job_data.get('type') == 'job_list':
                jobs = job_data.get('jobs', [])
                
                if not jobs:
                    st.warning("⚠️ List page detected, but AI found no matching links.")
                    continue
                    
                st.info(f"📋 List Page Detected. Found {len(jobs)} potential matches. Diving in...")
                
                # --- INNER LOOP: VISIT EACH LINK ---
                for job in jobs:
                    if global_processed_count >= num_jobs:
                        break
                        
                    link_title = job.get('title', 'Unknown Job')
                    link_url = job.get('url')
                    
                    if not link_url: continue

                    # Fix Relative URLs
                    if not link_url.startswith("http"):
                        link_url = urljoin(url, link_url)
                        
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ **Deep Diving:** {link_title}")
                    
                    try:
                        with st.spinner(f"🔥 Scraping sub-page: {link_title}..."):
                            
                            # 1. SCRAPE THE SUB-PAGE
                            sub_job_text = search_logic.scrape_with_firecrawl(link_url, FIRECRAWL_API_KEY)
                            
                            if sub_job_text:
                                # 2. SECOND AI INVOKE (CRITICAL STEP)
                                # We pass the new text to the AI to get requirements, company name, etc.
                                sub_job_data = ai_logic.extract_job_details(sub_job_text, target_role=role)
                                
                                # 3. VALIDATE & GENERATE
                                if sub_job_data and (sub_job_data.get('type') == 'job_post' or sub_job_data.get('valid_job')):
                                    global_processed_count += 1
                                    process_single_job_data(sub_job_data, cv_text, global_processed_count)
                                else:
                                    st.caption("❌ AI decided this sub-link wasn't a valid job post.")
                    except Exception as e:
                        st.caption(f"⚠️ Failed to process sub-link: {e}")

            st.divider()
    
    if global_processed_count == 0:
        st.error("Finished analysis but found no valid jobs to apply to.")
    else:
        st.balloons()
        st.success(f"🎉 Job Done! Generated {global_processed_count} applications.")