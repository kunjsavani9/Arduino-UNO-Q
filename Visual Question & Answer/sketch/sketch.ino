/*
 * Visual QA - MCU side (STM32U5)
 * --------------------------------
 * Drives the onboard RGB LED as a status indicator for the
 * vision-language pipeline running on the Linux MPU.
 * The LED is exposed to Python through Bridge RPC (set_status).
 *
 * Onboard RGB LED channels are ACTIVE-LOW: HIGH = off, LOW = on.
 *   BLUE  -> capturing a webcam frame
 *   RED   -> model is thinking (inference in progress)
 *   GREEN -> answer is ready
 *   (all off) -> idle
 */

#include "Arduino_RouterBridge.h"

void all_off() {
  digitalWrite(LED4_R, HIGH);
  digitalWrite(LED3_G, HIGH);
  digitalWrite(LED3_B, HIGH);
}

// Called from Python via Bridge.call("set_status", state)
void set_status(String state) {
  all_off();
  if      (state == "CAPTURE") { digitalWrite(LED3_B, LOW); }  // blue
  else if (state == "THINK")   { digitalWrite(LED4_R, LOW); }  // red
  else if (state == "READY")   { digitalWrite(LED3_G, LOW); }  // green
  // "IDLE" leaves all channels off
  Serial.println("Status: " + state);
}

void setup() {
  Serial.begin(9600);
  pinMode(LED4_R, OUTPUT);
  pinMode(LED3_G, OUTPUT);
  pinMode(LED3_B, OUTPUT);
  all_off();

  Bridge.begin();
  Bridge.provide("set_status", set_status);
  Serial.println("Visual QA MCU ready");
}

void loop() {
  // Nothing to do here - the Bridge handles incoming status calls.
}
