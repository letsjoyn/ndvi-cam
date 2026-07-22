# Raspberry Pi Capture and Backend Integration

This guide connects the Raspberry Pi 5 capture service to the FieldScope
backend. The controlled profile is obtained from:

```text
GET /api/devices/{device_id}/capture-profile
```

The device shall cache the last validated profile and include its
`calibration_id` with every capture.

## 1. Fixed Geometry and "Same Zoom"

Camera Module 3 has autofocus but no optical zoom. A stable field of view is
created by fixing all of the following:

- A rigid camera mount that cannot rotate or translate.
- The same camera module and lens.
- Full-sensor `ScalerCrop`, normally `[0, 0, 4608, 2592]`.
- Output resolution `4608 x 2592`.
- Manual lens position after focus calibration.
- Camera orientation and physical distance from the scene.

Do not use digital zoom, dynamic crop, stabilization crop, or automatic
reframing. The backend rejects device uploads whose reported crop differs from
the locked profile.

## 2. One-Time Focus Calibration

Perform this after the cameras, 850 nm filter, windows, and enclosure are in
their final mechanical positions.

1. Place a high-contrast target at the normal observation distance.
2. Sweep `LensPosition` through a useful range.
3. Capture one image at each step.
4. Calculate sharpness using variance of the grayscale Laplacian.
5. Inspect center and corners at normal, hot, and cold temperatures.
6. Save the best repeatable position separately for RGB and NIR.
7. Set autofocus to manual for normal captures.

The default demonstration profile uses:

```text
RGB LensPosition: 3.2
NIR LensPosition: 3.6
```

These numbers are placeholders. Each final camera pair must be calibrated.

## 3. White Balance and Exposure

### RGB

Run automatic white balance only during commissioning under a representative
reference target. Record the returned red/blue gains, then disable AWB.

The default profile uses fixed gains:

```text
ColourGains: [1.75, 1.55]
AwbEnable: false
```

### NIR

White balance has no normal color meaning after the 850 nm filter. Disable AWB
and use fixed calibrated gains, initially:

```text
ColourGains: [1.0, 1.0]
AwbEnable: false
```

### Exposure

Disable automatic exposure. Use a small set of fixed profiles selected by lux
or schedule. Every profile has a fixed exposure time and analogue gain.

```text
RGB overcast: 4000 us, gain 1.0
NIR overcast: 8000 us, gain 1.5
```

The selected profile ID and the values returned by libcamera must be uploaded.
The backend rejects a device capture when the controls drift beyond the
configured tolerance.

## 4. Picamera2 Control Pattern

Use the values returned by the profile endpoint:

```python
from libcamera import controls

def apply_fixed_controls(camera, camera_profile, exposure_profile):
    camera.set_controls(
        {
            "AeEnable": False,
            "AwbEnable": False,
            "AfMode": controls.AfModeEnum.Manual,
            "LensPosition": camera_profile["lens_position"],
            "ColourGains": tuple(camera_profile["colour_gains"]),
            "ScalerCrop": tuple(camera_profile["scaler_crop"]),
            "ExposureTime": exposure_profile["exposure_us"],
            "AnalogueGain": exposure_profile["analogue_gain"],
        }
    )
```

After applying controls, discard several frames. Save the metadata returned by
the final capture request rather than assuming every requested value was
applied exactly.

Capture RGB and NIR within the profile's `maximum_sync_delta_ms`. The baseline
sequence is RGB then NIR. For windy vegetation, use RGB-NIR-RGB and reject the
session when the first and second RGB frames show excessive motion.

## 5. Blur and Exposure Gate on the Device

The device should reject a poor pair before using bandwidth:

```python
import cv2

def image_quality(path):
    image = cv2.imread(path, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return {
        "blur_score": float(cv2.Laplacian(gray, cv2.CV_64F).var()),
        "mean": float(gray.mean() / 255.0),
        "dark_fraction": float((gray <= 12).mean()),
        "saturated_fraction": float((gray >= 250).mean()),
    }
```

