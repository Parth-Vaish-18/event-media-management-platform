import boto3
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "eu-north-1")

s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

def upload_file_to_s3(file_obj, original_filename: str, content_type: str) -> str:
    """Uploads a file to AWS S3 and returns the public URL."""
    try:
        # Create a unique filename to prevent overwriting
        unique_filename = f"{uuid.uuid4()}_{original_filename}"
        
        s3_client.upload_fileobj(
            file_obj,
            AWS_BUCKET_NAME,
            unique_filename,
            ExtraArgs={'ContentType': content_type}
        )
        # Construct the AWS public URL
        s3_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
        return s3_url
    except Exception as e:
        print(f"S3 Upload Error: {e}")
        return None