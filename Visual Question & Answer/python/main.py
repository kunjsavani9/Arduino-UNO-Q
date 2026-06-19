"""
Visual QA - Vision Assistant (dual backend)
===========================================
On capture, the current webcam frame is sent to a vision-language model and
the answer is shown on the dashboard. Two backends, tried in order:

  1. PRIMARY  : Ollama on the local network  (private, no cloud, free)
  2. FALLBACK : Google Gemini cloud API      (used only if Ollama fails)

If Ollama is unreachable, slow, or errors, the app automatically falls back to
Gemini so a live demo never dead-ends. The on-board RGB LED (via the STM32)
mirrors pipeline status. Open from a browser on the same network:

    http://<board-ip>:7000
"""

import sys
sys.path.insert(0, "/app")

import time
import base64

import requests
from arduino.app_utils import App, Bridge
from arduino.app_utils.image import compress_to_jpeg
from arduino.app_bricks.web_ui import WebUI
from arduino.app_peripherals.camera import Camera

# =================================================================
# BACKEND 1 (PRIMARY) - Ollama on your laptop / LAN
#   On the machine running Ollama, start it so the board can reach it:
#       OLLAMA_HOST=0.0.0.0 ollama serve
#       ollama pull llava
#   Then set OLLAMA_HOST below to that machine's LAN IP.
# =================================================================
USE_OLLAMA     = True
OLLAMA_HOST    = "192.168.1.19"
OLLAMA_PORT    = 11434
OLLAMA_MODEL   = "llava:latest"
OLLAMA_TIMEOUT = 60          # seconds to wait before falling back to Gemini

OLLAMA_CHAT_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/chat"
OLLAMA_TAGS_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/tags"

# =================================================================
# BACKEND 2 (FALLBACK) - Google Gemini (OpenAI-compatible endpoint)
#   Get a free key at https://aistudio.google.com  (no credit card).
#   Set USE_GEMINI = False to disable the fallback entirely.
# =================================================================
USE_GEMINI        = True
GEMINI_KEY        = "AQ.Ab8RN6JXGu376zK-bF4qavF8Nihqy6fnPZwAqUCvHh33Qjy1yg"
GEMINI_URL        = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
GEMINI_MODEL      = "gemini-2.5-flash"
GEMINI_MAX_TOKENS = 512      # higher: 2.5 "thinking" models spend tokens before the visible answer

# =================================================================
# Shared
# =================================================================
DEFAULT_QUESTION = "Describe this scene in one short paragraph."
JPEG_QUALITY     = 80
SYSTEM_PROMPT = ("You are a vision assistant. Answer the user's question about the image "
                 "directly and concisely in 1-3 sentences. Do not begin with phrases like "
                 "'Based on the image' or 'Here are'.")


def gemini_key_ok():
    return USE_GEMINI and bool(GEMINI_KEY) and GEMINI_KEY != "PASTE_YOUR_GEMINI_KEY_HERE"


def ollama_online():
    if not USE_OLLAMA:
        return False
    try:
        return requests.get(OLLAMA_TAGS_URL, timeout=3).status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------
# Camera + WebUI
# ---------------------------------------------------------------
cam = Camera("usb:0", resolution=(640, 480), fps=10)
try:
    cam.start()
    print("[VisualQA] camera started")
except Exception as e:
    print(f"[VisualQA] camera start failed: {e}")

ui = WebUI()
ui.expose_camera("/video_feed", cam, jpeg_quality=JPEG_QUALITY)


def led(state):
    try:
        Bridge.call("set_status", state)
    except Exception:
        pass


# ---------------------------------------------------------------
# Backend callers
# ---------------------------------------------------------------
def ask_ollama(b64_image, question):
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question, "images": [b64_image]},
        ],
    }
    r = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=OLLAMA_TIMEOUT)
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


def ask_gemini(b64_image, question):
    headers = {"Authorization": f"Bearer {GEMINI_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": GEMINI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": question},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}},
            ]},
        ],
        "max_tokens": GEMINI_MAX_TOKENS,
        "temperature": 0.2,
    }
    r = requests.post(GEMINI_URL, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def ask_vlm(b64_image, question):
    """Try Ollama first, then Gemini. Returns (answer, source)."""
    errors = []

    if USE_OLLAMA:
        try:
            return ask_ollama(b64_image, question), f"Ollama \u00b7 {OLLAMA_MODEL}"
        except Exception as e:
            msg = f"Ollama unavailable ({e}); falling back to Gemini"
            print("[VisualQA]", msg)
            errors.append(msg)

    if gemini_key_ok():
        try:
            return ask_gemini(b64_image, question), f"Gemini \u00b7 {GEMINI_MODEL}"
        except Exception as e:
            msg = f"Gemini failed: {e}"
            print("[VisualQA]", msg)
            errors.append(msg)

    raise RuntimeError(" | ".join(errors) or
                       "No backend configured - enable Ollama or set a Gemini key.")


# ---------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------
def ask(payload: dict):
    question = (payload or {}).get("question") or DEFAULT_QUESTION

    frame = cam.capture()
    if frame is None:
        return {"error": "Camera has no frame yet - is the webcam connected?"}
    jpeg = compress_to_jpeg(frame, quality=JPEG_QUALITY)
    if jpeg is None:
        return {"error": "Failed to encode the captured frame."}
    b64 = base64.b64encode(jpeg.tobytes()).decode("utf-8")

    led("THINK")
    t0 = time.perf_counter()
    try:
        answer, source = ask_vlm(b64, question)
    except Exception as e:
        led("IDLE")
        return {"error": str(e)}
    dt = time.perf_counter() - t0
    led("READY")

    return {
        "question": question,
        "answer":   answer,
        "source":   source,                 # which backend answered (Ollama / Gemini)
        "latency":  round(dt, 1),
        "image":    "data:image/jpeg;base64," + b64,
    }


def status():
    ol = ollama_online()
    gm = gemini_key_ok()
    if ol:
        provider = f"Ollama \u00b7 {OLLAMA_MODEL} (local)"
    elif gm:
        provider = f"Gemini \u00b7 {GEMINI_MODEL} (cloud fallback)"
    else:
        provider = "no backend"
    return {"model_online": ol or gm, "provider": provider,
            "ollama": ol, "gemini": gm}


ui.expose_api("POST", "/ask",    ask)
ui.expose_api("GET",  "/status", status)

print(f"[VisualQA] dashboard on 7000 | primary: Ollama {OLLAMA_MODEL} @ {OLLAMA_HOST} | "
      f"fallback: Gemini {GEMINI_MODEL} (key set: {gemini_key_ok()})")

App.run()