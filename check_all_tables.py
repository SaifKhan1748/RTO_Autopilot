from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Check all tables
    tables = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
    print("Tables:", [row[0] for row in tables])
    
    # Check offices table
    print("\n--- Offices table ---")
    result = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'offices'"))
    for row in result:
        print(f"{row[0]}: {row[1]}")
    
    # Check staff table
    print("\n--- Staff table ---")
    result = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'staff'"))
    for row in result:
        print(f"{row[0]}: {row[1]}")
    
    # Check customers table
    print("\n--- Customers table ---")
    result = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'customers'"))
    for row in result:
        print(f"{row[0]}: {row[1]}")
    
    # Check cases table
    print("\n--- Cases table ---")
    result = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'cases'"))
    for row in result:
        print(f"{row[0]}: {row[1]}")