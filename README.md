# AIOT 學習專注與坐姿輔助系統

基於邊緣視覺運算與 IoT 協同的學習專注度與坐姿監測系統。透過單一攝影機即時分析使用者的頭部姿態、視線、眨眼與身體坐姿，並透過 WebSocket 即時推送狀態至 Web 儀表板，同時支援 ESP32 實體提醒。

---

## 系統架構

```
┌─────────────────────────────────────────────────────────┐
│  Node A — Combine_System (Raspberry Pi / 電腦)           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │ 攝影機   │→ │ MediaPipe│→ │ 狀態機   │→ │ SQLite │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘  │
│                               │                          │
│                    ┌──────────┴──────────┐               │
│                    ↓                     ↓               │
│              WebSocket :9548       HTTP REST :9547        │
│              MJPEG Stream          /api/status            │
│                                    /api/history           │
└─────────────────────────────────────────────────────────┘
         │                              │
         ↓                              ↓
┌─────────────────┐          ┌──────────────────────┐
│  Node B          │          │  Node C               │
│  ESP32 / Mock    │          │  React Dashboard      │
│  port 9549       │          │  port 5173 (dev)      │
│  LED / 蜂鳴器    │          │  即時狀態 + 歷史圖表  │
└─────────────────┘          └──────────────────────┘
```

---

## 目錄結構

```
AIOT_final_project/
├── Combine_System/          # Node A：邊緣感知節點
│   ├── pyproject.toml
│   ├── models/
│   │   └── face_landmarker.task
│   └── src/combine_system/
│       ├── app.py           # 主程式入口
│       ├── config.py        # 所有可調參數
│       ├── models.py        # 資料模型
│       ├── pose.py          # MediaPipe 視覺估算
│       ├── calibration.py   # 校準緩衝區
│       ├── state_machine.py # 注意力與姿勢狀態機
│       ├── event_bus.py     # 執行緒安全事件分發
│       ├── ws_server.py     # WebSocket 廣播伺服器
│       ├── db.py            # SQLite 持久化
│       └── api_handler.py   # REST API 端點
│
├── Node_B/                  # Node B：ESP32 提醒節點（含 mock）
│   ├── pyproject.toml
│   └── src/node_b/
│       └── server.py        # HTTP mock 伺服器
│
├── Node_C/                  # Node C：Web 儀表板
│   ├── vite.config.ts
│   └── src/
│       ├── types.ts
│       ├── hooks/           # useWebSocket, useHistory
│       ├── components/      # UI 元件
│       └── pages/           # Dashboard, History
│
├── spec.md                  # 系統規格書
└── chat_log.md              # 開發紀錄
```

---

## 快速開始

### 環境需求

| 元件 | 版本 |
|------|------|
| Python | 3.11 – 3.12 |
| Node.js | 18+ |
| uv | 最新版 |
| 攝影機 | USB Webcam 或 Raspberry Pi Camera |

### 1. Node A — 啟動邊緣感知節點

```bash
cd Combine_System

# 安裝依賴（首次）
uv sync --no-dev

# 啟動
uv run python -m combine_system.app
```

啟動後提供：
- `http://<IP>:9547/` — 監看頁面（含 Start / End 按鈕）
- `http://<IP>:9547/stream.mjpg` — MJPEG 即時串流
- `http://<IP>:9547/start` — 開始校準
- `http://<IP>:9547/end` — 停止並重置
- `http://<IP>:9547/api/status` — 最新 SystemEvent JSON
- `http://<IP>:9547/api/history` — 歷史查詢
- `ws://<IP>:9548` — WebSocket 即時事件流

### 2. Node B — 啟動提醒 Mock 伺服器

```bash
cd Node_B
python src/node_b/server.py
```

啟動後監聽 `http://localhost:9549`，接收 Node A 的告警請求：

