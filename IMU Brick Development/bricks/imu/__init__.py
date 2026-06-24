# bricks/imu/__init__.py

import subprocess
import json
import time

MODEL_PATH = "/app/python/gesture_model.eim"

class GestureClassifier:

    def __init__(self):
        print("[GestureClassifier] Starting .eim runner...")

        # ── Read model params dynamically from --print-info ──
        info_result = subprocess.run(
            [MODEL_PATH, "--print-info"],
            capture_output=True, text=True
        )
        # Output has a text line first, then JSON — find the JSON part
        info_lines = info_result.stdout.strip().split("\n")
        info_json  = "\n".join(
            line for line in info_lines
            if line.strip().startswith("{") or line.strip().startswith("}")
            or (info_lines.index(line) > 0)
        )
        # Parse from second line onward (skip "Edge Impulse Linux..." text)
        model_info   = json.loads("\n".join(info_lines[1:]))
        params       = model_info["model_parameters"]

        self.labels  = params["labels"]
        self.freq    = params["frequency"]
        self.window  = params["input_features_count"] // params["axis_count"]

        print(f"[GestureClassifier] Labels  : {self.labels}")
        print(f"[GestureClassifier] Freq    : {self.freq} Hz")
        print(f"[GestureClassifier] Window  : {self.window} samples")

        # ── Start stdin runner ────────────────────────────────
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
        self.process.stdout.readline()

        # Hello handshake
        self.process.stdin.write(json.dumps({"id": 1, "hello": 1}).encode() + b"\n")
        self.process.stdin.flush()

        hello_resp = json.loads(self.process.stdout.readline().decode().strip())
        if not hello_resp.get("success", False):
            raise RuntimeError(f"Handshake failed: {hello_resp}")

        self._msg_id = 1
        print("[GestureClassifier] Ready.")

    def predict(self, window_data: list) -> tuple:
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