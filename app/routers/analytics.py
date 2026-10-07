"""
Analytics Router - API endpoints for analytics and reporting.
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import func, and_, extract
from io import BytesIO
import base64

from app.core.database import get_db
from app.models.models import Event, Case, Staff

# Create router
router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_date_range(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> tuple[datetime, datetime]:
    """
    Parse date range parameters or default to last 30 days.
    
    Args:
        start_date: Optional start date string (YYYY-MM-DD)
        end_date: Optional end date string (YYYY-MM-DD)
        
    Returns:
        tuple: (start_datetime, end_datetime)
    """
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start_dt = datetime.now() - timedelta(days=30)
    
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)  # Include the end date
    else:
        end_dt = datetime.now() + timedelta(days=1)  # Include today
    
    return start_dt, end_dt


@router.get("/case-volume")
async def get_case_volume(
    request: Request,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get case volume by week/month (count of "case_created" events over time).
    Scoped to the logged-in staff's office only.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get the office ID from session
    office_id = request.session.get("office_id")
    
    # Get date range
    start_dt, end_dt = get_date_range(start_date, end_date)
    
    try:
        # Query case_created events grouped by date
        case_volume = db.query(
            func.date(Event.created_at).label('date'),
            func.count(Event.id).label('count')
        ).filter(
            Event.office_id == office_id,
            Event.event_type == "case_created",
            Event.created_at >= start_dt,
            Event.created_at < end_dt
        ).group_by(
            func.date(Event.created_at)
        ).order_by(
            func.date(Event.created_at)
        ).all()
        
        # Convert to list of dicts
        result = [
            {"date": str(row.date), "count": row.count}
            for row in case_volume
        ]
        
        return {
            "success": True,
            "data": result,
            "start_date": start_dt.strftime("%Y-%m-%d"),
            "end_date": (end_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching case volume: {str(e)}")


@router.get("/turnaround-time")
async def get_turnaround_time(
    request: Request,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get average turnaround time between "case_created" and "case_completed" events per service_type.
    Scoped to the logged-in staff's office only.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get the office ID from session
    office_id = request.session.get("office_id")
    
    # Get date range
    start_dt, end_dt = get_date_range(start_date, end_date)
    
    try:
        # Subquery to get case_created events
        created_events = db.query(
            Event.case_id,
            Event.created_at.label('created_time')
        ).filter(
            Event.office_id == office_id,
            Event.event_type == "case_created"
        ).subquery()
        
        # Subquery to get case_completed events
        completed_events = db.query(
            Event.case_id,
            Event.created_at.label('completed_time')
        ).filter(
            Event.office_id == office_id,
            Event.event_type == "case_completed"
        ).subquery()
        
        # Join with cases to get service_type
        turnaround_data = db.query(
            Case.service_type,
            func.avg(
                (completed_events.c.completed_time - created_events.c.created_time)
            ).label('avg_interval')
        ).join(
            created_events, Case.id == created_events.c.case_id
        ).join(
            completed_events, Case.id == completed_events.c.case_id
        ).filter(
            Case.office_id == office_id,
            created_events.c.created_time >= start_dt,
            created_events.c.created_time < end_dt
        ).group_by(
            Case.service_type
        ).all()
        
        # Convert to list of dicts (convert interval to hours for better readability)
        result = [
            {
                "service_type": row.service_type or "Unknown",
                "avg_turnaround_hours": round(row.avg_interval.total_seconds() / 3600, 2) if row.avg_interval else 0
            }
            for row in turnaround_data
        ]
        
        return {
            "success": True,
            "data": result,
            "start_date": start_dt.strftime("%Y-%m-%d"),
            "end_date": (end_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching turnaround time: {str(e)}")


@router.get("/document-bottlenecks")
async def get_document_bottlenecks(
    request: Request,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get document bottlenecks - which document_type has the longest average gap
    between "document_requested" and "document_received" events.
    Scoped to the logged-in staff's office only.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get the office ID from session
    office_id = request.session.get("office_id")
    
    # Get date range
    start_dt, end_dt = get_date_range(start_date, end_date)
    
    try:
        # Subquery to get document_requested events
        requested_events = db.query(
            Event.case_id,
            Event.created_at.label('requested_time'),
            Event.description
        ).filter(
            Event.office_id == office_id,
            Event.event_type == "document_requested"
        ).subquery()
        
        # Subquery to get document_received events
        received_events = db.query(
            Event.case_id,
            Event.created_at.label('received_time'),
            Event.description
        ).filter(
            Event.office_id == office_id,
            Event.event_type == "document_received"
        ).subquery()
        
        # Join and calculate average gap by document type
        # Extract document_type from description (assuming format: "Document requested: ID Proof")
        bottleneck_data = db.query(
            func.substr(requested_events.c.description, 21).label('document_type'),
            func.avg(
                (received_events.c.received_time - requested_events.c.requested_time)
            ).label('avg_interval')
        ).join(
            received_events, requested_events.c.case_id == received_events.c.case_id
        ).filter(
            requested_events.c.requested_time >= start_dt,
            requested_events.c.requested_time < end_dt
        ).group_by(
            func.substr(requested_events.c.description, 21)
        ).order_by(
            func.avg(
                (received_events.c.received_time - requested_events.c.requested_time)
            ).desc()
        ).all()
        
        # Convert to list of dicts (convert interval to hours for better readability)
        result = [
            {
                "document_type": row.document_type or "Unknown",
                "avg_gap_hours": round(row.avg_interval.total_seconds() / 3600, 2) if row.avg_interval else 0
            }
            for row in bottleneck_data
        ]
        
        return {
            "success": True,
            "data": result,
            "start_date": start_dt.strftime("%Y-%m-%d"),
            "end_date": (end_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching document bottlenecks: {str(e)}")


@router.get("/staff-performance")
async def get_staff_performance(
    request: Request,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get staff performance - cases closed per staff member in a selected period.
    Scoped to the logged-in staff's office only.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get the office ID from session
    office_id = request.session.get("office_id")
    
    # Get date range
    start_dt, end_dt = get_date_range(start_date, end_date)
    
    try:
        # Query case_completed events grouped by staff member
        staff_performance = db.query(
            Event.created_by.label('staff_email'),
            func.count(Event.id).label('cases_closed')
        ).filter(
            Event.office_id == office_id,
            Event.event_type == "case_completed",
            Event.created_at >= start_dt,
            Event.created_at < end_dt,
            Event.created_by.isnot(None)
        ).group_by(
            Event.created_by
        ).order_by(
            func.count(Event.id).desc()
        ).all()
        
        # Get staff names for emails
        staff_emails = [row.staff_email for row in staff_performance]
        staff_info = db.query(Staff.email, Staff.full_name).filter(
            Staff.email.in_(staff_emails)
        ).all()
        
        # Create email to name mapping
        email_to_name = {row.email: row.full_name for row in staff_info}
        
        # Convert to list of dicts
        result = [
            {
                "staff_email": row.staff_email,
                "staff_name": email_to_name.get(row.staff_email, row.staff_email),
                "cases_closed": row.cases_closed
            }
            for row in staff_performance
        ]
        
        return {
            "success": True,
            "data": result,
            "start_date": start_dt.strftime("%Y-%m-%d"),
            "end_date": (end_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching staff performance: {str(e)}")


@router.get("/dashboard")
async def get_analytics_dashboard(
    request: Request,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get all analytics data in a single call for the dashboard.
    Scoped to the logged-in staff's office only.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Get all analytics data
        case_volume = await get_case_volume(request, start_date, end_date, db)
        turnaround_time = await get_turnaround_time(request, start_date, end_date, db)
        document_bottlenecks = await get_document_bottlenecks(request, start_date, end_date, db)
        staff_performance = await get_staff_performance(request, start_date, end_date, db)
        
        return {
            "success": True,
            "case_volume": case_volume["data"],
            "turnaround_time": turnaround_time["data"],
            "document_bottlenecks": document_bottlenecks["data"],
            "staff_performance": staff_performance["data"],
            "start_date": case_volume["start_date"],
            "end_date": case_volume["end_date"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching analytics dashboard: {str(e)}")


@router.get("/export-pdf")
async def export_analytics_pdf(
    request: Request,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Export analytics report as PDF with charts as images.
    Scoped to the logged-in staff's office only.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Get all analytics data
        analytics_data = await get_analytics_dashboard(request, start_date, end_date, db)
        
        # Import PDF generation
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        
        # Create PDF buffer
        buffer = BytesIO()
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
        primary_900 = colors.HexColor('#263d4f')
        primary_600 = colors.HexColor('#447090')
        gray_500 = colors.HexColor('#6b7280')
        
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
        header_data = [[Paragraph("<b>RTO Autopilot - Analytics Report</b>", header_style)]]
        header_table = Table(header_data, colWidths=[5 * inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), primary_900),
            ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (0, 0), 20),
            ('BOTTOMPADDING', (0, 0), (0, 0), 20),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Report date range
        story.append(Paragraph(f"<b>Report Period:</b> {analytics_data['start_date']} to {analytics_data['end_date']}", normal_style))
        story.append(Spacer(1, 0.2 * inch))
        
        # Case Volume Section
        story.append(Paragraph("<b>Case Volume Summary</b>", section_style))
        if analytics_data['case_volume']:
            total_cases = sum(item['count'] for item in analytics_data['case_volume'])
            story.append(Paragraph(f"Total cases created: {total_cases}", normal_style))
            story.append(Paragraph(f"Average daily cases: {round(total_cases / len(analytics_data['case_volume']), 2)}", normal_style))
        else:
            story.append(Paragraph("No case volume data available for this period.", normal_style))
        story.append(Spacer(1, 0.2 * inch))
        
        # Turnaround Time Section
        story.append(Paragraph("<b>Average Turnaround Time by Service Type</b>", section_style))
        if analytics_data['turnaround_time']:
            turnaround_data = [['Service Type', 'Avg Turnaround (Hours)']]
            for item in analytics_data['turnaround_time']:
                turnaround_data.append([item['service_type'], str(item['avg_turnaround_hours'])])
            
            turnaround_table = Table(turnaround_data, colWidths=[2.5 * inch, 1.5 * inch])
            turnaround_table.setStyle(TableStyle([
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
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(turnaround_table)
        else:
            story.append(Paragraph("No turnaround time data available for this period.", normal_style))
        story.append(Spacer(1, 0.2 * inch))
        
        # Document Bottlenecks Section
        story.append(Paragraph("<b>Document Bottlenecks</b>", section_style))
        if analytics_data['document_bottlenecks']:
            bottleneck_data = [['Document Type', 'Avg Gap (Hours)']]
            for item in analytics_data['document_bottlenecks']:
                bottleneck_data.append([item['document_type'], str(item['avg_gap_hours'])])
            
            bottleneck_table = Table(bottleneck_data, colWidths=[2.5 * inch, 1.5 * inch])
            bottleneck_table.setStyle(TableStyle([
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
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(bottleneck_table)
        else:
            story.append(Paragraph("No document bottleneck data available for this period.", normal_style))
        story.append(Spacer(1, 0.2 * inch))
        
        # Staff Performance Section
        story.append(Paragraph("<b>Staff Performance</b>", section_style))
        if analytics_data['staff_performance']:
            staff_data = [['Staff Member', 'Cases Closed']]
            for item in analytics_data['staff_performance']:
                staff_data.append([item['staff_name'], str(item['cases_closed'])])
            
            staff_table = Table(staff_data, colWidths=[2.5 * inch, 1.5 * inch])
            staff_table.setStyle(TableStyle([
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
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(staff_table)
        else:
            story.append(Paragraph("No staff performance data available for this period.", normal_style))
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
        story.append(Paragraph("Internal analytics report — generated by RTO Autopilot.", footer_style))
        
        # Build PDF
        pdf_doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        # Return PDF as downloadable file
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=analytics_report_{datetime.now().strftime('%Y%m%d')}.pdf"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")