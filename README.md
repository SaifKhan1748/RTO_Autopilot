# RTO Autopilot

RTO Autopilot is a multi-tenant web application that automates Regional Transport Office (RTO) workflows for vehicle registration, licensing, and related services. It streamlines case management, document tracking, and policy compliance with AI-powered intelligence.

## Features

### Core Functionality
- **Multi-tenant Office Management**: Support for multiple RTO offices with complete data isolation
- **Case Intake & Tracking**: Streamlined workflow for vehicle registration, transfers, renewals, and licensing
- **Document Management**: Secure upload and tracking of required documents
- **Automated Reminders**: Smart reminder system for pending document submissions
- **Audit Logging**: Complete audit trail for all case operations
- **Customizable Checklists**: Office-specific document requirements per service type

### AI-Powered Features
- **Policy RAG (Retrieval-Augmented Generation)**: Intelligent policy lookup using vector embeddings
- **Case Analysis**: AI-powered document analysis and case insights
- **Intake Agent**: AI-assisted form filling for new cases
- **Policy Intelligence**: State-specific RTO policy retrieval (Karnataka, Maharashtra, etc.)

### Security & Compliance
- **Role-Based Access Control**: Admin and staff roles with appropriate permissions
- **Account Lockout**: Brute-force protection with 5-attempt lockout
- **Password Reset**: Secure email-based password reset flow
- **Rate Limiting**: API rate limiting to prevent abuse
- **Office Isolation**: Staff can only access their office's data

## Technology Stack

- **Backend**: FastAPI, SQLAlchemy, APScheduler
- **Database**: PostgreSQL with pgvector (hosted on Neon)
- **Storage**: Cloudflare R2 (S3-compatible)
- **AI/ML**: Groq API, Sentence Transformers
- **Email**: Resend API
- **Frontend**: Jinja2 templates, Tailwind CSS

## Architecture

For detailed architecture information, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Prerequisites

- Python 3.11 or higher
- PostgreSQL 13 or higher (or use Neon free tier)
- Groq API key
- Resend API key (for password reset emails)
- Cloudflare R2 account (for document storage)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd rto-autopilot
```

### 2. Create Virtual Environment

```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Database

#### Option A: Local PostgreSQL

1. Install PostgreSQL on your machine
2. Create a database:
```sql
CREATE DATABASE rto_autopilot;
```

3. Enable pgvector extension:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

#### Option B: Neon PostgreSQL (Recommended for Production)

