# utils.py
import re
from io import BytesIO
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT, WD_TAB_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from config import MASTER_RESUME_DATA

# Helper function to add hyperlinks to paragraphs
def _add_hyperlink(paragraph, text, url):
    part = paragraph.part
    r_id = part.relate_to(url, RT.HYPERLINK, is_external=True)
    hyperlink = OxmlElement('w:hyperlink'); hyperlink.set(qn('r:id'), r_id)
    new_run = OxmlElement('w:r'); rPr = OxmlElement('w:rPr')
    rFont = OxmlElement('w:rFonts'); rFont.set(qn('w:ascii'), 'Times New Roman'); rFont.set(qn('w:hAnsi'), 'Times New Roman'); rPr.append(rFont)
    sz = OxmlElement('w:sz'); sz.set(qn('w:val'), '20'); rPr.append(sz)
    c = OxmlElement('w:color'); c.set(qn('w:val'), '0563C1'); rPr.append(c)
    u = OxmlElement('w:u'); u.set(qn('w:val'), 'single'); rPr.append(u)
    new_run.append(rPr); new_run.text = text; hyperlink.append(new_run)
    paragraph._p.append(hyperlink)

# Helper function to add section headers with consistent formatting
def _add_section_header(doc, text):
    """Helper function to add section headers with consistent formatting"""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    run = p.add_run(text)
    run.bold = True
    run.underline = True
    return p

# Function to create the final DOCX document
def create_final_docx(tailored_data):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(10)
    style.paragraph_format.line_spacing = 1.0; style.paragraph_format.space_before = Pt(0); style.paragraph_format.space_after = Pt(0)
    section = doc.sections[0]
    section.left_margin = Inches(0.75); section.right_margin = Inches(0.75); section.top_margin = Inches(0.5); section.bottom_margin = Inches(0.5)
    tab_stops = doc.styles['Normal'].paragraph_format.tab_stops
    tab_stops.add_tab_stop(Inches(7.0), WD_TAB_ALIGNMENT.RIGHT)
    
    # --- Contact Info & Main Divider ---
    contact_info = MASTER_RESUME_DATA['CONTACT_INFO']
    p_name = doc.add_paragraph(); p_name.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run_name = p_name.add_run(contact_info['name']); run_name.font.size = Pt(14); run_name.bold = True
    p_details = doc.add_paragraph(); p_details.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER; p_details.paragraph_format.space_after = Pt(4)
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', contact_info['details'])
    if email_match:
        p_details.add_run(contact_info['details'][:email_match.start()])
        _add_hyperlink(p_details, email_match.group(0), f"mailto:{email_match.group(0)}")
        p_details.add_run(contact_info['details'][email_match.end():])
    else: p_details.add_run(contact_info['details'])
    p_divider = doc.add_paragraph()
    p_divider_pr = p_divider._p.get_or_add_pPr(); p_bdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom'); bottom.set(qn('w:val'), 'single'); bottom.set(qn('w:sz'), '4'); bottom.set(qn('w:space'), '1'); bottom.set(qn('w:color'), 'auto')
    p_bdr.append(bottom); p_divider_pr.append(p_bdr)
    
    # --- Education ---
    _add_section_header(doc, "EDUCATION")
    if len(doc.paragraphs) > 0 and not doc.paragraphs[-1].text.strip():
        doc.paragraphs[-1]._element.getparent().remove(doc.paragraphs[-1]._element)
    
    for i, edu in enumerate(MASTER_RESUME_DATA['EDUCATION']):
        p_inst = doc.add_paragraph()
        p_inst.add_run(edu['institution']).bold = True
        p_inst.add_run(f"\t{edu['location']}")
        
        p_deg = doc.add_paragraph()
        run_deg = p_deg.add_run(edu['degree'])
        run_deg.bold = True
        run_deg.italic = True
        
        # Make dates bold
        dates_run = p_deg.add_run(f"\t{edu['dates']}")
        dates_run.bold = True
        
        doc.add_paragraph(edu['courses']).add_run().italic = True
        
        # Add space between education entries except after last one
        if i < len(MASTER_RESUME_DATA['EDUCATION']) - 1:
            p = doc.add_paragraph(' ', style='Normal')
            p.paragraph_format.space_after = Pt(2)
    
    # --- Relevant Experience ---
    _add_section_header(doc, "RELEVANT EXPERIENCE")

    if len(doc.paragraphs) > 0 and not doc.paragraphs[-1].text.strip():
        doc.paragraphs[-1]._element.getparent().remove(doc.paragraphs[-1]._element)
    
    static_exp = MASTER_RESUME_DATA['RELEVANT_EXPERIENCE_STATIC']
    for i, (company, static_info) in enumerate(static_exp.items()):
        p_comp = doc.add_paragraph()
        p_comp.add_run(company).bold = True
        p_comp.add_run(f"\t{static_info['location']}")
        
        p_role = doc.add_paragraph()
        p_role.add_run(tailored_data['experience'][company]['role']).bold = True
        
        # Make dates bold
        dates_run = p_role.add_run(f"\t{static_info['dates']}")
        dates_run.bold = True
        
        for bullet in tailored_data['experience'][company]['bullets']:
            doc.add_paragraph(bullet, style='List Bullet')
        
        # Add space between experience entries except after last one
        if i < len(static_exp) - 1:
            p = doc.add_paragraph(' ', style='Normal')
            p.paragraph_format.space_after = Pt(2)
    
    # --- Award ---
    p = doc.add_paragraph(' ', style='Normal')
    p.paragraph_format.space_after = Pt(8)
    p_award = doc.add_paragraph()
    run_award_label = p_award.add_run("AWARD: ")
    run_award_label.bold = True
    run_award_label.underline = True
    p_award.add_run(MASTER_RESUME_DATA['AWARD'])

    
    # --- Skills ---
    _add_section_header(doc, "SKILLS:")
    
    p_tech = doc.add_paragraph()
    p_tech.add_run("Technical Skills: ").bold = True
    p_tech.add_run(tailored_data['skills']['technical'])
    
    p_soft = doc.add_paragraph()
    p_soft.paragraph_format.space_before = Pt(4)
    p_soft.add_run("Soft Skills: ").bold = True
    p_soft.add_run(tailored_data['skills']['soft'])
    
    # --- Organizations ---
    _add_section_header(doc, "ORGANIZATIONS")
    
    org_data = MASTER_RESUME_DATA['ORGANIZATIONS']
    p_org = doc.add_paragraph()
    p_org.add_run(f"{org_data['role']}\t")
    
    # Make dates bold
    dates_run = p_org.add_run(org_data['dates'])
    dates_run.bold = True

    # Final cleanup
    for p in reversed(doc.paragraphs):
        if (
            not p.text.strip()
            and not len(p.runs)
            and p._p.pPr is None
            and (
                not hasattr(p.paragraph_format, 'space_after')
                or p.paragraph_format.space_after == Pt(0)
            )
        ):
            p._element.getparent().remove(p._element)

    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio.getvalue()
