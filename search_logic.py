import requests
from firecrawl import Firecrawl
from config import SEARXNG_API_URL, BROWSER_HEADERS
from pydantic import BaseModel, Field
from typing import List, Optional

class JobLink(BaseModel):
    title: str = Field(description="The title of the job link found")
    url: str = Field(description="The absolute URL to the job details")
    company: Optional[str] = None
    location: Optional[str] = None

class SingleJobDetails(BaseModel):
    job_title: str = Field(description="The specific role title")
    company_name: str = Field(description="Name of the company hiring")
    location: Optional[str] = Field(description="Job location or 'Remote'")
    
    # CRITICAL: We need the full text to validate quality
    description_text: str = Field(description="The full job description and responsibilities text.")
    
    requirements: str = Field(description="Comprehensive list of technical skills and requirements")
    
    # Optional: Extract the actual apply link if it's different from the current URL
    application_url: Optional[str] = Field(description="The URL to submit the application, if different from current page")

class JobExtractionSchema(BaseModel):
    page_type: str = Field(
        description="Determine if this page is a list of multiple jobs ('job_list') or a specific single job description ('single_job').", 
        enum=["job_list", "single_job"]
    )
    jobs_list: Optional[List[JobLink]] = Field(description="Extract this ONLY if page_type is 'job_list'.")
    single_job: Optional[SingleJobDetails] = Field(description="Extract this ONLY if page_type is 'single_job'.")


# --- 2. SEARXNG SEARCH ---

def check_searxng_status():
    try:
        requests.get(SEARXNG_API_URL, timeout=1)
        return True
    except:
        return False

def query_searxng(query, num_results=5):
    url = f"{SEARXNG_API_URL}/search"
    params = {"q": query, "format": "json", "language": "en-US"}
    try:
        resp = requests.get(url, params=params, headers=BROWSER_HEADERS, timeout=10)
        if resp.status_code == 200:
            return resp.json().get('results', [])[:num_results]
    except Exception as e:
        print(f"Search failed: {e}")
    return []

# --- 3. FIRECRAWL SCRAPER ---

def scrape_with_firecrawl(url, api_key, target_role=""):
    """
    Uses Firecrawl's JSON Extract feature with strict Schema validation.
    """
    print(f"    🔥 Firecrawl Extracting: {url}")
    
    if not api_key:
        raise ValueError("API Key is missing.")

    app = Firecrawl(api_key=api_key)
    
    # Get the raw JSON schema
    schema_json = JobExtractionSchema.model_json_schema()

    try:
        # --- THE FIX ---
        # Passing schema inside the formats list as requested
        data = app.scrape(
            url,
            formats=[{
                "type": "json",
                "schema": schema_json
            }]
        )
        
        # Firecrawl returns the data under the 'json' key
        if data and data.json:
            return data.json
            
        print(f"    ⚠️ Firecrawl returned no JSON data.")
        return None
        
    except Exception as e:
        print(f"    ❌ Firecrawl Error: {e}")
        raise e