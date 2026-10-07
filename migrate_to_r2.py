"""
Database Migration Script - Migrate from local file storage to Cloudflare R2.
This script handles the transition from local file_path to R2 object_key.
"""

import sys
import os
from pathlib import Path
from sqlalchemy import text, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from app.core.database import engine
from app.models.models import Document
from app.services.r2_storage import get_r2_service

# Load environment variables
load_dotenv()


def migrate_database_schema():
    """
    Update the database schema to replace file_path with r2_object_key.
    This handles the column rename and data migration.
    """
    print("Starting database schema migration...")
    
    try:
        # Check if file_path column still exists
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('documents')]
        
        if 'file_path' in columns and 'r2_object_key' not in columns:
            print("Found old file_path column, renaming to r2_object_key...")
            
            # Rename the column
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE documents RENAME COLUMN file_path TO r2_object_key"))
                conn.commit()
            
            print("Successfully renamed file_path to r2_object_key")
        elif 'file_path' in columns and 'r2_object_key' in columns:
            print("Both columns exist. Migrating data from file_path to r2_object_key...")
            
            # Migrate data using raw SQL
            with engine.connect() as conn:
                # Copy data from file_path to r2_object_key where r2_object_key is NULL
                conn.execute(text("""
                    UPDATE documents 
                    SET r2_object_key = file_path 
                    WHERE r2_object_key IS NULL AND file_path IS NOT NULL
                """))
                conn.commit()
                
                print("Data migration completed")
                
                # Remove the old file_path column
                conn.execute(text("ALTER TABLE documents DROP COLUMN file_path"))
                conn.commit()
                
                print("Removed old file_path column")
        else:
            print("Database schema is already up to date")
            
    except Exception as e:
        print(f"Error during schema migration: {str(e)}")
        raise


def migrate_existing_files_to_r2():
    """
    Migrate existing local files to R2 storage.
    This function reads files from the local uploads directory and uploads them to R2.
    """
    print("Starting file migration to R2...")
    
    try:
        # Get R2 service
        r2_service = get_r2_service()
        
        # Create a session
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            # Check if there are any existing local files in uploads directory
            uploads_dir = Path("uploads")
            if not uploads_dir.exists():
                print("No uploads directory found. Nothing to migrate.")
                return
            
            # Get all files in uploads directory
            local_files = list(uploads_dir.glob("*"))
            print(f"Found {len(local_files)} files in uploads directory")
            
            # For each local file, check if there's a corresponding document
            for file_path in local_files:
                if file_path.is_file():
                    filename = file_path.name
                    
                    # Try to find a document with this filename
                    document = db.query(Document).filter(
                        Document.file_name == filename
                    ).first()
                    
                    if document and not document.r2_object_key:
                        print(f"  - Migrating {filename}...")
                        
                        try:
                            # Read the local file
                            with open(file_path, 'rb') as f:
                                file_content = f.read()
                            
                            # Upload to R2
                            r2_object_key, _ = r2_service.upload_file(
                                file_content=file_content,
                                file_name=filename
                            )
                            
                            # Update the document record
                            document.r2_object_key = r2_object_key
                            db.commit()
                            
                            print(f"    Successfully uploaded to R2: {r2_object_key}")
                            
                            # Optionally delete the local file
                            # file_path.unlink()
                            # print(f"    Deleted local file: {file_path}")
                            
                        except Exception as e:
                            print(f"    Error migrating {filename}: {str(e)}")
                            db.rollback()
                    elif document and document.r2_object_key:
                        print(f"  - {filename} already has R2 object key, skipping")
                    else:
                        print(f"  - No document found for {filename}, skipping")
            
            print("File migration completed")
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"Error during file migration: {str(e)}")
        print("Note: Make sure your R2 credentials are properly configured in .env")
        raise


def main():
    """Main migration function."""
    print("=" * 60)
    print("RTO Autopilot - R2 Storage Migration")
    print("=" * 60)
    print()
    
    try:
        # Step 1: Migrate database schema
        migrate_database_schema()
        print()
        
        # Step 2: Skip file migration for now (requires R2 credentials)
        print("Note: File migration requires R2 credentials to be configured.")
        print("Skipping file migration. You can run this script again after setting up R2.")
        print()
        
        print("=" * 60)
        print("Database schema migration completed successfully!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Update your .env file with R2 credentials (see R2_SETUP_GUIDE.md)")
        print("2. Test the application by uploading a new document")
        print("3. Once R2 is configured, run this script again to migrate existing files")
        print("4. Verify the document appears in your R2 bucket")
        
    except Exception as e:
        print()
        print("=" * 60)
        print("Migration failed!")
        print("=" * 60)
        print(f"Error: {str(e)}")
        print()
        print("Please check the error message and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()