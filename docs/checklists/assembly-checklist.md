# Assembly and Factory Inspection Checklist

| Record Field | Value |
|---|---|
| Device ID | |
| Unit serial | |
| Hardware revision | |
| Work order | |
| Technician | |
| Inspector | |
| Build date | |
| Software image/version | |
| Configuration SHA-256 | |
| Calibration package ID | |

Mark each item `PASS`, `FAIL`, or `N/A`. Record evidence and deviation numbers.

## 1. Incoming Inspection

- [ ] Raspberry Pi model, memory, revision, and serial recorded.
- [ ] RGB camera model/identity recorded; lens and connector undamaged.
- [ ] NoIR camera model/identity recorded; lens and connector undamaged.
- [ ] Camera cables are correct Pi 5 22-pin to camera 15-pin type.
- [ ] SSD model, serial, capacity, and initial health recorded.
- [ ] Modem exact regional model, revision, and identity recorded securely.
- [ ] Cellular antennas match modem bands and connector type.
- [ ] NIR filter model, lot, passband, dimensions, and condition recorded.
- [ ] Optical windows are clean and transmission-compatible.
- [ ] Sensor models/addresses/lots are correct.
- [ ] DC/DC model and ratings match released BOM.
- [ ] Enclosure, gasket, vent, glands, and mounting plate match drawing.
- [ ] Battery, BMS, panel, and MPPT match approved site power design.
- [ ] No unapproved substitution is present.

## 2. Compute Assembly

- [ ] ESD controls active.
- [ ] Active cooler installed and retained correctly.
- [ ] RTC battery installed with correct polarity/connector.
- [ ] Controlled OS image checksum verified before imaging.
- [ ] Pi boots from approved source without undervoltage warning.
- [ ] RTC read/write and holdover verified.
- [ ] Recovery microSD prepared, labeled, and tested.
- [ ] SSD installed with mechanical support and correct cable orientation.
- [ ] SSD partitions/mounts match release image.
- [ ] CPU, memory, Ethernet, Wi-Fi, USB, and storage baseline tests pass.
- [ ] Hardware watchdog device is present.
- [ ] No default password or unauthenticated service remains.

## 3. Camera Assembly

- [ ] Power removed before every FFC insertion/removal.
- [ ] RGB camera connected to assigned CAM0 port.
- [ ] NIR camera connected to assigned CAM1 port.
- [ ] FFC contact orientation and latches inspected under magnification.
- [ ] Cables labeled at both ends.
- [ ] Cables have adequate bend radius and strain relief.
- [ ] Both cameras enumerate with expected model/identity.
- [ ] RGB camera produces valid test image.
- [ ] NIR camera produces valid test image.
- [ ] NIR filter is installed with no edge light path.
- [ ] Filter and windows have no protective film, fingerprint, scratch, or debris.
- [ ] Black baffles prevent internal LED/reflection contamination.
- [ ] Camera bracket revision and serial recorded.
- [ ] Alignment fasteners tightened and witness-marked.

## 4. Sensor and GPIO Assembly

- [ ] I2C bus is 3.3 V.
- [ ] Exactly one effective pull-up set is fitted.
- [ ] SDA/SCL idle levels and oscilloscope rise time pass.
- [ ] Total local I2C cable length is within released limit.
- [ ] SHT45 reads at address `0x44`.
- [ ] BMP390 reads at address `0x77`.
- [ ] VEML7700 reads at address `0x10`.
- [ ] INA228 reads at address `0x40`.
- [ ] Optional ADS1115 address is `0x48` and does not conflict.
- [ ] GNSS UART uses 3.3 V logic and correct baud rate.
- [ ] GNSS PPS edge is detected on GPIO18.
- [ ] External pulse inputs use released isolation/protection board.
- [ ] Service button and status LED have defined power-up states.
- [ ] Modem/heater GPIO drives a switch, not the load directly.
- [ ] Sensor disconnect fault is handled without acquisition deadlock.

## 5. Power Assembly

- [ ] Battery/source positive fuse is installed near source.
- [ ] Service disconnect is accessible and labeled.
- [ ] Input polarity and protection-stage orientation verified.
- [ ] TVS/fuse values match released electrical drawing.
- [ ] INA228 shunt has Kelvin sense routing.
- [ ] No-load converter output is set to released 5.1 V target.
- [ ] Pi, modem, storage, and auxiliary loads have separate protected branches.
- [ ] Branch wire gauges and connector current ratings match drawing.
- [ ] Modem load switch defaults to safe state.
- [ ] Heater output defaults off and has independent fuse/current limit.
- [ ] System 0 V and chassis/earth arrangement matches site design.
- [ ] 5 V at Pi remains above acceptance target during combined peak test.
- [ ] No Pi undervoltage flag occurs during modem transmit/SSD write/camera load.
- [ ] Branch short/current-limit behavior passes safe fixture test.
- [ ] Low-voltage shutdown and recovery hysteresis pass.
- [ ] RTC wake passes repeated cycle test for duty-cycled units.

