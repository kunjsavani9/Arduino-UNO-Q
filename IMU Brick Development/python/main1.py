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
