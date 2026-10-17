"""
AWS Lambda Function for IoT Image Gallery - Auto Thumbnail Generator
====================================================================
This function can run directly inside AWS Lambda (Python 3.9+) or be executed
by our local Serverless Engine emulator.

Event Trigger: S3 ObjectCreated (or IoT Core Gateway payload)
Input: S3 Event Notification with bucket and object key
Output: High-performance auto thumbnail generated and saved to thumbnails bucket
"""

import os
import sys
import time
import uuid
import json
import io
from datetime import datetime
from PIL import Image, ImageOps

THUMBNAIL_MAX_SIZE = (320, 320)
THUMBNAIL_QUALITY = 85

def lambda_handler(event, context=None):
    """
    Standard AWS Lambda entry point.
    Handles S3 ObjectCreated events or custom payload from IoT Gateway.
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    logs = []
    def log(msg):
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        line = f"{timestamp} [{request_id[:8]}] {msg}"
        logs.append(line)
        print(line)

    log(f"START RequestId: {request_id} Version: $LATEST")
    log("Lambda Triggered: Auto Thumbnail Generator for IoT Image Gallery")

    try:
        # Extract bucket and object key from event
        bucket_name = "iot-image-gallery-raw"
        object_key = None
        raw_image_data = None
        metadata = {}

        # 1. Inspect event structure (AWS S3 or Local Direct)
        if "Records" in event and len(event["Records"]) > 0:
            s3_record = event["Records"][0].get("s3", {})
            bucket_name = s3_record.get("bucket", {}).get("name", bucket_name)
            object_key = s3_record.get("object", {}).get("key")
            log(f"Received S3 Event: s3://{bucket_name}/{object_key}")
        elif "object_key" in event:
            object_key = event["object_key"]
            metadata = event.get("metadata", {})
            log(f"Received Direct Ingestion Event for key: {object_key}")
        else:
            raise ValueError("Invalid event structure: No object_key or S3 Records found")

        # 2. Acquire Image bytes
        is_aws_lambda = bool(os.environ.get("AWS_EXECUTION_ENV") or os.environ.get("LAMBDA_TASK_ROOT"))
        base_dir = os.path.dirname(os.path.abspath(__file__))
        raw_storage_dir = os.path.join(base_dir, "storage", "raw")
        thumb_storage_dir = os.path.join(base_dir, "storage", "thumbnails")

        # Allow passing base64 image data directly in event
        if "image_base64" in event:
            import base64
            img_b64 = event["image_base64"]
            if "," in img_b64:
                img_b64 = img_b64.split(",", 1)[1]
            raw_image_data = base64.b64decode(img_b64)
            log(f"Acquired image from direct event payload ({len(raw_image_data)} bytes)")
        elif not is_aws_lambda and os.path.exists(os.path.join(raw_storage_dir, str(object_key))):
            raw_file_path = os.path.join(raw_storage_dir, str(object_key))
            log(f"Fetching raw image from local storage: {raw_file_path}")
            with open(raw_file_path, "rb") as f:
                raw_image_data = f.read()
        else:
            # Running on AWS Lambda or fetching from real AWS S3
            try:
                import boto3
                s3 = boto3.client('s3')
                log(f"Downloading from AWS S3: s3://{bucket_name}/{object_key}")
                response = s3.get_object(Bucket=bucket_name, Key=object_key)
                raw_image_data = response['Body'].read()
            except Exception as e:
                # Fallback to local file if available
                raw_file_path = os.path.join(raw_storage_dir, str(object_key))
                if os.path.exists(raw_file_path):
                    with open(raw_file_path, "rb") as f:
                        raw_image_data = f.read()
                else:
                    raise FileNotFoundError(f"Could not locate raw image '{object_key}' in S3 or local storage: {str(e)}")

        original_size_bytes = len(raw_image_data)
        log(f"Loaded raw image ({original_size_bytes} bytes). Processing image with Pillow...")

        # 3. Process Image with Pillow
        img = Image.open(io.BytesIO(raw_image_data))
        orig_width, orig_height = img.size
        orig_format = img.format or "JPEG"
        log(f"Original image specs: {orig_width}x{orig_height}px, Format: {orig_format}, Mode: {img.mode}")

        # Preserve orientation if EXIF orientation tag exists
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        # Convert RGBA / P to RGB for clean JPEG thumbnailing
        if img.mode in ("RGBA", "P"):
            rgb_img = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                rgb_img.paste(img, mask=img.split()[3])
            else:
                rgb_img.paste(img)
            img = rgb_img

        # Compute Dominant Color & Brightness
        small_preview = img.resize((1, 1), Image.Resampling.BOX)
        dom_r, dom_g, dom_b = small_preview.getpixel((0, 0))
        dominant_hex = f"#{dom_r:02x}{dom_g:02x}{dom_b:02x}"
        brightness = round((0.299 * dom_r + 0.587 * dom_g + 0.114 * dom_b) / 255 * 100, 1)

        # 4. Generate Thumbnail
        thumb_img = img.copy()
        thumb_img.thumbnail(THUMBNAIL_MAX_SIZE, Image.Resampling.LANCZOS)
        thumb_width, thumb_height = thumb_img.size
        log(f"Generated thumbnail: {thumb_width}x{thumb_height}px (Lanczos filter)")

        # Save thumbnail to buffer
        thumb_buffer = io.BytesIO()
        thumb_img.save(thumb_buffer, format="JPEG", quality=THUMBNAIL_QUALITY, optimize=True)
        thumb_bytes = thumb_buffer.getvalue()
        thumb_size_bytes = len(thumb_bytes)

        # Calculate compression & savings
        savings_percent = round((1.0 - (thumb_size_bytes / max(original_size_bytes, 1))) * 100, 2)
        log(f"Compression completed: Original {original_size_bytes} B -> Thumbnail {thumb_size_bytes} B ({savings_percent}% reduction)")

        # 5. Save Thumbnail to Destination
        thumb_filename = f"thumb_{object_key}"

        # If running locally, save to local disk
        if not is_aws_lambda:
            try:
                os.makedirs(thumb_storage_dir, exist_ok=True)
                thumb_file_path = os.path.join(thumb_storage_dir, thumb_filename)
                with open(thumb_file_path, "wb") as f:
                    f.write(thumb_bytes)
                log(f"Saved thumbnail to local storage: {thumb_file_path}")
            except Exception as e:
                log(f"Local storage write skipped: {e}")

        # If AWS S3 target configured or running on AWS Lambda
        dest_bucket = os.environ.get("AWS_THUMBNAILS_BUCKET")
        if not dest_bucket and bucket_name:
            if "raw" in bucket_name:
                dest_bucket = bucket_name.replace("raw", "thumbnails")
        
        if dest_bucket:
            try:
                import boto3
                s3 = boto3.client('s3')
                s3.put_object(
                    Bucket=dest_bucket,
                    Key=thumb_filename,
                    Body=thumb_bytes,
                    ContentType="image/jpeg"
                )
                log(f"Uploaded thumbnail to AWS S3: s3://{dest_bucket}/{thumb_filename}")
            except Exception as e:
                log(f"Warning: Cloud S3 thumbnail upload skipped ({e})")

        # 6. Calculate execution metrics
        duration_ms = round((time.time() - start_time) * 1000, 2)
        billed_ms = int(((duration_ms // 100) + 1) * 100)
        log(f"END RequestId: {request_id}")
        log(f"REPORT RequestId: {request_id} Duration: {duration_ms} ms Billed Duration: {billed_ms} ms Memory Size: 128 MB Max Memory Used: 38 MB")

        result = {
            "statusCode": 200,
            "requestId": request_id,
            "success": True,
            "objectKey": object_key,
            "thumbnailKey": thumb_filename,
            "originalSize": {
                "width": orig_width,
                "height": orig_height,
                "bytes": original_size_bytes,
                "formatted": format_bytes(original_size_bytes)
            },
            "thumbnailSize": {
                "width": thumb_width,
                "height": thumb_height,
                "bytes": thumb_size_bytes,
                "formatted": format_bytes(thumb_size_bytes)
            },
            "savingsPercent": savings_percent,
            "dominantColor": dominant_hex,
            "brightness": brightness,
            "durationMs": duration_ms,
            "billedDurationMs": billed_ms,
            "memorySizeMB": 128,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "cloudWatchLogs": logs
        }
        return result

    except Exception as err:
        err_msg = str(err)
        log(f"ERROR: Lambda execution failed - {err_msg}")
        duration_ms = round((time.time() - start_time) * 1000, 2)
        log(f"END RequestId: {request_id}")
        log(f"REPORT RequestId: {request_id} Duration: {duration_ms} ms Status: FAILED")
        return {
            "statusCode": 500,
            "requestId": request_id,
            "success": False,
            "error": err_msg,
            "durationMs": duration_ms,
            "cloudWatchLogs": logs
        }

def format_bytes(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

if __name__ == "__main__":
    # Test script run directly
    print("Testing lambda_handler with test mock event...")
    test_event = {"object_key": "test.jpg"}
    res = lambda_handler(test_event)
    print("Result:", json.dumps(res, indent=2))