## 6. Harness and Workmanship

- [ ] Harnesses match released drawing and revision.
- [ ] Contact part numbers and wire gauges are correct.
- [ ] Crimps pass visual and pull inspection.
- [ ] Ferrules are used at compatible screw terminals.
- [ ] No loose jumper wire or unsupported solder splice is present.
- [ ] Every connector is keyed or unmistakably labeled.
- [ ] Both ends of every harness are labeled.
- [ ] High-current wiring is separated from camera, GNSS, and sensor wiring.
- [ ] Coax and FFC bend radii are acceptable.
- [ ] Strain relief prevents gland force reaching PCB connectors.
- [ ] No loose wire strand, clipped lead, or hardware remains.
- [ ] Photographs of final harness routing are attached to build record.

## 7. Enclosure and Mechanical Assembly

- [ ] Enclosure machining matches released drawing and is deburred.
- [ ] Empty-enclosure ingress test passed before electronics installation.
- [ ] Internal mounting plate is secure and bonded/isolated per design.
- [ ] Camera optical datums are not carried by flexible cable or lid gasket.
- [ ] RGB and NIR windows are installed with controlled gasket compression.
- [ ] Hydrophobic vent is installed in protected orientation.
- [ ] Glands match cable diameter and are torqued.
- [ ] Unused entries have rated plugs.
- [ ] External cable entries use drip loops/downward paths.
- [ ] LTE/GNSS antenna bulkheads are labeled and weather-sealed.
- [ ] Radiation shield is separated from enclosure heat and direct sun.
- [ ] White solar shield has specified air gap.
- [ ] Pole/wall mount and secondary retention are installed correctly.
- [ ] Gasket and mating surface are clean.
- [ ] No cable crosses the lid gasket.
- [ ] Lid fasteners are torqued in specified pattern.
- [ ] Completed assembly ingress/moisture test passes.

## 8. Calibration

- [ ] Focus calibrated through final RGB optical stack.
- [ ] Focus calibrated through final NIR filter/window stack.
- [ ] Hot/cold focus verification completed.
- [ ] Fixed RGB exposure/color-gain profiles approved.
- [ ] Fixed NIR exposure/gain profiles approved.
- [ ] Geometric calibration dataset and residual report complete.
- [ ] Pair registration meets acceptance limit.
- [ ] Dark and flat-field datasets captured.
- [ ] Reflectance reference method documented.
- [ ] SHT45 assembled-head calibration/verification passes.
- [ ] BMP390 pressure verification passes.
- [ ] VEML7700 assembled-path profile test passes.
- [ ] INA228/shunt calibration passes.
- [ ] GNSS position/PPS validation passes where fitted.
- [ ] Calibration file IDs and checksums recorded.

## 9. Software and Interface Acceptance

- [ ] Configuration schema validation passes.
- [ ] Camera identities match calibration package.
- [ ] One complete local session commits atomically.
- [ ] Asset sizes and SHA-256 values match.
- [ ] Backend create request is idempotent.
- [ ] Asset upload and completion acknowledgement pass.
- [ ] Duplicate completion returns same logical acknowledgement.
- [ ] Offline session queues and uploads after link restoration.
- [ ] Sensor failure creates null/status without losing valid images.
- [ ] Camera failure creates explicit partial or failed session.
- [ ] Storage-pressure policy follows configuration.
- [ ] Watchdog and systemd recovery tests pass.
- [ ] Diagnostics bundle contains required data and no secrets.
- [ ] Signed update/rollback test passes when update is enabled.

## 10. Final Release

- [ ] 1,000-cycle camera integration test passed for design/unit as required.
- [ ] 100-event power-interruption test passed for release design.
- [ ] 168-hour soak passed.
- [ ] Factory acceptance report approved.
- [ ] All deviations are approved and linked.
- [ ] Device/site labels and QR code are legible.
- [ ] SIM and service ports are closed and sealed.
- [ ] Optical windows have final clean inspection.
- [ ] Final reference RGB/NIR images archived.
- [ ] Build record, photos, test reports, and calibration package uploaded.
- [ ] Unit status marked `RELEASED FOR PILOT`.

## Sign-Off

| Role | Name | Signature/Approval | Date |
|---|---|---|---|
| Assembly technician | | | |
| Quality inspector | | | |
| Hardware lead | | | |
| Embedded lead | | | |

