# AIoT Autonomous RGB + NIR Remote-Sensing Device

## Hardware and Embedded-System Engineering Specification

| Field | Value |
|---|---|
| Document ID | AIOT-HW-SPEC-001 |
| Revision | 1.0 |
| Status | Prototype Design Baseline / PDR |
| Baseline date | 2026-07-22 |
| Owner | Hardware and Embedded Systems Team |
| Target platform | Raspberry Pi 5 |
| Intended lifecycle stage | EVT prototype and 30-day field pilot |

### Revision History

| Revision | Date | Description |
|---|---|---|
| 0.1 | 2026-07-22 | Initial architecture and requirements baseline |
| 1.0 | 2026-07-22 | Implementation-ready prototype specification |

### Approval Record

| Role | Name | Approval | Date |
|---|---|---|---|
| Product owner | TBD | Pending | TBD |
| Hardware lead | TBD | Pending | TBD |
| Embedded lead | TBD | Pending | TBD |
| Backend lead | TBD | Pending | TBD |
| Field operations lead | TBD | Pending | TBD |

---

## 1. Executive Summary

This document defines a field-deployable, autonomous remote-sensing node built
around a Raspberry Pi 5, one Raspberry Pi Camera Module 3 for visible-light
imaging, one Camera Module 3 NoIR for near-infrared imaging, environmental
sensors, local nonvolatile storage, and Ethernet, Wi-Fi, or cellular backhaul.
The node is intended to operate unattended, acquire a complete observation
every 10 to 30 minutes, preserve observations through network outages, and
deliver authenticated data to a cloud backend.

The prototype architecture uses the two independent MIPI camera connectors on
Raspberry Pi 5. Both cameras remain mechanically fixed and are calibrated as a
pair. The RGB camera retains its factory infrared-cut optical path. The NoIR
camera must receive an external narrow NIR optical filter; without this filter,
the NoIR image contains both visible and infrared energy and is not an isolated
NIR measurement. The baseline filter is an 850 nm band-pass filter with an
approximately 40 to 80 nm full-width passband. A 715 nm long-pass filter is a
lower-cost alternative but is less spectrally selective.

The Camera Module 3 pair does not provide a documented external trigger input
for deterministic hardware synchronization. The baseline therefore uses
closely timed sequential captures, individual timestamps, a rigid low-baseline
mount, and geometric image registration. This is suitable for fixed scenes and
relative vegetation monitoring after validation. It is not equivalent to a
laboratory multispectral camera. Scenes with wind-driven foliage, nearby
three-dimensional structure, or rapidly changing illumination may require
triggerable global-shutter sensors or a beam-splitter optical system.

The reference sensor set is:

- Sensirion SHT45 for external air temperature and relative humidity.
- Bosch BMP390 for barometric pressure.
- Vishay VEML7700 for ambient illuminance.
- Texas Instruments INA228 for battery/input power monitoring.
- u-blox MAX-M10S GNSS, or modem-integrated GNSS, when location and PPS time
  synchronization are required.
- Optional protected pulse or RS-485 interfaces for rain and wind instruments.

The system supports two deployment power profiles:

1. **Continuous profile:** Pi, storage, and network remain powered. This profile
   has the simplest recovery behavior and is recommended for AC, PoE, or sites
   with a large solar system.
2. **Duty-cycled solar profile:** the Pi uses its real-time clock wake alarm and
   low-power halt mode. The modem, SSD, fan, and heaters are load-switched. This
   materially reduces energy use but adds boot-cycle, timing, and shutdown
   requirements.

The baseline outdoor assembly uses an opaque UV-stable polycarbonate IP66
enclosure, a white solar shield, separate optical windows, an IP-rated pressure
equalization vent, sealed cable glands, a metal internal mounting plate, and a
rigid external pole or tripod bracket. Any window, gland, vent, or drilled hole
invalidates the enclosure vendor's original ingress claim unless the completed
assembly is tested.

The prototype is expected to proceed through bench EVT, environmental DVT, and
a 30-day pilot. Production deployment must not begin until the project closes
the site-specific design inputs listed in Section 2.4 and passes the acceptance
criteria in Section 18.

---

## 2. Scope, Assumptions, and Design Inputs

### 2.1 In Scope

The hardware and embedded team owns:

- Compute platform, carrier hardware, cameras, sensors, storage, power
  conversion, network adapters, enclosure, wiring, and field mounting.
- Camera setup, calibration, capture scheduling, and deterministic capture
  parameters.
- Sensor acquisition, validation, timestamps, and metadata generation.
- Local queueing, data integrity, upload, acknowledgement, retry, cleanup, and
  observability.
- Boot, shutdown, watchdog, failure recovery, configuration, and a controlled
  update mechanism.
- Assembly, calibration, commissioning, maintenance, and troubleshooting
  documentation.

### 2.2 Out of Scope

The following are backend or analytics responsibilities except for interface
requirements:

- Fleet dashboard and database design.
- Cloud infrastructure and user-facing authentication.
- Production NDVI algorithm, AI inference, or visualization.
- Agronomic interpretation and scientific claims.
- Long-term cloud retention.

The hardware team must nevertheless preserve enough radiometric, geometric,
time, health, and provenance metadata for those systems to operate correctly.

### 2.3 Prototype Design Assumptions

| Parameter | Baseline assumption | Design action if false |
|---|---|---|
| Capture interval | 15 minutes, configurable 10 to 30 minutes | Recalculate storage, data plan, and energy |
| Scene | Fixed outdoor vegetation or terrain | Moving platform requires IMU and triggerable cameras |
| Typical target distance | 2 m to infinity | Near targets require tighter parallax analysis |
| Network | Intermittent but available at least once per day | Increase local storage and autonomy |
| Primary cellular generation | 4G LTE Cat 4 | Validate carrier sunset plans before long deployment |
| Ambient prototype range | 0 to 45 C | Add controlled heating/cooling or substitute cameras |
| Internal target range | 5 to 45 C | Thermal redesign if exceeded |
| Ingress target | Completed assembly equivalent to IP65 or better | Formal certification if contractual |
| Autonomy | 2 days without solar input | Increase battery for site weather requirement |
| Solar resource for planning | 4 peak-sun-hours/day | Use site-specific worst-month solar data |
| Image profile | JPEG preview plus optional raw/DNG | Confirm backend and data-plan constraints |
| Position accuracy | 5 m class in open sky | Use surveyed location or RTK for higher accuracy |

### 2.4 Mandatory Site Inputs Before Procurement Freeze

The following values are design gates, not optional refinements:

- Deployment country, carrier, LTE/5G bands, SIM/APN, antenna rules, and radio
  certification requirements.
- Site latitude/longitude, worst-month peak sun hours, shade, panel orientation,
  wind loading, and lightning exposure.
- Expected ambient temperature, solar loading, humidity, condensation, salt,
  dust, insects, and precipitation.
- Required battery autonomy and acceptable missed-capture behavior.
- Target distance, field of view, mounting height, scene motion, and required
  RGB-to-NIR registration error.
- Whether outputs are qualitative trends, calibrated reflectance products, or
  data intended for scientific publication.
- Required image encoding and maximum monthly cellular data volume.
- Backend base URL, certificate trust chain, device enrollment, idempotency,
  maximum object size, and acknowledgement semantics.
- Local electrical code, grounding practice, mast/pole requirements, and
  maintenance access.

### 2.5 Engineering Conventions

- All timestamps are UTC using RFC 3339 with fractional seconds.
- All electrical voltages are DC unless marked otherwise.
- Costs are prototype planning ranges in USD as of the document baseline date;
  they are not supplier quotes.
- GPIO numbers are Broadcom GPIO numbers, not physical header pin numbers.
- The words **shall**, **should**, and **may** mean mandatory, recommended, and
  optional respectively.

---

## 3. Functional Requirements

### 3.1 Acquisition Requirements

| ID | Requirement | Verification |
|---|---|---|
| FR-001 | The device shall capture one RGB and one NIR observation per scheduled capture session. | Functional test |
| FR-002 | The interval shall be configurable from 10 to 30 minutes without rebuilding software. | Configuration test |
| FR-003 | Every image shall carry camera identity, sensor timestamp, host UTC timestamp, exposure, analogue gain, lens position, resolution, encoding, and checksum. | Metadata inspection |
| FR-004 | The device shall acquire temperature, humidity, pressure, ambient light, input/battery voltage, input/battery current, and available location fields. | Sensor test |
| FR-005 | Sensor failure shall not discard otherwise valid images; failed values shall be null with explicit status. | Fault injection |
| FR-006 | The device shall use fixed, version-controlled camera parameter profiles during production captures. | Config and EXIF/metadata inspection |
| FR-007 | RGB and NIR capture start times shall be separated by no more than 2 seconds in the baseline sequential mode. | Timestamp analysis |
| FR-008 | The device shall support a burst mode of RGB-NIR-RGB for high-motion-risk scenes. | Functional test |
| FR-009 | The system shall reject or flag images that are blank, grossly underexposed, grossly saturated, or unavailable. | Image-quality test |
| FR-010 | Calibration version and camera-pair geometry version shall be stored with every session. | Metadata inspection |

### 3.2 Storage and Transfer Requirements

| ID | Requirement | Verification |
|---|---|---|
| FR-020 | Every capture shall be committed atomically to local persistent storage before upload. | Power-fail test |
| FR-021 | The local queue shall survive unclean reboot without losing a fully committed session. | Repeated power-fail test |
| FR-022 | The device shall calculate SHA-256 for each asset and include byte size and media type. | Hash comparison |
| FR-023 | Upload shall use HTTPS with unique per-device credentials. | Security inspection |
| FR-024 | The uploader shall be idempotent and shall not create duplicate backend sessions after retries. | Network fault test |
| FR-025 | The device shall retain unacknowledged data during network outages subject to storage policy. | 24-hour outage test |
| FR-026 | Local data shall be marked acknowledged only after a backend completion response validates the session and asset checksums. | Protocol test |
| FR-027 | Cleanup shall delete acknowledged sessions oldest-first and shall never silently delete unacknowledged sessions. | Storage-pressure test |
| FR-028 | Ethernet, Wi-Fi, and cellular shall be independently configurable and assigned explicit route priorities. | Network test |
| FR-029 | The device shall recover upload automatically after link restoration or process restart. | Fault injection |

### 3.3 Operation and Maintenance Requirements

| ID | Requirement | Verification |
|---|---|---|
| FR-040 | Acquisition and upload shall start automatically after boot without interactive login. | Reboot test |
| FR-041 | A hardware watchdog shall recover a nonresponsive operating system. | Watchdog test |
| FR-042 | Each long-running service shall publish a health heartbeat and restart under systemd policy. | Service fault test |
| FR-043 | The system shall record reboot reason, boot identifier, software version, configuration checksum, and persistent error counters. | Log inspection |
| FR-044 | Configuration shall be schema-validated before activation, with rollback to the last valid copy. | Invalid-config test |
| FR-045 | Updates shall be signed and support rollback after failed boot or health validation. | OTA staging test |
| FR-046 | The system shall support safe shutdown before planned power removal. | Shutdown test |
| FR-047 | A technician shall be able to export diagnostics without removing the primary data drive. | Maintenance test |
| FR-048 | The enclosure shall expose no field-service connector without a cap or ingress-rated mating part. | Visual inspection |

---

## 4. Non-Functional Requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-001 | Scheduled capture availability | At least 99% in lab soak, excluding configured daylight restrictions |
| NFR-002 | Timestamp accuracy with network time | Better than 100 ms to UTC after synchronization |
| NFR-003 | Timestamp accuracy with GNSS PPS | Better than 10 ms host timestamp alignment after validation |
| NFR-004 | RGB/NIR geometric registration | Median residual below 2 pixels on calibration plane after rectification |
| NFR-005 | Unacknowledged retention | At least 30 days in standard profile with 20% storage reserve |
| NFR-006 | Recovery after network return | Upload attempt begins within 5 minutes |
| NFR-007 | Recovery after OS hang | Automatic reboot within 2 minutes |
| NFR-008 | Cold boot to acquisition-ready | Under 90 seconds for standard profile |
| NFR-009 | Enclosure ingress | No water on electronics during project-defined rain/ingress test |
| NFR-010 | Continuous soak | 168 hours without unrecovered fault before pilot |
| NFR-011 | Pilot duration | 30 days at representative site before design freeze |
| NFR-012 | Maintainability | Camera/sensor module replacement in under 30 minutes by trained technician |
| NFR-013 | Security | No shared default password, plaintext credential, or unauthenticated upload path |
| NFR-014 | Data integrity | Zero checksum mismatch accepted as a successful upload |

The prototype is not represented as certified IP65, EMC-compliant, or
scientifically calibrated solely because it follows this specification.
Certification and scientific validation require the relevant controlled tests.

---

## 5. System Architecture

### 5.1 Logical Architecture

```text
                       OUTDOOR OBSERVATION NODE

  Scene
    |
    +--> RGB Camera Module 3 ---- CSI-0 ----+
    |                                      |
    +--> NoIR + 850 nm filter --- CSI-1 ----+--> Raspberry Pi 5
                                                   |
       External sensor head                        +--> Acquisition service
    +--> SHT45 temperature/RH ---- I2C ------------+--> Session manifest
    +--> BMP390 pressure ---------- I2C ------------+--> Quality checks
    +--> VEML7700 illuminance ----- I2C ------------+
    +--> Optional rain/wind ----- GPIO/RS-485 ------+
                                                   |
       Time/location                               |
    +--> MAX-M10S GNSS ------- UART + PPS ----------+
    +--> RTC backup battery ------------------------+
                                                   |
       Power telemetry                             |
    +--> INA228 + shunt ----------- I2C ------------+
                                                   |
                                                   v
                                         Local queue on SSD
                                                   |
                                            SHA-256 manifest
                                                   |
                      +----------------------------+------------------+
                      |                            |                  |
                   Ethernet                     Wi-Fi            4G/5G modem
                      |                            |                  |
                      +----------------------------+------------------+
                                                   |
                                                HTTPS API
                                                   |
                                            Backend/object store
```

### 5.2 Physical Architecture

The system is divided into replaceable functional assemblies:

1. **Compute plate:** Raspberry Pi 5, active cooler, RTC battery, storage
   adapter, terminal blocks, and service access.
2. **Optical head:** paired camera mount, optical windows, NIR filter, black
   baffles, optional anti-condensation heaters, and alignment features.
3. **Environmental head:** radiation shield containing the temperature/RH
   sensor, pressure path, and ambient-light optical diffuser.
4. **Communications assembly:** cellular modem or M.2 carrier, SIM, powered USB
   path, and separated LTE/GNSS/Wi-Fi antennas.
5. **Power assembly:** input disconnect, fuse, reverse-polarity protection, TVS,
   DC/DC converter, load switches, shunt, and optional solar charger/battery.
6. **Enclosure and mount:** opaque IP66 polycarbonate box, sun shield, vent,
   glands, internal aluminum plate, pole/tripod bracket, strain relief, and
   grounding hardware.

Each assembly shall have a drawing identifier and serialized label so that a
field replacement does not change calibration records invisibly.

### 5.3 Data Flow

```text
Schedule due
   |
   v
Acquire exclusive hardware lock
   |
   +--> Verify storage, time state, thermal state, and power state
   |
   +--> Select fixed exposure profile from configured schedule/lux band
   |
   +--> Configure and settle RGB camera
   |       +--> capture raw + preview
   |       +--> read final controls and timestamp
   |
   +--> Configure and settle NIR camera
   |       +--> capture raw + preview
   |       +--> read final controls and timestamp
   |
   +--> Read sensors and health telemetry
   |
   +--> Run lightweight image validation
   |
   +--> Write assets as *.part, fsync, hash, and atomically rename
   |
   +--> Commit session record to durable queue
   |
   +--> Release hardware lock
   |
   +--> Uploader creates remote session idempotently
           +--> upload missing assets
           +--> complete remote session
           +--> validate acknowledgement
           +--> mark local session acknowledged
```

Acquisition is not blocked on network availability. Upload and capture are
separate services joined by a durable queue.

### 5.4 Power Flow

```text
 OPTION A: AC/PoE SITE                 OPTION B: SOLAR SITE

 AC mains or 802.3bt                  PV panel
       |                                  |
 Listed AC/DC or PoE splitter             v
       |                           MPPT charge controller
       |                                  |
       +--------------+              LiFePO4 battery
                      |                   |
                      +--------- input disconnect
                                  |
                          fuse + reverse protection
                                  |
                         surge/TVS + EMI filtering
                                  |
                        9-36 V to 5.1 V DC/DC
                                  |
                       +----------+------------+
                       |          |            |
                    Pi branch  modem branch  heater/fan branch
                       |          |            |
                    eFuse      load switch   load switch
                       |          |            |
                    Pi 5       USB modem     controlled loads
```

High-current modem and heater loads shall not share the final thin-gauge lead
or connector used by the Pi. Star distribution from a fused terminal block
prevents modem current pulses from causing Pi undervoltage.

### 5.5 Communication Buses

| Bus | Use | Rules |
|---|---|---|
| MIPI CSI-2 port 0 | RGB camera | Use correct Pi 5 22-pin-to-camera 15-pin cable; lock connectors |
| MIPI CSI-2 port 1 | NIR camera | Same cable rule; label both ends |
| I2C1 | Local environmental and power sensors | 3.3 V only, 100 kHz baseline, less than 300 mm total cable |
| UART | GNSS NMEA/UBX | 3.3 V logic, dedicated ground, PPS on separate GPIO |
| USB 3 | LTE/5G modem or powered hub | Externally powered; verify reset/re-enumeration |
| PCIe FFC | Optional M.2 SSD HAT | Use Raspberry Pi-approved cable/adapter and mechanical support |
| Ethernet | Preferred fixed-site uplink | Shield termination per site grounding plan |
| GPIO pulse | Optional rain/wind | ESD-protected and optically isolated for long outdoor cable |
| RS-485 | Preferred remote weather instruments | Isolated transceiver, termination at cable ends, surge protection |