Compare these values to the quality block returned by the profile endpoint.
Both images must:

- Decode successfully.
- Have the same width and height.
- Match the locked production resolution and crop.
- Exceed the minimum blur score.
- Remain inside the brightness, dark-pixel, and saturation limits.

Retry once. If the retry fails, store a local diagnostic record and do not send
the blurred image pair as a valid observation.

## 6. Device Upload

The device sends a multipart request:

```text
POST /api/captures
X-Device-Key: <unique or site-specific development key>
Content-Type: multipart/form-data
```

Fields:

| Field | Value |
|---|---|
| `device_id` | Backend device identifier |
| `captured_at` | UTC ISO 8601 timestamp |
| `source` | `device` |
| `sync_delta_ms` | Measured RGB-to-NIR capture delta |
| `metadata` | JSON camera controls and calibration identity |
| `rgb` | RGB JPEG/PNG |
| `nir` | Filtered NIR JPEG/PNG |

Example controls metadata:

```json
{
  "calibration_id": "CAL-2026-07-A",
  "rgb_controls": {
    "ae_enabled": false,
    "awb_enabled": false,
    "scaler_crop": [0, 0, 4608, 2592],
    "lens_position": 3.2,
    "colour_gains": [1.75, 1.55],
    "profile_id": "overcast",
    "exposure_us": 4000,
    "analogue_gain": 1.0
  },
  "nir_controls": {
    "ae_enabled": false,
    "awb_enabled": false,
    "scaler_crop": [0, 0, 4608, 2592],
    "lens_position": 3.6,
    "colour_gains": [1.0, 1.0],
    "profile_id": "overcast",
    "exposure_us": 8000,
    "analogue_gain": 1.5
  }
}
```

The backend performs the same checks again, calculates NDVI, stores thumbnails,
stores the original files, and stores a compressed float NDVI matrix.

## 7. Wi-Fi Setup

Raspberry Pi OS uses NetworkManager. Configure the deployment network once:

```bash
sudo nmcli radio wifi on
sudo nmcli device wifi list ifname wlan0
sudo nmcli device wifi connect "FIELD_SSID" password "FIELD_PASSWORD" ifname wlan0
sudo nmcli connection modify "FIELD_SSID" connection.autoconnect yes
sudo nmcli connection modify "FIELD_SSID" connection.autoconnect-priority 100
```

Do not put the Wi-Fi password in source code or uploaded metadata. Provision it
through a protected setup process.

Verify:

```bash
nmcli -f GENERAL.STATE,GENERAL.CONNECTION,IP4.ADDRESS device show wlan0
nmcli -f IN-USE,SSID,SIGNAL,SECURITY device wifi list ifname wlan0
```

Network loss must not stop capture. Commit the pair locally, place it in an
upload queue, and retry with exponential backoff after NetworkManager
reconnects.

## 8. Heartbeat

Send current connectivity and queue status periodically:

```text
POST /api/devices/{device_id}/heartbeat
X-Device-Key: <key>
Content-Type: application/json
```

```json
{
  "status": "online",
  "wifi_ssid": "FieldNet-5G",
  "wifi_rssi_dbm": -58,
  "ip_address": "192.168.20.41",
  "firmware_version": "0.1.0",
  "queue_depth": 0,
  "storage_used_percent": 18.6,
  "battery_percent": 84
}
```

The dashboard displays Wi-Fi signal, last-seen time, local queue, storage, and
battery state.

## 9. Calibration Rules

Recalibrate when any of these changes:

- Camera module or lens.
- Camera bracket or orientation.
- NIR filter.
- Optical window.
- Focus position.
- Resolution or crop.
- RGB color gains.
- Exposure profile values.

Keep old calibration IDs. Historical captures must remain linked to the profile
used when they were acquired.

