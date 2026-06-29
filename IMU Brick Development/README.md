# 🏎️ IMU Brick Development
## Gesture Recognition with Modulino Movement + Edge Impulse + Custom App Brick
**Platform:** Arduino UNO Q · **Sensor:** Modulino Movement (LSM6DSOX) · **Model:** Edge Impulse `.eim`
**Gestures:** `idle` · `up_down` · `circle` · **Sample Rate:** 62.5 Hz · **Window:** 2s / 125 samples

---

## Project File Structure

```
IMU Brick Development/
├── bricks/
│   └── imu/
│       ├── __init__.py          ← GestureClassifier custom brick
│       ├── README.md
│       ├── brick_compose.yaml
│       └── brick_config.yaml
├── python/
│   ├── data/
│   │   ├── train_data_idle_YYYYMMDD_HHMMSS.csv
│   │   ├── train_data_up_down_YYYYMMDD_HHMMSS.csv
│   │   └── train_data_circle_YYYYMMDD_HHMMSS.csv
│   ├── gesture_model.eim        ← Edge Impulse model binary
│   └── main.py                  ← Phase A: data collection OR Phase B: live inference
├── sketch/
│   └── sketch.ino               ← STM32 MCU: reads Modulino Movement, pushes via Bridge
├── app.yaml
└── README.md
```

---

## Hardware

| Component | Connection |
|---|---|
| Modulino Movement (LSM6DSOX) | Qwiic connector → UNO Q Wire1 |
| Arduino UNO Q | USB-C to Mac |

---

## Phase 1 — sketch.ino (IMU Reader)

Paste into `sketch.ino` in App Lab. This runs on the STM32 MCU and streams accelerometer data to Python via `Bridge.notify()` at 62.5 Hz.

```cpp
#include <Arduino_RouterBridge.h>
#include <Arduino_Modulino.h>

ModulinoMovement movement;

float x_accel, y_accel, z_accel;

unsigned long previousMillis = 0;
const long interval = 16;   // 16ms = 62.5 Hz
int has_movement = 0;

void setup() {
  Serial.begin(115200);
  Bridge.begin();

  Modulino.begin(Wire1);    // Wire1 — not Wire

  while (!movement.begin()) {
    Serial.println("Waiting for movement sensor...");
    delay(1000);
  }

  Serial.println("IMU ready. Streaming via Bridge.notify...");
}

void loop() {
  unsigned long currentMillis = millis();

  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;

    has_movement = movement.update();

    if (has_movement == 1) {
      x_accel = movement.getX();
      y_accel = movement.getY();
      z_accel = movement.getZ();

      Bridge.notify("record_sensor_movement", x_accel, y_accel, z_accel);
    }
  }
}
```

Click **Run** — Serial Monitor should show:
```
IMU ready. Streaming via Bridge.notify...
```

---

## Phase 2A — main.py (Data Collection — Fixed 2 Minutes Per Class)

Use this version of `main.py` to collect gesture training data.
Each run collects exactly **2 minutes** of data then stops automatically.

> **Change `label` on line 14 before each run.**

