"""
Migration script to export data from local PostgreSQL and import to Neon.
Run this after setting up your Neon database.
"""
import os
import sys
import time
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Local database connection
LOCAL_DB_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

# Neon database connection (update this with your Neon connection string)
NEON_DB_URL = "postgresql://neondb_owner:npg_bV8nd9RFwEXt@ep-dawn-wind-ak7e2ch4-pooler.c-3.us-west-2.aws.neon.tech/rto_autopilot?sslmode=require"

# Table names in order (respecting foreign key dependencies)
TABLES = [
    'offices',
    'staff',
    'customers',
    'cases',
    'documents',
    'events',
    'pending_reminders',
    'policy_chunks',
    'checklist_configs',
    'password_resets'
]

BATCH_SIZE = 50  # Process rows in smaller batches to avoid connection issues

def migrate_data():
    """Migrate data from local PostgreSQL to Neon."""
    print("Starting migration from local PostgreSQL to Neon...")
    
    # Create engines with pool settings for better connection handling
    local_engine = create_engine(LOCAL_DB_URL)
    neon_engine = create_engine(NEON_DB_URL, pool_pre_ping=True, pool_recycle=3600)
    
    try:
        for table in TABLES:
            print(f"\nMigrating table: {table}")
            
            # Read data from local database
            with local_engine.connect() as local_conn:
                result = local_conn.execute(text(f"SELECT * FROM {table}"))
                rows = result.fetchall()
                columns = result.keys()
                
                if not rows:
                    print(f"  No data in {table}, skipping...")
                    continue
                
                print(f"  Found {len(rows)} rows")
                
                # Prepare insert statement
                columns_str = ', '.join(columns)
                placeholders = ', '.join([':' + col for col in columns])
                insert_sql = text(f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})")
                
                # Insert data into Neon in batches
                total_migrated = 0
                for i in range(0, len(rows), BATCH_SIZE):
                    batch = rows[i:i+BATCH_SIZE]
                    
                    with neon_engine.begin() as neon_conn:
                        for row in batch:
                            row_dict = dict(zip(columns, row))
                            neon_conn.execute(insert_sql, row_dict)
                    
                    total_migrated += len(batch)
                    print(f"  Progress: {total_migrated}/{len(rows)} rows")
                    time.sleep(0.5)  # Small delay between batches
                
                print(f"  Successfully migrated {total_migrated} rows")
        
        print("\n[SUCCESS] Migration completed successfully!")
        print(f"\nYour Neon connection string is:")
        print(NEON_DB_URL)
        print("\nUpdate your .env file with:")
        print(f"DATABASE_URL={NEON_DB_URL}")
        
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("This script will migrate data from your local PostgreSQL to Neon.")
    print(f"Local database: {LOCAL_DB_URL}")
    print(f"Neon database: {NEON_DB_URL}")
    
    confirm = input("\nDo you want to proceed? (yes/no): ")
    if confirm.lower() == 'yes':
        migrate_data()
    else:
        print("Migration cancelled.")
