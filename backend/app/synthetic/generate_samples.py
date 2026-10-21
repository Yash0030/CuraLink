"""Synthetic PDF and Test Data Generator for Personal Health Record Organizer.

Generates realistic medical PDFs covering all test cases:
- TC1: Valid lab reports for A1, CityScan Imaging, and Vitals (single combined timeline).
- TC2: Duplicate file with identical SHA-256 or Report ID (stored once).
- TC3: Look-alike name document ('Anita Sharma-Rao' vs expected 'Anita Sharma') -> exclude.
- TC4: HTML login page saved with .pdf extension -> fails not_pdf.
- Discrepancy: Portal date differing from internal PDF date -> goes to review.
"""

import io
from datetime import date
from typing import Dict, Any, Tuple
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def create_a1_report(
    patient_name: str = "Aarav Roy",
    patient_id: str = "pt001",
    report_id: str = "A-20260121-001-2",
    report_date: str = "2026-01-21",
    test_name: str = "Complete Blood Count (CBC)"
) -> bytes:
    """Generates an A1 Diagnostics PDF matching the table layout style."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    header_style = ParagraphStyle(
        'A1Header',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=12
    )

    meta_style = ParagraphStyle(
        'A1Meta',
        parent=styles['Normal'],
        fontSize=10,
        leading=14
    )

    story = [
        Paragraph("<b>A1 REFERENCE LABORATORIES & DIAGNOSTICS</b>", header_style),
        Paragraph("<i>Accredited Medical Diagnostics Facility</i>", styles['Italic']),
        Spacer(1, 15)
    ]

    meta_data = [
        [Paragraph(f"<b>Patient Name:</b> {patient_name}", meta_style), Paragraph(f"<b>Patient ID:</b> {patient_id}", meta_style)],
        [Paragraph(f"<b>Report ID:</b> {report_id}", meta_style), Paragraph(f"<b>Report Date:</b> {report_date}", meta_style)],
        [Paragraph(f"<b>Test / Examination:</b> {test_name}", meta_style), Paragraph("<b>Status:</b> Final / Verified", meta_style)],
    ]
    t_meta = Table(meta_data, colWidths=[270, 270])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 20))

    # Test Results Table
    results_data = [
        ["Investigation", "Observed Value", "Reference Range", "Units"],
        ["Hemoglobin", "14.2", "13.0 - 17.0", "g/dL"],
        ["RBC Count", "4.8", "4.5 - 5.5", "mil/uL"],
        ["WBC Count", "6,500", "4,000 - 11,000", "/uL"],
        ["Platelet Count", "240,000", "150,000 - 450,000", "/uL"],
    ]
    t_results = Table(results_data, colWidths=[180, 120, 140, 100])
    t_results.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#94A3B8')),
    ]))
    story.append(t_results)
    doc.build(story)
    return buffer.getvalue()

def create_cityscan_report(
    patient_name: str = "ROY, AARAV",
    patient_id: str = "pt001",
    report_id: str = "B-20260122-004-1",
    report_date: str = "2026-01-22",
    test_name: str = "Chest X-Ray PA View"
) -> bytes:
    """Generates a CityScan Imaging PDF report."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    header_style = ParagraphStyle(
        'CityScanHeader',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#0F766E'),
        spaceAfter=12
    )
    meta_style = ParagraphStyle('CSMeta', parent=styles['Normal'], fontSize=10, leading=14)

    story = [
        Paragraph("<b>CITYSCAN ADVANCED IMAGING CENTER</b>", header_style),
        Paragraph("Department of Radiodiagnosis & Imaging", styles['Normal']),
        Spacer(1, 15)
    ]

    meta_data = [
        [Paragraph(f"<b>PATIENT NAME:</b> {patient_name}", meta_style), Paragraph(f"<b>MRN / Patient ID:</b> {patient_id}", meta_style)],
        [Paragraph(f"<b>Scan ID / Report No:</b> {report_id}", meta_style), Paragraph(f"<b>Exam Date:</b> {report_date}", meta_style)],
        [Paragraph(f"<b>Study / Procedure:</b> {test_name}", meta_style), Paragraph("<b>Modality:</b> Digital Radiography", meta_style)],
    ]
    t_meta = Table(meta_data, colWidths=[270, 270])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0FDFA')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#99F6E4')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CCFBF1')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 20))

    findings = [
        Paragraph("<b>CLINICAL INDICATION:</b> Routine health checkup.", meta_style),
        Spacer(1, 8),
        Paragraph("<b>FINDINGS:</b> Heart size is within normal limits. Lung fields are clear bilaterally with no active focal consolidation, effusion, or pneumothorax. Costophrenic angles are sharp.", meta_style),
        Spacer(1, 8),
        Paragraph("<b>IMPRESSION:</b> Normal chest radiograph.", meta_style)
    ]
    story.extend(findings)
    doc.build(story)
    return buffer.getvalue()

def create_vitals_report(
    patient_name: str = "Aarav Roy",
    patient_id: str = "pt001",
    report_id: str = "C-20260124-008-3",
    report_date: str = "2026-01-24",
    test_name: str = "Comprehensive Lipid Panel"
) -> bytes:
    """Generates a Vitals Health Laboratory PDF report."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    header_style = ParagraphStyle(
        'VitalsHeader',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#7E22CE'),
        spaceAfter=12
    )
    meta_style = ParagraphStyle('VMeta', parent=styles['Normal'], fontSize=10, leading=14)

    story = [
        Paragraph("<b>VITALS DIAGNOSTIC LABORATORIES</b>", header_style),
        Paragraph("Clinical Pathology & Biochemistry Division", styles['Normal']),
        Spacer(1, 15)
    ]

    meta_data = [
        [Paragraph(f"<b>Client / Patient:</b> {patient_name}", meta_style), Paragraph(f"<b>UHID / ID:</b> {patient_id}", meta_style)],
        [Paragraph(f"<b>Sample ID / Report Ref:</b> {report_id}", meta_style), Paragraph(f"<b>Collection Date:</b> {report_date}", meta_style)],
        [Paragraph(f"<b>Test Panel:</b> {test_name}", meta_style), Paragraph("<b>Specimen:</b> Serum", meta_style)],
    ]
    t_meta = Table(meta_data, colWidths=[270, 270])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FAF5FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E9D5FF')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#F3E8FF')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 20))

    results_data = [
        ["Parameter", "Result", "Standard Target", "Units"],
        ["Total Cholesterol", "185", "< 200", "mg/dL"],
        ["Triglycerides", "130", "< 150", "mg/dL"],
        ["HDL Cholesterol", "52", "> 40", "mg/dL"],
        ["LDL Cholesterol", "107", "< 100", "mg/dL"],
    ]
    t_results = Table(results_data, colWidths=[180, 120, 140, 100])
    t_results.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#7E22CE')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D8B4FE')),
    ]))
    story.append(t_results)
    doc.build(story)
    return buffer.getvalue()

def create_fake_html_pdf() -> bytes:
    """TC4: Simulates a login redirection HTML response mistakenly saved as .pdf."""
    html_content = (
        "<!DOCTYPE html>\n"
        "<html>\n"
        "<head><title>Portal Login</title></head>\n"
        "<body>\n"
        "<h2>Your session has expired. Please log in to continue.</h2>\n"
        "<form action='/login' method='post'>\n"
        "<input type='text' name='username' />\n"
        "<input type='password' name='password' />\n"
        "<button type='submit'>Login</button>\n"
        "</form>\n"
        "</body>\n"
        "</html>"
    )
    return html_content.encode('utf-8')
