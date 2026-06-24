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