1. Sign up at [console.neon.tech](https://console.neon.tech)
2. Create a new project named "rto-autopilot"
3. Create a database named "rto_autopilot"
4. Enable pgvector extension in the SQL editor:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
5. Copy the connection string from the Neon dashboard

### 5. Configure Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Database Configuration
DATABASE_URL=postgresql://user:password@host:port/rto_autopilot

# Email Service (Resend) for Password Reset
RESEND_API_KEY=your_resend_api_key_here

# Session Secret Key (change this in production!)
SECRET_KEY=your-secret-key-change-this-in-production

# Cloudflare R2 Storage (for document uploads)
R2_ACCOUNT_ID=your_r2_account_id
R2_ACCESS_KEY_ID=your_r2_access_key_id
R2_SECRET_ACCESS_KEY=your_r2_secret_access_key
R2_BUCKET_NAME=your_r2_bucket_name

# AI Service (Groq)
GROQ_API_KEY=your_groq_api_key_here
```

### 6. Initialize Database Tables

```bash
python init_db.py
```

This will create all required tables in your database.

### 7. (Optional) Ingest Policy Documents

If you want to use the policy RAG feature:

```bash
python -m app.scripts.ingest_policy_docs
```

This will ingest policy documents from the `policy_documents/` directory into the database with vector embeddings.

## Running the Application

### Development Mode

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The application will be available at `http://localhost:8000`

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Initial Setup

### Create an Office

1. Navigate to `http://localhost:8000/signup`
2. Fill in the office details:
   - Office Name: e.g., "Central RTO Office"
   - Office Code: e.g., "central-rto" (must be unique)
   - Admin Email: your email address
   - Admin Password: secure password
   - Admin Full Name: your name
   - Display Name: optional (for branding)

3. Click "Create Office"

This will create:
- A new office record
- An admin staff account
- Default checklist configurations for common service types

### Login

1. Navigate to `http://localhost:8000/login`
2. Enter your admin email and password
3. You'll be redirected to the dashboard

## Usage

### Creating a New Case

1. Click "New Case" in the dashboard
2. Enter customer information
3. Select service type (New Registration, Transfer, Renewal, License Renewal, etc.)
4. Upload required documents based on the checklist
5. Submit the case

### Managing Cases

- **Dashboard**: View all cases for your office
- **Case Detail**: View case details, documents, and event history
- **Status Updates**: Change case status (pending, in_progress, completed, rejected)
- **Document Upload**: Add additional documents to a case

### AI-Powered Analysis

1. Navigate to a case detail page
2. Click "Analyze Case" to get AI-powered insights
3. The system will:
   - Analyze uploaded documents
   - Retrieve relevant policies using RAG
   - Provide recommendations and requirements

### Automated Reminders

The system automatically checks for cases where documents were requested more than 2 days ago but haven't been uploaded. Staff can:
- Review drafted reminder messages
- Approve or reject reminders
- System sends email notifications for approved reminders

### Admin Functions

Admin users can:
- View audit logs for all operations
- Delete customer data (with confirmation)
- Configure office settings
- Manage staff accounts

## Deployment

### Render Deployment

1. Create a free account at [render.com](https://render.com)
2. Create a new Web Service
3. Connect your GitHub repository
4. Configure build settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables in the Render dashboard:
   - `DATABASE_URL`: Your Neon connection string
   - `SECRET_KEY`: Generate a secure random key
   - `GROQ_API_KEY`: Your Groq API key
   - `RESEND_API_KEY`: Your Resend API key
   - `R2_ACCOUNT_ID`: Your R2 account ID
   - `R2_ACCESS_KEY_ID`: Your R2 access key
   - `R2_SECRET_ACCESS_KEY`: Your R2 secret key
   - `R2_BUCKET_NAME`: Your R2 bucket name
6. Deploy

### Railway Deployment

1. Create a free account at [railway.app](https://railway.app)
2. Create a new project
3. Add a PostgreSQL service (or use your Neon connection string)
4. Add your GitHub repository
5. Configure environment variables
6. Deploy

**Important**: Use Neon for PostgreSQL (not Render/Railway's managed Postgres) because:
- Neon's free tier has no expiry date
- Neon supports pgvector (required for RAG feature)
- Render's managed Postgres auto-deletes after 30 days on free tier

## Migrating Data to Neon

If you have existing data in a local PostgreSQL database and want to migrate to Neon:

1. Set up your Neon database as described above
2. Update the `NEON_DB_URL` in `migrate_to_neon.py` with your Neon connection string
3. Run the migration script:
```bash
python migrate_to_neon.py
```
4. Update your `.env` file with the Neon connection string

## Testing

Run the test suite:

```bash
pytest
```

## Project Structure

```
rto-autopilot/
├── app/
│   ├── core/
│   │   ├── database.py       # Database configuration
│   │   ├── ai_client.py      # Groq API client
│   │   └── exceptions.py     # Exception handlers
│   ├── models/
│   │   └── models.py         # SQLAlchemy models
│   ├── routers/
│   │   ├── intake.py         # Intake API routes
│   │   ├── analytics.py      # Analytics API routes
│   │   └── case_analysis.py  # Case analysis routes
│   ├── services/
│   │   ├── policy_rag.py     # Policy RAG service
│   │   ├── r2_storage.py     # R2 storage service
│   │   ├── pdf_generator.py  # PDF generation
│   │   ├── intake_agent.py   # AI intake agent
│   │   └── case_analysis.py  # Case analysis service
│   ├── templates/            # Jinja2 HTML templates
│   ├── scripts/
│   │   └── ingest_policy_docs.py  # Policy document ingestion
│   ├── main.py               # FastAPI application
│   └── scheduler.py          # Background task scheduler
├── policy_documents/         # Policy documents for RAG
├── tests/                    # Test suite
├── docs/                     # Documentation
├── .env                      # Environment variables (not in git)
├── .env.example              # Environment variables template
├── requirements.txt          # Python dependencies
├── render.yaml              # Render deployment config
├── railway.json             # Railway deployment config
└── init_db.py               # Database initialization script
```

## API Documentation

Once the application is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Troubleshooting

### Database Connection Issues
- Verify your `DATABASE_URL` is correct
- Ensure PostgreSQL is running (if using local)
- Check firewall settings (if using Neon)

### pgvector Extension Not Found
- Ensure you're using PostgreSQL 13 or higher
- Run `CREATE EXTENSION IF NOT EXISTS vector;` in your database
- If using Neon, pgvector is available by default

### R2 Upload Failures
- Verify your R2 credentials are correct
- Ensure the bucket exists and is accessible
- Check bucket permissions

### AI Analysis Not Working
- Verify your `GROQ_API_KEY` is valid
- Check that policy documents have been ingested
- Ensure pgvector extension is enabled

## Contributing

Contributions are welcome! Please read the project's documentation and follow the existing code style.

## License

[Add your license here]

## Support

For issues or questions, please open an issue on the GitHub repository.
