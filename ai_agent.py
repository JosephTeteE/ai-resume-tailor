# ai_agent.py
"""
AI Agent module for generating resume content using multiple LLM providers.
Handles API calls, failover logic, and response processing.
"""

import os
import logging
import json
import openai
import cohere
import google.generativeai as genai
import requests
from prompts import (
    get_title_extraction_prompt, 
    get_master_resume_prompt,
    get_cover_letter_prompt, 
    get_cheatsheet_prompt
)

logger = logging.getLogger(__name__)

def _call_openai_compatible_api(prompt, base_url, api_key, model, json_mode=False):
    """Generic function to call any OpenAI-compatible API endpoint."""
    client = openai.OpenAI(base_url=base_url, api_key=api_key)
    
    # Truncate prompt if exceeds length limit
    if len(prompt) > 7000:
        prompt = prompt[:7000] + "\n...[CONTENT TRUNCATED TO FIT LENGTH LIMIT]"
    
    response_format_arg = {"type": "json_object"} if json_mode else {"type": "text"}
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            timeout=180,
            response_format=response_format_arg
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"API call failed: {e}")
        raise

def _get_groq_response(prompt, json_mode=False):
    """Execute API call to Groq's LLM endpoint."""
    return _call_openai_compatible_api(
        prompt=prompt,
        base_url="https://api.groq.com/openai/v1",
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama3-8b-8192",
        json_mode=json_mode
    )

def _get_fireworks_response(prompt, json_mode=False):
    """Execute API call to Fireworks.ai's LLM endpoint."""
    return _call_openai_compatible_api(
        prompt=prompt,
        base_url="https://api.fireworks.ai/inference/v1",
        api_key=os.getenv("FIREWORKS_API_KEY"),
        model="accounts/fireworks/models/llama-v3-8b-instruct",
        json_mode=json_mode
    )

def _get_gemini_response(prompt, json_mode=False):
    """Execute API call to Google's Gemini model."""
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    if len(prompt) > 7000:
        prompt = prompt[:7000] + "\n...[CONTENT TRUNCATED TO FIT LENGTH LIMIT]"
    
    if json_mode:
        prompt += "\n\nRespond with only valid JSON between ```json``` markers."
        
    try:
        response = model.generate_content(prompt, request_options={"timeout": 180})
        return response.text
    except Exception as e:
        logger.error(f"Gemini API failed: {e}")
        raise

def _get_huggingface_response(prompt, json_mode=False):
    """Execute API call to Hugging Face inference endpoint."""
    api_url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
    headers = {"Authorization": f"Bearer {os.getenv('HUGGINGFACE_API_KEY')}"}
    
    if len(prompt) > 7000:
        prompt = prompt[:7000] + "\n...[CONTENT TRUNCATED TO FIT LENGTH LIMIT]"
    
    if json_mode:
        prompt += "\n\nRespond with only valid JSON output."
    
    try:
        response = requests.post(api_url, headers=headers, json={"inputs": prompt}, timeout=180)
        response.raise_for_status()
        return response.json()[0]['generated_text'][len(prompt):]
    except Exception as e:
        logger.error(f"Hugging Face API failed: {e}")
        raise

def _get_cohere_response(prompt, json_mode=False):
    """Execute API call to Cohere's LLM endpoint."""
    client = cohere.Client(os.getenv("COHERE_API_KEY"))
    
    if len(prompt) > 7000:
        prompt = prompt[:7000] + "\n...[CONTENT TRUNCATED TO FIT LENGTH LIMIT]"
    
    if json_mode:
        prompt += "\n\nRespond with only valid JSON output."
    
    try:
        response = client.chat(message=prompt, model="command-r")
        return response.text
    except Exception as e:
        logger.error(f"Cohere API failed: {e}")
        raise

def get_ai_response(prompt, json_mode=False, start_index=0):
    """
    Orchestrate API calls across multiple providers with failover logic.
    
    Args:
        prompt: The input prompt for the LLM
        json_mode: Whether to expect JSON response
        start_index: Which provider to try first
        
    Returns:
        str: The generated content or error message
    """
    providers = [
        ("Groq", _get_groq_response),
        ("Google Gemini", _get_gemini_response),
        ("Hugging Face", _get_huggingface_response),
        ("Fireworks.ai", _get_fireworks_response),
        ("Cohere", _get_cohere_response)
    ]
    
    # Rotate providers based on start index
    for provider_name, provider_func in providers[start_index:] + providers[:start_index]:
        try:
            logger.info(f"Attempting provider: {provider_name}")
            response = provider_func(prompt, json_mode)
            if response and "Error:" not in response:
                return response
        except Exception as e:
            logger.warning(f"{provider_name} failed: {e}")
    
    logger.error("All providers failed")
    return "Error: All AI providers failed. Please check your API keys and network connection."

def extract_job_title(job_title, job_description):
    """
    Extract standardized job title from user input and description.
    
    Args:
        job_title: User-provided job title
        job_description: Full job description text
        
    Returns:
        str: Cleaned and standardized job title
    """
    if not job_description:
        return job_title
        
    try:
        prompt = get_title_extraction_prompt(job_title, job_description)
        response = get_ai_response(prompt)
        return response.strip().replace('"', '') if "Error:" not in response else job_title
    except Exception as e:
        logger.error(f"Title extraction failed: {e}")
        return job_title

def _parse_json_from_ai_response(response_text):
    """
    Safely extract JSON from potentially malformed AI response.
    
    Args:
        response_text: Raw text response from AI
        
    Returns:
        dict: Parsed JSON data or None if invalid
    """
    try:
        start = response_text.find('{')
        end = response_text.rfind('}')
        if start >= 0 and end > start:
            return json.loads(response_text[start:end+1])
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed: {e}")
    return None

def generate_tailored_resume_data(job_description, job_title, start_provider_index=0):
    """
    Generate complete tailored resume content from job description.
    
    Args:
        job_description: The full job description text
        job_title: Target job title
        start_provider_index: Which AI provider to try first
        
    Returns:
        dict: Generated resume content or error dict
    """
    try:
        prompt = get_master_resume_prompt(job_title, job_description)
        response = get_ai_response(prompt, json_mode=True, start_index=start_provider_index)
        
        if "Error:" in response:
            return {"error": response}
            
        parsed = _parse_json_from_ai_response(response)
        if parsed and "skills" in parsed and "experience" in parsed:
            return parsed
        return {"error": "Invalid response structure from AI"}
    except Exception as e:
        logger.error(f"Resume generation failed: {e}")
        return {"error": str(e)}

def generate_cover_letter(final_resume_data, job_description, job_title, company_name, start_provider_index=0):
    """
    Generate tailored cover letter content.
    
    Args:
        final_resume_data: Processed resume data
        job_description: Target job description
        job_title: Official job title
        company_name: Target company name
        start_provider_index: Which AI provider to try first
        
    Returns:
        str: Generated cover letter text
    """
    prompt = get_cover_letter_prompt(final_resume_data, job_description, job_title, company_name)
    return get_ai_response(prompt, start_index=start_provider_index)

def generate_cheatsheet(final_resume_text, job_description, job_title, start_provider_index=0):
    """
    Generate interview preparation cheatsheet.
    
    Args:
        final_resume_text: Formatted resume text
        job_description: Target job description
        job_title: Official job title
        start_provider_index: Which AI provider to try first
        
    Returns:
        str: Generated cheatsheet content
    """
    prompt = get_cheatsheet_prompt(final_resume_text, job_description, job_title)
    return get_ai_response(prompt, start_index=start_provider_index)