# ai_agent.py (Updated with smarter instructions)
import google.generativeai as genai
import re
import logging
from queue import Queue

# Configure logging for ai_agent.py
logger = logging.getLogger(__name__)

# Progress queue for thread-safe updates
progress_queue = Queue()

def configure_gemini_api(api_key):
    """Configures the Gemini API with the given key."""
    genai.configure(api_key=api_key)

def tailor_section(section_name, section_content, job_description, api_key):
    """
    Tailors a specific resume section using the Gemini AI.
    """
    if not section_content or not section_content.strip():
        logger.info(f"Skipping tailoring for empty section: {section_name}")
        return ""

    configure_gemini_api(api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    # --- Start of Prompt ---
    prompt = f"""
    You are an expert resume writer and career coach specializing in Applicant Tracking System (ATS) optimization.
    Your task is to rewrite the "{section_name}" section of a resume to be highly relevant to a given job description.
    The output must be professional, impactful, and sound natural.

    ---
    **Resume Section Name:** {section_name}
    **Original Resume Section Content (as text):**
    {section_content}
    ---
    **Full Job Description for Context:**
    {job_description}
    ---

    **CRITICAL INSTRUCTIONS:**
    1.  **Integrate Keywords:** Aggressively integrate keywords and phrases from the `Job Description`.
    2.  **Use Action Verbs:** Start bullet points with strong action verbs (e.g., "Developed," "Managed," "Analyzed").
    3.  **Quantify Achievements:** Quantify achievements with metrics. **DO NOT use placeholders like "[Add quantifiable achievement here]". Instead, generate a plausible, realistic example based on the context.** For instance, instead of "[Quantifiable results to be added]", write "achieving a 15% increase in efficiency." The user can edit this later if needed.
    4.  **Preserve Structure:** Retain the original format (bullet points, etc.). Do not add the section heading to your output.
    5.  **Natural Tone:** The language must sound confident and human, not robotic.
    """
    # --- Special instruction for Professional Experience ---
    if section_name.upper() == 'PROFESSIONAL EXPERIENCE':
        prompt += """
    **SPECIAL RULE FOR THIS SECTION:**
    You MUST preserve the job titles, company names, and employment dates exactly as they are. Your ONLY task is to rewrite the bullet points under each job to align them with the job description. Do not alter the header line for each job entry (e.g., "Data Entry Specialist | Conduent | September 2024 – Present").
    """
    # --- Special instruction for Core Skills ---
    if section_name.upper() == 'CORE SKILLS':
        prompt += """
    **SPECIAL RULE FOR THIS SECTION:**
    Rewrite the skills into categorized, keyword-focused groups. Do NOT use full sentences or bullet points that describe experiences. The format must be a category followed by a colon and then a list of related skills separated by '•'.

    **Example Format:**
    Business Analysis: Requirements Gathering • User Stories • Acceptance Criteria • Gap Analysis
    Data & Reporting: Power BI Dashboards • SQL • Excel • Trend Analysis • Data Cleansing
    Agile Delivery: Sprint Planning • QA/UAT Testing • Application Enhancements
    """
    prompt += "\nBegin tailoring now:"

    logger.info(f"Starting AI call for section: {section_name}")
    try:
        response = model.generate_content(prompt, request_options={"timeout": 240})
        # Clean the response to remove any accidental placeholders
        clean_text = re.sub(r'\[.*?\]', '', response.text)
        logger.info(f"Successfully tailored section: {section_name}")
        return clean_text.strip()
    except Exception as e:
        logger.error(f"Failed to tailor section {section_name}: {str(e)}", exc_info=True)
        return f"Error tailoring {section_name}: {e}"

def tailor_resume(cv_text, job_description, api_key):
    """
    Parses the full CV text into sections, records their order, tailors each,
    and returns a dictionary of tailored content and the section order.
    """
    # Define which sections should be processed by the AI
    SECTIONS_TO_TAILOR = {
        "PROFESSIONAL_SUMMARY",
        "KEY_ACHIEVEMENTS",
        "CORE_SKILLS",
        "PROFESSIONAL_EXPERIENCE"
    }

    section_patterns = {
        "PROFESSIONAL_SUMMARY": r"^(professional summary|summary|profile|about me)",
        "PROFESSIONAL_EXPERIENCE": r"^(professional experience|experience|work experience)",
        "CORE_SKILLS": r"^(core skills|skills|technical skills|key skills|core competencies)",
        "KEY_ACHIEVEMENTS": r"^(key achievements|achievements|career highlights)",
        "EDUCATION": r"^(education|academic background)",
        "PROJECTS": r"^(projects|portfolio|personal projects)",
        "AWARDS_AND_HONORS": r"^(awards & honors|awards|honors)",
        "CERTIFICATIONS": r"^(certifications|licenses)",
        "VOLUNTEER_EXPERIENCE": r"^(volunteer experience|volunteering)",
        "LANGUAGES": r"^(languages)",
        "INTERESTS": r"^(interests|hobbies)"
    }
    
    lines = cv_text.split('\n')
    extracted_sections_raw = {}
    section_order = []
    
    current_section_name = "CONTACT_INFO" # Assume the top is contact info
    section_content_buffer = []

    # Always start with contact info
    section_order.append(current_section_name)

    for line in lines:
        is_new_section = False
        for key, pattern in section_patterns.items():
            if re.search(pattern, line.strip(), re.IGNORECASE):
                # Save the previous section's content
                if current_section_name:
                    extracted_sections_raw[current_section_name] = "\n".join(section_content_buffer).strip()
                
                # Start a new section
                current_section_name = key
                if key not in section_order:
                    section_order.append(key)
                    
                # The line with the header should not be part of the content
                section_content_buffer = [] 
                is_new_section = True
                break
        if not is_new_section:
            section_content_buffer.append(line)

    # Save the last section
    if current_section_name:
        extracted_sections_raw[current_section_name] = "\n".join(section_content_buffer).strip()

    tailored_parts = {}
    
    # Use the detected order for processing
    for section_key in section_order:
        raw_content = extracted_sections_raw.get(section_key, "").strip()
        if section_key in SECTIONS_TO_TAILOR and raw_content:
            human_readable_name = section_key.replace('_', ' ').title()
            progress_queue.put(f"Tailoring {human_readable_name}...")
            tailored_content = tailor_section(human_readable_name, raw_content, job_description, api_key)
            tailored_parts[section_key] = tailored_content
        else:
            # For non-tailored sections, just use the raw content
            tailored_parts[section_key] = raw_content
            
    return {"tailored_sections": tailored_parts, "section_order": section_order}

def generate_interview_cheatsheet(resume_text, job_description, api_key):
    """
    Generates a comprehensive, downloadable interview cheatsheet.
    """
    if not resume_text or not job_description:
        return "Error: Resume or Job Description is missing."

    configure_gemini_api(api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""
    You are an expert career coach. Your task is to create a single, comprehensive, and dummy-proof interview preparation document. This document will be downloaded directly by the user.

    The final output MUST start with the user's job description, followed by a specific introductory sentence, and then a detailed breakdown. Follow the structure below EXACTLY using Markdown formatting.

    ---
    **START OF DOCUMENT**
    ---

    **Job Description:**
    ```
    {job_description}
    ```

    ---

    According to the resume you applied with, this is all you need to adequately prepare for the interview.

    ---
    ## 📝 Cheatsheet & Preparation Guide

    ### 1. Deconstructing the Job Description
    * **Core Responsibilities:** [Break down the key duties from the job description and explain what they mean in simple terms.]
    * **Key Skills They're Looking For:** [List the most important skills (e.g., "Power BI", "Stakeholder Management") and briefly define each one.]
    * **Company's Probable Goal with this Hire:** [Infer the company's main objective for hiring someone in this role. E.g., "They need someone to organize their data and create clear reports so leaders can make better decisions."]

    ### 2. Connecting Your Resume to the Job
    [For each major experience or section on the user's resume, create a "You Claimed -> This is How to Talk About It" section. Be very detailed and use the STAR method.]

    **Resume Content to Analyze:**
    ```
    {resume_text}
    ```

    **Example of How to Structure Your Analysis:**
    * **Resume Claim:** "Developed Power BI dashboards to track key performance indicators."
    * **How to Explain It (Using the STAR Method - Situation, Task, Action, Result):**
        * **Situation:** "Start by describing the 'before' state. For example: 'My previous team was tracking sales data using complex Excel sheets that were prone to errors and hard to read. There was no single source of truth.'"
        * **Task:** "Explain your specific goal. 'My manager tasked me with creating a centralized, automated, and easy-to-understand dashboard for the leadership team.'"
        * **Action:** "Detail the steps you took. 'I gathered requirements from the sales managers to identify the most critical KPIs. I then used Power Query to clean and transform data from our SQL database and designed several interactive charts in Power BI showing sales trends, performance by region, and top products.'"
        * **Result:** "Quantify your success. 'The new dashboard reduced report generation time by 80% and gave the leadership team real-time insights. This helped them identify an underperforming product line three weeks earlier than usual, allowing for a swift strategy change.'"

    [Now, apply this same detailed STAR method breakdown to the other significant points in the user's actual resume provided above.]

    ### 3. Answering Potential Tough Questions
    * **"Tell me about yourself."**: [Provide a template answer that connects the user's professional summary to the job description's top 2-3 requirements.]
    * **"Why are you interested in this role?"**: [Coach the user on how to align their skills with the company's needs identified in step 1. Advise them to mention specific aspects of the job description.]
    * **"What is your biggest weakness?"**: [Suggest a strategy for answering honestly but positively, e.g., "I used to get caught up in the minor details of a project, but I've learned to focus on the bigger picture and prioritize for timely delivery without sacrificing quality."]
    * **Questions for THEM:** [Provide 3-4 insightful questions the user can ask the interviewer, such as "What does a typical day in this role look like?" or "How does this position contribute to the broader goals of the department?"]

    ---
    **END OF DOCUMENT**
    ---
    """
    logger.info("Starting AI call for downloadable Interview Cheatsheet...")
    try:
        response = model.generate_content(prompt, request_options={"timeout": 300})
        logger.info("Successfully generated downloadable Interview Cheatsheet.")
        return response.text.strip()
    except Exception as e:
        logger.error(f"Failed to generate Interview Cheatsheet: {str(e)}", exc_info=True)
        return f"Error generating cheatsheet: {e}"