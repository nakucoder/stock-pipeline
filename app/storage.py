import boto3
import json
from datetime import datetime
from app.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME, AWS_REGION

def save_to_s3(data: dict):
    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        timestamp = datetime.utcnow().strftime("%Y/%m/%d/%H-%M-%S")
        filename = f"stock-prices/{timestamp}.json"
        s3_client.put_object(
            Bucket=AWS_BUCKET_NAME,
            Key=filename,
            Body=json.dumps(data, indent=2),
            ContentType="application/json"
        )
        print(f"Successfully saved to S3: {filename}")
        return filename
    except Exception as e:
        print(f"Error saving to S3: {e}")
        return None
