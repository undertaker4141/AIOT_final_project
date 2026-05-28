# ESP32 接線說明

## 硬體清單

| 元件 | 數量 |
|------|------|
| ESP32 開發板 | 1 |
| 紅色 LED | 1 |
| 黃色 LED | 1 |
| 無源蜂鳴器 | 1 |
| 100Ω 電阻 | 3（每個 LED/蜂鳴器各一） |
| 麵包板 + 杜邦線 | 若干 |

## 接線圖

```
ESP32 GPIO 2  ──[100Ω]── 紅色 LED 正極 ── GND
ESP32 GPIO 4  ──[100Ω]── 黃色 LED 正極 ── GND
ESP32 GPIO 5  ──[100Ω]── 無源蜂鳴器 + 極 ── GND
ESP32 GND     ── 共地
ESP32 3.3V    ── 可選（LED 也可直接從 GPIO 供電）
```

## 燒錄步驟

1. 安裝 [Arduino IDE 2.x](https://www.arduino.cc/en/software)
2. 在 Arduino IDE → 偏好設定 → 額外開發板管理員 URL 加入：
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. 開發板管理員搜尋 `esp32`，安裝 **Espressif Systems esp32**
4. 函式庫管理員搜尋 `ArduinoJson`，安裝 **ArduinoJson by Benoit Blanchon**（v7.x）
5. 開啟 `aiot_esp32.ino`
6. 修改頂部設定：
   ```cpp
   const char* WIFI_SSID     = "你的WiFi名稱";
   const char* WIFI_PASSWORD = "你的WiFi密碼";
   const char* NODE_A_IP     = "樹莓派的區域網路IP";  // 例如 "192.168.1.100"
   ```
7. 選擇開發板：**ESP32 Dev Module**
8. 選擇正確的 COM port
9. 上傳

## 告警行為

| 情況 | 紅色 LED | 黃色 LED | 蜂鳴器 |
|------|----------|----------|--------|
| 分心率 > 40% | 閃爍 3 次 | 不亮 | 短響 × 2 |
| 不良坐姿率 > 40% | 不亮 | 閃爍 3 次 | 長響 × 1 |
| 兩者同時 | 交替閃爍 | 交替閃爍 | 雙音 |
| WiFi 連線成功 | 亮一下 | 亮一下 | — |
| WiFi 連線失敗 | 快閃 6 次 | 不亮 | — |
| 開機自檢 | 亮 0.2s | 亮 0.2s | 短響 |

## 注意事項

- 無源蜂鳴器需要 PWM 驅動，**不可用有源蜂鳴器**（有源蜂鳴器只需 HIGH/LOW，音調固定）
- GPIO 5 在部分 ESP32 板子上是 SPI CLK，若有衝突可改用 GPIO 18 或 GPIO 19
- 輪詢間隔預設 3 秒（`POLL_INTERVAL_MS = 3000`），可依需求調整
- ESP32 與樹莓派需在同一個區域網路
