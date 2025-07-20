# ai_agent.py
import os
import logging
import openai
import cohere
import google.generativeai as genai
from config import MASTER_RESUME_DATA

# Setup logger for this module
logger = logging.getLogger(__name__)

# --- Provider-Specific API Functions ---
# Each function is responsible for calling a single AI provider's API.

def _get_groq_response(prompt):
    """Gets a response from Groq's API using the OpenAI SDK."""
    client = openai.OpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role": "user", "content": prompt}],
        timeout=180
    )
    return response.choices[0].message.content

def _get_gemini_response(prompt):
    """Gets a response from Google's Gemini API."""
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt, request_options={"timeout": 180})
    return response.text

def _get_fireworks_response(prompt):
    """Gets a response from Fireworks.ai's API using the OpenAI SDK."""
    client = openai.OpenAI(base_url="https://api.fireworks.ai/inference/v1", api_key=os.getenv("FIREWORKS_API_KEY"))
    response = client.chat.completions.create(
        model="accounts/fireworks/models/mixtral-8x7b-instruct",
        messages=[{"role": "user", "content": prompt}],
        timeout=180
    )
    return response.choices[0].message.content

def _get_cohere_response(prompt):
    """Gets a response from Cohere's API."""
    client = cohere.Client(os.getenv("COHERE_API_KEY"))
    response = client.chat(message=prompt, model="command-r")
    return response.text

# --- Master Failover Wrapper ---
def get_ai_response(prompt):
    """
    Attempts to get a response from a series of AI providers in a specific order.
    This creates a resilient system that can handle API quota limits or downtime.
    """
    # 1. Primary: Groq (Fastest)
    try:
        logger.info("Attempting provider: Groq")
        return _get_groq_response(prompt)
    except Exception as e:
        logger.warning(f"Groq failed: {e}. Failing over...")

    # 2. Fallback: Gemini (Generous & Reliable)
    try:
        logger.info("Attempting provider: Gemini")
        return _get_gemini_response(prompt)
    except Exception as e:
        logger.warning(f"Gemini failed: {e}. Failing over...")

    # 3. Fallback: Fireworks.ai (Solid Alternative)
    try:
        logger.info("Attempting provider: Fireworks.ai")
        return _get_fireworks_response(prompt)
    except Exception as e:
        logger.warning(f"Fireworks.ai failed: {e}. Failing over...")

    # 4. Final Fallback: Cohere
    try:
        logger.info("Attempting provider: Cohere")
        return _get_cohere_response(prompt)
    except Exception as e:
        logger.error(f"All providers failed. Final error from Cohere: {e}")
        return "Error: AI generation failed. Please try again later."

# --- Tailoring Functions ---
# These functions use the AI response to tailor resume sections based on job descriptions.

def _tailor_skills(job_description, job_title):
    """Generates a highly optimized SKILLS section."""

    prompt = f"""
    Task: Generate a 'SKILLS' section for a resume that is hyper-optimized for the following job description.

    ### Target Job Description
    "{job_description}"

    ### INSTRUCTIONS
    1.  **Keyword Extraction:** Meticulously scan the job description and extract the most important technical and soft skills mentioned.
    2.  **Formatting:** Your output MUST contain exactly two lines.
        - The first line MUST begin with "Technical Skills: ".
        - The second line MUST begin with "Soft Skills: ".
    3.  **Prohibitions:** DO NOT use Markdown. DO NOT add any conversational text.
    """
    response_text = get_ai_response(prompt)
    if "Error:" in response_text:
        return {"technical": "Error generating skills.", "soft": "Please try again."}
    try:
        technical = response_text.split("Technical Skills:")[1].split("Soft Skills:")[0].strip()
        soft = response_text.split("Soft Skills:")[1].strip()
        return {"technical": technical, "soft": soft}
    except IndexError:
        logger.error(f"Failed to parse skills from AI response: {response_text}")
        return {"technical": "AI response format error.", "soft": "Please try again."}

