# app.py

import streamlit as st
import os
from dotenv import load_dotenv
import logging

load_dotenv()

from ai_agent import extract_job_title, generate_tailored_resume_data, generate_cheatsheet, generate_cover_letter
from utils import create_final_docx, create_cheatsheet_docx, create_cover_letter_docx, slugify
from config import MASTER_RESUME_DATA

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Page Config ---
st.set_page_config(layout="wide", page_title="AI Resume Strategist")
st.title("📄 AI Resume Strategist")

# --- Helper Function ---
def assemble_content_string(final_resume_data):
    """Assembles the final, edited resume data into a string for the cheatsheet prompt."""
    content_parts = []
    contact = MASTER_RESUME_DATA['CONTACT_INFO']
    content_parts.append(f"{contact['name']}\n{contact['details']}")
    content_parts.append("\nEDUCATION")
    for edu in MASTER_RESUME_DATA['EDUCATION']:
        content_parts.append(f"{edu['institution']}\n{edu['degree']}")
    content_parts.append("\nRELEVANT EXPERIENCE")
    for company in MASTER_RESUME_DATA["RELEVANT_EXPERIENCE_STATIC"]:
        if company in final_resume_data.get('experience', {}):
            details = final_resume_data['experience'][company]
            role = details.get('role', 'Error')
            bullets = "\n".join([f"• {b}" for b in details.get('bullets', [])])
            content_parts.append(f"\n{company}\n{role}\n{bullets}")
    skills = final_resume_data.get('skills', {})
    content_parts.append(f"\nSKILLS:\nTechnical Skills: {skills.get('technical', '')}\nSoft Skills: {skills.get('soft', '')}")
    return "\n".join(content_parts)

# --- Main UI ---
st.subheader("Step 1: Provide Job Details")

st.session_state.job_title_input = st.text_input(
    "Target Job Title (or paste full description below)", value=st.session_state.get('job_title_input', '')
)
st.session_state.company_name_input = st.text_input(
    "Company Name", value=st.session_state.get('company_name_input', '')
)
st.session_state.job_description_input = st.text_area(
    "Paste the Job Description", height=250, value=st.session_state.get('job_description_input', '')
)

# Initialize provider index for cycling
if 'provider_index' not in st.session_state:
    st.session_state.provider_index = 0

if st.button("🚀 Generate Resume Content", use_container_width=True, type="primary"):
    if st.session_state.job_description_input:
        # Clear previous generated data, but keep inputs
        for key in ['generated_data', 'editable_sections', 'finalized', 'final_resume_data', 'cover_letter', 'cheatsheet', 'official_job_title']:
            if key in st.session_state:
                del st.session_state[key]
        
        with st.spinner("Step 1/2: Identifying job title and generating all content..."):
            st.session_state.official_job_title = extract_job_title(
                st.session_state.job_title_input,
                st.session_state.job_description_input
            )
            
            generated_data = generate_tailored_resume_data(
                st.session_state.job_description_input, 
                st.session_state.official_job_title,
                start_provider_index=st.session_state.provider_index
            )
        
        if generated_data and not generated_data.get("error"):
            st.session_state.generated_data = generated_data
            st.session_state.editable_sections = generated_data
            # --- UPDATED: Changed cycle count from 4 to 5 ---
            st.session_state.provider_index = (st.session_state.provider_index + 1) % 5
            st.success("Step 2/2: Content generated! Please review and edit below.")
        else:
            error_message = generated_data.get("error", "An unknown error occurred.")
            st.error(f"AI Generation Failed: {error_message} Please try again.")

