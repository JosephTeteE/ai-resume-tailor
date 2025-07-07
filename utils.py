# utils.py
from docx import Document
import pdfplumber
from io import BytesIO
import re
from collections import Counter
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.opc.constants import RELATIONSHIP_TYPE as RT

# --- Document Extraction Functions ---
def extract_text_from_docx(uploaded_file):
    """Extracts text from a .docx file."""
    try:
        document = Document(uploaded_file)
        full_text = []
        for para in document.paragraphs:
            full_text.append(para.text)
        return "\n".join(full_text)
    except Exception as e:
        if "Zipfile is not a zip file" in str(e):
             raise ValueError("Invalid or corrupted .docx file.")
        raise e

def extract_text_from_pdf(uploaded_file):
    """Extracts text from a .pdf file."""
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            return "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    except Exception as e:
        raise ValueError(f"Could not process PDF: {e}")

# --- Keyword & ATS Functions ---
def extract_keywords(text, top_n=50):
    """Extracts relevant keywords from text, excluding common stopwords."""
    if not text:
        return []
    words = re.findall(r'\b[a-z\d]{3,}\b', text.lower())
    stopwords = set([
        "a", "an", "the", "and", "but", "or", "for", "nor", "as", "at", "by", "from", 
        "in", "into", "of", "on", "to", "with", "is", "are", "was", "were", "be", 
        "been", "has", "had", "have", "do", "does", "did", "will", "can", "should", 
        "would", "could", "its", "it's", "that", "this", "these", "those", "etc",
        "job", "description", "experience", "required", "skills", "responsibilities"
    ])
    keywords = [word for word in words if word not in stopwords]
    return [kw for kw, _ in Counter(keywords).most_common(top_n)]

def calculate_ats_score(resume_text, job_description):
    """Calculates a basic ATS match score based on shared keywords."""
    resume_kws = set(extract_keywords(resume_text, top_n=100))
    jd_kws = set(extract_keywords(job_description, top_n=100))
    if not jd_kws:
        return 0
    matched_kws = resume_kws.intersection(jd_kws)
    score = (len(matched_kws) / len(jd_kws)) * 100
    return min(100, int(score))

# --- DOCX Creation & Styling Functions ---
def _add_hyperlink(paragraph, text, url):
    """Adds a hyperlink to a paragraph."""
    part = paragraph.part
    r_id = part.relate_to(url, RT.HYPERLINK, is_external=True)
    hyperlink = OxmlElement('w:hyperlink')
    hyperlink.set(qn('r:id'), r_id)
    new_run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    c = OxmlElement('w:color')
    c.set(qn('w:val'), '0563C1')
    rPr.append(c)
    u = OxmlElement('w:u')
    u.set(qn('w:val'), 'single')
    rPr.append(u)
    new_run.append(rPr)
    new_run.text = text
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)

