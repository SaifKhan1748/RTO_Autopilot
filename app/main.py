from fastapi import FastAPI, Request, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, Response, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.core.database import engine, Base, get_db
from app.models.models import Staff, Case, Customer, Event, Document, PendingReminder, PolicyChunk, Office, ChecklistConfig, PasswordReset
from app.core.exceptions import setup_exception_handlers
from sqlalchemy.orm import Session, joinedload
from app.scheduler import start_scheduler, shutdown_scheduler, check_pending_documents
from app.services.pdf_generator import generate_case_pdf
from app.services.r2_storage import get_r2_service
from app.services.policy_rag import get_policy_rag_service
from app.routers import intake, analytics, case_analysis
import bcrypt
from datetime import datetime, timedelta
import secrets
import logging
import os

logger = logging.getLogger(__name__)

# Create the FastAPI app
app = FastAPI(title="RTO Autopilot")

# Setup centralized error handling
setup_exception_handlers(app)

# Helper function to check if request is from an authenticated staff member
def is_authenticated_staff(request: Request) -> bool:
    """Check if the request comes from an authenticated staff member."""
    return bool(request.session.get("staff_id"))

# Setup rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Clean error response when rate limit is exceeded."""
    if "text/html" in request.headers.get("accept", ""):
        return HTMLResponse(
            status_code=429,
            content=f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>Rate Limit Exceeded - RTO Autopilot</title>
                <script src="https://cdn.tailwindcss.com"></script>
            </head>
            <body class="bg-gray-50 flex items-center justify-center min-h-screen p-4">
                <div class="max-w-md w-full bg-white shadow-lg rounded-lg p-6 text-center border-t-4 border-red-500">
                    <h1 class="text-2xl font-bold text-gray-900 mb-2">Too Many Requests</h1>
                    <p class="text-gray-600 mb-6">You have exceeded the request limit ({exc.detail}). Please wait a minute and try again.</p>
                    <a href="javascript:history.back()" class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700">Go Back</a>
                </div>
            </body>
            </html>
            """
        )
    return _rate_limit_exceeded_handler(request, exc)

app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)

# Include the intake router
app.include_router(intake.router, tags=["intake"])

# Include the analytics router
app.include_router(analytics.router, tags=["analytics"])

# Include the case analysis router
app.include_router(case_analysis.router, tags=["case_analysis"])

# Add session middleware for login authentication
import os
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "fallback-secret-key"))

# Set up Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

# Mount static files directory for PWA assets
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Helper function to check admin role in route handlers
def check_admin_role(request: Request, db: Session):
    """
    Check if the logged-in user has admin role.
    Returns True if admin, False otherwise.
    Used in route handlers that need to redirect instead of raising exceptions.
    """
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return False
    
    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    return staff and staff.role == "admin"

# Create database tables (if they don't exist)
# Wrap in try-except to handle connection issues gracefully
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    logger.warning(f"Could not create database tables at startup: {e}")
    logger.info("Tables may already exist or will be created manually")

@app.get("/", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/offline", response_class=HTMLResponse)
async def offline_page(request: Request):
    """Render the offline page for PWA."""
    return templates.TemplateResponse(request=request, name="offline.html")

@app.get("/login", response_class=HTMLResponse)
@limiter.limit("20/minute")
async def login_page(request: Request):
    """Render the login page."""
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
@limiter.limit("20/minute")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Handle login form submission.
    Check email/password and create session if valid.
    Implements account lockout after 5 failed attempts with 15-minute cooldown.
    """
    # Find staff member by email
    staff = db.query(Staff).filter(Staff.email == email).first()
    
    # Check if account is locked
    if staff and staff.locked_until and staff.locked_until > datetime.utcnow():
        remaining_time = int((staff.locked_until - datetime.utcnow()).total_seconds() / 60)
        return templates.TemplateResponse(
            request=request, 
            name="login.html", 
            context={"error": f"Account locked. Try again in {remaining_time} minutes."}
        )
    
    # Verify staff exists, is active, and password is correct
    if not staff or not bcrypt.checkpw(password.encode('utf-8'), staff.password_hash.encode('utf-8')):
        # Increment failed login attempts
        if staff:
            staff.failed_login_attempts = (staff.failed_login_attempts or 0) + 1
            
            # Lock account after 5 failed attempts
            if staff.failed_login_attempts >= 5:
                staff.locked_until = datetime.utcnow() + timedelta(minutes=15)
                logger.warning(f"Account locked for {staff.email} after 5 failed login attempts")
                db.commit()
                return templates.TemplateResponse(
                    request=request, 
                    name="login.html", 
                    context={"error": "Account locked due to too many failed attempts. Try again in 15 minutes."}
                )
            
            db.commit()
        
        return templates.TemplateResponse(
            request=request, 
            name="login.html", 
            context={"error": "Invalid email or password"}
        )
    
    if staff.is_active != 1:
        return templates.TemplateResponse(
            request=request, 
            name="login.html", 
            context={"error": "Account is inactive"}
        )
    
    # Reset failed login attempts on successful login
    staff.failed_login_attempts = 0
    staff.locked_until = None
    db.commit()
    
    # Store staff info in session
    request.session["staff_id"] = staff.id
    request.session["staff_email"] = staff.email
    request.session["staff_name"] = staff.full_name
    request.session["office_id"] = staff.office_id
    request.session["office_name"] = staff.office.name
    request.session["office_display_name"] = staff.office.display_name or staff.office.name
    request.session["staff_role"] = staff.role
    
    logger.info(f"Successful login for {staff.email}")
    
    # Redirect to dashboard
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    """Clear session and redirect to login."""
    request.session.clear()
    logger.info("User logged out")
    return RedirectResponse(url="/login")

@app.get("/forgot-password", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def forgot_password_page(request: Request):
    """Render the forgot password page."""
    return templates.TemplateResponse(request=request, name="forgot_password.html")

@app.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Handle forgot password form submission.
    Generates a password reset token and emails it to the user.
    """
    try:
        # Find staff member by email
        staff = db.query(Staff).filter(Staff.email == email).first()
        
        if not staff:
            # Don't reveal whether email exists for security
            return templates.TemplateResponse(
                request=request,
                name="forgot_password.html",
                context={"success": "If an account with this email exists, a password reset link has been sent."}
            )
        
        # Generate a secure token
        token = secrets.token_urlsafe(32)
        
        # Calculate expiration (1 hour from now)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Create password reset record
        password_reset = PasswordReset(
            staff_id=staff.id,
            token=token,
            expires_at=expires_at
        )
        db.add(password_reset)
        db.commit()
        
        # Send email with reset link
        try:
            import resend
            resend.api_key = os.getenv("RESEND_API_KEY")
            
            reset_link = f"{request.base_url}reset-password?token={token}"
            
            params = {
                "from": "RTO Autopilot <noreply@rtoautopilot.com>",
                "to": [staff.email],
                "subject": "Password Reset Request",
                "html": f"""
                <h2>Password Reset Request</h2>
                <p>Hello {staff.full_name},</p>
                <p>You requested a password reset for your RTO Autopilot account.</p>
                <p>Click the link below to reset your password:</p>
                <p><a href="{reset_link}">Reset Password</a></p>
                <p>This link will expire in 1 hour.</p>
                <p>If you didn't request this, please ignore this email.</p>
                """
            }
            
            resend.Emails.send(params)
            logger.info(f"Password reset email sent to {staff.email}")
            
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")
            # Continue anyway - don't reveal the error to user
        
        return templates.TemplateResponse(
            request=request,
            name="forgot_password.html",
            context={"success": "If an account with this email exists, a password reset link has been sent."}
        )
        
    except Exception as e:
        logger.error(f"Error in forgot password: {e}")
        return templates.TemplateResponse(
            request=request,
            name="forgot_password.html",
            context={"error": "An error occurred. Please try again."}
        )

@app.get("/reset-password", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def reset_password_page(request: Request, token: str = None, db: Session = Depends(get_db)):
    """
    Render the reset password page.
    Validates the token before showing the form.
    """
    if not token:
        return templates.TemplateResponse(
            request=request,
            name="reset_password.html",
            context={"error": "Invalid reset link"}
        )
    
    # Find and validate the token
    password_reset = db.query(PasswordReset).filter(
        PasswordReset.token == token,
        PasswordReset.used == 0,
        PasswordReset.expires_at > datetime.utcnow()
    ).first()
    
    if not password_reset:
        return templates.TemplateResponse(
            request=request,
            name="reset_password.html",
            context={"error": "Invalid or expired reset link"}
        )
    
    return templates.TemplateResponse(
        request=request,
        name="reset_password.html",
        context={"token": token}
    )

@app.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    token: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Handle password reset form submission.
    Updates the password if the token is valid.
    """
    try:
        # Validate passwords match
        if new_password != confirm_password:
            return templates.TemplateResponse(
                request=request,
                name="reset_password.html",
                context={"token": token, "error": "Passwords do not match"}
            )
        
        # Find and validate the token
        password_reset = db.query(PasswordReset).filter(
            PasswordReset.token == token,
            PasswordReset.used == 0,
            PasswordReset.expires_at > datetime.utcnow()
        ).first()
        
        if not password_reset:
            return templates.TemplateResponse(
                request=request,
                name="reset_password.html",
                context={"error": "Invalid or expired reset link"}
            )
        
        # Get the staff member
        staff = db.query(Staff).filter(Staff.id == password_reset.staff_id).first()
        if not staff:
            return templates.TemplateResponse(
                request=request,
                name="reset_password.html",
                context={"error": "User not found"}
            )
        
        # Update password
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        staff.password_hash = password_hash
        staff.failed_login_attempts = 0  # Reset failed attempts
        staff.locked_until = None  # Unlock account if locked
        
        # Mark token as used
        password_reset.used = 1
        
        db.commit()
        
        logger.info(f"Password reset successful for {staff.email}")
        
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"success": "Password reset successful. Please login with your new password."}
        )
        
    except Exception as e:
        logger.error(f"Error in reset password: {e}")
        return templates.TemplateResponse(
            request=request,
            name="reset_password.html",
            context={"token": token, "error": "An error occurred. Please try again."}
        )