if 'editable_sections' in st.session_state:
    st.markdown("---")
    st.subheader("Step 2: Review & Edit Your Generated Resume")
    
    # Determine if fields should be disabled
    disable_fields = st.session_state.get('finalized', False)
    
    with st.expander("Skills Section", expanded=True):
        st.session_state.editable_sections['skills']['technical'] = st.text_area(
            "Technical Skills", 
            st.session_state.editable_sections['skills']['technical'],
            disabled=disable_fields,
            key="technical_skills_final"
        )
        st.session_state.editable_sections['skills']['soft'] = st.text_area(
            "Soft Skills", 
            st.session_state.editable_sections['skills']['soft'],
            disabled=disable_fields,
            key="soft_skills_final"
        )
    
    with st.expander("Experience Section", expanded=True):
        for company in MASTER_RESUME_DATA["RELEVANT_EXPERIENCE_STATIC"]:
            if company in st.session_state.editable_sections['experience']:
                details = st.session_state.editable_sections['experience'][company]
                st.markdown(f"**{company}**")
                details['role'] = st.text_input(
                    "Role Title", 
                    details.get('role', 'Error'), 
                    key=f"role_{company}_final",
                    disabled=disable_fields
                )
                bullets_as_string = "\n".join(details.get('bullets', []))
                edited_bullets_string = st.text_area(
                    "Bullet Points", 
                    bullets_as_string, 
                    key=f"bullets_{company}_final", 
                    height=140,
                    disabled=disable_fields
                )
                if not disable_fields:  # Only update if fields are editable
                    details['bullets'] = [line.strip() for line in edited_bullets_string.split('\n') if line.strip()]

    st.markdown("---")
    st.subheader("Step 3: Finalize & Generate Documents")

    if not st.session_state.get('finalized', False):
        if st.button("✅ Finalize Resume & Prepare Downloads", use_container_width=True, type="primary"):
            st.session_state.finalized = True
            st.session_state.final_resume_data = st.session_state.editable_sections
            st.success("Resume finalized! Your download links are ready below.")
            st.rerun()

if st.session_state.get('finalized', False):
    if 'official_job_title' in st.session_state:
        include_cover_letter = st.toggle("Generate a Cover Letter?", value=True, key="cover_letter_toggle")

        col1, col2 = st.columns(2)
        with col1:
            if include_cover_letter:
                if st.button("✍️ Generate Cover Letter", use_container_width=True):
                    with st.spinner("Writing your cover letter..."):
                        st.session_state.cover_letter = generate_cover_letter(
                            st.session_state.final_resume_data, st.session_state.job_description_input, 
                            st.session_state.official_job_title, st.session_state.company_name_input,
                            start_provider_index=st.session_state.provider_index
                        )
        with col2:
            if st.button("🧠 Generate Interview Cheatsheet", use_container_width=True):
                with st.spinner("Creating your interview prep guide..."):
                    resume_content = assemble_content_string(st.session_state.final_resume_data)
                    st.session_state.cheatsheet = generate_cheatsheet(
                        resume_content, st.session_state.job_description_input, 
                        st.session_state.official_job_title,
                        start_provider_index=st.session_state.provider_index
                    )

        st.markdown("---")
        st.subheader("Step 4: Download Your Documents")
        
        base_name = "Aye_Uweja"
        job_slug = slugify(st.session_state.official_job_title)
        company_slug = slugify(st.session_state.company_name_input)
        file_slug = f"{job_slug}_{company_slug}" if company_slug else job_slug

        st.download_button("⬇️ Download Resume as DOCX", create_final_docx(st.session_state.final_resume_data),
            file_name=f"{base_name}_{file_slug}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True)

        if 'cover_letter' in st.session_state:
            st.download_button("⬇️ Download Cover Letter as DOCX", create_cover_letter_docx(st.session_state.cover_letter),
                file_name=f"Cover_Letter_{file_slug}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True)
        
        if 'cheatsheet' in st.session_state:
            st.download_button("⬇️ Download Cheatsheet as DOCX", create_cheatsheet_docx(st.session_state.cheatsheet),
                file_name=f"Cheatsheet_{file_slug}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True)

st.markdown("---")
if st.button("🔄 Start New Application", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()