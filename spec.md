# 系統規格書

專案名稱：基於邊緣視覺運算與 IoT 協同之學習專注與坐姿輔助系統  
版本：v1.2  
更新日期：2026-05-26

## 1. 專案定位

本專案目前的核心已不再是單一的「不專心偵測」或單一的「坐姿矯正」，而是以 `Combine_System` 作為 Node A 的整合式邊緣感知節點，同時處理：

- 專注度偵測
- 分心狀態判定
- 疲勞閉眼偵測
- 坐姿與頭頸姿勢分析
- Web 串流與遠端啟停控制
- 對外告警與後續 IoT 整合

系統透過單一攝影機即時估算使用者的臉部、眼部與身體姿態資訊，並將結果整理成可供提醒模組、前端儀表板與自動化流程使用的結構化狀態。

## 2. 系統架構

本系統採用「邊緣感知節點 + 選配訊息中樞 + 展示與提醒節點」的架構。現階段的核心已收斂為 `Combine_System`，其本身可獨立運作；若需擴充完整 IoT 流程，可再外接 Broker、Node B 與 Node C。

### 2.1 Node A：`Combine_System`

Node A 由 `Combine_System` 組成，負責：

- 擷取即時攝影機畫面
- 以 MediaPipe Face Landmarker 估算頭部 `pitch / yaw / roll`
- 估算眼部狀態，例如 `EAR`、眨眼、`gaze_x / gaze_y`
- 以 MediaPipe Pose 分析肩膀、耳朵與頸部相對關係
- 在啟動後執行專注區與姿勢基準線校準
- 以狀態機判斷 `idle`、`calibrating`、`tracking`
- 在 `tracking` 期間判斷 `focused`、`pending_distraction`、`distracted`、`no_face`、`fatigued`
- 評估不良姿勢，例如 `Forward Head`、`Slouching`、`Too Close`、`Lateral Tilt`
- 提供 MJPEG Web 串流與 `/start`、`/end` 控制端點
- 於長期分心或長期不良姿勢時，以非同步 HTTP GET 觸發外部告警

### 2.2 Broker：訊息中樞選配層

Broker 為選配模組，建議用於後續整合：

- 接收 Node A 正規化後的事件資料
- 分發資料給 Node B 與 Node C
- 作為 MQTT、Home Assistant、規則引擎或其他裝置的統一入口

現有 `Combine_System` 尚未內建 MQTT 發布流程，因此若要導入 Broker，需在 Node A 外再包一層事件轉接器。

### 2.3 Node B：實體提醒節點

Node B 可由 ESP32 或其他微控制器組成，負責：

- 接收來自 Node A 或 Broker 的注意力與姿勢事件
- 控制 LED、蜂鳴器、喇叭或震動模組
- 依照分心程度與姿勢嚴重度提供分級提醒

### 2.4 Node C：展示與應用節點

Node C 為 Web 或 App 展示層，負責：

- 顯示即時畫面與系統狀態
- 呈現專注區、視線落點與分心累積
- 呈現姿勢品質、姿勢異常原因與長期比例
- 提供遠端啟動、停止、歷史查詢與統計圖表

### 2.5 整體資料流

1. 使用者透過 Web 頁面或 API 觸發 `/start`。
2. Node A 進入 `calibrating`，建立專注區與姿勢基準線。
3. 校準完成後，Node A 進入 `tracking` 並持續輸出專注與姿勢狀態。
4. Node A 將結果用於本地 overlay、Web 串流與對外告警。
5. 若有外接 Broker，則由轉接層將事件送往 Node B 與 Node C。

## 3. Node A 子系統設計

`Combine_System` 為整合式視覺節點，主要模組如下。

### 3.1 `config.py`

- 定義攝影機解析度、FPS 與 Web 服務埠號
- 定義專注區與姿勢判定閾值
- 定義分心與姿勢長期統計的視窗大小與警報門檻
- 定義外部告警 URL

預設埠號為 `9547`，預設校準時間為 `10` 秒。

### 3.2 `pose.py`

- 初始化 MediaPipe Face Landmarker 與 Pose 偵測器
- 透過 OpenCV `solvePnP` 計算頭部 `pitch / yaw / roll`
- 估算眼睛開闔程度 `EAR`
- 推算視線落點 `gaze_x / gaze_y`
- 估算左右虹膜大小，用於大角度轉頭時的輔助判斷
- 回傳臉部與身體姿態資料給上層狀態機

### 3.3 `calibration.py`

- 在校準期間收集頭部姿態與眼部資料
- 根據 `pitch` 分布自動決定是否建立 1 到 2 個專注區
- 為每個專注區建立 `pitch / yaw / gaze_x / gaze_y` 邊界
- 收集姿勢基準線，包括頸部向量、肩膀高度、耳距與肩膀傾斜

