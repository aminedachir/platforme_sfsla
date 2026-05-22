"""
app/utils/certificate.py
------------------------
Generates professional Arabic certificate PDFs for PSFSLA.
Uses reportlab + arabic-reshaper + python-bidi for RTL rendering.

Requirements (pip):
    reportlab arabic-reshaper python-bidi

System fonts required (apt):
    fonts-noto-extra  (provides NotoNaskhArabic-*.ttf)
"""

import os
import io
from datetime import datetime, timezone

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
import arabic_reshaper
from bidi.algorithm import get_display

# ── Font paths ────────────────────────────────────────────────────────────────
_FONT_DIR   = "/usr/share/fonts/truetype/noto"
_FONT_REG   = os.path.join(_FONT_DIR, "NotoNaskhArabic-Regular.ttf")
_FONT_BOLD  = os.path.join(_FONT_DIR, "NotoNaskhArabic-Bold.ttf")
_FONT_SEMI  = os.path.join(_FONT_DIR, "NotoNaskhArabic-SemiBold.ttf")

# Allow override via env for Docker/production
_FONT_REG  = os.environ.get("PSF_FONT_REG",  _FONT_REG)
_FONT_BOLD = os.environ.get("PSF_FONT_BOLD", _FONT_BOLD)

# ── Register once ─────────────────────────────────────────────────────────────
def _register_fonts():
    """Register Arabic fonts with ReportLab (idempotent)."""
    if "NaskhAr" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("NaskhAr",     _FONT_REG))
        pdfmetrics.registerFont(TTFont("NaskhArBold", _FONT_BOLD))
        if os.path.exists(_FONT_SEMI):
            pdfmetrics.registerFont(TTFont("NaskhArSemi", _FONT_SEMI))
        else:
            pdfmetrics.registerFont(TTFont("NaskhArSemi", _FONT_BOLD))

_register_fonts()


# ── Arabic helper ─────────────────────────────────────────────────────────────
def _ar(text: str) -> str:
    """Reshape + apply BiDi algorithm so Arabic renders correctly in PDF."""
    return get_display(arabic_reshaper.reshape(str(text)))


# ── Color palette ─────────────────────────────────────────────────────────────
NAVY      = colors.HexColor("#1B2A52")
NAVY_DARK = colors.HexColor("#0F1A38")
NAVY_MID  = colors.HexColor("#2A3E80")
GOLD      = colors.HexColor("#F0B429")
GOLD_DARK = colors.HexColor("#C8921A")
WHITE     = colors.white
GRAY_LIGHT= colors.HexColor("#F2F5FD")
GRAY_TEXT = colors.HexColor("#4B5563")
GREEN     = colors.HexColor("#16A34A")


# ── Certificate ID generator ──────────────────────────────────────────────────
def generate_certificate_id() -> str:
    """
    Return a unique certificate ID in the format PSFSLA-YYYY-NNNNN.
    Uses the Certificate table to determine the next sequence number.
    Import is deferred to avoid circular imports at module load time.
    """
    from app.models import Certificate  # deferred import
    year = datetime.now(timezone.utc).year
    # Count existing certs this year
    prefix = f"PSFSLA-{year}-"
    count = Certificate.query.filter(
        Certificate.certificate_id.like(f"{prefix}%")
    ).count()
    return f"{prefix}{(count + 1):05d}"


# ── Drawing helpers ───────────────────────────────────────────────────────────
def _draw_background(c, W, H):
    """Navy gradient-like background using layered rectangles."""
    # Base fill
    c.setFillColor(NAVY_DARK)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Subtle lighter panel
    c.setFillColor(NAVY)
    c.rect(15*mm, 15*mm, W - 30*mm, H - 30*mm, fill=1, stroke=0)


def _draw_border(c, W, H):
    """Decorative double border."""
    # Outer gold border
    c.setStrokeColor(GOLD)
    c.setLineWidth(3)
    c.rect(12*mm, 12*mm, W - 24*mm, H - 24*mm, fill=0, stroke=1)

    # Inner thin border
    c.setStrokeColor(GOLD_DARK)
    c.setLineWidth(0.8)
    c.rect(16*mm, 16*mm, W - 32*mm, H - 32*mm, fill=0, stroke=1)


def _draw_corner_ornaments(c, W, H):
    """Simple circle ornaments at each corner."""
    r = 5*mm
    positions = [
        (12*mm, 12*mm),
        (W - 12*mm, 12*mm),
        (12*mm, H - 12*mm),
        (W - 12*mm, H - 12*mm),
    ]
    c.setFillColor(GOLD)
    c.setStrokeColor(GOLD_DARK)
    c.setLineWidth(1)
    for x, y in positions:
        c.circle(x, y, r, fill=1, stroke=1)
        c.setFillColor(NAVY_DARK)
        c.circle(x, y, r * 0.5, fill=1, stroke=0)
        c.setFillColor(GOLD)


