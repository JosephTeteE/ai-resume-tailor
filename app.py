# app.py

import streamlit as st
import os
from dotenv import load_dotenv
from io import BytesIO
import re
import logging
from streamlit_quill import st_quill

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import local modules
from utils import extract_text_from_docx, extract_text_from_pdf, calculate_ats_score, create_styled_docx, create_cheatsheet_docx
from ai_agent import tailor_resume, generate_interview_cheatsheet

# --- API Key Configuration ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    st.error("Gemini API Key not found.")
    st.stop()

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="AI Resume Tailor")
st.title("📄 AI-Powered Resume Tailor")
st.markdown("Effortlessly adapt your resume to a job description. Upload, paste, and get a tailored resume in moments!")

# --- Sidebar ---
with st.sidebar:
    st.header("How It Works:")
    st.markdown("""
    1.  **Upload CV** (.docx or .pdf)
    2.  **Paste Job Description**
    3.  **Click 'Tailor My Resume!'**
    4.  **Review & Edit:** If you make changes, a 'Re-tailor' button will appear.
    5.  **Download** your tailored resume and generate a cheatsheet to help you prepare!
    """)
    st.info("For best results, ensure your CV has clear section headings.")

# --- Helper Functions ---
def markdown_to_html(text):
    text = text.replace('\n', '<br>')
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    text = re.sub(r'([^<br>]+?): (.*?)(<br>|$)', r'<strong>\1:</strong> \2<br>', text)
    return text

def html_to_markdown(html):
    if not html: return ""
    html = re.sub(r'<p><br></p>', '\n', html)
    html = html.replace('<p>', '').replace('</p>', '\n')
    html = html.replace('<br>', '\n')
    html = re.sub(r'<strong>(.*?)</strong>', r'**\1**', html)
    html = re.sub(r'<em>(.*?)</em>', r'*\1*', html)
    html = re.sub(r'<[^>]+>', '', html)
    return html.strip()

def extract_job_title(jd_text):
    for line in jd_text.split('\n'):
        clean_line = line.strip()
        if any(keyword in clean_line.lower() for keyword in ['job title', 'position:']):
            return clean_line.split(':')[-1].strip()
    for line in jd_text.split('\n'):
        if line.strip(): return line.strip()
    return "Job"

# --- Main UI ---
def initialize_session():
    # Store uploaded file info to survive a full re-run
    if 'uploaded_cv' in st.session_state:
        st.session_state['original_filename'] = st.session_state.uploaded_cv.name
        with st.spinner("Extracting text..."):
            file_extension = os.path.splitext(st.session_state.uploaded_cv.name)[1]
            if file_extension == ".docx":
                st.session_state['original_cv_content'] = extract_text_from_docx(st.session_state.uploaded_cv)
            else:
                st.session_state['original_cv_content'] = extract_text_from_pdf(st.session_state.uploaded_cv)

col1, col2 = st.columns(2)
with col1:
    st.subheader("1. Upload Your Current CV")
    st.file_uploader("Choose a file", type=["docx", "pdf"], key="uploaded_cv", on_change=initialize_session)
    if 'original_cv_content' in st.session_state:
        st.text_area("Preview of Original CV", st.session_state.original_cv_content, height=300, disabled=True)

with col2:
    st.subheader("2. Paste the Job Description")
    st.text_area("Paste the job description here:", height=400, key="job_description_content")

st.markdown("---")

if st.button("🚀 Tailor My Resume!", use_container_width=True, type="primary"):
    if 'original_cv_content' in st.session_state and 'job_description_content' in st.session_state:
        st.session_state.tailoring_in_progress = True
        st.session_state.cv_source_for_tailoring = st.session_state.original_cv_content
    else:
        st.warning("Please upload your CV and paste the Job Description.")

