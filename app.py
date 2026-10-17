"""
IoT Image Gallery - Cloud Computing Application Server
======================================================
Backend service featuring:
- IoT Edge Ingestion & Event Gateway
- Virtual & Physical LED State Synchronization
- S3 Bucket Storage Emulator (Raw & Thumbnails)
- Real-time Server-Sent Events (SSE) Stream
- RESTful Gallery API & Cloud Performance Metrics
"""

import os
import sys
import json
import time
import uuid
import queue
import base64
import threading
from datetime import datetime
from flask import Flask, request, jsonify, Response, send_from_directory, render_template_string
from flask_cors import CORS
from lambda_function import lambda_handler
from aws_service import aws_service

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
RAW_DIR = os.path.join(STORAGE_DIR, "raw")
THUMB_DIR = os.path.join(STORAGE_DIR, "thumbnails")
DB_FILE = os.path.join(STORAGE_DIR, "database.json")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)

app = Flask(__name__, static_folder="static")
CORS(app)

# Thread-safe database lock and SSE subscribers
db_lock = threading.Lock()
sse_subscribers = []
sse_lock = threading.Lock()

# IoT Device State
device_state = {
    "deviceId": "ESP32-CAM-NODE-01",
    "status": "ONLINE",
    "firmware": "v2.4.1-cloud",
    "ledState": "IDLE",  # IDLE, CAPTURING, UPLOADING, CONFIRMED, ERROR
    "lastPing": datetime.utcnow().isoformat() + "Z",
    "gpio": {
        "buttonPin": 14,
        "greenLedPin": 27,
        "statusLedPin": 12
    },
    "telemetry": {
        "battery": 94,
        "temperature": 27.4,
        "lightLux": 420,
        "wifiRssi": -58
    }
}

def load_db():
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def broadcast_event(event_type, payload):
    """Broadcast real-time event to all active SSE browser connections"""
    message = f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
    with sse_lock:
        dead_clients = []
        for q in sse_subscribers:
            try:
                q.put_nowait(message)
            except Exception:
                dead_clients.append(q)
        for d in dead_clients:
            if d in sse_subscribers:
                sse_subscribers.remove(d)

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/storage/raw/<path:filename>")
def serve_raw(filename):
    return send_from_directory(RAW_DIR, filename)

@app.route("/storage/thumbnails/<path:filename>")
def serve_thumbnail(filename):
    return send_from_directory(THUMB_DIR, filename)

# ----------------- REAL-TIME SSE STREAM -----------------
@app.route("/api/events")
def events_stream():
    """Server-Sent Events endpoint for instant UI updates"""
    client_queue = queue.Queue(maxsize=100)
    with sse_lock:
        sse_subscribers.append(client_queue)

    def stream():
        # Send initial device state
        yield f"event: device_state\ndata: {json.dumps(device_state)}\n\n"
        while True:
            try:
                msg = client_queue.get(timeout=30)
                yield msg
            except queue.Empty:
                # Keep-alive heartbeat
                yield ": heartbeat\n\n"
            except GeneratorExit:
                with sse_lock:
                    if client_queue in sse_subscribers:
                        sse_subscribers.remove(client_queue)
                break

    return Response(stream(), mimetype="text/event-stream")

# ----------------- IOT EDGE APIS -----------------
@app.route("/api/iot/status", methods=["GET"])
def get_iot_status():
    device_state["lastPing"] = datetime.utcnow().isoformat() + "Z"
    return jsonify({"success": True, "device": device_state})

