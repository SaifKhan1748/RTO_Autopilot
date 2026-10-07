# R2 Storage Migration Summary

## What Changed and Why

### Problem with Previous Implementation
Your application was saving uploaded documents to a local `uploads` folder in the project directory. This approach has several critical issues:

1. **Data Loss on Redeploy**: Files get wiped when you redeploy the application
2. **No Access Control**: Anyone with access to the server could access sensitive documents
3. **Security Risk**: Sensitive documents shouldn't live in the codebase
4. **Scalability Issues**: Local storage doesn't scale across multiple servers
5. **No Backup Strategy**: Local files are not automatically backed up

### Solution: Cloudflare R2 Storage
We migrated to Cloudflare R2, which provides:

1. **Persistent Storage**: Files survive redeployments and server changes
2. **Secure Access**: Files are private by default, accessible only via signed URLs
3. **Scalability**: Cloud-based storage that grows with your needs
4. **Cost-Effective**: Generous free tier (10GB storage, 10M operations/month)
5. **S3-Compatible**: Uses standard boto3 library, easy to maintain

## Changes Made

### 1. Dependencies Updated
- **File**: `requirements.txt`
- **Change**: Added `boto3` library for S3-compatible R2 operations

### 2. New R2 Storage Service
- **File**: `app/services/r2_storage.py` (new file)
- **Purpose**: Handles all R2 operations (upload, signed URLs, deletion)
- **Key Features**:
  - `upload_file()`: Uploads files to R2 with unique object keys
  - `generate_signed_url()`: Creates time-limited access URLs (default 10 minutes)
  - `delete_file()`: Removes files from R2
  - `file_exists()`: Checks if a file exists in R2

### 3. Database Model Updated
- **File**: `app/models/models.py`
- **Change**: Renamed `file_path` column to `r2_object_key` in Document model
- **Reason**: Store R2 object key instead of local file path

### 4. Document Upload Refactored
- **File**: `app/main.py`
- **Endpoint**: `POST /case/{case_id}/upload`
- **Changes**:
  - Removed local file saving logic
  - Added R2 upload functionality
  - Stores R2 object key instead of local path
  - Preserves original filename for display

### 5. Signed URL Endpoint Added
- **File**: `app/main.py`
- **Endpoint**: `GET /documents/{document_id}/download`
- **Purpose**: Generates secure, time-limited access URLs
- **Security**: 
  - Requires authentication
  - Validates office ownership
  - URLs expire after 10 minutes
  - Files remain private in R2

### 6. Frontend Updated
- **File**: `app/templates/case_detail.html`
- **Change**: Updated document download links to use signed URL endpoint
- **Old**: `/uploads/{{ document.file_name }}`
- **New**: `/documents/{{ document.id }}/download`

### 7. Local File Serving Removed
- **File**: `app/main.py`
- **Changes**:
  - Removed uploads directory mounting
  - Removed local file path handling
  - Removed unused imports (Path, uuid, os)

### 8. Environment Configuration
- **Files**: `.env` and `.env.example`
- **Added Variables**:
  - `R2_ACCOUNT_ID`: Cloudflare account ID
  - `R2_ACCESS_KEY_ID`: R2 API access key
  - `R2_SECRET_ACCESS_KEY`: R2 API secret key
  - `R2_BUCKET_NAME`: Name of your R2 bucket

### 9. Migration Script Created
- **File**: `migrate_to_r2.py` (new file)
- **Purpose**: Migrates existing data from local storage to R2
- **Features**:
  - Updates database schema (renames column)
  - Uploads existing local files to R2
  - Updates document records with new object keys
  - Safe rollback on errors

## Security Improvements

### Before (Local Storage)
- Files stored in project directory
- Publicly accessible via `/uploads/` route
- No access control or expiration
- Vulnerable to directory traversal attacks

### After (R2 Storage)
- Files stored in private R2 bucket
- Access only via authenticated signed URLs
- URLs expire after 10 minutes
- R2 provides built-in security features
- No direct file system access

