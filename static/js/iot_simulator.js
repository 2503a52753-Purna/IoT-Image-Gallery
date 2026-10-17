/**
 * IoT Simulator - Camera, Push Button, Audio FX & Hardware LED Controller
 */

class IoTSimulator {
  constructor() {
    this.mode = 'simulated'; // 'simulated', 'webcam', 'upload'
    this.canvas = document.getElementById('sceneCanvas');
    this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
    this.video = document.getElementById('webcamVideo');
    this.shutterFlash = document.getElementById('shutterFlash');
    this.tactileBtn = document.getElementById('tactileCaptureBtn');
    this.ledLamp = document.getElementById('hardwareLedLamp');
    this.ledText = document.getElementById('hardwareLedStatusText');
    this.audioEnabled = true;

    this.audioCtx = null;
    this.sceneIndex = 0;
    this.scenes = [
      { name: "Smart Entrance Node", icon: "🚪", bgTop: "#1e3a8a", bgBot: "#0f172a" },
      { name: "Smart Farm & Weather", icon: "🌾", bgTop: "#14532d", bgBot: "#052e16" },
      { name: "Warehouse Surveillance", icon: "📦", bgTop: "#581c87", bgBot: "#1e1b4b" },
      { name: "Autonomous Rover", icon: "🤖", bgTop: "#7c2d12", bgBot: "#450a0a" }
    ];

    this.telemetry = {
      battery: 94,
      temp: 27.4,
      lux: 420
    };

    this.animationFrameId = null;
    this.init();
  }

  init() {
    this.initAudio();
    this.startSceneAnimation();
    this.setupEventListeners();
    this.setLedState('IDLE');
  }