def _draw_header(c, W, H):
    """Organisation logo area and title block."""
    # Top decorative band
    c.setFillColor(GOLD)
    c.rect(16*mm, H - 40*mm, W - 32*mm, 6*mm, fill=1, stroke=0)

    # Org name
    c.setFont("NaskhArBold", 13)
    c.setFillColor(GOLD)
    c.drawCentredString(W / 2, H - 52*mm, _ar("المنصة الوطنية للتكوين المستمر في الأنظمة الفيزيائية"))

    # Sub-line
    c.setFont("NaskhAr", 9)
    c.setFillColor(WHITE)
    c.drawCentredString(W / 2, H - 60*mm, _ar("PSFSLA — Plateforme de Formation Continue"))

    # Thin separator
    c.setStrokeColor(GOLD_DARK)
    c.setLineWidth(0.6)
    c.line(40*mm, H - 64*mm, W - 40*mm, H - 64*mm)


def _draw_seal(c, W, H):
    """Draw a simple circular seal / stamp in bottom-left area."""
    cx, cy = 55*mm, 55*mm
    # Outer ring
    c.setStrokeColor(GOLD)
    c.setFillColor(colors.HexColor("#162045"))
    c.setLineWidth(2)
    c.circle(cx, cy, 22*mm, fill=1, stroke=1)
    # Inner ring
    c.setStrokeColor(GOLD_DARK)
    c.setLineWidth(0.8)
    c.circle(cx, cy, 17*mm, fill=0, stroke=1)
    # Text
    c.setFont("NaskhArBold", 7)
    c.setFillColor(GOLD)
    c.drawCentredString(cx, cy + 5*mm,  _ar("شهادة معتمدة"))
    c.drawCentredString(cx, cy - 2*mm,  _ar("PSFSLA"))
    c.drawCentredString(cx, cy - 9*mm,  _ar("الجزائر"))


def _draw_qr_placeholder(c, W, H, verify_url: str):
    """Draw a QR code placeholder box with verification URL text."""
    # In production replace this with: import qrcode; draw QR image
    bx, by = W - 65*mm, 30*mm
    bw, bh = 35*mm, 35*mm

    c.setFillColor(WHITE)
    c.setStrokeColor(GOLD_DARK)
    c.setLineWidth(0.8)
    c.rect(bx, by, bw, bh, fill=1, stroke=1)

    # QR icon hint
    c.setFillColor(NAVY)
    c.setFont("NaskhAr", 6)
    c.drawCentredString(bx + bw/2, by + bh/2 + 3*mm, _ar("رمز التحقق"))
    c.setFont("Helvetica", 5)
    c.setFillColor(GRAY_TEXT)
    # Truncate URL for display
    short = verify_url[-35:] if len(verify_url) > 35 else verify_url
    c.drawCentredString(bx + bw/2, by + 4*mm, short)


