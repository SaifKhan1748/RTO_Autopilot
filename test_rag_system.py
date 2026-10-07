"""
Test script for the RAG system
This script tests the policy RAG service with sample questions.
"""

import sys
import io

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.policy_rag import get_policy_rag_service

def test_rag_system():
    """Test the RAG system with sample questions."""
    print("Testing RAG System...\n")
    
    # Get the RAG service
    rag_service = get_policy_rag_service()
    
    # Test questions
    test_questions = [
        {
            "question": "What documents are required for license renewal in Karnataka?",
            "state": "Karnataka",
            "service_type": "License Renewal"
        },
        {
            "question": "What is the fee for vehicle registration in Karnataka?",
            "state": "Karnataka",
            "service_type": "Vehicle Registration"
        },
        {
            "question": "When should I apply for license renewal in Maharashtra?",
            "state": "Maharashtra",
            "service_type": "License Renewal"
        }
    ]
    
    for i, test in enumerate(test_questions, 1):
        print(f"Test {i}: {test['question']}")
        print(f"State: {test['state']}, Service: {test['service_type']}")
        print("-" * 60)
        
        try:
            result = rag_service.ask_question(
                question=test['question'],
                state=test['state'],
                service_type=test['service_type']
            )
            
            print(f"Answer: {result['answer']}")
            print(f"\nHas Conflict: {result['has_conflict']}")
            if result['has_conflict']:
                print(f"Conflict Reason: {result['conflict_reason']}")
            
            print(f"\nSources ({len(result['sources'])}):")
            for j, source in enumerate(result['sources'], 1):
                print(f"  {j}. {source['source_name']}")
                print(f"     State: {source['state']}, Service: {source['service_type']}")
                print(f"     Snippet: {source['snippet'][:100]}...")
            
        except Exception as e:
            print(f"Error: {e}")
        
        print("\n" + "=" * 60 + "\n")

if __name__ == "__main__":
    test_rag_system()