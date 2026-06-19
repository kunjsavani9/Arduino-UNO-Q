# Dual-Channel Thermal PID Controller

Real-time, two-channel closed-loop temperature controller for the Arduino UNO Q.
Two NPN power transistors act as heaters (PWM on ~3 and ~5); an LM35 on each
transistor (A0, A2) measures temperature. A PID controller on the STM32 MCU
(Zephyr RTOS) drives each transistor to a user-defined reference and holds it.
A high-priority monitor task lights an onboard LED when a channel reaches its
reference and enforces an over-temperature safety cut-off. The Linux MPU serves
a web dashboard (WebUI-HTML brick) for entering references and watching live
temperatures.

## App Lab project layout

    Dual-Channel Thermal PID Controller
     |-> assets/
     |  |-> index.html            #web dashboard (served by the WebUI-HTML brick)
     |  |-> bitgreen-logo.png     #logo shown in the dashboard header
     |-> python/
     |  |-> main.py               #WebUI brick + Bridge orchestration (Linux MPU)
     |-> sketch/
     |  |-> sketch.ino            #dual PID + monitor/safety threads (STM32 MCU)
     |-> app.yaml                 #lists the WebUI - HTML brick

## Hardware / pin map

    LM35 sensor 1     -> A0        transistor 1 temperature
    LM35 sensor 2     -> A2        transistor 2 temperature
    Heater 1 (PWM)    -> ~3        NPN transistor 1 base drive
    Heater 2 (PWM)    -> ~5        NPN transistor 2 base drive
    Ch1 indicator     -> LED4_R    red, ON when T1 reaches reference
    Ch2 indicator     -> LED3_G    green, ON when T2 reaches reference
    Safety alarm      -> LED3_B    blue, blinks on over-temp trip
    Fan               -> barrel jack (constant cooling / disturbance)

## Setup

1. In App Lab, create a new app and rename it so the title reads
   "Dual-Channel Thermal PID Controller".
2. Add the WebUI - HTML brick: Bricks panel -> grid icon -> Add App Brick ->
   WebUI - HTML -> Add brick. (This updates app.yaml automatically.)
3. Put sketch.ino in the sketch/ folder and main.py in the python/ folder.
4. Create an assets/ folder at the app root and add index.html and
   bitgreen-logo.png to it. The logo is a binary file - drag it from your
   computer into the assets folder (do not create it with New File).
5. Creat a new file inside the assets/ index.html foe web page design

## Run

1. Save all files (Cmd+S) and click Run. App Lab compiles and flashes the MCU.
2. Open Serial Monitor; confirm the boot line "Dual PID v2 - reference LEDs"
   and the 1 Hz T1/T2 debug.
3. Open the Python tab to read the dashboard URL, then browse to
   http://<board-ip>:7000 (e.g. http://192.168.1.23:7000).
4. Enter Reference Temp 1 and Reference Temp 2 (deg C) and press Set.

## Control parameters

    PID gains          Kp = 15.0, Ki = 0.30, Kd = 0.0
    Control rate       20 Hz (LOOP_MS = 50)
    Sensor reading     average of 10 ADC samples (12-bit, 3.3 V, 10 mV/degC)
    LED threshold      ON within 1 degC of reference, 2 degC hysteresis
    Safety cut-off     62 degC per channel -> clamp heaters, blink LED3_B

Measured plant: ambient ~30 degC, max ~65 degC at full PWM, time constant
~65 s, DC gain ~0.14 degC per PWM count, cross-coupling ~3 degC.

## How it works

- sketch.ino runs two Zephyr threads: a control thread (priority 5) that reads
  both sensors and runs both PID loops at 20 Hz, and a monitor/safety thread
  (priority 3, higher) for the reference LEDs and the over-temp cut-off. The
  Bridge exposes set_sp1 / set_sp2 (set references) and read_all (telemetry).
- main.py adds the WebUI brick, pushes references to the MCU via the Bridge,
  and streams telemetry to the browser once per second over a WebSocket.
- index.html sends references with socket.emit("set_refs", ...) and updates a
  Chart.js graph from the "telemetry" messages.

(c) Bitgreen Technolabz - Edge AI Curriculum
