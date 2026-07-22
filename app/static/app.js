const state = {
  dashboard: null,
  devices: [],
  captures: [],
  selectedDeviceId: null,
  calibration: null,
  selectedCapture: null,
  selectedAsset: "ndvi",
  currentView: "dashboard",
  liveSource: "device",
  liveDeviceId: null,
  devicePreview: null,
  devicePreviewSequence: null,
  devicePreviewPoll: null,
  devicePreviewKeepalive: null,
  fieldCaptureCommand: null,
  fieldCaptureResult: null,
  fieldCapturePoll: null,
  webcamStatus: null,
  webcamSnapshots: [],
  webcamPoll: null,
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

function iconRefresh() {
  if (window.lucide) {
    window.lucide.createIcons({
      attrs: {
        "aria-hidden": "true",
      },
    });
  }
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();
  if (!response.ok) {
    const detail = payload?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : detail?.message || payload?.message || `Request failed (${response.status})`;
    throw new Error(message);
  }
  return payload;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function percent(value, digits = 0) {
  if (value === null || value === undefined) return "-";
  return `${(Number(value) * 100).toFixed(digits)}%`;
}

function ndvi(value) {
  if (value === null || value === undefined) return "-";
  return Number(value).toFixed(2);
}

function dateLabel(value, options = {}) {
  if (!value) return "Never";
  const includeYear = options.year === true;
  const { year: _yearFlag, ...intlOptions } = options;
  return new Intl.DateTimeFormat(undefined, {
    day: "2-digit",
    month: "short",
    year: includeYear ? "numeric" : undefined,
    ...intlOptions,
  }).format(new Date(value));
}

function timeLabel(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function relativeTime(value) {
  if (!value) return "Never";
  const delta = Date.now() - new Date(value).getTime();
  const minutes = Math.max(0, Math.round(delta / 60000));
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  return `${Math.round(hours / 24)} d ago`;
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("is-visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("is-visible"), 2800);
}

function setBackendState(status) {
  const dot = $("#backend-dot");
  dot.classList.toggle("is-online", status === "online");
  dot.classList.toggle("is-offline", status === "offline");
  $("#backend-state").textContent = status === "online" ? "Live" : "Offline";
}

async function refreshAll() {
  const button = $("#refresh-button");
  button.classList.add("is-active");
  try {
    const dashboard = await api("/api/dashboard?days=14");
    state.dashboard = dashboard;
    state.devices = dashboard.devices;
    if (!state.selectedDeviceId && state.devices.length) {
      state.selectedDeviceId = state.devices[0].id;
    }
    setBackendState("online");
    renderDashboard();
    renderDeviceRail();
    renderDeviceTable();
    populateDeviceSelects();
  } catch (error) {
    setBackendState("offline");
    showToast(error.message);
  } finally {
    window.setTimeout(() => button.classList.remove("is-active"), 350);
    iconRefresh();
  }
}

function renderDashboard() {
  if (!state.dashboard) return;
  const { summary, trend, latest, devices } = state.dashboard;
  const metrics = [
    {
      label: "Captures today",
      value: String(summary.captures_today),
      foot: `${latest.length} recent observations`,
      icon: "camera",
      tone: "",
    },
    {
      label: "Mean NDVI",
      value: ndvi(summary.mean_ndvi),
      foot: "Across selected period",
      icon: "sprout",
      tone: "positive",
    },
    {
      label: "Quality pass",
      value: percent(summary.quality_pass_rate),
      foot: summary.quality_pass_rate >= 0.95 ? "Within target" : "Needs review",
      icon: "shield-check",
      tone: summary.quality_pass_rate >= 0.95 ? "positive" : "warning",
    },
    {
      label: "Nodes online",
      value: `${summary.online_devices}/${summary.total_devices}`,
      foot: `${summary.queued_uploads} queued uploads`,
      icon: "wifi",
      tone: summary.online_devices === summary.total_devices ? "positive" : "warning",
    },
  ];

  $("#metric-grid").innerHTML = metrics
    .map(
      (metric) => `
        <article class="metric-item">
          <div class="metric-topline">
            <span>${escapeHtml(metric.label)}</span>
            <span class="metric-icon"><i data-lucide="${metric.icon}"></i></span>
          </div>
          <strong class="metric-value">${escapeHtml(metric.value)}</strong>
          <span class="metric-foot ${metric.tone}">
            <i data-lucide="${metric.tone === "warning" ? "alert-circle" : "activity"}"></i>
            ${escapeHtml(metric.foot)}
          </span>
        </article>
      `,
    )
    .join("");

  renderTrend(trend);
  $("#health-list").innerHTML = devices
    .map(
      (device) => `
        <div class="health-item">
          <span class="device-row-state ${escapeHtml(device.status)}"></span>
          <div class="health-copy">
            <strong>${escapeHtml(device.name)}</strong>
            <span>${escapeHtml(device.site_name)}</span>
          </div>
          <div class="health-meta">
            <strong>${device.wifi_rssi_dbm === null ? "No link" : `${device.wifi_rssi_dbm} dBm`}</strong>
            <span>${escapeHtml(relativeTime(device.last_seen_at))}</span>
          </div>
        </div>
      `,
    )
    .join("");

  $("#latest-captures").innerHTML = latest.length
    ? latest.map(captureCard).join("")
    : `<div class="empty-state">No captures in this period.</div>`;

  bindCaptureCards($("#latest-captures"));
  const queue = summary.queued_uploads;
  $("#rail-queue").textContent = String(queue);
  $("#queue-progress").style.width = `${Math.min(100, queue * 4)}%`;
  iconRefresh();
}

function renderTrend(points) {
  const target = $("#trend-chart");
  if (!points.length) {
    target.innerHTML = `<div class="chart-empty">No NDVI observations.</div>`;
    return;
  }

  const width = 760;
  const height = 250;
  const pad = { left: 38, right: 12, top: 16, bottom: 28 };
  const chartWidth = width - pad.left - pad.right;
  const chartHeight = height - pad.top - pad.bottom;
  const yMin = 0;
  const yMax = 0.9;
  const x = (index) =>
    pad.left + (points.length === 1 ? chartWidth / 2 : (index / (points.length - 1)) * chartWidth);
  const y = (value) => pad.top + ((yMax - value) / (yMax - yMin)) * chartHeight;

  const linePoints = points
    .map((point, index) => `${x(index).toFixed(1)},${y(point.mean_ndvi).toFixed(1)}`)
    .join(" ");
  const areaPoints = [
    `${x(0)},${pad.top + chartHeight}`,
    ...points.map(
      (point, index) => `${x(index).toFixed(1)},${y(point.healthy_fraction).toFixed(1)}`,
    ),
    `${x(points.length - 1)},${pad.top + chartHeight}`,
  ].join(" ");

  const grids = [0.2, 0.4, 0.6, 0.8]
    .map(
      (value) => `
        <line class="chart-grid-line" x1="${pad.left}" y1="${y(value)}"
          x2="${width - pad.right}" y2="${y(value)}"></line>
        <text class="chart-label" x="3" y="${y(value) + 3}">${value.toFixed(1)}</text>
      `,
    )
    .join("");

  const labels = points
    .map((point, index) => {
      if (points.length > 8 && index % 2 !== 0 && index !== points.length - 1) return "";
      return `<text class="chart-label" text-anchor="middle" x="${x(index)}" y="${height - 7}">
        ${escapeHtml(dateLabel(`${point.date}T00:00:00Z`))}
      </text>`;
    })
    .join("");

  const circles = points
    .map(
      (point, index) => `
        <circle class="chart-point" cx="${x(index)}" cy="${y(point.mean_ndvi)}" r="4">
          <title>${point.date}: mean NDVI ${point.mean_ndvi.toFixed(2)}</title>
        </circle>
      `,
    )
    .join("");

  target.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Mean NDVI by date">
      ${grids}
      <polygon class="chart-area" points="${areaPoints}"></polygon>
      <polyline class="chart-line" points="${linePoints}"></polyline>
      ${circles}
      ${labels}
    </svg>
  `;
}

function renderDeviceRail() {
  const query = $("#device-search").value.trim().toLowerCase();
  const devices = state.devices.filter(
    (device) =>
      !query ||
      device.name.toLowerCase().includes(query) ||
      device.site_name.toLowerCase().includes(query),
  );
  $("#device-count").textContent = String(devices.length);
  $("#device-list").innerHTML = devices
    .map(
      (device) => `
        <button class="device-row ${device.id === state.selectedDeviceId ? "is-selected" : ""}"
          type="button" data-device-id="${escapeHtml(device.id)}">
          <span class="device-row-state ${escapeHtml(device.status)}"></span>
          <span class="device-row-copy">
            <strong>${escapeHtml(device.name)}</strong>
            <span>${escapeHtml(device.site_name)}</span>
          </span>
          <span class="signal-value">${device.wifi_rssi_dbm === null ? "-" : device.wifi_rssi_dbm}</span>
        </button>
      `,
    )
    .join("");

  $$(".device-row", $("#device-list")).forEach((button) => {
    button.addEventListener("click", async () => {
      state.selectedDeviceId = button.dataset.deviceId;
      renderDeviceRail();
      $("#calibration-device-select").value = state.selectedDeviceId;
      await loadCalibration(state.selectedDeviceId);
      switchView("calibration");
    });
  });
}

function captureCard(capture) {
  return `
    <article class="capture-card" tabindex="0" data-capture-id="${escapeHtml(capture.id)}">
      <div class="capture-card-image">
        <img src="${escapeHtml(capture.assets.ndvi_thumb)}"
          alt="NDVI heatmap from ${escapeHtml(capture.site_name)}">
        <div class="capture-card-overlay">
          <span class="status-badge ${escapeHtml(capture.quality_state)}">
            ${escapeHtml(capture.quality_state)}
          </span>
        </div>
      </div>
      <div class="capture-card-body">
        <div class="capture-card-title">
          <strong>${escapeHtml(capture.device_name)}</strong>
          <time>${escapeHtml(timeLabel(capture.captured_at))}</time>
        </div>
        <span class="capture-card-site">${escapeHtml(capture.site_name)} / ${escapeHtml(dateLabel(capture.captured_at))}</span>
        <div class="capture-metrics">
          <div><span>Mean NDVI</span><strong>${ndvi(capture.ndvi.mean)}</strong></div>
          <div><span>Healthy</span><strong>${percent(capture.ndvi.healthy_fraction)}</strong></div>
          <div><span>Sync</span><strong>${capture.sync_delta_ms === null ? "-" : `${Math.round(capture.sync_delta_ms)} ms`}</strong></div>
        </div>
      </div>
    </article>
  `;
}

function bindCaptureCards(root) {
  $$(".capture-card", root).forEach((card) => {
    const open = () => openCapture(card.dataset.captureId);
    card.addEventListener("click", open);
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        open();
      }
    });
  });
}

async function loadCaptures() {
  const params = new URLSearchParams();
  const from = $("#date-from").value;
  const to = $("#date-to").value;
  const device = $("#capture-device-filter").value;
  const status = $("#capture-status-filter").value;
  if (from) params.set("date_from", from);
  if (to) params.set("date_to", to);
  if (device) params.set("device_id", device);
  if (status) params.set("status", status);
  params.set("limit", "300");

  try {
    state.captures = await api(`/api/captures?${params.toString()}`);
    renderCaptureArchive();
  } catch (error) {
    showToast(error.message);
  }
}

function renderCaptureArchive() {
  const groups = new Map();
  for (const capture of state.captures) {
    if (!groups.has(capture.date_key)) groups.set(capture.date_key, []);
    groups.get(capture.date_key).push(capture);
  }

  const meanValue = state.captures.length
    ? state.captures.reduce((sum, item) => sum + item.ndvi.mean, 0) / state.captures.length
    : null;
  $("#archive-summary").innerHTML = `
    <span><strong>${state.captures.length}</strong> captures</span>
    <span><strong>${groups.size}</strong> dates</span>
    <span><strong>${ndvi(meanValue)}</strong> mean NDVI</span>
  `;

  const entries = Array.from(groups.entries()).sort(([a], [b]) => b.localeCompare(a));
  $("#capture-archive").innerHTML = entries.length
    ? entries
        .map(
          ([key, captures]) => `
            <section class="date-group">
              <div class="date-group-heading">
                <h2>${escapeHtml(dateLabel(`${key}T00:00:00Z`, { year: true }))}</h2>
                <span>${captures.length} observation${captures.length === 1 ? "" : "s"}</span>
              </div>
              <div class="capture-grid">${captures.map(captureCard).join("")}</div>
            </section>
          `,
        )
        .join("")
    : `<div class="empty-state">No captures match the selected dates.</div>`;
  bindCaptureCards($("#capture-archive"));
  iconRefresh();
}

function signalLevel(rssi) {
  if (rssi === null || rssi === undefined) return 0;
  if (rssi >= -60) return 4;
  if (rssi >= -68) return 3;
  if (rssi >= -76) return 2;
  return 1;
}

function renderDeviceTable() {
  $("#device-table-body").innerHTML = state.devices
    .map(
      (device) => `
        <tr>
          <td>
            <div class="table-primary">
              <strong>${escapeHtml(device.name)}</strong>
              <span>${escapeHtml(device.site_name)}</span>
            </div>
          </td>
          <td>
            <span class="status-badge ${escapeHtml(device.status)}">${escapeHtml(device.status)}</span>
            <div class="table-muted">${escapeHtml(device.wifi_ssid || "No active Wi-Fi")}</div>
          </td>
          <td>
            <div class="table-signal">
              <span class="signal-bars" data-level="${signalLevel(device.wifi_rssi_dbm)}">
                <i></i><i></i><i></i><i></i>
              </span>
              <span>${device.wifi_rssi_dbm === null ? "-" : `${device.wifi_rssi_dbm} dBm`}</span>
            </div>
          </td>
          <td>${device.queue_depth}</td>
          <td>${Number(device.storage_used_percent).toFixed(1)}%</td>
          <td>${device.battery_percent === null ? "-" : `${Math.round(device.battery_percent)}%`}</td>
          <td>${escapeHtml(relativeTime(device.last_seen_at))}</td>
          <td>
            <div class="table-actions">
              <button class="icon-button table-capture-now" type="button"
                data-device-id="${escapeHtml(device.id)}" title="Capture now">
                <i data-lucide="camera"></i>
              </button>
              <button class="icon-button table-calibration" type="button"
                data-device-id="${escapeHtml(device.id)}" title="Open calibration">
                <i data-lucide="settings-2"></i>
              </button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");

  $$(".table-calibration").forEach((button) => {
    button.addEventListener("click", async () => {
      state.selectedDeviceId = button.dataset.deviceId;
      $("#calibration-device-select").value = state.selectedDeviceId;
      await loadCalibration(state.selectedDeviceId);
      switchView("calibration");
    });
  });
  $$(".table-capture-now").forEach((button) => {
    button.addEventListener("click", () =>
      requestCaptureNow(button.dataset.deviceId, button),
    );
  });
  iconRefresh();
}

function populateDeviceSelects() {
  const options = state.devices
    .map(
      (device) =>
        `<option value="${escapeHtml(device.id)}">${escapeHtml(device.name)} / ${escapeHtml(device.site_name)}</option>`,
    )
    .join("");
  $("#upload-device").innerHTML = options;
  $("#calibration-device-select").innerHTML = options;
  $("#capture-device-filter").innerHTML = `<option value="">All devices</option>${options}`;
  $("#live-device-select").innerHTML = options;
  if (state.selectedDeviceId) {
    $("#calibration-device-select").value = state.selectedDeviceId;
  }
  if (!state.liveDeviceId && state.devices.length) {
    state.liveDeviceId = state.devices[0].id;
  }
  if (state.liveDeviceId) {
    $("#live-device-select").value = state.liveDeviceId;
  }
}

async function loadCalibration(deviceId) {
  try {
    state.calibration = await api(`/api/devices/${encodeURIComponent(deviceId)}/capture-profile`);
    renderCalibration();
  } catch (error) {
    showToast(error.message);
  }
}

function renderCalibration() {
  if (!state.calibration) return;
  const data = state.calibration;
  const profile = data.profile;
  $("#calibration-status").innerHTML = `
    <div><span>Device</span><strong>${escapeHtml(data.device_id)}</strong></div>
    <div><span>Profile</span><strong>${escapeHtml(data.calibration_id)}</strong></div>
    <div>
      <span>Interval</span>
      <div class="calibration-interval-control">
        <input id="capture-interval-input" type="number" min="10" max="30"
          step="1" value="${data.capture_interval_minutes}" aria-label="Capture interval in minutes">
        <span>min</span>
        <button class="icon-button" id="save-capture-interval" type="button"
          title="Save capture interval">
          <i data-lucide="save"></i>
        </button>
      </div>
    </div>
    <div><span>State</span><strong>${profile.locked ? "Locked" : "Editable"}</strong></div>
  `;
  $("#rgb-profile").innerHTML = cameraProfileMarkup(profile.cameras.rgb, profile.resolution);
  $("#nir-profile").innerHTML = cameraProfileMarkup(profile.cameras.nir, profile.resolution);
  const quality = profile.quality;
  $("#quality-gates").innerHTML = [
    ["Minimum blur score", quality.minimum_blur_score],
    ["Dark-pixel ceiling", percent(quality.maximum_dark_fraction)],
    ["Saturation ceiling", percent(quality.maximum_saturated_fraction)],
    ["Pair delta ceiling", `${profile.maximum_sync_delta_ms} ms`],
    ["Minimum mean level", Number(quality.minimum_mean).toFixed(2)],
    ["Maximum mean level", Number(quality.maximum_mean).toFixed(2)],
  ]
    .map(
      ([label, value]) => `
        <div class="gate-item"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>
      `,
    )
    .join("");
  $("#ingest-profile").innerHTML = `
    <div class="endpoint-list">
      <div class="endpoint-row"><span>Method</span><strong>${escapeHtml(data.ingest.method)}</strong></div>
      <div class="endpoint-row"><span>Endpoint</span><code>${escapeHtml(data.ingest.path)}</code></div>
      <div class="endpoint-row"><span>Device header</span><code>${escapeHtml(data.ingest.device_key_header)}</code></div>
      <div class="endpoint-row"><span>Content type</span><code>${escapeHtml(data.ingest.content_type)}</code></div>
    </div>
  `;
  $("#save-capture-interval").addEventListener("click", saveCaptureInterval);
  iconRefresh();
}

async function saveCaptureInterval() {
  if (!state.calibration) return;
  const input = $("#capture-interval-input");
  const interval = Number(input.value);
  if (!Number.isInteger(interval) || interval < 10 || interval > 30) {
    showToast("Interval must be from 10 to 30 minutes.");
    input.focus();
    return;
  }
  const button = $("#save-capture-interval");
  button.disabled = true;
  try {
    state.calibration = await api(
      `/api/devices/${encodeURIComponent(state.calibration.device_id)}/capture-profile`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          calibration_id: state.calibration.calibration_id,
          capture_interval_minutes: interval,
          profile: state.calibration.profile,
        }),
      },
    );
    renderCalibration();
    showToast(`Capture interval updated to ${interval} minutes.`);
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  } finally {
    if (document.body.contains(button)) button.disabled = false;
  }
}

async function requestCaptureNow(deviceId, button = null) {
  if (!deviceId) return;
  if (button) button.disabled = true;
  try {
    await api(`/api/devices/${encodeURIComponent(deviceId)}/commands`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        type: "capture_now",
        payload: { requested_from: "dashboard" },
      }),
    });
    showToast("Capture command queued.");
  } catch (error) {
    showToast(error.message);
  } finally {
    if (button) button.disabled = false;
    iconRefresh();
  }
}