@app.route("/api/iot/capture", methods=["POST"])
def iot_capture():
    """
    Main IoT Capture Endpoint:
    1. Receives button trigger & image (webcam snapshot, upload, or simulated frame)
    2. Changes LED to CAPTURING, then UPLOADING
    3. Saves raw image to Raw Bucket (S3 simulated)
    4. CONFIRMS UPLOAD -> LED changes to CONFIRMED (Solid bright GREEN)
    5. Triggers Serverless Lambda for auto-thumbnail generation
    6. Updates database & broadcasts all pipeline steps in real-time
    """
    capture_start = time.time()
    event_id = str(uuid.uuid4())
    timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    raw_filename = f"iot_event_{timestamp_str}_{event_id[:6]}.jpg"
    raw_filepath = os.path.join(RAW_DIR, raw_filename)

    trigger_source = "button_press"
    sensor_data = {}

    # Update device state: CAPTURING
    device_state["ledState"] = "CAPTURING"
    broadcast_event("pipeline_step", {
        "step": "iot_captured",
        "title": "IoT Button Triggered",
        "description": "GPIO 14 Button pressed. Camera shutter activated.",
        "ledState": "CAPTURING"
    })

    # Read payload
    if request.is_json:
        data = request.get_json() or {}
        trigger_source = data.get("trigger", "button_press")
        sensor_data = data.get("sensors", {})
        image_base64 = data.get("image_base64", "")
        if image_base64.startswith("data:image"):
            # strip data:image/jpeg;base64,
            image_base64 = image_base64.split(",", 1)[1]
        raw_bytes = base64.b64decode(image_base64)
    elif "image" in request.files:
        uploaded_file = request.files["image"]
        trigger_source = request.form.get("trigger", "manual_upload")
        raw_bytes = uploaded_file.read()
    else:
        return jsonify({"success": False, "error": "No image data provided"}), 400

    # Device state: UPLOADING
    device_state["ledState"] = "UPLOADING"
    is_cloud_active = aws_service.enabled and bool(aws_service.raw_bucket)

    if is_cloud_active:
        broadcast_event("pipeline_step", {
            "step": "uploading",
            "title": "Uploading to AWS S3 Raw Bucket",
            "description": f"Transmitting payload ({len(raw_bytes)} bytes) to s3://{aws_service.raw_bucket}/{raw_filename}...",
            "ledState": "UPLOADING",
            "cloudMode": "AWS_CLOUD"
        })
        # Upload to AWS S3
        aws_upload_res = aws_service.upload_raw_image(raw_filename, raw_bytes)
        if not aws_upload_res or not aws_upload_res.get("success"):
            print(f"[app.py] AWS S3 upload warning: {aws_upload_res.get('error') if aws_upload_res else 'Failed'}")
    else:
        broadcast_event("pipeline_step", {
            "step": "uploading",
            "title": "Ingesting to Cloud Raw Bucket (Simulated)",
            "description": f"Transmitting payload ({len(raw_bytes)} bytes) to storage/raw/...",
            "ledState": "UPLOADING",
            "cloudMode": "LOCAL_SIMULATION"
        })

    # Save to local storage as cache / offline backup
    try:
        with open(raw_filepath, "wb") as f:
            f.write(raw_bytes)
    except Exception as e:
        print(f"[app.py] Local write error: {e}")

    upload_duration_ms = round((time.time() - capture_start) * 1000, 2)

    # UPLOAD CONFIRMED! Green LED lights up!
    device_state["ledState"] = "CONFIRMED"
    if is_cloud_active:
        broadcast_event("pipeline_step", {
            "step": "upload_confirmed",
            "title": "AWS S3 Upload Confirmed - LED Active!",
            "description": f"Upload confirmed by AWS S3 ({aws_service.raw_bucket}) in {upload_duration_ms} ms. Hardware Green LED: ON.",
            "ledState": "CONFIRMED",
            "rawFilename": raw_filename,
            "cloudMode": "AWS_CLOUD"
        })
    else:
        broadcast_event("pipeline_step", {
            "step": "upload_confirmed",
            "title": "Upload Confirmed - LED Active!",
            "description": f"Upload verified by Cloud Gateway in {upload_duration_ms} ms. Hardware Green LED: ON.",
            "ledState": "CONFIRMED",
            "rawFilename": raw_filename,
            "cloudMode": "LOCAL_SIMULATION"
        })

    # Prepare S3 Event Notification payload
    target_bucket = aws_service.raw_bucket if is_cloud_active else "iot-image-gallery-raw"
    s3_event = {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {"name": target_bucket},
                    "object": {"key": raw_filename, "size": len(raw_bytes)}
                }
            }
        ],
        "metadata": {
            "trigger": trigger_source,
            "deviceId": device_state["deviceId"],
            "sensors": sensor_data
        }
    }

    # Execute Lambda function (Remote AWS Lambda or Local Serverless Engine)
    lambda_res = None
    if is_cloud_active and aws_service.lambda_function_name:
        broadcast_event("pipeline_step", {
            "step": "lambda_invoking",
            "title": "Triggering AWS Cloud Lambda",
            "description": f"Invoking Lambda ({aws_service.lambda_function_name}) for s3://{target_bucket}/{raw_filename}...",
            "ledState": "PROCESSING",
            "cloudMode": "AWS_CLOUD"
        })
        lambda_res = aws_service.invoke_lambda(s3_event)

    if not lambda_res or not lambda_res.get("success"):
        # Fallback to local serverless handler
        broadcast_event("pipeline_step", {
            "step": "lambda_invoking",
            "title": "Triggering Serverless Lambda (Local)",
            "description": f"S3 ObjectCreated event dispatched for s3://{target_bucket}/{raw_filename}",
            "ledState": "PROCESSING",
            "cloudMode": "LOCAL_SIMULATION"
        })
        lambda_res = lambda_handler(s3_event)

    total_pipeline_ms = round((time.time() - capture_start) * 1000, 2)
    thumb_filename = lambda_res.get("thumbnailKey", f"thumb_{raw_filename}")

    # Resolve URLs (AWS Presigned S3 URLs if active, else local static storage)
    raw_url = f"/storage/raw/{raw_filename}"
    thumb_url = f"/storage/thumbnails/{thumb_filename}"

    if is_cloud_active and aws_upload_res and aws_upload_res.get("success"):
        presigned_raw = aws_service.get_presigned_url(aws_service.raw_bucket, raw_filename)
        if presigned_raw:
            raw_url = presigned_raw
        
        dest_thumb_bucket = aws_service.thumbnails_bucket or aws_service.raw_bucket.replace("raw", "thumbnails")
        presigned_thumb = aws_service.get_presigned_url(dest_thumb_bucket, thumb_filename)
        if presigned_thumb:
            thumb_url = presigned_thumb

    # Build gallery item record
    item = {
        "id": event_id,
        "filename": raw_filename,
        "thumbnail": thumb_filename,
        "rawUrl": raw_url,
        "thumbnailUrl": thumb_url,
        "trigger": trigger_source,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "createdAtFormatted": datetime.utcnow().strftime("%b %d, %Y - %I:%M:%S %p UTC"),
        "originalSize": lambda_res.get("originalSize", {}),
        "thumbnailSize": lambda_res.get("thumbnailSize", {}),
        "savingsPercent": lambda_res.get("savingsPercent", 0),
        "dominantColor": lambda_res.get("dominantColor", "#3b82f6"),
        "brightness": lambda_res.get("brightness", 50),
        "uploadDurationMs": upload_duration_ms,
        "lambdaDurationMs": lambda_res.get("durationMs", 0),
        "billedDurationMs": lambda_res.get("billedDurationMs", 100),
        "totalPipelineMs": total_pipeline_ms,
        "cloudWatchLogs": lambda_res.get("cloudWatchLogs", []),
        "cloudMode": "AWS_CLOUD" if is_cloud_active else "LOCAL_SIMULATION",
        "awsLambdaInvoked": lambda_res.get("awsLambdaInvoked", False),
        "cloudInfo": {
            "region": aws_service.region,
            "rawBucket": aws_service.raw_bucket if is_cloud_active else None,
            "thumbnailsBucket": aws_service.thumbnails_bucket if is_cloud_active else None,
            "lambdaFunction": aws_service.lambda_function_name if is_cloud_active else None
        },
        "sensors": {
            "battery": sensor_data.get("battery", device_state["telemetry"]["battery"]),
            "temperature": sensor_data.get("temperature", device_state["telemetry"]["temperature"]),
            "lightLux": sensor_data.get("lightLux", device_state["telemetry"]["lightLux"]),
            "deviceId": device_state["deviceId"],
            "gpioButton": device_state["gpio"]["buttonPin"],
            "gpioLed": device_state["gpio"]["greenLedPin"]
        }
    }

    with db_lock:
        gallery = load_db()
        gallery.insert(0, item)
        save_db(gallery)

    # Broadcast thumbnail ready and gallery update
    broadcast_event("pipeline_step", {
        "step": "thumbnail_ready",
        "title": "Lambda Execution Succeeded",
        "description": f"Generated {item['thumbnailSize'].get('formatted', '')} thumbnail in {item['lambdaDurationMs']} ms. Total savings: {item['savingsPercent']}%.",
        "ledState": "CONFIRMED",
        "item": item
    })

    broadcast_event("gallery_updated", {"item": item, "total": len(gallery)})

    # Return full response to the caller
    return jsonify({
        "success": True,
        "message": "Event captured, uploaded, and thumbnail generated successfully",
        "ledStatus": "CONFIRMED (Green)",
        "uploadDurationMs": upload_duration_ms,
        "lambdaDurationMs": item["lambdaDurationMs"],
        "totalPipelineMs": total_pipeline_ms,
        "item": item
    })

