# Visual QA — Edge Vision Assistant

A live webcam dashboard for the **Arduino UNO Q**. Frame a subject, tap the
camera button, ask a question in plain English, and a vision-language model
answers. The app runs on the board (App Lab WebUI brick + USB webcam); the
model inference is delegated to one of two backends.

## Dual backend (local-first, cloud fallback)

The app tries two backends **in order** on every capture:

1. **Primary — Ollama (local network).** A vision model (`llava`) running on
   your laptop or a LAN machine. Private (frames never leave your network),
   free, and the "real edge" story for the curriculum.
2. **Fallback — Google Gemini (cloud).** Used automatically only if Ollama is
   unreachable, times out, or errors. Keeps a live workshop from dead-ending.

Each answer is tagged with the backend that produced it, so you can see at a
glance whether it came from the local model or the cloud.

## What you need

- Arduino UNO Q, flashed and connected in Arduino App Lab.
- A USB webcam plugged into the board.
- A laptop / machine on the **same network** as the board, running Ollama
  (for the primary backend).
- A free Google AI Studio API key (for the cloud fallback). Optional — set
  `USE_GEMINI = False` to disable.

## File layout

```
visual_qa/
  app.yaml          # declares the WebUI-HTML brick
  sketch/
    sketch.ino      # STM32 sketch: RGB status LED via Bridge
  python/
    main.py         # the app: camera, dashboard API, backend routing
  assets/
    index.html      # the dashboard UI
    bitgreen-logo.png
  README.md
```

## Setup

### 1. Ollama (primary backend)

On the laptop that will run the model:

- Install Ollama from https://ollama.com and pull a vision model:
  ```
  ollama pull llava
  ```
- Start Ollama **bound to all interfaces** so the board can reach it over the
  LAN (by default Ollama only listens on localhost):
  ```
  OLLAMA_HOST=0.0.0.0 ollama serve
  ```
- Find that machine's LAN IP (e.g. `192.168.1.19`) and make sure its firewall
  allows inbound port `11434`.

In `python/main.py`, set the primary backend to match:
```
OLLAMA_HOST  = "192.168.1.19"     # your laptop's LAN IP
OLLAMA_MODEL = "llava:latest"
```

### 2. Gemini (fallback backend)

- Sign in at https://aistudio.google.com with a Google account and create an
  API key (no credit card required on the free tier).
- In `python/main.py`, paste it in:
  ```
  GEMINI_KEY   = "AIzaSy...your key..."
  GEMINI_MODEL = "gemini-2.5-flash"
  ```
- Keep this key private — do not share `main.py` with the key inside it. If it
  ever leaks, delete it in AI Studio and generate a new one.

## Run

1. In App Lab, open the **Visual QA** app and press **Run**.
2. Open `http://<board-ip>:7000` in a browser on the same network.
3. The status pill turns green when at least one backend is reachable; it shows
   which one is active (local Ollama or cloud Gemini).
4. Frame a subject, optionally type a question (or tap a preset chip), and tap
   the round camera button. The answer, its latency, and the backend that
   produced it appear in the Questions & Answers panel.

## How the fallback works

- On capture, the frame is JPEG-encoded once and offered to Ollama first.
- If Ollama answers, that result is shown (tagged `Ollama`).
- If Ollama is down, times out after `OLLAMA_TIMEOUT` seconds, or returns an
  error, the same frame is sent to Gemini (tagged `Gemini`).
- If neither is available, the panel shows a clear error instead of a silent
  failure.

Tune `OLLAMA_TIMEOUT` (default 60s) to control how long the app waits on the
local model before falling back.

## Good questions for a small vision model

Reliable: scene description, what objects are present, scene type, dominant
colour, coarse counts (1–3 items), is a person visible.

Less reliable (small models may guess or hallucinate): exact counts of many
items, reading small or handwritten text, identifying specific people, precise
measurements. This is a useful teaching point — vision models describe
confidently even when wrong.

## Privacy note

- **Ollama (primary):** frames stay on your local network. Nothing is sent to
  the cloud.
- **Gemini (fallback):** captured frames are sent to Google. On the free tier,
  prompts may be used to improve Google's products. Avoid sensitive scenes when
  the cloud fallback is active, or set `USE_GEMINI = False` to stay fully local.

This local-vs-cloud trade-off (privacy, cost, reliability, latency) is the core
lesson of the lab.

## Troubleshooting

- **Pill stays red / "no backend":** Ollama isn't reachable and no Gemini key is
  set. Check that Ollama is running with `OLLAMA_HOST=0.0.0.0`, that the IP/port
  in `main.py` are correct, and that the board and laptop are on the same
  network. Test from the board's terminal:
  ```
  curl http://192.168.1.19:11434/api/tags
  ```
- **Answers cut off mid-sentence (Gemini):** raise `GEMINI_MAX_TOKENS`. The 2.5
  "thinking" models spend tokens reasoning before the visible answer.
- **`API error 429` (Gemini):** free-tier rate/quota limit. Wait ~60s, try a
  different model (e.g. `gemini-2.0-flash-lite`), or rely on Ollama as primary.
- **Slow first Ollama answer:** the model loads into memory on first use; later
  captures are faster. A laptop with more RAM/GPU helps a lot.
- **Webcam not found:** the UNO Q has a single USB-C port, so run the app in
  Network mode (not tethered/desktop) so the webcam can be attached.
