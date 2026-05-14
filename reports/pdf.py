from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


def _fig_to_png_bytes(fig, dpi=150):
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=dpi)
    buf.seek(0)
    return buf


def build_pdf_report(title, settings, metrics, figures):
    """
    settings: dict
    metrics: dict
    figures: list of tuples [("Figure Title", matplotlib_fig), ...]
    Returns: bytes (PDF)
    """
    pdf_buf = BytesIO()
    doc = SimpleDocTemplate(pdf_buf, pagesize=letter, leftMargin=0.7*inch, rightMargin=0.7*inch,
                            topMargin=0.7*inch, bottomMargin=0.7*inch)

    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(title, styles["Title"]))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    # Settings table
    story.append(Paragraph("Strategy Settings", styles["Heading2"]))
    settings_rows = [["Key", "Value"]] + [[str(k), str(v)] for k, v in settings.items()]
    t1 = Table(settings_rows, colWidths=[2.2*inch, 3.6*inch])
    t1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
    ]))
    story.append(t1)
    story.append(Spacer(1, 0.25 * inch))

    # Metrics table
    story.append(Paragraph("Key Metrics", styles["Heading2"]))
    metrics_rows = [["Key", "Value"]] + [[str(k), str(v)] for k, v in metrics.items()]
    t2 = Table(metrics_rows, colWidths=[2.2*inch, 3.6*inch])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
    ]))
    story.append(t2)
    story.append(Spacer(1, 0.25 * inch))

    # Figures
    story.append(Paragraph("Charts", styles["Heading2"]))

    for fig_title, fig in figures:
        story.append(Paragraph(str(fig_title), styles["Heading3"]))
        png_buf = _fig_to_png_bytes(fig)

        # Fit image to page width
        img = Image(png_buf, width=6.2*inch, height=3.3*inch)
        story.append(img)
        story.append(Spacer(1, 0.2 * inch))

    doc.build(story)
    pdf_buf.seek(0)
    return pdf_buf.getvalue()
