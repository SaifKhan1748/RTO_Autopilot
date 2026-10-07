"""
Case Analysis Service - AI-powered case analysis and audit functionality.
This service analyzes cases to identify issues, provide summaries, and suggest next actions.
"""

from app.core.ai_client import get_ai_client, get_ai_model
from sqlalchemy.orm import Session, joinedload
from app.models.models import Case, Customer, Document, Event
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta


def analyze_case(case_id: int, db: Session) -> Dict[str, Any]:
    """
    Analyze a case using AI to identify issues, provide summary, and suggest next actions.
    
    Args:
        case_id: The ID of the case to analyze
        db: Database session
        
    Returns:
        Dictionary with:
        - issues: List of issues with severity and description
        - summary: Plain-language explanation of current stage
        - blocking_issue: Description of blocking issue or null
        - next_action: Suggested next action
        - confidence: Confidence score based on real signals
        - signals: Dictionary of signals used for confidence calculation
    """
    
    # Fetch complete case data
    case = db.query(Case).options(
        joinedload(Case.customer),
        joinedload(Case.documents),
        joinedload(Case.events)
    ).filter(Case.id == case_id).first()
    
    if not case:
        raise ValueError(f"Case with ID {case_id} not found")
    
    # Gather case data for analysis
    case_data = {
        "case_id": case.id,
        "service_type": case.service_type,
        "status": case.status,
        "vehicle_number": case.vehicle_number,
        "notes": case.notes,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "updated_at": case.updated_at.isoformat() if case.updated_at else None,
        "customer": {
            "full_name": case.customer.full_name if case.customer else None,
            "phone": case.customer.phone if case.customer else None,
            "email": case.customer.email if case.customer else None,
            "address": case.customer.address if case.customer else None
        },
        "documents": [
            {
                "id": doc.id,
                "document_type": doc.document_type,
                "file_name": doc.file_name,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None
            }
            for doc in case.documents
        ],
        "events": [
            {
                "event_type": event.event_type,
                "description": event.description,
                "created_by": event.created_by,
                "created_at": event.created_at.isoformat() if event.created_at else None
            }
            for event in sorted(case.events, key=lambda x: x.created_at, reverse=True)
        ]
    }
    
    # Calculate real signals for confidence
    signals = calculate_case_signals(case_data)
    
    # Build AI prompt with structured context
    prompt = build_analysis_prompt(case_data, signals)
    
    # Get AI client and make the call
    try:
        client = get_ai_client()
        model = get_ai_model()
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert RTO (Regional Transport Office) case analyst. Your role is to analyze vehicle registration cases, identify issues, provide clear summaries, and suggest appropriate next actions. Always respond with valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        ai_response = response.choices[0].message.content
        
        # Parse the AI response
        analysis_result = parse_ai_response(ai_response)
        
        # Add confidence and signals to the result
        analysis_result["confidence"] = signals["confidence"]
        analysis_result["signals"] = signals
        
        return analysis_result
        
    except Exception as e:
        # Fallback to rule-based analysis if AI fails
        return fallback_analysis(case_data, signals, str(e))