Long external sensor runs shall not use raw Raspberry Pi GPIO or unbuffered
I2C. Use isolated RS-485/Modbus or a remote microcontroller gateway.

---

## 6. Component Selection

### 6.1 Compute Platform

**Baseline:** Raspberry Pi 5, 4 GB RAM.

The workload is camera capture, encoding, sensor I/O, queue management, and
network transfer. Four gigabytes is sufficient when local AI inference is out
of scope. The 8 GB model may be selected when the software team intends to add
large local models or memory-heavy processing, but it increases cost without
improving camera or I/O capability.

Required accessories:

- Raspberry Pi Active Cooler or equivalent mechanically retained cooler.
- Official-compatible RTC backup battery.
- High-endurance 32 GB or larger microSD for recovery/commissioning, even when
  the primary OS boots from SSD.
- 512 GB SSD for the local data queue.
- Pi 5 camera cables with 22-pin host and 15-pin camera connectors.

The Pi 5 product brief lists two four-lane MIPI camera/display transceivers,
PCIe 2.0 x1, a real-time clock, and the requirement for a high-quality 5 V
supply. The two MIPI connectors permit both camera modules to remain attached.

### 6.2 Camera Selection

| Function | Baseline | Reason |
|---|---|---|
| RGB | Camera Module 3, standard field of view | Factory IR-cut path, autofocus available, lower distortion than wide version |
| NIR | Camera Module 3 NoIR, standard field of view | Matching sensor/lens family and no factory IR-cut filter |
| NIR isolation | 850 nm band-pass filter | Rejects visible light and narrows spectral response |
| Protective window | AR-coated optical glass with transmission verified at 850 nm | Avoids unknown tint and distortion of enclosure lid |
| Mount | Machined or accurately printed rigid common bracket | Preserves baseline, roll, pitch, and calibration |

Both Camera Module 3 variants use the Sony IMX708 11.9 megapixel sensor with
4608 x 2592 active pixels and phase-detection autofocus. The standard lens has
a substantially narrower field of view than the wide version. The standard
variant is preferred because it reduces edge distortion, window size, filter
angle shift, and registration difficulty.

Camera Module 3 documentation specifies a 0 to 50 C operating range. This is a
material outdoor design constraint. For sub-zero sites, provide controlled
heating and verify cold starts, or select industrial cameras rated for the
site. For high solar load, use a white shade, thermal conduction to the mounting
plate, and temperature-based scheduling or shutdown.

### 6.3 NIR Filter Selection

The NoIR designation means that the camera lacks the normal infrared-blocking
filter. It does not mean the sensor measures only NIR. A filter is mandatory for
an NIR channel suitable for vegetation-index experiments.

**Baseline filter specification:**

- Center wavelength: 850 nm.
- Full width at half maximum: 40 to 80 nm.
- Peak transmission: greater than 80% preferred.
- Optical density outside passband: OD3 or better over the visible band
  preferred.
- Clear aperture: large enough to avoid vignetting at the selected lens field.
- Environmental mounting: internal, dry, blackened holder with no edge light
  leak.

An 850 nm filter aligns with the high reflectance plateau of healthy vegetation
and is well separated from the red channel. A 715 nm long-pass filter is easier
to source and passes more energy, but it creates a broad, sensor-dependent NIR
measurement that is harder to compare between devices.

Interference filters shift passband with incidence angle. The filter shall be
mounted close to normal incidence, and the optical stack shall be tested across
the full field. A narrow filter on a very wide-angle camera may produce
position-dependent spectral shift and vignetting.

### 6.4 Environmental Sensors

#### 6.4.1 Temperature and Humidity

**Baseline:** Sensirion SHT45 on a protected carrier.

The SHT45 offers better humidity accuracy and long-term behavior than many
low-cost hobby modules. It shall be located in an external naturally ventilated
radiation shield, not inside the electronics enclosure. Heat from the Pi can
otherwise bias temperature by several degrees and corrupt relative humidity.

Use a PTFE membrane or vendor protective cover compatible with the sensor, a
downward-facing drip path, and a replaceable insect screen. Do not pot or coat
the humidity opening. The cable between the shield and enclosure should be
short. For a longer mast cable, place a small microcontroller in the sensor head
and return measurements over isolated RS-485.

#### 6.4.2 Barometric Pressure

**Baseline:** Bosch BMP390.

The pressure sensor may be inside the enclosure only if an IP-rated pressure
equalization vent connects the enclosure air volume to atmosphere. It shall be
kept away from heat sources and rapid airflow from fans. Pressure is optional
for the minimum image product but useful for environmental context and system
diagnostics.

#### 6.4.3 Ambient Light

**Baseline:** Vishay VEML7700.

The sensor shall view the sky or scene illumination through a dedicated
diffuser with known visible transmission. Mounting it behind a tinted enclosure
lid invalidates absolute lux readings unless calibrated in the assembled
optical path. Use illuminance primarily to choose among fixed exposure profiles
and to identify night or heavily obscured captures.

Lux is a photopic human-vision quantity and is not an NIR irradiance
measurement. It cannot normalize the NIR channel by itself.

#### 6.4.4 Battery and Input Power

**Baseline:** TI INA228 plus a four-terminal external shunt sized for the system
current.

Place the shunt on the battery/input high side before branch distribution. Use
Kelvin sense routing and a fuse before the monitor assembly. Record voltage,
current, power, accumulated charge where supported, minimum voltage since boot,
and low-voltage events. A 10 mOhm shunt produces 100 mV at 10 A and dissipates
1 W; select power rating and measurement range with margin.

#### 6.4.5 GNSS

**Baseline when required:** u-blox MAX-M10S with an active external antenna.

Use GNSS when the node location may change, when surveyed coordinates are not
available, or when a PPS signal is needed for time discipline. A permanently
fixed node may instead store surveyed coordinates and use network time plus the
Pi RTC. If the cellular modem provides a documented GNSS and PPS interface,
that function may replace the separate receiver after field validation.

Place the GNSS antenna above the enclosure with a sky view and at least 100 mm
from cellular transmitting antennas where practical. Use the antenna vendor's
ground-plane and cable recommendations. Persist last known coordinates but mark
them stale when no current fix is available.

#### 6.4.6 Optional Rain and Wind

- A tipping-bucket rain gauge typically provides a reed-switch pulse. Interface
  through surge protection, hardware debounce, and an optocoupler or isolated
  digital input.
- A cup anemometer may provide pulse frequency; a wind vane may require an ADC.
  Use an ADS1115 only for short protected wiring. Prefer an RS-485 weather
  transmitter for long outdoor runs.
- Pulse counters must persist regularly enough that a reboot does not erase a
  large measurement interval.

### 6.5 Storage

**Baseline:** 512 GB NVMe or USB 3 SSD using 3D TLC NAND from a reputable vendor.

The OS and data queue shall be separate partitions. The data partition uses
ext4 with periodic health checks. The root filesystem should use a read-only or
overlay strategy after commissioning to reduce corruption risk. The data queue
shall not reside solely on a consumer microSD card.

Preferred storage hierarchy:

```text
Recovery microSD
  +--> diagnostics, re-image tools, encrypted configuration backup

SSD partition 1
  +--> A/B or recoverable operating-system deployment

SSD partition 2
  +--> /var/lib/aiot/queue
  +--> /var/lib/aiot/calibration
  +--> bounded persistent logs
```

For production, evaluate an industrial-temperature SSD with published
endurance, health telemetry, and power-loss behavior. Consumer NVMe devices may
throttle or reset in a sealed hot enclosure.

### 6.6 Connectivity

#### Ethernet

Ethernet is preferred for fixed sites when a protected cable path exists. Use a
surge-protected entry, outdoor-rated cable, and a documented shield/earth
strategy. Do not connect a mast shield casually to signal ground.

#### Wi-Fi

Wi-Fi is suitable when the access point is controlled and signal strength is
verified at the installed enclosure. An external antenna may be required for a
metal mounting environment. Log RSSI and reconnect events.

#### 4G LTE

**Prototype reference:** Quectel EG25-G on a reputable USB or M.2 carrier with
SIM holder, ESD protection, and external main/diversity antennas.

The exact modem variant shall be selected only after matching its supported
bands and certifications to the country and carrier. LTE Cat 4 is normally
adequate for periodic image upload and has lower cost and power than 5G.

The modem shall have a dedicated power branch capable of its documented peak
current. It shall not draw high-current transmit pulses through the Pi USB
power path. The carrier shall expose a controllable power/reset input or be fed
through a load switch so software can recover a wedged modem.

#### 5G

5G, for example a Quectel RM520N family device, is optional. It increases peak
power, heat, antenna count, cost, and integration effort. Select it only when
upload latency or local carrier coverage justifies it. Validate USB 3 signal
integrity, enclosure temperature, SIM/eSIM support, and regional approval.

#### Interface Priority

Default route priority is:

1. Ethernet.
2. Managed Wi-Fi.
3. Cellular.

The device may override this order by site configuration. Cellular data-cost
policy may prohibit raw-image upload except during a scheduled window.

### 6.7 Enclosure and Mechanical Components

Use an opaque, UV-stabilized polycarbonate IP66/NEMA 4X class enclosure in the
approximate 300 x 250 x 150 mm range for the first prototype. Fibox ARCA,
Hammond, Polycase, and equivalent industrial families are candidates; select a
locally available enclosure only after verifying dimensions, material, gasket,
UV rating, and mounting accessories.

Required enclosure features:

- Removable internal aluminum or galvanized mounting plate.
- Stainless external fasteners and captive lid hardware.
- Downward-facing cable entries where practical.
- IP68 cable glands with strain relief and fitted cable diameter.
- One hydrophobic pressure equalization vent.
- White solar/rain shield separated from the enclosure by an air gap.
- Separate optical windows, not a clear enclosure lid.
- Black internal camera tunnel and baffles to suppress reflections.
- Desiccant holder for commissioning and a humidity indicator card.
- Tamper-evident label and external device serial/QR label.
- Pole or tripod mounting bracket that does not rely on plastic lid screws.

### 6.8 Selection Summary and Alternatives

| Subsystem | Baseline | Alternative | Switch when |
|---|---|---|---|
| Compute | Pi 5 4 GB | Pi 5 8 GB or Compute Module platform | Local AI or production carrier needed |
| RGB camera | Camera Module 3 standard | Industrial global-shutter RGB | Motion/sync/rating requirement fails |
| NIR camera | Camera Module 3 NoIR + 850 nm filter | Monochrome triggerable NIR camera | Scientific calibration or sync required |
| Temp/RH | SHT45 | Modbus weather probe | Cable exceeds 0.3 m or harsh site |
| Pressure | BMP390 | Integrated Modbus probe | Long cable/industrial calibration |
| Lux | VEML7700 | Calibrated irradiance sensor | Radiometric normalization required |
| GNSS | MAX-M10S | Modem GNSS or surveyed coordinates | Minimize parts for fixed site |
| Storage | 512 GB SSD | Industrial SSD, 1 TB SSD | Heat/endurance or longer outage |
| WAN | EG25-G class LTE | Regional LTE or 5G modem | Carrier/band review |
| Power | 12 V input + 5.1 V industrial DC/DC | 24 V plant supply or 802.3bt PoE | Site infrastructure |
| Outdoor bus | Protected I2C locally | Isolated RS-485 | Long cable or surge exposure |

---

## 7. Electrical Architecture and Wiring

### 7.1 GPIO Allocation

The controlled wiring schedule is also provided in `docs/wiring.csv`.

| Function | BCM GPIO | Header pin | Direction | Notes |
|---|---:|---:|---|---|
| I2C SDA | GPIO2 | 3 | Bidirectional | 3.3 V, common sensor bus |
| I2C SCL | GPIO3 | 5 | Output | 100 kHz baseline |
| GNSS UART TX | GPIO14 | 8 | Output | Pi to GNSS RX, optional |
| GNSS UART RX | GPIO15 | 10 | Input | GNSS to Pi TX, optional |
| GNSS PPS | GPIO18 | 12 | Input | Edge timestamp, protected |
| Rain pulse | GPIO17 | 11 | Input | Through isolated/protected interface |
| Wind pulse | GPIO27 | 13 | Input | Through isolated/protected interface |
| Service button | GPIO22 | 15 | Input | Local debounce, safe diagnostic action |
| Status LED | GPIO23 | 16 | Output | Use transistor if more than a few mA |
| Modem power/reset | GPIO24 | 18 | Output | Drives load switch/isolator, not modem directly |
| Heater enable | GPIO25 | 22 | Output | Drives MOSFET/load switch |
| Spare interrupt | GPIO5 | 29 | Input | Sensor alert or tamper input |
| Spare chip select | GPIO8 | 24 | Output | Reserve for SPI expansion |

The Pi header shall not directly source a heater, fan, relay coil, modem, or
external cable. Every such load uses a transistor, load switch, or isolated
interface with defined power-up state.

### 7.2 I2C Address Map

| Device | Address | Placement |
|---|---:|---|
| VEML7700 | 0x10 | External light head |
| INA228 | 0x40 | Power board |
| SHT45 | 0x44 | Radiation shield |
| Optional ADS1115 | 0x48 | Protected expansion board |
| BMP390 | 0x77 | Enclosure near vent |

Requirements:

- Bus voltage shall be 3.3 V.
- Exactly one effective set of pull-ups shall be fitted. Start with 4.7 kOhm
  and verify rise time with an oscilloscope.
- Use 33 to 100 Ohm series damping at the Pi for a cable leaving the compute
  plate.
- Route SDA with ground and SCL with ground in twisted pairs where possible.
- Add low-capacitance ESD protection at the enclosure boundary.
- Keep the complete unbuffered bus below approximately 300 mm and verify it at
  100 kHz under cold/hot conditions.
- Do not hot-plug unprotected I2C.

### 7.3 CSI Wiring

Raspberry Pi 5 uses 22-pin MIPI connectors while Camera Module 3 uses the
traditional 15-pin camera connector. Use designated Pi 5 camera cables, not
display cables of uncertain pinout.

Assembly requirements:

1. Power shall be removed before inserting or removing an FFC.
2. The exposed contacts shall face the connector contact side specified by the
   board silkscreen and cable documentation.
3. The latch shall be fully seated and visually inspected under magnification.
4. The cable shall have a relaxed bend radius and shall not pass across the fan.
5. Each end shall be labeled `RGB/CAM0` or `NIR/CAM1`.
6. A clamp shall prevent enclosure vibration from loading the connector.
7. Camera enumeration shall be recorded before optical-head closure.

### 7.4 Power Input and Protection

The baseline accepts a nominal 12 V battery/plant input and tolerates the
selected converter's verified input range. A 24 V site may use the same
architecture with appropriately rated components.

```text
Battery/plant positive
   |
   +-- service disconnect
   |
   +-- branch fuse sized for wire and expected fault current
   |
   +-- reverse-polarity MOSFET or ideal-diode controller
   |
   +-- TVS diode selected for nominal bus and converter limits
   |
   +-- common-mode/differential EMI filtering as validated
   |
   +-- INA228 shunt and Kelvin sense
   |
   +-- industrial 5.1 V DC/DC converter
          |
          +-- Pi eFuse branch
          +-- modem/hub load-switch branch
          +-- SSD branch if independently powered
          +-- fan/heater branch
```

Protection component values depend on the source transient environment. A
vehicle, long outdoor cable, solar battery, and indoor listed adapter have
different surge requirements. The final TVS standoff, fuse interrupt rating,
wire gauge, and grounding shall be reviewed against the actual source.

### 7.5 5 V Distribution

The 5 V converter shall provide at least 8 A continuous at enclosure
temperature, with a preferred 10 A class rating and adjustable output set to
5.1 V at the distribution block. A Mean Well DDR-60G-5 class converter is a
prototype candidate for 12 V systems. Verify minimum input voltage,
temperature derating, startup behavior, ripple, and mechanical format against
the selected battery and enclosure.

Use these branch targets:

| Branch | Continuous rating | Protection | Wiring |
|---|---:|---|---|
| Raspberry Pi 5 | 5 A capability | 5 A eFuse or fuse | Short 18 AWG equivalent pair |
| Cellular modem/hub | 4 A capability | Resettable load switch plus fuse | Separate 18-20 AWG pair |
| Storage | 2 A capability | Load switch/fuse | Per carrier requirement |
| Fan and window heaters | 2 A capability | MOSFET and fuse | Separate branch |

When powering the Pi through USB-C from a non-PD industrial rail, the Pi may
apply the lower USB peripheral current budget because no 5 A USB-PD contract is
present. The reference design therefore powers high-current USB peripherals
from their own branch. If a Pi-compatible 5 V/5 A USB-PD source is used, its
negotiation, cable current rating, and brownout behavior shall be tested.

Direct power through the 40-pin header bypasses parts of the normal input
protection and shall only be used on a designed carrier with eFuse,
reverse-current blocking, controlled sequencing, and documented service
procedure.

### 7.6 External Pulse and RS-485 Interfaces

An outdoor reed switch can experience ESD, induced surge, long bounce, and
ground-potential differences. The baseline input board shall include:

