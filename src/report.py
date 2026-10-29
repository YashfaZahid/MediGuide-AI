"""Build a simple downloadable PDF guidance report (bonus feature)."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any


def _pdf_text(text: Any) -> str:
    """Helvetica core fonts need Latin-1-safe text."""
    raw = str(text or "").strip() or "-"
    return raw.encode("latin-1", errors="replace").decode("latin-1")


def build_guidance_pdf(
    assessment: dict[str, Any],
    normalized: dict[str, Any],
) -> bytes:
    """Create a PDF report from the assessment JSON + intake fields."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()
    usable = pdf.w - pdf.l_margin - pdf.r_margin

    def heading(text: str, size: int = 12) -> None:
        pdf.set_font("Helvetica", "B", size)
        pdf.multi_cell(usable, 8, _pdf_text(text))

    def body(text: str, size: int = 10) -> None:
        pdf.set_font("Helvetica", "", size)
        pdf.multi_cell(usable, 5, _pdf_text(text))

    heading("MediGuide AI - Educational Guidance Report", 16)
    body(
        "Educational prototype only. Not a medical diagnosis, prescription, "
        "or emergency service. Consult a licensed healthcare professional."
    )
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(
        usable,
        5,
        _pdf_text(
            f"Generated (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
        ),
    )
    pdf.ln(3)

    heading("Patient intake")
    for line in [
        f"Age: {_pdf_text(normalized.get('age'))}",
        f"Gender: {_pdf_text(normalized.get('gender'))}",
        f"Symptoms: {_pdf_text(normalized.get('symptoms_text'))}",
        f"Duration: {_pdf_text(normalized.get('duration'))}",
        f"Severity: {_pdf_text(normalized.get('severity'))}/10",
        f"Existing conditions: {_pdf_text(normalized.get('existing_conditions'))}",
        f"Medications: {_pdf_text(normalized.get('medications'))}",
        f"Notes: {_pdf_text(normalized.get('notes'))}",
        f"Language: {_pdf_text(normalized.get('language'))}",
    ]:
        body(line)

    pdf.ln(2)
    heading("Assessment summary")
    body(assessment.get("summary"))
    pdf.ln(1)
    heading(f"Urgency: {_pdf_text(assessment.get('urgency_level')).upper()}", 11)

    pdf.ln(2)
    heading("Possible conditions (education only)")
    conditions = assessment.get("possible_conditions") or []
    if not conditions:
        body("None listed.")
    for item in conditions:
        if isinstance(item, dict):
            body(f"- {_pdf_text(item.get('name'))}: {_pdf_text(item.get('reason'))}")
        else:
            body(f"- {_pdf_text(item)}")

    def bullets(title: str, values: list[Any]) -> None:
        pdf.ln(2)
        heading(title)
        if not values:
            body("None listed.")
            return
        for value in values:
            body(f"- {_pdf_text(value)}")

    bullets(
        "Recommended next steps",
        list(assessment.get("recommended_next_steps") or []),
    )
    bullets(
        "Questions for a doctor",
        list(assessment.get("questions_for_doctor") or []),
    )
    bullets("Warning signs", list(assessment.get("warning_signs") or []))

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(
        usable,
        5,
        _pdf_text(
            "If symptoms are severe or worsening - especially chest pain or "
            "trouble breathing - seek emergency care immediately."
        ),
    )

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()