# --- Full Tailoring or Re-tailoring Logic ---
if st.session_state.get('tailoring_in_progress') or st.session_state.get('retailoring_in_progress'):
    spinner_text = "✨ Re-tailoring with your edits..." if st.session_state.get('retailoring_in_progress') else "✨ Tailoring your resume..."
    with st.spinner(spinner_text):
        source_cv = st.session_state.get('cv_source_for_retailoring', st.session_state.get('original_cv_content'))
        tailoring_result = tailor_resume(source_cv, st.session_state['job_description_content'], GEMINI_API_KEY)
        
        st.session_state['tailored_sections_dict'] = tailoring_result["tailored_sections"]
        st.session_state['display_order'] = tailoring_result["section_order"]
        display_output_markdown = ""
        for key in st.session_state['display_order']:
            content = st.session_state['tailored_sections_dict'].get(key, "")
            if content and content.strip():
                if key != "CONTACT_INFO": display_output_markdown += f"## {key.replace('_', ' ').title()}\n\n"
                display_output_markdown += f"{content}\n\n"
        
        st.session_state['final_markdown_output'] = display_output_markdown.strip()
        st.session_state['ats_score'] = calculate_ats_score(display_output_markdown, st.session_state['job_description_content'])
        
        # Reset flags
        st.session_state.tailoring_in_progress = False
        st.session_state.retailoring_in_progress = False
        st.session_state.show_editor = True
        if 'cheatsheet_content' in st.session_state: del st.session_state['cheatsheet_content'] # Clear old cheatsheet
        st.rerun()

# --- Editor and Action Buttons ---
if st.session_state.get('show_editor'):
    st.subheader("3. Review, Edit & Download")
    st.progress(st.session_state.get('ats_score', 0) / 100, text=f"ATS Match Score: {st.session_state.get('ats_score', 0)}%")
    edited_content_html = st_quill(value=markdown_to_html(st.session_state.get('final_markdown_output', '')), key='editor')
    final_markdown = html_to_markdown(edited_content_html)
    
    st.markdown("---")
    cols = st.columns(3)
    # Download Resume Button
    with cols[0]:
        try:
            docx_bytes = create_styled_docx(st.session_state['tailored_sections_dict'], final_markdown, st.session_state['original_cv_content'])
            st.download_button(label="⬇️ Download Resume", data=docx_bytes, file_name=f"{os.path.splitext(st.session_state.original_filename)[0]}_Tailored.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True, type="primary")
        except Exception as e:
            st.error(f"Error making DOCX: {e}")

    # Re-tailor Button (Conditional)
    with cols[1]:
        if final_markdown != st.session_state.get('final_markdown_output'):
            if st.button("🔄 Re-tailor With Your Edits", use_container_width=True):
                st.session_state.retailoring_in_progress = True
                st.session_state.cv_source_for_retailoring = final_markdown
                st.rerun()

    # Generate Cheatsheet Button
    with cols[2]:
        if st.button("💡 Generate Cheatsheet", use_container_width=True):
            st.session_state['generating_cheatsheet'] = True
            st.session_state['cheatsheet_source_resume'] = final_markdown
            st.rerun()

# --- Cheatsheet Generation & Download Logic ---
if st.session_state.get('generating_cheatsheet'):
    with st.spinner("🧠 Generating your personalized interview cheatsheet..."):
        cheatsheet_content = generate_interview_cheatsheet(st.session_state['cheatsheet_source_resume'], st.session_state['job_description_content'], GEMINI_API_KEY)
        st.session_state['cheatsheet_docx_bytes'] = create_cheatsheet_docx(cheatsheet_content)
        del st.session_state['generating_cheatsheet']
        st.rerun()

if 'cheatsheet_docx_bytes' in st.session_state:
    st.success("✅ Your Interview Cheatsheet is ready!")
    job_title = extract_job_title(st.session_state['job_description_content'])
    cheatsheet_filename = f"Cheatsheet_for_{job_title.replace(' ', '_')}.docx"
    st.download_button(label="⬇️ Download Cheatsheet (.docx)", data=st.session_state['cheatsheet_docx_bytes'], file_name=cheatsheet_filename, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True, type="primary")