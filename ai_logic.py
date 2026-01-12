import os
import json
import numpy as np
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from openai import OpenAI
from config import OLLAMA_MODEL
import search_logic
from dotenv import load_dotenv

# --- 1. CHAT MODEL (For Extraction & Writing) ---
# Low temperature for strictness, high context for large pages
llm = ChatOllama(
    model=OLLAMA_MODEL, 
    temperature=0.0,
    num_ctx=8192 
)

# --- 2. EMBEDDING MODEL (For Filtering) ---
# Requires: ollama pull nomic-embed-text
embeddings_model = OllamaEmbeddings(model="nomic-embed-text")

def invoke_openrouter(prompt:str, model_name="xiaomi/mimo-v2-flash:free"):

    load_dotenv()

    # Initialize client with OpenRouter API key
    client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    )

    response = client.chat.completions.create(
    model=model_name,
    messages=[
            {
                "role": "user",
                "content": prompt
        }
    ],
    extra_body={"reasoning": {"enabled": False}}
    )

    response = response.choices[0].message

    return response

def calculate_similarity(target_role, job_titles):
    """
    Converts titles to vectors and calculates similarity scores.
    Returns a list of valid indices.
    """
    if not job_titles: return []
    
    print(f"    🧮 Calculating Semantic Similarity for '{target_role}'...")
    
    try:
        # 1. Embed the Target Role (User's input)
        target_vector = embeddings_model.embed_query(target_role)
        
        # 2. Embed all found Job Titles
        title_vectors = embeddings_model.embed_documents(job_titles)
        
        valid_indices = []
        
        # 3. Math: Cosine Similarity
        # Score ranges from -1 to 1. 
        # 0.45 is a safe cutoff (allows "Software Engineer" for "Python Dev" but blocks "Sales")
        THRESHOLD = 0.45 
        
        for i, vector in enumerate(title_vectors):
            dot_product = np.dot(target_vector, vector)
            norm_target = np.linalg.norm(target_vector)
            norm_title = np.linalg.norm(vector)
            score = dot_product / (norm_target * norm_title)
            
            print(f"       • '{job_titles[i]}' Score: {score:.4f} [{'✅' if score > THRESHOLD else '❌'}]")
            
            if score > THRESHOLD:
                valid_indices.append(i)
                
        return valid_indices
        
    except Exception as e:
        print(f"    ⚠️ Embedding calculation failed: {e}. Defaulting to Accept All.")
        return range(len(job_titles))

