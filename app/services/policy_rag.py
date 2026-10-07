"""
Policy RAG Service - Retrieval-Augmented Generation for policy questions.
This service uses array-based embeddings to retrieve relevant policy chunks and generates
answers using the LLM, with source citations and conflict detection.
"""

import os
import logging
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from sentence_transformers import SentenceTransformer
import numpy as np
from app.core.database import SessionLocal
from app.models.models import PolicyChunk
from app.core.ai_client import get_ai_client, get_ai_model

logger = logging.getLogger(__name__)

class PolicyRAGService:
    """Service for policy question answering using RAG."""
    
    def __init__(self):
        """Initialize the RAG service with embedding model."""
        logger.info("Loading sentence-transformers model for RAG...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Embedding model loaded successfully")
        self.ai_client = get_ai_client()
        self.ai_model = get_ai_model()
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a text query."""
        embedding = self.embedding_model.encode(text)
        return embedding.tolist()
    
    def _retrieve_relevant_chunks(
        self, 
        question: str, 
        state: Optional[str] = None, 
        service_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[PolicyChunk]:
        """
        Retrieve the most relevant policy chunks for a question.
        
        Args:
            question: The user's question
            state: Optional state filter (e.g., "Karnataka")
            service_type: Optional service type filter (e.g., "License Renewal")
            top_k: Number of chunks to retrieve
        
        Returns:
            List of relevant PolicyChunk objects
        """
        db = SessionLocal()
        try:
            # Generate embedding for the question
            question_embedding = np.array(self._generate_embedding(question))
            
            # Build the query
            query = db.query(PolicyChunk)
            
            # Apply filters if provided
            if state:
                query = query.filter(PolicyChunk.state.ilike(f"%{state}%"))
            
            if service_type:
                # Make service type matching more flexible
                service_type_lower = service_type.lower()
                
                # Try matching key terms in the service type
                if "renewal" in service_type_lower:
                    query = query.filter(PolicyChunk.service_type.ilike("%renewal%"))
                elif "registration" in service_type_lower:
                    query = query.filter(PolicyChunk.service_type.ilike("%registration%"))
                elif "transfer" in service_type_lower:
                    query = query.filter(PolicyChunk.service_type.ilike("%transfer%"))
                elif "license" in service_type_lower:
                    query = query.filter(PolicyChunk.service_type.ilike("%license%"))
                else:
                    # Fallback to exact match
                    query = query.filter(PolicyChunk.service_type.ilike(f"%{service_type}%"))
            
            # Get all candidate chunks
            chunks = query.all()
            
            # Calculate cosine similarity for each chunk
            chunk_similarities = []
            for chunk in chunks:
                chunk_embedding = np.array(chunk.embedding)
                # Calculate cosine similarity
                similarity = np.dot(question_embedding, chunk_embedding) / (
                    np.linalg.norm(question_embedding) * np.linalg.norm(chunk_embedding)
                )
                chunk_similarities.append((chunk, similarity))
            
            # Sort by similarity and get top_k
            chunk_similarities.sort(key=lambda x: x[1], reverse=True)
            top_chunks = [chunk for chunk, similarity in chunk_similarities[:top_k]]
            
            return top_chunks
            
        finally:
            db.close()
    
    def _detect_conflicts(self, chunks: List[PolicyChunk]) -> Tuple[bool, str]:
        """
        Detect if there are conflicts between the retrieved chunks.
        
        Args:
            chunks: List of retrieved policy chunks
        
        Returns:
            Tuple of (has_conflict, conflict_description)
        """
        if len(chunks) < 2:
            return False, ""
        
        # Extract chunk texts
        chunk_texts = [chunk.chunk_text for chunk in chunks]
        
        # Use LLM to detect conflicts
        conflict_prompt = f"""Analyze these policy chunks and determine if they contain contradictory information about the same topic.

Chunks:
{chr(10).join([f"Chunk {i+1}: {text}" for i, text in enumerate(chunk_texts)])}

