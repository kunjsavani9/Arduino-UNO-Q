#include <zephyr/kernel.h>
#include "Arduino_RouterBridge.h"

#define LM35_CH1  A0
#define LM35_CH2  A2
#define HEAT_CH1   3
#define HEAT_CH2   5

float Kp = 15.0, Ki = 0.30, Kd = 0.0;
volatile float sp1 = 45.0, sp2 = 55.0;

const float SAFETY_LIMIT = 70.0;
const int   LOOP_MS = 50;

volatile float T1 = 0, T2 = 0;
volatile int   pwm1 = 0, pwm2 = 0;
volatile bool  trip1 = false, trip2 = false;
volatile bool  led1_state = false, led2_state = false;
float int1 = 0, prev1 = 0, int2 = 0, prev2 = 0;

// Single-threaded ADC access — average of 10 readings
float readLM35(int pin) {
  long acc = 0;
  for (int i = 0; i < 10; i++) acc += analogRead(pin);
  float avg = acc / 10.0;
  return (avg * 3300.0 / 4096.0) / 10.0;   // 12-bit, 3.3V, LM35 10mV/°C
}

int pid_step(float sp, float T, float &integ, float &prev, volatile bool &trip) {
  if (T >= SAFETY_LIMIT) trip = true;
  if (trip) { integ = 0; return 0; }
  const float dt = LOOP_MS / 1000.0;
  float err = sp - T;
  integ += err * dt;
  float out = Kp*err + Ki*integ + Kd*(err - prev)/dt;
  prev = err;
  int pwm = (int)out;
  if (pwm > 255) pwm = 255;
  if (pwm < 0)   pwm = 0;
  if ((out > 255 && err > 0) || (out < 0 && err < 0)) integ -= err*dt;
  return pwm;
}

// ---- ONE control thread handling BOTH channels (priority 5) ----
K_THREAD_STACK_DEFINE(ctrl_stack, 4096);
struct k_thread ctrl_thread;
void control_loop(void*, void*, void*) {
  int dbg = 0;
  while (1) {
    float t1 = readLM35(LM35_CH1); T1 = t1;
    float t2 = readLM35(LM35_CH2); T2 = t2;

    if (t1 < 5.0) { analogWrite(HEAT_CH1, 0); pwm1 = 0; }
    else { pwm1 = pid_step(sp1, t1, int1, prev1, trip1); analogWrite(HEAT_CH1, pwm1); }

    if (t2 < 5.0) { analogWrite(HEAT_CH2, 0); pwm2 = 0; }
    else { pwm2 = pid_step(sp2, t2, int2, prev2, trip2); analogWrite(HEAT_CH2, pwm2); }

    if (++dbg >= 20) {                 // ~1 Hz debug to Serial Monitor
      dbg = 0;
      Serial.print("T1="); Serial.print(t1, 2); Serial.print(" pwm1="); Serial.print(pwm1);
      Serial.print(" | T2="); Serial.print(t2, 2); Serial.print(" pwm2="); Serial.println(pwm2);
    }
    k_msleep(LOOP_MS);
  }
}

// ---- Monitor / safety thread (priority 3, no ADC) ----
K_THREAD_STACK_DEFINE(mon_stack, 1024);
struct k_thread mon_thread;
void monitor(void*, void*, void*) {
  const float TOL = 1.0, HYST = 2.0;   // LED on within 1°C of ref; off if 2°C below
  while (1) {
    // Ch1 LED: ON when T1 reaches reference sp1
    if (!led1_state && T1 >= sp1 - TOL)  led1_state = true;
    if ( led1_state && T1 <  sp1 - HYST) led1_state = false;
    digitalWrite(LED4_R, led1_state ? LOW : HIGH);

    // Ch2 LED: ON when T2 reaches reference sp2
    if (!led2_state && T2 >= sp2 - TOL)  led2_state = true;
    if ( led2_state && T2 <  sp2 - HYST) led2_state = false;
    digitalWrite(LED3_G, led2_state ? LOW : HIGH);

    // Safety
    if (trip1 || trip2) {
      analogWrite(HEAT_CH1, 0); analogWrite(HEAT_CH2, 0);
      digitalWrite(LED3_B, LOW);  k_msleep(150);
      digitalWrite(LED3_B, HIGH); k_msleep(150);
    } else {
      digitalWrite(LED3_B, HIGH);
      k_msleep(LOOP_MS);
    }
  }
}

String set_sp1(String v){ sp1 = v.toFloat(); int1 = 0; return "OK"; }
String set_sp2(String v){ sp2 = v.toFloat(); int2 = 0; return "OK"; }
String read_all(String){
  return String(T1,2)+","+String(T2,2)+","+String(pwm1)+","+String(pwm2)+","
       + String(trip1?1:0)+","+String(trip2?1:0)+","
       + String(led1_state?1:0)+","+String(led2_state?1:0);
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  pinMode(HEAT_CH1, OUTPUT); analogWrite(HEAT_CH1, 0);
  pinMode(HEAT_CH2, OUTPUT); analogWrite(HEAT_CH2, 0);
  pinMode(LED4_R, OUTPUT); digitalWrite(LED4_R, HIGH);
  pinMode(LED3_G, OUTPUT); digitalWrite(LED3_G, HIGH);
  pinMode(LED3_B, OUTPUT); digitalWrite(LED3_B, HIGH);

  Bridge.begin();
  Bridge.provide("set_sp1", set_sp1);
  Bridge.provide("set_sp2", set_sp2);
  Bridge.provide("read_all", read_all);

  k_thread_create(&ctrl_thread, ctrl_stack, K_THREAD_STACK_SIZEOF(ctrl_stack),
                  control_loop, NULL,NULL,NULL, 5, 0, K_NO_WAIT);
  k_thread_create(&mon_thread, mon_stack, K_THREAD_STACK_SIZEOF(mon_stack),
                  monitor, NULL,NULL,NULL, 3, 0, K_NO_WAIT);

  Serial.println("Dual PID v2 - reference LEDs");   // <-- verify this in Serial Monitor
}

void loop() {}