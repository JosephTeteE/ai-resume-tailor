# app.py
import streamlit as st
import os
import re
from dotenv import load_dotenv
import logging

load_dotenv()

from ai_agent import generate_tailored_resume_data, generate_cheatsheet, generate_cover_letter
from utils import create_final_docx
from config import MASTER_RESUME_DATA

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Page Config ---
st.set_page_config(layout="wide", page_title="AI Resume Tailor")
st.title("📄 AI-Powered Resume Tailor")

# --- Helper Functions ---
def assemble_content_string(tailored_data):
    """Assembles a simple string representation for the cheatsheet prompt."""
    content_parts = []
    contact = MASTER_RESUME_DATA['CONTACT_INFO']
    content_parts.append(f"{contact['name']}\n{contact['details']}")
    content_parts.append("\nEDUCATION")
    for edu in MASTER_RESUME_DATA['EDUCATION']:
        content_parts.append(f"{edu['institution']}\n{edu['degree']}\n{edu['courses']}")
    content_parts.append("\nRELEVANT EXPERIENCE")
    static_exp = MASTER_RESUME_DATA['RELEVANT_EXPERIENCE_STATIC']
    for company in static_exp:
        role = tailored_data['experience'][company]['role']
        bullets = "\n".join([f"• {b}" for b in tailored_data['experience'][company]['bullets']])
        content_parts.append(f"\n{company}\n{role}\n{bullets}")
    content_parts.append(f"\nAWARD: {MASTER_RESUME_DATA['AWARD']}")
    skills = tailored_data['skills']
    content_parts.append(f"\nSKILLS:\nTechnical Skills: {skills['technical']}\nSoft Skills: {skills['soft']}")
    
    # --- Organizations ---
    org_data = MASTER_RESUME_DATA['ORGANIZATIONS']
    content_parts.append(f"\nORGANIZATIONS\n{org_data['role']}\t{org_data['dates']}")
    
    return "\n".join(content_parts)

def slugify(text):
    """Converts a string into a URL-friendly slug for filenames."""
    text = str(text).strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'\s+', '_', text)
    text = re.sub(r'_{2,}', '_', text)
    return text.strip('_').lower()

# --- Main UI ---
st.subheader("1. Provide Job Details")
job_title = st.text_input("Enter the Job Title (e.g., Data Analyst)")
company_name = st.text_input("Company Name (optional)", "")
job_description = st.text_area("Paste the full job description here:", height=250)

# Cover letter toggle
include_cover_letter = st.toggle("Include Cover Letter", value=False)

# --- Resume Generation Button ---
if st.button("🚀 Generate Resume!", use_container_width=True, type="primary", key="generate_resume"):
    if job_description and job_title:
        with st.spinner("✨ Tailoring your resume with AI... This may take a moment."):
            # Clear previous state
            keys_to_clear = ['tailored_data', 'cover_letter', 'cheatsheet']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            
            # Store current input
            st.session_state.job_title = job_title
            st.session_state.company_name = company_name
            st.session_state.job_description = job_description
            
            # Generate resume data
            st.session_state.tailored_data = generate_tailored_resume_data(job_description, job_title)
            
            # Generate cover letter only if toggle is on
            if include_cover_letter and company_name:
                with st.spinner("📝 Crafting your cover letter..."):
                    st.session_state.cover_letter = generate_cover_letter(
                        st.session_state.tailored_data,
                        job_description,
                        job_title,
                        company_name
                    )
    else:
        st.warning("Please provide both the Job Title and the Job Description.")

# --- If Resume is Generated ---
if 'tailored_data' in st.session_state:
    st.subheader("2. Download Your Tailored Resume")
    try:
        docx_bytes = create_final_docx(st.session_state.tailored_data)
        
        # Create filename
        base_name = "Aye_Uweja"
        file_slug = slugify(f"{st.session_state.job_title}_{st.session_state.company_name}" 
                          if st.session_state.company_name 
                          else st.session_state.job_title)

        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.download_button(
                label="⬇️ Download Resume as DOCX",
                data=docx_bytes,
                file_name=f"{base_name}_{file_slug}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                key="resume_download"
            )

            if st.button("🔄 Generate Another Resume", 
                        use_container_width=True,
                        key="reset_button"):
                keys_to_clear = ['job_title', 'company_name', 'job_description', 
                                'tailored_data', 'cover_letter', 'cheatsheet']
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

        # --- Cover Letter Section ---
        if include_cover_letter:
            if 'cover_letter' not in st.session_state and company_name:
                if st.button("📝 Generate Cover Letter",
                            use_container_width=True,
                            key="cover_letter_button"):
                    with st.spinner("Crafting your cover letter..."):
                        st.session_state.cover_letter = generate_cover_letter(
                            st.session_state.tailored_data,
                            st.session_state.job_description,
                            st.session_state.job_title,
                            st.session_state.company_name
                        )
            
            if 'cover_letter' in st.session_state:
                st.markdown("---")
                st.subheader("Cover Letter")
                with st.expander("View Your Tailored Cover Letter", expanded=True):
                    st.write(st.session_state.cover_letter)
                    st.download_button(
                        label="⬇️ Download Cover Letter",
                        data=st.session_state.cover_letter.encode('utf-8'),
                        file_name=f"Cover_Letter_{file_slug}.txt",
                        mime="text/plain",
                        use_container_width=True,
                        key="cover_download"
                    )

        # --- Cheatsheet Section ---
        st.markdown("---")
        st.subheader("3. Interview Preparation")
        
        if st.button("🧠 Generate Interview Cheatsheet", 
                    type="secondary", 
                    use_container_width=True,
                    key="cheatsheet_button"):
            with st.spinner("✨ Creating your personalized cheatsheet..."):
                resume_content = assemble_content_string(st.session_state.tailored_data)
                st.session_state.cheatsheet = generate_cheatsheet(
                    resume_content,
                    st.session_state.job_description,
                    st.session_state.job_title
                )
        
        if 'cheatsheet' in st.session_state:
            with st.expander("Your Interview Cheatsheet", expanded=True):
                st.markdown(st.session_state.cheatsheet, unsafe_allow_html=True)
                st.download_button(
                    label="⬇️ Download Cheatsheet",
                    data=st.session_state.cheatsheet.encode('utf-8'),
                    file_name=f"Cheatsheet_{file_slug}.md",
                    mime="text/markdown",
                    use_container_width=True,
                    key="cheatsheet_download"
                )

    except Exception as e:
        st.error(f"An error occurred: {e}")
        logger.error(f"Generation Error: {e}", exc_info=True)