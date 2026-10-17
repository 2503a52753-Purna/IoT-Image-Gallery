import os
import sys
from PIL import Image, ImageDraw

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from lambda_function import lambda_handler

def run_test():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    raw_dir = os.path.join(base_dir, "storage", "raw")
    thumb_dir = os.path.join(base_dir, "storage", "thumbnails")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(thumb_dir, exist_ok=True)

    test_filename = "test_iot_capture.jpg"
    test_filepath = os.path.join(raw_dir, test_filename)

    # 1. Create a dummy test image (1280x720)
    img = Image.new("RGB", (1280, 720), color=(30, 144, 255))
    draw = ImageDraw.Draw(img)
    draw.text((100, 100), "IoT Sensor Capture - Event #1", fill=(255, 255, 255))
    img.save(test_filepath, format="JPEG")
    print(f"Created test raw image: {test_filepath}")

    # 2. Invoke Lambda
    event = {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {"name": "iot-image-gallery-raw"},
                    "object": {"key": test_filename}
                }
            }
        ]
    }

    result = lambda_handler(event)
    print("Lambda Response:", result["statusCode"])
    assert result["statusCode"] == 200, "Lambda should return 200"
    assert result["success"] is True, "Lambda should succeed"

    thumb_path = os.path.join(thumb_dir, f"thumb_{test_filename}")
    assert os.path.exists(thumb_path), f"Thumbnail file should exist at {thumb_path}"
    print(f"Thumbnail created successfully at {thumb_path}")
    print(f"Original size: {result['originalSize']['formatted']} -> Thumbnail: {result['thumbnailSize']['formatted']} (Savings: {result['savingsPercent']}%)")
    print("Test passed successfully!")

if __name__ == "__main__":
    run_test()
