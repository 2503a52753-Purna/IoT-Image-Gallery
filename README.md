# IoT Image Gallery

> **Cloud Computing Project**  
> *"Press a button to capture an event; an LED confirms upload; image auto thumbnail via Lambda."*

---

## 🌟 Overview & Architecture

The **IoT Image Gallery** is an end-to-end cloud-native IoT solution demonstrating event-driven serverless architecture. When an event occurs at the edge, a camera sensor captures an image, transmits it to cloud storage, confirms the upload to the physical device via an LED indicator, and automatically invokes an **AWS Lambda function** to generate bandwidth-optimized thumbnails.

```mermaid
flowchart LR
    A[IoT Camera Node\nButton Trigger] -->|HTTP / MQTT| B[Cloud Ingestion\nGateway]
    B -->|Upload Raw Image| C[(S3 Raw Bucket\ns3://raw-images)]
    C -.->|Upload Confirmed| D[Hardware LED\nGPIO 27 Solid GREEN]
    C -->|S3:ObjectCreated Event| E[AWS Lambda\nAuto-Thumbnailer]
    E -->|Write Thumbnail| F[(S3 Thumbnails\ns3://thumbnails)]
    F -->|Real-Time SSE Sync| G[Live Image Gallery\n& Cloud Metrics]
```

---

## 🚀 Key Features

### 1. "Press a Button to Capture an Event"
- **Tactile Button & Key Trigger:** Large interactive 3D push button (GPIO 14) with mechanical press animation, shutter audio FX, and keyboard shortcut (`Spacebar`).
- **Flexible Camera Sources:**
  - **Dynamic Simulated Scenes:** 4 interactive IoT surveillance & environmental scenes with animated objects, telemetry watermarks, and bounding boxes.
  - **Live Webcam Mode:** Direct hardware access to your laptop/USB camera for real live testing.
  - **File Upload Mode:** Test with any custom image file from your computer.

### 2. "An LED Confirms Upload"
- **Hardware State Machine:** Synchronized virtual and physical GPIO 27 status LED:
  - `IDLE / STANDBY`: Soft ambient ready indicator.
  - `CAPTURING`: Rapid flashing amber shutter indicator.
  - `UPLOADING`: Smooth breathing cyan data transmission indicator.
  - `UPLOAD CONFIRMED`: **Solid bright emerald GREEN** with pulse bloom animation upon cloud gateway verification.
  - `PROCESSING`: Shimmering violet during Lambda execution.
- **Audio Feedback:** Real-time Web Audio API synthesized confirmation chime upon cloud acknowledgment.

### 3. "Image Auto Thumbnail via Lambda"
- **Serverless Event-Driven Invocation:** When raw image is saved to the Raw Bucket, the Lambda function is triggered automatically.
- **High-Efficiency Thumbnailing:** Lanczos resampling via Pillow preserves aspect ratio, reducing file size by **90% - 97%** with typical execution times under **40ms**.
- **AWS CloudWatch Execution Logs:** Full logs with Request ID, duration, billed duration, and memory utilization for academic and cloud grading.
- **Side-by-Side Comparison:** Interactive modal comparing the raw S3 image vs the Lambda-generated thumbnail.

---

## 🛠️ Technology Stack

- **Backend:** Python 3 (Flask, Pillow, Threading, Server-Sent Events)
- **Serverless Runtime:** AWS Lambda (Python runtime) / Local Serverless Engine
- **Storage:** Amazon S3 emulation (`storage/raw/` and `storage/thumbnails/`)
- **Frontend:** Vanilla HTML5, Modern CSS (Glassmorphism, CSS Grid, Custom Design Tokens), Vanilla JavaScript (SSE, Web Audio API, Canvas rendering)
- **Deployment:** AWS SAM (`aws_deploy/template.yaml`)

---

## ⚡ Quick Start

### 1. Launch the Application
Double-click `run.bat` or run:

```bash
python app.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

### 2. Run Automated Unit Tests
To verify Lambda triggers and thumbnail compression independently:

```bash
python tests/test_lambda.py
```

---

## 🧪 Testing Guide

1. **Test Button Capture:**
   - Click the big red button on the camera panel (or press the **Spacebar**).
   - Observe the camera shutter flash and audio click.
   - Watch the LED switch from **Amber (Capturing)** &rarr; **Cyan (Uploading)** &rarr; **Bright Green (Upload Confirmed)**!
2. **Observe Serverless Pipeline:**
   - Watch the cloud pipeline visualizer light up node-by-node.
   - See the real-time Lambda logs appear in the Cloud Activity Console.
3. **Inspect the Generated Thumbnail:**
   - The thumbnail immediately appears in the **Captured Events Gallery**.
   - Click on the thumbnail card to open the **Original vs Thumbnail Comparison Modal**.
   - Check the compression percentage (e.g. *-94.9%*) and Lambda latency (e.g. *28 ms*).
4. **Inspect CloudWatch Logs:**
   - Click the terminal icon on any gallery card to view AWS CloudWatch execution logs.
5. **Test Webcam:**
   - Click "Webcam Live" in the camera bar to capture your real camera feed.
6. **Test Concurrency:**
   - Click "Burst Test (3x)" in the top navigation bar to trigger 3 rapid captures.

---

## ☁️ Linking to Your AWS Cloud Account

The application supports dual-mode operation: **Local Simulation Mode** (default when no AWS credentials are provided) and **Live AWS Cloud Mode** (real Amazon S3 storage and AWS Lambda execution).

You can connect your AWS account using any of the following 3 easy methods:

### Method 1: 1-Click Automated Provisioner (Recommended)
This script validates your credentials with AWS STS, auto-creates unique S3 Raw & Thumbnails buckets with CORS, provisions the IAM execution role, packages `lambda_function.py` with Pillow, deploys the AWS Lambda function, attaches the S3 event trigger, and writes `.env` automatically:

```bash
python setup_aws.py
```

Or pass arguments directly:
```bash
python setup_aws.py --access-key <YOUR_ACCESS_KEY> --secret-key <YOUR_SECRET_KEY> --region us-east-1
```

### Method 2: Via the Web Dashboard UI
1. Start the application:
   ```bash
   python app.py
   ```
2. Open `http://127.0.0.1:5000` in your browser.
3. Click the **"Link AWS Account"** button (or click the AWS status pill in the top header).
4. Enter your AWS Access Key ID, Secret Access Key, Region, S3 bucket names, and Lambda function name.
5. Click **"Test Connection"** to verify AWS STS and bucket permissions in real-time.
6. Click **"Save & Activate Cloud Mode"** to switch the live pipeline directly to AWS!

### Method 3: Direct `.env` File Configuration
Create a `.env` file in the root directory (based on `.env.example`):

```ini
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
AWS_RAW_BUCKET=iot-gallery-raw-youraccount-us-east-1
AWS_THUMBNAILS_BUCKET=iot-gallery-thumbnails-youraccount-us-east-1
AWS_LAMBDA_FUNCTION_NAME=IoTImageGalleryThumbnailer
AWS_MODE=true
```

### Method 4: Infrastructure-as-Code via AWS SAM CLI
If you prefer AWS Serverless Application Model (SAM):
```bash
cd aws_deploy
sam build
sam deploy --guided
```

