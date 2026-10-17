"""
IoT Image Gallery - Automated AWS Cloud Setup & Provisioner
============================================================
This script automatically provisions and connects your project to real AWS Cloud:
1. Validates AWS IAM Credentials via STS
2. Creates S3 Raw and Thumbnails Buckets with CORS configured
3. Creates IAM Execution Role for Lambda with S3 permissions
4. Packages lambda_function.py with Linux Pillow wheel into a self-contained zip
5. Deploys/Updates AWS Lambda Function (Python 3.11, x86_64)
6. Configures S3 Event Notification (s3:ObjectCreated:* -> Lambda Trigger)
7. Writes credentials and bucket names to .env automatically
"""

import os
import sys
import time
import json
import zipfile
import tempfile
import subprocess
import shutil
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv, set_key

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_FILE)

import argparse

def print_banner():
    print("=" * 65)
    print("      IoT Image Gallery - AWS Cloud Auto-Provisioner       ")
    print("=" * 65)

def get_credentials(cli_ak=None, cli_sk=None, cli_region=None, cli_token=None, non_interactive=False):
    default_ak = cli_ak or os.environ.get("AWS_ACCESS_KEY_ID", "")
    default_sk = cli_sk or os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    default_region = cli_region or os.environ.get("AWS_REGION", "us-east-1")
    default_token = cli_token or os.environ.get("AWS_SESSION_TOKEN", "")

    if non_interactive or (cli_ak and cli_sk):
        if not default_ak or not default_sk:
            print("Error: Both AWS Access Key ID and Secret Access Key must be specified.")
            sys.exit(1)
        return default_ak, default_sk, default_region, default_token

    print("\n--- Step 1: AWS Credentials ---")
    if default_ak and default_sk:
        masked = default_ak[:4] + "..." + default_ak[-4:] if len(default_ak) >= 8 else "****"
        print(f"Detected existing credentials (Key: {masked})")
        use_existing = input("Use these credentials? [Y/n]: ").strip().lower()
        if use_existing not in ('n', 'no'):
            return default_ak, default_sk, default_region, default_token

    ak = input(f"Enter AWS Access Key ID [{default_ak}]: ").strip() or default_ak
    sk = input("Enter AWS Secret Access Key: ").strip() or default_sk

    # Detect AWS Academy / Learner Lab temporary credentials
    token = default_token
    if ak.startswith("ASIA"):
        print("\n* Temporary STS credentials detected (AWS Academy / Learner Lab).")
        token = input("Enter AWS Session Token: ").strip() or default_token
    else:
        opt_token = input("Using AWS Academy? (Needs Session Token) [y/N]: ").strip().lower()
        if opt_token in ('y', 'yes'):
            token = input("Enter AWS Session Token: ").strip()

    region = input(f"Enter AWS Region [{default_region}]: ").strip() or default_region

    if not ak or not sk:
        print("Error: Both AWS Access Key ID and Secret Access Key are required.")
        sys.exit(1)

    return ak, sk, region, token

def create_s3_bucket(s3_client, bucket_name, region):
    print(f"Creating S3 Bucket: {bucket_name} in {region}...")
    try:
        if region == "us-east-1":
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        print(f"  [OK] Bucket created: s3://{bucket_name}")
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            print(f"  [OK] Bucket already exists: s3://{bucket_name}")
        else:
            raise e

    # Apply CORS Configuration so web dashboard can fetch/upload
    cors_config = {
        'CORSRules': [
            {
                'AllowedHeaders': ['*'],
                'AllowedMethods': ['GET', 'PUT', 'POST', 'HEAD'],
                'AllowedOrigins': ['*'],
                'MaxAgeSeconds': 3600
            }
        ]
    }
    try:
        s3_client.put_bucket_cors(Bucket=bucket_name, CORSConfiguration=cors_config)
        print(f"  [OK] Configured CORS for s3://{bucket_name}")
    except Exception as e:
        print(f"  [Note] CORS setup skipped ({e})")

