from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("S3_BUCKET")


def _get_s3_client():
    import boto3
    return boto3.client("s3", region_name=os.environ.get("AWS_REGION", "ap-northeast-1"))


def upload_export(key: str, data: bytes, content_type: str) -> str | None:
    if not S3_BUCKET:
        return None
    try:
        client = _get_s3_client()
        client.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        logger.info("Uploaded %s to s3://%s/%s", content_type, S3_BUCKET, key)
        return f"s3://{S3_BUCKET}/{key}"
    except Exception:
        logger.exception("Failed to upload to S3")
        return None