- Series fuse or fusible resistor.
- Bidirectional TVS at the cable entry.
- RC debounce and Schmitt trigger, or optocoupler isolation.
- Defined pull-up/down so a disconnected cable has a known state.
- Galvanic isolation for long runs or separate structures.
- Pluggable, keyed terminal block and shield termination point.

For RS-485, use an isolated transceiver rated for the site temperature, 120 Ohm
termination only at each physical bus end, switchable biasing at one location,
and surge protection referenced to chassis/earth as designed.

### 7.7 Connector Policy

- Internal low-voltage power: locking Micro-Fit, Mini-Fit Jr, JST-VH, or
  pluggable industrial terminal blocks sized for current.
- Sensors: keyed locking connector; never use loose Dupont jumpers in the
  deployed unit.
- External cables: circular IP-rated connectors or permanently glanded cable
  with internal pluggable terminal.
- Antennas: SMA-family bulkhead connectors with weather boots and correct
  polarity; do not mix SMA and RP-SMA.
- Every connector shall be keyed or labeled, have a pin-1 definition, and be
  represented in the wiring schedule.

### 7.8 Prototype Interface PCB

A small interface/power PCB is recommended after the first breadboard test. It
shall provide:

- Fused input and reverse-polarity protection.
- TVS footprint and input filter.
- INA228, shunt Kelvin routing, and test points.
- Four protected/load-switched 5 V branches.
- I2C connector with configurable pull-ups and series resistors.
- Protected GNSS PPS and external pulse inputs.
- MOSFET outputs for heater and modem power.
- Status LED drivers, service button, and tamper input.
- Board ID, revision, serial label area, and clearly marked test points.

Maintain separation between high-current switch loops, sensitive shunt sense
traces, MIPI/PCIe cables, GNSS antenna feed, and sensor wiring. The prototype
board is not a substitute for a formal EMC and safety review.

---

## 8. Power-System Design

### 8.1 Power Design Objectives

The power subsystem shall:

- Start the Pi, cameras, storage, and modem under worst-case temperature and
  battery voltage.
- Hold the 5 V rail above the verified undervoltage margin during CPU load,
  storage writes, camera operation, and cellular transmit bursts.
- Shut down cleanly before battery damage or converter dropout.
- Recover automatically when input power becomes valid.
- Measure energy use with enough accuracy to validate solar sizing.
- Isolate or switch nonessential loads during low-energy operation.
- Prevent a fault in a heater or modem branch from disabling the entire node.

The final design is based on measured current waveforms, not nameplate averages.
Capture startup, modem registration, cellular upload, SSD writes, heater
switching, and Pi stress concurrently while observing the 12 V input and 5 V
rail with an oscilloscope/current probe.

### 8.2 Load Budget

The controlled calculation is in `docs/power-budget.csv`. The following values
are conservative planning assumptions and shall be replaced by prototype
measurements.

| Load | Idle/standby | Active average | Design peak |
|---|---:|---:|---:|
| Raspberry Pi 5 + cooler | 4.5 W | 7.0 W | 12 W |
| Two cameras | 0.2 W | 2.5 W | 3 W |
| SSD | 0.5 W | 2.5 W | 5 W |
| Sensors and interface PCB | 0.3 W | 0.5 W | 1 W |
| LTE modem | 0.8 W | 3.5 W | 10 W |
| Window heater, optional | 0 W | 2.0 W | 4 W |
| Conversion/wiring allowance | 12% | 12% | Included in source rating |

The design peak is not the arithmetic sum of permanently simultaneous loads,
but the 5 V distribution shall tolerate at least 40 W continuous and transient
loads above that value without falling outside the validated rail range. A
50-60 W converter provides practical margin.

### 8.3 Continuous Operating Profile

For planning, use:

- 8.5 W average electrical load before autonomy margin.
- 204 Wh/day raw energy.
- 20% allowance for cold battery behavior, converter losses beyond assumptions,
  aging, retries, and heater use.
- **Design energy: approximately 245 Wh/day.**

At four peak-sun-hours per day and 70% total solar-system derating:

```text
Required panel = 245 Wh/day / (4 h/day x 0.70)
               = 87.5 W
```

A 100 W panel is the mathematical minimum under those assumptions. The baseline
recommendation is **150 W** because weather, dirt, shade, panel temperature,
orientation, and winter irradiance reduce real output.

For two days of autonomy using a 12.8 V LiFePO4 battery and 80% usable capacity:

```text
Required capacity = (245 Wh/day x 2 days) / (12.8 V x 0.80)
                  = 47.9 Ah
```

Select a **12.8 V, 50 Ah minimum** battery for this planning case. Use 100 Ah
when four days of autonomy or significant cold-weather heater use is required.

### 8.4 Duty-Cycled Solar Profile

The duty-cycled profile shuts down the operating system after queue and upload
work completes, arms the Pi 5 RTC wake alarm, and removes power from the modem,
storage where supported, fan, and heaters. An external supervisor is preferred
for deployments where a Pi firmware or shutdown failure must not prevent the
next wake.

Planning case:

- Active duration: 3 minutes per 15-minute interval, 20% duty.
- Active system power: 12 W average.
- System sleep and always-on supervisor: 0.15 W.

```text
Average = (12 W x 0.20) + (0.15 W x 0.80)
        = 2.52 W

Daily energy = 2.52 W x 24 h
             = 60.5 Wh/day
```

Apply a 25% field margin: **approximately 76 Wh/day**. A 50 W panel can satisfy
the mathematical four-sun-hour case, but the reference field build retains a
**100 W panel and 40 Ah LiFePO4 battery** to cover slow network registration,
retries, short winter days, and battery aging.

Duty cycling has tradeoffs:

- More boot and storage mount cycles.
- Less time for background upload during a prolonged backlog.
- Cellular registration can consume much of a short wake window.
- RTC, low-power halt, and load-switch sequencing become critical.
- A 10-minute schedule may make continuous operation more practical.

The embedded implementation shall measure actual awake time and automatically
remain awake when backlog, update, or diagnostic policy requires it.

### 8.5 Battery Selection

LiFePO4 is preferred over lead-acid for cycle life, usable capacity, and stable
voltage. The selected pack shall include a documented battery management
system, cell balancing, overcurrent protection, low-voltage cutoff, and
temperature-qualified charging.

Lithium batteries generally shall not be charged below the battery vendor's
allowed cell temperature. For freezing sites, select a pack with low-temperature
charge cutoff or internal heating and configure the charge controller
accordingly. Do not assume an enclosure warmed by the Pi keeps the battery
within charge limits.

Battery installation requirements:

- Install a source fuse close to the positive terminal.
- Use a service disconnect accessible without exposing live conductors.
- Size conductors for fault current and voltage drop.
- Provide retention against transport and mast vibration.
- Keep battery terminals protected from dropped tools.
- Record pack serial, installation date, rated capacity, and BMS model.
- Provide a temperature sensor thermally coupled to the pack.

### 8.6 Solar Charger and Panel

Use an MPPT controller compatible with the panel open-circuit voltage, battery
chemistry, expected cold-temperature panel voltage, maximum charge current, and
low-temperature charge policy. A controller with telemetry and configurable
load disconnect is preferred.

Panel sizing shall use the site's worst representative month, not annual
average sun. The site survey shall account for:

- Horizon and seasonal shade.
- Dust, snow, bird fouling, and cleaning interval.
- Cable voltage drop.
- Panel temperature derating.
- Controller efficiency.
- Mount angle, azimuth, and wind load.
- Several consecutive low-sun days.

The panel frame, mast, enclosure mounting plate, and surge strategy require a
site grounding review. Lightning protection cannot be solved by adding a small
PCB TVS alone.

### 8.7 Low-Voltage Policy

Use multiple thresholds with hysteresis. Example thresholds for a 12.8 V
LiFePO4 system are placeholders and shall be matched to the battery/BMS:

| State | Example action |
|---|---|
| Normal | Capture and upload all configured assets |
| Energy-saving | Defer raw upload, reduce wake duration, disable heaters unless needed for optics |
| Critical | Capture previews/metadata only or extend interval per product policy |
| Shutdown | Flush queue, arm RTC wake, and halt before converter or BMS cutoff |
| Recovery | Resume only after voltage remains above recovery threshold for configured duration |

Battery voltage alone is a poor state-of-charge indicator for LiFePO4 because
of its flat discharge curve. Use coulomb counting and charger/BMS telemetry,
then periodically reconcile at known full-charge conditions.

### 8.8 Power-Fail Behavior

The preferred design provides enough hold-up or early-warning time for a clean
shutdown. Options, in order:

1. UPS/charger with a power-fail signal and guaranteed shutdown reserve.
2. Supercapacitor hold-up sized for queue commit and OS shutdown.
3. Battery-backed source with software low-voltage shutdown before BMS cutoff.
4. At minimum, a read-only root, durable queue protocol, and tested recovery
   from abrupt removal.

The test plan includes 100 uncontrolled removals at different pipeline states.
No fully acknowledged backend session may be uploaded twice as a distinct
session, and no fully committed local session may disappear.

### 8.9 Thermal Power Controls

Heaters and fans are controlled loads:

- The Pi active cooler responds to CPU temperature.
- A small internal recirculation fan may eliminate local hot spots but does not
  cool below enclosure ambient.
- A lens-window heater is enabled only when the calculated dew point approaches
  window temperature or condensation is detected.
- A battery heater follows battery vendor requirements and has an independent
  thermostat/fuse.

Every heater output shall fail off on Pi reset and have a hardware current
limit. Thermal runaway protection shall not depend solely on application
software.

---

## 9. Camera and Optical Design

### 9.1 Camera Architecture Decision

The baseline dual-camera architecture is accepted for the prototype because it
uses the required Raspberry Pi modules, allows simultaneous physical
connection, and supports rapid field iteration. It has four limitations:

1. Separate viewpoints create parallax.
2. Separate rolling-shutter sensors are not hardware-trigger synchronized.
3. The NoIR sensor has broad and Bayer-dependent NIR response.
4. Consumer camera operating-temperature limits constrain outdoor deployment.

These limitations shall be written into dataset provenance. The prototype may
support relative vegetation monitoring, but absolute scientific equivalence to
a calibrated multispectral instrument shall not be claimed without independent
validation.

### 9.2 Mechanical Alignment

Mount both modules on one rigid reference part with:

- Optical axes parallel within the tolerance established by calibration.
- Minimum practical horizontal baseline, nominally 35 to 50 mm.
- No independent flexible stalk or adhesive-only location.
- Datum pins or pockets for repeatable replacement.
- Three-axis adjustment during engineering setup, then locking features.
- Camera identifiers visible without disassembly.
- A thermal-expansion-compatible material and fastener pattern.

The mount shall resist movement during lid operation, cable handling, vibration,
and thermal cycling. A 3D-printed bracket is acceptable for EVT if printed in a
dimensionally stable, heat-resistant material and followed by a machined or
validated molded design for pilot units.

Parallax cannot be removed globally by a homography when the scene contains
objects at materially different depths. Reduce baseline, increase target
distance, choose a reference plane, or use depth-aware registration.

### 9.3 Optical Window Design

Each camera receives a separate circular or rectangular optical window:

- Material with verified transmission across its band.
- Flatness and surface quality adequate to avoid visible blur.
- Optional broadband AR coating.
- Hydrophobic exterior coating or replaceable rain hood.
- Gasket compression controlled by a mechanical shoulder.
- Slight downward view or hood to reduce standing water.
- Blackened internal tube to prevent reflections from status LEDs and bright
  enclosure surfaces.
- Replaceable construction without moving the camera mount.

Do not use an uncharacterized clear polycarbonate enclosure cover as the camera
window. It can add distortion, birefringence, scratches, spectral attenuation,
and reflections.

The NIR filter is preferably mounted inside the protective window. This keeps
the expensive filter dry and allows the external pane to be replaced. Verify
that the protective window itself transmits the complete NIR passband.

### 9.4 Focus

Camera Module 3 autofocus is useful during commissioning, but production
captures require a fixed lens position:

1. Assemble the final camera, filter, window, gasket, and mount.
2. Bring the assembly to representative operating temperature.
3. Place a high-contrast target at the design distance and across the field.
4. Run autofocus or a controlled lens-position sweep.
5. Select the lens position using objective sharpness metrics and visual
   inspection.
6. Repeat for hot and cold limits.
7. Store the selected position separately for RGB and NIR.
8. Disable autofocus during normal capture.

NIR focus shall be calibrated through the installed 850 nm filter. Infrared
focus can differ from visible focus, and the two modules will normally require
different lens-position values.

For variable scene distances, choose a focus position and aperture/FOV that
provide sufficient depth of field, or adopt a controlled autofocus event with
strict metadata and quality checks. Continuous autofocus is not recommended for
time-series comparison because it can alter framing and fail on low-contrast
NIR scenes.

### 9.5 Exposure and White Balance

The requirement for fixed parameters is interpreted as deterministic,
versioned controls rather than one exposure value for every lighting condition.
One fixed setting cannot cover dawn, cloud, and noon without clipping or noise.

The baseline uses a small table of calibrated profiles:

| Profile | Selection input | RGB controls | NIR controls |
|---|---|---|---|
| Bright | Lux above configured threshold | Fixed short exposure/gain and fixed color gains | Fixed independently calibrated exposure/gain |
| Overcast | Mid-range lux or schedule | Fixed medium exposure/gain | Fixed medium NIR exposure/gain |
| Low light | Low lux but above capture floor | Fixed longer exposure, constrained for motion | Fixed longer NIR exposure |
| Night/skip | Below minimum lux | Skip or capture diagnostic only | Skip or capture diagnostic only |

Profile thresholds and values are calibration data, not source-code constants.
The selected profile ID and all applied/final controls are stored per image.

During commissioning, automatic exposure and white balance may be run on a
representative target to establish candidate values. Production behavior:

- `AeEnable = false`.
- `AwbEnable = false`.
- Fixed `ExposureTime` and `AnalogueGain`.
- Fixed RGB `ColourGains`.
- Fixed manual autofocus mode and `LensPosition`.
- Fixed resolution, pixel format, orientation, and image-processing settings.
- NIR color gains treated as calibration coefficients, not visual white balance.

Avoid automatic HDR, denoise changes, tone-map changes, or format changes that
are not captured in metadata. For radiometric processing, retain raw data and
record black level, Bayer order, bit depth, exposure, gain, and software
pipeline version.

### 9.6 Resolution and Encoding

**Baseline capture resolution:** full 4608 x 2592 for both modules.

Each session may contain:

- `rgb_preview.jpg`: full or reduced resolution, quality 90 baseline.
- `nir_preview.jpg`: grayscale-rendered preview for inspection.
- `rgb_raw.dng`: optional raw Bayer capture.
- `nir_raw.dng`: recommended for calibrated NIR processing.
- `metadata.json`: complete session manifest.

JPEG is suitable for visual inspection and bandwidth-constrained qualitative
processing but is nonlinear and lossy. Raw/DNG is preferred for calibrated
cross-camera indices. The backend team shall explicitly approve any workflow
that computes a scientific product from JPEG alone.

Store the original files. Image registration and cropping normally occur in
the backend so calibration algorithms can be updated without losing source
data.

### 9.7 Capture Timing

The two modules shall be initialized before the capture window where energy
permits. Baseline sequence:

```text
T0          read time state and trigger session
T0 + settle capture RGB
T0 + <2 s   capture NIR
T0 + end    read final camera metadata and sensor values
```

For motion-sensitive scenes:

```text
RGB-A -> NIR -> RGB-B
```

The backend can estimate movement between RGB-A and RGB-B and reject or flag a
session when foliage motion exceeds threshold. This costs additional energy and
storage but provides an objective temporal-consistency signal.

Simultaneous software requests to two cameras may reduce offset but do not
provide deterministic exposure-start synchronization. Measure the actual
timestamp distribution over at least 1,000 cycles before claiming a tighter
limit.

### 9.8 Timestamping

Record at least:

- Scheduler trigger UTC and monotonic timestamps.
- Capture-request monotonic timestamp.
- Sensor-reported frame timestamp when available.
- Host receive/write timestamp.
- RGB-to-NIR delta.
- Time source: GNSS PPS, NTP, RTC holdover, or unsynchronized.
- Estimated time uncertainty.
- Boot ID and monotonic uptime.

Use `CLOCK_MONOTONIC_RAW` or equivalent for within-session timing and
disciplined UTC for external correlation. Never infer a short inter-camera
delta by subtracting two wall-clock values that can step during NTP correction.

### 9.9 Geometric Calibration

Calibration shall be performed after final assembly:

1. Stabilize temperature for at least 15 minutes.
2. Place a high-contrast calibration target visible in both RGB and 850 nm.
3. Capture at multiple positions, angles, and relevant focus distances.
4. Estimate intrinsics, distortion, relative rotation, and translation for
   each camera.
5. Generate rectification maps and a reference-plane transform.
6. Validate on separate images not used for fitting.
7. Store calibration files with immutable version and checksums.
8. Recalibrate after camera, lens, filter, window, or mount replacement.

An ordinary printed checkerboard may have weak NIR contrast. Verify the target
under the actual filter; use materials with distinct NIR reflectance when
needed.

Acceptance target for the calibration plane is median residual below 2 pixels
and 95th percentile below 5 pixels after rectification. The project shall
define a larger or depth-dependent tolerance for non-planar vegetation.

### 9.10 Radiometric Calibration

For defensible cross-camera vegetation indices:

- Capture dark frames or covered-lens offsets at representative temperatures.
- Measure flat-field/vignetting response for both cameras.
- Include calibrated neutral/reflectance references in the scene when feasible.
- Normalize using exposure time, analogue gain, black level, flat field, and
  reference target.
- Characterize filter transmission and sensor response by channel.
- Avoid saturated pixels and define a minimum signal-to-noise threshold.
- Record sun angle, lux, cloud/rain context, and exposure profile.
- Revalidate after window cleaning/replacement and seasonally.

Because RGB red and NIR come from different sensors and optical paths, the raw
ratio is device-specific. Calibration coefficients shall be tied to camera
serials, filter lot, windows, and calibration date.

### 9.11 Image Quality Gates

The embedded node runs inexpensive checks before queue commit:

| Check | Example criterion | Result |
|---|---|---|
| Decode/dimensions | File decodes and dimensions match profile | Fail image if invalid |
| Mean intensity | Within calibrated range | Flag under/overexposure |
| Saturation | Saturated fraction below profile maximum | Flag or retry once |
| Darkness | Dark fraction below profile maximum | Flag |
| Sharpness | Laplacian/edge metric above per-camera baseline | Flag focus/condensation |
| Uniform blank frame | Variance above minimum | Reset camera and retry once |
| Timestamp | Present and plausible | Mark time fault |
| Inter-camera delta | Below configured maximum | Mark sync-risk fault |

Thresholds are established from known-good captures, not copied between camera
pairs. Automatic retry is limited to prevent a bad camera from blocking the
schedule or filling storage.

### 9.12 Example Picamera2 Control Intent

The implementation shall use the installed Picamera2/libcamera API version and
enumerated controls. This non-normative example shows the intended behavior:

```python
controls = {
    "AeEnable": False,
    "AwbEnable": False,
    "ExposureTime": profile.exposure_us,
    "AnalogueGain": profile.analogue_gain,
    "ColourGains": profile.colour_gains,
    "AfMode": manual_af_mode,
    "LensPosition": calibration.lens_position,
    "FrameDurationLimits": profile.frame_duration_limits_us,
}
```

After applying controls, discard enough frames for the pipeline to settle and
read the metadata from the captured request. Store actual values rather than
assuming requested values were applied exactly.

---

## 10. Sensor Integration and Calibration

### 10.1 Sensor Acquisition Timing

Sensor readings should represent conditions near the image capture:

- Read fast sensors immediately before and after the camera pair.
- Store both values or the average plus range when the difference matters.
- GNSS may run continuously or be sampled during the wake window.
- Battery minimum voltage should be tracked over the entire active cycle so a
  transmit-related sag is not missed.
- Wind/rain pulse counters use a defined integration interval independent of
  camera timing.

Every value includes unit, status, sample time, driver version, and calibration
version. Do not use sentinel numbers such as `-999`; use JSON `null` with an
error code.

### 10.2 Temperature/Humidity Calibration

Factory sensor accuracy does not eliminate assembly error. Validate the complete
radiation-shielded head against a traceable reference at:

- One nominal indoor point.
- A high-humidity point.
- A low and high temperature representative of the site where practical.

Use a stable chamber or saturated-salt method only with a documented procedure.
Calculate and store offset or polynomial correction only when repeatable bias
is demonstrated. Avoid correcting transient self-heating with an arbitrary
constant.

Acceptance for the prototype:

- Temperature error within +/-0.5 C from the reference after stabilization.
- Relative humidity error within +/-3 %RH over the tested range.
- No persistent condensation or water path to the PCB.

The product target may be tightened to the sensor's warranted performance after
the mechanical design is validated.

### 10.3 Pressure Calibration

Compare against a calibrated barometer at the same elevation. Verify:

- No enclosure pressure lag after a controlled pressure/temperature change.
- Fan operation does not cause a measurable offset.
- Vent membrane remains dry and unobstructed.
- Altitude conversion, if used, identifies the assumed sea-level pressure.

Store pressure in pascals. Altitude derived from pressure is not a replacement
for GNSS/surveyed elevation unless atmospheric assumptions are documented.

### 10.4 Illuminance Calibration

Calibrate the assembled VEML7700 path against a reference lux meter over the
profiles used for exposure selection. Test:

- Diffuser angular response.
- Enclosure shadow and mast shadow.
- Full sunlight saturation.
- Temperature behavior.
- Night noise floor.

If the sensor saturates in direct sun, change integration/gain settings or use
a characterized neutral-density diffuser. Store raw counts and conversion
settings in diagnostics.

### 10.5 Power Monitor Calibration

Use a calibrated bench supply, DMM, and load:

1. Verify zero-current offset.
2. Apply at least three current points across the expected range.
3. Measure shunt resistance by four-wire method or use its certified value.
4. Validate voltage at high and low input levels.
5. Compare integrated charge over a multi-hour load test.
6. Record coefficient and shunt serial/lot.

The monitor's common-mode and shunt voltage shall remain within data-sheet
limits under reverse, startup, and surge conditions.

### 10.6 GNSS Validation

At an open-sky site, record:

- Time to first fix after cold and warm start.
- Satellite count and constellation use.
- Horizontal accuracy estimate and fix type.
- Position scatter over at least 30 minutes.
- PPS behavior during temporary antenna obstruction.
- Recovery after modem/GNSS power cycle.

For a fixed installation, compute a surveyed or averaged position during
commissioning, store it as the installation coordinate, and separately report
live GNSS data. Do not allow a single poor fix to overwrite the installation
record.

### 10.7 Expandable Sensor Architecture

The local 3.3 V I2C bus is intentionally limited. Expansion paths are:

| Need | Recommended interface |
|---|---|
| One additional internal low-speed sensor | Existing I2C bus after address and capacitance review |
| Multiple same-address sensors | TCA9548A-class I2C switch inside enclosure |
| Analog 0-3.3 V signal | Protected ADC close to source |
| 4-20 mA industrial transducer | Precision shunt/input module with isolation |
| Remote weather station | Isolated RS-485 Modbus |
| SDI-12 environmental probe | Dedicated protected SDI-12 interface |
| High-rate IMU | SPI with local mounting and timestamp strategy |

Each new sensor requires a unique schema path, unit, validity status, calibration
record, power impact, cable protection review, and test case.

---

## 11. Embedded Software Architecture

### 11.1 Operating System Baseline

Use the current supported 64-bit Raspberry Pi OS Lite release available at
implementation freeze, pinned by image checksum and package manifest. A minimal
headless system reduces attack surface and update variability.

Required platform services:

- systemd for lifecycle, timers, watchdogs, and resource limits.
- NetworkManager for Ethernet, Wi-Fi, and cellular route policy.
- ModemManager for supported LTE/5G devices.
- chrony for network/GNSS time discipline.
- Picamera2/libcamera for camera control.
- SQLite for the durable local session queue.
- journald with bounded persistent storage.

All package versions used in release images shall be captured in a software
bill of materials.

### 11.2 Process Model

```text
aiot-config-validate.service
    |
    +--> validates schema, calibration files, secrets references, storage paths

aiot-acquire.timer --> aiot-acquire.service
    |
    +--> owns camera/sensor lock
    +--> creates complete local session
    +--> exits after bounded execution

aiot-uploader.service
    |
    +--> long-running or timer-driven queue consumer
    +--> independent of acquisition

aiot-health.service
    |
    +--> temperatures, storage, camera inventory, sensor status, network,
         queue depth, power state, watchdog notification

aiot-housekeeping.timer --> aiot-housekeeping.service
    |
    +--> retention, log rotation checks, SSD SMART/NVMe health, diagnostics

aiot-power.service
    |
    +--> low-voltage policy, RTC wake, controlled shutdown, switched loads
```

Acquisition shall be a bounded one-shot unit so a hung capture can be timed out
and killed without wedging the scheduler indefinitely.

### 11.3 Boot Sequence

1. Pi firmware and bootloader start the selected A/B or recoveryable OS.
2. Kernel initializes storage, RTC, CSI, USB, PCIe, GPIO, and watchdog.
3. Root filesystem is mounted read-only/overlay; writable data and log
   partitions are mounted.
4. Configuration and calibration checksums are validated.
5. Queue database integrity and orphaned `.part` files are reconciled.
6. Time state is classified: synchronized, RTC holdover, or invalid.
7. Sensors and cameras are inventoried by expected serial/path.
8. NetworkManager starts configured links.
9. Health service begins and notifies the service watchdog.
10. Missed persistent schedule behavior is evaluated.
11. Uploader resumes incomplete remote sessions.
12. Acquisition timer is activated.

If configuration validation fails, the device shall use the last known-good
configuration and emit a critical health event. It shall not guess defaults
that can change camera calibration or delete data.

### 11.4 Scheduling

The scheduler supports:

- Interval in minutes.
- Optional UTC-aligned boundaries, such as `00, 15, 30, 45`.
- Optional daylight window or solar-elevation policy.
- Randomized upload timing, but not randomized capture timing.
- Missed-event policy after reboot.
- Minimum spacing to prevent concurrent sessions.
- Maintenance blackout periods.

Use one authoritative scheduler. Do not combine an application loop, cron, and
systemd timer for the same capture.

Recommended missed-event policy: after a late boot, capture once if the most
recent scheduled time is within a configured grace window; never replay every
missed 15-minute event.

### 11.5 Configuration Management

The versioned YAML configuration and its validation contract are represented
by `docs/interfaces/device-config.example.yaml` and
`docs/interfaces/device-config.schema.json`. The implementation shall parse
YAML into a data structure and validate it against the JSON Schema before
activation. Production rules:

- Configuration has a schema version and monotonically increasing revision.
- Unknown keys are rejected.
- Units are explicit in key names or schema.
- Secrets are referenced, not embedded in the readable YAML.
- Activation uses write-temp, fsync, rename, validate, then atomic symlink or
  equivalent.
- Previous known-good configuration is retained.
- Applied configuration SHA-256 is recorded with every capture.
- Device-specific calibration is separate from fleet policy.

Remote configuration changes require authentication, signature validation,
staging, and health confirmation. Camera calibration values shall not be
silently overwritten by a generic fleet profile.

### 11.6 Local Queue and Atomic Commit

Each session has a generated immutable `capture_id` and directory:

```text
/var/lib/aiot/queue/YYYY/MM/DD/<capture_id>/
    metadata.json
    rgb_preview.jpg
    nir_preview.jpg
    rgb_raw.dng            # optional
    nir_raw.dng            # optional/recommended
    commit.json
```

Commit protocol:

1. Create session in a temporary directory on the same filesystem.
2. Write every asset with a `.part` suffix.
3. Flush and `fsync` each completed file.
4. Calculate SHA-256 and size.
5. Write and `fsync` metadata.
6. Write a commit record listing every expected asset and hash.
7. `fsync` the temporary directory.
8. Atomically rename the directory to its final capture ID.
9. `fsync` the parent directory.
10. Insert the committed session into SQLite in a transaction with
    `synchronous=FULL`.

On boot, directories without a valid commit record are quarantined for
diagnostics or safely removed according to age. A valid committed directory can
repopulate the database if the database update was interrupted.

### 11.7 Queue State Machine

```text
CAPTURING
    |
    v
COMMITTED_LOCAL
    |
    v
REMOTE_SESSION_CREATED
    |
    v
ASSETS_PARTIAL
    |
    v
AWAITING_COMPLETE
    |
    v
ACKNOWLEDGED
    |
    v
ELIGIBLE_FOR_CLEANUP
```

Each transition is idempotent. A reboot may repeat a request but may not create
a second logical capture. Backend state is queried or reconciled when the local
state is uncertain.

### 11.8 Storage Pressure Policy

Example thresholds:

| Used capacity | Action |
|---:|---|
| Below 80% | Normal operation |
| 80-90% | Warning; increase upload priority |
| 90-95% | Delete acknowledged data beyond minimum local retention |
| 95-98% | Stop optional raw capture or extend interval only if product policy permits |
| Above 98% | Pause acquisition rather than silently deleting unacknowledged sessions |

Any degradation in capture products shall be explicitly represented in
metadata and a health event. The default policy protects unacknowledged data.
Sites that prioritize fresh data over old data must approve a different,
documented eviction policy.

### 11.9 Logging and Diagnostics

Use structured logs with:

- UTC timestamp and monotonic uptime.
- Severity, service, event code, capture ID, boot ID, and device ID.
- No credentials, tokens, full SIM identifiers, or private keys.
- Bounded persistent retention.
- Rate limiting for repeated faults.

The diagnostics bundle should contain:

- Recent journal excerpts.
- Configuration with secrets redacted.
- Software/package versions.
- Camera and sensor inventory.
- Queue summary, not image content by default.
- Network state and signal metrics.
- Storage health and filesystem usage.
- Temperature/power history.
- Reboot and watchdog counters.

### 11.10 Watchdog Strategy

Use layered recovery:

1. Application timeout for each camera/sensor/network operation.
2. systemd restart policy for failed services.
3. systemd service watchdog heartbeat for the health supervisor.
4. Kernel hardware watchdog with approximately 30 to 60 second timeout after
   validation.
5. Optional external power supervisor that can remove and restore power if the
   Pi fails to halt or reboot.

Avoid a watchdog loop where a repeatedly failing camera causes endless rapid
reboots. Persist failure counters and enter a degraded mode after a bounded
number of resets.

### 11.11 Time Management

Time-source priority:

1. GNSS PPS plus NMEA/UBX time when fitted and valid.
2. Authenticated or controlled NTP through chrony.
3. Pi RTC holdover.
4. Invalid/unknown time.

The system shall never move a committed file solely because wall time changes.
Use immutable capture IDs and monotonic order. If UTC is invalid, continue
capture when product policy permits, mark `time_quality=invalid`, and reconcile
later without rewriting the original acquisition timing evidence.

### 11.12 Updates

Use signed image-based updates with A/B or equivalent rollback, using a mature
framework such as RAUC or Mender after platform evaluation. Production updates
shall:

- Verify signature and compatible hardware model.
- Download to inactive slot.
- Start only with adequate power and free storage.
- Preserve queue and calibration partitions.
- Boot into a probation state.
- Require camera, storage, network, and health checks before confirmation.
- Roll back automatically after repeated failed boots.

Do not use unattended full-distribution upgrades as the primary fleet update
method. Security package updates shall be integrated into a tested release
image.

### 11.13 Security Baseline

- Unique device identity and credential per node.
- TLS server validation with pinned enterprise trust policy where appropriate.
- Mutual TLS preferred; OAuth client credentials with protected private key is
  an acceptable alternative.
- SSH disabled by default or restricted to key authentication through a VPN.
- No password login, default account password, or exposed management port.
- nftables default-deny inbound policy.
- Secrets stored with restrictive permissions and preferably protected by a TPM
  2.0 or secure element.
- Signed updates and configuration.
- Boot and software measurements recorded where feasible.
- Service processes run with least privilege, read-only paths, and systemd
  sandboxing.
- Physical tamper evidence; optional lid switch.

Full-disk encryption requires an unattended key strategy. A TPM-bound key can
protect data at rest but complicates board replacement and recovery; decide
this at threat-model review.

---

## 12. Data Acquisition Pipeline

### 12.1 Session Workflow

The normative workflow is:

```text
1. Scheduler emits due event.
2. Acquisition obtains a process and hardware lock.
3. Health preflight checks:
      - configuration valid
      - storage mounted and below critical threshold
      - power above capture threshold
      - enclosure/camera temperature within policy
      - camera identities match calibration
4. Generate capture ID and record trigger timestamps.
5. Read pre-capture environmental and power values.
6. Select deterministic camera profile.
7. Capture RGB and validate.
8. Capture NIR and validate.
9. Optional capture RGB-B motion reference.
10. Read post-capture sensors and camera metadata.
11. Generate asset hashes and complete metadata.
12. Atomically commit the local session.
13. Publish queue and health metrics.
14. Release lock.
15. Uploader independently transfers and acknowledges session.
16. Power manager evaluates sleep/shutdown policy.
```

Each numbered step has a timeout and error result. The system shall not wait
indefinitely for a sensor, camera, DNS request, modem, or backend.

### 12.2 Capture ID

The capture ID shall be globally unique even when UTC is unavailable. A
recommended format is UUIDv7 when the time is valid and random UUIDv4 when it
is not, with separate fields for boot ID and monotonically increasing local
sequence.

Human-readable filenames may include a sanitized UTC timestamp but shall not be
the database identity:

```text
device-017_20260722T103000.123Z_0190...uuid_rgb_preview.jpg
```

### 12.3 Preflight Policy

| Condition | Default behavior |
|---|---|
| RGB camera unavailable | Attempt one camera reset/re-enumeration, then create failed session health record |
| NIR camera unavailable | Capture RGB only, commit partial session with explicit missing asset |
| One noncritical sensor unavailable | Continue image capture and write null/status |
| Storage unmounted | Do not capture large assets; attempt remount/recovery and raise critical fault |
| Storage above critical threshold | Follow storage-pressure policy |
| Time invalid | Capture if configured, using monotonic evidence and `time_quality=invalid` |
| Low battery | Apply energy policy or controlled shutdown |
| Camera too hot/cold | Delay, heat, cool, or skip according to component-protection policy |
| Network offline | Capture normally and queue |

A partial session is better than silently substituting data. It is not better
than damaging hardware or corrupting storage.

### 12.4 Camera Reset Escalation

1. Stop and release the Picamera2 instance.
2. Wait a bounded settle interval and re-enumerate.
3. Retry the failed camera once.
4. If failure persists, power-cycle the relevant camera rail only if the
   hardware supports safe isolated switching.
