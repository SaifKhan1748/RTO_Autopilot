# Cloudflare R2 Setup Guide for RTO Autopilot

This guide will walk you through setting up Cloudflare R2 (S3-compatible object storage) for your RTO Autopilot application to securely store uploaded documents.

## Why Cloudflare R2?

- **Free Tier**: R2 offers a generous free tier (10GB storage, 10 million Class A operations/month)
- **S3-Compatible**: Works with standard S3 tools and libraries (like boto3)
- **Secure**: Files are private by default, accessible only via signed URLs
- **Scalable**: No need to worry about storage limits or server redeployment
- **Cost-Effective**: No egress fees (unlike AWS S3)

## Step-by-Step Setup Instructions

### Step 1: Create a Cloudflare Account

1. Go to [https://dash.cloudflare.com/sign-up](https://dash.cloudflare.com/sign-up)
2. Sign up for a free Cloudflare account (if you don't have one)
3. Verify your email address
4. Log in to the Cloudflare Dashboard

### Step 2: Enable R2 in Your Cloudflare Account

1. In the Cloudflare Dashboard, click on **R2** in the left sidebar
2. If R2 is not visible, you may need to enable it:
   - Click on your profile in the top-right corner
   - Select **Subscriptions & Add-ons**
   - Find **R2** and click **Enable**
3. Once enabled, you'll see the R2 dashboard

### Step 3: Create an R2 Bucket

1. In the R2 dashboard, click **Create bucket**
2. Enter a bucket name (e.g., `rto-autopilot-documents`)
   - **Note**: Bucket names must be globally unique across all R2 users
   - Use only lowercase letters, numbers, and hyphens
   - Must start and end with a letter or number
3. Select a location (default is fine for most use cases)
4. **Important**: Keep the bucket **Private** (do not enable public access)
5. Click **Create bucket**

### Step 4: Get Your R2 Credentials

1. In the R2 dashboard, click on **Manage R2 API Tokens** (or go to Settings → R2 API)
2. Click **Create API Token**
3. Choose **Admin API Token** for full access, or customize permissions if needed
4. Give the token a name (e.g., "RTO Autopilot API Token")
5. Select the permissions needed:
   - **Object Read & Write** for your bucket
6. Click **Create API Token**
7. **Important**: Copy the following information immediately (you won't see it again):
   - **Account ID** (found in the right sidebar of your R2 dashboard)
   - **Access Key ID**
   - **Secret Access Key**

### Step 5: Configure Your Application

1. Open your `.env` file in the RTO Autopilot project directory
2. Add the following variables with your R2 credentials:

```env
# Cloudflare R2 Storage Configuration
R2_ACCOUNT_ID=your_actual_account_id_here
R2_ACCESS_KEY_ID=your_actual_access_key_here
R2_SECRET_ACCESS_KEY=your_actual_secret_key_here
R2_BUCKET_NAME=your_actual_bucket_name_here
```

Replace the placeholder values with:
- `R2_ACCOUNT_ID`: Your Cloudflare Account ID (from Step 4)
- `R2_ACCESS_KEY_ID`: The Access Key ID from your API token
- `R2_SECRET_ACCESS_KEY`: The Secret Access Key from your API token
- `R2_BUCKET_NAME`: The exact name of the bucket you created in Step 3

### Step 6: Install Required Dependencies

1. Open your terminal/command prompt
2. Navigate to your project directory:
   ```bash
   cd C:\Users\saifk\Downloads\rto-autopilot
   ```
3. Activate your virtual environment (if not already active):
   ```bash
   venv\Scripts\activate
   ```
4. Install the boto3 library:
   ```bash
   pip install boto3
   ```

### Step 7: Run Database Migration (If You Have Existing Documents)

If you have existing documents stored locally and want to migrate them to R2:

1. Run the migration script:
   ```bash
   python migrate_to_r2.py
   ```
2. Follow the prompts to migrate your database schema and existing files
3. The script will:
   - Update the database schema (rename `file_path` to `r2_object_key`)
   - Upload existing local files to R2
   - Update document records with new R2 object keys

### Step 8: Test the Setup

1. Start your FastAPI application:
   ```bash
   python -m uvicorn app.main:app --reload
   ```
2. Log in to your application
3. Navigate to a case detail page
4. Try uploading a new document
5. Verify the upload succeeds
6. Click on the "View/Download" link for the document
7. The document should open via a signed URL (valid for 10 minutes)

### Step 9: Verify Files in R2 Dashboard

1. Go to your Cloudflare R2 dashboard
2. Click on your bucket name
3. You should see the uploaded files listed there
4. You can click on a file to view its details and metadata

## Security Best Practices

1. **Never commit credentials to version control**: The `.env` file should be in `.gitignore`
2. **Use read-only tokens for read operations**: If you only need to read files, create a token with read-only permissions
3. **Rotate credentials periodically**: Update your API tokens regularly for better security
4. **Monitor usage**: Check your R2 usage in the Cloudflare dashboard to stay within free tier limits
5. **Keep bucket private**: Never enable public access on your R2 bucket

## Troubleshooting

### Error: "Missing R2 configuration"
- Make sure all four R2 environment variables are set in your `.env` file
- Restart your application after updating the `.env` file

### Error: "Access Denied"
- Verify your API token has the correct permissions for the bucket
- Check that the bucket name in your `.env` matches exactly (case-sensitive)
- Ensure your Access Key ID and Secret Access Key are correct

### Error: "Bucket not found"
- Verify the bucket name in your `.env` file
- Check that the bucket exists in your R2 dashboard
- Ensure you're using the correct Account ID

### Signed URLs expire too quickly
- The default expiration is 10 minutes (600 seconds)
- You can adjust this in the `download_document` endpoint in `app/main.py`
- Change `expiration_seconds=600` to a higher value if needed

### Migration script fails
- Ensure your R2 credentials are properly configured before running the migration
- Check that your local `uploads` directory exists and contains files
- Verify your database connection is working

## Cost Monitoring

R2's free tier includes:
- 10 GB storage
- 10 million Class A operations (write requests) per month
- 10 million Class B operations (read requests) per month

Monitor your usage in the Cloudflare R2 dashboard to avoid unexpected charges.

## Next Steps

After completing the setup:
1. Remove or backup your local `uploads` directory (files are now in R2)
2. Update your deployment process to include the R2 environment variables
3. Consider implementing file deletion functionality for old documents
4. Set up monitoring for R2 usage and costs

## Support

If you encounter issues:
- Check the [Cloudflare R2 documentation](https://developers.cloudflare.com/r2/)
- Review Cloudflare's [API token documentation](https://developers.cloudflare.com/api/tokens/)
- Ensure your Python environment has the required dependencies installed