def extract_job_details(text, target_role, top_k=5):
    # Guard clause
    if not text or len(text) < 150: return None
        
    parser = JsonOutputParser()

    prompt = PromptTemplate(
        template="""
        Analyze this website markdown.
        
        USER TARGET ROLE: "{role}"
        CONTENT:
        {text}
        
        ---
        
        ### TASK
        Identify all distinct job opportunities on this page.
        
        ### DECISION LOGIC
        1. Does the page list **multiple distinct jobs** (e.g., "Similar Jobs", "Other openings", or a search result list)?
           -> **YES**: Treat this as a **LIST PAGE** (`job_list`), even if one job is fully described/expanded.
           -> **NO**: If only ONE job exists on the entire page, treat as `job_post`.

        ---

        ### SCENARIO 1: SINGLE JOB POSTING (`job_post`)
        (Only use this if NO other distinct job links are found)
        - Set "type": "job_post"
        - Extract company, role, location, responsibilities, requirements, desired_skills, hiring_person.

        ### SCENARIO 2: JOB LIST / SPLIT VIEW (`job_list`)
        (Use this if multiple jobs appear, even if one is highlighted)
        - Set "type": "job_list"
        - **Action**: Extract the "url", "role", "company", and "location" for the top {top_k} jobs found. You can probably get the urls from the href elements near the job titles.
        - **Crucial**: If a main job is currently displayed/expanded, include it as the first item in the list!
        - **Filter**: Only include {top_k} jobs that are relevant to "{role}".
        - **Deduplicate**: Ensure the same URL/Job is not listed twice.

        Example Output for Scenario 2:
        {{
            "type": "job_list", 
            "jobs": [
                {{ "role": "Python Developer", "company": "Huawei", "location": "Istanbul", "url": "..."}},
                {{ "role": "AI Engineer", "company": "Siemens", "location": "Istanbul", "url": "...",}},
                {{}}, ..., {{}}
            ]
        }}
        
        OUTPUT JSON ONLY. Ensure keys are enclosed in double quotes.
        
        {format_instructions}
        """,
        input_variables=["role", "text"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    chain = prompt | llm | parser
    
    try:
        result = chain.invoke({
            "text": text, # Increased context to see sidebar items
            "role": target_role,
            "top_k": top_k
        })
        
        # --- SEMANTIC FILTERING ---
        # We apply the Python Hybrid Filter (Keyword + Semantic) here
        # to remove the "Business Development" or "Truck Driver" links 
        # that the permissive AI might have grabbed.
        
        if result.get('type') == 'job_list' and 'jobs' in result:
            raw_jobs = result['jobs']
            candidate_roles = [job.get('role', 'Unknown') for job in raw_jobs]
            
            # Use the calculate_similarity function defined earlier
            valid_indices = calculate_similarity(target_role, candidate_roles)
            
            filtered_jobs = [raw_jobs[i] for i in valid_indices]
            
            print(f"    🧹 Hybrid Filter: Kept {len(filtered_jobs)}/{len(raw_jobs)} jobs.")
            result['jobs'] = filtered_jobs

        return result

    except Exception as e:
        print(f"    ❌ AI Process Error: {e}")
        return None

def research_company_news(company):
    """
    Searches SearXNG for recent news.
    """
    if not company: return "No company detected."
    
    query = f"{company} company achievements milestones news"
    # Uses SearXNG to get snippets
    results = search_logic.query_searxng(query, num_results=3)
    
    if not results: return "No recent news found."
    
    snippets = "\n".join([r.get('content', '') for r in results])
    
    prompt = PromptTemplate.from_template(
        """
        Summarize 2 key achievements or positive news items for {company} based on these search snippets.
        Keep it professional and concise (2 sentences max).
        Snippets: {snippets}
        """
    )
    chain = prompt | llm
    return chain.invoke({"company": company, "snippets": snippets}).content

def research_hiring_manager(name, company):
    """
    Searches for the hiring manager's public profile info.
    """
    if not name: return "Hiring Manager"
    
    query = f"{name} {company} linkedin"
    results = search_logic.query_searxng(query, num_results=1)

    print(f"Results:\n{results}\n")
    
    if not results: return name
    
    return f"{name} (Context: {results[0].get('content', '')})"

def generate_application_package(cv_text, job_data):
    """
    Generates CV, Cover Letter and Cold Email.
    """
    print(f"    ✍️ Generating Tailored CV...")
    cv_res = invoke_openrouter(
        prompt=f"""
        You are an expert Resume Writer. 
        
        TASK: Rewrite the User's CV to target the specific job below. Only output the full CV in Markdown format.
        
        CONSTRAINT 1: PRESERVE STRUCTURE. Keep the exact same sections, headers, and layout style as the original CV. Add linebreaks where needed.
        CONSTRAINT 2: FOCUS ON RELEVANCE. Only include experiences, skills, and achievements that are relevant to the target job. Remove unrelated content.
        CONSTRAINT 3: OPTIMIZE CONTENT. Rewrite the bullet points and summary to highlight skills relevant to the job description. Use keywords from the job.
        CONSTRAINT 4: DO NOT HALLUCINATE. Do not invent experiences. Only rephrase existing ones to match the target role.
        
        ORIGINAL CV:
        {cv_text}
        
        TARGET JOB DESCRIPTION:
        Role: {job_data.get('job_title', '')}
        Company: {job_data.get('company_name', '')}
        Requirements: {job_data.get('requirements', '')}
        Responsibilities: {job_data.get('responsabilities', '')}
        
        OUTPUT:
        Return the full Rewritten CV in clean Markdown format.
"""
        )

    print(f"    ✍️ Generating Cover Letter...")
    cl_res = invoke_openrouter(
        prompt=f"""
        You are an expert career coach and copywriter. Write a highly tailored cover letter. Output only full letter.
        
        MY RESUME: {cv_text}
        
        TARGET JOB DETAILS:
        Role: {job_data.get('job_title', '')} at {job_data.get('company_name', '')}
        Key Requirements: {job_data.get('requirements', '')}
        
        INSTRUCTIONS:
        - Professional tone.
        - Connect my experience directly to their requirements.
        - Keep it under 350 words.
        - Do NOT include placeholders like [Manager Name], just use "Hiring Manager".
"""
        )
    
    print(f"    ✍️ Generating Email...")
    em_res = invoke_openrouter(
        prompt=f"""
        Write a short cold email (subject + body) applying for:
        {job_data.get('job_title','')} at {job_data.get('company_name','')}.
        
        Highlight my top 3 matching skills based on: {job_data.get('requirements','')}.
        Keep it concise (<100 words).
        Output only the full email with subject line.
"""
    )

    return {
        "tailored_cv": cv_res.content,
        "cover_letter": cl_res.content,
        "email": em_res.content
    }


    # cl_prompt = PromptTemplate.from_template(
    #     """
    #     You are an expert career coach and copywriter. Write a highly tailored cover letter.
        
    #     MY RESUME: {cv}
        
    #     TARGET JOB DETAILS:
    #     Role: {role} at {company}
    #     Hiring Manager context: {manager}
    #     Company Recent News: {news}
    #     Key Requirements: {requirements}
        
    #     INSTRUCTIONS:
    #     1. Use a professional but enthusiastic tone.
    #     2. Address the hiring manager by name if provided.
    #     3. Mention the company's recent news/achievements to show deep research.
    #     4. Explicitly map my skills (from CV) to their requirements.
    #     5. Keep it under 400 words.
    #     """
    # )
    
    # email_prompt = PromptTemplate.from_template(
    #     """
    #     Write a short, punchy cold email to send my application to {manager}.
        
    #     Role: {role} @ {company}
    #     My Top Skill match: {requirements}
        
    #     Keep it under 150 words. Subject line included.
    #     """
    # )
    
    # cl_chain = cl_prompt | llm
    # em_chain = email_prompt | llm
    
    # # Extract fields safely
    # role = job_data.get('role', 'Target Role')
    # company = job_data.get('company', 'Target Company')
    # reqs = str(job_data.get('requirements', []))
    
    # # Generate content
    # cl_res = cl_chain.invoke({
    #     "cv": cv[:4000],
    #     "role": role,
    #     "company": company,
    #     "manager": manager_info,
    #     "news": company_news,
    #     "requirements": reqs
    # })
    
    # em_res = em_chain.invoke({
    #     "role": role,
    #     "company": company,
    #     "manager": manager_info,
    #     "requirements": reqs
    # })
    
    return cl_res.content, em_res.content