  initAudio() {
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        this.audioCtx = new AudioContext();
      }
    } catch (e) {
      console.warn("Web Audio not supported", e);
    }
  }

  playShutterSound() {
    if (!this.audioEnabled || !this.audioCtx) return;
    try {
      if (this.audioCtx.state === 'suspended') {
        this.audioCtx.resume();
      }
      const osc = this.audioCtx.createOscillator();
      const gain = this.audioCtx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(800, this.audioCtx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(120, this.audioCtx.currentTime + 0.08);

      gain.gain.setValueAtTime(0.3, this.audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, this.audioCtx.currentTime + 0.08);

      osc.connect(gain);
      gain.connect(this.audioCtx.destination);
      osc.start();
      osc.stop(this.audioCtx.currentTime + 0.09);
    } catch (e) {}
  }

  playConfirmChime() {
    if (!this.audioEnabled || !this.audioCtx) return;
    try {
      if (this.audioCtx.state === 'suspended') {
        this.audioCtx.resume();
      }
      const now = this.audioCtx.currentTime;
      // Two-tone chime (E5 -> B5)
      const freqs = [659.25, 987.77];
      freqs.forEach((freq, idx) => {
        const osc = this.audioCtx.createOscillator();
        const gain = this.audioCtx.createGain();
        osc.type = 'sine';
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.18, now + idx * 0.1);
        gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.1 + 0.35);
        osc.connect(gain);
        gain.connect(this.audioCtx.destination);
        osc.start(now + idx * 0.1);
        osc.stop(now + idx * 0.1 + 0.35);
      });
    } catch (e) {}
  }

  setupEventListeners() {
    // Tactile button click
    if (this.tactileBtn) {
      this.tactileBtn.addEventListener('click', () => {
        this.triggerCapture('button_press');
      });
    }

    // Spacebar capture trigger
    window.addEventListener('keydown', (e) => {
      if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
        e.preventDefault();
        this.triggerCapture('button_press');
      }
    });

    // Camera Mode Selectors
    const btnSim = document.getElementById('camModeSim');
    const btnWebcam = document.getElementById('camModeWebcam');
    const btnUpload = document.getElementById('camModeUpload');
    const fileInput = document.getElementById('hiddenFileInput');

    if (btnSim) {
      btnSim.addEventListener('click', () => {
        this.setMode('simulated');
        this.updatePillActive(btnSim);
      });
    }

    if (btnWebcam) {
      btnWebcam.addEventListener('click', async () => {
        const ok = await this.startWebcam();
        if (ok) {
          this.setMode('webcam');
          this.updatePillActive(btnWebcam);
        }
      });
    }

    if (btnUpload && fileInput) {
      btnUpload.addEventListener('click', () => {
        fileInput.click();
      });
      fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
          this.handleFileUpload(e.target.files[0]);
        }
      });
    }

    // Next Scene button
    const btnNextScene = document.getElementById('btnNextScene');
    if (btnNextScene) {
      btnNextScene.addEventListener('click', () => {
        this.sceneIndex = (this.sceneIndex + 1) % this.scenes.length;
      });
    }

    // Sound toggle
    const audioToggle = document.getElementById('audioToggle');
    if (audioToggle) {
      audioToggle.addEventListener('click', () => {
        this.audioEnabled = !this.audioEnabled;
        audioToggle.style.opacity = this.audioEnabled ? "1" : "0.5";
        showToast(this.audioEnabled ? "Audio FX: ON" : "Audio FX: Muted");
      });
    }
  }

  updatePillActive(activeBtn) {
    document.querySelectorAll('.camera-controls-bar .pill-btn').forEach(btn => btn.classList.remove('active'));
    activeBtn.classList.add('active');
  }

  setMode(mode) {
    this.mode = mode;
    if (mode === 'webcam') {
      this.video.style.display = 'block';
      this.canvas.style.display = 'none';
    } else {
      this.video.style.display = 'none';
      this.canvas.style.display = 'block';
      if (this.webcamStream) {
        this.webcamStream.getTracks().forEach(t => t.stop());
        this.webcamStream = null;
      }
    }
  }

  async startWebcam() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720 } });
      this.webcamStream = stream;
      this.video.srcObject = stream;
      await this.video.play();
      showToast("Live Webcam activated");
      return true;
    } catch (err) {
      alert("Could not access webcam: " + err.message + "\nUsing simulated camera instead.");
      return false;
    }
  }

  handleFileUpload(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        // Draw file onto canvas
        this.setMode('simulated');
        this.ctx.drawImage(img, 0, 0, this.canvas.width, this.canvas.height);
        showToast(`Image loaded: ${file.name}`);
        this.triggerCapture('manual_upload', e.target.result);
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  }

  startSceneAnimation() {
    if (!this.canvas || !this.ctx) return;
    this.canvas.width = 640;
    this.canvas.height = 360;

    let tick = 0;
    const draw = () => {
      if (this.mode === 'simulated') {
        tick++;
        const scene = this.scenes[this.sceneIndex];
        const w = this.canvas.width;
        const h = this.canvas.height;

        // Background Gradient
        const grad = this.ctx.createLinearGradient(0, 0, 0, h);
        grad.addColorStop(0, scene.bgTop);
        grad.addColorStop(1, scene.bgBot);
        this.ctx.fillStyle = grad;
        this.ctx.fillRect(0, 0, w, h);

        // Perspective grid lines
        this.ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
        this.ctx.lineWidth = 1;
        const horizon = h * 0.55;
        for (let x = 0; x <= w; x += 40) {
          this.ctx.beginPath();
          this.ctx.moveTo(w / 2, horizon);
          this.ctx.lineTo(x, h);
          this.ctx.stroke();
        }
        for (let y = horizon; y <= h; y += 25) {
          this.ctx.beginPath();
          this.ctx.moveTo(0, y);
          this.ctx.lineTo(w, y);
          this.ctx.stroke();
        }

        // Animated target / movement simulation
        const moveX = (w / 2) + Math.sin(tick * 0.03) * 140;
        const moveY = horizon - 20 + Math.cos(tick * 0.04) * 40;

        // Bounding box / motion detector simulation
        this.ctx.strokeStyle = "rgba(56, 189, 248, 0.8)";
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(moveX - 35, moveY - 35, 70, 70);

        // Scene Icon
        this.ctx.font = "32px sans-serif";
        this.ctx.textAlign = "center";
        this.ctx.textBaseline = "middle";
        this.ctx.fillText(scene.icon, moveX, moveY);

        // AI Label badge
        this.ctx.fillStyle = "rgba(14, 165, 233, 0.9)";
        this.ctx.fillRect(moveX - 35, moveY - 50, 70, 16);
        this.ctx.fillStyle = "#ffffff";
        this.ctx.font = "bold 9px monospace";
        this.ctx.fillText("OBJECT 98%", moveX, moveY - 42);

        // Live Sensor Overlay Watermark
        this.ctx.fillStyle = "rgba(0, 0, 0, 0.6)";
        this.ctx.fillRect(10, h - 35, w - 20, 25);
        this.ctx.fillStyle = "#38bdf8";
        this.ctx.font = "11px monospace";
        this.ctx.textAlign = "left";
        const dateStr = new Date().toISOString().replace('T', ' ').substring(0, 19);
        this.ctx.fillText(`CAM-01 [${scene.name}] | ${dateStr} UTC | LUX: ${this.telemetry.lux} | BAT: ${this.telemetry.battery}%`, 18, h - 18);
      }

      this.animationFrameId = requestAnimationFrame(draw);
    };

    draw();
  }

  getSnapshotBase64() {
    if (this.mode === 'webcam' && this.video.srcObject) {
      const snapCanvas = document.createElement('canvas');
      snapCanvas.width = this.video.videoWidth || 1280;
      snapCanvas.height = this.video.videoHeight || 720;
      const snapCtx = snapCanvas.getContext('2d');
      snapCtx.drawImage(this.video, 0, 0, snapCanvas.width, snapCanvas.height);
      return snapCanvas.toDataURL('image/jpeg', 0.9);
    } else {
      return this.canvas.toDataURL('image/jpeg', 0.9);
    }
  }

  setLedState(state) {
    if (!this.ledLamp || !this.ledText) return;

    this.ledLamp.className = 'led-lamp';
    this.ledText.className = 'led-status-text';

    switch (state) {
      case 'CAPTURING':
        this.ledLamp.classList.add('state-capturing');
        this.ledText.textContent = 'CAPTURING (Amber)';
        this.ledText.style.color = '#fbbf24';
        break;

      case 'UPLOADING':
        this.ledLamp.classList.add('state-uploading');
        this.ledText.textContent = 'UPLOADING (Cyan)';
        this.ledText.style.color = '#38bdf8';
        break;

      case 'CONFIRMED':
        this.ledLamp.classList.add('state-confirmed');
        this.ledText.textContent = 'UPLOAD CONFIRMED (LED: GREEN)';
        this.ledText.classList.add('confirmed');
        this.ledText.style.color = '#4ade80';
        break;

      case 'PROCESSING':
        this.ledLamp.classList.add('state-processing');
        this.ledText.textContent = 'LAMBDA RESIZING (Purple)';
        this.ledText.style.color = '#c084fc';
        break;

      case 'ERROR':
        this.ledLamp.style.background = '#ef4444';
        this.ledLamp.style.boxShadow = '0 0 20px #ef4444';
        this.ledText.textContent = 'ERROR (Red)';
        this.ledText.style.color = '#f87171';
        break;

      case 'IDLE':
      default:
        this.ledText.textContent = 'READY / STANDBY';
        this.ledText.style.color = 'var(--text-muted)';
        break;
    }
  }

  async triggerCapture(triggerType = 'button_press', preloadedBase64 = null) {
    // Visual tactile button press animation
    if (this.tactileBtn) {
      this.tactileBtn.classList.add('pressed');
      setTimeout(() => this.tactileBtn.classList.remove('pressed'), 180);
    }

    // Camera Shutter Flash & Audio
    if (this.shutterFlash) {
      this.shutterFlash.classList.add('flash');
      setTimeout(() => this.shutterFlash.classList.remove('flash'), 120);
    }
    this.playShutterSound();

    // 1. LED State: CAPTURING
    this.setLedState('CAPTURING');
    logConsole("iot", "GPIO 14 Button Pressed. Camera sensor frame acquired.");
    setPipelineNodeState('node-button', 'active');
    setConnectorActive('conn-button-gateway');

    // Get snapshot data
    const imageBase64 = preloadedBase64 || this.getSnapshotBase64();

    // Small delay to simulate shutter/upload pipeline
    setTimeout(() => {
      this.setLedState('UPLOADING');
      logConsole("info", "Transmitting image payload to Cloud Ingestion Gateway...");
      setPipelineNodeState('node-gateway', 'active');
      setConnectorActive('conn-gateway-s3');
    }, 250);

    // Call Cloud Backend
    try {
      const response = await fetch('/api/iot/capture', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          trigger: triggerType,
          image_base64: imageBase64,
          sensors: {
            battery: this.telemetry.battery,
            temperature: (27 + Math.random() * 2).toFixed(1),
            lightLux: Math.floor(400 + Math.random() * 50)
          }
        })
      });

      const res = await response.json();
      if (res.success) {
        // 2. LED Confirms Upload: Solid GREEN!
        this.setLedState('CONFIRMED');
        this.playConfirmChime();
        setPipelineNodeState('node-s3-raw', 'success');
        setPipelineNodeState('node-lambda', 'success');
        setPipelineNodeState('node-s3-thumb', 'success');

        logConsole("success", `Upload Confirmed! Green LED Active. Cloud acknowledgment in ${res.uploadDurationMs}ms.`);
        logConsole("lambda", `Lambda thumbnail completed in ${res.lambdaDurationMs}ms (Savings: ${res.item.savingsPercent}%).`);
        showToast("Upload Confirmed! LED Green & Thumbnail Ready");

        // Keep LED confirmed green for 3 seconds before reverting to ready/idle
        setTimeout(() => {
          if (this.ledText.textContent.includes('UPLOAD CONFIRMED')) {
            this.setLedState('IDLE');
          }
        }, 3500);

      } else {
        this.setLedState('ERROR');
        logConsole("warn", `Upload failed: ${res.error}`);
        showToast("Error: " + res.error);
      }
    } catch (err) {
      this.setLedState('ERROR');
      logConsole("warn", `Network error: ${err.message}`);
      showToast("Network Error: " + err.message);
    }
  }
}
