# Quick Setup with SQLite (For Testing/Screenshots)

This guide helps you set up RTO Autopilot with SQLite for easy testing and screenshot capture. SQLite doesn't require any external database setup.

## Step 1: Create .env File

Create a `.env` file in the project root with these contents:

```env
# Use SQLite for local development (easiest for testing)
USE_SQLITE=true

# Session Secret Key
SECRET_KEY=dev-secret-key-change-in-production

# Optional: Add these if you want to test AI features
GROQ_API_KEY=your_groq_api_key_here

# Optional: Add these if you want to test email features
RESEND_API_KEY=your_resend_api_key_here

# Optional: Add these if you want to test document uploads
R2_ACCOUNT_ID=your_r2_account_id
R2_ACCESS_KEY_ID=your_r2_access_key_id
R2_SECRET_ACCESS_KEY=your_r2_secret_access_key
R2_BUCKET_NAME=your_r2_bucket_name
```

**Important**: Only set the API keys if you want to test those specific features. For basic screenshot testing, you only need `USE_SQLITE=true` and `SECRET_KEY`.

## Step 2: Initialize Database

Run the database initialization script:

```bash
python init_db.py
```

This will create a `test.db` file in your project directory with all required tables.

## Step 3: Start the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The app will now run at `http://localhost:8000` using SQLite.

## Step 4: Follow the User Guide

Now follow the steps in `USER_GUIDE.md` to take screenshots. The app will work the same way, just using a local SQLite database instead of PostgreSQL.

## What Works with SQLite

✅ **Core Features** (all work with SQLite):
- Office creation and signup
- Login/logout
- Dashboard
- Add customer
- Create case
- View case details
- Update case status
- Event history/audit log
- Admin checklist management
- Data deletion
- Analytics dashboard
- PWA features
- Status check (public feature)

⚠️ **Limited Features** (require additional setup):
- **AI Intake**: Requires `GROQ_API_KEY` in .env
- **Document Uploads**: Requires R2 storage credentials
- **Password Reset Emails**: Requires `RESEND_API_KEY` in .env
- **Policy RAG**: Requires PostgreSQL with pgvector (not available in SQLite)

## Resetting the Database

If you want to start fresh (clear all data), simply:

1. Stop the application
2. Delete the `test.db` file
3. Run `python init_db.py` again
4. Restart the application

## Switching Back to PostgreSQL

If you want to switch to PostgreSQL/Neon later:

1. Edit `.env`:
   ```env
   USE_SQLITE=false
   DATABASE_URL=postgresql://user:password@host:port/rto_autopilot
   ```
2. Delete `test.db` (SQLite file)
3. Run `python init_db.py` (this will use PostgreSQL)
4. Restart the application

## Troubleshooting

**Error: "database is locked"**
- Stop the application first before deleting test.db
- Make sure only one instance of the app is running

**Error: "table already exists"**
- Delete test.db and run init_db.py again
- Or just continue using the existing database

**AI features not working**
- Make sure GROQ_API_KEY is set in .env
- Check that the key is valid

## Notes

- SQLite is perfect for development and testing
- SQLite file (`test.db`) is created in the project root
- All data is stored locally on your computer
- No external services required for basic features
- SQLite doesn't support pgvector (RAG feature won't work)
- For production, use PostgreSQL/Neon
