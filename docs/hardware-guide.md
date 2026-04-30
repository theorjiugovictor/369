# 369 Hardware Guide

## Bill of Materials — Backyard Setup

### Controller
- **Raspberry Pi 4B** (4GB+) — runs 369 core + Docker
- 32GB+ microSD card (A2 rated)
- Official Pi power supply (5V 3A)
- Case with passive cooling

### Edge Sensors (per zone)
- **ESP32-S3** dev board — WiFi + BLE, deep sleep capable
- Capacitive soil moisture sensor (v1.2+)
- DS18B20 waterproof temperature probe
- BME280 (temperature + humidity + pressure)
- Optional: analog pH sensor module

### Actuators
- 12V solenoid valves (normally closed, 3/4" thread)
- Relay module (4-channel, optoisolated)
- 12V power supply for valves
- Waterproof enclosure (IP65+)

### Compost Monitoring
- K-type thermocouple + MAX6675 module (high-temp capable)
- Soil moisture sensor (for compost moisture)
- Long probe housing (stainless steel, 30cm+)

## ESP32 Sensor Node Setup

### Wiring

```
ESP32-S3
├── GPIO 34 ─── Soil Moisture (analog)
├── GPIO 4  ─── DS18B20 (OneWire, 4.7kΩ pull-up)
├── I2C SDA ─── BME280
├── I2C SCL ─── BME280
└── GPIO 2  ─── Status LED
```

### Firmware

Each ESP32 runs a minimal MQTT firmware:
1. Wake from deep sleep
2. Read sensors
3. Publish to MQTT topic: `369/sensors/{zone}/{metric}`
4. Return to deep sleep (configurable interval, default 5min)

Recommended firmware: **ESPHome** or custom MicroPython.

### MQTT Topic Convention

```
369/sensors/{zone-id}/{metric-type}
369/actuators/{zone-id}/{actuator-type}
```

Payload format (JSON):
```json
{
  "value": 45.2,
  "unit": "%",
  "metric": "soil.moisture",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## Network Architecture

```
[ESP32 nodes] ──WiFi──▶ [Mosquitto MQTT] ◀── [369 HAL/MQTT Adapter]
                              │
                              ▼
                     [Raspberry Pi 4]
                     ┌────────────────┐
                     │ Docker Compose │
                     │ • Redis        │
                     │ • PostgreSQL   │
                     │ • 369 API      │
                     │ • Mosquitto    │
                     └────────────────┘
```

## Power Considerations

- ESP32 deep sleep: ~10µA (months on 18650 battery)
- Pi 4 idle: ~3W, under load: ~6W
- Solenoid valves: ~350mA @ 12V each (only during actuation)
- Total backyard system: ~10W average

## Weatherproofing

- All outdoor electronics in IP65 enclosures minimum
- Conformal coating on PCBs
- UV-resistant cable ties and conduit
- Silicone sealant on cable entry points
