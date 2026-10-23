"""
SurplusBite — Presigned URL Generator Lambda.

CLOUD ENGINEER NOTES:
1. ENVIRONMENT VARIABLES:
   - SOURCE_BUCKET: The name of the S3 bucket where original photos are uploaded.
2. IAM EXECUTION ROLE:
   - s3:PutObject on the source bucket.
3. TRIGGER:
   - Lambda Function URL (with CORS enabled for your frontend domain).
"""

import boto3
import os
import json
import uuid
import logging
from botocore.config import Config

s3_client = boto3.client(
    "s3",
    region_name=os.environ.get("AWS_REGION", "eu-west-1"),
    config=Config(
        signature_version="s3v4",
        s3={"addressing_style": "virtual"},
    ),
)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    source_bucket = os.environ.get("SOURCE_BUCKET")
    if not source_bucket:
        return {"statusCode": 500, "body": json.dumps({"error": "SOURCE_BUCKET not set"})}

    try:
        # Extract original filename from query string if provided
        query_params = event.get("queryStringParameters") or {}
        original_name = query_params.get("filename", "upload.jpg")
        
        # Clean the filename (prevent directory traversal)
        original_name = os.path.basename(original_name)
        
        # Generate a unique key to prevent overwriting files with the same name
        file_ext = os.path.splitext(original_name)[1].lower()
        if file_ext not in [".jpg", ".jpeg", ".png"]:
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid file type"})}

        unique_key = f"uploads/{uuid.uuid4().hex}{file_ext}"

        # Generate presigned PUT URL (valid for 5 minutes)
        presigned_url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": source_bucket,
                "Key": unique_key,
                "ContentType": f"image/{'jpeg' if file_ext in ['.jpg', '.jpeg'] else 'png'}"
            },
            ExpiresIn=300
        )

        # Return the URL and the key to the frontend
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "upload_url": presigned_url,
                "key": unique_key
            })
        }
    except Exception:
        logger.exception("Failed to generate a presigned upload URL")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Could not create upload URL"})
        }