def create_or_get_lambda_role(iam_client, role_name, raw_bucket, thumb_bucket):
    print(f"\n--- Setting up IAM Role: {role_name} ---")

    # 1. First check if AWS Academy pre-configured "LabRole" exists
    try:
        lab_resp = iam_client.get_role(RoleName="LabRole")
        lab_arn = lab_resp['Role']['Arn']
        print(f"  [AWS Academy Detected] Using pre-configured LabRole: {lab_arn}")
        return lab_arn
    except Exception:
        pass

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }

    try:
        resp = iam_client.get_role(RoleName=role_name)
        role_arn = resp['Role']['Arn']
        print(f"  [OK] Existing IAM Role found: {role_arn}")
        return role_arn
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "NoSuchEntity":
            print(f"  Creating new IAM Role: {role_name}...")
            try:
                resp = iam_client.create_role(
                    RoleName=role_name,
                    AssumeRolePolicyDocument=json.dumps(trust_policy),
                    Description="Execution role for IoT Image Gallery auto-thumbnailer Lambda"
                )
                role_arn = resp['Role']['Arn']
                print(f"  [OK] Created IAM Role: {role_arn}")
            except ClientError as err:
                if "is not authorized to perform: iam:CreateRole" in str(err) or err.response.get("Error", {}).get("Code") == "AccessDenied":
                    print("  [AWS Academy] Role creation restricted. Trying fallback to LabRole...")
                    try:
                        lab_resp = iam_client.get_role(RoleName="LabRole")
                        return lab_resp['Role']['Arn']
                    except Exception:
                        pass
                raise err
        else:
            raise e

    # Attach basic execution policy if permissions allow
    try:
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        )
    except Exception:
        pass

    # Attach inline policy for S3 Read/Write if permissions allow
    s3_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:ListBucket"],
                "Resource": [f"arn:aws:s3:::{raw_bucket}", f"arn:aws:s3:::{raw_bucket}/*"]
            },
            {
                "Effect": "Allow",
                "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
                "Resource": [f"arn:aws:s3:::{thumb_bucket}", f"arn:aws:s3:::{thumb_bucket}/*"]
            }
        ]
    }
    try:
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName="IoTGalleryS3Access",
            PolicyDocument=json.dumps(s3_policy)
        )
        print("  [OK] Attached S3 read/write permissions to Lambda role")
    except Exception:
        pass

    return role_arn

def build_lambda_package():
    """Build standalone deployment zip with lambda_function.py and Linux Pillow"""
    print("\n--- Packaging AWS Lambda Function with Pillow ---")
    staging_dir = tempfile.mkdtemp(prefix="iot_lambda_build_")
    wheel_dir = tempfile.mkdtemp(prefix="iot_whl_")
    zip_path = os.path.join(tempfile.gettempdir(), "iot_image_gallery_lambda.zip")

    try:
        print("  Downloading Linux x86_64 Pillow wheel from PyPI...")
        cmd = [
            sys.executable, "-m", "pip", "download",
            "--platform", "manylinux2014_x86_64",
            "--only-binary=:all:",
            "--python-version", "3.11",
            "--implementation", "cp",
            "--dest", wheel_dir,
            "Pillow"
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"  Warning: pip wheel download returned code {result.returncode}. Fallback to local files if any.")

        # Find downloaded wheel
        wheels = [f for f in os.listdir(wheel_dir) if f.endswith(".whl")]
        if wheels:
            wheel_file = os.path.join(wheel_dir, wheels[0])
            print(f"  Extracting Pillow binary: {wheels[0]}...")
            with zipfile.ZipFile(wheel_file, 'r') as zf:
                zf.extractall(staging_dir)

        # Copy lambda_function.py into staging
        lambda_src = os.path.join(BASE_DIR, "lambda_function.py")
        shutil.copy2(lambda_src, os.path.join(staging_dir, "lambda_function.py"))

        # Create the zip
        print(f"  Creating Lambda deployment zip at: {zip_path}")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(staging_dir):
                for f in files:
                    file_path = os.path.join(root, f)
                    arcname = os.path.relpath(file_path, staging_dir)
                    zf.write(file_path, arcname)

        size_mb = round(os.path.getsize(zip_path) / (1024 * 1024), 2)
        print(f"  [OK] Package ready! Size: {size_mb} MB")
        return zip_path
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)
        shutil.rmtree(wheel_dir, ignore_errors=True)

