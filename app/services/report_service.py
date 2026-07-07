"""Builds the downloadable PDF for a single prediction - the risk result,
the SHAP explanation (if available), and enough patient context to make
the page useful to hand to a real doctor.

Uses reportlab directly rather than a templating layer since this is one
fixed, fairly simple layout - not worth a heavier abstraction for now.
"""
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)

DISEASE_LABELS = {
    "diabetes": "Diabetes",
    "heart": "Heart Disease",
    "parkinsons": "Parkinson's Disease",
    "kidney": "Kidney Disease (CKD)",
}


def build_prediction_report_pdf(prediction, patient_name: str, contributions: list | None) -> bytes:
    """Returns the finished PDF as raw bytes, ready to stream back in an
    HTTP response - nothing here touches the DB or the request/response
    cycle, so it's easy to test or reuse (e.g. for a future "email me
    a copy" feature) independent of the endpoint that calls it.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], fontSize=18, spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle", parent=styles["Normal"], fontSize=10, textColor=colors.grey, spaceAfter=16,
    )
    section_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading2"], spaceBefore=16, spaceAfter=8,
    )
    body_style = styles["Normal"]

    disease_label = DISEASE_LABELS.get(prediction.disease, prediction.disease.title())
    is_high_risk = prediction.risk_level == "High Risk"
    risk_color = colors.HexColor("#c0392b") if is_high_risk else colors.HexColor("#27ae60")

    elements = []

    elements.append(Paragraph("P.H.D. Prediction - Health Screening Report", title_style))
    elements.append(Paragraph(
        f"Generated on {datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')}", subtitle_style
    ))

    # --- Patient / prediction summary table ---
    summary_data = [
        ["Patient", patient_name],
        ["Condition screened", disease_label],
        ["Result", prediction.risk_level],
        ["Confidence", f"{prediction.probability * 100:.1f}%"],
        ["Prediction date", prediction.created_at.strftime("%d %b %Y, %H:%M UTC")],
    ]
    summary_table = Table(summary_data, colWidths=[5 * cm, 10 * cm])
    summary_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (1, 2), (1, 2), risk_color),
        ("FONTNAME", (1, 2), (1, 2), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#dddddd")),
    ]))
    elements.append(summary_table)

    # --- Contributing factors (SHAP), if available ---
    if contributions:
        elements.append(Paragraph("What most influenced this result", section_style))
        elements.append(Paragraph(
            "Ranked by how much each factor pushed the result toward or away from "
            "High Risk, based on this specific prediction.", body_style
        ))
        elements.append(Spacer(1, 8))

        rows = [["Factor", "Your value", "Effect"]]
        for c in contributions[:10]:
            direction = "Increases risk" if c["contribution"] > 0 else "Decreases risk"
            rows.append([c["feature"], str(c["value"]), direction])

        factor_table = Table(rows, colWidths=[6 * cm, 4 * cm, 5 * cm])
        factor_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#eeeeee")),
        ]))
        elements.append(factor_table)

    elements.append(Spacer(1, 24))
    elements.append(Paragraph(
        "<i>This report is a screening estimate produced by a machine learning "
        "model, not a medical diagnosis. Please discuss this result with a "
        "qualified healthcare professional before making any medical decisions.</i>",
        ParagraphStyle("Disclaimer", parent=body_style, fontSize=8, textColor=colors.grey),
    ))

    doc.build(elements)
    return buffer.getvalue()
