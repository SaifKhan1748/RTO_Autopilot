from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import Case, Document, PendingReminder, Event
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = BackgroundScheduler()

def check_pending_documents():
    """
    Daily job that checks for cases where a document was requested more than 2 days ago
    and still isn't uploaded, then creates PendingReminder rows.
    """
    logger.info("Running daily document check job...")
    
    db = SessionLocal()
    try:
        # Get the cutoff date (2 days ago)
        cutoff_date = datetime.now() - timedelta(days=2)
        
        # Find cases where:
        # 1. Case was created more than 2 days ago
        # 2. Case has status that indicates document request (not completed/rejected)
        # 3. No documents have been uploaded for this case
        # 4. No pending reminder already exists for this case
        cases_needing_reminder = db.query(Case).filter(
            Case.created_at < cutoff_date,
            Case.status.in_(['new', 'pending', 'in_progress']),
            ~Case.id.in_(
                db.query(Document.case_id).distinct()
            ),
            ~Case.id.in_(
                db.query(PendingReminder.case_id).filter(
                    PendingReminder.status == 'pending'
                )
            )
        ).all()
        
        logger.info(f"Found {len(cases_needing_reminder)} cases needing reminders")
        
        # Create a PendingReminder for each case
        for case in cases_needing_reminder:
            # Generate a friendly reminder message
            message = f"Reminder: Case #{case.id} for {case.service_type} was created on {case.created_at.strftime('%Y-%m-%d')} but no documents have been uploaded yet. Please contact the customer to request the required documents."
            
            # Create the pending reminder
            reminder = PendingReminder(
                case_id=case.id,
                office_id=case.office_id,
                message=message,
                status='pending'
            )
            db.add(reminder)
            
            logger.info(f"Created pending reminder for case #{case.id}")
        
        if cases_needing_reminder:
            db.commit()
            logger.info(f"Successfully created {len(cases_needing_reminder)} pending reminders")
        else:
            logger.info("No new reminders needed")
            
    except Exception as e:
        logger.error(f"Error in daily document check: {str(e)}")
        db.rollback()
    finally:
        db.close()

def start_scheduler():
    """
    Start the APScheduler with the daily check job.
    This should be called when the FastAPI app starts.
    """
    try:
        # Add the daily job - runs at 9:00 AM every day
        scheduler.add_job(
            check_pending_documents,
            trigger=CronTrigger(hour=9, minute=0),  # Run at 9:00 AM daily
            id='daily_document_check',
            name='Daily Document Check',
            replace_existing=True
        )
        
        # Start the scheduler
        scheduler.start()
        logger.info("Scheduler started successfully. Daily check scheduled for 9:00 AM.")
        
    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}")

def shutdown_scheduler():
    """
    Shutdown the scheduler gracefully.
    This should be called when the FastAPI app shuts down.
    """
    try:
        scheduler.shutdown()
        logger.info("Scheduler shutdown successfully")
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {str(e)}")