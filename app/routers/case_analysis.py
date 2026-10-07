"""
Case Analysis Router - API endpoints for AI-powered case analysis.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.core.database import get_db
from app.services.case_analysis import analyze_case

# Create router
router = APIRouter(prefix="/cases", tags=["case_analysis"])


@router.get("/{case_id}/analyze")
async def analyze_case_endpoint(
    case_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Analyze a case using AI to identify issues, provide summary, and suggest next actions.
    Scoped to the logged-in staff's office only.
    
    Args:
        case_id: The ID of the case to analyze
        request: FastAPI request object
        db: Database session
        
    Returns:
        JSON response with analysis results including:
        - issues: List of issues with severity and description
        - summary: Plain-language explanation of current stage
        - blocking_issue: Description of blocking issue or null
        - next_action: Suggested next action
        - confidence: Confidence score based on real signals
        - signals: Dictionary of signals used for confidence calculation
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get the office ID from session
    office_id = request.session.get("office_id")
    
    try:
        # First verify the case belongs to this office
        from app.models.models import Case
        case = db.query(Case).filter(
            Case.id == case_id,
            Case.office_id == office_id
        ).first()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Perform the analysis
        analysis_result = analyze_case(case_id, db)
        
        return JSONResponse(content=analysis_result)
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing case: {str(e)}")