| 端點 | 說明 |
|------|------|
| `GET /notfocus` | 分心告警（Node A 自動呼叫） |
| `GET /badposture` | 坐姿不良告警（Node A 自動呼叫） |
| `GET /test?type=distraction` | 手動觸發分心告警（測試用） |
| `GET /test?type=posture` | 手動觸發坐姿告警（測試用） |
| `GET /status` | JSON：累計次數、最後觸發時間、最近 50 筆紀錄 |
| `GET /` | 告警監看頁面（每 2 秒自動刷新，含計數器與手動觸發按鈕） |

> **Node A 預設已指向本地 Node B**，`config.py` 中：
> ```python
> alert_distraction_url: str = "http://localhost:9549/notfocus"
> alert_posture_url: str = "http://localhost:9549/badposture"
> ```
> 部署實體 ESP32 時再改回外部 URL。

### 3. Node C — 啟動 Web 儀表板

```bash
cd Node_C

# 安裝依賴（首次）
npm install

# 開發模式
npm run dev
```

開啟 `http://localhost:5173`，提供：
- **儀表板**（`/`）：即時顯示專注狀態、坐姿狀態、頭部姿態、視線追蹤、分心率、坐姿率、MJPEG 串流；校準期間顯示倒數 banner；WebSocket 斷線時顯示連線狀態提示
- **歷史紀錄**（`/history`）：日期範圍查詢、折線圖（分心率 / 不良坐姿率）、資料表格與分頁；所有欄位以中文顯示

---

## 使用流程

1. 啟動 Node B：`cd Node_B && python src/node_b/server.py`
2. 啟動 Node A：`cd Combine_System && uv run python -m combine_system.app`，等待終端機顯示 `Web streaming started on http://0.0.0.0:9547`
3. 啟動 Node C：`cd Node_C && npm run dev`，開啟 `http://localhost:5173`
4. 點擊儀表板上的 **開始** 按鈕，系統進入 10 秒校準模式（頁面顯示青色倒數 banner）
5. 校準期間保持正常坐姿與視線，讓系統建立基準線
6. 校準完成後進入 **追蹤中** 模式，儀表板即時更新
7. 分心或坐姿不良持續超過閾值時，Node A 自動發送告警至 Node B（可在 `http://localhost:9549/` 看到計數器增加）
8. 點擊 **結束** 重置系統

> **測試 Node B 告警**：直接在瀏覽器點擊 `http://localhost:9549/` 的「手動觸發」按鈕，或執行：
> ```bash
> curl http://localhost:9549/test?type=distraction
> curl http://localhost:9549/test?type=posture
> ```

---

## 系統狀態說明

### 系統狀態（System State）

| 狀態 | 說明 |
|------|------|
| `idle` | 等待啟動 |
| `calibrating` | 10 秒校準中 |
| `tracking` | 即時追蹤中 |

### 注意力狀態（Attention State）

| 狀態 | 說明 |
|------|------|
| `focused` | 專注（視線在專注區內） |
| `pending_distraction` | 短暫離開專注區（緩衝中） |
| `distracted` | 持續分心超過閾值 |
| `no_face` | 偵測不到臉部 |
| `fatigued` | 閉眼超過 2 秒（疲勞） |

### 姿勢異常原因（Bad Posture Reasons）

| 原因 | 說明 |
|------|------|
| `Forward Head` | 頭部前傾角度過大 |
| `Slouching` | 肩膀下沉或頸部縮短 |
| `Too Close` | 距離螢幕過近 |
| `Lateral Tilt` | 頭部或肩膀側傾 |

---

## 設定參數

所有參數集中在 `Combine_System/src/combine_system/config.py`：