function setFieldCaptureButton(active) {
  const button = $("#device-capture-pair");
  button.disabled = active;
  button.innerHTML = active
    ? `<i data-lucide="loader-circle"></i> Capture in progress`
    : `<i data-lucide="camera"></i> Capture RGB + NIR`;
  iconRefresh();
}

function renderFieldCaptureCommand(command) {
  state.fieldCaptureCommand = command;
  const section = $("#field-capture-section");
  const result = $("#field-capture-result");
  const progress = $("#field-command-progress");
  const badge = $("#field-command-badge");
  const title = $("#field-command-title");
  const detail = $("#field-command-detail");
  section.classList.remove("is-hidden");
  result.classList.add("is-hidden");
  progress.classList.remove("is-hidden");
  badge.className = `status-badge command-${command.status}`;
  badge.textContent = command.status;

  const copy = {
    pending: [
      "Capture command queued",
      "Waiting for the Raspberry Pi agent",
    ],
    running: [
      "Capturing RGB + NIR",
      "The node is validating and uploading the full-resolution pair",
    ],
    completed: [
      "Capture stored",
      "Loading the accepted observation and NDVI result",
    ],
    failed: [
      "Capture failed",
      command.result?.message || "The device could not complete this capture",
    ],
  }[command.status] || ["Capture status", command.status];
  title.textContent = copy[0];
  detail.textContent = copy[1];
  setFieldCaptureButton(["pending", "running"].includes(command.status));
  iconRefresh();
}

function renderFieldCaptureResult(capture) {
  state.fieldCaptureResult = capture;
  $("#field-capture-section").classList.remove("is-hidden");
  $("#field-command-progress").classList.add("is-hidden");
  $("#field-capture-result").classList.remove("is-hidden");
  const badge = $("#field-command-badge");
  badge.className = "status-badge command-completed";
  badge.textContent = "stored";

  const assets = [
    ["rgb", "RGB", capture.assets.rgb_thumb || capture.assets.rgb],
    ["nir", "NIR", capture.assets.nir_thumb || capture.assets.nir],
    ["ndvi", "NDVI", capture.assets.ndvi_thumb || capture.assets.ndvi],
  ];
  $("#field-result-assets").innerHTML = assets
    .map(
      ([key, label, source]) => `
        <button class="field-result-asset" type="button"
          data-result-asset="${key}" title="Open ${label} observation">
          <img src="${escapeHtml(source)}" alt="${label} full-resolution capture result">
          <span>${label}</span>
        </button>
      `,
    )
    .join("");
  $("#field-result-time").textContent =
    `${dateLabel(capture.captured_at, { year: true })}, ${timeLabel(capture.captured_at)}`;
  $("#field-result-ndvi").textContent = ndvi(capture.ndvi.mean);
  $("#field-result-healthy").textContent = percent(capture.ndvi.healthy_fraction);
  $("#field-result-delta").textContent =
    capture.sync_delta_ms === null
      ? "-"
      : `${Number(capture.sync_delta_ms).toFixed(1)} ms`;
  $$(".field-result-asset").forEach((button) => {
    button.addEventListener("click", async () => {
      await openCapture(capture.id);
      state.selectedAsset = button.dataset.resultAsset;
      renderCaptureAsset();
    });
  });
  setFieldCaptureButton(false);
  iconRefresh();
}

function clearFieldCaptureState() {
  window.clearInterval(state.fieldCapturePoll);
  state.fieldCapturePoll = null;
  state.fieldCaptureCommand = null;
  state.fieldCaptureResult = null;
  $("#field-capture-section").classList.add("is-hidden");
  $("#field-capture-result").classList.add("is-hidden");
  $("#field-command-progress").classList.remove("is-hidden");
  setFieldCaptureButton(false);
}

async function pollFieldCaptureCommand() {
  const command = state.fieldCaptureCommand;
  if (!command || !state.liveDeviceId) return;
  try {
    const updated = await api(
      `/api/devices/${encodeURIComponent(command.device_id)}/commands/${encodeURIComponent(command.id)}`,
    );
    renderFieldCaptureCommand(updated);
    if (updated.status === "completed") {
      window.clearInterval(state.fieldCapturePoll);
      state.fieldCapturePoll = null;
      const captureId = updated.result?.capture_id;
      if (!captureId) {
        throw new Error("Capture completed without a stored observation ID");
      }
      const capture = await api(`/api/captures/${encodeURIComponent(captureId)}`);
      renderFieldCaptureResult(capture);
      showToast("RGB, NIR, and NDVI were stored.");
      await refreshAll();
    } else if (updated.status === "failed") {
      window.clearInterval(state.fieldCapturePoll);
      state.fieldCapturePoll = null;
      setFieldCaptureButton(false);
      showToast(updated.result?.message || "Remote capture failed.");
    }
  } catch (error) {
    $("#field-command-detail").textContent = error.message;
  }
}

function watchFieldCaptureCommand(command) {
  window.clearInterval(state.fieldCapturePoll);
  renderFieldCaptureCommand(command);
  if (!["pending", "running"].includes(command.status)) return;
  state.fieldCapturePoll = window.setInterval(pollFieldCaptureCommand, 1500);
}

async function requestFieldCapture() {
  if (!state.liveDeviceId) return;
  clearFieldCaptureState();
  setFieldCaptureButton(true);
  try {
    const command = await api(
      `/api/devices/${encodeURIComponent(state.liveDeviceId)}/commands`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: "capture_now",
          payload: { requested_from: "live_field_preview" },
        }),
      },
    );
    watchFieldCaptureCommand(command);
    showToast("Full-resolution capture queued.");
  } catch (error) {
    setFieldCaptureButton(false);
    showToast(error.message);
  }
}

async function loadFieldCaptureState() {
  if (!state.liveDeviceId || state.liveSource !== "device") return;
  try {
    const commands = await api(
      `/api/devices/${encodeURIComponent(state.liveDeviceId)}/commands?limit=10`,
    );
    const command = commands.find((item) => item.type === "capture_now");
    if (!command) {
      clearFieldCaptureState();
      return;
    }
    renderFieldCaptureCommand(command);
    if (["pending", "running"].includes(command.status)) {
      watchFieldCaptureCommand(command);
    } else if (command.status === "completed" && command.result?.capture_id) {
      const capture = await api(
        `/api/captures/${encodeURIComponent(command.result.capture_id)}`,
      );
      renderFieldCaptureResult(capture);
    }
  } catch (_error) {
    clearFieldCaptureState();
  }
}

function cameraProfileMarkup(camera, resolution) {
  const exposures = Object.entries(camera.exposure_profiles)
    .map(
      ([name, value]) => `
        <div class="exposure-item">
          <span>${escapeHtml(name)}</span>
          <strong>${value.exposure_us} us / ${value.analogue_gain}x</strong>
        </div>
      `,
    )
    .join("");
  return `
    <table class="profile-table">
      <tbody>
        <tr><th>Model</th><td>${escapeHtml(camera.model)}</td></tr>
        <tr><th>Resolution</th><td>${resolution.width} x ${resolution.height}</td></tr>
        <tr><th>Sensor crop</th><td>${escapeHtml(camera.scaler_crop.join(", "))}</td></tr>
        <tr><th>Lens position</th><td>${camera.lens_position}</td></tr>
        <tr><th>AE / AWB</th><td>${camera.ae_enabled ? "On" : "Off"} / ${camera.awb_enabled ? "On" : "Off"}</td></tr>
        <tr><th>Colour gains</th><td>${camera.colour_gains.join(" / ")}</td></tr>
        ${camera.filter ? `<tr><th>Optical filter</th><td>${escapeHtml(camera.filter)}</td></tr>` : ""}
      </tbody>
    </table>
    <div class="profile-subheading">Fixed exposure profiles</div>
    <div class="exposure-grid">${exposures}</div>
  `;
}

async function openCapture(captureId) {
  try {
    const capture = await api(`/api/captures/${encodeURIComponent(captureId)}`);
    state.selectedCapture = capture;
    state.selectedAsset = "ndvi";
    $("#capture-detail-site").textContent = capture.site_name;
    $("#capture-detail-title").textContent =
      `${capture.device_name} / ${dateLabel(capture.captured_at, { year: true })}, ${timeLabel(capture.captured_at)}`;
    renderCaptureAsset();
    renderCaptureInspector();
    $("#capture-dialog").showModal();
    iconRefresh();
  } catch (error) {
    showToast(error.message);
  }
}

function renderCaptureAsset() {
  const capture = state.selectedCapture;
  if (!capture) return;
  const asset = state.selectedAsset;
  $("#capture-detail-image").src = capture.assets[asset];
  $("#capture-detail-image").alt = `${asset.toUpperCase()} capture from ${capture.site_name}`;
  $("#capture-download").href = capture.assets[asset];
  $("#capture-download").download = `${capture.date_key}-${capture.device_id}-${asset}`;
  $("#ndvi-scale").style.display = asset === "ndvi" ? "grid" : "none";
  $$("[data-asset]", $("#asset-tabs")).forEach((button) => {
    button.classList.toggle("is-active", button.dataset.asset === asset);
  });
}

function renderCaptureInspector() {
  const capture = state.selectedCapture;
  const metadata = capture.metadata || {};
  $("#capture-inspector").innerHTML = `
    <div class="inspector-block">
      <h3>Vegetation index</h3>
      <div class="inspector-metric-grid">
        <div class="inspector-metric"><span>Mean</span><strong>${ndvi(capture.ndvi.mean)}</strong></div>
        <div class="inspector-metric"><span>Range</span><strong>${ndvi(capture.ndvi.minimum)} to ${ndvi(capture.ndvi.maximum)}</strong></div>
        <div class="inspector-metric"><span>Healthy</span><strong>${percent(capture.ndvi.healthy_fraction)}</strong></div>
        <div class="inspector-metric"><span>Stressed</span><strong>${percent(capture.ndvi.stressed_fraction)}</strong></div>
      </div>
    </div>
    <div class="inspector-block">
      <h3>Capture quality</h3>
      <div class="quality-list">
        <div class="quality-row"><span>State</span><span class="status-badge ${escapeHtml(capture.quality_state)}">${escapeHtml(capture.quality_state)}</span></div>
        <div class="quality-row"><span>RGB sharpness</span><strong>${capture.quality.rgb_blur_score.toFixed(1)}</strong></div>
        <div class="quality-row"><span>NIR sharpness</span><strong>${capture.quality.nir_blur_score.toFixed(1)}</strong></div>
        <div class="quality-row"><span>Capture delta</span><strong>${capture.sync_delta_ms === null ? "-" : `${capture.sync_delta_ms.toFixed(1)} ms`}</strong></div>
        <div class="quality-row"><span>Saturated</span><strong>${percent(capture.quality.saturated_fraction, 2)}</strong></div>
        ${
          capture.quality_flags?.includes("nir_resampled_to_rgb")
            ? `<div class="quality-row"><span>Pair grid</span><strong>NIR resampled</strong></div>`
            : ""
        }
        ${
          capture.quality_flags?.includes("rgb_saturation_high")
            ? `<div class="quality-row"><span>Quality gate</span><strong>RGB saturation high</strong></div>`
            : ""
        }
        ${
          capture.quality_flags?.includes("nir_saturation_high")
            ? `<div class="quality-row"><span>Quality gate</span><strong>NIR saturation high</strong></div>`
            : ""
        }
      </div>
    </div>
    <div class="inspector-block">
      <h3>Provenance</h3>
      <div class="quality-list">
        <div class="quality-row"><span>Resolution</span><strong>${capture.resolution.width} x ${capture.resolution.height}</strong></div>
        <div class="quality-row"><span>Source</span><strong>${escapeHtml(capture.source)}</strong></div>
        <div class="quality-row"><span>Calibration</span><strong>${escapeHtml(metadata.calibration_id || "Not supplied")}</strong></div>
        <div class="quality-row"><span>Stage</span><strong>${escapeHtml(metadata.phenology_stage || "Unclassified")}</strong></div>
      </div>
    </div>
    <div class="inspector-block">
      <button class="button button-secondary" type="button" id="recompute-ndvi">
        <i data-lucide="refresh-cw"></i>
        Recompute NDVI
      </button>
      ${
        capture.assets.ndvi_data
          ? `<a class="button button-quiet" href="${escapeHtml(capture.assets.ndvi_data)}" download>
              <i data-lucide="binary"></i>Raw matrix
            </a>`
          : ""
      }
    </div>
  `;
  $("#recompute-ndvi").addEventListener("click", recomputeNdvi);
}

async function recomputeNdvi() {
  if (!state.selectedCapture) return;
  const button = $("#recompute-ndvi");
  button.disabled = true;
  try {
    state.selectedCapture = await api(
      `/api/captures/${encodeURIComponent(state.selectedCapture.id)}/recompute-ndvi`,
      { method: "POST" },
    );
    renderCaptureAsset();
    renderCaptureInspector();
    showToast("NDVI was recomputed.");
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  } finally {
    button.disabled = false;
    iconRefresh();
  }
}

function setDevicePreviewConnection(status, label) {
  const connection = $("#device-preview-connection");
  const dot = $(".status-dot", connection);
  dot.classList.toggle("is-online", status === "online");
  dot.classList.toggle("is-offline", status === "offline");
  $("span:last-child", connection).textContent = label;
}

function resetDevicePreviewImages() {
  state.devicePreviewSequence = null;
  ["rgb", "nir"].forEach((channel) => {
    const image = $(`#device-${channel}-preview`);
    const placeholder = $(`#device-${channel}-placeholder`);
    image.removeAttribute("src");
    image.classList.remove("is-visible");
    placeholder.classList.remove("is-hidden");
  });
}

function renderDevicePreview() {
  const preview = state.devicePreview;
  if (!preview) return;
  $("#device-preview-name").textContent =
    `${preview.device_name} / ${preview.site_name}`;
  $("#device-preview-state").textContent =
    preview.state === "streaming"
      ? "Streaming"
      : preview.state === "waiting"
        ? "Waiting for Pi"
        : "Stopped";
  $("#device-preview-resolution").textContent = preview.resolution
    ? `${preview.resolution.width} x ${preview.resolution.height}`
    : "-";
  $("#device-rgb-sharpness").textContent = preview.quality
    ? Number(preview.quality.rgb_blur_score).toFixed(1)
    : "-";
  $("#device-nir-sharpness").textContent = preview.quality
    ? Number(preview.quality.nir_blur_score).toFixed(1)
    : "-";
  $("#device-preview-delta").textContent =
    preview.sync_delta_ms === null
      ? "-"
      : `${Number(preview.sync_delta_ms).toFixed(1)} ms`;
  $("#device-preview-sequence").textContent = String(preview.sequence || 0);
  $("#device-preview-cadence").textContent =
    `One paired frame every ${Number(preview.interval_seconds).toFixed(0)} seconds`;
  $("#device-preview-age").textContent = preview.latest_at
    ? `Updated ${relativeTime(preview.latest_at).toLowerCase()}`
    : "Waiting for first frame";

  if (preview.state === "streaming") {
    setDevicePreviewConnection("online", "RGB + NIR live");
  } else if (preview.active) {
    setDevicePreviewConnection("idle", "Waiting for Pi agent");
  } else {
    setDevicePreviewConnection("offline", "Preview stopped");
  }

  const version = `${preview.session_id || "none"}-${preview.sequence || 0}`;
  if (
    preview.sequence > 0
    && preview.assets.rgb
    && preview.assets.nir
    && state.devicePreviewSequence !== version
  ) {
    state.devicePreviewSequence = version;
    [
      ["rgb", preview.assets.rgb],
      ["nir", preview.assets.nir],
    ].forEach(([channel, asset]) => {
      const image = $(`#device-${channel}-preview`);
      const placeholder = $(`#device-${channel}-placeholder`);
      image.src = `${asset}?v=${encodeURIComponent(version)}`;
      image.decode()
        .then(() => {
          image.classList.add("is-visible");
          placeholder.classList.add("is-hidden");
        })
        .catch(() => {});
    });
  } else if (preview.sequence === 0 && state.devicePreviewSequence !== null) {
    resetDevicePreviewImages();
  }
}

async function refreshDevicePreview() {
  if (
    state.currentView !== "live"
    || state.liveSource !== "device"
    || !state.liveDeviceId
  ) {
    return;
  }
  try {
    state.devicePreview = await api(
      `/api/devices/${encodeURIComponent(state.liveDeviceId)}/preview`,
    );
    renderDevicePreview();
  } catch (error) {
    setDevicePreviewConnection("offline", "Preview unavailable");
  }
}

async function startDevicePreview() {
  if (!state.liveDeviceId) return;
  window.clearInterval(state.devicePreviewPoll);
  window.clearInterval(state.devicePreviewKeepalive);
  try {
    state.devicePreview = await api(
      `/api/devices/${encodeURIComponent(state.liveDeviceId)}/preview/start`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          interval_seconds: 2,
          preview_width: 960,
          session_seconds: 90,
        }),
      },
    );
    renderDevicePreview();
    state.devicePreviewPoll = window.setInterval(refreshDevicePreview, 1000);
    state.devicePreviewKeepalive = window.setInterval(async () => {
      if (
        state.currentView !== "live"
        || state.liveSource !== "device"
        || !state.liveDeviceId
      ) {
        return;
      }
      try {
        state.devicePreview = await api(
          `/api/devices/${encodeURIComponent(state.liveDeviceId)}/preview/start`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              interval_seconds: 2,
              preview_width: 960,
              session_seconds: 90,
            }),
          },
        );
        renderDevicePreview();
      } catch (_error) {
        setDevicePreviewConnection("offline", "Preview unavailable");
      }
    }, 45000);
  } catch (error) {
    setDevicePreviewConnection("offline", "Preview unavailable");
    showToast(error.message);
  }
}

async function stopDevicePreview(deviceId = state.liveDeviceId) {
  window.clearInterval(state.devicePreviewPoll);
  window.clearInterval(state.devicePreviewKeepalive);
  state.devicePreviewPoll = null;
  state.devicePreviewKeepalive = null;
  resetDevicePreviewImages();
  if (!deviceId) return;
  try {
    await api(`/api/devices/${encodeURIComponent(deviceId)}/preview/stop`, {
      method: "POST",
    });
  } catch (_error) {
    // Preview sessions expire automatically if the browser disconnects.
  }
}

async function restartDevicePreview() {
  const button = $("#device-preview-restart");
  button.disabled = true;
  button.classList.add("is-active");
  try {
    await stopDevicePreview();
    await startDevicePreview();
  } finally {
    button.disabled = false;
    button.classList.remove("is-active");
    iconRefresh();
  }
}

function openLiveView() {
  if (state.liveSource === "device") {
    startDevicePreview();
  } else {
    openWebcamView();
  }
}

function closeLiveView() {
  if (state.liveSource === "device") {
    stopDevicePreview();
  } else {
    closeWebcamView();
  }
}

async function switchLiveSource(source) {
  if (!["device", "webcam"].includes(source) || source === state.liveSource) {
    return;
  }
  if (state.currentView === "live") {
    if (state.liveSource === "device") {
      await stopDevicePreview();
    } else {
      closeWebcamView();
    }
  }
  state.liveSource = source;
  $$("[data-live-source]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.liveSource === source);
  });
  $("#device-live-actions").classList.toggle("is-hidden", source !== "device");
  $("#device-live-panel").classList.toggle("is-hidden", source !== "device");
  $("#webcam-live-actions").classList.toggle("is-hidden", source !== "webcam");
  $("#webcam-live-panel").classList.toggle("is-hidden", source !== "webcam");
  $("#live-view-title").textContent =
    source === "device" ? "Field camera preview" : "USB RGB test camera";
  if (state.currentView === "live") openLiveView();
  iconRefresh();
}

function setWebcamConnection(status, label) {
  const connection = $("#webcam-connection");
  const dot = $(".status-dot", connection);
  dot.classList.toggle("is-online", status === "online");
  dot.classList.toggle("is-offline", status === "offline");
  $("span:last-child", connection).textContent = label;
}

function renderWebcamStatus() {
  const status = state.webcamStatus;
  if (!status) return;

  const configured = status.configured;
  const active = status.active;
  const frame = status.frame;
  $("#webcam-name").textContent = status.camera_name;
  $("#webcam-resolution").value = `${configured.width}x${configured.height}`;
  $("#webcam-fps").value = String(configured.fps);
  $("#webcam-zoom").value = String(configured.zoom);
  $("#webcam-zoom-value").value = `${Number(configured.zoom).toFixed(1)}x`;
  $("#webcam-active-mode").textContent = `${active.width} x ${active.height}`;
  $("#webcam-active-fps").textContent = `${Number(active.fps).toFixed(0)} FPS`;
  $("#webcam-brightness").textContent = frame ? percent(frame.brightness) : "-";
  $("#webcam-sharpness").textContent = frame
    ? Number(frame.sharpness).toFixed(1)
    : "-";
  $("#webcam-dark-fraction").textContent = frame
    ? percent(frame.dark_fraction, 1)
    : "-";
  $("#webcam-saturation").textContent = frame
    ? percent(frame.saturated_fraction, 1)
    : "-";

  if (status.running) {
    setWebcamConnection("online", "Camera live");
  } else if (status.error) {
    setWebcamConnection("offline", "Camera unavailable");
  } else {
    setWebcamConnection("idle", "Camera idle");
  }
}

