# prompts.py
"""
Prompt engineering module containing all LLM prompt templates.
Designed to generate professional, standardized resume content.
"""

from config import MASTER_RESUME_DATA
from datetime import datetime

def get_title_extraction_prompt(job_title, job_description):
    """
    Generate prompt for extracting standardized job title.
    
    Args:
        job_title: Raw job title input
        job_description: Full job description
        
    Returns:
        str: Formatted prompt text
    """
    return f"""
    Analyze the job title and description below. Extract and return only the most 
    appropriate standardized job title. Do not include any additional text.
    
    Requirements:
    - Use only widely-recognized job titles
    - Match the seniority level implied by the description
    - Exclude company-specific terminology
    
    Job Title Input: "{job_title}"
    Job Description: "{job_description[:1000]}..."
    
    Standardized Job Title:
    """

def get_master_resume_prompt(job_title, job_description):
    """
    Generate main prompt for complete resume content generation.
    
    Args:
        job_title: Target job title
        job_description: Full job description
        
    Returns:
        str: Formatted prompt text with strict JSON requirements
    """
    companies = list(MASTER_RESUME_DATA["RELEVANT_EXPERIENCE_STATIC"].keys())
    
    return f"""
    Generate a complete, professional resume tailored for: {job_title}
    
    Requirements:
    1. ROLE TITLES:
       - Create 3 distinct but related positions
       - Example variations for {job_title}:
         - "Data Analyst", "Business Intelligence Analyst", "Research Analyst"
         - "Marketing Specialist", "Digital Strategist", "Content Manager"
       - No explicit seniority labels unless specified in description
    
    2. BULLET POINTS:
       - 30-50 words each
       - Show progressive skill development
       - Include specific tools/technologies
       - Quantify achievements
       - Follow: [Action] using [Tool] resulting in [Metric]
    
    3. OUTPUT FORMAT:
       - Strict JSON only
       - No additional text or commentary
       - Structure must exactly match:
    {{
      "skills": {{
        "technical": "comma, separated, hard, skills",
        "soft": "comma, separated, soft, skills"
      }},
      "experience": {{
        "{companies[0]}": {{
          "role": "Professional Title Variation 1",
          "bullets": [
            "Achievement statement 1",
            "Achievement statement 2",
            "Achievement statement 3",
            "Achievement statement 4"
          ]
        }},
        "{companies[1]}": {{
          "role": "Professional Title Variation 2",
          "bullets": [
            "Achievement statement 1",
            "Achievement statement 2",
            "Achievement statement 3",
            "Achievement statement 4"
          ]
        }},
        "{companies[2]}": {{
          "role": "Professional Title Variation 3",
          "bullets": [
            "Achievement statement 1",
            "Achievement statement 2",
            "Achievement statement 3",
            "Achievement statement 4"
          ]
        }}
      }}
    }}
    
    Job Description Excerpt:
    "{job_description[:2500]}..."
    
    Begin JSON Resume Content:
    """

def get_cover_letter_prompt(final_resume_data, job_description, job_title, company_name):
    """
    Generate prompt for professional cover letter creation.
    
    Args:
        final_resume_data: Processed resume content
        job_description: Target job description
        job_title: Official job title
        company_name: Target company name
        
    Returns:
        str: Formatted prompt text
    """
    education = MASTER_RESUME_DATA['EDUCATION'][0]
    first_job = MASTER_RESUME_DATA["RELEVANT_EXPERIENCE_STATIC"]["Mangrove & Partners Ltd"]["dates"].split(' – ')[0]
    experience_years = datetime.now().year - datetime.strptime(f"01 {first_job}", "%d %b %Y").year - 1
    
    return f"""
    Compose a professional cover letter (4 paragraphs) with:
    
    CANDIDATE PROFILE:
    - Name: {MASTER_RESUME_DATA['CONTACT_INFO']['name']}
    - Education: Pursuing {education['degree']} (Expected {education['dates'].split(': ')[1]})
    - Experience: {experience_years} years in relevant roles
    
    JOB TARGET:
    - Position: {job_title} at {company_name}
    - Key Requirements: "{job_description[:600]}..."
    
    STRUCTURE:
    1. Opening: Concise value proposition
    2. Qualifications: Top 3 relevant strengths
    3. Company Fit: Alignment with organization
    4. Closing: Confident call to action
    
    REQUIREMENTS:
    - 180-220 words total
    - Professional tone
    - Incorporate resume achievements
    - No placeholders
    
    Begin Cover Letter Content:
    """

def get_cheatsheet_prompt(final_resume_text, job_description, job_title):
    """
    Generate prompt for interview preparation cheatsheet.
    
    Args:
        final_resume_text: Formatted resume content
        job_description: Target job description
        job_title: Official job title
        
    Returns:
        str: Formatted prompt text
    """
    return f"""
    Create an interview preparation guide with these sections:
    
    1. ELEVATOR PITCH (30-40 words):
       - Blend your strengths with role requirements
    
    2. ACHIEVEMENT CONTEXT:
       - For each resume bullet point:
         • Explain the business context
         • Detail your specific contribution
    
    3. STAR STORIES (2 examples):
       - Situation: Organizational context
       - Task: Specific challenge
       - Action: Steps you took
       - Result: Quantified outcome
    
    4. INTELLIGENT QUESTIONS (3 items):
       - Team dynamics inquiry
       - Success metrics question
       - Future challenges query
    
    RESUME CONTENT:
    {final_resume_text}
    
    JOB DESCRIPTION:
    {job_description}
    
    Begin Interview Guide:
    """