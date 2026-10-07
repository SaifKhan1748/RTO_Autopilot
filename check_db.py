from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'offices'"))
    columns = [row[0] for row in result]
    print("Office table columns:", columns)