function renderWebcamSnapshots() {
  const snapshots = state.webcamSnapshots;
  $("#webcam-snapshot-count").textContent =
    `${snapshots.length} saved`;
  if (!snapshots.length) {
    $("#webcam-snapshots").innerHTML = `
      <div class="empty-state webcam-empty">
        No RGB snapshots have been captured yet.
      </div>
    `;
    return;
  }

  const groups = new Map();
  snapshots.forEach((snapshot) => {
    if (!groups.has(snapshot.date_key)) groups.set(snapshot.date_key, []);
    groups.get(snapshot.date_key).push(snapshot);
  });
  $("#webcam-snapshots").innerHTML = Array.from(groups.entries())
    .map(
      ([dateKey, items]) => `
        <section class="webcam-date-group">
          <div class="webcam-date-heading">
            <h3>${escapeHtml(dateLabel(`${dateKey}T00:00:00Z`, { year: true }))}</h3>
            <span>${items.length} RGB image${items.length === 1 ? "" : "s"}</span>
          </div>
          <div class="webcam-date-grid">
            ${items
              .map(
                (snapshot) => `
                  <article class="webcam-snapshot-card">
                    <a href="${escapeHtml(snapshot.assets.rgb)}" target="_blank"
                      rel="noopener" title="Open full RGB image">
                      <img src="${escapeHtml(snapshot.assets.thumb)}"
                        alt="RGB snapshot captured at ${escapeHtml(timeLabel(snapshot.captured_at))}">
                    </a>
                    <div class="webcam-snapshot-meta">
                      <div>
                        <strong>${escapeHtml(timeLabel(snapshot.captured_at))}</strong>
                        <span>${snapshot.resolution.width} x ${snapshot.resolution.height}</span>
                      </div>
                      <div>
                        <strong>${Number(snapshot.quality.blur_score).toFixed(0)}</strong>
                        <span>Sharpness</span>
                      </div>
                      <a class="icon-button" href="${escapeHtml(snapshot.assets.rgb)}"
                        download="${escapeHtml(`${snapshot.date_key}-${snapshot.id}-rgb.jpg`)}"
                        title="Download RGB image">
                        <i data-lucide="download"></i>
                      </a>
                    </div>
                  </article>
                `,
              )
              .join("")}
          </div>
        </section>
      `,
    )
    .join("");
  iconRefresh();
}

function startWebcamPreview() {
  const image = $("#webcam-stream");
  const placeholder = $("#webcam-placeholder");
  placeholder.classList.remove("is-hidden");
  $("#webcam-placeholder-detail").textContent = "Waiting for the USB camera";
  image.classList.remove("is-visible");
  image.src = `/api/webcam/stream.mjpg?t=${Date.now()}`;
}

async function refreshWebcamStatus() {
  if (state.currentView !== "live" || state.liveSource !== "webcam") return;
  try {
    state.webcamStatus = await api("/api/webcam/status");
    renderWebcamStatus();
  } catch (error) {
    setWebcamConnection("offline", "Camera unavailable");
  }
}

async function loadWebcamSnapshots() {
  try {
    state.webcamSnapshots = await api("/api/webcam/snapshots?limit=48");
    renderWebcamSnapshots();
  } catch (error) {
    showToast(error.message);
  }
}

async function openWebcamView() {
  window.clearInterval(state.webcamPoll);
  try {
    state.webcamStatus = await api("/api/webcam/start", { method: "POST" });
    renderWebcamStatus();
    startWebcamPreview();
    await loadWebcamSnapshots();
    state.webcamPoll = window.setInterval(refreshWebcamStatus, 2000);
  } catch (error) {
    setWebcamConnection("offline", "Camera unavailable");
    $("#webcam-placeholder-detail").textContent = error.message;
    showToast(error.message);
  }
}

function closeWebcamView() {
  window.clearInterval(state.webcamPoll);
  state.webcamPoll = null;
  const stream = $("#webcam-stream");
  stream.removeAttribute("src");
  stream.classList.remove("is-visible");
  $("#webcam-placeholder").classList.remove("is-hidden");
  api("/api/webcam/stop", { method: "POST" }).catch(() => {});
}

async function restartWebcamPreview() {
  const button = $("#webcam-restart");
  button.disabled = true;
  button.classList.add("is-active");
  try {
    await api("/api/webcam/stop", { method: "POST" });
    await openWebcamView();
  } catch (error) {
    showToast(error.message);
  } finally {
    button.disabled = false;
    button.classList.remove("is-active");
    iconRefresh();
  }
}

async function updateWebcamConfig() {
  const [width, height] = $("#webcam-resolution").value.split("x").map(Number);
  const fps = Number($("#webcam-fps").value);
  const zoom = Number($("#webcam-zoom").value);
  $$(".camera-control select, .camera-control input").forEach((control) => {
    control.disabled = true;
  });
  try {
    state.webcamStatus = await api("/api/webcam/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ width, height, fps, zoom }),
    });
    renderWebcamStatus();
    startWebcamPreview();
    showToast(`Camera set to ${width} x ${height}, ${fps} FPS, ${zoom.toFixed(1)}x.`);
  } catch (error) {
    showToast(error.message);
    await refreshWebcamStatus();
  } finally {
    $$(".camera-control select, .camera-control input").forEach((control) => {
      control.disabled = false;
    });
  }
}

async function captureWebcamSnapshot() {
  const button = $("#webcam-capture");
  button.disabled = true;
  button.innerHTML = `<i data-lucide="loader-circle"></i> Checking frame`;
  iconRefresh();
  try {
    const snapshot = await api("/api/webcam/capture", { method: "POST" });
    state.webcamSnapshots = [
      snapshot,
      ...state.webcamSnapshots.filter((item) => item.id !== snapshot.id),
    ].slice(0, 48);
    renderWebcamSnapshots();
    showToast("RGB snapshot passed quality checks and was saved.");
  } catch (error) {
    showToast(error.message);
  } finally {
    button.disabled = false;
    button.innerHTML = `<i data-lucide="camera"></i> Capture RGB`;
    iconRefresh();
  }
}

function switchView(view) {
  if (state.currentView === "live" && view !== "live") {
    closeLiveView();
  }
  state.currentView = view;
  $$(".app-view").forEach((section) => {
    section.classList.toggle("is-active", section.id === `view-${view}`);
  });
  $$(".nav-tab").forEach((tab) => {
    tab.classList.toggle("is-active", tab.dataset.viewTarget === view);
  });
  if (view === "captures") loadCaptures();
  if (view === "calibration" && state.selectedDeviceId) {
    $("#calibration-device-select").value = state.selectedDeviceId;
    loadCalibration(state.selectedDeviceId);
  }
  if (view === "live") openLiveView();
  window.scrollTo({ top: 0, behavior: "instant" });
  iconRefresh();
}

