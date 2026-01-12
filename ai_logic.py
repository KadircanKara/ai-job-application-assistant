import os
from openai import OpenAI
from dotenv import load_dotenv


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