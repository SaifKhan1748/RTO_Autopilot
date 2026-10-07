from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from sqlalchemy.orm import Session
from app.models.models import Case, Document


def generate_case_pdf(case_id: int, db: Session) -> bytes:
    """
    Generate a PDF for a given case including customer info and document checklist.
    
    Args:
        case_id: The ID of the case to generate PDF for
        db: Database session
        
    Returns:
        bytes: The generated PDF as bytes
    """
    # Import here to avoid circular imports
    from sqlalchemy.orm import joinedload
    
    # Fetch the case with customer and documents
    case = db.query(Case).options(
        joinedload(Case.customer),
        joinedload(Case.documents)
    ).filter(Case.id == case_id).first()
    
    if not case:
        raise ValueError(f"Case with ID {case_id} not found")
    
    # Create PDF buffer
    buffer = BytesIO()
    
    # Renamed to pdf_doc to avoid conflict with `for doc in case.documents`
    pdf_doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Story (content elements)
    story = []
    
    # Define custom colors matching the web app
    primary_900 = colors.HexColor('#263d4f')  # Dark blue (header background)
    primary_600 = colors.HexColor('#447090')  # Medium blue (buttons)
    primary_500 = colors.HexColor('#5c8aab')  # Light blue
    gray_500 = colors.HexColor('#6b7280')    # Gray text
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom header style
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.white,
        alignment=TA_CENTER,
        spaceAfter=20,
        spaceBefore=0
    )
    
    # Custom section header style
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=primary_900,
        spaceAfter=10,
        spaceBefore=20
    )
    
    # Custom normal text style
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.black,
        spaceAfter=5
    )
    
    # Header with brand color background
    header_data = [[Paragraph("<b>RTO Autopilot</b>", header_style)]]
    header_table = Table(header_data, colWidths=[5 * inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), primary_900),
        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (0, 0), 20),
        ('BOTTOMPADDING', (0, 0), (0, 0), 20),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.3 * inch))
    
    # Case Information Section
    story.append(Paragraph("<b>Case Information</b>", section_style))
    
    # Customer info table
    case_info_data = [
        ['Customer Name:', case.customer.full_name if case.customer else 'N/A'],
        ['Phone:', case.customer.phone if (case.customer and case.customer.phone) else 'N/A'],
        ['Service Type:', case.service_type or 'N/A'],
        ['Status:', case.status.capitalize() if case.status else 'N/A'],
        ['Vehicle Number:', case.vehicle_number or 'N/A'],
        ['Created:', case.created_at.strftime('%Y-%m-%d %H:%M') if case.created_at else 'N/A'],
    ]
    
    case_info_table = Table(case_info_data, colWidths=[1.5 * inch, 3.5 * inch])
    case_info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (0, -1), gray_500),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(case_info_table)
    story.append(Spacer(1, 0.2 * inch))
    
    # Document Checklist Section
    story.append(Paragraph("<b>Document Checklist</b>", section_style))
    
    # Prepare document data
    if case.documents:
        doc_data = [['Document Type', 'Received', 'Date Received']]
        for doc in case.documents:
            # Check if document object indicates upload/received status
            received_status = "Yes" if getattr(doc, 'uploaded_at', None) or getattr(doc, 'is_received', True) else "No"
            date_received = doc.uploaded_at.strftime('%Y-%m-%d') if getattr(doc, 'uploaded_at', None) else 'N/A'
            doc_data.append([getattr(doc, 'document_type', 'Unknown'), received_status, date_received])
    else:
        doc_data = [['Document Type', 'Received', 'Date Received']]
        doc_data.append(['No documents uploaded', '-', '-'])
    
    # Create document table
    doc_table = Table(doc_data, colWidths=[2.5 * inch, 1 * inch, 1.5 * inch])
    doc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_600),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('GRID', (0, 0), (-1, -1), 1, colors.gray),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(doc_table)
    story.append(Spacer(1, 0.4 * inch))
    
    # Footer note
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=gray_500,
        alignment=TA_CENTER,
        spaceBefore=20
    )
    story.append(Paragraph("Internal preparation document — not a government-issued document.", footer_style))
    
    # Build PDF using the renamed variable `pdf_doc`
    pdf_doc.build(story)
    
    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes