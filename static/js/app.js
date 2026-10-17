/**
 * IoT Image Gallery - Main Application Controller
 * Real-time SSE, Gallery Rendering, CloudWatch Inspector & AWS Modal
 */

let iotSim = null;
let currentItems = [];
let currentFilter = 'all';

document.addEventListener('DOMContentLoaded', () => {
  // Initialize IoT Simulator
  iotSim = new IoTSimulator();

  // Load Initial Gallery Data & Metrics
  loadGallery();
  loadMetrics();

  // Load Real-time AWS Cloud Status
  loadCloudStatus();

  // Setup Server-Sent Events (SSE)
  initSSE();

  // Setup Global Listeners & Modals
  setupGlobalActions();
  setupAwsConnectHandlers();
});

/* ==========================================================================
   Server-Sent Events (SSE) Stream
   ========================================================================== */
function initSSE() {
  const eventSource = new EventSource('/api/events');

  eventSource.addEventListener('device_state', (e) => {
    try {
      const state = JSON.parse(e.data);
      updateDeviceStateBadge(state);
    } catch (err) {}
  });

  eventSource.addEventListener('pipeline_step', (e) => {
    try {
      const data = JSON.parse(e.data);
      handlePipelineStep(data);
    } catch (err) {}
  });

  eventSource.addEventListener('cloud_mode_changed', (e) => {
    try {
      const data = JSON.parse(e.data);
      if (data.status) {
        updateCloudStatusUI(data.status);
      }
    } catch (err) {}
  });

  eventSource.addEventListener('gallery_updated', (e) => {
    try {
      const data = JSON.parse(e.data);
      if (data.cleared) {
        currentItems = [];
        renderGallery();
        loadMetrics();
      } else if (data.deletedId) {
        currentItems = currentItems.filter(i => i.id !== data.deletedId);
        renderGallery();
        loadMetrics();
      } else if (data.item) {
        // Prepend new item if not present
        if (!currentItems.some(i => i.id === data.item.id)) {
          currentItems.unshift(data.item);
          renderGallery();
          loadMetrics();
        }
      }
    } catch (err) {}
  });

  eventSource.onerror = () => {
    // Reconnects automatically
  };
}

function updateDeviceStateBadge(state) {
  const devBadge = document.getElementById('deviceStatusBadge');
  if (devBadge) {
    devBadge.innerHTML = `<span class="status-dot"></span> ${state.deviceId} (ONLINE)`;
  }
}

function handlePipelineStep(data) {
  switch (data.step) {
    case 'iot_captured':
      setPipelineNodeState('node-button', 'active');
      setConnectorActive('conn-button-gateway');
      break;
    case 'uploading':
      setPipelineNodeState('node-gateway', 'active');
      setConnectorActive('conn-gateway-s3');
      break;
    case 'upload_confirmed':
      setPipelineNodeState('node-s3-raw', 'success');
      setConnectorActive('conn-s3-lambda');
      if (iotSim) iotSim.setLedState('CONFIRMED');
      break;
    case 'lambda_invoking':
      setPipelineNodeState('node-lambda', 'active');
      break;
    case 'thumbnail_ready':
      setPipelineNodeState('node-lambda', 'success');
      setConnectorActive('conn-lambda-thumb');
      setPipelineNodeState('node-s3-thumb', 'success');
      break;
  }
}

/* ==========================================================================
   Pipeline Flow Animation
   ========================================================================== */
function setPipelineNodeState(nodeId, stateClass) {
  const el = document.getElementById(nodeId);
  if (!el) return;
  el.classList.remove('active', 'success');
  if (stateClass) {
    el.classList.add(stateClass);
    // Auto reset after 4.5 seconds if it's success/active
    setTimeout(() => {
      el.classList.remove('active', 'success');
    }, 4500);
  }
}

function setConnectorActive(connId) {
  const el = document.getElementById(connId);
  if (!el) return;
  el.classList.add('active');
  setTimeout(() => el.classList.remove('active'), 3500);
}

function logConsole(type, message) {
  const box = document.getElementById('cloudConsoleBox');
  if (!box) return;

  const now = new Date();
  const timeStr = now.toTimeString().substring(0, 8);

  const line = document.createElement('div');
  line.className = 'console-line';

  let tagClass = 'info';
  let tagText = 'INFO';
  if (type === 'success') { tagClass = 'success'; tagText = 'CONFIRM'; }
  else if (type === 'lambda') { tagClass = 'lambda'; tagText = 'LAMBDA'; }
  else if (type === 'warn') { tagClass = 'warn'; tagText = 'WARN'; }
  else if (type === 'iot') { tagClass = 'info'; tagText = 'IOT-EDGE'; }

  line.innerHTML = `
    <span class="console-ts">${timeStr}</span>
    <span class="console-tag ${tagClass}">${tagText}</span>
    <span class="console-msg">${escapeHtml(message)}</span>
  `;

  box.appendChild(line);
  box.scrollTop = box.scrollHeight;
}

/* ==========================================================================
   Gallery Loading & Rendering
   ========================================================================== */
function resolveUrl(url) {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) {
    return url;
  }
  return url.startsWith('/') ? url.slice(1) : url;
}

function addGalleryItemLocally(item) {
  if (!currentItems.some(i => i.id === item.id)) {
    currentItems.unshift(item);
    try {
      const localSaved = JSON.parse(localStorage.getItem('iot_gallery_items') || '[]');
      localSaved.unshift(item);
      localStorage.setItem('iot_gallery_items', JSON.stringify(localSaved.slice(0, 30)));
    } catch (e) {}
    renderGallery();
    loadMetrics();
  }
}

async function loadGallery() {
  try {
    const res = await fetch('/api/gallery');
    if (!res.ok) throw new Error('API offline');
    const data = await res.json();
    if (data.success) {
      currentItems = data.items;
      renderGallery();
      return;
    }
  } catch (e) {
    // Static / GitHub Pages fallback
    try {
      const resFallback = await fetch('storage/database.json');
      if (resFallback.ok) {
        const fallbackItems = await resFallback.json();
        let stored = [];
        try { stored = JSON.parse(localStorage.getItem('iot_gallery_items') || '[]'); } catch (err) {}
        const merged = [...stored];
        fallbackItems.forEach(it => {
          if (!merged.some(m => m.id === it.id)) merged.push(it);
        });
        currentItems = merged;
        renderGallery();
        loadMetrics();
      }
    } catch (err) {
      console.warn("Could not load database.json fallback", err);
    }
  }
}

async function loadMetrics() {
  try {
    const res = await fetch('/api/cloud/stats');
    if (res.ok) {
      const data = await res.json();
      if (data.success) {
        document.getElementById('metricTotalEvents').textContent = data.totalEvents;
        document.getElementById('metricSavedPct').textContent = `${data.overallSavingsPercent}%`;
        document.getElementById('metricSavedBytes').textContent = formatBytes(data.bytesSaved);
        document.getElementById('metricAvgLambda').textContent = `${data.avgLambdaDurationMs} ms`;
        return;
      }
    }
  } catch (e) {}

  if (currentItems && currentItems.length > 0) {
    const total = currentItems.length;
    let totalOrig = 0, totalThumb = 0, totalDuration = 0;
    currentItems.forEach(it => {
      totalOrig += (it.originalSize && it.originalSize.bytes) || 34000;
      totalThumb += (it.thumbnailSize && it.thumbnailSize.bytes) || 5000;
      totalDuration += it.lambdaDurationMs || 35;
    });
    const bytesSaved = Math.max(0, totalOrig - totalThumb);
    const savingsPct = totalOrig > 0 ? ((bytesSaved / totalOrig) * 100).toFixed(1) : '85.0';
    const avgDuration = Math.round(totalDuration / total);
    const elTotal = document.getElementById('metricTotalEvents');
    const elSavedPct = document.getElementById('metricSavedPct');
    const elSavedBytes = document.getElementById('metricSavedBytes');
    const elAvgLambda = document.getElementById('metricAvgLambda');
    if (elTotal) elTotal.textContent = total;
    if (elSavedPct) elSavedPct.textContent = `${savingsPct}%`;
    if (elSavedBytes) elSavedBytes.textContent = formatBytes(bytesSaved);
    if (elAvgLambda) elAvgLambda.textContent = `${avgDuration} ms`;
  }
}

function renderGallery() {
  const grid = document.getElementById('galleryGrid');
  if (!grid) return;

  const filtered = currentItems.filter(item => {
    if (currentFilter === 'all') return true;
    return item.trigger === currentFilter;
  });

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div class="empty-gallery">
        <div class="empty-icon">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <rect x="3" y="3" width="18" height="18" rx="2"/>
            <circle cx="8.5" cy="8.5" r="1.5"/>
            <path d="m21 15-5-5L5 21"/>
          </svg>
        </div>
        <h3 style="font-weight: 700; color: #fff;">No IoT Events Recorded Yet</h3>
        <p style="color: var(--text-muted); font-size: 0.85rem; max-width: 400px;">
          Press the big red tactile button on the camera panel (or press Spacebar) to capture an event. An LED will confirm the upload, and AWS Lambda will auto-generate the thumbnail!
        </p>
      </div>
    `;
    return;
  }

  grid.innerHTML = filtered.map(item => `
    <div class="gallery-card" id="card-${item.id}">
      <div class="gallery-card-thumb-wrap" onclick="openCompareModal('${item.id}')">
        <img class="gallery-card-thumb" src="${resolveUrl(item.thumbnailUrl)}" alt="${item.filename}" loading="lazy" onerror="if(this.src && !this.src.endsWith('${resolveUrl(item.thumbnail)}')) { this.src='storage/thumbnails/${item.thumbnail}'; }" />
        <span class="card-badge">⚡ -${item.savingsPercent}%</span>
        <span class="card-trigger-badge">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
          ${formatTrigger(item.trigger)}
        </span>
      </div>

      <div class="card-body">
        <div class="card-title-row">
          <div class="card-title" title="${item.filename}">${item.filename}</div>
          <div class="dominant-color-indicator" style="background-color: ${item.dominantColor};" title="Dominant Color: ${item.dominantColor}"></div>
        </div>

        <div class="card-stats-grid">
          <div class="stat-item">
            <span class="stat-label">Lambda Runtime</span>
            <span class="stat-val" style="color: #c084fc;">${item.lambdaDurationMs} ms</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Thumbnail Size</span>
            <span class="stat-val" style="color: #34d399;">${item.thumbnailSize.formatted || 'N/A'}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Original Size</span>
            <span class="stat-val">${item.originalSize.formatted || 'N/A'}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Billed Memory</span>
            <span class="stat-val">128 MB</span>
          </div>
        </div>

        <div class="card-footer">
          <span class="card-time">${item.createdAtFormatted}</span>
          <div class="card-actions">
            <button class="icon-btn" title="Compare Original vs Thumbnail" onclick="openCompareModal('${item.id}')">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="2" y="3" width="20" height="18" rx="2"/>
                <line x1="12" y1="3" x2="12" y2="21"/>
              </svg>
            </button>
            <button class="icon-btn" title="View CloudWatch Lambda Logs" onclick="openLogsModal('${item.id}')">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="4 17 10 11 4 5"/>
                <line x1="12" y1="19" x2="20" y2="19"/>
              </svg>
            </button>
            <a class="icon-btn" title="Download Raw Image" href="${resolveUrl(item.rawUrl)}" download>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
            </a>
            <button class="icon-btn danger" title="Delete" onclick="deleteItem('${item.id}')">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  `).join('');
}

function formatTrigger(trigger) {
  if (trigger === 'button_press') return 'Hardware Button';
  if (trigger === 'manual_upload') return 'File Upload';
  if (trigger === 'motion_sensor') return 'Motion Detect';
  return trigger;
}

/* ==========================================================================
   Modals & Details
   ========================================================================== */
function openCompareModal(itemId) {
  const item = currentItems.find(i => i.id === itemId);
  if (!item) return;

  const modal = document.getElementById('compareModal');
  const title = document.getElementById('compareModalTitle');
  const rawImg = document.getElementById('compareRawImg');
  const thumbImg = document.getElementById('compareThumbImg');
  const rawMeta = document.getElementById('compareRawMeta');
  const thumbMeta = document.getElementById('compareThumbMeta');

  title.textContent = `Comparison: ${item.filename}`;
  const rUrl = resolveUrl(item.rawUrl);
  const tUrl = resolveUrl(item.thumbnailUrl);
  rawImg.onerror = () => { if (rawImg.src && !rawImg.src.endsWith(`storage/raw/${item.filename}`)) rawImg.src = `storage/raw/${item.filename}`; };
  thumbImg.onerror = () => { if (thumbImg.src && !thumbImg.src.endsWith(`storage/thumbnails/${item.thumbnail}`)) thumbImg.src = `storage/thumbnails/${item.thumbnail}`; };
  rawImg.src = rUrl;
  thumbImg.src = tUrl;

  rawMeta.innerHTML = `
    <div><strong>Storage Location:</strong> s3://iot-image-gallery-raw/</div>
    <div><strong>Resolution:</strong> ${item.originalSize.width} × ${item.originalSize.height} px</div>
    <div><strong>File Size:</strong> ${item.originalSize.formatted} (${item.originalSize.bytes.toLocaleString()} bytes)</div>
    <div><strong>Upload Latency:</strong> ${item.uploadDurationMs} ms (LED: CONFIRMED GREEN)</div>
  `;

  thumbMeta.innerHTML = `
    <div><strong>Storage Location:</strong> s3://iot-image-gallery-thumbnails/</div>
    <div><strong>Resolution:</strong> ${item.thumbnailSize.width} × ${item.thumbnailSize.height} px</div>
    <div><strong>File Size:</strong> ${item.thumbnailSize.formatted} (${item.thumbnailSize.bytes.toLocaleString()} bytes)</div>
    <div><strong>Storage Savings:</strong> <span style="color:#34d399;font-weight:bold;">${item.savingsPercent}% Reduction</span></div>
    <div><strong>Lambda Execution:</strong> ${item.lambdaDurationMs} ms (Billed: ${item.billedDurationMs} ms)</div>
  `;

  modal.classList.add('open');
}

function openLogsModal(itemId) {
  const item = currentItems.find(i => i.id === itemId);
  if (!item) return;

  const modal = document.getElementById('logsModal');
  const term = document.getElementById('cloudWatchTerminal');
  const title = document.getElementById('logsModalTitle');

  title.textContent = `AWS CloudWatch Logs - ${item.filename}`;

  const logs = (item.cloudWatchLogs && item.cloudWatchLogs.length > 0) 
    ? item.cloudWatchLogs.join('\n')
    : `2026-10-02T23:59:00.000Z START RequestId: 00000000-0000-0000-0000-000000000000 Version: $LATEST\nNo detailed logs stored for this execution.`;

  term.textContent = logs;
  modal.classList.add('open');
}

function openAwsSpecModal() {
  const modal = document.getElementById('awsSpecModal');
  if (modal) modal.classList.add('open');
}

function closeModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) m.classList.remove('open');
}

/* ==========================================================================
   Global Actions & Delete
   ========================================================================== */
function setupGlobalActions() {
  // Filter pills
  document.querySelectorAll('.filter-pills .pill-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-pills .pill-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.getAttribute('data-filter');
      renderGallery();
    });
  });

  // Burst capture simulation
  const burstBtn = document.getElementById('burstCaptureBtn');
  if (burstBtn) {
    burstBtn.addEventListener('click', async () => {
      showToast("Starting Burst Capture (3 Events)...");
      for (let i = 1; i <= 3; i++) {
        if (iotSim) {
          iotSim.triggerCapture('button_press');
        }
        await new Promise(r => setTimeout(r, 1200));
      }
    });
  }

  // Clear Gallery
  const clearBtn = document.getElementById('clearGalleryBtn');
  if (clearBtn) {
    clearBtn.addEventListener('click', async () => {
      if (confirm("Are you sure you want to clear all images from both Raw and Thumbnail storage?")) {
        try {
          await fetch('/api/gallery/clear', { method: 'POST' });
          showToast("Gallery and buckets cleared");
        } catch (e) {
          alert("Error clearing gallery: " + e.message);
        }
      }
    });
  }

  // AWS Architecture button
  const awsBtn = document.getElementById('btnOpenAwsSpec');
  if (awsBtn) {
    awsBtn.addEventListener('click', openAwsSpecModal);
  }

  // Close modals on clicking outside or ESC
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-backdrop.open').forEach(m => m.classList.remove('open'));
    }
  });

  document.querySelectorAll('.modal-backdrop').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.classList.remove('open');
      }
    });
  });
}

async function deleteItem(id) {
  if (confirm("Delete this event, raw image, and thumbnail?")) {
    try {
      const res = await fetch(`/api/gallery/${id}`, { method: 'DELETE' });
      const data = await res.json();
      if (data.success) {
        showToast("Item deleted");
      }
    } catch (e) {
      alert("Error: " + e.message);
    }
  }
}

/* ==========================================================================
   Utilities
   ========================================================================== */
function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/[&<>'"]/g, 
    tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
  );
}

function showToast(message) {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#34d399" stroke-width="2.5">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
    <span>${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

/* ==========================================================================
   AWS Cloud Connection & Configuration Manager
   ========================================================================== */
let cloudStatusData = null;

async function loadCloudStatus(notify = false) {
  try {
    const res = await fetch('/api/cloud/status');
    const data = await res.json();
    if (data.success && data.status) {
      cloudStatusData = data.status;
      updateCloudStatusUI(data.status);
      if (notify) showToast("AWS Status Refreshed");
    }
  } catch (err) {
    console.warn("Could not fetch cloud status:", err);
  }
}

function updateCloudStatusUI(status) {
  const dot = document.getElementById('awsStatusDot');
  const text = document.getElementById('awsStatusText');
  const banner = document.getElementById('awsModalStatusBanner');
  const heading = document.getElementById('awsModalStatusHeading');
  const sub = document.getElementById('awsModalStatusSub');

  const isConnected = status.connected && status.mode !== 'LOCAL_SIMULATION';

  if (dot && text) {
    if (isConnected) {
      dot.style.background = '#00ff66';
      dot.style.boxShadow = '0 0 10px #00ff66';
      text.textContent = `AWS: Active (${status.region || 'cloud'})`;
    } else {
      dot.style.background = 'var(--accent-amber)';
      dot.style.boxShadow = 'none';
      text.textContent = 'AWS: Local Sim';
    }
  }

  if (banner && heading && sub) {
    if (isConnected) {
      banner.className = 'cloud-status-banner connected';
      heading.textContent = `Mode: AWS Cloud Active (Account: ${status.accountId || 'Connected'})`;
      sub.innerHTML = `Region: <strong style="color:#fff;">${escapeHtml(status.region)}</strong> | S3 Raw: <strong style="color:#38bdf8;">${escapeHtml(status.rawBucket || 'Configured')}</strong> | Latency: <strong>${status.latencyMs || 0} ms</strong>`;
    } else {
      banner.className = 'cloud-status-banner disconnected';
      heading.textContent = 'Mode: Local Simulation';
      sub.textContent = status.error ? `AWS Error: ${status.error}` : 'Running with local storage and Python serverless emulator.';
    }
  }

  // Populate form fields if available
  const regEl = document.getElementById('cfgAwsRegion');
  const rawEl = document.getElementById('cfgAwsRawBucket');
  const thumbEl = document.getElementById('cfgAwsThumbBucket');
  const lambdaEl = document.getElementById('cfgAwsLambda');
  const toggleEl = document.getElementById('cfgAwsModeToggle');

  if (regEl && status.region) regEl.value = status.region;
  if (rawEl && status.rawBucket && !rawEl.value) rawEl.value = status.rawBucket;
  if (thumbEl && status.thumbnailsBucket && !thumbEl.value) thumbEl.value = status.thumbnailsBucket;
  if (lambdaEl && status.lambdaFunction && !lambdaEl.value) lambdaEl.value = status.lambdaFunction;
  if (toggleEl) toggleEl.checked = status.mode !== 'LOCAL_SIMULATION';
}

function openAwsConnectModal() {
  const modal = document.getElementById('awsConnectModal');
  if (modal) {
    modal.classList.add('open');
    loadCloudStatus();
  }
}

function setupAwsConnectHandlers() {
  // Open modal buttons
  const btnOpen = document.getElementById('btnOpenAwsConnect');
  const badge = document.getElementById('awsStatusBadge');
  if (btnOpen) btnOpen.addEventListener('click', openAwsConnectModal);
  if (badge) badge.addEventListener('click', openAwsConnectModal);

  // Refresh status button
  const btnRefresh = document.getElementById('btnRefreshAwsStatus');
  if (btnRefresh) {
    btnRefresh.addEventListener('click', () => loadCloudStatus(true));
  }

  // Tabs inside modal
  document.querySelectorAll('.modal-tabs .modal-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.modal-tabs .modal-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('#awsConnectModal .tab-pane').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      const targetId = tab.getAttribute('data-tab');
      const pane = document.getElementById(targetId);
      if (pane) pane.classList.add('active');
    });
  });

  // Secret key visibility toggle
  const toggleEye = document.getElementById('toggleSecretKeyVisibility');
  const secretInput = document.getElementById('cfgAwsSecretKey');
  if (toggleEye && secretInput) {
    toggleEye.addEventListener('click', () => {
      if (secretInput.type === 'password') {
        secretInput.type = 'text';
      } else {
        secretInput.type = 'password';
      }
    });
  }

  // Test Connection
  const btnTest = document.getElementById('btnTestAwsConnection');
  const resultCard = document.getElementById('testResultCard');
  if (btnTest) {
    btnTest.addEventListener('click', async () => {
      const ak = document.getElementById('cfgAwsAccessKey').value.trim();
      const sk = document.getElementById('cfgAwsSecretKey').value.trim();
      const st = (document.getElementById('cfgAwsSessionToken')?.value || '').trim();
      const reg = document.getElementById('cfgAwsRegion').value;
      const raw = document.getElementById('cfgAwsRawBucket').value.trim();
      const thumb = document.getElementById('cfgAwsThumbBucket').value.trim();
      const lam = document.getElementById('cfgAwsLambda').value.trim();

      const originalHtml = btnTest.innerHTML;
      btnTest.disabled = true;
      btnTest.innerHTML = `
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
          <circle cx="12" cy="12" r="10" stroke-dasharray="32" stroke-linecap="round"/>
        </svg>
        <span>Testing AWS STS...</span>
      `;

      try {
        const resp = await fetch('/api/cloud/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            accessKeyId: ak,
            secretAccessKey: sk,
            sessionToken: st,
            region: reg,
            rawBucket: raw,
            thumbnailsBucket: thumb,
            lambdaFunction: lam
          })
        });
        const res = await resp.json();

        if (res.connected && res.success) {
          resultCard.className = 'test-result-card success';
          resultCard.innerHTML = `
            <div style="font-weight: 700; color: #34d399; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.4rem;">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
              <span>AWS Credentials Authenticated Successfully! (${res.latencyMs} ms)</span>
            </div>
            <div class="test-result-row">
              <span style="color: var(--text-muted);">AWS Account ID:</span>
              <span style="font-family: var(--font-mono); font-weight: 600;">${escapeHtml(res.accountId || 'Verified')}</span>
            </div>
            <div class="test-result-row">
              <span style="color: var(--text-muted);">IAM User / Role ARN:</span>
              <span style="font-family: var(--font-mono); font-size: 0.75rem;">${escapeHtml(res.arn || 'Verified')}</span>
            </div>
            <div class="test-result-row">
              <span style="color: var(--text-muted);">S3 Raw Bucket (${escapeHtml(res.rawBucket?.name || 'Not specified')}):</span>
              <span class="badge-pill ${res.rawBucket?.accessible ? 'success' : 'danger'}">
                ${res.rawBucket?.accessible ? '✓ Accessible' : (res.rawBucket?.name ? '✕ Unreachable / Not Created' : 'Not Configured')}
              </span>
            </div>
            <div class="test-result-row">
              <span style="color: var(--text-muted);">S3 Thumbnails Bucket (${escapeHtml(res.thumbnailsBucket?.name || 'Not specified')}):</span>
              <span class="badge-pill ${res.thumbnailsBucket?.accessible ? 'success' : 'danger'}">
                ${res.thumbnailsBucket?.accessible ? '✓ Accessible' : (res.thumbnailsBucket?.name ? '✕ Unreachable / Not Created' : 'Not Configured')}
              </span>
            </div>
            <div class="test-result-row">
              <span style="color: var(--text-muted);">Lambda Function (${escapeHtml(res.lambdaFunction?.name || 'Not specified')}):</span>
              <span class="badge-pill ${res.lambdaFunction?.accessible ? 'success' : 'danger'}">
                ${res.lambdaFunction?.accessible ? '✓ Deployed & Ready' : (res.lambdaFunction?.name ? '✕ Not Found' : 'Not Configured')}
              </span>
            </div>
          `;
          showToast("AWS Authentication Passed!");
        } else {
          resultCard.className = 'test-result-card error';
          resultCard.innerHTML = `
            <div style="font-weight: 700; color: #fda4af; margin-bottom: 0.4rem; display: flex; align-items: center; gap: 0.4rem;">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              <span>Connection Failed</span>
            </div>
            <div style="font-size: 0.78rem; color: #fecdd3; line-height: 1.5;">${escapeHtml(res.error || 'Unknown error during AWS STS verification')}</div>
          `;
        }
      } catch (err) {
        resultCard.className = 'test-result-card error';
        resultCard.innerHTML = `<div style="color: #fda4af;">Network error: ${escapeHtml(err.message)}</div>`;
      } finally {
        btnTest.disabled = false;
        btnTest.innerHTML = originalHtml;
      }
    });
  }

  // Save Configuration
  const btnSave = document.getElementById('btnSaveAwsConfig');
  if (btnSave) {
    btnSave.addEventListener('click', async () => {
      const ak = document.getElementById('cfgAwsAccessKey').value.trim();
      const sk = document.getElementById('cfgAwsSecretKey').value.trim();
      const st = (document.getElementById('cfgAwsSessionToken')?.value || '').trim();
      const reg = document.getElementById('cfgAwsRegion').value;
      const raw = document.getElementById('cfgAwsRawBucket').value.trim();
      const thumb = document.getElementById('cfgAwsThumbBucket').value.trim();
      const lam = document.getElementById('cfgAwsLambda').value.trim();
      const enabled = document.getElementById('cfgAwsModeToggle').checked;

      const originalHtml = btnSave.innerHTML;
      btnSave.disabled = true;
      btnSave.innerHTML = `<span>Saving to .env...</span>`;

      try {
        const resp = await fetch('/api/cloud/configure', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            accessKeyId: ak,
            secretAccessKey: sk,
            sessionToken: st,
            region: reg,
            rawBucket: raw,
            thumbnailsBucket: thumb,
            lambdaFunction: lam,
            enabled: enabled
          })
        });
        const res = await resp.json();
        if (res.success) {
          updateCloudStatusUI(res.status);
          showToast(enabled ? "AWS Cloud Configuration Active!" : "Local Simulation Mode Active!");
          setTimeout(() => closeModal('awsConnectModal'), 1200);
        } else {
          alert("Error saving configuration");
        }
      } catch (e) {
        alert("Error saving config: " + e.message);
      } finally {
        btnSave.disabled = false;
        btnSave.innerHTML = originalHtml;
      }
    });
  }
}
