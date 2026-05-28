/*
 * AIOT 學習輔助系統 — ESP32 告警節點韌體
 *
 * 硬體接線：
 *   紅色 LED  → GPIO 2  (分心告警)
 *   黃色 LED  → GPIO 4  (坐姿不良告警)
 *   無源蜂鳴器 → GPIO 5  (PWM，需接 100Ω 限流電阻)
 *
 * 功能：
 *   - 連上 WiFi 後每 POLL_INTERVAL_MS 向 Node A 的 /api/status 輪詢
 *   - 偵測到新的分心告警 → 紅色 LED 閃爍 3 次 + 蜂鳴器短響
 *   - 偵測到新的坐姿不良告警 → 黃色 LED 閃爍 3 次 + 蜂鳴器長響
 *   - 兩種告警同時發生 → 兩顆 LED 交替閃爍 + 蜂鳴器雙音
 *
 * 依賴函式庫（Arduino Library Manager 安裝）：
 *   - ArduinoJson  (Benoit Blanchon, v7.x)
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ── 使用者設定區 ──────────────────────────────────────────
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Node A 的 IP（樹莓派在區域網路的 IP）與 port
const char* NODE_A_IP   = "192.168.1.100";
const int   NODE_A_PORT = 9547;

// 輪詢間隔（毫秒）
const int POLL_INTERVAL_MS = 3000;
// ─────────────────────────────────────────────────────────

// GPIO 腳位
const int PIN_LED_RED    = 2;   // 分心告警 LED（紅）
const int PIN_LED_YELLOW = 4;   // 坐姿不良 LED（黃）
const int PIN_BUZZER     = 5;   // 無源蜂鳴器（PWM）

// PWM 設定
const int BUZZER_CHANNEL  = 0;
const int BUZZER_FREQ_HZ  = 2000;
const int BUZZER_RESOLUTION = 8;   // 8-bit duty cycle

// 上次告警時間戳（用來判斷是否有新告警）
String lastDistractionTs = "";
String lastPostureTs     = "";

// ── 蜂鳴器輔助函式 ────────────────────────────────────────

void buzzerOn(int freqHz) {
  ledcWriteTone(BUZZER_CHANNEL, freqHz);
}

void buzzerOff() {
  ledcWrite(BUZZER_CHANNEL, 0);
}

void beepShort() {
  // 短響 × 2（分心）
  for (int i = 0; i < 2; i++) {
    buzzerOn(2000);
    delay(100);
    buzzerOff();
    delay(80);
  }
}

void beepLong() {
  // 長響（坐姿不良）
  buzzerOn(1500);
  delay(400);
  buzzerOff();
}

void beepDouble() {
  // 雙音（兩種告警同時）
  buzzerOn(2000); delay(100); buzzerOff(); delay(60);
  buzzerOn(1500); delay(200); buzzerOff();
}

// ── LED 閃爍輔助函式 ──────────────────────────────────────

void flashLed(int pin, int times, int onMs = 150, int offMs = 100) {
  for (int i = 0; i < times; i++) {
    digitalWrite(pin, HIGH);
    delay(onMs);
    digitalWrite(pin, LOW);
    if (i < times - 1) delay(offMs);
  }
}

void flashBoth(int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(PIN_LED_RED, HIGH);
    delay(100);
    digitalWrite(PIN_LED_RED, LOW);
    digitalWrite(PIN_LED_YELLOW, HIGH);
    delay(100);
    digitalWrite(PIN_LED_YELLOW, LOW);
    delay(60);
  }
}

// ── 告警動作 ──────────────────────────────────────────────

void alertDistraction() {
  Serial.println("[ALERT] 分心告警！");
  flashLed(PIN_LED_RED, 3);
  beepShort();
}

void alertPosture() {
  Serial.println("[ALERT] 坐姿不良告警！");
  flashLed(PIN_LED_YELLOW, 3);
  beepLong();
}

void alertBoth() {
  Serial.println("[ALERT] 分心 + 坐姿不良同時告警！");
  flashBoth(3);
  beepDouble();
}

// ── WiFi 連線 ─────────────────────────────────────────────

void connectWiFi() {
  Serial.print("連線至 WiFi: ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi 連線成功！IP: " + WiFi.localIP().toString());
    // 連線成功：兩顆 LED 同時閃一下
    digitalWrite(PIN_LED_RED, HIGH);
    digitalWrite(PIN_LED_YELLOW, HIGH);
    delay(300);
    digitalWrite(PIN_LED_RED, LOW);
    digitalWrite(PIN_LED_YELLOW, LOW);
  } else {
    Serial.println("\nWiFi 連線失敗，請檢查 SSID/密碼");
    // 連線失敗：快速閃爍紅燈
    for (int i = 0; i < 6; i++) {
      digitalWrite(PIN_LED_RED, HIGH); delay(100);
      digitalWrite(PIN_LED_RED, LOW);  delay(100);
    }
  }
}

// ── 輪詢 Node A /api/status ───────────────────────────────

void pollNodeA() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi 斷線，嘗試重連...");
    connectWiFi();
    return;
  }

  String url = String("http://") + NODE_A_IP + ":" + NODE_A_PORT + "/api/status";
  HTTPClient http;
  http.begin(url);
  http.setTimeout(2000);

  int httpCode = http.GET();
  if (httpCode != 200) {
    Serial.printf("HTTP 錯誤: %d\n", httpCode);
    http.end();
    return;
  }

  String payload = http.getString();
  http.end();

  // 解析 JSON
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, payload);
  if (err) {
    Serial.println("JSON 解析失敗");
    return;
  }

  // 只在 tracking 狀態下處理告警
  const char* sysState = doc["system_state"] | "";
  if (strcmp(sysState, "tracking") != 0) return;

  // 讀取分心率與坐姿率（超過閾值才觸發）
  float distractionRatio = doc["distraction_ratio"] | 0.0f;
  bool hasPostureMetrics = !doc["posture_metrics"].isNull();
  float postureRatio = hasPostureMetrics ? (doc["posture_metrics"]["posture_ratio"] | 0.0f) : 0.0f;

  bool newDistraction = (distractionRatio > 0.4f);
  bool newPosture     = (postureRatio > 0.4f);

  if (newDistraction && newPosture) {
    alertBoth();
  } else if (newDistraction) {
    alertDistraction();
  } else if (newPosture) {
    alertPosture();
  }

  Serial.printf("[STATUS] state=%s distract=%.0f%% posture=%.0f%%\n",
    sysState, distractionRatio * 100, postureRatio * 100);
}

// ── Arduino 主程式 ────────────────────────────────────────

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n=== AIOT ESP32 告警節點啟動 ===");

  // GPIO 初始化
  pinMode(PIN_LED_RED,    OUTPUT);
  pinMode(PIN_LED_YELLOW, OUTPUT);
  digitalWrite(PIN_LED_RED,    LOW);
  digitalWrite(PIN_LED_YELLOW, LOW);

  // PWM 蜂鳴器初始化
  ledcSetup(BUZZER_CHANNEL, BUZZER_FREQ_HZ, BUZZER_RESOLUTION);
  ledcAttachPin(PIN_BUZZER, BUZZER_CHANNEL);
  buzzerOff();

  // 開機自檢：依序亮燈 + 蜂鳴
  Serial.println("自檢中...");
  digitalWrite(PIN_LED_RED, HIGH);    delay(200);
  digitalWrite(PIN_LED_RED, LOW);
  digitalWrite(PIN_LED_YELLOW, HIGH); delay(200);
  digitalWrite(PIN_LED_YELLOW, LOW);
  buzzerOn(1000); delay(100); buzzerOff();
  Serial.println("自檢完成");

  connectWiFi();
}

void loop() {
  pollNodeA();
  delay(POLL_INTERVAL_MS);
}
