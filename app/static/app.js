const state = {
  dashboard: null,
  devices: [],
  captures: [],
  selectedDeviceId: null,
  calibration: null,
  selectedCapture: null,
  selectedAsset: "ndvi",
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
            <button class="icon-button table-calibration" type="button"
              data-device-id="${escapeHtml(device.id)}" title="Open calibration">
              <i data-lucide="settings-2"></i>
            </button>
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
  if (state.selectedDeviceId) {
    $("#calibration-device-select").value = state.selectedDeviceId;
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
    <div><span>Interval</span><strong>${data.capture_interval_minutes} min</strong></div>
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
  iconRefresh();
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

function switchView(view) {
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
