# Arduino-UNO-Q

**Edge AI & Industrial applications on the Arduino UNO Q.**

This repository is a collection of hands-on Edge AI and industrial-control projects built on the [Arduino UNO Q](https://www.arduino.cc/) platform using the **Arduino App Lab** development environment. Each project runs across both processors of the board and demonstrates a different slice of on-device intelligence — from classical control loops to gesture recognition to vision-language understanding.

---

## The Platform

The Arduino UNO Q is a **dual-processor** board:

| Processor | Role | Runs |
|-----------|------|------|
| **Qualcomm QRB2210 / QCS6490** | Linux MPU (`aarch64`) | Debian — Python (`main.py`), ML inference, web UIs |
| **STM32U585 / U5** | Real-time MCU | Zephyr RTOS — firmware (`sketch.ino`, C++) |

All projects are developed in **Arduino App Lab** (not the Arduino IDE). Code is split between:

- `sketch.ino` — C++ running on the STM32 MCU
- `main.py` — Python running on the Linux MPU
- `app.yaml` — App Lab brick/app declarations

**Inter-processor communication (IPC)** between Linux and the STM32 uses the USB gadget serial device `/dev/ttyGS0` with a plain-text protocol. Shell commands (ADB / SSH) are run from an external terminal, not inside App Lab.

---

## Projects

### Dual Channel Thermal PID Controller
A two-channel closed-loop thermal controller. The STM32 firmware runs the real-time PID loops and exchanges setpoints/readings with Linux over `/dev/ttyGS0` using a simple `SP:value\n` protocol. The Python layer hosts a live web dashboard (Chart.js) that plots both channels in real time and lets the user adjust setpoints.

- Real-time dual-channel PID control on the MCU
- Setpoint / telemetry IPC over USB gadget serial
- Browser dashboard with live charts

### Face Recognition
An on-device person-recognition pipeline. A MobileNetV2 image-classification model identifies known individuals from a USB webcam (Logitech C270 via a USB-C PD hub) and serves a personalized web UI with per-person greetings.

- MobileNetV2 image classification (~85.7% validation accuracy)
- ~6 ms inference on the Linux MPU
- Personalized App Lab web interface
- Runs in network mode (Wi-Fi + powered USB hub for the camera)

### IMU Brick Development
A custom App Lab brick (`gesture_classifier`) that wraps a TensorFlow Lite gesture model trained with Edge Impulse. Accelerometer data is streamed from the Modulino Movement (LSM6DSOX) IMU and classified into gestures on-device.

- Accelerometer-only capture (`raw_x`, `raw_y`, `raw_z`) at 62.5 Hz
- Labels: `idle`, `up_down`, `circle`
- `Bridge.notify()` push pattern for sensor streaming
- TFLite model trained via Edge Impulse, packaged as a reusable brick

### Visual Question & Answer
An Edge Vision Assistant that answers natural-language questions about what the camera sees. It supports a dual backend: a local vision-language model for fully on-LAN operation, with a cloud model as fallback.

- Primary backend: **Ollama** (`llava:latest`) on the local network
- Fallback backend: **Gemini** (`gemini-2.5-flash`) via the OpenAI-compatible endpoint
- Web UI for asking questions about live camera frames

---

## Repository Structure

```
Arduino-UNO-Q/
├── Dual Channel Thermal PID Controller/
├── Face Recognition/
├── IMU Brick Development/
├── Visual Question & Answer/
└── README.md
```

Each project folder typically contains its own `sketch.ino`, `main.py`, `app.yaml`, and supporting web/UI assets.

---

## Getting Started

1. Open the desired project folder in **Arduino App Lab**.
2. Connect the Arduino UNO Q and let App Lab flash both the MCU (`sketch.ino`) and Linux (`main.py`) sides.
3. For projects that need camera/network access, connect a USB-C PD hub and join Wi-Fi.
4. Open the web UI (served by the Linux MPU) in a browser on the same network.

> **Note:** Vision/cloud projects expect API keys and backend addresses to be supplied via configuration or environment variables. Keep credentials out of source control.

---

## Tech Stack

- **Hardware:** Arduino UNO Q, Modulino Movement (LSM6DSOX), Logitech C270 webcam, USB-C PD hub
- **Environment:** Arduino App Lab (Python + C++)
- **ML / Inference:** TensorFlow Lite, Edge Impulse, MobileNetV2, Ollama (`llava`), Gemini
- **UI:** HTML / JavaScript / Chart.js
- **RTOS:** Zephyr (STM32)

**Languages:** HTML · Python · JavaScript · C++

---
## Demo Video

https://drive.google.com/drive/folders/1Kua1aSmeAhjPNTTjuvVJiPrs7v6err-W?usp=drive_link

---
## Author

**Kunj Savani** ([@kunjsavani9](https://github.com/kunjsavani9))
