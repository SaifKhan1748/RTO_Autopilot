# RTO Autopilot - Architecture Diagram Description

## Overview
RTO Autopilot is a multi-tenant web application that automates Regional Transport Office (RTO) workflows for vehicle registration and licensing services. The system uses a modern Python stack with PostgreSQL database, vector embeddings for policy intelligence, and cloud storage for document management.

## System Components

### 1. Web Application Layer (FastAPI)
- **FastAPI Server**: Main application framework handling HTTP requests
- **Jinja2 Templates**: Server-side rendering for web UI
- **Session Middleware**: User authentication and session management
- **Rate Limiting**: SlowAPI for API rate limiting and DDoS protection
- **Background Scheduler**: APScheduler for automated reminder tasks

### 2. Database Layer (Neon PostgreSQL)
- **PostgreSQL Database**: Primary data store (hosted on Neon free tier)
- **pgvector Extension**: Vector similarity search for RAG (Retrieval-Augmented Generation)
- **Connection Pooling**: SQLAlchemy with connection pooling
- **Multi-tenant Architecture**: Office-based data isolation

### 3. AI & Intelligence Layer
- **Groq API**: LLM for case analysis and document understanding
- **Sentence Transformers**: Embedding generation for policy documents
- **Policy RAG Service**: Vector-based retrieval of RTO policies and procedures
- **Intake Agent**: AI-powered form filling assistance

### 4. Storage Layer (Cloudflare R2)
- **Document Storage**: Secure object storage for uploaded documents
- **R2 Service**: Wrapper for S3-compatible API
- **Access Control**: Bucket-level permissions for document security

### 5. Email Service (Resend)
- **Password Reset**: Email delivery for password reset flows
- **Notification System**: Email notifications for case updates

## Data Flow

### User Registration & Login Flow
```
User → Signup/Login Page → FastAPI → PostgreSQL (Staff Table)
                         → Session Creation → Cookie Storage
```

### Case Intake Flow
```
User → Intake Form → FastAPI → PostgreSQL (Cases, Customers, Documents)
                   → R2 Storage (Document Uploads)
                   → AI Analysis (Groq API)
                   → Policy RAG (pgvector)
```

### Case Management Flow
```
Staff → Dashboard → FastAPI → PostgreSQL (Cases, Events)
                   → Audit Log Creation
                   → Status Updates
```

### Automated Reminder Flow
```
APScheduler → Check Pending Documents → Generate Reminders
                                   → PostgreSQL (Pending Reminders)
                                   → Staff Approval
                                   → Email Notification (Resend)
```

### Document Analysis Flow
```
Case Analysis → FastAPI → Groq API (Document Understanding)
                        → Policy RAG (pgvector similarity search)
                        → PDF Generation (ReportLab)
```

## Database Schema

### Core Tables
- **offices**: Multi-tenant office definitions (name, code, display_name)
- **staff**: Office staff with authentication (email, password_hash, role)
- **customers**: Customer information per office
- **cases**: Vehicle registration cases linked to office and customer
- **documents**: Document uploads with R2 object keys
- **events**: Append-only audit trail for case history
- **pending_reminders**: Automated reminders awaiting staff approval
- **policy_chunks**: Vector embeddings for RAG (state, service_type, embedding)
- **checklist_configs**: Customizable document checklists per office
- **password_resets**: Secure password reset tokens

### Key Relationships
- Each office has multiple staff members and customers
- Each case belongs to one office and one customer
- Each case has multiple documents and events
- Policy chunks are indexed by state and service type
- Checklists are configured per office and service type

## Security Features

### Authentication
- Password hashing with bcrypt
- Session-based authentication
- Account lockout after 5 failed attempts (15-minute cooldown)
- Password reset with expiring tokens

### Authorization
- Role-based access control (admin, staff)
- Office-based data isolation (staff only see their office's data)
- Admin-only operations (audit logs, data deletion)

### Data Protection
- Rate limiting on sensitive endpoints
- SQL injection prevention via SQLAlchemy ORM
- Secure document storage with access controls
- Audit logging for all operations

## Deployment Architecture

### Production Deployment (Render or Railway)
```
User Browser → HTTPS → Render/Railway (FastAPI App)
                     → Neon PostgreSQL (Database)
                     → Cloudflare R2 (Storage)
                     → Groq API (AI)
                     → Resend API (Email)
```

### Development Environment
```
Local Machine → FastAPI (Uvicorn) → Local PostgreSQL
                             → Local File Storage
                             → API Services (Groq, Resend)
```

## Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: ORM for database operations
- **APScheduler**: Background task scheduling
- **Uvicorn**: ASGI server

### Database
- **PostgreSQL**: Relational database (Neon free tier)
- **pgvector**: Vector similarity search extension
- **psycopg2**: PostgreSQL adapter for Python

### AI & ML
- **Groq API**: Fast LLM inference
- **Sentence Transformers**: Text embeddings
- **NumPy**: Numerical operations

### Storage & External Services
- **Cloudflare R2**: S3-compatible object storage
- **Resend**: Email delivery service
- **ReportLab**: PDF generation

### Frontend
- **Jinja2**: Server-side templating
- **Tailwind CSS**: Utility-first CSS framework (via CDN)
- **HTML5/CSS3**: Modern web standards

## Diagram Layout Suggestion

When creating the actual diagram, organize components in three layers:

**Top Layer (User Interface)**
- Web Browser
- Mobile Browser

**Middle Layer (Application & Services)**
- FastAPI Web Service (Render/Railway)
- Background Scheduler
- API Gateways (Groq, Resend)

**Bottom Layer (Data & Storage)**
- Neon PostgreSQL (with pgvector)
- Cloudflare R2 Storage

Use arrows to show data flow between components, with labels indicating the type of operation (read, write, query, upload).

## Key Design Decisions

1. **Multi-tenant Architecture**: Office-based isolation allows the same system to serve multiple RTO offices without data leakage
2. **Vector Database**: pgvector enables intelligent policy retrieval without external vector database costs
3. **Cloud Storage**: R2 provides cost-effective document storage compared to Render's ephemeral filesystem
4. **Neon Database**: Free tier with no expiry and pgvector support, unlike Render's managed Postgres
5. **Event Sourcing**: Append-only event log provides complete audit trail for compliance
6. **Rate Limiting**: Protects against brute-force attacks and API abuse
