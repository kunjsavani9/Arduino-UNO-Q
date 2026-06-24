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
label = "circle"

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

    # Stop if time is up
    if done:
        return

    elapsed = time.time() - start_time

    if elapsed >= COLLECTION_SECS:
        if not done:
            done = True
            logger.info(f"[{label.upper()}] 2 minutes complete!")
            logger.info(f"[{label.upper()}] Total samples saved: {total_saved}")
            logger.info(f"[{label.upper()}] File: {collection_csv_path.name}")
            App.stop()
        return

    # Show countdown every 30 seconds
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