def calculate_case_signals(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate real signals from case data for confidence assessment.
    
    Args:
        case_data: Complete case data dictionary
        
    Returns:
        Dictionary with signals and calculated confidence
    """
    signals = {
        "document_count": len(case_data["documents"]),
        "event_count": len(case_data["events"]),
        "case_age_days": 0,
        "has_completion_event": False,
        "has_creation_event": False,
        "recent_activity": False,
        "missing_required_docs": False,
        "confidence": 0.0
    }
    
    # Calculate case age
    if case_data["created_at"]:
        created_date = datetime.fromisoformat(case_data["created_at"])
        # Handle timezone-aware datetimes
        if created_date.tzinfo is not None:
            # Convert to naive datetime by removing timezone info
            created_date = created_date.replace(tzinfo=None)
        signals["case_age_days"] = (datetime.now() - created_date).days
    
    # Check for key events
    for event in case_data["events"]:
        if event["event_type"] == "case_created":
            signals["has_creation_event"] = True
        if event["event_type"] == "case_completed":
            signals["has_completion_event"] = True
    
    # Check for recent activity (within last 7 days)
    if case_data["events"]:
        latest_event = case_data["events"][0]  # Events are sorted by date desc
        if latest_event["created_at"]:
            event_date = datetime.fromisoformat(latest_event["created_at"])
            # Handle timezone-aware datetimes
            if event_date.tzinfo is not None:
                event_date = event_date.replace(tzinfo=None)
            signals["recent_activity"] = (datetime.now() - event_date).days <= 7
    
    # Check for missing required documents (simplified logic)
    # In a real implementation, this would check against service-specific requirements
    required_doc_types = ["ID Proof", "Address Proof"]
    current_doc_types = [doc["document_type"] for doc in case_data["documents"]]
    signals["missing_required_docs"] = any(
        req not in current_doc_types for req in required_doc_types
    )
    
    # Calculate confidence based on signals
    confidence = 0.0
    
    # Base confidence
    confidence += 0.3
    
    # Add confidence for having documents
    if signals["document_count"] > 0:
        confidence += 0.2
    
    # Add confidence for having creation event
    if signals["has_creation_event"]:
        confidence += 0.1
    
    # Add confidence for recent activity
    if signals["recent_activity"]:
        confidence += 0.1
    
    # Subtract confidence for missing required docs
    if signals["missing_required_docs"]:
        confidence -= 0.2
    
    # Add confidence for completion
    if signals["has_completion_event"]:
        confidence += 0.1
    
    # Ensure confidence is between 0 and 1
    signals["confidence"] = max(0.0, min(1.0, confidence))
    
    return signals


def build_analysis_prompt(case_data: Dict[str, Any], signals: Dict[str, Any]) -> str:
    """
    Build the analysis prompt for the AI.
    
    Args:
        case_data: Complete case data dictionary
        signals: Calculated signals
        
    Returns:
        Formatted prompt string
    """
    prompt = f"""Analyze this RTO case and provide a structured assessment:

CASE INFORMATION:
- Case ID: {case_data['case_id']}
- Service Type: {case_data['service_type']}
- Status: {case_data['status']}
- Vehicle Number: {case_data['vehicle_number'] or 'N/A'}
- Created: {case_data['created_at'] or 'N/A'}
- Notes: {case_data['notes'] or 'None'}

CUSTOMER INFORMATION:
- Name: {case_data['customer']['full_name']}
- Phone: {case_data['customer']['phone'] or 'N/A'}
- Email: {case_data['customer']['email'] or 'N/A'}
- Address: {case_data['customer']['address'] or 'N/A'}

DOCUMENTS ({len(case_data['documents'])} uploaded):
"""
    
    for doc in case_data["documents"]:
        prompt += f"- {doc['document_type']}: {doc['file_name']} (uploaded: {doc['uploaded_at'] or 'N/A'})\n"
    
    prompt += f"""
RECENT EVENTS ({len(case_data['events'])}):
"""
    
    for event in case_data["events"][:5]:  # Show last 5 events
        prompt += f"- {event['event_type']}: {event['description']} (by {event['created_by'] or 'system'} on {event['created_at'] or 'N/A'})\n"
    
    prompt += f"""
ANALYSIS SIGNALS:
- Document count: {signals['document_count']}
- Case age: {signals['case_age_days']} days
- Has creation event: {signals['has_creation_event']}
- Has completion event: {signals['has_completion_event']}
- Recent activity: {signals['recent_activity']}
- Missing required documents: {signals['missing_required_docs']}

Please analyze this case and provide a JSON response with this exact structure:
{{
  "issues": [
    {{
      "severity": "low|medium|high",
      "description": "Clear description of the issue"
    }}
  ],
  "summary": "Plain-language explanation of current stage and what has happened",
  "blocking_issue": "Description of the main blocking issue or null if none",
  "next_action": "Specific, actionable next step for staff"
}}

Focus on:
1. Missing or incomplete documents
2. Data inconsistencies
3. Process bottlenecks
4. Next steps to move the case forward
5. Any compliance or regulatory concerns

Be specific and actionable in your recommendations."""
    
    return prompt


def parse_ai_response(ai_response: str) -> Dict[str, Any]:
    """
    Parse the AI response into structured format.
    
    Args:
        ai_response: Raw AI response string
        
    Returns:
        Parsed analysis result dictionary
    """
    try:
        # Try to extract JSON from the response
        json_start = ai_response.find("{")
        json_end = ai_response.rfind("}") + 1
        
        if json_start != -1 and json_end > json_start:
            json_str = ai_response[json_start:json_end]
            parsed_data = json.loads(json_str)
            
            # Validate required fields
            required_fields = ["issues", "summary", "blocking_issue", "next_action"]
            for field in required_fields:
                if field not in parsed_data:
                    parsed_data[field] = None if field in ["blocking_issue"] else []
            
            return parsed_data
        else:
            # Fallback if no JSON found
            return {
                "issues": [],
                "summary": ai_response,
                "blocking_issue": None,
                "next_action": "Review case manually"
            }
            
    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        return {
            "issues": [],
            "summary": ai_response,
            "blocking_issue": None,
            "next_action": "Review case manually"
        }


def fallback_analysis(case_data: Dict[str, Any], signals: Dict[str, Any], error: str) -> Dict[str, Any]:
    """
    Provide rule-based fallback analysis if AI fails.
    
    Args:
        case_data: Complete case data dictionary
        signals: Calculated signals
        error: Error message from AI failure
        
    Returns:
        Analysis result dictionary
    """
    issues = []
    
    # Check for missing documents
    if signals["missing_required_docs"]:
        issues.append({
            "severity": "high",
            "description": "Missing required documents (ID Proof or Address Proof)"
        })
    
    # Check for no documents
    if signals["document_count"] == 0:
        issues.append({
            "severity": "high",
            "description": "No documents uploaded for this case"
        })
    
    # Check for old cases
    if signals["case_age_days"] > 30:
        issues.append({
            "severity": "medium",
            "description": f"Case is {signals['case_age_days']} days old - may need attention"
        })
    
    # Check for missing creation event
    if not signals["has_creation_event"]:
        issues.append({
            "severity": "high",
            "description": "Missing case creation event - data integrity issue"
        })
    
    # Generate summary
    if case_data["status"] == "completed":
        summary = f"Case for {case_data['customer']['full_name']} has been completed. Service type: {case_data['service_type']}."
    elif signals["document_count"] == 0:
        summary = f"Case for {case_data['customer']['full_name']} is waiting for document upload. No documents have been submitted yet."
    elif signals["missing_required_docs"]:
        summary = f"Case for {case_data['customer']['full_name']} has some documents but may be missing required documentation."
    else:
        summary = f"Case for {case_data['customer']['full_name']} is in progress with {signals['document_count']} documents uploaded."
    
    # Determine blocking issue
    blocking_issue = None
    if signals["document_count"] == 0:
        blocking_issue = "No documents uploaded - cannot proceed without documentation"
    elif signals["missing_required_docs"]:
        blocking_issue = "Missing required documents - need ID Proof and/or Address Proof"
    
    # Suggest next action
    if signals["document_count"] == 0:
        next_action = "Upload required documents (ID Proof, Address Proof) to begin processing"
    elif signals["missing_required_docs"]:
        next_action = "Upload missing required documents to complete the case"
    elif case_data["status"] == "completed":
        next_action = "Case is complete - no further action required"
    else:
        next_action = "Review documents and proceed with next processing step"
    
    return {
        "issues": issues,
        "summary": summary,
        "blocking_issue": blocking_issue,
        "next_action": next_action,
        "confidence": signals["confidence"],
        "signals": signals,
        "fallback": True,
        "error": error
    }