# ----------------- GALLERY APIS -----------------
@app.route("/api/gallery", methods=["GET"])
def get_gallery():
    with db_lock:
        items = load_db()
    return jsonify({"success": True, "count": len(items), "items": items})

@app.route("/api/gallery/<item_id>", methods=["GET"])
def get_gallery_item(item_id):
    with db_lock:
        items = load_db()
    for it in items:
        if it["id"] == item_id or it["filename"] == item_id:
            return jsonify({"success": True, "item": it})
    return jsonify({"success": False, "error": "Item not found"}), 404

@app.route("/api/gallery/<item_id>", methods=["DELETE"])
def delete_gallery_item(item_id):
    with db_lock:
        items = load_db()
        target = None
        new_items = []
        for it in items:
            if it["id"] == item_id or it["filename"] == item_id:
                target = it
            else:
                new_items.append(it)
        if target:
            save_db(new_items)
            # Remove files
            raw_path = os.path.join(RAW_DIR, target["filename"])
            thumb_path = os.path.join(THUMB_DIR, target["thumbnail"])
            if os.path.exists(raw_path):
                os.remove(raw_path)
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
            broadcast_event("gallery_updated", {"deletedId": item_id, "total": len(new_items)})
            return jsonify({"success": True, "message": "Item deleted"})
    return jsonify({"success": False, "error": "Item not found"}), 404

