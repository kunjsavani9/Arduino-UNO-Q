import sys, time, threading
sys.path.insert(0, "/app")
from arduino.app_utils import App, Bridge
from arduino.app_bricks.web_ui import WebUI

web_ui = WebUI()                       # 0.0.0.0:7000, serves /app/assets/index.html

ref  = {"ref1": 45.0, "ref2": 55.0, "dirty": True}
lock = threading.Lock()

# Browser -> server: new reference temperatures
def on_set_refs(sid, data):
    if isinstance(data, dict):
        with lock:
            if "ref1" in data: ref["ref1"] = float(data["ref1"])
            if "ref2" in data: ref["ref2"] = float(data["ref2"])
            ref["dirty"] = True
    return {"ok": True}

web_ui.on_message("set_refs", on_set_refs)
web_ui.start()
print(f"==> Control page at {web_ui.url}")

start = time.time(); last_poll = 0.0

def loop():
    global last_poll
    now = time.time()
    with lock:
        push = ref["dirty"]; r1, r2 = ref["ref1"], ref["ref2"]; ref["dirty"] = False
    if push:
        Bridge.call("set_sp1", str(r1)); Bridge.call("set_sp2", str(r2))
        print(f"Setpoints -> Ref1={r1} Ref2={r2}")
    if now - last_poll >= 1.0:
        last_poll = now
        try:
            T1,T2,p1,p2,tr1,tr2,l1,l2 = Bridge.call("read_all", "").split(",")
            web_ui.send_message("telemetry", {
                "t": round(now - start, 1),
                "T1": float(T1), "T2": float(T2), "ref1": r1, "ref2": r2,
                "pwm1": int(p1), "pwm2": int(p2),
                "led1": int(l1), "led2": int(l2),
                "trip1": int(tr1), "trip2": int(tr2)})
        except Exception as e:
            print("read error:", e)
    time.sleep(0.05)

App.run(user_loop=loop)