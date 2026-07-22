# Engineering Acceptance Test Record

| Record Field | Value |
|---|---|
| Test report ID | |
| Device/design under test | |
| Hardware revision | |
| Software image/version | |
| Configuration revision/SHA-256 | |
| Calibration package | |
| Test location | |
| Test start/end | |
| Operator | |
| Reviewer | |

## Test Equipment

| Equipment | Manufacturer/model | Serial | Calibration due |
|---|---|---|---|
| Bench supply | | | |
| DMM | | | |
| Oscilloscope | | | |
| Current probe/logger | | | |
| Temperature/RH reference | | | |
| Pressure reference | | | |
| Lux meter | | | |
| Environmental chamber | | | |
| Network impairment tool | | | |

## Requirements Traceability

| Requirement | Test ID | Result | Evidence/Deviation |
|---|---|---|---|
| FR-001 to FR-010 | CAM-TEST | | |
| FR-020 to FR-029 | DATA-NET-TEST | | |
| FR-040 to FR-048 | OPS-TEST | | |
| NFR-001 | SOAK-TEST | | |
| NFR-002 and NFR-003 | TIME-TEST | | |
| NFR-004 | CAL-GEO-TEST | | |
| NFR-005 | STORAGE-CALC/TEST | | |
| NFR-006 | NET-RECOVERY-TEST | | |
| NFR-007 | WATCHDOG-TEST | | |
| NFR-008 | BOOT-TIME-TEST | | |
| NFR-009 | INGRESS-TEST | | |
| NFR-010 | SOAK-TEST | | |
| NFR-011 | PILOT-REPORT | | |
| NFR-012 | SERVICE-TEST | | |
| NFR-013 | SECURITY-TEST | | |
| NFR-014 | HASH-TEST | | |

## CAM-TEST: Camera Functional and Timing

**Method**

1. Run 1,000 scheduled dual-camera sessions at accelerated safe interval.
2. Record enumeration, returned controls, frame timestamps, retry, and quality.
3. Inject one camera service failure and one camera disconnect before boot.

**Acceptance**

- [ ] 1,000 sessions run without unrecovered camera loss.
- [ ] Valid RGB and NIR assets are present when hardware is healthy.
- [ ] Returned fixed controls match profile within approved tolerance.
- [ ] RGB/NIR delta is below 2,000 ms for at least 99.9% of valid sessions.
- [ ] Retry is bounded to configured count.
- [ ] Camera fault creates explicit partial/failed session and health code.

**Result/Evidence**

| Metric | Expected | Actual | Result |
|---|---:|---:|---|
| Sessions attempted | 1000 | | |
| Sessions complete | >= 990 or project release target | | |
| Maximum RGB/NIR delta | <= 2000 ms | | |
| Unrecovered camera hangs | 0 | | |

## CAL-GEO-TEST: Geometric Calibration

- [ ] Final optical stack and enclosure are used.
- [ ] Target has contrast in visible and 850 nm bands.
- [ ] Training and independent validation datasets are separate.
- [ ] Median validation residual is below 2 pixels on reference plane.
- [ ] 95th percentile validation residual is below 5 pixels.
- [ ] Alignment remains within tolerance after open/close.
- [ ] Alignment remains within tolerance after thermal/vibration test.

| Metric | Expected | Actual | Result |
|---|---:|---:|---|
| Median residual | < 2 px | | |
| 95th percentile residual | < 5 px | | |
| RGB/NIR baseline | Released drawing | | |

## CAL-RAD-TEST: Radiometric and NIR Optical Validation

- [ ] NIR filter model/lot matches record.
- [ ] Visible-light blocking is demonstrated.
- [ ] No edge light leak or field vignetting.
- [ ] Dark frames collected at required temperatures/exposures.
- [ ] Flat-field maps generated.
- [ ] Reflectance references are measured without saturation.
- [ ] Repeatability target is defined and met.
- [ ] Calibration files and source dataset checksums are archived.

## SENSOR-TEST: Environmental and Power Sensors

| Sensor | Expected | Actual | Result |
|---|---:|---:|---|
| Air temperature | Reference +/-0.5 C | | |
| Relative humidity | Reference +/-3 %RH | | |
| Pressure | Reference +/-1 hPa | | |
| Illuminance/profile selection | Correct profile and hysteresis | | |
| Input voltage | Reference +/-2% | | |
| Input current | Reference +/-2% | | |
| GNSS position/time | Site requirement | | |

- [ ] Sensor disconnects time out without acquisition deadlock.
- [ ] Invalid readings are null/status, not numeric sentinels.
- [ ] Calibration IDs appear in metadata.

## POWER-TEST: Power Integrity and Energy

