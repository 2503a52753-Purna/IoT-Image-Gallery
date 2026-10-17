"""
Generate PowerPoint Presentation for IoT Image Gallery
======================================================
Theme: Modern Dark Tech & Neon Keynote
High-contrast obsidian background with vibrant Emerald (LED), Electric Cyan (Cloud),
and Radiant Purple (Lambda) accents.
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def build_presentation():
    prs = Presentation()
    # 16:9 Widescreen layout
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6]

    # New Theme: Dark Tech & Neon Keynote Palette
    COLOR_BG = RGBColor(11, 15, 25)           # Deep Dark Obsidian
    COLOR_CARD_BG = RGBColor(20, 28, 46)      # Frosted Navy-Indigo Card
    COLOR_CARD_BORDER = RGBColor(38, 52, 82)  # Card Outline
    
    # Neon Accent Colors
    COLOR_NEON_GREEN = RGBColor(0, 230, 118)  # Bright Emerald LED Green
    COLOR_NEON_CYAN = RGBColor(0, 229, 255)   # Electric Cloud Cyan
    COLOR_NEON_PURPLE = RGBColor(168, 85, 247)# Radiant Lambda Purple
    COLOR_NEON_CORAL = RGBColor(255, 99, 132) # Coral Button Trigger
    COLOR_NEON_AMBER = RGBColor(255, 184, 0)  # Amber Sensor / Alert

    # Typography Colors
    COLOR_WHITE = RGBColor(255, 255, 255)
    COLOR_LIGHT_GRAY = RGBColor(226, 232, 240)
    COLOR_MUTED_GRAY = RGBColor(148, 163, 184)
    COLOR_DIM_GRAY = RGBColor(100, 116, 139)

    def set_slide_background(slide, color=COLOR_BG):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = color
        bg.line.fill.background()

        # Top neon accent line
        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.08))
        line.fill.solid()
        line.fill.fore_color.rgb = COLOR_NEON_CYAN
        line.line.fill.background()
        return bg

    def add_header(slide, title_text, category_text="IOT & SERVERLESS CLOUD ARCHITECTURE", accent_color=COLOR_NEON_CYAN):
        # Header Badge
        badge = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.45), Inches(3.8), Inches(0.38))
        badge.fill.solid()
        badge.fill.fore_color.rgb = RGBColor(15, 23, 42)
        badge.line.color.rgb = accent_color
        badge.line.width = Pt(1)

        btf = badge.text_frame
        btf.word_wrap = False
        btf.margin_left = btf.margin_right = btf.margin_top = btf.margin_bottom = 0
        bp = btf.paragraphs[0]
        bp.text = f"  ●  {category_text.upper()}"
        bp.font.size = Pt(10)
        bp.font.bold = True
        bp.font.color.rgb = accent_color
        bp.alignment = PP_ALIGN.LEFT

        # Main Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.9), Inches(11.7), Inches(0.9))
        tf = title_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        p_title = tf.paragraphs[0]
        p_title.text = title_text
        p_title.font.size = Pt(28)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_WHITE

    def add_card(slide, left, top, width, height, bg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1.5)
        return card

    # =========================================================================
    # SLIDE 1: HERO TITLE SLIDE (Cyber-Dark Theme)
    # =========================================================================
    slide1 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide1, RGBColor(7, 10, 19))

    # Center Hero Card Container
    hero_card = add_card(slide1, Inches(1.2), Inches(1.2), Inches(10.9), Inches(5.1), RGBColor(16, 22, 38), COLOR_CARD_BORDER)

    tbox1 = slide1.shapes.add_textbox(Inches(1.8), Inches(1.7), Inches(9.7), Inches(4.2))
    tf1 = tbox1.text_frame
    tf1.word_wrap = True

    p = tf1.paragraphs[0]
    p.text = "CLOUD COMPUTING & IOT ARCHITECTURE"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = COLOR_NEON_CYAN

    p = tf1.add_paragraph()
    p.text = "IoT Image Gallery"
    p.font.size = Pt(46)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE
    p.space_before = Pt(8)

    p = tf1.add_paragraph()
    p.text = "“Press a button to capture an event; an LED confirms upload; image auto thumbnail via Lambda”"
    p.font.size = Pt(18)
    p.font.color.rgb = COLOR_NEON_GREEN
    p.space_before = Pt(14)

    p = tf1.add_paragraph()
    p.text = "A simple, beginner-friendly walkthrough explaining how physical IoT hardware connects with Cloud Storage and AWS Serverless Functions."
    p.font.size = Pt(14)
    p.font.color.rgb = COLOR_MUTED_GRAY
    p.space_before = Pt(16)

    # Bottom pill badges
    pills = [("📸 Hardware Button", COLOR_NEON_CORAL), ("🟢 Green LED Indicator", COLOR_NEON_GREEN), ("⚡ AWS Lambda Serverless", COLOR_NEON_PURPLE), ("🌐 Live Web Gallery", COLOR_NEON_CYAN)]
    px_start = Inches(1.8)
    for title, col in pills:
        pill = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, px_start, Inches(5.35), Inches(2.2), Inches(0.42))
        pill.fill.solid()
        pill.fill.fore_color.rgb = RGBColor(11, 15, 25)
        pill.line.color.rgb = col
        pill.line.width = Pt(1)
        ptf = pill.text_frame
        ptf.margin_left = ptf.margin_right = ptf.margin_top = ptf.margin_bottom = 0
        pp = ptf.paragraphs[0]
        pp.text = title
        pp.font.size = Pt(11)
        pp.font.bold = True
        pp.font.color.rgb = col
        pp.alignment = PP_ALIGN.CENTER
        px_start += Inches(2.4)

    # =========================================================================
    # SLIDE 2: WHAT IS THIS PROJECT? (Overview)
    # =========================================================================
    slide2 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide2)
    add_header(slide2, "What is the IoT Image Gallery?", "Introduction & Goal")

    # Left Card: Big Idea
    add_card(slide2, Inches(0.8), Inches(1.9), Inches(5.6), Inches(4.9), RGBColor(17, 24, 39), COLOR_NEON_CYAN)
    tb2a = slide2.shapes.add_textbox(Inches(1.1), Inches(2.2), Inches(5.0), Inches(4.3))
    tf2a = tb2a.text_frame
    tf2a.word_wrap = True

    p = tf2a.paragraphs[0]
    p.text = "💡 The Big Idea in Plain English"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = COLOR_NEON_CYAN

    p = tf2a.add_paragraph()
    p.text = "Think of a smart security doorbell or trail camera:\n\n" \
             "1. When something happens, you press a button to capture the moment.\n\n" \
             "2. The camera takes a picture and sends it straight to Cloud Storage.\n\n" \
             "3. A bright GREEN LED light turns on right away on the device, confirming: 'Your photo reached the cloud safely!'\n\n" \
             "4. Behind the scenes, the Cloud automatically creates a lightweight thumbnail version so it loads instantly in the gallery!"
    p.font.size = Pt(14)
    p.font.color.rgb = COLOR_LIGHT_GRAY
    p.space_before = Pt(12)

    # Right Card: Problems Solved
    add_card(slide2, Inches(6.8), Inches(1.9), Inches(5.7), Inches(4.9), RGBColor(17, 24, 39), COLOR_CARD_BORDER)
    tb2b = slide2.shapes.add_textbox(Inches(7.1), Inches(2.2), Inches(5.1), Inches(4.3))
    tf2b = tb2b.text_frame
    tf2b.word_wrap = True

    p = tf2b.paragraphs[0]
    p.text = "🎯 What Problem Does This Solve?"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = COLOR_NEON_GREEN

    p = tf2b.add_paragraph()
    p.text = "• Without an LED Light:\n" \
             "  The user has no idea if the image uploaded or if the internet failed.\n\n" \
             "• Without Cloud Thumbnails:\n" \
             "  Loading 50 large high-resolution photos on a phone or dashboard wastes internet data and makes screens lag.\n\n" \
             "• The Smart Solution:\n" \
             "  Immediate physical feedback (Green LED) + Automatic Serverless resizing in the Cloud!"
    p.font.size = Pt(14)
    p.font.color.rgb = COLOR_LIGHT_GRAY
    p.space_before = Pt(12)

    # =========================================================================
    # SLIDE 3: THE 3 CORE STEPS
    # =========================================================================
    slide3 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide3)
    add_header(slide3, "The 3 Main Steps of the System", "System Overview", COLOR_NEON_GREEN)

    col_width = Inches(3.64)
    gap = Inches(0.4)
    y_top = Inches(1.9)
    h_card = Inches(4.9)

    # Card 1: Step 1 (Capture)
    add_card(slide3, Inches(0.8), y_top, col_width, h_card, RGBColor(18, 26, 44), COLOR_NEON_CORAL)
    tb1 = slide3.shapes.add_textbox(Inches(1.0), Inches(2.1), Inches(3.24), Inches(4.5))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    
    # Title Step 1
    p = tf1.paragraphs[0]
    p.text = "STEP 1 📸"
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = COLOR_NEON_CORAL

    p_sub = tf1.add_paragraph()
    p_sub.text = "Press the Button"
    p_sub.font.size = Pt(17)
    p_sub.font.bold = True
    p_sub.font.color.rgb = COLOR_WHITE
    p_sub.space_before = Pt(4)

    bullets_step1 = [
        ("Push Button Trigger:", "User presses the tactile button (GPIO 14) or Spacebar."),
        ("Instant Capture:", "Camera sensor captures the current scene with shutter flash."),
        ("Flexible Sources:", "Works with animated IoT scenes, custom files, or live webcam."),
        ("Upload Begins:", "Device prepares payload and sends it to the cloud gateway.")
    ]
    for b_title, b_desc in bullets_step1:
        p = tf1.add_paragraph()
        p.text = f"• {b_title} {b_desc}"
        p.font.size = Pt(14)
        p.font.color.rgb = COLOR_WHITE
        p.space_before = Pt(8)

    # Card 2: Step 2 (LED Confirmation)
    add_card(slide3, Inches(0.8) + col_width + gap, y_top, col_width, h_card, RGBColor(18, 26, 44), COLOR_NEON_GREEN)
    tb2 = slide3.shapes.add_textbox(Inches(1.0) + col_width + gap, Inches(2.1), Inches(3.24), Inches(4.5))
    tf2 = tb2.text_frame
    tf2.word_wrap = True

    p = tf2.paragraphs[0]
    p.text = "STEP 2 🟢"
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = COLOR_NEON_GREEN

    p_sub = tf2.add_paragraph()
    p_sub.text = "LED Confirms Upload"
    p_sub.font.size = Pt(17)
    p_sub.font.bold = True
    p_sub.font.color.rgb = COLOR_WHITE
    p_sub.space_before = Pt(4)

    bullets_step2 = [
        ("Cloud Ingestion:", "Image arrives safely into Amazon S3 Raw Bucket storage."),
        ("Gateway Ack:", "Cloud Gateway verifies the file and sends back confirmation."),
        ("Green LED Active:", "Hardware status LED lights up solid bright GREEN!"),
        ("User Confidence:", "The user gets instant proof that their photo is saved in the cloud.")
    ]
    for b_title, b_desc in bullets_step2:
        p = tf2.add_paragraph()
        p.text = f"• {b_title} {b_desc}"
        p.font.size = Pt(14)
        p.font.color.rgb = COLOR_WHITE
        p.space_before = Pt(8)

    # Card 3: Step 3 (Lambda Thumbnail)
    add_card(slide3, Inches(0.8) + (col_width + gap) * 2, y_top, col_width, h_card, RGBColor(18, 26, 44), COLOR_NEON_PURPLE)
    tb3 = slide3.shapes.add_textbox(Inches(1.0) + (col_width + gap) * 2, Inches(2.1), Inches(3.24), Inches(4.5))
    tf3 = tb3.text_frame
    tf3.word_wrap = True

    p = tf3.paragraphs[0]
    p.text = "STEP 3 ⚡"
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = COLOR_NEON_PURPLE

    p_sub = tf3.add_paragraph()
    p_sub.text = "Lambda Thumbnail"
    p_sub.font.size = Pt(17)
    p_sub.font.bold = True
    p_sub.font.color.rgb = COLOR_WHITE
    p_sub.space_before = Pt(4)

    bullets_step3 = [
        ("Event Triggered:", "New S3 upload automatically wakes up AWS Lambda."),
        ("High-Speed Resizing:", "Creates optimized thumbnail using Pillow in just ~30ms!"),
        ("90%+ Data Saved:", "Reduces megabyte-sized raw photo to a lightweight ~40KB file."),
        ("Live Gallery:", "Thumbnail appears instantly in the web gallery without refresh.")
    ]
    for b_title, b_desc in bullets_step3:
        p = tf3.add_paragraph()
        p.text = f"• {b_title} {b_desc}"
        p.font.size = Pt(14)
        p.font.color.rgb = COLOR_WHITE
        p.space_before = Pt(8)

    # =========================================================================
    # SLIDE 4: STEP 1 DETAILED - CAPTURING AN EVENT
    # =========================================================================
    slide4 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide4)
    add_header(slide4, "Step 1: Pressing the Button to Capture", "Edge Device Interaction", COLOR_NEON_CORAL)

    add_card(slide4, Inches(0.8), Inches(1.9), Inches(11.7), Inches(4.9), RGBColor(18, 25, 42), COLOR_CARD_BORDER)
    tb4 = slide4.shapes.add_textbox(Inches(1.2), Inches(2.2), Inches(10.9), Inches(4.3))
    tf4 = tb4.text_frame
    tf4.word_wrap = True

    p = tf4.paragraphs[0]
    p.text = "How Does the Edge Camera Device Work?"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE

    p = tf4.add_paragraph()
    p.text = "In real hardware, this is an ESP32-CAM or Raspberry Pi with a physical push button (GPIO 14). In our software, we created a full hardware simulation and live camera bridge:"
    p.font.size = Pt(14)
    p.font.color.rgb = COLOR_MUTED_GRAY
    p.space_before = Pt(8)

    points = [
        ("🔴 Tactile Push Button:", "Clicking the big red button on the dashboard (or tapping Spacebar) immediately fires the camera shutter."),
        ("📷 Multiple Camera Feeds:", "Test with 4 animated IoT scenes (Smart Doorbell, Smart Farm, Warehouse, Rover), connect a real laptop Webcam, or upload an image file."),
        ("🔊 Shutter Sound & Flash:", "Equipped with a realistic camera shutter flash animation and synthesized click sound so it feels like a real device."),
        ("📡 Sensor Telemetry:", "Together with the photo, the device collects battery percentage (94%), temperature (27.4°C), and ambient light lux.")
    ]

    for title, desc in points:
        p = tf4.add_paragraph()
        p.text = f"{title}  {desc}"
        p.font.size = Pt(14)
        p.font.color.rgb = COLOR_LIGHT_GRAY
        p.space_before = Pt(10)

    # =========================================================================
    # SLIDE 5: STEP 2 DETAILED - LED UPLOAD CONFIRMATION
    # =========================================================================
    slide5 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide5)
    add_header(slide5, "Step 2: An LED Confirms the Upload", "Hardware State Machine", COLOR_NEON_GREEN)

    add_card(slide5, Inches(0.8), Inches(1.9), Inches(11.7), Inches(4.9), RGBColor(18, 25, 42), COLOR_CARD_BORDER)
    tb5 = slide5.shapes.add_textbox(Inches(1.2), Inches(2.2), Inches(10.9), Inches(4.3))
    tf5 = tb5.text_frame
    tf5.word_wrap = True

    p = tf5.paragraphs[0]
    p.text = "Why Do We Need an LED Confirmation?"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE

    p = tf5.add_paragraph()
    p.text = "In real IoT edge devices, there is no computer monitor. An LED indicator gives instant, crystal-clear status so anyone standing by knows what is happening:"
    p.font.size = Pt(14)
    p.font.color.rgb = COLOR_MUTED_GRAY
    p.space_before = Pt(8)

    led_states = [
        ("1. STANDBY (Dim/Off):", "The device is in low-power idle mode, waiting for a button press.", COLOR_MUTED_GRAY),
        ("2. CAPTURING (Blinking Amber):", "Button was pressed! The camera is actively exposing and capturing the frame.", COLOR_NEON_AMBER),
        ("3. UPLOADING (Pulsing Cyan):", "The image is being uploaded to the Cloud Gateway over Wi-Fi / HTTP.", COLOR_NEON_CYAN),
        ("4. UPLOAD CONFIRMED (Solid Glowing GREEN):", "Cloud received the image safely! Green LED lights up with a confirmation chime. You know the photo is secure!", COLOR_NEON_GREEN),
        ("5. ERROR (Red):", "Alerts the user if the network connection was lost or upload failed.", COLOR_NEON_CORAL)
    ]

    for title, desc, col in led_states:
        p = tf5.add_paragraph()
        p.text = f"{title}  {desc}"
        p.font.size = Pt(14)
        p.font.color.rgb = col if col == COLOR_NEON_GREEN else COLOR_LIGHT_GRAY
        if col == COLOR_NEON_GREEN:
            p.font.bold = True
        p.space_before = Pt(8)

    # =========================================================================
    # SLIDE 6: STEP 3 DETAILED - LAMBDA AUTO-THUMBNAIL
    # =========================================================================
    slide6 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide6)
    add_header(slide6, "Step 3: Image Auto Thumbnail via AWS Lambda", "Serverless Cloud Computing", COLOR_NEON_PURPLE)

    # Left Card
    add_card(slide6, Inches(0.8), Inches(1.9), Inches(5.6), Inches(4.9), RGBColor(19, 26, 44), COLOR_NEON_PURPLE)
    tb6a = slide6.shapes.add_textbox(Inches(1.1), Inches(2.2), Inches(5.0), Inches(4.3))
    tf6a = tb6a.text_frame
    tf6a.word_wrap = True

    p = tf6a.paragraphs[0]
    p.text = "⚡ What is AWS Lambda?"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = COLOR_NEON_PURPLE

    p = tf6a.add_paragraph()
    p.text = "• True Serverless Computing:\n" \
             "  No need to configure, rent, or manage a 24/7 virtual computer.\n\n" \
             "• Automatic Event Trigger:\n" \
             "  The Lambda function 'sleeps' until an image lands in the S3 Raw Bucket (`s3:ObjectCreated`).\n\n" \
             "• Blazing Fast Execution:\n" \
             "  Wakes up in milliseconds, resizes the image, writes the thumbnail, and exits in under 35ms!\n\n" \
             "• Zero Idle Cost:\n" \
             "  You only pay for the exact milliseconds used."
    p.font.size = Pt(14)
    p.font.color.rgb = COLOR_LIGHT_GRAY
    p.space_before = Pt(10)

    # Right Card
    add_card(slide6, Inches(6.8), Inches(1.9), Inches(5.7), Inches(4.9), RGBColor(19, 26, 44), COLOR_NEON_CYAN)
    tb6b = slide6.shapes.add_textbox(Inches(7.1), Inches(2.2), Inches(5.1), Inches(4.3))
    tf6b = tb6b.text_frame
    tf6b.word_wrap = True

    p = tf6b.paragraphs[0]
    p.text = "🖼️ The Thumbnail Magic"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = COLOR_NEON_CYAN

    p = tf6b.add_paragraph()
    p.text = "• Pillow Image Processing:\n" \
             "  Uses Python Pillow with high-quality Lanczos resampling to preserve aspect ratio and visual clarity.\n\n" \
             "• 90% to 96% Data Reduction:\n" \
             "  Shrinks large multi-megabyte photos down to lightweight 30-40 KB thumbnails!\n\n" \
             "• Instant Gallery Loading:\n" \
             "  Mobile apps and web pages load immediately without consuming excessive internet data or bandwidth."
    p.font.size = Pt(14)
    p.font.color.rgb = COLOR_LIGHT_GRAY
    p.space_before = Pt(10)

    # =========================================================================
    # SLIDE 7: COMPLETE PROCESS FLOW (Architecture Map)
    # =========================================================================
    slide7 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide7)
    add_header(slide7, "The Complete Cloud Architecture Flow", "Step-by-Step Data Journey")

    add_card(slide7, Inches(0.8), Inches(1.9), Inches(11.7), Inches(4.9), RGBColor(18, 25, 42), COLOR_CARD_BORDER)
    tb7 = slide7.shapes.add_textbox(Inches(1.2), Inches(2.2), Inches(10.9), Inches(4.3))
    tf7 = tb7.text_frame
    tf7.word_wrap = True

    p = tf7.paragraphs[0]
    p.text = "The End-to-End Journey of an Image:"
    p.font.size = Pt(19)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE

    flow_steps = [
        ("1️⃣ User presses button", "Camera captures the event frame and gathers sensor telemetry.", COLOR_NEON_CORAL),
        ("2️⃣ Cloud Gateway receives photo", "Sends raw image into Amazon S3 Raw Bucket (`s3://raw-images`).", COLOR_NEON_CYAN),
        ("3️⃣ Upload Confirmed!", "Cloud sends confirmation code -> Hardware LED turns solid glowing GREEN!", COLOR_NEON_GREEN),
        ("4️⃣ S3 Event triggers Lambda", "S3 automatically fires an `ObjectCreated` event notification to AWS Lambda.", COLOR_NEON_PURPLE),
        ("5️⃣ Lambda creates Thumbnail", "Generates high-efficiency thumbnail and saves it to `s3://thumbnails`.", COLOR_NEON_PURPLE),
        ("6️⃣ Real-time Gallery Sync", "Web gallery updates live over Server-Sent Events (SSE) without refreshing!", COLOR_NEON_CYAN)
    ]

    for title, desc, col in flow_steps:
        p = tf7.add_paragraph()
        p.text = f"{title}   ➔   {desc}"
        p.font.size = Pt(14)
        p.font.color.rgb = COLOR_LIGHT_GRAY
        p.space_before = Pt(8)

    # =========================================================================
    # SLIDE 8: REAL-WORLD RESULTS & METRICS
    # =========================================================================
    slide8 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide8)
    add_header(slide8, "Real-World Results & Benefits", "Performance & Cost Savings", COLOR_NEON_GREEN)

    # 4 Glowing Metric Cards
    metrics = [
        ("⚡ 30 ms", "Avg Lambda Speed", "Thumbnails are ready almost instantaneously.", COLOR_NEON_PURPLE),
        ("💾 91% - 96%", "Storage & Data Saved", "Massive reduction in bandwidth and load times.", COLOR_NEON_GREEN),
        ("🟢 100%", "Visual Confidence", "Green LED guarantees proof of upload to the user.", COLOR_NEON_CYAN),
        ("💰 $0 Server Cost", "True Serverless", "Zero idle costs; you only pay when photos arrive.", COLOR_NEON_AMBER),
    ]

    m_width = Inches(2.7)
    m_gap = Inches(0.3)
    for idx, (stat, label, desc, col) in enumerate(metrics):
        left_pos = Inches(0.8) + idx * (m_width + m_gap)
        add_card(slide8, left_pos, Inches(1.9), m_width, Inches(4.9), RGBColor(19, 26, 44), col)
        tbm = slide8.shapes.add_textbox(left_pos + Inches(0.2), Inches(2.2), m_width - Inches(0.4), Inches(4.3))
        tfm = tbm.text_frame
        tfm.word_wrap = True

        p = tfm.paragraphs[0]
        p.text = stat
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = col

        p = tfm.add_paragraph()
        p.text = label
        p.font.size = Pt(15)
        p.font.bold = True
        p.font.color.rgb = COLOR_WHITE
        p.space_before = Pt(10)

        p = tfm.add_paragraph()
        p.text = desc
        p.font.size = Pt(13)
        p.font.color.rgb = COLOR_MUTED_GRAY
        p.space_before = Pt(10)

    # =========================================================================
    # SLIDE 9: SUMMARY & CONCLUSION
    # =========================================================================
    slide9 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide9, RGBColor(7, 10, 19))

    # Center Conclusion Card
    add_card(slide9, Inches(1.2), Inches(1.2), Inches(10.9), Inches(5.1), RGBColor(16, 22, 38), COLOR_NEON_CYAN)

    tb9 = slide9.shapes.add_textbox(Inches(1.8), Inches(1.6), Inches(9.7), Inches(4.3))
    tf9 = tb9.text_frame
    tf9.word_wrap = True

    p = tf9.paragraphs[0]
    p.text = "CONCLUSION"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = COLOR_NEON_CYAN

    p = tf9.add_paragraph()
    p.text = "Summary: IoT Image Gallery"
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE
    p.space_before = Pt(6)

    takeaways = [
        ("✔ Seamless IoT to Cloud Connection:", "Physical button capture feeds directly into cloud storage."),
        ("✔ Instant Human Feedback:", "Green LED confirms upload success immediately without needing a screen."),
        ("✔ Serverless Efficiency:", "AWS Lambda automatically processes images without managing servers."),
        ("✔ High Performance:", "Achieves over 90% bandwidth savings and ultra-fast web gallery rendering.")
    ]

    for title, desc in takeaways:
        p = tf9.add_paragraph()
        p.text = f"{title}  {desc}"
        p.font.size = Pt(15)
        p.font.color.rgb = COLOR_LIGHT_GRAY
        p.space_before = Pt(14)

    # Output files (handle file lock if user has the previous PPT open)
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "IoT_Image_Gallery_Presentation.pptx")
    alt_output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "IoT_Image_Gallery_Presentation_Updated.pptx")
    
    saved_paths = []
    # Always save updated version
    try:
        prs.save(alt_output_path)
        saved_paths.append(alt_output_path)
    except Exception as e:
        print(f"Could not save to alt path: {e}")

    try:
        prs.save(output_path)
        saved_paths.append(output_path)
    except PermissionError:
        print(f"Note: {output_path} is currently open in PowerPoint. Saved to {alt_output_path} instead.")

    print(f"Presentation saved to: {saved_paths}")
    return saved_paths[0] if saved_paths else alt_output_path

if __name__ == "__main__":
    build_presentation()