Respond in this exact format:
CONFLICT: yes/no
REASON: [brief explanation if conflict exists, otherwise "none"]"""

        try:
            response = self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=[
                    {"role": "system", "content": "You are a policy analyst. Detect contradictions in policy documents."},
                    {"role": "user", "content": conflict_prompt}
                ],
                temperature=0.1
            )
            
            result = response.choices[0].message.content.strip()
            
            if "CONFLICT: yes" in result.lower():
                # Extract reason
                reason = "none"
                for line in result.split('\n'):
                    if line.startswith("REASON:"):
                        reason = line.replace("REASON:", "").strip()
                        break
                return True, reason
            else:
                return False, ""
                
        except Exception as e:
            logger.error(f"Error detecting conflicts: {e}")
            return False, ""
    
    def _generate_answer(
        self, 
        question: str, 
        chunks: List[PolicyChunk]
    ) -> Dict:
        """
        Generate an answer using the LLM based on retrieved chunks.
        
        Args:
            question: The user's question
            chunks: Retrieved policy chunks
        
        Returns:
            Dictionary with answer, sources, and metadata
        """
        if not chunks:
            return {
                "answer": "I couldn't find any relevant policy information for your question. The policy database may not contain information about this topic yet.",
                "sources": [],
                "has_conflict": False,
                "conflict_reason": ""
            }
        
        # Prepare context from chunks
        context = "\n\n---\n\n".join([
            f"Source: {chunk.source_name}\nState: {chunk.state}\nService: {chunk.service_type}\nContent: {chunk.chunk_text}"
            for chunk in chunks
        ])
        
        # Prepare source information
        sources = [
            {
                "source_name": chunk.source_name,
                "state": chunk.state,
                "service_type": chunk.service_type,
                "snippet": chunk.chunk_text[:200] + "..." if len(chunk.chunk_text) > 200 else chunk.chunk_text
            }
            for chunk in chunks
        ]
        
        # Generate answer using LLM
        prompt = f"""You are an RTO policy expert. Answer the following question using ONLY the provided policy chunks. 
If the answer is not in the chunks, say "I don't have enough information in the policy documents to answer this question."
Always cite which source(s) you used in your answer.

Question: {question}

Policy Context:
{context}

Provide a clear, accurate answer based on the policy documents above. Include specific source citations in your answer."""

        try:
            response = self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=[
                    {"role": "system", "content": "You are an RTO policy expert. Answer questions based only on provided policy documents."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            answer = response.choices[0].message.content.strip()
            
            return {
                "answer": answer,
                "sources": sources,
                "has_conflict": False,
                "conflict_reason": ""
            }
            
        except Exception as e:
            return {
                "answer": f"Error generating answer: {str(e)}",
                "sources": sources,
                "has_conflict": False,
                "conflict_reason": ""
            }
    
    def ask_question(
        self, 
        question: str, 
        state: Optional[str] = None, 
        service_type: Optional[str] = None
    ) -> Dict:
        """
        Ask a policy question and get an answer with sources.
        
        Args:
            question: The user's question
            state: Optional state filter
            service_type: Optional service type filter
        
        Returns:
            Dictionary with answer, sources, and conflict information
        """
        # Retrieve relevant chunks
        chunks = self._retrieve_relevant_chunks(question, state, service_type)
        
        if not chunks:
            return {
                "answer": "I couldn't find any relevant policy information for your question. The policy database may not contain information about this topic yet.",
                "sources": [],
                "has_conflict": False,
                "conflict_reason": ""
            }
        
        # Detect conflicts
        has_conflict, conflict_reason = self._detect_conflicts(chunks)
        
        if has_conflict:
            return {
                "answer": "POLICY CONFLICT DETECTED: The retrieved policy chunks contain contradictory information. This requires human review to determine the correct policy.",
                "sources": [
                    {
                        "source_name": chunk.source_name,
                        "state": chunk.state,
                        "service_type": chunk.service_type,
                        "snippet": chunk.chunk_text[:200] + "..." if len(chunk.chunk_text) > 200 else chunk.chunk_text
                    }
                    for chunk in chunks
                ],
                "has_conflict": True,
                "conflict_reason": conflict_reason
            }
        
        # Generate answer
        result = self._generate_answer(question, chunks)
        result["has_conflict"] = has_conflict
        result["conflict_reason"] = conflict_reason
        
        return result

# Global service instance
_rag_service = None

def get_policy_rag_service():
    """Get or create the global RAG service instance."""
    global _rag_service
    if _rag_service is None:
        _rag_service = PolicyRAGService()
    return _rag_service