@app.get("/signup", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def signup_page(request: Request):
    """Render the office signup page."""
    return templates.TemplateResponse(request=request, name="signup.html")

@app.post("/signup")
@limiter.limit("5/minute")
async def signup(
    request: Request,
    office_name: str = Form(...),
    office_code: str = Form(...),
    admin_email: str = Form(...),
    admin_password: str = Form(...),
    admin_full_name: str = Form(...),
    display_name: str = Form(""),
    db: Session = Depends(get_db)
):
    """
    Handle office signup form submission.
    Creates a new Office and an admin Staff member.
    """
    try:
        # Check if office code already exists
        existing_office = db.query(Office).filter(Office.code == office_code).first()
        if existing_office:
            return templates.TemplateResponse(
                request=request,
                name="signup.html",
                context={"error": "Office code already exists. Please choose a different code."}
            )
        
        # Check if admin email already exists
        existing_staff = db.query(Staff).filter(Staff.email == admin_email).first()
        if existing_staff:
            return templates.TemplateResponse(
                request=request,
                name="signup.html",
                context={"error": "Email already exists. Please use a different email."}
            )
        
        # Create new office
        new_office = Office(
            name=office_name,
            code=office_code,
            display_name=display_name if display_name else None
        )
        db.add(new_office)
        db.flush()  # Get the office ID without committing yet
        
        # Hash the admin password
        password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create admin staff member
        new_admin = Staff(
            office_id=new_office.id,
            email=admin_email,
            password_hash=password_hash,
            full_name=admin_full_name,
            role="admin"
        )
        db.add(new_admin)
        
        # Create default checklist configurations for common service types
        default_service_types = [
            ("New Registration", ["ID Proof", "Address Proof", "Vehicle RC", "Insurance"]),
            ("Transfer", ["ID Proof", "Address Proof", "Vehicle RC", "Insurance", "NOC"]),
            ("Renewal", ["ID Proof", "Vehicle RC", "Insurance", "Emission Certificate"]),
            ("License Renewal", ["ID Proof", "Existing License", "Address Proof"])
        ]
        
        for service_type, documents in default_service_types:
            for order, document_type in enumerate(documents):
                checklist_config = ChecklistConfig(
                    office_id=new_office.id,
                    service_type=service_type,
                    document_type=document_type,
                    is_required=1,
                    display_order=order
                )
                db.add(checklist_config)
        
        db.commit()
        
        # Show success message
        return templates.TemplateResponse(
            request=request,
            name="signup.html",
            context={"success": f"Office '{office_name}' created successfully! You can now login with your admin credentials."}
        )
        
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse(
            request=request,
            name="signup.html",
            context={"error": f"Error creating office: {str(e)}"}
        )

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """
    Render the dashboard with cases for the logged-in staff member's office only.
    This ensures data isolation - each office sees only its own cases.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    # Get the office ID from session
    office_id = request.session.get("office_id")
    
    # Get staff info for display
    staff_name = request.session.get("staff_name", "Staff Member")
    office_display_name = request.session.get("office_display_name", "Office")
    staff_role = request.session.get("staff_role", "staff")
    
    # Get cases for this office only (data isolation)
    # Use join to get customer data efficiently
    cases = db.query(Case).options(joinedload(Case.customer)).filter(Case.office_id == office_id).all()
    
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "staff_name": staff_name,
            "office_display_name": office_display_name,
            "staff_role": staff_role,
            "cases": cases
        }
    )

@app.get("/add-customer", response_class=HTMLResponse)
async def add_customer_page(request: Request):
    """Render the add customer form page."""
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    return templates.TemplateResponse(
        request=request, 
        name="add_customer.html",
        context={
            "office_display_name": request.session.get("office_display_name"),
            "staff_role": request.session.get("staff_role")
        }
    )

@app.get("/intake", response_class=HTMLResponse)
async def intake_page(request: Request):
    """Render the conversational intake page."""
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    return templates.TemplateResponse(
        request=request, 
        name="intake.html",
        context={
            "office_display_name": request.session.get("office_display_name"),
            "staff_role": request.session.get("staff_role")
        }
    )

@app.post("/add-customer")
async def add_customer(
    request: Request,
    full_name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(""),
    address: str = Form(""),
    db: Session = Depends(get_db)
):
    """
    Handle add customer form submission.
    Creates a new customer tied to the logged-in staff member's office.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    # Get the office ID from session
    office_id = request.session.get("office_id")
    
    try:
        # Create new customer
        new_customer = Customer(
            office_id=office_id,
            full_name=full_name,
            phone=phone,
            email=email if email else None,
            address=address if address else None
        )
        db.add(new_customer)
        db.commit()
        
        # Redirect to dashboard with success
        return RedirectResponse(url="/dashboard", status_code=303)
        
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse(
            request=request,
            name="add_customer.html",
            context={"error": f"Error creating customer: {str(e)}"}
        )

@app.get("/new-case", response_class=HTMLResponse)
async def new_case_page(request: Request, db: Session = Depends(get_db)):
    """Render the new case form page with customer dropdown."""
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    # Get the office ID from session
    office_id = request.session.get("office_id")
    
    # Get customers for this office only
    customers = db.query(Customer).filter(Customer.office_id == office_id).all()
    
    return templates.TemplateResponse(
        request=request,
        name="new_case.html",
        context={
            "customers": customers,
            "office_display_name": request.session.get("office_display_name"),
            "staff_role": request.session.get("staff_role")
        }
    )

@app.post("/new-case")
async def new_case(
    request: Request,
    customer_id: int = Form(...),
    service_type: str = Form(...),
    vehicle_number: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db)
):
    """
    Handle new case form submission.
    Creates a new case and logs a case_created event.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    # Get the office ID and staff email from session
    office_id = request.session.get("office_id")
    staff_email = request.session.get("staff_email")
    
    try:
        # Verify customer belongs to this office
        customer = db.query(Customer).filter(
            Customer.id == customer_id,
            Customer.office_id == office_id
        ).first()
        
        if not customer:
            return templates.TemplateResponse(
                request=request,
                name="new_case.html",
                context={
                    "customers": db.query(Customer).filter(Customer.office_id == office_id).all(),
                    "error": "Invalid customer selected"
                }
            )
        
        # Create new case with status "new"
        new_case = Case(
            office_id=office_id,
            customer_id=customer_id,
            service_type=service_type,
            status="new",
            vehicle_number=vehicle_number if vehicle_number else None,
            notes=notes if notes else None
        )
        db.add(new_case)
        db.flush()  # Get the case ID without committing yet
        
        # Create event log for case creation
        new_event = Event(
            case_id=new_case.id,
            office_id=office_id,
            event_type="case_created",
            description=f"Case created for {service_type}",
            created_by=staff_email
        )
        db.add(new_event)
        
        db.commit()
        
        # Redirect to dashboard with success
        return RedirectResponse(url="/dashboard", status_code=303)
        
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse(
            request=request,
            name="new_case.html",
            context={
                "customers": db.query(Customer).filter(Customer.office_id == office_id).all(),
                "error": f"Error creating case: {str(e)}"
            }
        )

@app.get("/case/{case_id}", response_class=HTMLResponse)
async def case_detail(request: Request, case_id: int, db: Session = Depends(get_db)):
    """Render the case detail page with document upload and list."""
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    # Get the office ID from session
    office_id = request.session.get("office_id")
    
    # Get the case with customer and documents
    case = db.query(Case).options(
        joinedload(Case.customer),
        joinedload(Case.documents)
    ).filter(
        Case.id == case_id,
        Case.office_id == office_id
    ).first()
    
    if not case:
        # Case not found or doesn't belong to this office
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "staff_name": request.session.get("staff_name", "Staff Member"),
                "cases": db.query(Case).options(joinedload(Case.customer)).filter(Case.office_id == office_id).all(),
                "error": "Case not found"
            }
        )
    
    return templates.TemplateResponse(
        request=request,
        name="case_detail.html",
        context={
            "case": case,
            "office_display_name": request.session.get("office_display_name"),
            "staff_role": request.session.get("staff_role")
        }
    )

@app.get("/cases/{case_id}/pdf")
async def generate_case_pdf_endpoint(
    request: Request,
    case_id: int,
    db: Session = Depends(get_db)
):
    """
    Generate and return a PDF for a given case.
    Returns the PDF as a downloadable file.
    Route: GET /cases/{case_id}/pdf
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    # Get the office ID from session
    office_id = request.session.get("office_id")
    
    try:
        # Verify case belongs to this office
        case = db.query(Case).filter(
            Case.id == case_id,
            Case.office_id == office_id
        ).first()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Generate PDF
        pdf_bytes = generate_case_pdf(case_id, db)
        
        # Return PDF as downloadable file
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=case_{case_id}_pdf.pdf"
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")