### 3.4 `state_machine.py`

- 管理注意力狀態與長期分心佇列
- 管理姿勢平滑佇列與長期姿勢異常佇列
- 對短暫離開專注區、短暫閉眼與短暫姿勢偏移做緩衝
- 在累積超過門檻時觸發分心告警與姿勢告警
- 輸出統一的 `SystemEvent`

### 3.5 `models.py`

- 定義 `SystemState`
- 定義 `AttentionState`
- 定義 `HeadPose`、`EyeState`、`AttentionZone`
- 定義 `PostureMetrics` 與 `SystemEvent`

### 3.6 `app.py`

- 整合攝影機來源、視覺估算、校準、狀態機與 Web 串流
- 支援 Raspberry Pi `Picamera2`、`rpicam-vid` / `libcamera-vid` 與一般 OpenCV 攝影機
- 提供 `/`、`/stream.mjpg`、`/start`、`/end`
- 在影像上疊加專注與姿勢 overlay
- 於終端機輸出除錯資訊

## 4. 硬體規格

| 類型 | 建議規格 | 職責 |
| --- | --- | --- |
| 邊緣運算主機 | Raspberry Pi 4B / 5 或同級 Linux / Windows 主機 | 執行 `Combine_System` |
| 視覺輸入設備 | Raspberry Pi Camera 或 720p / 1080p Webcam | 提供即時影像 |
| 網路設備 | Wi-Fi / Ethernet | 提供 Web 串流、遠端控制與 IoT 整合 |
| 微控制器選配 | ESP32 或同級控制器 | 接收提醒事件並驅動實體輸出 |
| 提醒元件選配 | LED、蜂鳴器、喇叭、震動馬達 | 實作分級提醒 |

## 5. 軟體與介面規範

### 5.1 Node A 執行環境

- Python `>=3.11,<3.13`
- `mediapipe==0.10.14`
- `opencv-python`
- `numpy`
- `requests`
- `uv`

### 5.2 Node A 對外介面

- `GET /`
  - 提供 Web 監看頁面與 `Start`、`End` 控制按鈕
- `GET /stream.mjpg`
  - 提供 MJPEG 即時影像串流
- `GET /start`
  - 將系統從 `idle` 切換到 `calibrating`
- `GET /end`
  - 將系統重置回 `idle`
- 外送 HTTP GET 告警
  - 分心告警：`alert_distraction_url`
  - 姿勢告警：`alert_posture_url`

### 5.3 Node A 與外部系統整合建議

- 若要接入 Broker，建議將 `SystemEvent` 正規化為 JSON 後再透過 MQTT 發布
- 若要接入 Node C，即時畫面可直接使用 MJPEG，狀態資料則可透過 REST、WebSocket 或 MQTT 轉送
- 若要接入 Node B，可將分心與姿勢事件映射為簡化的提醒等級

## 6. 功能性需求

### FR1：整合式視覺感知

- FR1.1 系統需能從單一攝影機影像估算頭部 `pitch / yaw / roll`。
- FR1.2 系統需能估算眼部開闔程度、是否眨眼與視線座標。
- FR1.3 系統需能取得肩膀、耳朵與頸部相關姿勢特徵。
- FR1.4 系統需在邊緣端本地完成推論，不依賴雲端影像分析。

### FR2：校準與狀態管理

- FR2.1 系統啟動後預設處於 `idle`。
- FR2.2 使用者透過 `/start` 後，系統需進入 `calibrating`。
- FR2.3 系統需以預設 `10` 秒的校準流程建立專注區與姿勢基準線。
- FR2.4 系統需可自動建立 `1` 至 `2` 個專注區，以支援不同閱讀或看螢幕姿態。
- FR2.5 校準完成後，系統需進入 `tracking`。
- FR2.6 `tracking` 期間需輸出 `focused`、`pending_distraction`、`distracted`、`no_face`、`fatigued` 等注意力狀態。
- FR2.7 系統需可判定 `Forward Head`、`Slouching`、`Too Close`、`Lateral Tilt` 等姿勢異常原因。
- FR2.8 系統需對短暫分心與短暫姿勢偏移提供緩衝，避免立即誤判。
- FR2.9 使用者透過 `/end` 後，系統需立即回到 `idle` 並清空當前追蹤狀態。

### FR3：告警與自動化

- FR3.1 當長期分心累積超過門檻時，系統需觸發分心告警。
- FR3.2 當長期姿勢異常累積超過門檻時，系統需觸發姿勢告警。
- FR3.3 告警需以非同步 HTTP GET 發送，避免阻塞主迴圈。
- FR3.4 告警需具備節流機制，避免短時間內重複觸發。
- FR3.5 系統需保留將告警事件轉交 MQTT、Home Assistant 或 ESP32 的擴充能力。

### FR4：監看與前端呈現

- FR4.1 系統需提供即時監看頁面。
- FR4.2 前端需顯示目前 `system_state` 與 `attention_state`。
- FR4.3 前端需顯示 `pitch / yaw / roll`、`EAR` 與視線落點。
- FR4.4 前端需顯示已校準專注區與目前是否命中專注區。
- FR4.5 前端需顯示 `seconds_outside_zone` 與 `distraction_ratio`。
- FR4.6 前端需顯示姿勢品質、姿勢長期比例與異常原因。
- FR4.7 前端需提供遠端 `Start` / `End` 操作能力。

### FR5：事件資料模型

- FR5.1 系統內部需維持統一事件模型，以承載專注與姿勢資訊。
- FR5.2 事件內容至少需包含時間戳、系統狀態、注意力狀態、頭部姿態、眼部資訊與姿勢資訊。
- FR5.3 事件內容需包含 `matched_zone`、`seconds_outside_zone`、`distraction_ratio` 與佇列大小等長期統計欄位。
- FR5.4 事件模型需保留後續轉為 JSON、MQTT payload、CSV 或資料庫紀錄的能力。

### FR6：歷史紀錄與分析

- FR6.1 系統應支援將事件流持久化為 JSONL、CSV 或資料庫紀錄。
- FR6.2 歷史資料應同時涵蓋注意力與姿勢面向，而非只保留其中一者。
- FR6.3 歷史查詢至少應能回溯時間、狀態、姿勢摘要、分心比例與告警紀錄。

## 7. 非功能性需求

- NFR1 端到端延遲目標應低於 `500ms`。
- NFR2 系統需支援無頭執行，使用者不必外接螢幕即可操作。
- NFR3 系統需可部署於 Raspberry Pi 或一般桌機。
- NFR4 系統需以本地影像分析為主，避免將原始影像送往外部服務。
- NFR5 前端介面需支援桌機與手機瀏覽。
- NFR6 主要參數應可透過 `config.py` 調整，而不需大幅修改主程式。

## 8. 事件資料格式建議

### 8.1 即時事件 JSON

```json
{
  "timestamp": 1760000000.125,
  "system_state": "tracking",
  "attention_state": "focused",
  "matched_zone": "zone_1",
  "seconds_outside_zone": 0.0,
  "head_pose": {
    "pitch": 4.8,
    "yaw": -2.1,
    "roll": 0.5
  },
  "eye_state": {
    "ear": 0.263,
    "is_blinking": false,
    "gaze_x": 0.51,
    "gaze_y": 0.62
  },
  "posture_metrics": {
    "v_neck_angle": 6.2,
    "shoulder_drop": 0.012,
    "ear_ratio": 1.03,
    "neck_ratio": 0.97,
    "lateral_diff": 0.011,
    "is_bad_posture": false,
    "bad_posture_reasons": [],
    "posture_ratio": 0.08,
    "posture_queue_size": 54
  },
  "distraction_ratio": 0.18,
  "queue_size": 120
}
```

### 8.2 歷史資料欄位建議

| 欄位 | 說明 |
| --- | --- |
| `timestamp` | 事件時間 |
| `system_state` | 系統狀態 |
| `attention_state` | 注意力狀態 |
| `matched_zone` | 命中的專注區 |
| `seconds_outside_zone` | 已離開專注區秒數 |
| `pitch` | 頭部俯仰角 |
| `yaw` | 頭部左右角 |
| `roll` | 頭部傾斜角 |
| `ear` | 眼部開闔程度 |
| `gaze_x` | 視線水平座標 |
| `gaze_y` | 視線垂直座標 |
| `is_bad_posture` | 是否為不良姿勢 |
| `bad_posture_reasons` | 不良姿勢原因 |
| `distraction_ratio` | 長期分心比例 |
| `posture_ratio` | 長期姿勢異常比例 |

## 9. 里程碑建議

### Phase 1：`Combine_System` 穩定化

- 完成專注區與姿勢基準線校準驗證
- 確認多種攝影機來源與 Raspberry Pi 相容性
- 確認注意力與姿勢判定閾值合理

### Phase 2：事件標準化與對外輸出

- 將 `SystemEvent` 轉為穩定 JSON payload
- 補上 MQTT、REST 或 WebSocket 事件出口
- 建立與 Broker 的整合介面

### Phase 3：Node B / Node C 串接

- 將分心與姿勢狀態映射到 ESP32 提醒邏輯
- 建立儀表板顯示專注與姿勢雙軌資訊
- 支援歷史資料查詢與趨勢圖

### Phase 4：整體整合與驗證

- 驗證端到端延遲
- 驗證校準流程、告警流程與遠端控制一致性
- 規劃歷史事件儲存與自動化整合
