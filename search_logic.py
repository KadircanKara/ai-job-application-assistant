import requests
from firecrawl import Firecrawl
from config import SEARXNG_API_URL, BROWSER_HEADERS

# --- SEARXNG SEARCH ---

def check_searxng_status():
    """
    Checks if the local SearXNG Docker container is reachable.
    """
    try:
        # Simple ping to the root URL
        requests.get(SEARXNG_API_URL, timeout=1)
        return True
    except:
        return False

def query_searxng(query, num_results=5):
    """
    Queries the local SearXNG instance.
    """
    url = f"{SEARXNG_API_URL}/search"
    
    params = {
        "q": query,
        "format": "json",
        "language": "en-US",
    }

    try:
        resp = requests.get(url, params=params, headers=BROWSER_HEADERS, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            return data.get('results', [])[:num_results]
        else:
            print(f"    ❌ SearXNG Error {resp.status_code}: {resp.text}")
            
    except Exception as e:
        print(f"    ❌ Search Connection Failed: {e}")
        
    return []

# --- FIRECRAWL SCRAPER ---

def scrape_with_firecrawl(url, api_key, target_role):
    """
    Uses the official Firecrawl Python SDK to scrape a URL into Markdown.
    """
    print(f"    🔥 Firecrawl Scraping: {url}")
    
    if not api_key:
        raise ValueError("API Key is missing/empty.")

    try:
        # Initialize the App with the key provided
        firecrawl = Firecrawl(api_key=api_key)
        
        # --- THE FIX: Replaced scrape_url with scrape ---
        # We pass params to ensure specific formats are requested
        # scraped_data = firecrawl.scrape(url, formats=['markdown'])
        if target_role:
            scraped_data = firecrawl.scrape( url, formats=[ "markdown",
                                                            {"type": "json", "prompt": f"Extract the details of every job related to the role '{target_role} in the page'. Output JSON with fields: 'job_title, company_name, location, job_description, requirements, responsabilities, salary, application_link.' for every relevant job. Name the root key as 'jobs' containing an array of jobs."}
                                                        ],
                                                    timeout=120000,
                                                    actions=[
                                                        # {"wait_for_event": "load"},
                                                        {"type": "scroll", "direction": "down", "steps": 5},
                                                        {"type": "wait", "milliseconds": 2000}
                                                        ],
                                                    only_main_content=False
                                            )
        else:
            scraped_data = firecrawl.scrape(url, formats=['markdown'])

        # print(f"Scraped Data:\n{scraped_data}\n")

        if scraped_data:
            if target_role:
                return scraped_data
            markdown = scraped_data.markdown
            return markdown
        return None
        
        # # The SDK returns a dictionary. We extract the markdown.
        # if scraped_data and 'markdown' in scraped_data:
        #     markdown = scraped_data['markdown']
        #     print(f"    ✅ Success! Retrieved {len(markdown)} chars.")
        #     return markdown
        
        # # Fallback: Sometimes it might return data directly or in 'data' key depending on version
        # if scraped_data and 'data' in scraped_data and 'markdown' in scraped_data['data']:
        #      markdown = scraped_data['data']['markdown']
        #      print(f"    ✅ Success! Retrieved {len(markdown)} chars.")
        #      return markdown
        
        # print(f"    ⚠️ Firecrawl returned no markdown content. Response keys: {scraped_data.keys() if scraped_data else 'None'}")
        print("    ⚠️ Firecrawl returned no markdown content.")
        return None
        
    except Exception as e:
        print(f"    ❌ Firecrawl SDK Error: {e}")
        raise e