```python
# 攝影機
camera_index: int = 0          # 攝影機索引
frame_width: int = 640
frame_height: int = 480
fps_limit: float = 30.0
web_port: int = 9547           # HTTP 服務埠
ws_port: int = 9548            # WebSocket 埠
db_path: str = "events.db"    # SQLite 資料庫路徑

# 告警 URL（預設指向本地 Node B mock，部署實體 ESP32 時改回外部 URL）
alert_distraction_url: str = "http://localhost:9549/notfocus"
alert_posture_url: str = "http://localhost:9549/badposture"

# 校準
calibration_seconds: float = 10.0

# 分心判定
absence_threshold_seconds: float = 8.0    # 離開專注區幾秒後判定分心
fatigue_closed_eyes_seconds: float = 2.0  # 閉眼幾秒後判定疲勞
long_term_distraction_threshold: int = 80 # 200 幀中超過 80 幀分心則告警

# 姿勢判定
posture_forward_head_angle: float = 12.0  # 頭部前傾角度閾值（度）
posture_slouch_shoulder_drop: float = 0.035
posture_too_close_ear_ratio: float = 1.15
posture_lateral_tilt_diff: float = 0.04
```

---

## REST API 參考

### `GET /api/status`

回傳最新一筆 SystemEvent JSON。

```json
{
  "timestamp": 1760000000.125,
  "system_state": "tracking",
  "attention_state": "focused",
  "matched_zone": "zone_1",
  "seconds_outside_zone": 0.0,
  "distraction_ratio": 0.18,
  "queue_size": 120,
  "head_pose": { "pitch": 4.8, "yaw": -2.1, "roll": 0.5 },
  "eye_state": { "ear": 0.263, "is_blinking": false, "gaze_x": 0.51, "gaze_y": 0.62 },
  "posture_metrics": {
    "v_neck_angle": 6.2,
    "is_bad_posture": false,
    "bad_posture_reasons": [],
    "posture_ratio": 0.08
  }
}
```

### `GET /api/history`

查詢歷史紀錄。

| 參數 | 說明 | 預設 |
|------|------|------|
| `start` | 起始 Unix timestamp | 無 |
| `end` | 結束 Unix timestamp | 無 |
| `limit` | 最多回傳筆數 | 100 |
| `offset` | 分頁偏移 | 0 |

```bash
curl "http://localhost:9547/api/history?limit=50&start=1760000000"
```

---

## 部署到 Raspberry Pi

```bash
# 在 Pi 上
git clone <repo>
cd AIOT_final_project/Combine_System
uv sync --no-dev
uv run python -m combine_system.app
```

Pi Camera 會自動偵測（優先使用 `Picamera2`，fallback 到 `rpicam-vid`）。

若使用 USB Webcam，設定 `camera_index = 0`（預設）。

---

## ESP32 實體接線（Node B）

ESP32 需訂閱 Node A 的告警 HTTP GET：

| 告警類型 | URL |
|----------|-----|
| 分心 | `GET http://<NodeA_IP>:9549/notfocus` |
| 坐姿不良 | `GET http://<NodeA_IP>:9549/badposture` |

部署時將 `config.py` 的 alert URL 改為 ESP32 實際 IP 或外部服務 URL：

```python
alert_distraction_url: str = "http://<ESP32_IP>/notfocus"
alert_posture_url: str = "http://<ESP32_IP>/badposture"
```

建議 ESP32 韌體邏輯：
- 收到 `distraction` → 紅色 LED 閃爍 + 蜂鳴器短響
- 收到 `posture` → 黃色 LED 閃爍 + 震動馬達

---

## 技術棧

| 層 | 技術 |
|----|------|
| 視覺推論 | MediaPipe Face Landmarker + Pose |
| 頭部姿態 | OpenCV `solvePnP` |
| 後端 | Python 3.11, `ThreadingHTTPServer`, `websockets`, `sqlite3` |
| 前端 | React 18, TypeScript, Tailwind CSS, Vite, recharts |
| 套件管理 | `uv`（Python）, `npm`（Node.js） |

---

## Windows 開發注意事項

- **Node B 需用系統 Python 啟動**（`python src/node_b/server.py`），不需 `uv`。
- **每次修改程式後需手動重啟對應 node**，確認舊 process 已終止再啟動新版。
- **確認 port 未被佔用**：若啟動失敗，執行 `netstat -ano | findstr "9547 9548 9549 5173"` 確認是否有殘留 process。
- Node B 的 console 輸出需在支援 ANSI 色彩的終端機（Windows Terminal / VS Code Terminal）才能正確顯示彩色警報。