- [ ] Converter starts at minimum/maximum approved input.
- [ ] Combined CPU/camera/SSD/modem/heater load test completed.
- [ ] Pi input remains above 4.9 V target during normal maximum load.
- [ ] No Pi undervoltage flag occurs.
- [ ] Modem branch power cycle does not reset Pi.
- [ ] Low-voltage transitions and hysteresis pass.
- [ ] RTC wake passes 100 cycles for duty-cycled design.
- [ ] 24-hour measured energy supports sizing calculation.

| Metric | Expected | Actual | Result |
|---|---:|---:|---|
| Minimum Pi 5 V rail | > 4.9 V target | | |
| 5 V peak ripple | Project limit | | |
| Continuous average power | <= approved budget | | |
| Duty-cycle average power | <= approved budget | | |
| Battery autonomy | Site requirement | | |

## POWER-FAIL-TEST: Queue Integrity

Perform 100 uncontrolled removals distributed across capture, commit, upload,
completion, and cleanup.

- [ ] Filesystem returns to service automatically.
- [ ] Every fully committed local session remains recoverable.
- [ ] Incomplete `.part` data is quarantined/removed safely.
- [ ] No backend duplicate logical capture is created.
- [ ] No checksum mismatch is acknowledged.
- [ ] Queue database reconciles from commit records.
- [ ] Unsafe-shutdown counter and event are observable.

## DATA-NET-TEST: Storage, API, and Connectivity

- [ ] Ethernet, Wi-Fi, and cellular operate independently.
- [ ] Route priority and failover match configuration.
- [ ] 24-hour outage does not block scheduled local capture.
- [ ] Upload starts within 5 minutes after restoration.
- [ ] Backlog clears without missing new capture windows.
- [ ] Create and complete calls are idempotent.
- [ ] Wrong hash/size is rejected.
- [ ] 401, 429, 500, timeout, and DNS failures follow retry policy.
- [ ] Presigned upload expiration is recovered.
- [ ] Storage thresholds perform documented actions.
- [ ] Unacknowledged sessions are not silently deleted.

## WATCHDOG-TEST: Recovery

- [ ] Acquisition timeout kills/restarts only the failed service.
- [ ] Health-service heartbeat loss triggers hardware watchdog.
- [ ] OS reboot occurs within 2 minutes.
- [ ] Reboot reason/counters persist.
- [ ] Repeated identical fault enters degraded mode instead of reboot storm.
- [ ] External supervisor recovery passes where fitted.

## TIME-TEST: UTC and Monotonic Timing

- [ ] NTP synchronized UTC error is under 100 ms.
- [ ] GNSS PPS host alignment is under 10 ms where required.
- [ ] RTC holdover behavior is measured.
- [ ] Wall-clock correction does not corrupt within-session delta.
- [ ] Invalid time state is explicit in metadata.

## ENV-TEST: Thermal, Humidity, Ingress, and Mechanical

- [ ] Hot operating soak passes with full workload.
- [ ] Cold start/capture passes at released minimum temperature.
- [ ] Thermal cycles do not shift alignment beyond tolerance.
- [ ] Condensation challenge is detected/managed.
- [ ] Completed enclosure rain/ingress test shows no water on electronics.
- [ ] Cable pull and strain relief pass.
- [ ] Transport/vibration test causes no loose connection or alignment failure.
- [ ] Solar shield and thermal controls maintain component limits.

## SECURITY-TEST

- [ ] Port scan finds no unapproved listening service.
- [ ] Password SSH/default credentials are absent.
- [ ] Invalid and revoked credentials are rejected.
- [ ] Invalid server certificate is rejected.
- [ ] Invalid update/configuration signature is rejected.
- [ ] Diagnostics/logs contain no secret material.
- [ ] Service users and file permissions follow least privilege.
- [ ] Failed update health check rolls back.

## SOAK-TEST: 168-Hour Integrated Operation

| Metric | Expected | Actual | Result |
|---|---:|---:|---|
| Duration | >= 168 h | | |
| Scheduled commit rate | >= 99% | | |
| Unrecovered fault | 0 | | |
| Unexplained reboot | 0 | | |
| Accepted hash mismatch | 0 | | |
| Queue after network recovery | Stable/clearing | | |
| Undervoltage events | 0 | | |
| Unsafe temperature events | 0 | | |

## Deviations

| Deviation ID | Description | Risk | Disposition | Approver |
|---|---|---|---|---|
| | | | | |

## Final Disposition

- [ ] PASS
- [ ] PASS WITH APPROVED DEVIATIONS
- [ ] FAIL

| Role | Name | Signature/Approval | Date |
|---|---|---|---|
| Test operator | | | |
| Hardware reviewer | | | |
| Embedded reviewer | | | |
| Quality/release approver | | | |