def deploy_lambda_function(lambda_client, function_name, role_arn, thumb_bucket, zip_path):
    print(f"\n--- Deploying AWS Lambda Function: {function_name} ---")
    with open(zip_path, 'rb') as f:
        zip_bytes = f.read()

    env_vars = {
        'Variables': {
            'AWS_THUMBNAILS_BUCKET': thumb_bucket
        }
    }

    try:
        resp = lambda_client.get_function(FunctionName=function_name)
        print(f"  Function {function_name} already exists. Updating code and configuration...")
        lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_bytes
        )
        # Wait a moment for code update
        time.sleep(3)
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment=env_vars,
            Timeout=15,
            MemorySize=256
        )
        fn_arn = resp['Configuration']['FunctionArn']
        print(f"  [OK] Updated Lambda function: {fn_arn}")
        return fn_arn
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
            print(f"  Creating new Lambda function {function_name}...")
            # Wait for IAM role propagation
            print("  Waiting 10 seconds for IAM role propagation in AWS...")
            time.sleep(10)

            for attempt in range(5):
                try:
                    resp = lambda_client.create_function(
                        FunctionName=function_name,
                        Runtime='python3.11',
                        Role=role_arn,
                        Handler='lambda_function.lambda_handler',
                        Code={'ZipFile': zip_bytes},
                        Description='Auto-Thumbnail generator for IoT Image Gallery',
                        Timeout=15,
                        MemorySize=256,
                        Architectures=['x86_64'],
                        Environment=env_vars
                    )
                    fn_arn = resp['FunctionArn']
                    print(f"  [OK] Created Lambda function: {fn_arn}")
                    return fn_arn
                except ClientError as err:
                    if "The role defined for the function cannot be assumed by Lambda" in str(err) and attempt < 4:
                        print("  IAM role not ready yet, retrying in 5 seconds...")
                        time.sleep(5)
                    else:
                        raise err
        else:
            raise e

def setup_s3_trigger(lambda_client, s3_client, raw_bucket, lambda_arn):
    print(f"\n--- Configuring S3 Event Notification Trigger ---")
    # Grant S3 permission to invoke Lambda
    try:
        lambda_client.add_permission(
            FunctionName=lambda_arn,
            StatementId=f"S3Invoke-{raw_bucket[:20]}",
            Action="lambda:InvokeFunction",
            Principal="s3.amazonaws.com",
            SourceArn=f"arn:aws:s3:::{raw_bucket}"
        )
        print("  [OK] Added Lambda invoke permission for S3")
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "ResourceConflictException":
            print("  [OK] Lambda invoke permission already present")
        else:
            print(f"  Note: {e}")

    # Set S3 bucket notification configuration
    print("  Waiting 3 seconds for Lambda permission propagation...")
    time.sleep(3)

    notification_config = {
        'LambdaFunctionConfigurations': [
            {
                'LambdaFunctionArn': lambda_arn,
                'Events': ['s3:ObjectCreated:*'],
                'Filter': {
                    'Key': {
                        'FilterRules': [
                            {'Name': 'suffix', 'Value': '.jpg'}
                        ]
                    }
                }
            }
        ]
    }
    for attempt in range(3):
        try:
            s3_client.put_bucket_notification_configuration(
                Bucket=raw_bucket,
                NotificationConfiguration=notification_config
            )
            print(f"  [OK] S3 Bucket Notification configured: s3://{raw_bucket} -> Lambda")
            break
        except Exception as e:
            if attempt < 2:
                print(f"  Notification setup retry in 3 seconds ({e})...")
                time.sleep(3)
            else:
                print(f"  Warning: Could not set bucket notification ({e}). Direct Lambda invocation will still work.")

def save_env_file(ak, sk, region, raw_bucket, thumb_bucket, lambda_name, token=None):
    print("\n--- Saving Configuration to .env ---")
    lines = [
        "# IoT Image Gallery - AWS Cloud Configuration\n",
        f"AWS_ACCESS_KEY_ID={ak}\n",
        f"AWS_SECRET_ACCESS_KEY={sk}\n",
        f"AWS_SESSION_TOKEN={token or ''}\n",
        f"AWS_REGION={region}\n",
        f"AWS_RAW_BUCKET={raw_bucket}\n",
        f"AWS_THUMBNAILS_BUCKET={thumb_bucket}\n",
        f"AWS_LAMBDA_FUNCTION_NAME={lambda_name}\n",
        "AWS_MODE=true\n"
    ]
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"  [OK] Updated {ENV_FILE} with all cloud parameters.")