def _add_section_divider(doc):
    """Adds a full-width, un-indented horizontal line."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '4')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), 'auto')
    pBdr.append(bottom)
    pPr.append(pBdr)

def _add_contact_info(doc, content):
    """Handles the special formatting for the contact info section."""
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    if not lines: return
    name_paragraph = doc.add_paragraph()
    name_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    name_run = name_paragraph.add_run(lines[0])
    name_run.font.name = 'Calibri'
    name_run.font.size = Pt(16)
    name_run.bold = True
    contact_details_paragraph = doc.add_paragraph()
    contact_details_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    contact_details_paragraph.paragraph_format.space_after = Pt(4)
    email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    details_line = " | ".join(lines[1:])
    last_end = 0
    for match in email_pattern.finditer(details_line):
        start, end = match.span()
        if start > last_end:
            contact_details_paragraph.add_run(details_line[last_end:start])
        _add_hyperlink(contact_details_paragraph, match.group(0), f"mailto:{match.group(0)}")
        last_end = end
    if last_end < len(details_line):
        contact_details_paragraph.add_run(details_line[last_end:])

def _add_section_content(doc, section_key, content):
    """Adds a standard section with a header and content."""
    header = doc.add_paragraph()
    header_run = header.add_run(section_key.replace('_', ' ').upper())
    header_run.font.name = 'Calibri'
    header_run.font.size = Pt(12)
    header_run.bold = True
    header.paragraph_format.space_before = Pt(2)
    header.paragraph_format.space_after = Pt(4)
    for line in content.split('\n'):
        line = line.strip()
        if not line: continue
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        if line.startswith('* ') or line.startswith('- '):
            p.style = 'List Bullet'
            text = line[2:]
        else:
            text = line
        parts = re.split(r'(\*\*.*?\*\*)', text)
        for part in parts:
            if part.startswith('**') and part.endswith('**'):
                run = p.add_run(part[2:-2])
                run.bold = True
            else:
                p.add_run(part)

def create_styled_docx(tailored_sections_dict, final_markdown, original_cv_text):
    """Creates a styled DOCX document from the final markdown content."""
    document = Document()
    style = document.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(11)
    style.paragraph_format.space_after = Pt(0)
    section = document.sections[0]
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    lines = final_markdown.strip().split('\n')
    sections_in_order = []
    current_section_content = []
    first_header_index = -1
    for i, line in enumerate(lines):
        if line.startswith("## "):
            first_header_index = i
            break
    if first_header_index == -1:
        contact_info_content = "\n".join(lines)
        sections_in_order.append(("CONTACT_INFO", contact_info_content))
        lines = []
    else:
        contact_info_content = "\n".join(lines[:first_header_index]).strip()
        sections_in_order.append(("CONTACT_INFO", contact_info_content))
        lines = lines[first_header_index:]
    current_section_key = None
    for line in lines:
        if line.startswith("## "):
            if current_section_key:
                sections_in_order.append((current_section_key, "\n".join(current_section_content).strip()))
            header_text = line[3:].strip().upper().replace(' ', '_')
            current_section_key = header_text
            current_section_content = []
        else:
            current_section_content.append(line)
    if current_section_key:
        sections_in_order.append((current_section_key, "\n".join(current_section_content).strip()))
    for i, (key, content) in enumerate(sections_in_order):
        if not content: continue
        if key == "CONTACT_INFO":
            _add_contact_info(document, content)
        else:
            _add_section_content(document, key, content)
        if i < len(sections_in_order) - 1:
            if i + 1 < len(sections_in_order) and sections_in_order[i+1][1]:
                 _add_section_divider(document)
    bio = BytesIO()
    document.save(bio)
    bio.seek(0)
    return bio.getvalue()

def create_cheatsheet_docx(cheatsheet_text):
    """Converts markdown cheatsheet text to a styled DOCX file."""
    document = Document()
    style = document.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(11)
    # Tighter spacing for cheatsheet
    style.paragraph_format.space_after = Pt(4)
    style.paragraph_format.line_spacing = 1.15
    
    # Custom heading styles
    styles = document.styles
    if 'heading 2' not in styles: styles.add_style('Heading 2', 1)
    if 'heading 3' not in styles: styles.add_style('Heading 3', 1)

    styles['Heading 2'].font.name = 'Calibri'
    styles['Heading 2'].font.size = Pt(14)
    styles['Heading 2'].font.bold = True
    styles['Heading 2'].paragraph_format.space_before = Pt(12)
    styles['Heading 2'].paragraph_format.space_after = Pt(4)
    
    styles['Heading 3'].font.name = 'Calibri'
    styles['Heading 3'].font.size = Pt(12)
    styles['Heading 3'].font.bold = True
    styles['Heading 3'].paragraph_format.space_before = Pt(10)
    styles['Heading 3'].paragraph_format.space_after = Pt(2)
    
    in_code_block = False
    for line in cheatsheet_text.split('\n'):
        if line.strip() == '---':
            document.add_page_break()
            continue
        
        if line.startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            p = document.add_paragraph(line)
            p.style = 'Normal' # Or a custom code style
            continue

        if line.startswith('## '):
            document.add_paragraph(line.lstrip('## ').strip(), style='Heading 2')
        elif line.startswith('### '):
            document.add_paragraph(line.lstrip('### ').strip(), style='Heading 3')
        elif line.strip().startswith('* '):
            p = document.add_paragraph(line.strip().lstrip('* '), style='List Bullet')
            p.paragraph_format.left_indent = Inches(0.25)
            p.paragraph_format.first_line_indent = Inches(-0.25)
        elif line.strip():
            p = document.add_paragraph()
            # Handle bolding within a line
            parts = re.split(r'(\*\*.*?\*\*)', line)
            for part in parts:
                if part.startswith('**') and part.endswith('**'):
                    p.add_run(part[2:-2]).bold = True
                else:
                    p.add_run(part)
        else:
            document.add_paragraph() # Add empty line for spacing
            
    bio = BytesIO()
    document.save(bio)
    bio.seek(0)
    return bio.getvalue()