/*
  esp32_example.ino
  Example ESP32 sketch to POST sensor readings to Flask backend.
  Replace HOST_IP with your machine's IP (e.g., 192.168.1.100)

  Notes:
  - Uses DHT library (DHT.h) for DHT11
  - Uses HTTPClient to POST JSON
  - Ultrasonic uses trigger/echo pins and pulseIn
  - Tipping-bucket is simulated here with a counter increment (adjust as needed)
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include "DHT.h"

#define DHTPIN 4
#define DHTTYPE DHT11
#define SOIL_PIN 13
#define TRIG_PIN 14
#define ECHO_PIN 12

// Replace with your WiFi credentials
const char* ssid = "YOUR_SSID";
const char* password = "YOUR_PASSWORD";

// Replace with your host IP and Flask port
const char* HOST_IP = "<HOST_IP>"; // e.g. 192.168.1.100
const int HOST_PORT = 5000;

DHT dht(DHTPIN, DHTTYPE);

volatile unsigned long tipCount = 0; // tipping-bucket counts

void IRAM_ATTR onTip(){
  tipCount++;
}

float readUltrasonic(){
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duration = pulseIn(ECHO_PIN, HIGH, 30000); // timeout 30ms
  if(duration==0) return 999.0;
  float distance = (duration / 2.0) / 29.1; // cm
  return distance;
}

// Convert tipping-bucket counts to mm/hr
float countsToMmPerHour(unsigned long counts, unsigned long intervalMs){
  // User should set calibrations according to their bucket (e.g., 0.2 mm per tip)
  const float mmPerTip = 0.2; // adjust
  float tipsPerHour = (counts * 3600000.0) / (float)intervalMs;
  return tipsPerHour * mmPerTip;
}

void setup(){
  Serial.begin(115200);
  pinMode(SOIL_PIN, INPUT_PULLUP);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  // Attach tipping-bucket pin if using real sensor
  // pinMode(TIP_PIN, INPUT_PULLUP);
  // attachInterrupt(digitalPinToInterrupt(TIP_PIN), onTip, FALLING);

  dht.begin();

  WiFi.begin(ssid, password);
  Serial.print("Connecting WiFi");
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print('.');
    if(millis() - start > 20000) break;
  }
  Serial.println();
  Serial.print("WiFi connected. IP: "); Serial.println(WiFi.localIP());
}

void loop(){
  static unsigned long lastPost = 0;
  static unsigned long lastTipSnapshot = 0;
  const unsigned long interval = 3000; // 3s

  if(millis() - lastPost < interval) return;
  lastPost = millis();

  // Read sensors
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();
  int soil = digitalRead(SOIL_PIN) == LOW ? 1 : 0; // adjust if inverted
  float ultrasonic = readUltrasonic();

  // Tipping bucket: read snapshot then reset counter for next window
  unsigned long currentTips = tipCount;
  tipCount = 0; // reset for next interval
  unsigned long intervalMs = interval;
  float rainfall = countsToMmPerHour(currentTips, intervalMs);

  // Build JSON
  String payload = "{";
  payload += "\"temperature\":" + String(temperature,2) + ",";
  payload += "\"humidity\":" + String(humidity,2) + ",";
  payload += "\"rainfall\":" + String(rainfall,2) + ",";
  payload += "\"soil\":" + String(soil) + ",";
  payload += "\"ultrasonic\":" + String(ultrasonic,2);
  payload += "}";

  if(WiFi.status() == WL_CONNECTED){
    HTTPClient http;
    String url = String("http://") + HOST_IP + ":" + String(HOST_PORT) + "/update";
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    int code = http.POST(payload);
    if(code>0){
      String resp = http.getString();
      Serial.printf("POST %s -> %d\n", url.c_str(), code);
      Serial.println(resp);
    } else {
      Serial.printf("POST failed, error: %s\n", http.errorToString(code).c_str());
    }
    http.end();
  } else {
    Serial.println("WiFi not connected, skipping POST");
  }
}
