from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

from django.db.models import Avg


def _mask_email(email):
    if not email:
        return ''
    parts = email.split('@')
    if len(parts) != 2:
        return '***'
    return parts[0][:2] + '***@' + parts[1]


def _mask_phone(phone):
    if not phone or len(phone) < 4:
        return '***'
    return phone[:4] + '***' + phone[-2:]


def _pct(part, total):
    return (part / total * 100) if total else 0


def build_pdf_report(report_type, complaints_qs, missions, form_data):
    total_complaints = complaints_qs.count()
    avg_rating = complaints_qs.aggregate(avg=Avg('rating'))['avg'] or 0
    positive_count = complaints_qs.filter(rating__gte=4).count()
    neutral_count = complaints_qs.filter(rating=3).count()
    negative_count = complaints_qs.filter(rating__lte=2).count()

    best_missions = missions.filter(average_rating__isnull=False).order_by('-average_rating')[:5]
    worst_missions = missions.filter(average_rating__isnull=False).order_by('average_rating')[:5]
    most_complained = missions.filter(complaint_count__gt=0).order_by('-complaint_count')[:5]

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=50,
        bottomMargin=50,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCenter', parent=styles['Title'], alignment=TA_CENTER, fontSize=22, spaceAfter=20))
    styles.add(ParagraphStyle(name='H1', parent=styles['Heading1'], fontSize=16, spaceBefore=10, spaceAfter=8))
    styles.add(ParagraphStyle(name='Body', parent=styles['BodyText'], fontSize=10, leading=14))

    story = []
    consulate = form_data.get('consulate') or 'All Consulates'
    date_range = form_data.get('date')
    include_complaints = form_data.get('include_complaints', True)
    include_sentiment = form_data.get('include_sentiment', True)

    story.append(Paragraph('Somali Missions – Complaint Report', styles['TitleCenter']))
    story.append(Paragraph(f'<b>Report type:</b> {report_type}', styles['Body']))
    story.append(Paragraph('Prepared for: Ministry of Foreign Affairs', styles['Body']))
    story.append(Spacer(1, 10))
    dr_text = str(date_range) if date_range else 'Not specified'
    story.append(Paragraph(f'<b>Date Range:</b> {dr_text}', styles['Body']))
    story.append(Paragraph(f'<b>Consulate Filter:</b> {consulate}', styles['Body']))
    story.append(PageBreak())

    if report_type == 'monthly_summary':
        story.append(Paragraph('Monthly Performance Summary (Last 30 Days Focus)', styles['H1']))
        story.append(Paragraph(
            f'Total complaints in selection: <b>{total_complaints}</b>. '
            f'Average rating: <b>{avg_rating:.1f}/5</b>.',
            styles['Body'],
        ))
        if include_sentiment:
            story.append(Paragraph(
                f'Sentiment proxy: { _pct(positive_count, total_complaints):.1f}% positive, '
                f'{_pct(neutral_count, total_complaints):.1f}% neutral, '
                f'{_pct(negative_count, total_complaints):.1f}% negative.',
                styles['Body'],
            ))
        story.append(PageBreak())

    elif report_type == 'analytics':
        story.append(Paragraph('Platform Analytics Overview', styles['H1']))
        metrics_data = [
            ['Indicator', 'Value'],
            ['Total Complaints', str(total_complaints)],
            ['Average Rating', f'{avg_rating:.1f} / 5'],
            ['Positive Ratio', f'{_pct(positive_count, total_complaints):.1f}%'],
            ['Neutral Ratio', f'{_pct(neutral_count, total_complaints):.1f}%'],
            ['Negative Ratio', f'{_pct(negative_count, total_complaints):.1f}%'],
        ]
        metrics_table = Table(metrics_data, colWidths=[3.2 * inch, 2.5 * inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#307de8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
        ]))
        story.append(metrics_table)
        story.append(Spacer(1, 12))

        def build_rank_table(title, rows):
            story.append(Paragraph(title, styles['H1']))
            data = [['Rank', 'Mission', 'Avg Rating', '# Complaints']]
            for idx, mission in enumerate(rows, start=1):
                data.append([
                    str(idx),
                    mission.name,
                    f'{(mission.average_rating or 0):.1f}',
                    str(mission.complaint_count or 0),
                ])
            table = Table(data, colWidths=[0.6 * inch, 3.0 * inch, 1.0 * inch, 1.2 * inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.black),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]))
            story.append(table)
            story.append(Spacer(1, 12))

        build_rank_table('Best-Rated Missions', best_missions)
        build_rank_table('Most Complained Missions', most_complained)
        build_rank_table('Lowest-Rated Missions', worst_missions)
        doc.build(story)
        buffer.seek(0)
        return buffer

    # complaint_log (default) — detailed per-mission + optional complaint list
    story.append(Paragraph('Executive Summary', styles['H1']))
    story.append(Paragraph(
        f'Recorded <b>{total_complaints}</b> complaints. Average score: <b>{avg_rating:.1f}/5</b>.',
        styles['Body'],
    ))
    story.append(PageBreak())

    story.append(Paragraph('Complaint Log Summary (Per Mission)', styles['H1']))
    for mission in missions:
        mission_complaints = complaints_qs.filter(mission=mission)
        if not mission_complaints.exists():
            continue
        m_total = mission_complaints.count()
        m_avg = mission_complaints.aggregate(avg=Avg('rating'))['avg'] or 0
        story.append(Paragraph(f'<b>Mission:</b> {mission.name}', styles['Body']))
        story.append(Paragraph(f'Complaints: {m_total} | Avg Rating: {m_avg:.1f}', styles['Body']))
        story.append(Spacer(1, 8))

    if include_complaints:
        story.append(PageBreak())
        story.append(Paragraph('Detailed Complaint List', styles['H1']))
        for index, complaint in enumerate(complaints_qs.order_by('-created_at'), start=1):
            user_display = 'Anonymous' if complaint.is_anonymous else (complaint.full_name or 'Anonymous')
            story.append(Paragraph(
                f'<b>#{index}</b> [{complaint.tracking_code}] — {complaint.created_at.date()} — {complaint.mission.name}',
                styles['Body'],
            ))
            story.append(Paragraph(f'Rating: {complaint.rating}/5 | Status: {complaint.get_status_display()}', styles['Body']))
            story.append(Paragraph(f'<b>Subject:</b> {complaint.subject}', styles['Body']))
            story.append(Paragraph(f'<b>Message:</b> {complaint.message}', styles['Body']))
            story.append(Paragraph(f'<b>User:</b> {user_display}', styles['Body']))
            if complaint.email:
                story.append(Paragraph(f'<b>Email:</b> {_mask_email(complaint.email)}', styles['Body']))
            if complaint.phone:
                story.append(Paragraph(f'<b>Phone:</b> {_mask_phone(complaint.phone)}', styles['Body']))
            story.append(Spacer(1, 10))

    doc.build(story)
    buffer.seek(0)
    return buffer
