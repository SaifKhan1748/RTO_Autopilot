"""
R2 Storage Service - Handles file uploads to Cloudflare R2 and signed URL generation.
This service provides S3-compatible storage functionality for document management.
"""

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv
from typing import Optional, Tuple
import uuid

# Load environment variables
load_dotenv()


class R2StorageService:
    """Service for managing Cloudflare R2 storage operations."""
    
    def __init__(self):
        """Initialize the R2 storage service with credentials from environment variables."""
        self.account_id = os.getenv("R2_ACCOUNT_ID")
        self.access_key = os.getenv("R2_ACCESS_KEY_ID")
        self.secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
        self.bucket_name = os.getenv("R2_BUCKET_NAME")
        
        if not all([self.account_id, self.access_key, self.secret_key, self.bucket_name]):
            raise ValueError(
                "Missing R2 configuration. Please set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, "
                "R2_SECRET_ACCESS_KEY, and R2_BUCKET_NAME in your .env file. "
                "See R2_SETUP_GUIDE.md for detailed setup instructions."
            )
        
        # Initialize S3 client with R2 endpoint
        self.s3_client = boto3.client(
            's3',
            endpoint_url=f'https://{self.account_id}.r2.cloudflarestorage.com',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(signature_version='s3v4'),
            region_name='auto'
        )
    
    def upload_file(
        self, 
        file_content: bytes, 
        file_name: str, 
        content_type: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Upload a file to R2 storage.
        
        Args:
            file_content: The file content as bytes
            file_name: The original file name
            content_type: The MIME type of the file (optional)
            
        Returns:
            Tuple of (object_key, file_url) where object_key is the R2 object key
            and file_url is the public URL (though bucket should be private)
        """
        # Generate a unique object key to prevent conflicts
        file_extension = os.path.splitext(file_name)[1]
        object_key = f"{uuid.uuid4()}{file_extension}"
        
        try:
            # Upload the file to R2
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=file_content,
                **extra_args
            )
            
            # Construct the file URL (for reference, though bucket should be private)
            file_url = f"https://{self.account_id}.r2.cloudflarestorage.com/{self.bucket_name}/{object_key}"
            
            return object_key, file_url
            
        except ClientError as e:
            raise Exception(f"Error uploading file to R2: {str(e)}")
    
    def generate_signed_url(
        self, 
        object_key: str, 
        expiration_seconds: int = 600
    ) -> str:
        """
        Generate a signed URL for temporary access to a file in R2.
        
        Args:
            object_key: The R2 object key
            expiration_seconds: URL validity duration in seconds (default: 600 = 10 minutes)
            
        Returns:
            A signed URL that provides temporary access to the file
        """
        try:
            signed_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=expiration_seconds
            )
            return signed_url
            
        except ClientError as e:
            raise Exception(f"Error generating signed URL: {str(e)}")
    
    def delete_file(self, object_key: str) -> bool:
        """
        Delete a file from R2 storage.
        
        Args:
            object_key: The R2 object key to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return True
            
        except ClientError as e:
            raise Exception(f"Error deleting file from R2: {str(e)}")
    
    def file_exists(self, object_key: str) -> bool:
        """
        Check if a file exists in R2 storage.
        
        Args:
            object_key: The R2 object key to check
            
        Returns:
            True if the file exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise Exception(f"Error checking file existence: {str(e)}")


# Global instance for reuse
_r2_service_instance = None


def get_r2_service() -> R2StorageService:
    """
    Get or create the R2 storage service instance.
    This follows the singleton pattern for efficient resource usage.
    
    Returns:
        The R2StorageService instance
    """
    global _r2_service_instance
    if _r2_service_instance is None:
        _r2_service_instance = R2StorageService()
    return _r2_service_instance