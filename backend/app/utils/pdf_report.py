from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def build_analyst_pdf(report: dict) -> BytesIO:
    """
    Creates a downloadable source-cited analyst-style PDF report.
    """

    output = BytesIO()

    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
    )

    styles = getSampleStyleSheet()
    elements = []

    company = report["company_name"]
    year = report.get("fiscal_year") or "Annual Report"

    elements.append(
        Paragraph(
            "Multi-Agent Financial Research Report",
            styles["Title"],
        )
    )
    elements.append(
        Paragraph(
            f"<b>Company:</b> {company}<br/>"
            f"<b>Fiscal Year:</b> {year}",
            styles["BodyText"],
        )
    )
    elements.append(Spacer(1, 14))

    elements.append(
        Paragraph("Executive Summary", styles["Heading2"])
    )
    elements.append(
        Paragraph(report["executive_summary"], styles["BodyText"])
    )
    elements.append(Spacer(1, 14))

    elements.append(
        Paragraph("Key Financials", styles["Heading2"])
    )

    metric_rows = [["Metric", "Value", "Period", "Source Page"]]

    for metric in report.get("key_financials", []):
        metric_rows.append(
            [
                metric["metric_name"],
                metric["metric_value"],
                metric.get("period") or "Annual report period",
                str(metric["source_page"]),
            ]
        )

    if len(metric_rows) == 1:
        metric_rows.append(
            ["No key metrics extracted", "—", "—", "—"]
        )

    metrics_table = Table(
        metric_rows,
        colWidths=[1.8 * inch, 1.5 * inch, 1.8 * inch, 0.9 * inch],
    )

    metrics_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4f91")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    elements.append(metrics_table)
    elements.append(Spacer(1, 14))

    elements.append(
        Paragraph("Red Flag and Risk Review", styles["Heading2"])
    )

    flag_rows = [["Severity", "Category", "Finding", "Source Page"]]

    for flag in report.get("red_flags", []):
        flag_rows.append(
            [
                flag["severity"].upper(),
                flag["category"],
                flag["title"],
                str(flag["source_page"]),
            ]
        )

    if len(flag_rows) == 1:
        flag_rows.append(
            ["—", "No direct warning signals", "No findings returned", "—"]
        )

    flags_table = Table(
        flag_rows,
        colWidths=[0.8 * inch, 1.4 * inch, 3.1 * inch, 0.9 * inch],
    )

    flags_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#9b1c1c")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#fff7f7")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    elements.append(flags_table)
    elements.append(Spacer(1, 16))

    elements.append(
        Paragraph(
            "Source Faithfulness Note: Every metric and risk signal in this "
            "report is linked to the uploaded annual report through its "
            "stored source-page reference.",
            styles["BodyText"],
        )
    )

    document.build(elements)
    output.seek(0)

    return output