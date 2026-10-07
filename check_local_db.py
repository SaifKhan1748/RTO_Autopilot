from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')
conn = engine.connect()

result = conn.execute(text('SELECT COUNT(*) FROM offices'))
print(f'Offices: {result.scalar()}')

result = conn.execute(text('SELECT COUNT(*) FROM staff'))
print(f'Staff: {result.scalar()}')

result = conn.execute(text('SELECT COUNT(*) FROM cases'))
print(f'Cases: {result.scalar()}')

conn.close()
