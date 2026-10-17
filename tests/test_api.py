import os
import sys
import base64
import io
import json
from PIL import Image

# Ensure project root is in python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def test_full_pipeline():
    base_url = "http://127.0.0.1:5000"
    client = None

    # Try live HTTP request, fallback to Flask test_client if server not active
    use_live_server = False
    try:
        import requests
        r = requests.get(f"{base_url}/api/iot/status", timeout=1.5)
        if r.status_code == 200:
            use_live_server = True
    except Exception:
        use_live_server = False

    if not use_live_server:
        print("[INFO] Live server not detected on port 5000. Running tests against Flask test_client...")
        from app import app
        client = app.test_client()
    else:
        print("[INFO] Live server detected on port 5000. Testing over HTTP...")

    def api_get(endpoint):
        if use_live_server:
            res = requests.get(f"{base_url}{endpoint}")
            return res.status_code, res.json()
        else:
            res = client.get(endpoint)
            return res.status_code, res.get_json()

    def api_post(endpoint, payload):
        if use_live_server:
            res = requests.post(f"{base_url}{endpoint}", json=payload)
            return res.status_code, res.json()
        else:
            res = client.post(endpoint, data=json.dumps(payload), content_type="application/json")
            return res.status_code, res.get_json()

    # 1. Check IoT Status
    status_code, data = api_get("/api/iot/status")
    print("1. IoT Status Check:", status_code, data["device"]["status"])
    assert status_code == 200

    # 2. Generate a realistic test image buffer
    img = Image.new("RGB", (800, 600), color=(16, 185, 129))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    # 3. Simulate IoT Capture Event (Button Press)
    payload = {
        "trigger": "button_press",
        "image_base64": img_b64,
        "sensors": {
            "battery": 92,
            "temperature": 28.1,
            "lightLux": 450
        }
    }
    status_code, res = api_post("/api/iot/capture", payload)
    print("2. Capture Response Status:", status_code)
    assert res["success"] is True
    print("   LED Status:", res["ledStatus"])
    print("   Upload Duration:", res["uploadDurationMs"], "ms")
    print("   Lambda Duration:", res["lambdaDurationMs"], "ms")
    print("   Savings %:", res["item"]["savingsPercent"])
    print("   Thumbnail:", res["item"]["thumbnail"])

    # 4. Check Gallery
    status_code, gallery = api_get("/api/gallery")
    assert status_code == 200
    print("3. Gallery Total Count:", gallery["count"])
    assert gallery["count"] >= 1

    # 5. Check Cloud Stats
    status_code, stats = api_get("/api/cloud/stats")
    print("4. Cloud Stats:", stats)
    assert stats["success"] is True

    # 6. Check AWS Cloud Status endpoint
    status_code, cloud_status = api_get("/api/cloud/status")
    print("5. Cloud Connection Status API:", cloud_status["status"]["mode"])
    assert status_code == 200

    print("\n>>> ALL TESTS PASSED SUCCESSFULLY! The end-to-end cloud pipeline is fully functional! <<<")

if __name__ == "__main__":
    test_full_pipeline()
