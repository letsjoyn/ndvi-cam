# Autonomous RGB + NIR Remote-Sensing Node

Engineering design package for an outdoor Raspberry Pi 5 AIoT device that
captures RGB and near-infrared imagery, records environmental measurements,
buffers data locally, and uploads complete capture sessions to a backend.

## FieldScope Application

This repository now includes a lightweight FastAPI and SQLite backend plus a
responsive operations dashboard:

- Date-wise RGB, NIR, and NDVI capture archive.
- Original image and compressed raw NDVI matrix storage.
- Blur, exposure, saturation, resolution, crop, focus, white-balance, and
  capture-delta validation.
- Manual RGB/NIR pairs with matching aspect ratios are resampled onto the RGB
  pixel grid and marked with a quality warning.
- Manual captures with localized saturation are stored with a warning, while
  saturated pixels are excluded from the NDVI matrix.
- Locked device calibration profiles.
- Wi-Fi, queue, storage, battery, and last-seen monitoring.
- Selected Raspberry Pi node preview with paired RGB and NIR frames relayed
  through the backend, plus remote full-resolution capture commands.
- Local USB RGB camera live preview with resolution, FPS, digital zoom,
  quality-gated capture, and a date-wise snapshot archive.
- Local filesystem storage by default and an S3-compatible adapter for cloud
  deployment.

### Run Locally

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\run.ps1
```

Open `http://127.0.0.1:8000`.

The first start creates a SQLite database and deterministic demonstration RGB
and NIR observations. Set `SEED_DEMO=false` for an empty deployment.

### Raspberry Pi RGB + NIR Preview

The **Live** page opens in **Field cameras** mode. Select a Raspberry Pi node
to request a temporary cloud-relayed preview session. The running device agent
polls the request, captures both cameras with the locked controls, aligns NIR
to RGB, downsizes temporary preview copies, and uploads a pair approximately
every two seconds.

**Capture RGB + NIR** is different from preview: it queues the existing
`capture_now` device command. The Pi then captures the full-resolution pair,
runs quality checks, preserves it in the offline queue, uploads it, and the
backend stores RGB, NIR, NDVI heatmap, and raw NDVI data.

Preview endpoints:

```text
POST /api/devices/{device_id}/preview/start
GET  /api/devices/{device_id}/preview
POST /api/devices/{device_id}/preview/stop
GET  /api/devices/{device_id}/preview/request
POST /api/devices/{device_id}/preview/frame
```

The browser-facing start/status/stop calls do not require direct network
access to the Pi. The agent initiates all field-device connections, so the
same path works behind Wi-Fi or cellular NAT.

### Local USB RGB Camera

Connect the USB camera before opening the dashboard, then select **Live**.
The default mode is `1280 x 720` at `30 FPS`; the page can switch among
`640 x 480`, `1280 x 720`, and `1920 x 1080`, change frame rate, apply
`1.0x` to `3.0x` center-crop digital zoom, and save a frame on demand.

Accepted snapshots are stored under `webcam/YYYY-MM-DD/<id>/` through the
configured local or S3 storage backend. Frames that are blurred, severely
under/overexposed, too dark, or highly saturated are rejected before storage.
This input is explicitly RGB-only and is never presented as NIR or NDVI.

Camera selection and defaults can be set before starting the server:

```powershell
$env:WEBCAM_INDEX = "0"
$env:WEBCAM_NAME = "Logitech Brio 300"
$env:WEBCAM_WIDTH = "1280"
$env:WEBCAM_HEIGHT = "720"
$env:WEBCAM_FPS = "30"
.\run.ps1
```

The relevant endpoints are `/api/webcam/status`, `/api/webcam/stream.mjpg`,
`/api/webcam/config`, `/api/webcam/capture`, and
`/api/webcam/snapshots`.

### Raspberry Pi Device Agent

The `device` package is the autonomous capture service. It retrieves the
device profile, captures an RGB/NIR pair, applies pair registration, validates
quality, commits the pair to a durable queue, uploads it, processes remote
commands, and sends heartbeats.

Run one simulated capture against the local backend:

```powershell
.\.venv\Scripts\python.exe -m device --config device\config.example.json --once
```

Process one queued `Capture now` command:

```powershell
.\.venv\Scripts\python.exe -m device --config device\config.example.json --command-once
```

For continuous interval scheduling and command polling:

```powershell
.\.venv\Scripts\python.exe -m device --config device\config.example.json
```

On Raspberry Pi OS, install Picamera2 and OpenCV from the OS repository, then
install the device HTTP dependency:

```bash
sudo apt update
sudo apt install -y python3-picamera2 python3-opencv python3-numpy python3-venv
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r requirements-device.txt
```

Copy `device/config.example.json` to `/etc/fieldscope/agent.json`, set
`simulate` to `false`, provide the backend URL and device key, and replace the
identity calibration with the measured NIR-to-RGB transform. The included
systemd unit is `device/fieldscope-agent.service`.

The hardware mode currently records camera controls and leaves environmental
sensor values empty until the SHT45/BMP390/VEML7700/GNSS driver adapters are
added. The Raspberry Pi agent supports the low-rate paired field preview
described above. High-frame-rate WebRTC/RTSP video is outside this prototype
baseline because it is poorly suited to intermittent cellular links.

### Cloud Storage

Install the cloud dependency set and configure `.env.example` values:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-cloud.txt
$env:STORAGE_BACKEND = "s3"
$env:S3_BUCKET = "fieldscope-captures"
```

The same `/api/media/...` route proxies private local or S3 objects to the
dashboard.

For a production deployment, set `DEVICE_INGEST_KEY`, terminate HTTPS at a
managed reverse proxy, and place dashboard access behind the organization's
identity provider. The built-in key is a prototype ingest control, not a full
user-management system.

## Document Set

| Artifact | Purpose |
|---|---|
| [Engineering specification](docs/AIOT-HW-SPEC.md) | Controlled system design, requirements, architecture, integration, validation, and operating guidance |
| [Device integration guide](docs/DEVICE-INTEGRATION.md) | Fixed focus/white balance/exposure, blur rejection, upload, heartbeat, and Wi-Fi setup |
| [Agent configuration](device/config.example.json) | Executable simulation/Pi configuration for the capture service |
| [Pair calibration example](device/calibration.example.json) | Development identity homography that must be replaced after calibration |
| [Bill of materials](docs/BOM.csv) | Prototype procurement list, alternatives, quantities, and planning costs |
| [Wiring schedule](docs/wiring.csv) | GPIO, I2C, UART, power, and connector allocation |
| [Power budget](docs/power-budget.csv) | Continuous and duty-cycled energy assumptions |
| [Storage budget](docs/storage-budget.csv) | Retention estimates for operating capture profiles |
| [Device configuration](docs/interfaces/device-config.example.yaml) | Versioned example configuration passed to embedded implementation |
| [Configuration schema](docs/interfaces/device-config.schema.json) | JSON Schema for validating the YAML configuration after YAML-to-JSON parsing |
| [Metadata schema](docs/interfaces/capture-metadata.schema.json) | JSON Schema for uploaded capture metadata |
| [Metadata example](docs/interfaces/capture-metadata.example.json) | Complete valid capture-session example |
| [API contract](docs/interfaces/openapi.yaml) | Preferred manifest, asset upload, and acknowledgement protocol |
| [Assembly checklist](docs/checklists/assembly-checklist.md) | Build and factory inspection record |
| [Deployment checklist](docs/checklists/deployment-checklist.md) | Site installation and commissioning record |
| [Acceptance test record](docs/checklists/acceptance-test-record.md) | Repeatable engineering and release test record |

## Design Status

- Document status: Prototype Design Baseline / Preliminary Design Review
- Revision: 1.0
- Baseline date: 2026-07-22
- Intended build stage: EVT prototype followed by a 30-day field pilot

This package is implementation-ready for a prototype, but it is not a
manufacturing release. The deployment climate, cellular carrier/bands, scene
geometry, autonomy target, regional radio approvals, and backend endpoint must
be confirmed at the design-review gates identified in the specification.