@app.post("/case/{case_id}/upload")
async def upload_document(
    request: Request,
    case_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Handle document upload for a case.
    Uploads file to Cloudflare R2 storage and creates Document record.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    # Get the office ID and staff email from session
    office_id = request.session.get("office_id")
    staff_email = request.session.get("staff_email")
    
    try:
        # Verify case belongs to this office
        case = db.query(Case).filter(
            Case.id == case_id,
            Case.office_id == office_id
        ).first()
        
        if not case:
            return templates.TemplateResponse(
                request=request,
                name="case_detail.html",
                context={
                    "case": db.query(Case).options(
                        joinedload(Case.customer),
                        joinedload(Case.documents)
                    ).filter(Case.id == case_id).first(),
                    "error": "Case not found"
                }
            )
        
        # Get R2 storage service
        r2_service = get_r2_service()
        
        # Read file content
        file_content = await file.read()
        
        # Determine content type
        content_type = file.content_type
        
        # Upload to R2
        r2_object_key, file_url = r2_service.upload_file(
            file_content=file_content,
            file_name=file.filename,
            content_type=content_type
        )
        
        # Create document record with R2 object key
        new_document = Document(
            case_id=case_id,
            office_id=office_id,
            document_type=document_type,
            file_name=file.filename,
            r2_object_key=r2_object_key
        )
        db.add(new_document)
        db.flush()  # Get the document ID
        
        # Create event log for document upload
        new_event = Event(
            case_id=case_id,
            office_id=office_id,
            event_type="document_uploaded",
            description=f"Document uploaded: {document_type} ({file.filename})",
            created_by=staff_email
        )
        db.add(new_event)
        
        db.commit()
        
        # Redirect back to case detail page
        return RedirectResponse(url=f"/case/{case_id}", status_code=303)
        
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse(
            request=request,
            name="case_detail.html",
            context={
                "case": db.query(Case).options(
                    joinedload(Case.customer),
                    joinedload(Case.documents)
                ).filter(Case.id == case_id).first(),
                "error": f"Error uploading document: {str(e)}"
            }
        )

@app.get("/documents/{document_id}/download")
async def download_document(
    request: Request,
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Generate a signed URL for temporary document access.
    This endpoint provides secure, time-limited access to documents stored in R2.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    # Get the office ID from session
    office_id = request.session.get("office_id")
    
    try:
        # Get the document
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.office_id == office_id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get R2 storage service
        r2_service = get_r2_service()
        
        # Generate signed URL (valid for 10 minutes)
        signed_url = r2_service.generate_signed_url(
            object_key=document.r2_object_key,
            expiration_seconds=600  # 10 minutes
        )
        
        # Redirect to the signed URL
        return RedirectResponse(url=signed_url)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating download link: {str(e)}")

@app.get("/reminders", response_class=HTMLResponse)
async def reminders_page(request: Request, db: Session = Depends(get_db)):
    """
    Render the reminders page showing pending reminders for the logged-in staff member's office.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    # Get the office ID from session
    office_id = request.session.get("office_id")
    
    # Get staff info for display
    staff_name = request.session.get("staff_name", "Staff Member")
    
    # Get pending reminders for this office only
    reminders = db.query(PendingReminder).options(
        joinedload(PendingReminder.case).joinedload(Case.customer)
    ).filter(
        PendingReminder.office_id == office_id,
        PendingReminder.status == 'pending'
    ).all()
    
    return templates.TemplateResponse(
        request=request,
        name="reminders.html",
        context={
            "staff_name": staff_name,
            "reminders": reminders,
            "office_display_name": request.session.get("office_display_name"),
            "staff_role": request.session.get("staff_role")
        }
    )

@app.post("/reminders/{reminder_id}/approve")
async def approve_reminder(
    request: Request,
    reminder_id: int,
    db: Session = Depends(get_db)
):
    """
    Approve a pending reminder - mark it as sent and log an event.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    # Get the office ID and staff email from session
    office_id = request.session.get("office_id")
    staff_email = request.session.get("staff_email")
    
    try:
        # Get the reminder with case and customer data
        reminder = db.query(PendingReminder).options(
            joinedload(PendingReminder.case).joinedload(Case.customer)
        ).filter(
            PendingReminder.id == reminder_id,
            PendingReminder.office_id == office_id,
            PendingReminder.status == 'pending'
        ).first()
        
        if not reminder:
            return RedirectResponse(url="/reminders")
        
        # Update reminder status
        reminder.status = 'approved'
        reminder.processed_at = datetime.now()
        
        # Log an event for the case
        new_event = Event(
            case_id=reminder.case_id,
            office_id=office_id,
            event_type="reminder_approved_sent",
            description=f"Reminder approved and marked as sent: {reminder.message}",
            created_by=staff_email
        )
        db.add(new_event)
        
        db.commit()
        
        return RedirectResponse(url="/reminders", status_code=303)
        
    except Exception as e:
        db.rollback()
        return RedirectResponse(url="/reminders")

@app.post("/reminders/{reminder_id}/reject")
async def reject_reminder(
    request: Request,
    reminder_id: int,
    db: Session = Depends(get_db)
):
    """
    Reject a pending reminder.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    # Get the office ID from session
    office_id = request.session.get("office_id")
    
    try:
        # Get the reminder
        reminder = db.query(PendingReminder).filter(
            PendingReminder.id == reminder_id,
            PendingReminder.office_id == office_id,
            PendingReminder.status == 'pending'
        ).first()
        
        if not reminder:
            return RedirectResponse(url="/reminders")
        
        # Update reminder status
        reminder.status = 'rejected'
        reminder.processed_at = datetime.now()
        
        db.commit()
        
        return RedirectResponse(url="/reminders", status_code=303)
        
    except Exception as e:
        db.rollback()
        return RedirectResponse(url="/reminders")

@app.post("/trigger-reminder-check")
async def trigger_reminder_check(request: Request):
    """
    Manual trigger endpoint for testing the daily check job.
    This allows you to test the reminder logic without waiting for the scheduled time.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    # Run the check manually
    check_pending_documents()
    
    return RedirectResponse(url="/reminders", status_code=303)

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    """Render the analytics page."""
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    return templates.TemplateResponse(
        request=request, 
        name="analytics.html",
        context={
            "office_display_name": request.session.get("office_display_name"),
            "staff_role": request.session.get("staff_role")
        }
    )

@app.get("/admin/checklist", response_class=HTMLResponse)
async def admin_checklist_page(request: Request, db: Session = Depends(get_db)):
    """
    Render the admin checklist configuration page.
    Only accessible to admin users.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    # Check if user is admin
    if not check_admin_role(request, db):
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "staff_name": request.session.get("staff_name", "Staff Member"),
                "cases": db.query(Case).options(joinedload(Case.customer)).filter(Case.office_id == request.session.get("office_id")).all(),
                "error": "Admin access required"
            }
        )
    
    # Get the office ID from session
    office_id = request.session.get("office_id")
    
    # Get all checklist configurations for this office, grouped by service type
    configs = db.query(ChecklistConfig).filter(
        ChecklistConfig.office_id == office_id
    ).order_by(ChecklistConfig.service_type, ChecklistConfig.display_order).all()
    
    # Group configs by service type
    service_configs = {}
    for config in configs:
        if config.service_type not in service_configs:
            service_configs[config.service_type] = []
        service_configs[config.service_type].append(config)
    
    return templates.TemplateResponse(
        request=request,
        name="admin_checklist.html",
        context={
            "service_configs": service_configs,
            "office_display_name": request.session.get("office_display_name"),
            "staff_role": request.session.get("staff_role")
        }
    )

@app.post("/admin/checklist/service-type")
async def add_service_type(
    request: Request,
    service_type: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Add a new service type for the office.
    Only accessible to admin users.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    # Check if user is admin
    if not check_admin_role(request, db):
        return RedirectResponse(url="/admin/checklist")
    
    # Get the office ID from session
    office_id = request.session.get("office_id")
    
    try:
        # Check if service type already exists for this office
        existing = db.query(ChecklistConfig).filter(
            ChecklistConfig.office_id == office_id,
            ChecklistConfig.service_type == service_type
        ).first()
        
        if existing:
            return RedirectResponse(
                url="/admin/checklist",
                status_code=303
            )
        
        # Create a default document for the new service type
        new_config = ChecklistConfig(
            office_id=office_id,
            service_type=service_type,
            document_type="General Document",
            is_required=1,
            display_order=0
        )
        db.add(new_config)
        db.commit()
        
        return RedirectResponse(url="/admin/checklist", status_code=303)
        
    except Exception as e:
        db.rollback()
        return RedirectResponse(url="/admin/checklist")

@app.post("/admin/checklist/service-type/delete")
async def delete_service_type(
    request: Request,
    service_type: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Delete a service type and all its document requirements.
    Only accessible to admin users.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    # Check if user is admin
    if not check_admin_role(request, db):
        return RedirectResponse(url="/admin/checklist")
    
    # Get the office ID from session
    office_id = request.session.get("office_id")
    
    try:
        # Delete all configs for this service type
        db.query(ChecklistConfig).filter(
            ChecklistConfig.office_id == office_id,
            ChecklistConfig.service_type == service_type
        ).delete()
        
        db.commit()
        
        return RedirectResponse(url="/admin/checklist", status_code=303)
        
    except Exception as e:
        db.rollback()
        return RedirectResponse(url="/admin/checklist")

@app.post("/admin/checklist/document")
async def add_document(
    request: Request,
    service_type: str = Form(...),
    document_type: str = Form(...),
    is_required: int = Form(...),
    db: Session = Depends(get_db)
):
    """
    Add a new document requirement to a service type.
    Only accessible to admin users.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    # Check if user is admin
    if not check_admin_role(request, db):
        return RedirectResponse(url="/admin/checklist")
    
    # Get the office ID from session
    office_id = request.session.get("office_id")
    
    try:
        # Get the highest display order for this service type
        max_order = db.query(ChecklistConfig).filter(
            ChecklistConfig.office_id == office_id,
            ChecklistConfig.service_type == service_type
        ).count()
        
        # Create new document config
        new_config = ChecklistConfig(
            office_id=office_id,
            service_type=service_type,
            document_type=document_type,
            is_required=is_required,
            display_order=max_order
        )
        db.add(new_config)
        db.commit()
        
        return RedirectResponse(url="/admin/checklist", status_code=303)
        
    except Exception as e:
        db.rollback()
        return RedirectResponse(url="/admin/checklist")

@app.post("/admin/checklist/document/toggle-required")
async def toggle_document_required(
    request: Request,
    config_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """
    Toggle a document between required and optional.
    Only accessible to admin users.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    # Check if user is admin
    if not check_admin_role(request, db):
        return RedirectResponse(url="/admin/checklist")
    
    # Get the office ID from session
    office_id = request.session.get("office_id")
    
    try:
        # Get the config
        config = db.query(ChecklistConfig).filter(
            ChecklistConfig.id == config_id,
            ChecklistConfig.office_id == office_id
        ).first()
        
        if config:
            # Toggle the required status
            config.is_required = 1 if config.is_required == 0 else 0
            db.commit()
        
        return RedirectResponse(url="/admin/checklist", status_code=303)
        
    except Exception as e:
        db.rollback()
        return RedirectResponse(url="/admin/checklist")

@app.post("/admin/checklist/document/delete")
async def delete_document(
    request: Request,
    config_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """
    Delete a document requirement.
    Only accessible to admin users.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    # Check if user is admin
    if not check_admin_role(request, db):
        return RedirectResponse(url="/admin/checklist")
    
    # Get the office ID from session
    office_id = request.session.get("office_id")
    
    try:
        # Delete the config
        db.query(ChecklistConfig).filter(
            ChecklistConfig.id == config_id,
            ChecklistConfig.office_id == office_id
        ).delete()
        
        db.commit()
        
        return RedirectResponse(url="/admin/checklist", status_code=303)
        
    except Exception as e:
        db.rollback()
        return RedirectResponse(url="/admin/checklist")

@app.post("/admin/checklist/reorder")
async def reorder_documents(
    request: Request,
    config_ids: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Reorder documents based on drag-and-drop.
    Only accessible to admin users.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    # Check if user is admin
    if not check_admin_role(request, db):
        return JSONResponse(content={"success": False})
    
    # Get the office ID from session
    office_id = request.session.get("office_id")
    
    try:
        # Parse the config IDs
        id_list = [int(id.strip()) for id in config_ids.split(',')]
        
        # Update the display order for each config
        for index, config_id in enumerate(id_list):
            config = db.query(ChecklistConfig).filter(
                ChecklistConfig.id == config_id,
                ChecklistConfig.office_id == office_id
            ).first()
            
            if config:
                config.display_order = index
        
        db.commit()
        
        return JSONResponse(content={"success": True})
        
    except Exception as e:
        db.rollback()
        return JSONResponse(content={"success": False})

# Policy RAG API endpoints
class PolicyQuestionRequest(BaseModel):
    """Request model for policy questions."""
    question: str
    state: Optional[str] = None
    service_type: Optional[str] = None

@app.post("/api/policy-question")
async def ask_policy_question(
    policy_request: PolicyQuestionRequest,
    http_request: Request
):
    """
    API endpoint for asking policy questions using RAG.
    Returns answer with source citations and conflict detection.
    """
    # Check if user is logged in
    staff_id = http_request.session.get("staff_id")
    if not staff_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Get RAG service
        rag_service = get_policy_rag_service()
        
        # Ask the question
        result = rag_service.ask_question(
            question=policy_request.question,
            state=policy_request.state,
            service_type=policy_request.service_type
        )
        
        return JSONResponse(content=result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing policy question: {str(e)}")

# Apply rate limiting to public endpoints
@app.get("/status", response_class=HTMLResponse)
@limiter.limit("10/minute", exempt_when=is_authenticated_staff)  # 10 requests per minute for status page
async def rate_limited_status_page(request: Request):
    """Render the public status check page (no login required) with rate limiting."""
    return templates.TemplateResponse(request=request, name="status.html")

@app.post("/status", response_class=HTMLResponse)
@limiter.limit("5/minute", exempt_when=is_authenticated_staff)  # 5 status checks per minute
async def rate_limited_check_status(
    request: Request,
    case_id: int = Form(...),
    phone: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Handle status check form submission with rate limiting.
    Looks up case by ID and validates phone number matches customer.
    """
    try:
        # Query the case with customer, documents, and events
        case = db.query(Case).options(
            joinedload(Case.customer),
            joinedload(Case.documents),
            joinedload(Case.events)
        ).filter(Case.id == case_id).first()
        
        # Check if case exists and phone matches customer's phone
        if not case or not case.customer or case.customer.phone != phone:
            # Return generic error message to avoid information leakage
            return templates.TemplateResponse(
                request=request,
                name="status.html",
                context={"error": "Case not found. Please check your Case ID and phone number."}
            )
        
        # Case found and phone matches - return case data
        # Sort events by created_at descending (most recent first)
        case.events = sorted(case.events, key=lambda x: x.created_at, reverse=True)
        
        return templates.TemplateResponse(
            request=request,
            name="status.html",
            context={"case": case}
        )
        
    except Exception as e:
        # Return generic error on any exception
        return templates.TemplateResponse(
            request=request,
            name="status.html",
            context={"error": "An error occurred. Please try again."}
        )

# Admin-only data deletion endpoint
@app.get("/admin/data-deletion", response_class=HTMLResponse)
async def admin_data_deletion_page(request: Request, db: Session = Depends(get_db)):
    """
    Render the admin data deletion page.
    Only accessible to admin users.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    # Check if user is admin
    if not check_admin_role(request, db):
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "staff_name": request.session.get("staff_name", "Staff Member"),
                "cases": db.query(Case).options(joinedload(Case.customer)).filter(Case.office_id == request.session.get("office_id")).all(),
                "error": "Admin access required"
            }
        )
    
    # Get the office ID from session
    office_id = request.session.get("office_id")
    
    # Get all customers for this office with their cases
    customers = db.query(Customer).options(
        joinedload(Customer.cases).joinedload(Case.documents)
    ).filter(Customer.office_id == office_id).all()
    
    return templates.TemplateResponse(
        request=request,
        name="admin_data_deletion.html",
        context={
            "customers": customers,
            "office_display_name": request.session.get("office_display_name"),
            "staff_role": request.session.get("staff_role")
        }
    )

@app.post("/admin/delete-customer")
async def delete_customer_data(
    request: Request,
    customer_id: int = Form(...),
    confirmation: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Permanently delete a customer and all associated data.
    Admin-only endpoint with confirmation requirement.
    Deletes from database AND Cloudflare R2 storage.
    Logs an audit event before deleting the customer record.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    # Check if user is admin
    if not check_admin_role(request, db):
        return RedirectResponse(url="/admin/data-deletion")
    
    # Verify confirmation
    if confirmation.lower() != "delete":
        return templates.TemplateResponse(
            request=request,
            name="admin_data_deletion.html",
            context={
                "customers": db.query(Customer).options(joinedload(Customer.cases)).filter(Customer.office_id == request.session.get("office_id")).all(),
                "error": "You must type 'delete' to confirm",
                "office_display_name": request.session.get("office_display_name"),
                "staff_role": request.session.get("staff_role")
            }
        )
    
    # Get the office ID and staff email from session
    office_id = request.session.get("office_id")
    staff_email = request.session.get("staff_email")
    
    try:
        # Get the customer with all related data
        customer = db.query(Customer).options(
            joinedload(Customer.cases).joinedload(Case.documents),
            joinedload(Customer.cases).joinedload(Case.events),
            joinedload(Customer.cases).joinedload(Case.reminders)
        ).filter(
            Customer.id == customer_id,
            Customer.office_id == office_id
        ).first()
        
        if not customer:
            return templates.TemplateResponse(
                request=request,
                name="admin_data_deletion.html",
                context={
                    "customers": db.query(Customer).options(joinedload(Customer.cases)).filter(Customer.office_id == office_id).all(),
                    "error": "Customer not found",
                    "office_display_name": request.session.get("office_display_name"),
                    "staff_role": request.session.get("staff_role")
                }
            )
        
        # Summary counts for audit log
        case_count = len(customer.cases)
        doc_count = sum(len(c.documents) for c in customer.cases)
        customer_name = customer.full_name
        
        # 1. Log the deletion event BEFORE deleting customer data
        # Note: case_id is None since this is a customer-level purge that survives case deletion
        deletion_event = Event(
            case_id=None,
            office_id=office_id,
            event_type="customer_deleted",
            description=f"Customer {customer_name} (ID: {customer_id}, Cases: {case_count}, Documents: {doc_count}) and all associated data permanently deleted by {staff_email}",
            created_by=staff_email
        )
        db.add(deletion_event)
        db.commit()
        
        # 2. Delete all documents from Cloudflare R2 storage
        r2_deleted_count = 0
        r2_failed_count = 0
        try:
            r2_service = get_r2_service()
            for case in customer.cases:
                for document in case.documents:
                    if document.r2_object_key:
                        try:
                            r2_service.delete_file(document.r2_object_key)
                            r2_deleted_count += 1
                            logger.info(f"Deleted R2 file: {document.r2_object_key}")
                        except Exception as e:
                            r2_failed_count += 1
                            logger.error(f"Failed to delete R2 file {document.r2_object_key}: {e}")
        except Exception as e:
            logger.warning(f"R2 storage service unavailable or unconfigured during deletion: {e}")
            
        # Also clean up any matching local files in uploads directory if present
        from pathlib import Path
        uploads_dir = Path("uploads")
        if uploads_dir.exists():
            for case in customer.cases:
                for document in case.documents:
                    if document.r2_object_key:
                        local_file = uploads_dir / Path(document.r2_object_key).name
                        if local_file.exists():
                            try:
                                local_file.unlink()
                            except Exception:
                                pass
                    if document.file_name:
                        local_file_named = uploads_dir / document.file_name
                        if local_file_named.exists():
                            try:
                                local_file_named.unlink()
                            except Exception:
                                pass
        
        # 3. Delete case-specific events first (leaving customer-level deletion_event with case_id=None intact)
        for case in customer.cases:
            db.query(Event).filter(Event.case_id == case.id).delete(synchronize_session=False)
        
        # Deleting customer cleanly cascades to all cases, documents, and reminders
        db.delete(customer)
        db.commit()
        
        logger.warning(f"Customer {customer_name} (ID: {customer_id}) and all associated data permanently deleted by {staff_email}")
        
        return templates.TemplateResponse(
            request=request,
            name="admin_data_deletion.html",
            context={
                "customers": db.query(Customer).options(joinedload(Customer.cases)).filter(Customer.office_id == office_id).all(),
                "success": f"Customer {customer_name} and all associated data (including R2 documents) permanently deleted",
                "office_display_name": request.session.get("office_display_name"),
                "staff_role": request.session.get("staff_role")
            }
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting customer {customer_id}: {e}")
        return templates.TemplateResponse(
            request=request,
            name="admin_data_deletion.html",
            context={
                "customers": db.query(Customer).options(joinedload(Customer.cases)).filter(Customer.office_id == office_id).all(),
                "error": f"Error deleting customer: {str(e)}",
                "office_display_name": request.session.get("office_display_name"),
                "staff_role": request.session.get("staff_role")
            }
        )

# Admin-only audit log viewer
@app.get("/admin/audit-log", response_class=HTMLResponse)
async def admin_audit_log_page(
    request: Request,
    db: Session = Depends(get_db),
    case_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Render the admin audit log viewer page.
    Only accessible to admin users.
    Shows raw events table for their office, searchable by case or date.
    """
    # Check if user is logged in
    staff_id = request.session.get("staff_id")
    if not staff_id:
        return RedirectResponse(url="/login")
    
    # Check if user is admin
    if not check_admin_role(request, db):
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "staff_name": request.session.get("staff_name", "Staff Member"),
                "cases": db.query(Case).options(joinedload(Case.customer)).filter(Case.office_id == request.session.get("office_id")).all(),
                "error": "Admin access required"
            }
        )
    
    # Get the office ID from session
    office_id = request.session.get("office_id")
    
    # Build query for events
    query = db.query(Event).filter(Event.office_id == office_id)
    
    # Filter by case ID if provided
    if case_id:
        query = query.filter(Event.case_id == case_id)
    
    # Filter by date range if provided
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(Event.created_at >= start_dt)
        except ValueError:
            pass  # Invalid date format, ignore
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(Event.created_at < end_dt)
        except ValueError:
            pass  # Invalid date format, ignore
    
    # Order by most recent first
    events = query.order_by(Event.created_at.desc()).limit(100).all()
    
    return templates.TemplateResponse(
        request=request,
        name="admin_audit_log.html",
        context={
            "events": events,
            "case_id": case_id,
            "start_date": start_date,
            "end_date": end_date,
            "office_display_name": request.session.get("office_display_name"),
            "staff_role": request.session.get("staff_role")
        }
    )

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Start the scheduler when the app starts."""
    start_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown the scheduler when the app stops."""
    shutdown_scheduler()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)