5. If both cameras or the MIPI subsystem remain unavailable, restart the camera
   service.
6. Reboot the node only after repeated session failures and according to a
   persisted backoff.

Camera FFCs are not hot-plug interfaces. A software-controlled camera power
switch requires a reviewed sequence and shall not toggle MIPI signals outside
the camera/host requirements.

### 12.5 Image Retry Policy

At most one immediate retry per camera is recommended for:

- Blank frame.
- Decode failure.
- Control mismatch outside tolerance.
- Gross underexposure/saturation when a configured adjacent fixed profile is
  allowed.

Store the rejected image in a bounded diagnostic area when useful, but do not
upload every failed attempt by default. Metadata records retry count and reason.

### 12.6 Sensor Read Policy

Each sensor driver:

- Verifies device identity at startup where supported.
- Applies documented conversion timing.
- Rejects CRC or bus errors.
- Applies calibrated coefficients.
- Enforces physical plausibility and rate-of-change checks.
- Distinguishes stale, unavailable, out-of-range, and invalid data.
- Never blocks the whole session beyond its timeout.

Example plausibility limits are deployment configuration, not universal
constants. A valid desert temperature and a failed indoor sensor may otherwise
look similar.

### 12.7 Local Commit Evidence

`commit.json` contains:

- Capture ID.
- Expected asset names.
- Size and SHA-256 for every asset.
- Metadata SHA-256.
- Commit software version.
- Commit UTC/monotonic timestamps.
- A final state value `committed_local`.

The file is generated after every asset and metadata file is durable. The
uploader ignores directories without a valid commit record.

### 12.8 Upload Concurrency

Acquisition has priority over upload for:

- Camera and storage I/O during the capture window.
- CPU thermal budget.
- Cellular power transients.

The uploader shall limit concurrency and bandwidth. A default of one capture
session and one or two assets in flight is appropriate for LTE. Pause or reduce
upload when:

- A scheduled capture is imminent.
- The 5 V rail or battery sags.
- CPU/storage temperature exceeds warning threshold.
- The link is metered and outside an approved upload window.

### 12.9 Data Cleanup

Default cleanup eligibility requires:

1. Backend completion acknowledgement.
2. Every required asset accepted with matching hash/ETag semantics.
3. Minimum local post-ack retention elapsed, nominally 24 hours.
4. Session not held for diagnostics.

Deletion is a transactional state change:

- Mark cleanup intent.
- Remove asset files.
- `fsync` directory changes.
- Remove directory.
- Commit queue record as purged with retained metadata summary.

---

## 13. Metadata and API Interface

### 13.1 Interface Principles

The hardware/backend boundary shall:

- Be versioned independently of device software.
- Support idempotent retry.
- Separate session metadata from potentially large binary assets.
- Validate content hashes and byte counts.
- Preserve partial-session status.
- Return machine-readable error codes.
- Permit future additional sensors/assets without breaking older clients.
- Avoid requiring continuous connectivity during acquisition.

The companion JSON Schema and OpenAPI files are normative starting points:

- `docs/interfaces/capture-metadata.schema.json`
- `docs/interfaces/capture-metadata.example.json`
- `docs/interfaces/openapi.yaml`

### 13.2 Metadata Top-Level Structure

```json
{
  "schema_version": "1.0.0",
  "capture_id": "0190f3d8-7a1b-7c50-a6f4-1d52b59f0101",
  "device": {},
  "time": {},
  "location": {},
  "capture": {},
  "images": [],
  "environment": {},
  "power": {},
  "network": {},
  "storage": {},
  "health": {},
  "provenance": {}
}
```

### 13.3 Required Metadata

#### Device

| Field | Description |
|---|---|
| `device_id` | Immutable fleet identifier |
| `hardware_revision` | System assembly revision |
| `unit_serial` | Human/service serial |
| `firmware_version` | Embedded software release |
| `os_image_version` | Controlled OS image |
| `boot_id` | Current boot UUID |
| `uptime_s` | Monotonic uptime at trigger |

#### Time

| Field | Description |
|---|---|
| `scheduled_at` | Intended UTC schedule time |
| `triggered_at` | Host UTC trigger time |
| `monotonic_ns` | Monotonic trigger timestamp |
| `source` | `gnss_pps`, `ntp`, `rtc`, or `invalid` |
| `synchronized` | Boolean time state |
| `uncertainty_ms` | Estimated UTC uncertainty |
| `rgb_nir_delta_ms` | Measured frame-time separation |

#### Location

| Field | Description |
|---|---|
| `installation_latitude_deg` | Commissioned fixed coordinate |
| `installation_longitude_deg` | Commissioned fixed coordinate |
| `live_latitude_deg` | Current GNSS result, nullable |
| `live_longitude_deg` | Current GNSS result, nullable |
| `altitude_m` | Ellipsoid/MSL reference explicitly identified |
| `fix_type` | GNSS fix classification |
| `horizontal_accuracy_m` | Receiver estimate |
| `fix_age_s` | Age of live fix |

#### Image Asset

| Field | Description |
|---|---|
| `asset_id` | Unique asset identity |
| `role` | `rgb_preview`, `nir_preview`, `rgb_raw`, `nir_raw`, or extension |
| `camera_id` | Logical and physical camera identity |
| `filename` | Local basename |
| `media_type` | MIME media type |
| `width_px`, `height_px` | Image dimensions |
| `byte_size` | Exact file length |
| `sha256` | Lowercase hex digest |
| `captured_at` | UTC frame/capture time |
| `sensor_timestamp_ns` | Sensor/monotonic timestamp |
| `exposure_us` | Applied exposure |
| `analogue_gain` | Applied sensor gain |
| `colour_gains` | Applied gains where applicable |
| `lens_position` | Applied manual focus position |
| `profile_id` | Fixed exposure profile |
| `quality` | Quality metrics and flags |

#### Environmental

- Air temperature in degrees Celsius.
- Relative humidity in percent.
- Pressure in pascals.
- Illuminance in lux.
- Optional rain accumulation in millimeters.
- Optional wind speed in meters/second and direction in degrees.
- Sensor status and sample times.

#### Power

- Input/battery voltage, current, and power.
- Minimum active-cycle voltage.
- Estimated state of charge and method.
- Battery temperature.
- Charger state and solar power where available.
- Energy policy state.

#### Health and Provenance

- Camera/sensor availability.
- CPU and storage temperatures.
- Storage free/used bytes and queue depth.
- Network interface, signal metrics, and offline duration.
- Configuration SHA-256.
- Calibration IDs and checksums.
- Filter model/lot and camera serials.
- Retry counters, partial-session flags, and error codes.

### 13.4 Preferred API Workflow

#### Step 1: Create or Reconcile Session

```http
POST /v1/capture-sessions
Authorization: Bearer <device credential>
Idempotency-Key: <capture_id>
Content-Type: application/json
```

The request contains metadata and an asset manifest. The backend returns:

- Existing or newly created remote session ID.
- Required/missing asset list.
- Per-asset upload URL and headers, or a direct API upload route.
- Upload expiration.
- Maximum accepted sizes.

Repeated requests with the same device ID and capture ID shall return the same
logical session, not create a duplicate.

#### Step 2: Upload Assets

For object storage:

```http
PUT <presigned-object-url>
Content-Type: image/jpeg
Content-Length: ...
X-Content-SHA256: ...
```

For direct API transfer:

```http
PUT /v1/capture-sessions/{session_id}/assets/{asset_id}
Authorization: Bearer <device credential>
Content-Type: application/octet-stream
Digest: sha-256=:base64-digest:
```

Presigned object upload is preferred because it avoids routing large image
payloads through the metadata API and can support multipart/resumable transfer.

#### Step 3: Complete Session

```http
POST /v1/capture-sessions/{session_id}/complete
Authorization: Bearer <device credential>
Idempotency-Key: <capture_id>:complete
Content-Type: application/json
```

The backend validates required assets, sizes, and hashes, then returns an
immutable acknowledgement:

```json
{
  "capture_id": "0190f3d8-7a1b-7c50-a6f4-1d52b59f0101",
  "session_id": "cs_01...",
  "state": "accepted",
  "accepted_at": "2026-07-22T10:31:42.123Z",
  "assets": [
    {
      "asset_id": "asset-rgb-preview",
      "sha256": "..."
    }
  ]
}
```

The device marks a session acknowledged only when the response matches local
capture and asset identities.

### 13.5 Multipart Fallback

A single multipart endpoint may be supported for simple deployments:

```http
POST /v1/device-captures
Idempotency-Key: <capture_id>
Content-Type: multipart/form-data

metadata: application/json
rgb: image/jpeg
nir: image/jpeg
rgb_raw: image/x-adobe-dng
nir_raw: image/x-adobe-dng
```

This is easier to implement but a failed large request may restart from zero,
proxy limits are more likely, and raw assets make the request unwieldy.
Idempotency and checksum validation remain mandatory.

### 13.6 Authentication

Preferred order:

1. Mutual TLS with a unique device certificate and private key protected by a
   TPM/secure element.
2. OAuth 2.0 client credentials using unique per-device client identity.
3. Time-limited signed device token provisioned through a secure enrollment
   process.

Never use one API key shared by the fleet. Credential rotation shall be
possible without physical recall. The device shall validate server hostname,
certificate chain, validity, and revocation policy. Time-invalid devices need a
documented certificate-validation bootstrapping strategy; do not simply disable
TLS time checks.

### 13.7 Timeout and Retry Policy

Baseline values:

| Operation | Timeout |
|---|---:|
| DNS | 10 s |
| TCP connect | 10 s |
| TLS handshake | 15 s |
| Metadata request | 60 s |
| Asset upload | 300 s per attempt, adjusted for object size/link |
| Completion request | 60 s |

Retry:

- Exponential backoff with full jitter.
- Base approximately 5 seconds.
- Maximum approximately 30 minutes during a sustained outage.
- Retry HTTP 408, 425, 429, and 5xx responses.
- Honor `Retry-After`.
- Retry transport interruption safely using the same idempotency key.
- Do not retry malformed metadata until configuration/software changes.
- On 401/403, refresh credentials once, then raise an authentication fault.
- On checksum rejection, reread and hash the local asset before retry.

Upload order is oldest-first by default, with a small reservation for current
health events. Do not starve the queue by repeatedly retrying one permanently
invalid session; quarantine it after bounded attempts and continue.

### 13.8 Response Error Model

Backend errors should include:

```json
{
  "error": {
    "code": "ASSET_HASH_MISMATCH",
    "message": "Asset digest does not match manifest",
    "retryable": false,
    "capture_id": "0190...",
    "request_id": "req_..."
  }
}
```

The device logs the stable code and request ID. Human prose is not parsed to
drive retry decisions.

### 13.9 Network Management

NetworkManager profiles shall set:

- Route metric and metered status.
- APN, SIM PIN handling, and roaming policy.
- DNS and connectivity-check policy.
- Automatic reconnect.
- Wi-Fi country code and approved SSIDs.
- Cellular data budget and upload windows.

Collect:

- Interface used for each upload.
- LTE/5G registration state.
- RSRP, RSRQ, SINR, or modem-equivalent signal metrics.
- Wi-Fi RSSI.
- Bytes sent/received by billing period.
- Reconnect and modem reset counts.

Do not treat a successful interface link as proof the backend is reachable.
Health checks should distinguish local link, DNS, TLS, authentication, and API
availability.

---

## 14. Reliability and Failure-Recovery Strategy

### 14.1 Reliability Philosophy

The device is designed so that:

- Image acquisition does not depend on current internet access.
- One failed optional sensor does not suppress all observations.
- Every persistent state transition is repeatable.
- High-current and failure-prone peripherals can be reset independently.
- The watchdog recovers a genuine hang but does not mask recurring faults.
- Logs and metadata explain degraded operation.
- Field replacement preserves traceability and triggers recalibration where
  required.

### 14.2 Failure Matrix

| Failure | Detection | Immediate response | Escalation | Data effect |
|---|---|---|---|---|
| AC/solar input loss | INA228/charger event | Continue on battery | Energy policy then clean shutdown | Queue retained |
| Sudden total power loss | Reboot reason/filesystem recovery | Reconcile queue | Raise power-fail counter | Committed sessions retained |
| Low battery | Voltage/SOC threshold | Reduce optional loads | Halt with RTC wake | Explicit degraded product |
| Pi OS hang | Hardware watchdog | Automatic reboot | External supervisor cycle | In-progress session may be quarantined |
| Acquisition process hang | systemd timeout | Kill/restart service | Reboot after repeated failures | Current session incomplete |
| RGB camera failure | Capture timeout/quality check | Reinitialize and retry once | Degraded NIR-only/health event | Partial session |
| NIR camera failure | Same | Reinitialize and retry once | Degraded RGB-only/health event | Partial session |
| Both cameras missing | Inventory mismatch | Stop image capture | Reboot then service required | Health only |
| Sensor missing | I2C/UART status | Retry bounded | Mark null/error | Images retained |
| I2C bus stuck | Bus timeout | Driver reset/unbind | Power-cycle sensor rail or reboot | Sensor fields missing |
| SSD full | Threshold | Delete eligible acknowledged data | Pause capture at critical limit | No silent unacked deletion |
| SSD corrupt/unmounted | Mount/SMART error | Remount read-only/recover | Switch to emergency storage if designed | Capture limited |
| Internet unavailable | Reachability state | Queue locally | Backoff and retry | No immediate loss |
| Modem wedged | No AT/QMI response | Restart ModemManager | Load-switch modem, then reboot | Queue retained |
| Authentication rejected | HTTP 401/403 | Refresh once | Critical credential event | Queue retained |
| Hash mismatch | Completion/API response | Rehash and retry | Quarantine asset/session | No false acknowledgement |
| RTC/NTP invalid | Time state | Use monotonic and flag | GNSS/NTP recovery | Time uncertainty recorded |
| Overtemperature | Sensor threshold | Throttle/pause upload | Halt until hysteresis recovery | Capture skipped/flagged |
| Window condensation | Image sharpness/internal RH | Enable heater if allowed | Skip/flag and service alert | Quality flag |
| Enclosure ingress | Humidity/tamper/inspection | Disconnect unsafe power if needed | Field replacement | Potential unit quarantine |

### 14.3 Reboot-Storm Prevention

Persist timestamps and reasons for service restarts and reboots. Example policy:

- Up to three service restarts in 30 minutes.
- One automatic OS reboot after service escalation.
- If the same fault recurs after reboot, enter degraded mode for at least one
  schedule interval and continue health reporting.
- Limit autonomous power cycles per day.
- Require remote or local service after the maximum is exceeded.

Thresholds shall be tuned in soak tests. The unit should remain observable
rather than continuously rebooting and consuming battery.

### 14.4 Storage Integrity

- Use a stable, quality SSD with adequate thermal margin.
- Keep at least 20% free for performance and retention planning.
- Monitor NVMe/SMART health, media errors, unsafe shutdown count, spare, and
  temperature where supported.
- Use ext4 and controlled mount options.
- Keep SQLite transactionally consistent and rebuildable from commit records.
- Bound logs and core dumps.
- Test filesystem recovery after abrupt removal.
- Keep calibration and identity backed up in a controlled secure repository.

RAID is not justified for a single-node prototype. Reliable queue semantics,
backlog monitoring, prompt upload, and replaceable storage provide more value
than adding a second uncoordinated consumer device.

### 14.5 Network Resilience

- Network loss never blocks capture.
- Retry state is persisted.
- Interface failover does not reset the capture ID.
- Partially uploaded assets are reconciled with backend state.
- A modem power cycle is separated from a Pi reboot.
- Data-plan exhaustion is a distinct health condition.
- SIM and antenna failures are distinguishable where modem metrics permit.

During commissioning, run a 24-hour network outage followed by restoration with
a representative backlog. The unit shall upload oldest-first without missing
new scheduled captures or overheating.

### 14.6 Environmental Reliability

The dominant outdoor risks are usually heat, condensation, water paths, UV,
surge, connectors, insects, and mechanical movement rather than nominal IP
rating alone.

Mitigations:

- White sun shield and air gap.
- Opaque enclosure.
- Hydrophobic vent to equalize pressure.
- Controlled optical-window seal and drip edge.
- Radiation shield for ambient sensors.
- Conformal coating only on suitable boards and never on optical, connector,
  humidity-sensing, or high-impedance surfaces without process review.
- Stainless hardware with anti-galling practice.
- UV-rated external cables and glands.
- Service loops and strain relief.
- Desiccant used as a commissioning aid, not the only moisture strategy.
- Insect screens that do not obstruct sensor airflow.
- Periodic window/gasket/vent inspection.

### 14.7 Diagnostics and Remote Observability

At least once per hour, or with every session, report:

- Last successful RGB/NIR capture.
- Last successful backend acknowledgement.
- Queue count and oldest unacknowledged age.
- Storage free space and health.
- CPU, SSD, enclosure, and battery temperature.
- Input voltage, minimum cycle voltage, SOC estimate, and charger state.
- Network interface and signal quality.
- Camera/sensor status and repeated failure counters.
- Time source and uncertainty.
- Software/configuration/calibration versions.
- Reboot and watchdog counters.

Alert thresholds belong to fleet policy but shall be represented in the device
health schema.

### 14.8 Spare and Replacement Strategy

Field program spares should include:

- Pre-imaged Pi 5 compute assembly.
- Matched camera pair or individually serialized camera modules.
- Pi 5 camera cables.
- Preconfigured LTE modem and antennas.
- Sensor head.
- SSD.
- DC/DC/interface board.
- Window/filter/gasket kit.
- Glands, fuses, connectors, desiccant, and labels.

