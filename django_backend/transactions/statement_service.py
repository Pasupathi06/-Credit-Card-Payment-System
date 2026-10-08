from io import BytesIO
from decimal import Decimal

from django.http import FileResponse
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


def generate_monthly_statement(user, year, month):
    from transactions.models import Transaction

    transactions = (
        Transaction.objects.filter(
            user=user,
            created_at__year=year,
            created_at__month=month,
        )
        .select_related("card")
        .order_by("-created_at")
    )

    total_spending = (
        transactions.filter(status="SUCCESS")
        .aggregate_total()
        if False
        else sum(
            (
                transaction.amount
                for transaction in transactions
                if transaction.status == "SUCCESS"
            ),
            Decimal("0.00"),
        )
    )

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "StatementTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        spaceAfter=10,
    )

    right_style = ParagraphStyle(
        "RightText",
        parent=styles["Normal"],
        alignment=TA_RIGHT,
    )

    story = []

    story.append(
        Paragraph(
            "Credit Card Monthly Statement",
            title_style,
        )
    )

    story.append(
        Paragraph(
            f"<b>Customer:</b> {user.get_full_name() or user.username}",
            styles["Normal"],
        )
    )

    story.append(
        Paragraph(
            f"<b>Email:</b> {user.email}",
            styles["Normal"],
        )
    )

    story.append(
        Paragraph(
            f"<b>Statement Period:</b> {year}-{month:02d}",
            styles["Normal"],
        )
    )

    story.append(Spacer(1, 10))

    story.append(
        Paragraph(
            f"<b>Total Spending:</b> ₹{total_spending:,.2f}",
            right_style,
        )
    )

    story.append(Spacer(1, 15))

    data = [
        [
            "Date",
            "Transaction",
            "Card",
            "Amount",
            "Status",
        ]
    ]

    for transaction in transactions:
        card_details = "N/A"

        if transaction.card:
            card_details = (
                f"{transaction.card.card_type} "
                f"****{transaction.card.last4}"
            )

        data.append(
            [
                transaction.created_at.strftime(
                    "%d-%m-%Y"
                ),
                transaction.description or "-",
                card_details,
                f"₹{transaction.amount:,.2f}",
                transaction.status,
            ]
        )

    table = Table(
        data,
        repeatRows=1,
        colWidths=[
            25 * mm,
            50 * mm,
            35 * mm,
            30 * mm,
            25 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#1f2937"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "ALIGN",
                    (3, 1),
                    (3, -1),
                    "RIGHT",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, 0),
                    8,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, 0),
                    8,
                ),
            ]
        )
    )

    story.append(table)

    story.append(Spacer(1, 15))

    story.append(
        Paragraph(
            "<b>Security:</b> Full card numbers and CVV are "
            "never displayed in this statement.",
            styles["Normal"],
        )
    )

    document.build(story)

    buffer.seek(0)

    return FileResponse(
        buffer,
        as_attachment=True,
        filename=(
            f"monthly_statement_{year}_{month:02d}.pdf"
        ),
        content_type="application/pdf",
    )