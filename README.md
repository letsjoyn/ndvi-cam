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