A camera, lens, filter, optical window, or mount replacement invalidates the
geometric/radiometric calibration until recalibrated. Compute, modem, or power
replacement normally does not, provided the optical assembly is undisturbed.

---

## 15. Mechanical and Enclosure Design

### 15.1 Mechanical Layout

Arrange the enclosure in thermal and service zones:

```text
FRONT / OPTICAL SIDE

 +------------------------------------------------------+
 | [RGB window] [NIR window]     black optical tunnels  |
 |       rigid dual-camera bracket on common datum      |
 |------------------------------------------------------|
 | Pi 5 + active cooler       SSD       sensor terminals|
 |                                                      |
 | modem/carrier                 LTE antenna bulkheads  |
 |------------------------------------------------------|
 | fused input  DC/DC  load switches  shunt  disconnect |
 +------------------------------------------------------+

 Cable glands downward; vent on protected lower side.
 External temperature/RH/light head mounted in radiation shield.
 White solar shield spaced above and around enclosure.
```

Keep the camera bracket mechanically independent of cables and the removable
lid where possible. If the cameras are lid-mounted, provide a defined hinge and
service support so opening the lid cannot strain FFCs or change alignment.

### 15.2 Thermal Design

Perform a thermal model and instrumented test with:

- Maximum CPU load.
- Both cameras active.
- SSD write.
- Cellular upload at weak signal.
- Maximum allowed solar load.
- Window and battery heaters where fitted.

Place temperature sensors at:

- Pi CPU (on-die).
- SSD.
- Cellular modem.
- Air near cameras.
- Enclosure air away from hot components.
- Battery.

The internal metal plate can spread heat but an IP enclosure has limited heat
rejection. A fan only mixes internal air. External fins or a conduction path
through a sealed wall may be needed, but every penetration requires ingress and
corrosion review.

Use firmware/application thermal states:

| Temperature state | Action |
|---|---|
| Normal | Full operation |
| Warm | Increase fan, defer noncritical CPU work |
| Hot | Pause upload/raw processing, record health |
| Critical | Protect storage/cameras with controlled halt |

Exact thresholds are component-specific and shall include measurement
uncertainty and hysteresis.

### 15.3 Condensation Control

Condensation occurs when a surface falls below dew point. Sealing humid air
inside an enclosure can be worse than controlled pressure equalization.

Design controls:

- Assemble in a dry environment.
- Use a hydrophobic vent sized for enclosure volume and pressure changes.
- Avoid large thermal bridges that make optical windows the coldest surface.
- Use low-power window heaters only when dew-point margin is small.
- Monitor internal relative humidity.
- Add a hood that reduces radiative cooling to the night sky.
- Use replaceable desiccant and a humidity card during prototype evaluation.

Heaters shall not warm the external ambient sensor or distort measured air
temperature.

### 15.4 Water Management

- Face glands downward or sideways under a drip loop.
- Do not route cables downward into an upward-facing gland.
- Use gasketed optical retainers with controlled compression.
- Add drip edges above windows.
- Avoid flat exterior ledges that collect water.
- Seal unused holes with rated plugs.
- Torque glands and lid fasteners to vendor values.
- Inspect cable outer diameter against gland sealing range.
- Water-test the completed assembly before electronics are installed, then
  repeat after final assembly with moisture indicators inside.

### 15.5 Antenna Placement

Use external antennas for cellular and GNSS unless RF testing proves internal
antennas are adequate through the selected enclosure.

- Maintain spacing among main LTE, diversity/MIMO, Wi-Fi, and GNSS antennas.
- Keep antennas away from the metal mounting plate edge and power converter.
- Follow modem carrier antenna cable and grounding instructions.
- Use weatherproof bulkheads and boots.
- Avoid tight coax bends and excessive cable length.
- Label ports; swapping GNSS and LTE can damage performance or hardware.
- Test signal metrics with enclosure closed and mounted on the actual pole.

### 15.6 Pole, Tripod, and Wall Mounting

The mount shall:

- Carry enclosure, panel, antenna, and wind loads with safety margin.
- Provide yaw/pitch adjustment with locking fasteners.
- Preserve camera direction after service.
- Include a secondary retention method where falling equipment is hazardous.
- Avoid obstructing camera view, light sensor, GNSS sky view, or solar panel.
- Include a reference mark or inclinometer record for repeatable orientation.
- Resist galvanic corrosion between dissimilar metals.

For permanent deployments, record mounting height, azimuth, pitch, roll,
target-distance range, and a reference scene image.

### 15.7 Camera Alignment in the Field

Provide a temporary alignment mode available only through authenticated local
service. It may display or save both camera previews and registration overlay.
The production application need not expose a user interface.

Commissioning steps:

1. Level and rigidly secure the mast/mount.
2. Aim using RGB preview.
3. Confirm NIR field contains the same target and no filter/window vignetting.
4. Capture calibration/reference target.
5. Run registration validation.
6. Tighten adjustment fasteners using witness marks.
7. Capture final reference image and store orientation.
8. Close enclosure and repeat image check; lid closure shall not alter framing.

### 15.8 Serviceability

The unit shall be serviceable without disturbing optical calibration for common
tasks:

- SIM replacement.
- SSD replacement.
- Fuse replacement.
- Diagnostics connection.
- Compute assembly replacement.
- Battery and solar maintenance.

Use cable labels, connector keys, terminal numbering, and a lid-mounted wiring
diagram. Avoid stacked boards that require removing the camera mount to access a
fuse.

### 15.9 Material and Fastener Guidance

- UV-stable polycarbonate enclosure and UV-rated cable jackets.
- Stainless external fasteners; use suitable anti-seize where galling is a
  concern.
- Black anodized or matte-black optical baffles.
- Closed-cell gasket material compatible with temperature and UV exposure.
- Avoid ordinary indoor foam tape as a structural or sealing component.
- Use thread-locking method compatible with service and plastics.
- Avoid overtightening fasteners into polycarbonate.

### 15.10 Drawings Required for Release

Before pilot build, produce:

- Overall assembly drawing.
- Enclosure machining drawing with gland/window/vent coordinates.
- Camera bracket drawing with datums and tolerances.
- Optical stack section drawing.
- Mounting plate layout.
- Pole/wall bracket drawing and load assumptions.
- Wiring harness drawings with connector pinouts and lengths.
- Label artwork and location drawing.
- Exploded service view.

---

## 16. Bill of Materials and Procurement

The detailed machine-readable BOM is `docs/BOM.csv`. Costs below are planning
ranges only and must be re-quoted. Regional modem variants, radio approvals,
optical filters, industrial storage, and enclosures can dominate lead time.

### 16.1 Core Prototype BOM

| Item | Reference model | Qty | Planning cost (USD) | Notes |
|---|---|---:|---:|---|
| Compute | Raspberry Pi 5, 4 GB | 1 | 100-120 | Current price to be confirmed at order |
| Cooler | Raspberry Pi Active Cooler | 1 | 5-10 | Required for sealed workload evaluation |
| RTC battery | Raspberry Pi RTC battery | 1 | 5-10 | Supports holdover and wake schedule |
| RGB camera | Camera Module 3 standard | 1 | 25-35 | Factory IR-cut |
| NIR camera | Camera Module 3 NoIR standard | 1 | 25-35 | Requires external NIR filter |
| Camera cables | Pi 5 22-pin to 15-pin, suitable length | 2 + spare | 15-30 | Use genuine/reputable cables |
| NIR filter | 850 nm band-pass, OD3 preferred | 1 | 80-250 | Cost depends on size/coating |
| RGB window | AR optical window | 1 | 20-60 | Verify visible transmission |
| NIR window | NIR-transmitting optical window | 1 | 20-60 | Verify 850 nm transmission |
| Storage | Raspberry Pi 512 GB SSD kit or qualified equivalent | 1 | 60-100 | Validate temperature/endurance |
| Recovery media | High-endurance microSD, 32-64 GB | 2 | 20-40 | One installed, one controlled spare |
| Temperature/RH | SHT45 carrier/probe | 1 | 15-40 | External radiation shield |
| Pressure | BMP390 carrier | 1 | 10-25 | Near pressure vent |
| Light | VEML7700 carrier | 1 | 8-20 | Requires diffuser/calibration |
| Power monitor | INA228 carrier + shunt | 1 | 20-50 | Kelvin connection |
| GNSS | MAX-M10S carrier + active antenna | 1 | 40-100 | Optional for fixed surveyed node |
| LTE modem | Regional EG25-G-class modem/carrier | 1 | 100-220 | Carrier and bands must be approved |
| LTE antennas | Main/diversity antennas and bulkheads | 2 | 30-100 | Match modem bands |
| Powered USB path | Industrial/reputable powered hub or carrier | 1 | 25-80 | Resettable branch |
| DC/DC | 9-36 V to 5.1 V, 50-60 W industrial converter | 1 | 45-90 | Verify derating and ripple |
| Interface PCB | Prototype protection/load-switch board | 1 | 40-120 | Includes assembly cost |
| Enclosure | UV-stable polycarbonate IP66 class | 1 | 80-220 | Approx. 300 x 250 x 150 mm |
| Mounting plate | Metal internal plate | 1 | 20-60 | Often enclosure accessory |
| Pressure vent | IP-rated hydrophobic vent | 1 | 10-35 | Match wall thickness |
| Cable glands | IP68 glands/plugs | 1 set | 30-80 | Correct diameter and thread |
| Radiation shield | Multi-plate sensor shield | 1 | 30-100 | Low thermal mass, ventilated |
| Camera bracket | Prototype machined/printed mount | 1 | 40-150 | Common rigid datum |
| External mount | Pole/wall/tripod bracket | 1 | 50-200 | Site load dependent |
| Wiring hardware | Fuse, terminals, connectors, cable, labels | 1 lot | 75-200 | No loose jumper wires |
| Calibration targets | Geometric and reflectance targets | 1 set | 75-400 | Accuracy dependent |

Expected core prototype total, excluding solar equipment, engineering labor,
test instruments, SIM/data plan, and shipping: **approximately USD 1,100 to
2,600**. A low-cost hobby build can be cheaper but will not meet the same
outdoor, optical, protection, and serviceability objectives.

### 16.2 Solar Add-On BOM

| Item | Baseline | Qty | Planning cost (USD) |
|---|---|---:|---:|
| Solar panel | 100 W duty-cycle or 150 W continuous profile | 1 | 80-220 |
| MPPT controller | LiFePO4-compatible with telemetry | 1 | 80-250 |
| Battery | 12.8 V 40-50 Ah LiFePO4, protected | 1 | 180-450 |
| PV/battery disconnects and fuses | DC-rated | 1 set | 40-120 |
| Outdoor PV cable/connectors | UV-rated, correct gauge | 1 set | 30-100 |
| Panel mount | Wind-rated site-specific bracket | 1 | 60-250 |
| Battery enclosure/retention | If separate from electronics | 1 | 40-180 |
| Low-temperature heat/control | Site dependent | 1 | 30-150 |

The MPPT, panel, and battery should be sourced as an electrically compatible
system. Do not select a controller solely by nominal wattage.

### 16.3 Optional Industrial Upgrades

- Industrial-temperature SSD.
- Isolated RS-485/Modbus weather station.
- Triggerable global-shutter RGB and monochrome NIR cameras.
- TPM 2.0 or secure element.
- External power supervisor/watchdog.
- 5G regional modem and four-antenna system.
- Surge-protected Ethernet or fiber media conversion.
- Heated optical windows.
- Formal calibrated irradiance sensor.
- Stainless or fiberglass enclosure for extreme environments.
- Conformal coating with controlled masking and inspection.

### 16.4 Supplier Guidance

Prefer:

- Raspberry Pi Approved Resellers for Pi boards and camera modules.
- Authorized distributors such as DigiKey, Mouser, element14/Farnell, RS, or
  equivalent regional authorized channels for semiconductors and industrial
  components.
- Modem/carrier vendors that provide schematics, power design, firmware support,
  and regional certifications.
- Optical vendors that publish passband curves, angle behavior, dimensions, and
  environmental specifications.
- Enclosure vendors with drawings, gasket data, UV/material data, and matching
  accessories.

Supplier listings on general marketplaces may be used for noncritical
mechanical prototypes, but camera, storage, battery, power, radio, and
protection parts require traceable sources.

### 16.5 Procurement Gates

Do not place the pilot quantity order until:

- Raspberry Pi/camera availability and unit price are revalidated.
- Camera standard versus wide FOV is confirmed by scene mock-up.
- The selected NIR filter is tested with the NoIR camera.
- Modem band/certification/carrier approval is complete.
- Battery chemistry and low-temperature policy are approved.
- Enclosure machining drawing passes mechanical review.
- Power converter survives integrated peak-load test.
- SSD thermal/endurance candidate passes soak.
- All long-lead items have an approved second source or spare strategy.

### 16.6 Incoming Inspection

For every serialized or critical item:

- Verify manufacturer label, part number, revision, and physical condition.
- Record serial/lot where available.
- Inspect connector and optical surfaces.
- Verify camera enumeration and test image before assembly.
- Capacity-test battery samples and record open-circuit voltage.
- Check SSD health counters before imaging.
- Verify optical filter dimensions and transmission certificate/curve.
- Measure shunt resistance or verify certificate.
- Quarantine substitutions until engineering approval.

---

## 17. Assembly and Integration Guide

The field checklist in `docs/checklists/assembly-checklist.md` is the controlled
record. This section explains the intended process.

### 17.1 Required Tools

- ESD-safe bench, grounded wrist strap, and ESD containers.
- Temperature-controlled soldering station and appropriate tips.
- Crimp tools matched to every connector family.
- Torque drivers for terminal, gland, and enclosure fasteners.
- Digital multimeter and bench power supply with current limiting.
- Oscilloscope; current probe or current logger preferred.
- USB power/current analyzer where applicable.
- Magnification and inspection lighting.
- Cable/connector testers.
- Calibrated thermometer/humidity reference and lux meter.
- GNSS test access/open-sky area.
- Camera calibration targets and rigid target support.
- Network impairment capability or controllable router.
- Heat chamber/cold chamber or controlled environmental test access.
- Water spray/ingress test fixture.

### 17.2 Workmanship Rules

- No loose Dupont jumpers, twisted bare wires, or unsupported solder joints.
- Crimp contacts shall pass pull inspection and visual inspection.
- Ferrules shall be used where stranded wire enters compatible screw terminals.
- Use heat-shrink labels or durable printed markers at both harness ends.
- Maintain bend radius and strain relief for FFC and coax.
- Clean flux residues using the process approved for the PCB/material.
- Keep optical surfaces capped until final assembly.
- Do not touch camera lens, filter, or window active surfaces.
- Record deviations and rework.

### 17.3 Build Sequence

#### Stage A: Bare Compute Bench

1. Record Pi serial/revision.
2. Install active cooler.
3. Prepare and verify the controlled OS image.
4. Boot with approved bench supply.
5. Update/pin bootloader as required by release image.
6. Verify RTC and backup battery.
7. Verify Ethernet, Wi-Fi, USB, PCIe/storage, and GPIO.
8. Run CPU/memory/storage baseline tests.
9. Save diagnostic report.

#### Stage B: Camera Bench

1. Inspect and label camera modules.
2. Connect each camera individually with power removed.
3. Record enumeration and test capture.
4. Connect both cameras to assigned Pi 5 ports.
5. Verify stable repeated dual-camera operation.
6. Install NIR filter in temporary holder and confirm visible rejection/NIR
   response.
7. Establish provisional focus and exposure profiles.

#### Stage C: Sensor Bench

1. Verify each I2C address individually.
2. Assemble the bus with controlled pull-ups.
3. Measure SDA/SCL idle voltage and rise time.
4. Run continuous reads for at least two hours.
5. Connect GNSS and validate UART/PPS.
6. Calibrate the INA228/shunt.
7. Fault-inject sensor disconnects and verify bounded recovery.

#### Stage D: Power Assembly

1. Inspect PCB and polarity before fitting the source.
2. Current-limit the bench supply.
3. Verify input protection and no-load 5.1 V output.
4. Verify each branch off/on state and default-off switched loads.
5. Verify Pi startup and shutdown.
6. Add modem and storage one branch at a time.
7. Run combined peak-load test while observing the rail.
8. Verify fuse selection, wire temperature, and voltage drop.

#### Stage E: Mechanical Assembly

1. Machine enclosure using released drawing.
2. Deburr and clean all openings.
3. Trial-fit windows, vent, glands, bulkheads, and mounting plate.
4. Perform an empty-enclosure water test.
5. Install mounting plate and power assembly.
6. Install compute, storage, and modem assemblies.
7. Install camera bracket without touching optics.
8. Route FFCs, coax, sensor harness, and power separately.
9. Install optical windows/filter/baffles.
10. Install external radiation shield and sensor cable.
11. Torque and witness-mark critical fasteners.
12. Photograph completed internal assembly.

#### Stage F: Final Calibration

1. Verify both cameras with enclosure closed.
2. Calibrate fixed focus through final optical stack.
3. Determine exposure profile table.
4. Perform geometric calibration and validation.
5. Perform radiometric baseline/dark/flat tests.
6. Calibrate assembled sensors.
7. Store calibration package with checksums.
8. Apply device serial and QR label.

### 17.4 Harness Guidance

Create harness drawings specifying:

- Source and destination connector IDs.
- Contact manufacturer and part number.
- Pin number, signal, color, gauge, and length.
- Shield termination.
- Twisted-pair grouping.
- Branch fuse.
- Maximum current.
- Test method.