```python
import pandas as pd
import time
import os

from collections import deque
from arduino.app_utils import *
from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────────────────────
# CHANGE THIS before each run:
#   "idle"     →  hold board completely still
#   "up_down"  →  move board up and down (~15 cm)
#   "circle"   →  move board in horizontal circles (~15 cm)
# ─────────────────────────────────────────────────────────
label = "idle"

SAMPLES_MAX      = 10
COLLECTION_SECS  = 120   # 2 minutes fixed per class

logger = Logger("gesture-recognition")

# ── File path setup ───────────────────────────────────────
timestamp           = datetime.now().strftime("%Y%m%d_%H%M%S")
collection_filename = f"train_data_{label}_{timestamp}.csv"
collection_csv_path = Path.cwd() / "python" / "data" / collection_filename

collection_csv_path.parent.mkdir(parents=True, exist_ok=True)

logger.info(f"Label       : {label}")
logger.info(f"Duration    : {COLLECTION_SECS}s (2 minutes)")
logger.info(f"Writing to  : {collection_csv_path.resolve()}")

# ── State ─────────────────────────────────────────────────
sample_list  = deque(maxlen=SAMPLES_MAX)
start_time   = None
total_saved  = 0
done         = False

# ── Bridge callback ───────────────────────────────────────
def record_sensor_movement(x: float, y: float, z: float):
    global start_time, total_saved, done

    # Start timer on first sample received
    if start_time is None:
        start_time = time.time()
        logger.info(f"[{label.upper()}] Collection started — 2 minutes running...")

    # Stop if already done
    if done:
        return

    elapsed = time.time() - start_time

    # Stop after 2 minutes
    if elapsed >= COLLECTION_SECS:
        if not done:
            done = True
            logger.info(f"[{label.upper()}] 2 minutes complete!")
            logger.info(f"[{label.upper()}] Total samples saved: {total_saved}")
            logger.info(f"[{label.upper()}] File: {collection_csv_path.name}")
            App.stop()
        return

    # Countdown reminders
    remaining = int(COLLECTION_SECS - elapsed)
    if remaining in [90, 60, 30] and len(sample_list) == 0:
        logger.info(f"[{label.upper()}] {remaining}s remaining...")

    try:
        sample = {
            "time":  time.time() * 1000,
            "raw_x": float(x),
            "raw_y": float(y),
            "raw_z": float(z)
        }

        sample_list.append(sample)

        if len(sample_list) == SAMPLES_MAX:
            df_chunk = pd.DataFrame(list(sample_list))

            df_chunk.to_csv(
                collection_csv_path,
                mode="a",
                header=not collection_csv_path.exists(),
                index=False
            )

            total_saved += SAMPLES_MAX
            elapsed_str  = f"{int(elapsed)}s"
            logger.info(f"  [{elapsed_str:>4}] Saved {SAMPLES_MAX} samples "
                        f"(total: {total_saved}) → {collection_csv_path.name}")

            sample_list.clear()

    except Exception as e:
        logger.exception(f"record_sensor_movement error: {e}")

# ── Register Bridge provider ──────────────────────────────
try:
    Bridge.provide("record_sensor_movement", record_sensor_movement)
    logger.info("Waiting for IMU data from MCU...")
except RuntimeError:
    logger.debug("'record_sensor_movement' already registered")

# ── Keep process alive ────────────────────────────────────
App.run()
```

### Collection Procedure

| Run | `label` value | Gesture to perform | Auto-stops after |
|---|---|---|---|
| Run 1 | `"idle"` | Hold board completely still on table | 2 minutes |
| Run 2 | `"up_down"` | Move board up ~15 cm then back down, steady rhythm | 2 minutes |
| Run 3 | `"circle"` | Move board in horizontal circles ~15 cm diameter | 2 minutes |

**Expected output during collection:**
```
Label       : idle
Duration    : 120s (2 minutes)
Writing to  : /app/python/data/train_data_idle_20260624_HHMMSS.csv
Waiting for IMU data from MCU...
[IDLE] Collection started — 2 minutes running...
  [  3s] Saved 10 samples (total: 10)   → train_data_idle_...csv
  [  6s] Saved 10 samples (total: 20)   → train_data_idle_...csv
[IDLE] 90s remaining...
[IDLE] 60s remaining...
[IDLE] 30s remaining...
[IDLE] 2 minutes complete!
[IDLE] Total samples saved: 7500
[IDLE] File: train_data_idle_20260624_HHMMSS.csv
```

---

## Phase 3 — Transfer Files to Mac

Run in a **Mac terminal** (not board shell):

```bash
scp -r arduino@192.168.1.28:/home/arduino/ArduinoApps/imu-brick-development/python/data /Users/kunj/Downloads/gesture_data
```

Verify all 3 files:
```bash
ls /Users/kunj/Downloads/gesture_data
# Expected:
# train_data_idle_20260624_HHMMSS.csv
# train_data_up_down_20260624_HHMMSS.csv
# train_data_circle_20260624_HHMMSS.csv
```

---

## Phase 4 — Upload to Edge Impulse

