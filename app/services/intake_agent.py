"""
Intake Agent Service - Handles conversational intake logic using AI.
This service manages the conversation flow to collect customer information
and identify the service type needed.
"""

from app.core.ai_client import get_ai_client, get_ai_model
import json
import re

# Define available service types and their required fields
SERVICE_TYPES = {
    "license_renewal": {
        "name": "License Renewal",
        "required_fields": ["full_name", "phone", "license_number", "date_of_birth"]
    },
    "vehicle_transfer": {
        "name": "Vehicle Transfer",
        "required_fields": ["full_name", "phone", "vehicle_number", "seller_name"]
    },
    "rc_duplicate": {
        "name": "RC Duplicate",
        "required_fields": ["full_name", "phone", "vehicle_number", "reason"]
    },
    "new_registration": {
        "name": "New Vehicle Registration",
        "required_fields": ["full_name", "phone", "vehicle_number", "vehicle_type"]
    },
    "address_change": {
        "name": "Address Change",
        "required_fields": ["full_name", "phone", "vehicle_number", "new_address"]
    },
    "general": {
        "name": "General Service",
        "required_fields": ["full_name", "phone", "service_description"]
    }
}

class IntakeAgent:
    """Manages the conversational intake process."""
    
    def __init__(self):
        self.client = get_ai_client()
        self.model = get_ai_model()
        self.conversation_history = []
        self.collected_data = {}
        self.current_service_type = None
        self.current_field_index = 0
        
    def initialize_conversation(self):
        """Initialize the conversation with a welcome message."""
        system_prompt = f"""You are a helpful RTO (Regional Transport Office) assistant. Your role is to help customers through a conversational intake process.

You can help with ANY service the customer needs - be flexible and adaptable. Common services include license renewal, vehicle transfer, RC duplicate, new registration, address change, but you should handle any request the customer makes.

Your task:
1. Understand what service the customer needs from their natural language input
2. Collect the required information for that service ONE field at a time
3. Be conversational and friendly
4. Ask clear, specific questions
5. Once all required fields are collected, return a JSON summary

For general services, collect: full name, phone number, and a description of what they need.

Response format:
- For regular conversation: plain text
- When all data is collected: return JSON with format {{"ready_to_submit": true, "service_type": "...", "data": {{...}}}}

Start by greeting the customer and asking what service they need."""

        self.conversation_history = [
            {"role": "system", "content": system_prompt}
        ]
        
        return "Hello! I'm here to help you with RTO services. What service do you need today? I can help with license renewal, vehicle transfer, RC duplicate, new registration, or address change."
    
    def process_message(self, user_message):
        """
        Process a user message and return the agent's response.
        
        Args:
            user_message: The customer's message
            
        Returns:
            Dictionary with:
            - reply: The agent's text response
            - ready_to_submit: Boolean indicating if all data is collected
            - service_type: The identified service type (if determined)
            - collected_data: All collected information (if ready to submit)
        """
        # Add pure user message to history
        self.conversation_history.append({
            "role": "user", 
            "content": user_message
        })
        
        # If this is the first real message, try to identify service type
        if not self.current_service_type and len(self.conversation_history) > 2:
            service_type = self._identify_service_type(user_message)
            if service_type:
                self.current_service_type = service_type
                self.current_field_index = 0
        
        # Build API payload with context injected cleanly as system guidance
        messages_to_send = list(self.conversation_history)
        
        if self.current_service_type:
            current_field = self._get_next_field()
            if current_field:
                system_context = (
                    f"SYSTEM STATE UPDATE:\n"
                    f"Current service: {SERVICE_TYPES[self.current_service_type]['name']}\n"
                    f"Next field to collect: {current_field}\n"
                    f"Already collected data: {json.dumps(self.collected_data)}"
                )
                messages_to_send.append({"role": "system", "content": system_context})
        
        # Get AI response
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages_to_send,
                temperature=0.7,
                max_tokens=500
            )
            
            ai_response = response.choices[0].message.content
            
            # Check if the response contains JSON (ready to submit)
            if "ready_to_submit" in ai_response and "true" in ai_response.lower():
                return self._parse_final_response(ai_response)
            
            # Extract information from the response/message context
            self._extract_info_from_response(ai_response, user_message)
            
            # Add AI response to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": ai_response
            })
            
            return {
                "reply": ai_response,
                "ready_to_submit": False,
                "service_type": self.current_service_type,
                "collected_data": self.collected_data
            }
            
        except Exception as e:
            error_message = f"I apologize, but I encountered an error: {str(e)}. Please try again."
            return {
                "reply": error_message,
                "ready_to_submit": False,
                "service_type": self.current_service_type,
                "collected_data": self.collected_data
            }
    
    def _identify_service_type(self, message):
        """Identify the service type from the user's message."""
        message_lower = message.lower()
        
        for service_key, service_info in SERVICE_TYPES.items():
            if service_key in message_lower or service_info["name"].lower() in message_lower:
                return service_key
        
        # Default to general service for any other request
        return "general"
    
    def _get_next_field(self):
        """Get the next field that needs to be collected."""
        if not self.current_service_type:
            return None
        
        required_fields = SERVICE_TYPES[self.current_service_type]["required_fields"]
        
        for field in required_fields:
            if field not in self.collected_data or not self.collected_data[field]:
                return field
        
        return None
    
    def _extract_info_from_response(self, ai_response, user_message):
        """Extract information from the conversation and update collected_data."""
        if not self.current_service_type:
            return
        
        required_fields = SERVICE_TYPES[self.current_service_type]["required_fields"]
        
        # Try to extract phone numbers
        phone_match = re.search(r'[\d\-\+\s]{10,}', user_message)
        if phone_match and "phone" not in self.collected_data:
            self.collected_data["phone"] = phone_match.group().strip()
        
        # Try to extract vehicle numbers
        vehicle_match = re.search(r'[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}', user_message.upper())
        if vehicle_match and "vehicle_number" not in self.collected_data:
            self.collected_data["vehicle_number"] = vehicle_match.group()
        
        # Use AI to extract structured information
        try:
            prompt = f"Extract information from this customer message: '{user_message}'. "
            prompt += f"Service type: {self.current_service_type}. "
            prompt += f"Fields needed: {required_fields}. "
            prompt += f"Already collected: {json.dumps(self.collected_data)}. "
            prompt += "Return only a JSON object with the new/updated fields."
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            
            content = response.choices[0].message.content
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start != -1 and json_end != 0:
                extracted_data = json.loads(content[json_start:json_end])
                self.collected_data.update(extracted_data)
            
        except Exception:
            pass
    
    def _parse_final_response(self, ai_response):
        """Parse the final JSON response when all data is collected."""
        try:
            json_start = ai_response.find("{")
            json_end = ai_response.rfind("}") + 1
            json_str = ai_response[json_start:json_end]
            
            final_data = json.loads(json_str)
            
            return {
                "reply": final_data.get("message", "All information collected! Ready to submit."),
                "ready_to_submit": True,
                "service_type": final_data.get("service_type", self.current_service_type),
                "collected_data": final_data.get("data", self.collected_data)
            }
            
        except Exception:
            return {
                "reply": ai_response,
                "ready_to_submit": True,
                "service_type": self.current_service_type,
                "collected_data": self.collected_data
            }
    
    def reset(self):
        """Reset the conversation state."""
        self.conversation_history = []
        self.collected_data = {}
        self.current_service_type = None
        self.current_field_index = 0