Power and sensor wiring shall not be inferred from wire color alone. Harness
continuity is tested before connection to the Pi.

### 17.5 Optical Cleanliness

- Work under clean lighting and use powder-free gloves/finger cots.
- Blow loose dust with clean filtered air before wiping.
- Use optical-grade tissue/swab and approved solution.
- Wipe once in a controlled direction; do not grind particles into coatings.
- Inspect with oblique light.
- Photograph or record defects that remain outside the active field.
- Close the optical head promptly after cleaning.

### 17.6 Enclosure Closure

Before final closure:

- Remove loose hardware and wire strands.
- Verify desiccant/humidity card placement.
- Confirm no cable crosses the gasket.
- Clean gasket and mating surface.
- Confirm vent and drain orientation.
- Confirm all unused entries are plugged.
- Verify internal service loop does not contact the fan.
- Verify camera FFC latches and clamps.
- Verify branch fuses and labels.
- Run live capture/upload with the lid in final position.
- Torque lid fasteners in a cross pattern per vendor instruction.

### 17.7 Build Record

The build record links:

- Device ID and enclosure serial.
- Pi serial, SSD serial, modem IMEI/equipment identity with protected handling,
  camera IDs, sensor serials/lots, battery serial, and filter lot.
- PCB and harness revisions.
- OS/software/config/calibration checksums.
- Technician, date, rework, and inspection signatures.
- Test report IDs.

---

## 18. Verification and Validation Plan

### 18.1 Test Levels

| Level | Purpose |
|---|---|
| Unit | Driver, sensor, power branch, and API client behavior |
| Integration | Cameras, storage, modem, sensors, and power on one bench |
| EVT | Prove architecture and identify electrical/optical issues |
| DVT | Verify environmental, reliability, and requirement compliance |
| Pilot | Validate representative site behavior for 30 days |
| Factory acceptance | Repeatable per-unit release test |

Every test record includes unit serial, hardware/software/config revision,
equipment IDs, environment, steps, expected result, actual result, evidence,
pass/fail, deviations, and approver.

### 18.2 Requirements Traceability

The acceptance-test record maps each FR/NFR to at least one test. Before pilot,
review the matrix for:

- Untested failure paths.
- Requirements verified only by inspection where a test is possible.
- Site conditions absent from lab tests.
- Changes made after the last passing test.

### 18.3 Factory Acceptance Test

Minimum per-unit sequence:

1. Visual/workmanship and serial inspection.
2. Harness continuity and polarity.
3. Input current-limited power-up.
4. 5 V rail at idle and combined load.
5. RTC backup and wake.
6. Storage identity, capacity, health, read/write.
7. Camera inventory, RGB/NIR capture, focus, exposure, and image-quality check.
8. Sensor inventory and plausibility.
9. GNSS fix/PPS where fitted.
10. Ethernet, Wi-Fi, and cellular registration/upload.
11. Backend idempotency and checksum acknowledgement.
12. Watchdog and service restart.
13. Controlled shutdown and restart.
14. Short enclosure leak/moisture inspection.
15. Final diagnostic bundle and release label.

No unit ships with an unexplained undervoltage event, media error, camera
enumeration warning, failed sensor, or default credential.

### 18.4 Camera Tests

#### Functional

- 1,000 scheduled dual-camera cycles without camera disappearance.
- Capture interval and timestamp delta distribution.
- Fixed control verification against returned metadata.
- One bounded retry under induced camera service failure.

#### Focus and Sharpness

- Center and corner sharpness at target distance.
- Hot and cold focus drift.
- NIR focus through final filter/window.
- Condensation simulation and recovery.

#### Exposure

- Bright sun, overcast, low-light, and night/skip profiles.
- Saturation and darkness percentages.
- Repeatability under stable illumination.
- Profile selection hysteresis around lux thresholds.

#### Geometry

- Intrinsic calibration residual.
- Pair rectification residual on reference plane.
- Alignment after thermal cycle and vibration.
- Alignment after enclosure open/close.

#### Radiometry

- Dark offset at multiple temperatures/exposures.
- Flat-field/vignetting map.
- Reflectance target repeatability.
- Filter light leak and passband suitability.
- Cross-unit variation for more than one camera pair.

### 18.5 Sensor Tests

| Sensor | Test | Prototype acceptance |
|---|---|---|
| SHT45 | Compare stabilized assembled head to reference | +/-0.5 C, +/-3 %RH |
| BMP390 | Compare to reference pressure | +/-1 hPa assembly target |
| VEML7700 | Compare profile selection against lux reference | Correct profile with defined hysteresis |
| INA228 | Voltage/current comparison at multiple loads | +/-2% system target after calibration |
| GNSS | Open-sky fix and scatter | Meets site position/time requirement |
| Rain/wind | Calibrated pulses/input simulator | No missed/double counts at rated rate |

Also disconnect, short where safe, corrupt data, and exercise out-of-range
handling.

### 18.6 Power Tests

- Converter input minimum/maximum and startup.
- Pi boot while modem/SSD branches are present.
- Combined CPU, camera, SSD write, and weak-signal upload.
- 5 V ripple and transient minimum at Pi connector.
- Branch short/current-limit behavior using safe fixtures.
- Reverse-polarity protection.
- Fuse clearing/selectivity review.
- Controlled low-battery transitions.
- RTC wake accuracy over 100 cycles.
- Duty-cycle energy measurement for at least 24 hours.
- Continuous-profile energy measurement for at least 72 hours.
- Battery runtime/autonomy test.
- Solar charge/discharge test using real or simulated profile.

Target the Pi input above 4.9 V during normal maximum load, with no undervoltage
flags. Final limits follow the selected distribution and measured cable drop.

### 18.7 Storage and Power-Interruption Tests

1. Populate queue with representative preview/raw sessions.
2. Remove power at:
   - image write,
   - metadata write,
   - directory rename,
   - queue transaction,
   - asset upload,
   - completion acknowledgement,
   - cleanup.
3. Repeat at least 100 times across states.
4. Verify filesystem mounts, queue reconciles, and no committed session is lost.
5. Verify backend receives no duplicate logical capture.
6. Verify partially written files are quarantined or removed.
7. Verify acknowledged data is never misclassified as unacknowledged solely
   because of an interrupted cleanup.

### 18.8 Connectivity Tests

- Ethernet-only, Wi-Fi-only, cellular-only.
- Priority and failover among all interfaces.
- SIM absent, PIN locked, APN wrong, roaming denied, and data exhausted.
- Weak LTE signal and antenna disconnect.
- DNS failure, TLS failure, backend 401, 429, 500, timeout, and connection reset.
- 24-hour complete outage, then backlog recovery.
- Presigned URL expiration and renewal.
- Multipart/resumable interrupted upload.
- Monthly byte counter and metered policy.
- Modem power cycle without Pi reboot.

### 18.9 API and Data Integrity Tests

- Valid complete session.
- Partial RGB-only or NIR-only session.
- Duplicate create with same idempotency key.
- Duplicate complete request.
- Wrong asset size.
- Wrong hash.
- Unknown schema version.
- Unsupported media type.
- Token/certificate expiry and rotation.
- Backend returns existing session after client lost response.
- Queue state reconciliation after reboot.

### 18.10 Environmental Tests

The actual test severity follows site requirements. Prototype minimum:

- Hot operating soak with full workload.
- Cold start and cold capture at the lowest allowed prototype temperature.
- Thermal cycling with enclosure closed.
- High-humidity dwell and condensation challenge.
- Rain/water spray from relevant directions.
- Dust/insect inspection.
- UV/material review and outdoor coupon exposure where practical.
- Vibration/transport and pole-mount shake.
- Cable pull/strain-relief test.
- Window impact risk review.

Ingress testing of a project-built enclosure is not an official IP
certification. Use an accredited laboratory if certification is required.

### 18.11 Soak Test

Run a 168-hour lab soak before pilot:

- Normal 15-minute schedule.
- Representative previews and raw assets.
- Cellular or impaired network with planned outages.
- Temperature variation.
- Daily modem reset and one planned Pi reboot.
- At least one storage-pressure scenario in a separate test.

Pass criteria:

- At least 99% scheduled sessions committed locally.
- No unrecovered camera or sensor hang.
- No checksum mismatch accepted.
- No unexplained reboot.
- No queue growth after network recovery beyond expected upload capacity.
- No unsafe temperature or persistent undervoltage.
- All injected faults observable in logs/health.

### 18.12 Field Pilot

Deploy at least one instrumented unit for 30 days; two units are preferred to
separate unit-specific from site-wide issues. Review daily during the first
week and at least weekly thereafter.

Pilot metrics:

- Scheduled/committed/accepted session rates.
- RGB-NIR time delta and registration quality.
- Exposure/quality flag rates by time and weather.
- Sensor plausibility and drift.
- Daily energy, battery minimum, and solar recovery.
- Queue depth and network data usage.
- CPU/SSD/modem/enclosure temperatures.
- Watchdog, reset, and reconnect events.
- Condensation, water, fouling, insect, and mount movement observations.
- Maintenance time.

The pilot exits only after open critical defects are resolved and affected
tests are repeated.

### 18.13 Calibration Acceptance

A calibration package is accepted when it contains:

- Camera and filter serial/lot identities.
- Final optical/mount revision.
- Intrinsic/extrinsic parameters and residual report.
- Focus positions and exposure profiles.
- Dark/flat-field data.
- Reflectance reference method.
- Sensor coefficients and reference equipment.
- Temperature/environment during calibration.
- Script/tool versions.
- Checksums and approver.

### 18.14 Security Tests

- Port scan on all interfaces.
- Verify no password SSH and no default credentials.
- Attempt upload with invalid/revoked credential.
- Verify server certificate rejection.
- Verify configuration/update signature failure.
- Check log and diagnostic bundle for secret leakage.
- Verify least-privilege service users and file permissions.
- Verify update rollback after failed health confirmation.

---

## 19. Deployment Plan

### 19.1 Deployment Phases

| Phase | Purpose | Exit |
|---|---|---|
| Site survey | Close environmental, view, network, power, and mounting inputs | Approved survey record |
| Bench staging | Enroll, configure, calibrate, and soak exact field unit | Factory acceptance pass |
| Dry installation | Install mount/power without exposing electronics to unsafe work | Mechanical/electrical inspection |
| Commissioning | Aim, connect, validate capture/upload/time/power | Deployment checklist pass |
| Observation period | Closely monitor first 72 hours | Stable power, queue, image, and network |
| Pilot | 30-day representative operation | Pilot acceptance review |
| Fleet release | Controlled replication | Approved DVT/PVT package |

### 19.2 Site Survey

Record:

- GPS/surveyed coordinate and elevation.
- Mount type, dimensions, material, condition, and owner approval.
- Camera target, distance, view obstruction, sunrise/sunset glare, and expected
  seasonal vegetation growth.
- Panel horizon, shade by hour/season, orientation, and wind exposure.
- Ambient temperature/humidity extremes and flooding/snow/salt/dust risk.
- Cellular signal metrics for candidate carriers at intended antenna height.
- Wi-Fi/Ethernet route and surge exposure.
- Lightning/grounding conditions.
- Safe technician access and fall/electrical hazards.
- Theft/vandalism risk.
- Service interval and spare-storage location.

Photograph all directions and the intended field of view. A phone signal icon
is not an acceptable cellular survey; use modem metrics and upload tests.

### 19.3 Pre-Deployment Staging

- Reserve device ID and enroll unique credential.
- Install the exact release image.
- Apply site configuration and validate schema.
- Install calibration package.
- Verify SIM/APN/data plan and backend authorization.
- Set surveyed coordinates and site metadata.
- Run full factory acceptance after staging.
- Charge battery fully and verify pack/BMS temperature.
- Set RTC and verify wake schedule.
- Export encrypted recovery material to controlled storage.
- Prepare labeled field spare kit and rollback image.

### 19.4 Installation Sequence

1. Verify permit, weather, and work-area safety.
2. Install pole/wall foundation and bracket.
3. Install solar panel and protected battery/power system with disconnect open.
4. Install enclosure and secondary retention.
5. Route cables with drip loops, UV protection, and strain relief.
6. Install antennas with spacing and weather seals.
7. Verify polarity, earth/shield strategy, fuses, and disconnects.
8. Energize with branch loads controlled.
9. Verify 12 V and 5 V rails before connecting the Pi where practical.
10. Boot and inspect power telemetry.
11. Aim cameras and lock mount.
12. Verify environmental sensor placement outside enclosure heat plume.
13. Close and torque enclosure.
14. Perform commissioning tests.

### 19.5 Commissioning Acceptance

The installer shall demonstrate:

- Device ID matches site assignment.
- UTC time source and RTC are valid.
- RGB and NIR images show expected field with no window/filter vignetting.
- Registered overlay meets field tolerance.
- Exposure profile is appropriate in current conditions.
- Temperature/RH sensor is shaded and ventilated.
- GNSS or surveyed location is correct.
- Input voltage and charging state are healthy.
- Ethernet/Wi-Fi/cellular route policy works.
- One complete capture is acknowledged by backend with matching hashes.
- Offline capture is queued, then uploads after restoration.
- Enclosure, glands, antennas, and mount pass visual inspection.
- Final orientation and reference images are archived.

### 19.6 First 72 Hours

Review at least every six hours:

- Battery voltage/SOC and daily energy balance.
- Solar charge recovery.
- Maximum CPU, SSD, modem, and enclosure temperatures.
- Queue depth and oldest pending session.
- Network signal and reconnects.
- Camera quality, condensation, rain on windows, and registration.
- Sensor plausibility.
- Reboot/watchdog/undervoltage events.

Any worsening energy deficit, persistent queue growth, enclosure overtemperature,
or water indication is a stop-and-correct condition.

### 19.7 Rollback and Retrieval

Prepare for:

- Remote rollback to last confirmed software image.
- Remote disable of heater/raw upload/high-energy features.
- Controlled shutdown until safe service.
- Physical recovery of SSD/data if the network fails.
- Complete unit swap without changing backend site identity incorrectly.

When retrieving a failed device, preserve logs, queue, seal condition, and
connector state. Photograph before opening. Do not immediately re-image or
clean evidence.

---

## 20. Maintenance Plan

### 20.1 Maintenance Intervals

Actual intervals depend on fouling and climate. Prototype schedule:

| Interval | Tasks |
|---|---|
| Remote daily | Review power, queue, last captures, temperatures, link, and fault counters |
| Remote weekly | Review image quality trend, registration, sensor drift, storage health, data use |
| Physical monthly during pilot | Clean windows/panel, inspect seals/glands/mount/antennas/sensor shield |
| Physical quarterly after pilot | Detailed enclosure, cable, battery, vent, corrosion, and calibration check |
| Annual | Replace weathered consumables, capacity-test battery, full calibration verification |
| Event-driven | Inspect after severe storm, impact, flood, lightning nearby, or unexplained alignment shift |

### 20.2 Optical Maintenance

- Use approved optical cleaning materials.
- Inspect coatings, scratches, water spots, insect residue, and internal haze.
- Verify heater and hood.
- Capture reference target after cleaning.
- Compare framing and sharpness to commissioning image.
- Recalibrate if camera/filter/window/mount moved or was replaced.

Cleaning can change radiometric response materially. Record before/after
reference images and maintenance timestamp.

### 20.3 Enclosure Maintenance

- Inspect gasket compression, cuts, set, dirt, and chemical attack.
- Verify gland tightness and cable jacket condition.
- Inspect vent for clogging, wetting, or delamination.
- Check unused plugs and antenna bulkhead seals.
- Look for water trails, corrosion, insect debris, and desiccant saturation.
- Verify fastener witness marks and mount movement.
- Replace damaged seals with vendor-compatible parts.

### 20.4 Power Maintenance

- Review battery capacity trend, BMS faults, cell balance if available, and
  minimum voltage.
- Inspect terminal torque, fuse holders, heat discoloration, and corrosion.
- Clean solar panel and check mounts/cable.
- Verify charger profile has not reset.
- Compare daily harvested energy to baseline.
- Capacity-test or replace battery according to measured health and vendor
  lifecycle.

### 20.5 Storage Maintenance

- Review SSD wear, spare, error, unsafe-shutdown, and temperature counters.
- Verify free-space policy.
- Test diagnostic export.
- Replace the SSD proactively before endurance or error thresholds.
- Preserve calibration and identity independently of the drive.

Do not defragment SSDs. Ensure TRIM policy is controlled and does not overlap a
capture-critical period if it causes latency spikes.

### 20.6 Software Maintenance

- Release signed, tested images with a change log.
- Pilot each update on representative hardware before fleet rollout.
- Roll out in cohorts and monitor probation health.
- Maintain backend compatibility for supported device schema versions.
- Rotate credentials before expiry.
- Review vulnerability advisories for OS, modem, and update stack.
- Export end-of-life data and securely decommission credentials.

### 20.7 Calibration Maintenance

Calibration verification is required:

- At initial assembly.
- After optical component replacement.
- After mount impact or observed registration shift.
- After major thermal/mechanical redesign.
- At least annually for long-term measurements.
- When comparison to a reference device indicates drift.

Store old calibration versions; historical data must remain traceable to the
calibration active at capture time.

---

## 21. Troubleshooting Guide

### 21.1 Device Does Not Boot

