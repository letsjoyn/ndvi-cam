# Site Deployment and Commissioning Checklist

| Record Field | Value |
|---|---|
| Device ID | |
| Unit serial | |
| Site ID | |
| Installation coordinate | |
| Installer(s) | |
| Installation date | |
| Weather | |
| Backend environment | |
| Deployment configuration revision | |

Mark each item `PASS`, `FAIL`, or `N/A`. Attach photographs and measured values.

## 1. Site and Safety

- [ ] Approved site survey is available.
- [ ] Required permits and owner approvals are available.
- [ ] Weather and work area are safe.
- [ ] Fall protection/electrical isolation procedures are followed.
- [ ] Mount structure and fasteners are suitable for expected wind load.
- [ ] Flood, runoff, snow, and falling-object risks were reviewed.
- [ ] Lightning/earth/shield plan is approved for this site.
- [ ] Technician maintenance access is practical.

## 2. Field of View

- [ ] Target scene and required distance range match design assumptions.
- [ ] No current obstruction blocks RGB or NIR view.
- [ ] Seasonal vegetation growth is unlikely to block the windows.
- [ ] Sunrise/sunset glare path has been considered.
- [ ] Mount height, azimuth, pitch, and roll are recorded.
- [ ] A reference photograph of the mounted direction is attached.

## 3. Solar and Power Installation

- [ ] Panel wattage and battery capacity match approved site design.
- [ ] Panel azimuth/tilt and horizon/shade match survey.
- [ ] Panel frame and mount are secure.
- [ ] PV and battery conductors are UV-rated and protected.
- [ ] DC disconnects and fuses are installed and labeled.
- [ ] Battery is retained, terminals protected, and temperature controlled.
- [ ] Battery voltage and state of charge are acceptable before startup.
- [ ] MPPT chemistry/profile and low-temperature policy are correct.
- [ ] Polarity is measured before closing disconnect.
- [ ] Converter input and 5.1 V output are measured.
- [ ] Pi reports no undervoltage during startup and upload.
- [ ] Charger/solar telemetry reaches device health data.

## 4. Mechanical and Enclosure

- [ ] Enclosure bracket and secondary retention are secure.
- [ ] Enclosure orientation provides drip paths and shield air gap.
- [ ] Cable glands face protected directions where practical.
- [ ] Cables have drip loops and strain relief.
- [ ] External jackets are protected from sharp edges and UV exposure.
- [ ] Pressure vent is unobstructed.
- [ ] Antenna bulkheads and boots are weather-sealed.
- [ ] Unused entries are plugged.
- [ ] Lid gasket is clean and unobstructed.
- [ ] Lid fasteners are torqued and witness-marked.
- [ ] Device label/QR is visible and durable.

## 5. Sensors and Antennas

- [ ] Temperature/RH head is in a ventilated radiation shield.
- [ ] Sensor head is outside enclosure heat plume.
- [ ] Light sensor has correct sky/scene view and no permanent shadow.
- [ ] Pressure vent/path is unobstructed.
- [ ] GNSS antenna has adequate sky view.
- [ ] LTE main/diversity antennas are on correct ports.
- [ ] Antenna spacing follows design.
- [ ] External rain/wind equipment is level/oriented/calibrated as required.
- [ ] Long sensor runs use released protected/isolated interface.

## 6. Device Startup

- [ ] Device ID and site ID are correct.
- [ ] Hardware, software, configuration, and calibration revisions are correct.
- [ ] RTC time and selected time source are valid.
- [ ] Storage mounts and reports healthy.
- [ ] Both cameras enumerate with expected identities.
- [ ] All required sensors report valid/plausible values.
- [ ] CPU, SSD, modem, enclosure, and battery temperatures are acceptable.
- [ ] Watchdog and health services are active.

## 7. Camera Aiming and Optical Validation

- [ ] RGB field of view contains complete target.
- [ ] NIR field of view contains complete target.
- [ ] No optical-window or filter vignetting is visible.
- [ ] Windows are clean and free of protective film/condensation.
- [ ] RGB and NIR focus scores pass.
- [ ] Current exposure profile avoids gross clipping/darkness.
- [ ] RGB/NIR timestamp delta is within limit.
- [ ] Registration overlay meets field tolerance.
- [ ] Alignment fasteners are locked and witness-marked.
- [ ] Enclosure closure did not shift framing.
- [ ] Final RGB, NIR, and overlay reference images are archived.

## 8. Location and Time

- [ ] Surveyed installation latitude/longitude are correct.
- [ ] Altitude value and reference are documented.
- [ ] Live GNSS fix is plausible where fitted.
- [ ] PPS/chrony status is valid where required.
- [ ] Time uncertainty meets project requirement.
- [ ] RTC holdover is available.

## 9. Network and Backend

- [ ] Ethernet route works if installed.
- [ ] Managed Wi-Fi route works if configured.
- [ ] Cellular SIM/APN registers with approved carrier.
- [ ] LTE/5G signal metrics are recorded with enclosure closed.
- [ ] Route priorities match configuration.
- [ ] Metered/raw upload policy is correct.
- [ ] TLS and device authentication succeed.
- [ ] One capture session is created and acknowledged.
- [ ] Backend asset hashes match local hashes.
- [ ] Interface failover test passes.
- [ ] Offline capture queues locally.
- [ ] Restored link uploads queued capture automatically.

## 10. Duty-Cycle and Recovery

- [ ] Capture schedule is correct in UTC.
- [ ] Missed-event policy is correct.
- [ ] Controlled shutdown completes.
- [ ] RTC wake returns the unit at the expected time.
- [ ] Modem/storage/heater load switches follow sleep policy.
- [ ] Watchdog recovery has been demonstrated on this hardware revision.
- [ ] Low-voltage policy and recovery hysteresis are enabled.

## 11. Final Site Record

- [ ] Installed equipment serials match staging record.
- [ ] Final wiring/antenna/enclosure photographs are attached.
- [ ] Panel orientation and mount measurements are attached.
- [ ] Commissioning sensor/power/network values are attached.
- [ ] Backend acceptance ID is recorded.
- [ ] Initial queue depth is zero or explained.
- [ ] No unresolved critical health event is present.
- [ ] Spare kit and service contact are available.
- [ ] Rollback/retrieval plan is confirmed.
- [ ] Site status marked `COMMISSIONED`.

## First 72-Hour Review

- [ ] Six-hour power/temperature/queue reviews completed.
- [ ] Daily battery energy balance is nonnegative or explained.
- [ ] Solar recovery reaches expected level.
- [ ] No persistent queue growth occurs.
- [ ] No unexplained reboot, watchdog, or undervoltage occurs.
- [ ] Camera quality and registration remain stable.
- [ ] No condensation, water, mount movement, or cable issue appears.
- [ ] Sensor readings track plausible site conditions.
- [ ] Site status marked `PILOT ACTIVE`.

## Sign-Off

| Role | Name | Signature/Approval | Date |
|---|---|---|---|
| Installer | | | |
| Field operations lead | | | |
| Hardware lead | | | |
| Backend/operations representative | | | |

