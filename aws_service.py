"""
AWS Cloud Integration Service for IoT Image Gallery
===================================================
Manages live AWS connections, S3 bucket storage, and Lambda invocations.
Supports dual-mode: Real AWS Cloud Mode & Local Simulation Mode.
"""

import os
import io
import time
import json
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError
from dotenv import load_dotenv, set_key

# Load environment variables from .env if present
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_FILE)

class AWSService:
    def __init__(self):
        self.reload_config()

    def reload_config(self):
        """Reload configuration from environment / .env file"""
        load_dotenv(ENV_FILE, override=True)
        self.region = os.environ.get("AWS_REGION", "us-east-1")
        self.access_key_id = os.environ.get("AWS_ACCESS_KEY_ID", "").strip()
        self.secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "").strip()
        self.session_token = os.environ.get("AWS_SESSION_TOKEN", "").strip()
        self.raw_bucket = os.environ.get("AWS_RAW_BUCKET", "").strip()
        self.thumbnails_bucket = os.environ.get("AWS_THUMBNAILS_BUCKET", "").strip()
        self.lambda_function_name = os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "").strip()
        
        # Explicit override or auto-detect if credentials exist
        aws_mode_val = os.environ.get("AWS_MODE", "").lower()
        if aws_mode_val in ("false", "0", "no", "local"):
            self.enabled = False
        else:
            self.enabled = bool(self.access_key_id and self.secret_access_key)
            
        self._cached_session = None

    def get_session(self, access_key=None, secret_key=None, region=None, session_token=None):
        ak = access_key or self.access_key_id
        sk = secret_key or self.secret_access_key
        st = session_token if session_token is not None else self.session_token
        reg = region or self.region
        
        if ak and sk:
            return boto3.Session(
                aws_access_key_id=ak,
                aws_secret_access_key=sk,
                aws_session_token=st if st else None,
                region_name=reg
            )
        return boto3.Session(region_name=reg)

    def test_connection(self, access_key=None, secret_key=None, region=None, raw_bucket=None, thumb_bucket=None, lambda_fn=None, session_token=None):
        """Test AWS credentials and resource accessibility"""
        start = time.time()
        ak = access_key or self.access_key_id
        sk = secret_key or self.secret_access_key
        st = session_token if session_token is not None else self.session_token
        reg = region or self.region
        rb = raw_bucket or self.raw_bucket
        tb = thumb_bucket or self.thumbnails_bucket
        lf = lambda_fn or self.lambda_function_name

        if not ak or not sk:
            return {
                "success": False,
                "connected": False,
                "error": "AWS credentials (Access Key ID and Secret Access Key) are not provided.",
                "latencyMs": 0
            }

        try:
            session = self.get_session(ak, sk, reg, st)
            sts = session.client('sts')
            identity = sts.get_caller_identity()
            latency = round((time.time() - start) * 1000, 1)

            results = {
                "success": True,
                "connected": True,
                "accountId": identity.get("Account"),
                "arn": identity.get("Arn"),
                "userId": identity.get("UserId"),
                "region": reg,
                "latencyMs": latency,
                "rawBucket": {"name": rb, "accessible": False},
                "thumbnailsBucket": {"name": tb, "accessible": False},
                "lambdaFunction": {"name": lf, "accessible": False}
            }

            s3 = session.client('s3')
            if rb:
                try:
                    s3.head_bucket(Bucket=rb)
                    results["rawBucket"]["accessible"] = True
                except Exception as e:
                    results["rawBucket"]["error"] = str(e)

            if tb:
                try:
                    s3.head_bucket(Bucket=tb)
                    results["thumbnailsBucket"]["accessible"] = True
                except Exception as e:
                    results["thumbnailsBucket"]["error"] = str(e)

            if lf:
                try:
                    lam = session.client('lambda')
                    fn_info = lam.get_function(FunctionName=lf)
                    results["lambdaFunction"]["accessible"] = True
                    results["lambdaFunction"]["arn"] = fn_info.get("Configuration", {}).get("FunctionArn")
                except Exception as e:
                    results["lambdaFunction"]["error"] = str(e)

            return results
        except Exception as err:
            latency = round((time.time() - start) * 1000, 1)
            return {
                "success": False,
                "connected": False,
                "error": str(err),
                "latencyMs": latency
            }

    def get_status(self):
        """Current operational status of AWS integration"""
        if not self.enabled:
            return {
                "mode": "LOCAL_SIMULATION",
                "connected": False,
                "region": self.region,
                "rawBucket": self.raw_bucket,
                "thumbnailsBucket": self.thumbnails_bucket,
                "lambdaFunction": self.lambda_function_name,
                "message": "Local Simulation Mode (No AWS credentials configured)"
            }

        test_res = self.test_connection()
        if test_res.get("connected"):
            return {
                "mode": "AWS_CLOUD" if (self.raw_bucket and self.thumbnails_bucket) else "AWS_CREDENTIALS_VALID",
                "connected": True,
                "accountId": test_res.get("accountId"),
                "arn": test_res.get("arn"),
                "region": self.region,
                "rawBucket": self.raw_bucket,
                "thumbnailsBucket": self.thumbnails_bucket,
                "lambdaFunction": self.lambda_function_name,
                "rawBucketAccessible": test_res.get("rawBucket", {}).get("accessible", False),
                "thumbnailsBucketAccessible": test_res.get("thumbnailsBucket", {}).get("accessible", False),
                "lambdaAccessible": test_res.get("lambdaFunction", {}).get("accessible", False),
                "latencyMs": test_res.get("latencyMs"),
                "message": f"Connected to AWS Cloud (Account: {test_res.get('accountId')})"
            }
        else:
            return {
                "mode": "LOCAL_SIMULATION",
                "connected": False,
                "region": self.region,
                "rawBucket": self.raw_bucket,
                "thumbnailsBucket": self.thumbnails_bucket,
                "lambdaFunction": self.lambda_function_name,
                "error": test_res.get("error"),
                "message": f"AWS connection failed: {test_res.get('error')}"
            }

    def upload_raw_image(self, filename, raw_bytes):
        """Upload raw captured image to AWS S3 Raw Bucket"""
        if not self.enabled or not self.raw_bucket:
            return None

        try:
            session = self.get_session()
            s3 = session.client('s3')
            start = time.time()
            s3.put_object(
                Bucket=self.raw_bucket,
                Key=filename,
                Body=raw_bytes,
                ContentType="image/jpeg",
                Metadata={
                    "uploadedBy": "iot-image-gallery",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            duration_ms = round((time.time() - start) * 1000, 2)
            return {
                "success": True,
                "bucket": self.raw_bucket,
                "key": filename,
                "durationMs": duration_ms
            }
        except Exception as e:
            print(f"[AWSService] S3 Raw upload failed: {e}")
            return {"success": False, "error": str(e)}

    def invoke_lambda(self, event_payload):
        """Invoke remote AWS Lambda function for serverless auto-thumbnailing"""
        if not self.enabled or not self.lambda_function_name:
            return None

        try:
            session = self.get_session()
            lam = session.client('lambda')
            start = time.time()
            response = lam.invoke(
                FunctionName=self.lambda_function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(event_payload)
            )
            duration_ms = round((time.time() - start) * 1000, 2)
            payload_data = response['Payload'].read()
            result = json.loads(payload_data.decode('utf-8'))
            result["awsLambdaInvoked"] = True
            result["networkDurationMs"] = duration_ms
            return result
        except Exception as e:
            print(f"[AWSService] AWS Lambda invocation failed: {e}")
            return None

    def get_presigned_url(self, bucket, key, expires_in=86400):
        """Generate presigned S3 URL for secure viewing from browser"""
        if not self.enabled or not bucket or not key:
            return None
        try:
            session = self.get_session()
            s3 = session.client('s3')
            return s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expires_in
            )
        except Exception as e:
            print(f"[AWSService] Presigned URL failed for s3://{bucket}/{key}: {e}")
            return None

    def save_configuration(self, access_key, secret_key, region, raw_bucket, thumb_bucket, lambda_fn, enabled=True, session_token=None):
        lines = [
            "# IoT Image Gallery - AWS Cloud Configuration\n",
            f"AWS_ACCESS_KEY_ID={access_key or ''}\n",
            f"AWS_SECRET_ACCESS_KEY={secret_key or ''}\n",
            f"AWS_SESSION_TOKEN={session_token or ''}\n",
            f"AWS_REGION={region or 'us-east-1'}\n",
            f"AWS_RAW_BUCKET={raw_bucket or ''}\n",
            f"AWS_THUMBNAILS_BUCKET={thumb_bucket or ''}\n",
            f"AWS_LAMBDA_FUNCTION_NAME={lambda_fn or 'IoTImageGalleryThumbnailer'}\n",
            f"AWS_MODE={'true' if enabled else 'false'}\n"
        ]
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)

        self.reload_config()
        return self.get_status()

# Singleton instance
aws_service = AWSService()