def _tailor_experience_for_company(company_name, static_details, job_description, job_title):
    """Generates a tailored job title and powerfully optimized bullet points."""
    original_bullets_str = "\n".join(f"- {b}" for b in static_details['original_bullets'])

    prompt = f"""
    You are a world-class resume writing AI. Your sole objective is to transform the candidate's duties into powerful, quantified, results-driven achievements that are irresistible to recruiters.

    ### CONTEXT
    - **Target Job:** "{job_title}"
    - **This Past Job:** at **{company_name}**.
    - **Candidate's Original Duties:**
    {original_bullets_str}

    ### INSTRUCTIONS
    1.  **Create a Varied, Relevant Job Title:** Generate a plausible job title that is highly relevant to the target "{job_title}" role but also distinct from other roles.
    2.  **Write Powerfully Optimized Bullet Points:** Write exactly three (3) detailed bullet points.
        - Each bullet point MUST start with a strong action verb (e.g., Orchestrated, Spearheaded, Revitalized, Streamlined).
        - **Aggressively quantify** every possible achievement. If no metric is provided, invent a plausible and impressive one (e.g., '...resulting in a 15% increase in efficiency,' '...handling over 500+ daily inquiries,' '...reducing processing time by 2 days').
        - Strategically weave in keywords from the target job description naturally.
        - Clearly state the **IMPACT** or **RESULT** of the action in each bullet point.

    ### ABSOLUTE OUTPUT FORMAT
    Your entire response MUST be exactly 4 lines. No more, no less.
    Line 1: The tailored job title ONLY.
    Line 2: The first bullet point, starting with '• '.
    Line 3: The second bullet point, starting with '• '.
    Line 4: The third bullet point, starting with '• '.

    ### PROHIBITIONS
    - **DO NOT** use any Markdown formatting (like `**bold**` or `*italics*`) in your output.
    - DO NOT write any introduction or conversational text.
    - DO NOT add any extra blank lines.
    """
    response_text = get_ai_response(prompt)
    
    lines = [line.strip() for line in response_text.strip().split('\n') if line.strip()]
    if len(lines) != 4:
        logger.error(f"Invalid response format from AI for {company_name}. Expected 4 lines, got {len(lines)}. Response: '{response_text}'")
        return { "role": job_title, "bullets": static_details['original_bullets'][:3] }
    
    return { "role": lines[0], "bullets": [line.lstrip('•').strip() for line in lines[1:4]] }


def generate_tailored_resume_data(job_description, job_title):
    """Orchestrates the AI tailoring for all dynamic sections."""
    logger.info("Starting resume data tailoring process with failover logic.")
    tailored_skills = _tailor_skills(job_description, job_title)
    tailored_experience = {}
    static_experience = MASTER_RESUME_DATA["RELEVANT_EXPERIENCE_STATIC"]
    for company, static_details in static_experience.items():
        tailored_experience[company] = _tailor_experience_for_company(company, static_details, job_description, job_title)
    logger.info("Finished resume data tailoring.")
    return {"skills": tailored_skills, "experience": tailored_experience}

def generate_cover_letter(resume_data, job_description, job_title, company_name=""):
    """Generates a tailored cover letter using AI."""
    prompt = f"""
    Write a professional cover letter for {MASTER_RESUME_DATA['CONTACT_INFO']['name']} applying to {company_name or "a company"} as a {job_title}.

    Resume Highlights:
    - Skills: {resume_data['skills']['technical']}
    - Experience: {len(MASTER_RESUME_DATA['RELEVANT_EXPERIENCE_STATIC'])} relevant positions

    Job Requirements:
    {job_description}

    Format Requirements:
    - 3-4 concise paragraphs
    - Reference specific skills from the resume
    - Length: 200-300 words
    - Tone: Professional yet approachable
    """
    return get_ai_response(prompt)

def generate_cheatsheet(final_resume_text, job_description, job_title):
    """Generates a comprehensive interview cheatsheet."""
    logger.info("Generating interview cheatsheet...")
    prompt = f"""
    As an expert career coach, create a personalized interview cheatsheet based on the user's tailored resume and the target job description. The tone should be encouraging and strategic. Format the output using Markdown.

    **Job Title:** {job_title}

    **User's Tailored Resume:**
    ---
    {final_resume_text}
    ---

    **Job Description:**
    ---
    {job_description}
    ---

    **Instructions:**
    Create a cheatsheet with the following sections:

    ### 1. Deconstructing the Job Description
    - **Key Responsibilities:** Identify the top 3-4 responsibilities from the job description.
    - **Must-Have Skills:** List the most critical technical and soft skills mentioned.
    - **Nice-to-Have Skills:** List any secondary skills or qualifications.

    ### 2. Connecting Your Resume to the Role
    Create a table that maps 3 key requirements from the job description to specific achievements on the resume. Explain *why* the achievement is relevant.
    | Job Requirement | Your Relevant Achievement | Why It Matters |
    |---|---|---|
    | [Requirement 1] | [Relevant bullet point from resume] | [Brief explanation] |
    | [Requirement 2] | [Relevant bullet point from resume] | [Brief explanation] |
    | [Requirement 3] | [Relevant bullet point from resume] | [Brief explanation] |

    ### 3. STAR Method Story Bank
    Based on the resume's achievements, develop two powerful and concise example stories using the STAR method (Situation, Task, Action, Result).
    - **Story 1: (Name of a key achievement, e.g., "Improving Reporting Efficiency")**
      - **Situation:**
      - **Task:**
      - **Action:**
      - **Result:**
    - **Story 2: (Name of another key achievement)**
      - **Situation:**
      - **Task:**
      - **Action:**
      - **Result:**

    ### 4. Questions to Ask Them
    Suggest 2-3 insightful questions the user can ask the interviewer about the role, team, or company challenges that demonstrate their engagement and expertise.
    """
    return get_ai_response(prompt)