function openUploadDialog() {
  const input = $("#upload-captured-at");
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  input.value = now.toISOString().slice(0, 16);
  $("#upload-error").classList.remove("is-visible");
  $("#upload-dialog").showModal();
}

async function submitUpload(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const errorBox = $("#upload-error");
  const submit = $("#upload-submit");
  const formData = new FormData(form);
  formData.set("source", "manual");
  formData.set("metadata", "{}");
  const localDate = new Date(formData.get("captured_at"));
  formData.set("captured_at", localDate.toISOString());

  errorBox.classList.remove("is-visible");
  submit.disabled = true;
  submit.innerHTML = `<i data-lucide="loader-circle"></i> Processing`;
  iconRefresh();
  try {
    const capture = await api("/api/captures", {
      method: "POST",
      body: formData,
    });
    $("#upload-dialog").close();
    form.reset();
    resetFileFields();
    showToast(`Capture accepted. Mean NDVI ${ndvi(capture.ndvi.mean)}.`);
    await refreshAll();
    switchView("captures");
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.classList.add("is-visible");
  } finally {
    submit.disabled = false;
    submit.innerHTML = `<i data-lucide="cloud-upload"></i> Validate and upload`;
    iconRefresh();
  }
}

function resetFileFields() {
  $$(".file-field").forEach((field) => {
    field.classList.remove("has-file");
    const span = $("span", field);
    span.textContent = field.id.startsWith("rgb") ? "JPEG or PNG" : "Same scene framing";
  });
}

function exportProfile() {
  if (!state.calibration) return;
  const blob = new Blob([JSON.stringify(state.calibration, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${state.calibration.device_id}-capture-profile.json`;
  link.click();
  URL.revokeObjectURL(url);
}

function bindEvents() {
  $$("[data-view-target]").forEach((button) => {
    button.addEventListener("click", () => switchView(button.dataset.viewTarget));
  });
  $("#refresh-button").addEventListener("click", refreshAll);
  $("#device-search").addEventListener("input", renderDeviceRail);
  $("#capture-filters").addEventListener("submit", (event) => {
    event.preventDefault();
    loadCaptures();
  });
  $("#open-upload").addEventListener("click", openUploadDialog);
  $("#open-upload-captures").addEventListener("click", openUploadDialog);
  $("#upload-form").addEventListener("submit", submitUpload);
  $("#calibration-device-select").addEventListener("change", (event) => {
    state.selectedDeviceId = event.target.value;
    renderDeviceRail();
    loadCalibration(state.selectedDeviceId);
  });
  $("#export-profile").addEventListener("click", exportProfile);
  $("#calibration-capture-now").addEventListener("click", (event) =>
    requestCaptureNow(state.selectedDeviceId, event.currentTarget),
  );
  $$("[data-live-source]").forEach((button) => {
    button.addEventListener("click", () =>
      switchLiveSource(button.dataset.liveSource),
    );
  });
  $("#live-device-select").addEventListener("change", async (event) => {
    const previousDeviceId = state.liveDeviceId;
    if (
      state.currentView === "live"
      && state.liveSource === "device"
      && previousDeviceId
    ) {
      await stopDevicePreview(previousDeviceId);
    }
    state.liveDeviceId = event.target.value;
    state.devicePreview = null;
    resetDevicePreviewImages();
    if (state.currentView === "live" && state.liveSource === "device") {
      await startDevicePreview();
    }
  });
  $("#device-preview-restart").addEventListener("click", restartDevicePreview);
  $("#device-capture-pair").addEventListener("click", (event) =>
    requestCaptureNow(state.liveDeviceId, event.currentTarget),
  );
  $("#webcam-restart").addEventListener("click", restartWebcamPreview);
  $("#webcam-capture").addEventListener("click", captureWebcamSnapshot);
  $("#webcam-resolution").addEventListener("change", updateWebcamConfig);
  $("#webcam-fps").addEventListener("change", updateWebcamConfig);
  $("#webcam-zoom").addEventListener("input", (event) => {
    $("#webcam-zoom-value").value = `${Number(event.target.value).toFixed(1)}x`;
  });
  $("#webcam-zoom").addEventListener("change", updateWebcamConfig);
  $("#webcam-stream").addEventListener("load", () => {
    $("#webcam-stream").classList.add("is-visible");
    $("#webcam-placeholder").classList.add("is-hidden");
  });
  $("#webcam-stream").addEventListener("error", () => {
    $("#webcam-stream").classList.remove("is-visible");
    $("#webcam-placeholder").classList.remove("is-hidden");
    $("#webcam-placeholder-detail").textContent = "Preview connection was interrupted";
  });
  ["rgb", "nir"].forEach((channel) => {
    const image = $(`#device-${channel}-preview`);
    const placeholder = $(`#device-${channel}-placeholder`);
    image.addEventListener("load", () => {
      image.classList.add("is-visible");
      placeholder.classList.add("is-hidden");
    });
    image.addEventListener("error", () => {
      image.classList.remove("is-visible");
      placeholder.classList.remove("is-hidden");
    });
  });
  $$("[data-close-dialog]").forEach((button) => {
    button.addEventListener("click", () => {
      document.getElementById(button.dataset.closeDialog).close();
    });
  });
  $$("[data-asset]", $("#asset-tabs")).forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedAsset = button.dataset.asset;
      renderCaptureAsset();
    });
  });
  $$(".file-field input").forEach((input) => {
    input.addEventListener("change", () => {
      const field = input.closest(".file-field");
      field.classList.toggle("has-file", Boolean(input.files.length));
      $("span", field).textContent = input.files[0]?.name || "No file selected";
    });
  });
  $$(".modal").forEach((dialog) => {
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });
  });
  window.addEventListener("pagehide", () => {
    if (state.currentView !== "live") return;
    if (state.liveSource === "device" && state.liveDeviceId) {
      navigator.sendBeacon(
        `/api/devices/${encodeURIComponent(state.liveDeviceId)}/preview/stop`,
      );
    } else {
      $("#webcam-stream").removeAttribute("src");
      navigator.sendBeacon("/api/webcam/stop");
    }
  });
}

async function init() {
  $("#today-label").textContent = new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date());

  const to = new Date();
  const from = new Date();
  from.setDate(to.getDate() - 14);
  $("#date-to").value = to.toISOString().slice(0, 10);
  $("#date-from").value = from.toISOString().slice(0, 10);

  bindEvents();
  iconRefresh();
  await refreshAll();
  if (state.selectedDeviceId) {
    await loadCalibration(state.selectedDeviceId);
  }
}

document.addEventListener("DOMContentLoaded", init);
