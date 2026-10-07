"""
Intake Router - API endpoints for the conversational intake feature.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.models.models import Customer, Case, Event, Office
from app.services.intake_agent import IntakeAgent, SERVICE_TYPES

# Setup rate limiting for intake endpoints
limiter = Limiter(key_func=get_remote_address)

# Create router with prefix to avoid conflicts
router = APIRouter(prefix="/intake/api", tags=["intake"])

# Global agent instance (in production, you'd use session management)
agent = IntakeAgent()

class MessageRequest(BaseModel):
    """Request model for chat messages."""
    message: str
    reset: Optional[bool] = False

class MessageResponse(BaseModel):
    """Response model for chat messages."""
    reply: str
    ready_to_submit: bool
    service_type: Optional[str] = None
    collected_data: Optional[Dict[str, Any]] = None

class SubmitRequest(BaseModel):
    """Request model for submitting collected data."""
    service_type: str
    collected_data: Dict[str, Any]

@router.get("", response_model=dict)
@limiter.limit("20/minute")  # 20 requests per minute for intake page
async def get_intake_page_context(request: Request):
    """Get initial context for the intake page."""
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    welcome_message = agent.initialize_conversation()
    
    return {
        "welcome_message": welcome_message,
        "available_services": SERVICE_TYPES
    }

@router.post("/message", response_model=MessageResponse)
@limiter.limit("30/minute")  # 30 messages per minute (conversational flow)
async def process_message(request: MessageRequest, http_request: Request):
    """
    Process a user message in the intake conversation.
    
    Args:
        request: MessageRequest containing the user's message and optional reset flag
        http_request: FastAPI request object for session access
        
    Returns:
        MessageResponse with the agent's reply and conversation state
    """
    # Check if user is logged in
    staff_id = http_request.session.get("staff_id")
    if not staff_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Reset conversation if requested
        if request.reset:
            agent.reset()
            welcome_message = agent.initialize_conversation()
            return MessageResponse(
                reply=welcome_message,
                ready_to_submit=False,
                service_type=None,
                collected_data={}
            )
        
        # Process the message
        response = agent.process_message(request.message)
        
        return MessageResponse(**response)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@router.post("/submit")
@limiter.limit("10/minute")  # 10 submissions per minute (case creation)
async def submit_intake(request: SubmitRequest, http_request: Request, db: Session = Depends(get_db)):
    """
    Submit the collected intake data to create a Customer and Case.
    
    Args:
        request: SubmitRequest with service type and collected data
        http_request: FastAPI request object for session access
        db: Database session
        
    Returns:
        JSON response with success status and case details
    """
    # Check if user is logged in
    staff_id = http_request.session.get("staff_id")
    if not staff_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get the office ID from session
    office_id = http_request.session.get("office_id")
    staff_email = http_request.session.get("staff_email")
    
    try:
        # Validate service type
        if request.service_type not in SERVICE_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid service type: {request.service_type}")
        
        # Get the office from session (not the first office in database)
        office = db.query(Office).filter(Office.id == office_id).first()
        if not office:
            raise HTTPException(status_code=404, detail="Office not found")
        
        # Extract customer data
        full_name = request.collected_data.get("full_name", "Unknown")
        phone = request.collected_data.get("phone", "")
        email = request.collected_data.get("email", "")
        address = request.collected_data.get("address", "")
        
        # Create customer for the authenticated user's office
        new_customer = Customer(
            office_id=office_id,
            full_name=full_name,
            phone=phone if phone else None,
            email=email if email else None,
            address=address if address else None
        )
        db.add(new_customer)
        db.flush()  # Get customer ID without committing
        
        # Create case for the authenticated user's office
        service_name = SERVICE_TYPES[request.service_type]["name"]
        new_case = Case(
            office_id=office_id,
            customer_id=new_customer.id,
            service_type=service_name,
            status="new",
            vehicle_number=request.collected_data.get("vehicle_number"),
            notes=f"Created via conversational intake. Service: {service_name}"
        )
        db.add(new_case)
        db.flush()  # Get case ID without committing
        
        # Create event log
        new_event = Event(
            case_id=new_case.id,
            office_id=office_id,
            event_type="case_created",
            description=f"Case created via conversational intake for {service_name}",
            created_by=staff_email or "intake_system"
        )
        db.add(new_event)
        
        db.commit()
        
        # Reset the agent for the next conversation
        agent.reset()
        
        return {
            "success": True,
            "message": f"Successfully created case #{new_case.id} for {full_name}",
            "case_id": new_case.id,
            "customer_id": new_customer.id,
            "service_type": service_name,
            "redirect_url": f"/case/{new_case.id}"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error submitting intake: {str(e)}")

@router.post("/reset")
@limiter.limit("20/minute")  # 20 resets per minute
async def reset_intake(request: Request):
    """Reset the intake conversation."""
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    agent.reset()
    welcome_message = agent.initialize_conversation()
    
    return {
        "success": True,
        "message": "Conversation reset",
        "welcome_message": welcome_message
    }