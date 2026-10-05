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
    h = hashlib.sha256(company.encode("utf-8")).hexdigest()[:16]
    return Path.home() / ".rolesmith_ai" / "resumes" / f"{comp_safe}-{h}"


def _draw_resume(c: canvas.Canvas, draft: ResumeDraft, master: MasterProfile, font_size: float) -> int:
    width, height = letter
    x_margin = 0.8 * inch
    y_margin = 0.8 * inch
    y_pos = height - y_margin
    page_num = 1

    line_height = font_size * 1.35

    primary_color = "#1f2937"  # Dark gray/black
    secondary_color = "#4b5563"  # Medium gray
    accent_color = "#2563eb"  # Professional blue

    c.setStrokeColor(secondary_color)

    def check_page(y, c, p_num, required_space=0):
        if y - required_space < y_margin:
            c.showPage()
            return height - y_margin, p_num + 1
        return y, p_num

    def draw_section_header(title: str, y: float, c: canvas.Canvas, p_num: int):
        y, p_num = check_page(y, c, p_num, line_height * 2)
        c.setFont("Helvetica-Bold", font_size + 2)
        c.setFillColor(primary_color)
        c.drawString(x_margin, y, title.upper())
        c.setLineWidth(0.5)
        c.line(x_margin, y - 4, width - x_margin, y - 4)
        return y - line_height * 1.5, p_num

    # Name and Contact
    c.setFont("Helvetica-Bold", font_size + 14)
    c.setFillColor(primary_color)
    c.drawString(x_margin, y_pos, master.name.upper())
    y_pos -= line_height * 1.5

    c.setFont("Helvetica", font_size - 1)
    c.setFillColor(secondary_color)
    contact = f"{master.email}  |  {master.phone}  |  {master.location}"
    if master.links:
        contact += f"  |  {'  |  '.join(master.links)}"
    c.drawString(x_margin, y_pos, contact)
    y_pos -= line_height * 2

    # Headline & Summary
    if draft.headline or draft.summary:
        if draft.headline:
            c.setFont("Helvetica-Bold", font_size + 1)
            c.setFillColor(accent_color)
            y_pos, page_num = check_page(y_pos, c, page_num)
            c.drawString(x_margin, y_pos, draft.headline)
            y_pos -= line_height

        if draft.summary:
            c.setFont("Helvetica", font_size)
            c.setFillColor(primary_color)
            chars_per_line = int((width - 2 * x_margin) / (font_size * 0.45))
            words = draft.summary.split()
            line = ""
            for w in words:
                if len(line) + len(w) + 1 <= chars_per_line:
                    line += w + " "
                else:
                    y_pos, page_num = check_page(y_pos, c, page_num)
                    c.drawString(x_margin, y_pos, line.strip())
                    y_pos -= line_height
                    line = w + " "
            if line:
                y_pos, page_num = check_page(y_pos, c, page_num)
                c.drawString(x_margin, y_pos, line.strip())
                y_pos -= line_height
        y_pos -= line_height * 0.5

    # Skills
    if draft.skills:
        y_pos, page_num = draw_section_header("Skills", y_pos, c, page_num)
        c.setFont("Helvetica", font_size)
        c.setFillColor(primary_color)
        for cat, skills in draft.skills.items():
            y_pos, page_num = check_page(y_pos, c, page_num)
            c.setFont("Helvetica-Bold", font_size)
            c.drawString(x_margin, y_pos, f"{cat}: ")
            c.setFont("Helvetica", font_size)
            c.drawString(x_margin + c.stringWidth(f"{cat}: ", "Helvetica-Bold", font_size), y_pos, ", ".join(skills))
            y_pos -= line_height
        y_pos -= line_height * 0.5

    # Experience
    if draft.experience:
        y_pos, page_num = draw_section_header("Experience", y_pos, c, page_num)
        chars_per_line = int((width - 2 * x_margin - 15) / (font_size * 0.45))

        for exp in draft.experience:
            y_pos, page_num = check_page(y_pos, c, page_num, line_height * 3)

            # Title & Company
            c.setFont("Helvetica-Bold", font_size + 1)
            c.setFillColor(primary_color)
            c.drawString(x_margin, y_pos, f"{exp.title}")
            c.setFont("Helvetica", font_size + 1)
            c.drawString(x_margin + c.stringWidth(f"{exp.title} ", "Helvetica-Bold", font_size + 1), y_pos, f"| {exp.company}")

            # Dates (Right aligned)
            c.setFont("Helvetica", font_size - 1)
            c.setFillColor(secondary_color)
            date_str = exp.dates + (f" | {exp.location}" if exp.location else "")
            c.drawRightString(width - x_margin, y_pos, date_str)
            y_pos -= line_height * 1.2

            c.setFillColor(primary_color)
            c.setFont("Helvetica", font_size)

            for b in exp.bullets:
                b_words = b.split()
                b_line = ""
                first_line = True
                for w in b_words:
                    if len(b_line) + len(w) + 1 <= chars_per_line:
                        b_line += w + " "
                    else:
                        y_pos, page_num = check_page(y_pos, c, page_num)
                        if first_line:
                            c.drawString(x_margin + 10, y_pos, "• " + b_line.strip())
                            first_line = False
                        else:
                            c.drawString(x_margin + 20, y_pos, b_line.strip())
                        y_pos -= line_height
                        b_line = w + " "
                if b_line:
                    y_pos, page_num = check_page(y_pos, c, page_num)
                    if first_line:
                        c.drawString(x_margin + 10, y_pos, "• " + b_line.strip())
                    else:
                        c.drawString(x_margin + 20, y_pos, b_line.strip())
                    y_pos -= line_height
            y_pos -= line_height * 0.5

    # Projects
    if draft.projects:
        y_pos, page_num = draw_section_header("Projects", y_pos, c, page_num)
        for p in draft.projects:
            y_pos, page_num = check_page(y_pos, c, page_num, line_height * 2)
            c.setFont("Helvetica-Bold", font_size)
            c.setFillColor(primary_color)
            p_head = p.name
            if p.link:
                p_head += f" | {p.link}"
            c.drawString(x_margin, y_pos, p_head)

            if p.technologies:
                c.setFont("Helvetica", font_size - 1)
                c.setFillColor(secondary_color)
                c.drawRightString(width - x_margin, y_pos, f"Tech: {', '.join(p.technologies)}")

            y_pos -= line_height
            c.setFont("Helvetica", font_size)
            c.setFillColor(primary_color)

            chars_per_line = int((width - 2 * x_margin) / (font_size * 0.45))
            p_words = p.description.split()
            p_line = ""
            for w in p_words:
                if len(p_line) + len(w) + 1 <= chars_per_line:
                    p_line += w + " "
                else:
                    y_pos, page_num = check_page(y_pos, c, page_num)
                    c.drawString(x_margin, y_pos, p_line.strip())
                    y_pos -= line_height
                    p_line = w + " "
            if p_line:
                y_pos, page_num = check_page(y_pos, c, page_num)
                c.drawString(x_margin, y_pos, p_line.strip())
                y_pos -= line_height
            y_pos -= line_height * 0.5

    # Education
    if master.education:
        y_pos, page_num = draw_section_header("Education", y_pos, c, page_num)
        c.setFont("Helvetica", font_size)
        c.setFillColor(primary_color)
        for e in master.education:
            y_pos, page_num = check_page(y_pos, c, page_num)
            c.setFont("Helvetica-Bold", font_size)
            c.drawString(x_margin, y_pos, e.degree)
            c.setFont("Helvetica", font_size)
            c.drawString(x_margin + c.stringWidth(e.degree + " ", "Helvetica-Bold", font_size), y_pos, f"| {e.institution}")
            c.setFont("Helvetica", font_size - 1)
            c.setFillColor(secondary_color)
            c.drawRightString(width - x_margin, y_pos, e.dates)
            c.setFillColor(primary_color)
            y_pos -= line_height
        y_pos -= line_height * 0.5

    # Certifications
    if master.certifications:
        y_pos, page_num = draw_section_header("Certifications", y_pos, c, page_num)
        c.setFont("Helvetica", font_size)
        c.setFillColor(primary_color)
        for c_item in master.certifications:
            y_pos, page_num = check_page(y_pos, c, page_num)
            c.setFont("Helvetica-Bold", font_size)
            c.drawString(x_margin, y_pos, c_item.name)
            c.setFont("Helvetica", font_size)
            c.drawString(x_margin + c.stringWidth(c_item.name + " ", "Helvetica-Bold", font_size), y_pos, f"| {c_item.issuer}")
            if c_item.dates:
                c.setFont("Helvetica", font_size - 1)
                c.setFillColor(secondary_color)
                c.drawRightString(width - x_margin, y_pos, c_item.dates)
                c.setFillColor(primary_color)
            y_pos -= line_height

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
