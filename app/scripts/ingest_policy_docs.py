"""
Policy Document Ingestion Script
This script reads plain-text policy documents from a folder, splits them into chunks,
generates embeddings using sentence-transformers, and stores them in the database.

Usage: python -m app.scripts.ingest_policy_docs --folder path/to/policy_documents
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from sentence_transformers import SentenceTransformer
import numpy as np
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models.models import PolicyChunk, Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

def chunk_text(text, chunk_size=800, overlap=100):
    """
    Split text into overlapping chunks.
    
    Args:
        text: The text to chunk
        chunk_size: Maximum characters per chunk
        overlap: Number of characters to overlap between chunks
    
    Returns:
        List of text chunks
    """
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap  # Overlap chunks for context
    
    return chunks

def parse_metadata_from_filename(filename):
    """
    Parse state and service_type from filename.
    Expected format: {state}_{service_type}.txt
    Example: karnataka_license_renewal.txt
    
    Args:
        filename: The filename to parse
    
    Returns:
        Tuple of (state, service_type, source_name)
    """
    # Remove extension
    name_without_ext = os.path.splitext(filename)[0]
    
    # Try to parse state and service_type
    parts = name_without_ext.split('_')
    
    if len(parts) >= 2:
        # First part is state, rest is service_type
        state = parts[0].capitalize()
        service_type = ' '.join(parts[1:]).capitalize()
        source_name = filename
        return state, service_type, source_name
    else:
        # Fallback if filename doesn't match expected format
        return "Unknown", "General", filename

def ingest_document(file_path, model, db):
    """
    Ingest a single policy document.
    
    Args:
        file_path: Path to the policy document
        model: SentenceTransformer model for embeddings
        db: Database session
    """
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Parse metadata from filename
        filename = os.path.basename(file_path)
        state, service_type, source_name = parse_metadata_from_filename(filename)
        
        logger.info(f"Processing: {filename}")
        logger.info(f"  State: {state}")
        logger.info(f"  Service Type: {service_type}")
        
        # Chunk the text
        chunks = chunk_text(text)
        logger.info(f"  Created {len(chunks)} chunks")
        
        # Generate embeddings for all chunks
        embeddings = model.encode(chunks, show_progress_bar=True)
        
        # Store chunks in database
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            policy_chunk = PolicyChunk(
                state=state,
                service_type=service_type,
                source_name=source_name,
                chunk_text=chunk,
                embedding=embedding.tolist()  # Convert numpy array to list
            )
            db.add(policy_chunk)
        
        db.commit()
        logger.info(f"  Successfully stored {len(chunks)} chunks\n")
        
    except Exception as e:
        db.rollback()
        logger.error(f"  Error processing {filename}: {e}\n")

def main():
    parser = argparse.ArgumentParser(description='Ingest policy documents into the RAG system')
    parser.add_argument('--folder', required=True, help='Path to folder containing policy documents')
    args = parser.parse_args()
    
    # Validate folder exists
    folder_path = Path(args.folder)
    if not folder_path.exists() or not folder_path.is_dir():
        logger.error(f"Folder '{args.folder}' does not exist or is not a directory")
        sys.exit(1)
    
    # Get all text files
    text_files = list(folder_path.glob('*.txt'))
    if not text_files:
        logger.error(f"No .txt files found in '{args.folder}'")
        sys.exit(1)
    
    logger.info(f"Found {len(text_files)} policy documents to ingest\n")
    
    # Load embedding model (using a free, open-source model)
    logger.info("Loading sentence-transformers model (this may take a moment)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')  # Free, lightweight model
    logger.info("Model loaded successfully\n")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Process each document
        for file_path in text_files:
            ingest_document(file_path, model, db)
        
        logger.info(f"\nIngestion complete! Processed {len(text_files)} documents.")
        
    except Exception as e:
        logger.error(f"\nError during ingestion: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()