# RTO Autopilot - Deployment Guide

This guide walks you through deploying RTO Autopilot to production using Render or Railway for the web service, and Neon for the PostgreSQL database.

## Prerequisites

Before starting deployment, ensure you have:

1. A GitHub repository with your RTO Autopilot code
2. A Neon account (free tier) for PostgreSQL
3. A Render or Railway account (free tier)
4. API keys for:
   - Groq (AI service)
   - Resend (email service)
   - Cloudflare R2 (document storage)

## Step 1: Set Up Neon PostgreSQL Database

### Why Neon?

- **Free tier has no expiry date** (unlike Render's managed Postgres which auto-deletes after 30 days)
- **Supports pgvector extension** (required for RAG feature)
- **Generous free tier limits**: 0.5 GB storage, 200 hours compute/month
- **Excellent performance** with serverless architecture

### Create Neon Project

1. Go to [console.neon.tech](https://console.neon.tech)
2. Sign up or log in
3. Click "Create a project"
4. Enter project name: `rto-autopilot`
5. Select region (choose closest to your deployment region)
6. Click "Create project"

### Create Database

1. In your Neon project, click "SQL Editor"
2. Run the following SQL:

```sql
CREATE DATABASE rto_autopilot;
```

3. Verify the database was created by clicking "Branches" and checking the databases list

### Enable pgvector Extension

1. Still in the SQL Editor, ensure you're connected to the `rto_autopilot` database
2. Run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

3. Verify it's enabled:

```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### Get Connection String

1. In Neon dashboard, go to your project
2. Click "Connection Details"
3. Copy the connection string (it will look like):
```
postgresql://neondb_owner:xxx@ep-xxx.us-west-2.aws.neon.tech/rto_autopilot?sslmode=require
```

**Save this connection string** - you'll need it for deployment configuration.

### Migrate Existing Data (Optional)

If you have existing data in a local PostgreSQL database:

1. Update the `NEON_DB_URL` in `migrate_to_neon.py` with your Neon connection string
2. Run the migration script:

```bash
python migrate_to_neon.py
```

3. The script will migrate all your data in batches of 50 rows to avoid connection issues

## Step 2: Deploy to Render

### Why Render?

- **Free tier available** for web services
- **Automatic SSL certificates**
- **Easy GitHub integration**
- **Built-in logging and monitoring**
- **Supports background workers** (for scheduler)

### Deploy to Render

1. **Push code to GitHub** (if not already done):
```bash
git add .
git commit -m "Ready for deployment"
git push origin main
```

2. **Create Render account** at [render.com](https://render.com)

3. **Create new Web Service**:
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the repository
   - Click "Connect"

4. **Configure build settings**:
   - **Name**: `rto-autopilot`
   - **Region**: Choose a region (same as Neon if possible)
   - **Branch**: `main`
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

5. **Configure environment variables**:
   Click "Advanced" → "Add Environment Variable"

   Add the following variables:

   ```
   DATABASE_URL=postgresql://neondb_owner:xxx@ep-xxx.us-west-2.aws.neon.tech/rto_autopilot?sslmode=require
   SECRET_KEY=<generate-a-secure-random-key>
   GROQ_API_KEY=your_groq_api_key
   RESEND_API_KEY=your_resend_api_key
   R2_ACCOUNT_ID=your_r2_account_id
   R2_ACCESS_KEY_ID=your_r2_access_key_id
   R2_SECRET_ACCESS_KEY=your_r2_secret_access_key
   R2_BUCKET_NAME=your_r2_bucket_name
   ```

   **Important**: For `SECRET_KEY`, generate a secure random key:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

6. **Deploy**:
   - Click "Create Web Service"
   - Wait for deployment to complete (2-5 minutes)
   - Render will provide a URL like `https://rto-autopilot.onrender.com`

7. **Initialize database tables**:
   - Once deployed, access the Render shell or use a local script to run:
   ```bash
   python init_db.py
   ```
   - This will create all required tables in your Neon database

### Using render.yaml (Alternative)

For automated deployment, use the included `render.yaml` file:

1. Ensure `render.yaml` is in your repository root
2. In Render, select "Existing blueprint" when creating a new service
3. Render will automatically read the configuration

## Step 3: Deploy to Railway (Alternative)

### Why Railway?

- **Simple deployment process**
- **Free tier available**
- **Built-in PostgreSQL** (but we'll use Neon instead)
- **Good for quick deployments**

### Deploy to Railway

1. **Create Railway account** at [railway.app](https://railway.app)

2. **Create new project**:
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

3. **Configure environment variables**:
   - Go to your project settings
   - Add the same environment variables as in Render step 5 above

4. **Deploy**:
   - Railway will automatically deploy
   - Wait for deployment to complete
   - Railway will provide a URL

5. **Initialize database**:
   - Same as Render step 7

## Step 4: Configure Cloudflare R2 Storage

### Why R2?

- **S3-compatible API**
- **Generous free tier**: 10 GB storage, 1 million Class A operations/month
- **No egress fees** (unlike AWS S3)
- **Fast performance**

### Set Up R2

1. **Create Cloudflare account** at [dash.cloudflare.com](https://dash.cloudflare.com)

2. **Create R2 bucket**:
   - Go to "R2" → "Create bucket"
   - Name: `rto-autopilot-documents` (or your preferred name)
   - Click "Create bucket"

3. **Get API credentials**:
   - Go to "R2" → "Manage R2 API Tokens"
   - Click "Create API Token"
   - Permissions: "Object Read & Write"
   - TTL: Choose appropriate duration
   - Copy:
     - Account ID (from Cloudflare dashboard)
     - Access Key ID
     - Secret Access Key

4. **Update environment variables**:
   - Add these to your Render/Railway environment variables:
   ```
   R2_ACCOUNT_ID=your_account_id
   R2_ACCESS_KEY_ID=your_access_key_id
   R2_SECRET_ACCESS_KEY=your_secret_access_key
   R2_BUCKET_NAME=your_bucket_name
   ```

5. **Redeploy**:
   - Trigger a new deployment in Render/Railway to pick up the new variables

## Step 5: Configure Groq API

### Get Groq API Key

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up or log in
3. Go to "API Keys"
4. Create a new API key
5. Copy the key

### Add to Environment Variables

Add to your Render/Railway environment variables:
```
GROQ_API_KEY=your_groq_api_key
```

## Step 6: Configure Resend API (Email Service)

### Get Resend API Key

1. Go to [resend.com](https://resend.com)
2. Sign up or log in
3. Go to "API Keys"
4. Create a new API key
5. Copy the key

### Verify Domain (Optional)

For production email delivery:
1. In Resend, go to "Domains"
2. Add your domain (e.g., `rtoautopilot.com`)
3. Add DNS records as instructed
4. Wait for domain verification

### Add to Environment Variables

Add to your Render/Railway environment variables:
```
RESEND_API_KEY=your_resend_api_key
```

## Step 7: Initialize Database

Once deployed, you need to create the database tables:

### Option A: Remote Shell (Render)

1. In Render dashboard, go to your web service
2. Click "Shell" (or "SSH")
3. Run:
```bash
python init_db.py
```

### Option B: Local Script

1. Update your local `.env` with the production `DATABASE_URL`
2. Run locally:
```bash
python init_db.py
```

### Option C: Render Build Script

Add to your `render.yaml`:
```yaml
services:
  - type: web
    name: rto-autopilot
    env: python
    buildCommand: pip install -r requirements.txt && python init_db.py
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    # ... rest of configuration
```

## Step 8: Ingest Policy Documents (Optional)

If you want to use the policy RAG feature:

1. Add policy documents to the `policy_documents/` directory
2. Run the ingestion script:
```bash
python -m app.scripts.ingest_policy_docs
```

This will:
- Read all `.txt` files from `policy_documents/`
- Split them into chunks
- Generate embeddings using Sentence Transformers
- Store chunks with embeddings in the `policy_chunks` table

## Step 9: Create Initial Office

1. Access your deployed application at the provided URL
2. Navigate to `/signup`
3. Create your office with admin credentials
4. This will create:
   - Office record
   - Admin staff account
   - Default checklist configurations

## Step 10: Verify Deployment

### Health Checks

1. **Test homepage**: Visit your URL, should see the landing page
2. **Test signup**: Create a test office
3. **Test login**: Login with admin credentials
4. **Test case creation**: Create a test case
5. **Test document upload**: Upload a test document to R2
6. **Test AI analysis**: Try the case analysis feature

### Monitoring

- **Render logs**: Check Render dashboard for logs
- **Railway logs**: Check Railway dashboard for logs
- **Neon logs**: Check Neon dashboard for database activity
- **R2 usage**: Check Cloudflare dashboard for storage usage

## Troubleshooting

### Database Connection Issues

**Symptom**: Application fails to start with database connection error

**Solutions**:
1. Verify `DATABASE_URL` is correct in environment variables
2. Check Neon database is running (not suspended)
3. Ensure pgvector extension is enabled
4. Check firewall settings in Neon dashboard

### Build Failures

**Symptom**: Deployment fails during build

**Solutions**:
1. Check Render/Railway build logs
2. Ensure all dependencies are in `requirements.txt`
3. Verify Python version compatibility
4. Check for missing files in repository

### Runtime Errors

**Symptom**: Application starts but crashes on requests

**Solutions**:
1. Check application logs
2. Verify all environment variables are set
3. Check database tables exist (run `init_db.py`)
4. Verify API keys are valid

### R2 Upload Failures

**Symptom**: Document uploads fail

**Solutions**:
1. Verify R2 credentials are correct
2. Check bucket exists and is accessible
3. Verify bucket permissions
4. Check R2 usage limits

### AI Analysis Not Working

**Symptom**: AI features return errors

**Solutions**:
1. Verify `GROQ_API_KEY` is valid
2. Check Groq API status
3. Ensure policy documents are ingested (for RAG)
4. Verify pgvector extension is enabled

## Maintenance

### Regular Tasks

**Weekly**:
- Check application logs for errors
- Monitor database storage usage
- Monitor R2 storage usage
- Review analytics for trends

**Monthly**:
- Update dependencies: `pip install --upgrade -r requirements.txt`
- Review and update security patches
- Check API quota usage (Groq, Resend)
- Backup database (Neon has automatic backups)

**Quarterly**:
- Review and optimize performance
- Update policy documents
- Staff training refresh
- Security audit

### Scaling

When you need to scale beyond free tier limits:

**Render**:
- Upgrade to Starter plan ($7/month) for better performance
- Add more workers for concurrency
- Use Redis for session storage

**Neon**:
- Upgrade to paid plan for more storage/compute
- Enable read replicas for better performance

**R2**:
- Paid tier for more storage
- Consider CDN for faster document delivery

## Security Best Practices

1. **Rotate API keys regularly**
2. **Use strong `SECRET_KEY`** (generate with `secrets.token_urlsafe(32)`)
3. **Enable SSL** (automatic on Render/Railway)
4. **Regular security updates**
5. **Monitor for suspicious activity**
6. **Keep dependencies updated**
7. **Use environment variables for secrets** (never commit to git)
8. **Enable account lockout** (already implemented)
9. **Regular backups** (Neon has automatic backups)
10. **Audit logs** (already implemented)

## Cost Summary

### Free Tier Limits

**Render**:
- Web Service: 750 hours/month
- SSD: 10 GB
- Bandwidth: 100 GB/month

**Railway**:
- $5 free credit/month
- 512 MB RAM
- 0.5 vCPU

**Neon**:
- Storage: 0.5 GB
- Compute: 200 hours/month
- Data transfer: 32 GB/month

**R2**:
- Storage: 10 GB
- Class A operations: 1 million/month
- Class B operations: 10 million/month

**Groq**:
- Free tier with generous limits
- Check current pricing at console.groq.com

**Resend**:
- 3,000 emails/month free
- $0.002 per additional email

### Estimated Monthly Cost (if exceeding free tiers)

- Render (Starter): $7/month
- Neon (Paid): Starts at $19/month
- R2 (Paid): $0.015/GB/month
- Groq: Usage-based
- Resend: Usage-based

**Total**: ~$26-50/month for a production-grade setup

## Support

For issues or questions:
- Check application logs
- Review this deployment guide
- Check Neon/Railway/Render documentation
- Open an issue on GitHub

## Next Steps

After successful deployment:

1. Train staff on the new system
2. Migrate existing cases and documents
3. Set up monitoring and alerts
4. Document office-specific workflows
5. Regular review and optimization