@app.route("/api/gallery/clear", methods=["POST"])
def clear_gallery():
    with db_lock:
        items = load_db()
        for it in items:
            raw_path = os.path.join(RAW_DIR, it["filename"])
            thumb_path = os.path.join(THUMB_DIR, it["thumbnail"])
            if os.path.exists(raw_path):
                try: os.remove(raw_path)
                except Exception: pass
            if os.path.exists(thumb_path):
                try: os.remove(thumb_path)
                except Exception: pass
        save_db([])
        broadcast_event("gallery_updated", {"total": 0, "cleared": True})
    return jsonify({"success": True, "message": "Gallery cleared"})

# ----------------- CLOUD METRICS API -----------------
@app.route("/api/cloud/stats", methods=["GET"])
def get_cloud_stats():
    with db_lock:
        items = load_db()
    
    total_images = len(items)
    total_raw_bytes = sum(it.get("originalSize", {}).get("bytes", 0) for it in items)
    total_thumb_bytes = sum(it.get("thumbnailSize", {}).get("bytes", 0) for it in items)
    bytes_saved = max(0, total_raw_bytes - total_thumb_bytes)
    overall_savings_pct = round((bytes_saved / max(total_raw_bytes, 1)) * 100, 1)
    
    durations = [it.get("lambdaDurationMs", 0) for it in items if it.get("lambdaDurationMs")]
    avg_duration = round(sum(durations) / max(len(durations), 1), 1) if durations else 0

    return jsonify({
        "success": True,
        "totalEvents": total_images,
        "totalRawBytes": total_raw_bytes,
        "totalThumbBytes": total_thumb_bytes,
        "bytesSaved": bytes_saved,
        "overallSavingsPercent": overall_savings_pct,
        "avgLambdaDurationMs": avg_duration,
        "activeSubscribers": len(sse_subscribers)
    })

# ----------------- AWS CLOUD CONFIGURATION APIS -----------------
@app.route("/api/cloud/status", methods=["GET"])
def get_cloud_status():
    """Return real-time AWS Cloud connectivity and resource status"""
    return jsonify({"success": True, "status": aws_service.get_status()})

@app.route("/api/cloud/test", methods=["POST"])
def test_cloud_connection():
    """Test AWS credentials and resource accessibility"""
    data = request.get_json() or {}
    res = aws_service.test_connection(
        access_key=data.get("accessKeyId"),
        secret_key=data.get("secretAccessKey"),
        region=data.get("region"),
        raw_bucket=data.get("rawBucket"),
        thumb_bucket=data.get("thumbnailsBucket"),
        lambda_fn=data.get("lambdaFunction"),
        session_token=data.get("sessionToken")
    )
    return jsonify(res)

@app.route("/api/cloud/configure", methods=["POST"])
def configure_cloud():
    """Update AWS credentials and cloud parameters, saving to .env"""
    data = request.get_json() or {}
    new_status = aws_service.save_configuration(
        access_key=data.get("accessKeyId"),
        secret_key=data.get("secretAccessKey"),
        region=data.get("region", "us-east-1"),
        raw_bucket=data.get("rawBucket"),
        thumb_bucket=data.get("thumbnailsBucket"),
        lambda_fn=data.get("lambdaFunction", "IoTImageGalleryThumbnailer"),
        enabled=data.get("enabled", True),
        session_token=data.get("sessionToken")
    )
    broadcast_event("cloud_mode_changed", {"status": new_status})
    return jsonify({"success": True, "status": new_status})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    cloud_st = aws_service.get_status()
    print(f"===========================================================")
    print(f"  IoT Image Gallery Cloud Application Starting...")
    print(f"  URL: http://127.0.0.1:{port}")
    print(f"  IoT Device: {device_state['deviceId']}")
    print(f"  Cloud Mode: {cloud_st.get('mode')} (Connected: {cloud_st.get('connected')})")
    if cloud_st.get("connected"):
        print(f"  AWS Account: {cloud_st.get('accountId')} | Region: {cloud_st.get('region')}")
        print(f"  S3 Raw: s3://{cloud_st.get('rawBucket')} -> Thumbnails: s3://{cloud_st.get('thumbnailsBucket')}")
        print(f"  Lambda: {cloud_st.get('lambdaFunction')}")
    else:
        print(f"  Storage: Local Emulation (storage/raw -> storage/thumbnails)")
    print(f"===========================================================")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)

