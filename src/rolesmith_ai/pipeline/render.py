import hashlib
import json
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from .models import MasterProfile, ResumeDraft
from .profile_store import load_master_profile


def _get_resume_dir(company: str) -> Path:
    # safe company name
    comp_safe = "".join([c if c.isalnum() else "_" for c in company]).strip("_")
    # hash for uniqueness
    h = hashlib.md5(company.encode("utf-8")).hexdigest()[:8]
    return Path.home() / ".rolesmith_ai" / "resumes" / f"{comp_safe}-{h}"


def _draw_resume(c: canvas.Canvas, draft: ResumeDraft, master: MasterProfile, font_size: float) -> int:
    width, height = letter
    x_margin = 1 * inch
    y_margin = 1 * inch
    y_pos = height - y_margin
    page_num = 1

    line_height = font_size * 1.2

    def check_page(y, c, p_num):
        if y < y_margin:
            c.showPage()
            return height - y_margin, p_num + 1
        return y, p_num

    def write_line(
        text: str,
        y: float,
        c: canvas.Canvas,
        p_num: int,
        is_bold: bool = False,
        indent: float = 0,
    ):
        font_name = "Helvetica-Bold" if is_bold else "Helvetica"
        c.setFont(font_name, font_size)
        c.drawString(x_margin + indent, y, text)
        return y - line_height

    # Name and Contact
    y_pos = write_line(master.name, y_pos, c, page_num, is_bold=True)
    contact = f"{master.email} | {master.phone} | {master.location}"
    if master.links:
        contact += f" | {' | '.join(master.links)}"
    y_pos = write_line(contact, y_pos, c, page_num)
    y_pos -= line_height / 2

    # Headline and Summary
    y_pos, page_num = check_page(y_pos, c, page_num)
    y_pos = write_line(draft.headline, y_pos, c, page_num, is_bold=True)

    # Simple word wrap for summary (approx 90 chars per line at 10pt)
    chars_per_line = int((width - 2 * x_margin) / (font_size * 0.5))
    words = draft.summary.split()
    line = ""
    for w in words:
        if len(line) + len(w) + 1 <= chars_per_line:
            line += w + " "
        else:
            y_pos, page_num = check_page(y_pos, c, page_num)
            y_pos = write_line(line.strip(), y_pos, c, page_num)
            line = w + " "
    if line:
        y_pos, page_num = check_page(y_pos, c, page_num)
        y_pos = write_line(line.strip(), y_pos, c, page_num)

    y_pos -= line_height / 2

    # Skills
    if draft.skills:
        y_pos, page_num = check_page(y_pos, c, page_num)
        y_pos = write_line("SKILLS", y_pos, c, page_num, is_bold=True)
        for cat, skills in draft.skills.items():
            s_text = f"{cat}: {', '.join(skills)}"
            y_pos, page_num = check_page(y_pos, c, page_num)
            y_pos = write_line(s_text, y_pos, c, page_num)
        y_pos -= line_height / 2

    # Experience
    if draft.experience:
        y_pos, page_num = check_page(y_pos, c, page_num)
        y_pos = write_line("EXPERIENCE", y_pos, c, page_num, is_bold=True)
        for exp in draft.experience:
            header1 = f"{exp.title} - {exp.company}"
            header2 = f"{exp.dates}"
            if exp.location:
                header2 += f" | {exp.location}"
            y_pos, page_num = check_page(y_pos, c, page_num)
            y_pos = write_line(header1, y_pos, c, page_num, is_bold=True)
            y_pos, page_num = check_page(y_pos, c, page_num)
            y_pos = write_line(header2, y_pos, c, page_num)

            for b in exp.bullets:
                # Wrap bullets
                b_words = b.split()
                b_line = "- "
                for w in b_words:
                    if len(b_line) + len(w) + 1 <= chars_per_line - 4:
                        b_line += w + " "
                    else:
                        y_pos, page_num = check_page(y_pos, c, page_num)
                        y_pos = write_line(b_line.strip(), y_pos, c, page_num, indent=15)
                        b_line = "  " + w + " "
                if b_line.strip() != "-" and b_line.strip() != "":
                    y_pos, page_num = check_page(y_pos, c, page_num)
                    y_pos = write_line(b_line.strip(), y_pos, c, page_num, indent=15)
            y_pos -= line_height / 4
        y_pos -= line_height / 4

    # Projects
    if draft.projects:
        y_pos, page_num = check_page(y_pos, c, page_num)
        y_pos = write_line("PROJECTS", y_pos, c, page_num, is_bold=True)
        for p in draft.projects:
            p_head = f"{p.name}"
            if p.link:
                p_head += f" ({p.link})"
            y_pos, page_num = check_page(y_pos, c, page_num)
            y_pos = write_line(p_head, y_pos, c, page_num, is_bold=True)

            y_pos, page_num = check_page(y_pos, c, page_num)
            p_desc = p.description
            if p.technologies:
                p_desc += f" (Tech: {', '.join(p.technologies)})"

            # wrap
            p_words = p_desc.split()
            p_line = ""
            for w in p_words:
                if len(p_line) + len(w) + 1 <= chars_per_line:
                    p_line += w + " "
                else:
                    y_pos, page_num = check_page(y_pos, c, page_num)
                    y_pos = write_line(p_line.strip(), y_pos, c, page_num)
                    p_line = w + " "
            if p_line:
                y_pos, page_num = check_page(y_pos, c, page_num)
                y_pos = write_line(p_line.strip(), y_pos, c, page_num)
            y_pos -= line_height / 4
        y_pos -= line_height / 4

    # Education
    if master.education:
        y_pos, page_num = check_page(y_pos, c, page_num)
        y_pos = write_line("EDUCATION", y_pos, c, page_num, is_bold=True)
        for e in master.education:
            y_pos, page_num = check_page(y_pos, c, page_num)
            y_pos = write_line(f"{e.degree} - {e.institution} ({e.dates})", y_pos, c, page_num)
        y_pos -= line_height / 4

    # Certifications
    if master.certifications:
        y_pos, page_num = check_page(y_pos, c, page_num)
        y_pos = write_line("CERTIFICATIONS", y_pos, c, page_num, is_bold=True)
        for c_item in master.certifications:
            c_text = f"{c_item.name} - {c_item.issuer}"
            if c_item.dates:
                c_text += f" ({c_item.dates})"
            y_pos, page_num = check_page(y_pos, c, page_num)
            y_pos = write_line(c_text, y_pos, c, page_num)

    return page_num


def render_resume(company: str, draft: ResumeDraft, warnings: list[str]) -> str:
    master = load_master_profile()
    out_dir = _get_resume_dir(company)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Safe name
    safe_name = "".join([c if c.isalnum() else "_" for c in master.name])
    pdf_path = out_dir / f"{safe_name}_Resume.pdf"

    # Try fonts from 10 down to 8.5
    for font_size in [10.0, 9.5, 9.0, 8.5]:
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        pages = _draw_resume(c, draft, master, font_size)
        if pages <= 2:
            c.save()
            break
        elif font_size == 8.5:
            # save anyway
            c.save()

    # Save json
    json_path = out_dir / "resume.json"
    data = draft.model_dump()
    data["warnings"] = warnings
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)

    return str(pdf_path)