## Testing Instructions

### Prerequisites
1. Complete the R2 setup using `R2_SETUP_GUIDE.md`
2. Install boto3: `pip install boto3`
3. Configure R2 credentials in `.env` file

### Step 1: Test Application Startup
```bash
cd C:\Users\saifk\Downloads\rto-autopilot
venv\Scripts\activate
python -m uvicorn app.main:app --reload
```

**Expected Result**: Application starts without errors

### Step 2: Test Document Upload
1. Log in to the application
2. Navigate to a case detail page
3. Fill in document type (e.g., "ID Proof")
4. Select a file to upload
5. Click "Upload Document"

**Expected Result**: 
- Upload succeeds without errors
- Document appears in the uploaded documents list
- No errors in console logs

### Step 3: Verify R2 Storage
1. Go to Cloudflare R2 Dashboard
2. Navigate to your bucket
3. Check that the uploaded file appears there

**Expected Result**: File is visible in your R2 bucket with the uploaded content

### Step 4: Test Signed URL Access
1. Click on "View/Download" link for the uploaded document
2. The document should open in your browser

**Expected Result**:
- Document opens successfully
- URL contains signature parameters
- No authentication prompts

### Step 5: Test URL Expiration
1. Wait 10+ minutes after generating a signed URL
2. Try to access the same signed URL again

**Expected Result**: 
- URL returns "Access Denied" or "Signature expired" error
- This confirms the security mechanism works

### Step 6: Test Migration (If You Have Existing Files)
```bash
python migrate_to_r2.py
```

**Expected Result**:
- Database schema updates successfully
- Existing files upload to R2
- Document records updated with new object keys

### Step 7: Verify No Local Files Being Created
1. Check your project directory
2. Confirm no new files appear in `uploads/` folder

**Expected Result**: 
- No new files in local uploads directory
- All files go directly to R2

## Common Issues and Solutions

### Issue: "Missing R2 configuration"
**Solution**: 
- Check that all 4 R2 environment variables are in `.env`
- Restart the application after updating `.env`

### Issue: "Access Denied" when uploading
**Solution**:
- Verify R2 credentials are correct
- Check API token permissions
- Ensure bucket name matches exactly

### Issue: "Bucket not found"
**Solution**:
- Verify bucket name in `.env` matches R2 dashboard
- Check you're using the correct Account ID

### Issue: Signed URLs don't work
**Solution**:
- Ensure system time is correct (signed URLs depend on timestamps)
- Check that R2 credentials are valid
- Verify the document exists in R2

## Next Steps After Testing

1. **Clean Up Local Files**: 
   - Backup your existing `uploads/` directory
   - Delete local files after confirming R2 migration

2. **Update Deployment**:
   - Add R2 environment variables to your deployment config
   - Ensure boto3 is in your production dependencies

3. **Monitor Usage**:
   - Check R2 dashboard for storage usage
   - Monitor API operation counts
   - Set up alerts if approaching free tier limits

4. **Optional Enhancements**:
   - Add file deletion functionality
   - Implement file size limits
   - Add virus scanning for uploaded files
   - Set up automatic cleanup of old documents

## Rollback Plan

If you need to rollback to local storage:

1. Restore local files from backup
2. Revert changes to `app/main.py` (restore local file upload logic)
3. Revert changes to `app/models/models.py` (restore `file_path` column)
4. Revert changes to `app/templates/case_detail.html` (restore local URLs)
5. Remove R2 environment variables from `.env`
6. Run database migration to revert schema changes

## Summary

The migration to Cloudflare R2 provides a robust, secure, and scalable solution for document storage. Files are now:

- **Persistent**: Survive redeployments and server changes
- **Secure**: Private storage with time-limited access
- **Scalable**: Cloud-based with generous free tier
- **Maintainable**: Standard S3-compatible tools and libraries

The implementation follows security best practices and provides a clear path for future enhancements.