1. Go to [studio.edgeimpulse.com](https://studio.edgeimpulse.com) → your **IMU** project → **Data acquisition**
2. Click **Upload data** (cloud icon) → **CSV Wizard**
3. Upload each file with these settings:

| File | Label | Category |
|---|---|---|
| `train_data_idle_*.csv` | `idle` | Auto-split |
| `train_data_up_down_*.csv` | `up_down` | Auto-split |
| `train_data_circle_*.csv` | `circle` | Auto-split |

**CSV Wizard settings:**
- Is this time-series data? → **Yes**
- Format → **Each row contains a reading, and sensor values are columns**
- Timestamp column → `time` (Milliseconds since epoch)
- Value columns → `raw_x`, `raw_y`, `raw_z` (all checked)
- Label → type gesture name per file
- Click **Next, split up into samples** → Sample length: `2000 ms`

---

## Phase 5 — Create Impulse & Train

### Create Impulse
**Impulse design → Create impulse:**

| Setting | Value |
|---|---|
| Window size | `2000 ms` |
| Window increase | `1000 ms` |
| Frequency | `62.5 Hz` |
| Processing block | Spectral Analysis (raw_x, raw_y, raw_z) |
| Learning block | Classification |

Click **Save Impulse**

### Spectral Features
→ **Spectral features** → **Save parameters** → **Generate features**

Verify 3 colour clusters visible in the feature explorer.

### Classifier Training
→ **Classifier**

| Setting | Value |
|---|---|
| Training cycles | `30` |
| Learning rate | `0.0005` |
| Validation split | `20%` |

Click **Start training** — target accuracy >80%

---

## Phase 6 — Deploy Model

→ **Deployment** → select **Arduino UNO Q** → **Quantized (int8)** → **Build**

Download the `.eim` file. Then transfer to board:

```bash
# Mac terminal
scp /Users/kunj/Downloads/ei-imu-arduino-uno-q-v1.eim \
    arduino@192.168.1.28:/home/arduino/ArduinoApps/imu-brick-development/python/gesture_model.eim
```

Make it executable:
```bash
# Board shell (SSH or ADB)
chmod +x /home/arduino/ArduinoApps/imu-brick-development/python/gesture_model.eim
ls -lh /home/arduino/ArduinoApps/imu-brick-development/python/gesture_model.eim
# Expected: -rwxr-xr-x ... 14M
```

Verify model info:
```bash
/home/arduino/ArduinoApps/imu-brick-development/python/gesture_model.eim --print-info
# Expected: JSON with labels: ["circle","idle","up_down"], frequency: 62.5, input_features_count: 375
```

---

## Phase 7 — Board Setup (Run Once on Every New Board)

> Run all commands in board shell via SSH or ADB.

### Step 1 — Verify internet connectivity

```bash
ping -c 3 8.8.8.8
# Must show: 3 packets transmitted, 3 received
```

If ping fails, fix DNS first:
```bash
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
echo "nameserver 8.8.4.4" | sudo tee -a /etc/resolv.conf
ping -c 3 deb.debian.org
```

---

### Step 2 — Update package list

```bash
sudo apt-get update
```

---

### Step 3 — Install system packages

```bash
sudo apt-get install -y \
  python3-pip \
  python3-pyaudio \
  portaudio19-dev \
  libportaudio2
```

---

### Step 4 — Install Python packages

```bash
python3 -m pip install \
  numpy \
  six \
  requests \
  pyserial \
  psutil \
  pandas \
  opencv-python-headless \
  --break-system-packages
```

---

### Step 5 — Verify all dependencies

```bash
python3 -c "
import numpy, six, cv2, pandas, serial, psutil
print('All dependencies OK')
"
# Expected: All dependencies OK
```

---

### Step 6 — Transfer .eim model from Mac to board

```bash
# Run on Mac terminal (not board shell)
scp /Users/kunj/Downloads/ei-imu-arduino-uno-q-v1.eim \
    arduino@192.168.1.28:/home/arduino/ArduinoApps/imu-brick-development/python/gesture_model_public.eim
```

---

### Step 7 — Fix execute permission

```bash
# Run on board shell — required after EVERY file transfer
chmod +x /home/arduino/ArduinoApps/imu-brick-development/python/gesture_model_public.eim
```

---

### Step 8 — Verify model is ready

```bash
ls -lh /home/arduino/ArduinoApps/imu-brick-development/python/gesture_model_public.eim
# Must show: -rwxr-xr-x ... 14M

/home/arduino/ArduinoApps/imu-brick-development/python/gesture_model_public.eim --print-info
# Must show JSON with:
#   "labels": ["circle", "idle", "up_down"]
#   "frequency": 62.5
#   "input_features_count": 375
```

---

### One-liner (Steps 2–5 combined)

```bash
sudo apt-get update && \
sudo apt-get install -y python3-pip python3-pyaudio portaudio19-dev libportaudio2 && \
python3 -m pip install numpy six requests pyserial psutil pandas opencv-python-headless --break-system-packages && \
python3 -c "import numpy, six, cv2, pandas, serial, psutil; print('All OK')"
```

> **Important:** `chmod +x` must be run every time a new `.eim` file is transferred to the board. File transfers do not preserve execute permission.

---

## Phase 8 — Create Custom Brick

In App Lab → grid icon (Bricks panel) → **Create custom brick** → name: `imu` → **Create**

App Lab generates:
```
bricks/imu/__init__.py
bricks/imu/README.md
bricks/imu/brick_compose.yaml
bricks/imu/brick_config.yaml
```

Open `bricks/imu/__init__.py` and paste:

```python
# bricks/imu/__init__.py

import subprocess
import json
import time

MODEL_PATH = "/app/python/gesture_model_public.eim"

class GestureClassifier:

    def __init__(self):
        print("[GestureClassifier] Starting .eim runner...")

        # Read model parameters dynamically
        info_result = subprocess.run(
            [MODEL_PATH, "--print-info"],
            capture_output=True, text=True
        )
        info_lines = info_result.stdout.strip().split("\n")
        model_info = json.loads("\n".join(info_lines[1:]))
        params     = model_info["model_parameters"]

        self.labels = params["labels"]
        self.freq   = params["frequency"]
        self.window = params["input_features_count"] // params["axis_count"]

        print(f"[GestureClassifier] Labels  : {self.labels}")
        print(f"[GestureClassifier] Freq    : {self.freq} Hz")
        print(f"[GestureClassifier] Window  : {self.window} samples")

        # Start stdin runner
        self.process = subprocess.Popen(
            [MODEL_PATH, "stdin"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        time.sleep(1.0)

        if self.process.poll() is not None:
            raise RuntimeError("[GestureClassifier] .eim exited immediately")

        # Drain startup line
        startup = self.process.stdout.readline().decode().strip()
        print(f"[GestureClassifier] Startup: '{startup}'")

        # Hello handshake — id field required in ALL messages
        hello_msg = json.dumps({"id": 1, "hello": 1}) + "\n"
        self.process.stdin.write(hello_msg.encode())
        self.process.stdin.flush()

        hello_resp = json.loads(self.process.stdout.readline().decode().strip())
        if not hello_resp.get("success", False):
            raise RuntimeError(f"[GestureClassifier] Handshake failed: {hello_resp}")

        print("[GestureClassifier] Handshake OK")

        self._msg_id = 1
        print("[GestureClassifier] Ready.")

    def predict(self, window_data: list) -> tuple:
        """
        Args:
            window_data : list of dicts with keys raw_x, raw_y, raw_z
                          length must equal self.window (125 samples at 62.5 Hz)
        Returns:
            (label: str, confidence: float, latency_ms: float)
        """
        features = []
        for sample in window_data:
            features.append(float(sample['raw_x']))
            features.append(float(sample['raw_y']))
            features.append(float(sample['raw_z']))

        self._msg_id += 1

        t0  = time.perf_counter()
        msg = json.dumps({"id": self._msg_id, "classify": features}) + "\n"
        self.process.stdin.write(msg.encode())
        self.process.stdin.flush()

        result_line = self.process.stdout.readline().decode().strip()
        latency_ms  = (time.perf_counter() - t0) * 1000

        try:
            result = json.loads(result_line)
        except json.JSONDecodeError:
            print(f"[GestureClassifier] Bad JSON: '{result_line[:100]}'")
            return "unknown", 0.0, round(latency_ms, 2)

        if 'result' in result and 'classification' in result['result']:
            classification = result['result']['classification']
        elif 'classification' in result:
            classification = result['classification']
        else:
            print(f"[GestureClassifier] Unexpected format: {result}")
            return "unknown", 0.0, round(latency_ms, 2)

        label      = max(classification, key=classification.get)
        confidence = classification[label]

        return label, round(confidence, 4), round(latency_ms, 2)

    def close(self):
        self.process.terminate()
        print("[GestureClassifier] Runner stopped.")
```

---

## Phase 9 — main.py (Live Inference)

Replace `main.py` with this for live gesture classification:

```python
import sys
import time
sys.path.insert(0, "/app")

from collections import deque
from arduino.app_utils import *
from bricks.imu import GestureClassifier

# ── Init classifier brick ──────────────────────────────────
classifier    = GestureClassifier()
WINDOW_SIZE   = classifier.window   # auto-read from model (125 samples)
window_buffer = deque(maxlen=WINDOW_SIZE)

print(f"[Main] Window size : {WINDOW_SIZE} samples")
print(f"[Main] Labels      : {classifier.labels}")
print("[Main] Perform gestures — results will print below")
print("=" * 55)

# ── Bridge callback ────────────────────────────────────────
def record_sensor_movement(x: float, y: float, z: float):
    window_buffer.append({
        "raw_x": float(x),
        "raw_y": float(y),
        "raw_z": float(z)
    })

    if len(window_buffer) == WINDOW_SIZE:
        label, confidence, latency = classifier.predict(list(window_buffer))

        print(
            f"  Gesture : [{label.upper():10s}]  "
            f"Confidence : {confidence * 100:.1f}%  "
            f"Latency : {latency:.1f} ms"
        )

        window_buffer.clear()

# ── Register Bridge provider ───────────────────────────────
try:
    Bridge.provide("record_sensor_movement", record_sensor_movement)
    print("[Main] Bridge provider registered. Waiting for IMU data...")
except RuntimeError:
    print("[Main] Bridge provider already registered.")

# ── Keep process alive ─────────────────────────────────────
App.run()
```

---

## Expected Output

```
[GestureClassifier] Labels  : ['circle', 'idle', 'up_down']
[GestureClassifier] Freq    : 62.5 Hz
[GestureClassifier] Window  : 125 samples
[GestureClassifier] Startup: 'Edge Impulse Linux impulse runner - listening for JSON messages on stdin'
[GestureClassifier] Handshake OK
[GestureClassifier] Ready.
[Main] Window size : 125 samples
[Main] Labels      : ['circle', 'idle', 'up_down']
[Main] Perform gestures — results will print below
=======================================================
[Main] Bridge provider registered. Waiting for IMU data...
  Gesture : [IDLE      ]  Confidence : 77.0%  Latency : 5.3 ms
  Gesture : [UP_DOWN   ]  Confidence : 89.4%  Latency : 5.1 ms
  Gesture : [CIRCLE    ]  Confidence : 84.2%  Latency : 5.4 ms
```

---

## Quick Reference — All Commands

```bash
# ── Board setup (run once on every new board) ─────────────────
sudo apt-get update
sudo apt-get install -y python3-pip python3-pyaudio portaudio19-dev libportaudio2
python3 -m pip install numpy six requests pyserial psutil pandas opencv-python-headless --break-system-packages
python3 -c "import numpy, six, cv2, pandas, serial, psutil; print('All OK')"

# ── Fix DNS if apt-get fails (no internet) ────────────────────
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
echo "nameserver 8.8.4.4" | sudo tee -a /etc/resolv.conf

# ── Transfer training data from board to Mac ───────────────────
scp -r arduino@192.168.1.28:/home/arduino/ArduinoApps/imu-brick-development/python/data \
    /Users/kunj/Downloads/gesture_data

# ── Transfer .eim model from Mac to board ─────────────────────
scp /Users/kunj/Downloads/ei-imu-arduino-uno-q-v1.eim \
    arduino@192.168.1.28:/home/arduino/ArduinoApps/imu-brick-development/python/gesture_model_public.eim

# ── Fix permission — run after EVERY transfer ─────────────────
chmod +x /home/arduino/ArduinoApps/imu-brick-development/python/gesture_model_public.eim

# ── Verify model ───────────────────────────────────────────────
ls -lh /home/arduino/ArduinoApps/imu-brick-development/python/gesture_model_public.eim
# Must show: -rwxr-xr-x ... 14M

/home/arduino/ArduinoApps/imu-brick-development/python/gesture_model_public.eim --print-info
# Must show labels: ["circle","idle","up_down"]

# ── Board access ───────────────────────────────────────────────
ssh arduino@192.168.1.28
adb shell
```

---

## Troubleshooting

| Error | Fix |
|---|---|
| `Temporary failure resolving 'deb.debian.org'` | Board has no internet. Fix DNS: `echo "nameserver 8.8.8.8" \| sudo tee /etc/resolv.conf` then retry |
| `PermissionError: [Errno 13] Permission denied` | Run `chmod +x` on the `.eim` file — required after every transfer |
| `FileNotFoundError: gesture_model.eim` | Model must be in `python/` folder — path must be `/app/python/gesture_model_public.eim` |
| `pip3: command not found` | Use `python3 -m pip install` instead |
| `Missing 'id' field in message` | All `.eim` messages require `"id"` field |
| `Invalid message, should initialize first` | Must send `{"id": 1, "hello": 1}` before any classify messages |
| `ModuleNotFoundError: edge_impulse_linux` | Package not available in Docker — use subprocess approach |
| `exited with code 0` immediately | Missing `App.run()` at end of `main.py` |
| `TypeError: not all arguments converted` | Use f-string: `logger.info(f"text {var}")` not `logger.info("text", var)` |
| `No module named 'numpy'` | Run `python3 -m pip install numpy --break-system-packages` |
| `No module named 'six'` | Run `python3 -m pip install six --break-system-packages` |
| `Missing OpenCV` | Run `python3 -m pip install opencv-python-headless --break-system-packages` |

---

*Arduino UNO Q · Bitgreen Technolabz · Edge AI Track 3 · Gesture Recognition*