1. Disconnect high-current peripheral branches.
2. Verify source polarity, fuse, disconnect, battery/BMS, and converter input.
3. Measure 5.1 V rail at no load and during attempted boot.
4. Inspect Pi status LEDs and serial/diagnostic output.
5. Test with controlled recovery microSD and known-good approved supply.
6. Reconnect SSD, modem, and heaters one at a time.
7. Preserve the original SSD for analysis.

Do not repeatedly cycle an overheated, wet, or visibly damaged assembly.

### 21.2 Undervoltage or Random Reboot

- Correlate reboot with modem transmit, SSD write, camera start, or heater.
- Measure at the Pi connector, not only at converter terminals.
- Check shared thin wire, loose terminal, fuse holder, USB cable, and branch
  topology.
- Verify converter current/thermal derating.
- Inspect battery minimum voltage and BMS events.
- Power modem separately and repeat.
- Review Pi undervoltage flags and INA228 minimum.

### 21.3 Camera Missing

- Confirm correct camera/port mapping in software.
- Power down before inspecting/reseating FFC.
- Check latch, contact orientation, cable damage, bend, and strain.
- Test camera and cable independently on known-good port.
- Inspect connector for contamination or damage.
- Verify software image/overlay/configuration.
- Reassign calibration only after identity is confirmed.

### 21.4 NIR Image Looks Like Normal Color

Likely causes:

- NIR band-pass filter absent, reversed optical holder, or bypassed by edge leak.
- Filter is a long-pass rather than narrow band-pass.
- Preview rendering maps Bayer channels to visible-looking color.
- Wrong camera role/port.
- Visible transmission of the selected filter is too high.

Verify with a known NIR-reflective target and a visible-blocking test. The NoIR
module by itself is expected to see visible light.

### 21.5 Images Are Blurred

- Inspect exterior water/dirt and interior condensation.
- Verify manual lens position and camera identity.
- Check camera bracket movement and FFC force.
- Compare center/corner sharpness and hot/cold history.
- Verify exposure time is not too long for wind motion.
- Check window flatness, stress, and incorrect protective film.
- Re-run focus sweep through the final optical stack.

### 21.6 RGB and NIR Do Not Register

- Confirm images belong to the same capture session and roles are not swapped.
- Inspect mechanical alignment and witness marks.
- Verify calibration version matches camera serials.
- Check lid/mount movement or thermal distortion.
- Test on the calibration plane.
- Evaluate scene depth/parallax; a single homography cannot align all depths.
- Review inter-camera time delta and scene motion.

### 21.7 Environmental Readings Are Implausible

- Check whether temperature/RH sensor is heated by enclosure exhaust or sun.
- Inspect radiation shield, membrane, insects, and condensation.
- Verify I2C status/CRC and calibration version.
- Compare raw and corrected value.
- Compare to a reference after stabilization.
- Check pressure vent obstruction.
- Confirm lux sensor diffuser/orientation and saturation setting.

### 21.8 No Cellular Connection

- Verify regional modem variant, supported bands, SIM orientation, PIN, APN,
  plan status, and carrier registration.
- Check main/diversity antenna port assignment and cable.
- Review RSRP/RSRQ/SINR and registration reject reason.
- Test outdoors away from enclosure and then in installed configuration.
- Restart ModemManager, then load-switch modem.
- Verify USB enumeration and modem branch voltage during transmit.
- Check roaming and carrier certification/provisioning.

### 21.9 Captures Do Not Upload

Distinguish:

1. Interface down.
2. No route/DNS.
3. TLS trust/time failure.
4. Authentication failure.
5. API validation failure.
6. Object upload failure.
7. Completion/hash failure.

Inspect stable error code and request ID. Do not delete or manually rename queue
data to force retry.

### 21.10 Queue Is Filling

- Compare generated bytes/day with measured upload capacity/data policy.
- Check oldest failure code.
- Verify backend idempotency and URL renewal.
- Review cellular data cap and upload window.
- Reduce optional raw upload only under approved policy.
- Expand storage or network capacity if the long-term balance is negative.

### 21.11 RTC Wake Fails

- Verify RTC battery and detected RTC.
- Verify wake alarm was written and read back.
- Confirm low-power halt firmware/configuration.
- Check external load switch/supervisor sequencing.
- Test 100 short cycles on bench before field use.
- Ensure a watchdog supervisor does not remove supply needed by RTC wake.

### 21.12 Water or Condensation Found

1. Isolate power.
2. Photograph exterior and interior before disturbing evidence.
3. Identify water path, gasket/gland/vent/window condition, and weather event.
4. Quarantine affected electronics; do not simply dry and redeploy.
5. Correct design/workmanship issue.
6. Repeat empty and populated ingress/condensation tests.

---

## 22. Design Reviews, Risks, and Future Improvements

### 22.1 Required Reviews

#### Preliminary Design Review

- Requirements and site assumptions.
- Architecture and subsystem selection.
- Initial power/storage/data calculations.
- Camera limitation and calibration plan.
- Prototype BOM and test plan.

#### Critical Design Review

- Final schematics/PCB/harness/drawings.
- Site-specific modem, antenna, solar, and enclosure selections.
- Measured power/thermal results.
- Camera/filter validation and calibration residuals.
- Security and API contract.
- Updated risk register and traceability.

#### Pilot Readiness Review

- Factory acceptance and 168-hour soak.
- Field installation package and spares.
- Backend monitoring and alerting.
- Recovery/rollback plan.
- Safety and work permits.

### 22.2 Principal Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| NoIR channel contaminated by visible light | High without filter | High | Mandatory band-pass filter and validation |
| RGB/NIR motion or parallax mismatch | Medium-high | High | Rigid low-baseline mount, rapid sequence, registration, RGB-NIR-RGB |
| Camera temperature outside rating | Site dependent | High | Site data, shade, heater/thermal design, industrial alternative |
| Sealed-enclosure overheating | Medium | High | Thermal test, white shield, load management, conduction |
| Condensation/window fouling | Medium-high | High | Vent, hood, dew control, maintenance, quality checks |
| Cellular band/carrier mismatch | Medium | High | Regional approval gate and site test |
| Modem pulse browns out Pi | Medium | High | Independent power branch and transient test |
| Solar system undersized | Medium | High | Worst-month model, measured duty, margin, telemetry |
| Consumer SSD heat/endurance failure | Medium | Medium-high | Thermal qualification, health monitoring, industrial option |
| I2C external cable instability | Medium | Medium | Short local bus; RS-485 for long runs |
| API retry duplicates sessions | Medium | High | Capture ID, idempotency keys, completion reconciliation |
| Shared credential compromises fleet | Low-medium | High | Unique credentials and rotation |
| Enclosure modifications break ingress | Medium | High | Controlled machining/sealing and completed-unit tests |
| Calibration drift after service | Medium | High | Serialized components and mandatory recalibration rules |
| Monthly data volume exceeds plan | Medium | Medium-high | Profile sizing, metering, raw upload policy |

### 22.3 Camera System Upgrade Path

Move away from the Camera Module 3 pair when any of these are mandatory:

- Sub-frame deterministic synchronization.
- Fast-moving platform or foliage with strict temporal consistency.
- Pixel-level registration across large depth variation.
- Published spectral response and scientific radiometric traceability.
- Outdoor temperature beyond consumer module limits.
- Global shutter.

Upgrade candidates include triggerable industrial USB3/GigE/MIPI cameras, one
RGB and one monochrome NIR sensor with matched lenses and hardware trigger.
A beam splitter can eliminate viewpoint parallax but adds optical complexity,
light loss, size, and calibration effort.

### 22.4 Compute Upgrade Path

For a production carrier, evaluate a Compute Module platform when it provides
the required lifecycle, connector, storage, and thermal options. Benefits:

- Custom protected power input.
- Locking camera/storage/modem connectors.
- Integrated TPM/secure element.
- Controlled USB and peripheral power switches.
- Smaller harness and improved EMC.
- Manufacturing test points.

The prototype remains on Pi 5 to reduce initial design time.

### 22.5 Sensing Improvements

- Calibrated spectral irradiance or PAR sensor.
- Soil moisture/temperature through SDI-12/RS-485.
- Leaf wetness sensor.
- All-in-one Modbus weather station.
- IMU/inclinometer to detect mount movement.
- Internal leak/condensation sensor.
- Door/tamper switch.
- Panel current and separate load-current monitoring.

### 22.6 Power Improvements

- External ultra-low-power supervisor that completely power-cycles the Pi.
- Smarter MPPT telemetry integration.
- Forecast-aware capture/upload policy.
- Fuel-gauge IC with characterized LiFePO4 model.
- Redundant power input.
- Supercapacitor shutdown reserve.
- Site-specific hybrid mains/solar design.

### 22.7 Fleet and Security Improvements

- Hardware-backed device enrollment.
- Measured/verified boot.
- Per-device VPN.
- Remote attestation.
- Signed diagnostic bundles.
- Configuration policy service with staged rollout.
- Backend command queue with replay protection.
- Coordinated certificate rotation and decommissioning.

---

## 23. Deliverables and Acceptance

### 23.1 Prototype Deliverables

The hardware team shall deliver:

1. Fully assembled outdoor prototype with serial label.
2. RGB and filtered-NIR camera pair with calibration package.
3. Environmental and power sensor integration.
4. Validated storage and autonomous acquisition queue.
5. Ethernet/Wi-Fi/cellular configuration as applicable.
6. Stable continuous or solar duty-cycled power system.
7. Backend API integration demonstrating hash-validated acknowledgement.
8. Wiring, schematic, harness, machining, assembly, and mount drawings.
9. BOM with approved substitutions.
10. Controlled OS/software image and configuration.
11. Factory acceptance, soak, calibration, and pilot reports.
12. Installation, maintenance, troubleshooting, and recovery materials.

### 23.2 Prototype Acceptance Criteria

The prototype is accepted for pilot only when:

- Both camera modules complete 1,000-cycle integration testing.
- The NIR path is demonstrably visible-blocked and spectrally filtered.
- Fixed focus/exposure profiles and camera metadata are repeatable.
- Registration meets project target on the calibration plane.
- Sensor assembly meets prototype accuracy targets.
- Power rail has no undervoltage under combined peak test.
- Energy and storage budgets are validated with measured data.
- 100 power-interruption tests preserve committed queue semantics.
- A 24-hour offline backlog uploads successfully after restoration.
- The 168-hour soak meets Section 18.11.
- The completed enclosure passes project rain/condensation tests.
- Unique credentials, TLS validation, watchdogs, and rollback are demonstrated.
- All critical risks have an owner and no unapproved critical deviation remains.

### 23.3 Definition of Done for Field Pilot

The pilot is complete when:

- Thirty consecutive days of representative operation are reviewed.
- Scheduled local commit rate and backend acceptance rate meet agreed targets.
- No unresolved unsafe thermal, water, battery, or mounting issue exists.
- Image quality and registration support the backend team's intended analysis.
- Daily energy is sustainable in representative weather with autonomy margin.
- Queue and network capacity are balanced.
- Maintenance procedure and spare replacement are demonstrated.
- Design changes are captured and affected tests repeated.

### 23.4 Production Release Caveat

Passing this prototype specification does not itself establish:

- Regulatory radio/EMC compliance.
- Electrical safety certification.
- Formal IP rating.
- Scientific measurement traceability.
- Long-term component availability.
- Suitability for hazardous locations.

Those items require a production requirements baseline, compliance plan, and
qualified test evidence.

---

## Appendix A: Recommended Device States

```text
BOOTING
   |
   +--> RECOVERY_REQUIRED
   |
   v
READY <------------------------------+
   |                                 |
   v                                 |
CAPTURING --> COMMITTING --> READY --+
   |
   +--> DEGRADED_CAMERA
   +--> DEGRADED_SENSOR
   +--> STORAGE_CRITICAL
   +--> THERMAL_HOLD
   +--> ENERGY_SAVING
   |
   v
SHUTDOWN_PENDING --> SLEEP/OFF --> RTC WAKE --> BOOTING
```

Network state is orthogonal: offline, local-link, internet, API-authenticated,
or backlogged. A device can remain acquisition-ready while offline.

## Appendix B: Status and Error Code Families

| Range | Family | Examples |
|---|---|---|
| CAM-1xxx | Camera | `CAM-1001_NOT_ENUMERATED`, `CAM-1004_BLANK_FRAME` |
| SNS-2xxx | Sensor | `SNS-2002_I2C_TIMEOUT`, `SNS-2010_VALUE_IMPLAUSIBLE` |
| STO-3xxx | Storage | `STO-3001_NOT_MOUNTED`, `STO-3005_HASH_MISMATCH` |
| NET-4xxx | Network | `NET-4003_DNS_FAILED`, `NET-4012_MODEM_RESET` |
| API-5xxx | Backend | `API-5001_AUTH_REJECTED`, `API-5007_SCHEMA_REJECTED` |
| PWR-6xxx | Power | `PWR-6002_UNDERVOLTAGE`, `PWR-6010_LOW_SOC` |
| THM-7xxx | Thermal | `THM-7003_CAMERA_TOO_HOT`, `THM-7005_CONDENSATION_RISK` |
| CFG-8xxx | Configuration | `CFG-8001_SCHEMA_INVALID`, `CFG-8004_CALIBRATION_MISMATCH` |
| SYS-9xxx | System | `SYS-9002_WATCHDOG_REBOOT`, `SYS-9006_TIME_INVALID` |

Codes are stable API values. Human messages may improve without changing code
semantics.

## Appendix C: Storage Sizing Examples

At 15-minute intervals there are 96 sessions/day.

| Profile | Estimated bytes/session | Per day | 30 days | 512 GB practical retention |
|---|---:|---:|---:|---:|
| Two JPEG previews | 12 MB | 1.15 GB | 34.6 GB | Greater than 300 days before reserve |
| Previews + two DNG, standard estimate | 60 MB | 5.76 GB | 172.8 GB | Approximately 70 days with 20% reserve |
| Large raw/diagnostic profile | 100 MB | 9.6 GB | 288 GB | Approximately 42 days with 20% reserve |

Actual size varies by scene, encoding, and software. Measure at least one week
of representative files. Use decimal GB consistently for procurement and
filesystem-reported bytes carefully in monitoring.

At 10-minute intervals, multiply 15-minute figures by 1.5. At 30-minute
intervals, multiply by 0.5.

## Appendix D: Network Data Sizing

Assuming all assets are uploaded:

```text
Monthly data = bytes/session x sessions/day x days
```

The standard preview-only profile is about 35 GB/month before protocol overhead.
The 60 MB raw profile is about 173 GB/month. Cellular plans, upload time, and
backend storage must be selected accordingly.

Possible approved controls:

- Upload previews immediately and raw assets during low-cost windows.
- Retain raw locally for periodic retrieval.
- Capture raw only at a lower cadence.
- Use lossless compression where effective and scientifically acceptable.
- Do not recompress already compressed JPEG.

Any policy that omits raw data changes the analytic product and shall be agreed
with the backend/remote-sensing owner.

## Appendix E: Configuration Ownership

| Configuration class | Owner | Examples |
|---|---|---|
| Fleet policy | Product/backend | Interval, upload policy, retention target |
| Site policy | Field operations | Coordinates, network, power mode, daylight window |
| Unit hardware | Hardware | Sensor addresses, GPIO mapping, modem type |
| Optical calibration | Vision/hardware | Focus, exposure profiles, intrinsics, transform |
| Security identity | Security/provisioning | Certificate/key references |
| Runtime learned state | Device | Queue, retry, health counters, SOC estimator |

Runtime state shall not overwrite controlled configuration or calibration.

## Appendix F: Reference Source Register

Primary manufacturer documentation shall be downloaded, revision-controlled,
and attached to the design record at procurement freeze. The following sources
informed this baseline:

1. Raspberry Pi 5 product brief and hardware documentation:
   `https://pip.raspberrypi.com/documents/RP-008348-DS-raspberry-pi-5-product-brief.pdf`
2. Raspberry Pi Camera Module 3 product brief:
   `https://pip.raspberrypi.com/documents/RP-008341-DS-1-camera-module-3-product-brief.pdf`
3. Raspberry Pi camera software documentation:
   `https://www.raspberrypi.com/documentation/computers/camera_software.html`
4. Raspberry Pi hardware/RTC documentation:
   `https://www.raspberrypi.com/documentation/computers/raspberry-pi.html`
5. Sensirion SHT4x product and data-sheet documentation:
   `https://sensirion.com/products/catalog/SHT45`
6. Bosch Sensortec BMP390 product and data-sheet documentation:
   `https://www.bosch-sensortec.com/products/environmental-sensors/pressure-sensors/bmp390/`
7. Vishay VEML7700 data sheet:
   `https://www.vishay.com/docs/84286/veml7700.pdf`
8. Texas Instruments INA228 product and data sheet:
   `https://www.ti.com/product/INA228`
9. u-blox MAX-M10 series product and data-sheet documentation:
   `https://www.u-blox.com/en/product/max-m10-series`
10. Quectel EG25-G product and hardware-design documentation:
    `https://www.quectel.com/product/lte-eg25-g/`
11. Quectel RM520N series product and hardware-design documentation:
    `https://www.quectel.com/product/5g-rm520n-series/`
12. MidOpt NIR long-pass/band-pass optical filter references:
    `https://midopt.com/filters/lp715/`
    and `https://midopt.com/filters/bn850/`
13. Mean Well DDR-60G series DC/DC documentation:
    `https://www.meanwell.com/productPdf.aspx?i=863`

Web pages and commercial part numbers change. The engineering team shall archive
the exact data-sheet revision used for each released BOM item and resolve any
conflict in favor of the current manufacturer document for the purchased part.

---

## End of Controlled Specification