# ── Public API ────────────────────────────────────────────────────────────────
def generate_certificate_pdf(
    student_full_name: str,
    course_title_ar: str,
    course_title_fr: str,
    certificate_id: str,
    issued_at: datetime,
    professor_name: str = "",
    duration_hours: int = 0,
    verify_url: str = "",
    output_path: str = None,
) -> bytes:
    """
    Generate a certificate PDF and return raw bytes.
    If *output_path* is provided the PDF is also written to disk.

    Parameters
    ----------
    student_full_name : str   Full name of the student (Arabic preferred)
    course_title_ar   : str   Course title in Arabic
    course_title_fr   : str   Course title in French
    certificate_id    : str   Unique ID, e.g. PSFSLA-2024-00001
    issued_at         : datetime
    professor_name    : str   Name of the instructor
    duration_hours    : int   Course duration in hours
    verify_url        : str   URL for online verification
    output_path       : str   Optional filesystem path to save PDF

    Returns
    -------
    bytes  Raw PDF content
    """
    buf = io.BytesIO()
    W, H = A4  # 595.27 × 841.89 pt  (portrait)

    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"شهادة - {student_full_name}")
    c.setAuthor("PSFSLA")
    c.setSubject(course_title_fr)

    # ── Background & borders ──────────────────────────────────
    _draw_background(c, W, H)
    _draw_border(c, W, H)
    _draw_corner_ornaments(c, W, H)

    # ── Header ────────────────────────────────────────────────
    _draw_header(c, W, H)

    # ── Main title ────────────────────────────────────────────
    c.setFont("NaskhArBold", 30)
    c.setFillColor(GOLD)
    c.drawCentredString(W / 2, H - 90*mm, _ar("شهادة إتمام التكوين"))

    # Decorative line under title
    line_y = H - 96*mm
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.5)
    c.line(W/2 - 50*mm, line_y, W/2 + 50*mm, line_y)

    # ── Body text ─────────────────────────────────────────────
    c.setFont("NaskhAr", 13)
    c.setFillColor(WHITE)
    c.drawCentredString(W / 2, H - 107*mm, _ar("تُشهد المنصة الوطنية للتكوين المستمر بأن:"))

    # Student name block
    name_y = H - 123*mm
    c.setFillColor(colors.HexColor("#162045"))
    c.roundRect(W/2 - 80*mm, name_y - 8*mm, 160*mm, 18*mm,
                radius=3*mm, fill=1, stroke=0)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.roundRect(W/2 - 80*mm, name_y - 8*mm, 160*mm, 18*mm,
                radius=3*mm, fill=0, stroke=1)

    c.setFont("NaskhArBold", 20)
    c.setFillColor(GOLD)
    c.drawCentredString(W / 2, name_y + 1*mm, _ar(student_full_name))

    # Completion text
    c.setFont("NaskhAr", 12)
    c.setFillColor(WHITE)
    c.drawCentredString(W / 2, H - 138*mm, _ar("قد أتمّ بنجاح متطلبات التكوين:"))

    # Course title (Arabic)
    c.setFont("NaskhArBold", 16)
    c.setFillColor(GOLD)
    c.drawCentredString(W / 2, H - 150*mm, _ar(course_title_ar))

    # Course title (French) – smaller
    if course_title_fr:
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#94A3B8"))
        c.drawCentredString(W / 2, H - 159*mm, course_title_fr)

    # Details row
    details_y = H - 173*mm
    c.setFont("NaskhAr", 10)
    c.setFillColor(colors.HexColor("#CBD5E1"))

    details = []
    if duration_hours:
        details.append(_ar(f"المدة: {duration_hours} ساعة"))
    if professor_name:
        details.append(_ar(f"المكوّن: {professor_name}"))
    details.append(_ar(f"تاريخ الإصدار: {issued_at.strftime('%d/%m/%Y')}"))

    detail_str = "   |   ".join(details)
    c.drawCentredString(W / 2, details_y, detail_str)

    # ── Separator ─────────────────────────────────────────────
    sep_y = H - 185*mm
    c.setStrokeColor(colors.HexColor("#2A3E80"))
    c.setLineWidth(0.5)
    c.line(25*mm, sep_y, W - 25*mm, sep_y)

    # ── Certificate ID ────────────────────────────────────────
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#64748B"))
    c.drawCentredString(W / 2, H - 193*mm, f"Certificate ID: {certificate_id}")

    # ── Seal & QR ─────────────────────────────────────────────
    _draw_seal(c, W, H)
    if verify_url:
        _draw_qr_placeholder(c, W, H, verify_url)

    # ── Bottom signature block ────────────────────────────────
    sig_y = 42*mm
    # Director signature line
    c.setStrokeColor(colors.HexColor("#334155"))
    c.setLineWidth(0.6)
    sig_x = W / 2 + 20*mm
    c.line(sig_x, sig_y, sig_x + 50*mm, sig_y)
    c.setFont("NaskhAr", 9)
    c.setFillColor(colors.HexColor("#94A3B8"))
    c.drawCentredString(sig_x + 25*mm, sig_y - 5*mm, _ar("المدير العام"))
    c.drawCentredString(sig_x + 25*mm, sig_y - 11*mm, _ar("PSFSLA"))

    # Bottom gold band
    c.setFillColor(GOLD)
    c.rect(16*mm, 16*mm, W - 32*mm, 5*mm, fill=1, stroke=0)

    # ── Finish ────────────────────────────────────────────────
    c.showPage()
    c.save()

    pdf_bytes = buf.getvalue()

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)

    return pdf_bytes


# ── Convenience wrapper (Flask context) ───────────────────────────────────────
def issue_certificate(enrollment, base_url: str = "", save_dir: str = "") -> "Certificate":
    """
    High-level helper called from routes.
    Creates a Certificate DB record and generates the PDF file.

    Parameters
    ----------
    enrollment : Enrollment   The completed enrollment object
    base_url   : str          App base URL for the verify link (e.g. https://psfsla.dz)
    save_dir   : str          Directory to store PDF files (e.g. app.config['CERT_FOLDER'])

    Returns
    -------
    Certificate  (not yet committed — caller must db.session.commit())
    """
    from app.models import Certificate  # deferred
    from app.extensions import db

    # Check if certificate already exists
    existing = Certificate.query.filter_by(
        student_id=enrollment.student_id,
        course_id=enrollment.course_id,
    ).first()
    if existing:
        return existing

    cert_id = generate_certificate_id()
    verify_url = f"{base_url}/verify/{cert_id}" if base_url else f"/verify/{cert_id}"

    student  = enrollment.student
    course   = enrollment.course
    prof     = course.professor

    # Determine save path
    pdf_rel  = None
    pdf_path = None
    if save_dir:
        pdf_rel  = f"certificates/{cert_id}.pdf"
        pdf_path = os.path.join(save_dir, f"{cert_id}.pdf")

    generate_certificate_pdf(
        student_full_name=student.full_name,
        course_title_ar=course.title_ar,
        course_title_fr=course.title_fr,
        certificate_id=cert_id,
        issued_at=datetime.now(timezone.utc),
        professor_name=prof.full_name if prof else "",
        duration_hours=course.duration_hours or 0,
        verify_url=verify_url,
        output_path=pdf_path,
    )

    cert = Certificate(
        certificate_id=cert_id,
        student_id=enrollment.student_id,
        course_id=enrollment.course_id,
        file_path=pdf_rel,
        is_valid=True,
    )
    db.session.add(cert)
    return cert