def main():
    parser = argparse.ArgumentParser(description="IoT Image Gallery - Automated AWS Cloud Setup")
    parser.add_argument("--access-key", help="AWS Access Key ID")
    parser.add_argument("--secret-key", help="AWS Secret Access Key")
    parser.add_argument("--session-token", help="AWS Session Token (for AWS Academy / temporary credentials)")
    parser.add_argument("--region", default="us-east-1", help="AWS Region (default: us-east-1)")
    parser.add_argument("--raw-bucket", help="Custom name for raw images S3 bucket")
    parser.add_argument("--thumb-bucket", help="Custom name for thumbnails S3 bucket")
    parser.add_argument("--non-interactive", action="store_true", help="Run without prompts (uses CLI args or .env)")

    args = parser.parse_args()

    print_banner()
    ak, sk, region, token = get_credentials(
        cli_ak=args.access_key,
        cli_sk=args.secret_key,
        cli_region=args.region,
        cli_token=args.session_token,
        non_interactive=args.non_interactive
    )

    print("\nValidating AWS credentials with AWS STS...")
    session = boto3.Session(
        aws_access_key_id=ak,
        aws_secret_access_key=sk,
        aws_session_token=token if token else None,
        region_name=region
    )
    sts = session.client('sts')
    try:
        identity = sts.get_caller_identity()
        account_id = identity.get("Account")
        print(f"  [SUCCESS] Authenticated to AWS!")
        print(f"  Account ID: {account_id}")
        print(f"  Caller ARN: {identity.get('Arn')}")
        print(f"  Region:     {region}")
    except Exception as e:
        print(f"\n[ERROR] Authentication failed: {e}")
        print("Please verify your AWS Access Key ID, Secret Access Key, and Session Token.")
        sys.exit(1)

    s3_client = session.client('s3')
    iam_client = session.client('iam')
    lambda_client = session.client('lambda')

    # Bucket names (globally unique by using account ID and region)
    raw_bucket = args.raw_bucket or f"iot-gallery-raw-{account_id}-{region}"
    thumb_bucket = args.thumb_bucket or f"iot-gallery-thumbnails-{account_id}-{region}"
    lambda_name = "IoTImageGalleryThumbnailer"
    role_name = "IoTImageGalleryLambdaRole"

    print("\n--- Step 2: S3 Buckets Setup ---")
    create_s3_bucket(s3_client, raw_bucket, region)
    create_s3_bucket(s3_client, thumb_bucket, region)

    print("\n--- Step 3: IAM Role Setup ---")
    role_arn = create_or_get_lambda_role(iam_client, role_name, raw_bucket, thumb_bucket)

    print("\n--- Step 4: Package & Deploy Lambda Function ---")
    zip_path = build_lambda_package()
    lambda_arn = deploy_lambda_function(lambda_client, lambda_name, role_arn, thumb_bucket, zip_path)

    # Clean up zip
    try:
        if os.path.exists(zip_path):
            os.remove(zip_path)
    except Exception:
        pass

    print("\n--- Step 5: Event Notifications ---")
    setup_s3_trigger(lambda_client, s3_client, raw_bucket, lambda_arn)

    print("\n--- Step 6: Persist Configuration ---")
    save_env_file(ak, sk, region, raw_bucket, thumb_bucket, lambda_name, token=token)

    print("\n" + "=" * 65)
    print("      [SUCCESS] AWS CLOUD PROVISIONING & CONNECTION COMPLETE!      ")
    print("=" * 65)
    print(f"  Raw S3 Bucket:        s3://{raw_bucket}")
    print(f"  Thumbnails S3 Bucket: s3://{thumb_bucket}")
    print(f"  Lambda Function:      {lambda_name}")
    print(f"  Lambda ARN:           {lambda_arn}")
    print(f"  Status:               CONNECTED (AWS Cloud Mode Active)")
    print("=" * 65)
    print("\nYou can now start the application with:")
    print("    python app.py")
    print("or double-click run.bat.\n")

if __name__ == "__main__":
    main()
