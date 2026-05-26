# MakeNTU 2026 Edge Model - 整合視覺監控系統 (Combine System)

這是一個專為樹莓派 (Raspberry Pi) 優化的邊緣運算專案，整合了**專注度偵測**（視線追蹤、疲勞眨眼）與**不良姿勢分析**（駝背、低頭、側傾等），並提供 Web 串流介面與遠端控制 API。

## 🌟 核心功能

1. **雙軌 AI 辨識**：
   - **專注度偵測**：利用 MediaPipe Face Landmarker 追蹤視線區域、頭部角度與眨眼頻率，判斷使用者是否專心或疲勞。
   - **姿勢分析**：利用 MediaPipe Pose 偵測肩膀與耳朵位置，判斷是否有低頭、駝背、側傾或距離螢幕過近等不良姿勢。
2. **無頭 (Headless) Web 串流與控制**：
   - 內建輕量化 MJPEG 伺服器，不需外接螢幕即可透過網頁（預設埠號 `9547`）監看畫面。
   - 提供 `GET /start` 與 `GET /end` 控制端點。
3. **10 秒快速校準**：
   - 收到 `/start` 指令後，系統會自動進行 10 秒的視覺與姿勢基準線校準。
4. **異步 HTTP GET 警報**：
   - 當不良姿勢或分心時間累積超過設定值（進度條滿），系統會自動向設定好的外部伺服器發送 GET 訊號。
   - **防呆機制**：同一個 API 在 2 分鐘內不會重複發送，避免洗板。
5. **樹莓派硬體優化**：
   - 針對新版樹莓派 OS 的相機驅動進行優化，採用 `rpicam-vid` / `libcamera-vid` 子行程擷取畫面，完美避開 Python 版本與 C-extension 的衝突。

## 🛠️ 環境需求

- 樹莓派 4B / 5 (建議) 或其他支援新版 `libcamera` 的 Linux 系統。
- 已安裝 `uv`（強烈建議用於管理虛擬環境）。
- 攝影機模組（支援 Raspberry Pi Camera 模組）。

## 🚀 快速開始

### 1. 安裝與同步環境

在專案目錄下執行：

```bash
uv sync
```

若提示缺少 `requests` 套件，請執行：

```bash
uv add requests
```

### 2. 設定 API 網址

打開 `src/combine_system/config.py`，您可以修改 Web 服務的埠號（預設為 `9547`），以及設定當進度條滿時要觸發的外部 API 網址：

```python
    # 預設範例
    alert_distraction_url: str = "https://controller.nchuit.com/notfocus"
    alert_posture_url: str = "https://controller.nchuit.com/badposture"
```

### 3. 執行系統

在樹莓派終端機執行：

```bash
uv run combine-system
```

系統啟動後會處於 `IDLE` 狀態，終端機會顯示 `Waiting for /start ...`。

## 🌐 Web 介面與 API 使用

### 網頁監看
打開同區網內電腦的瀏覽器，輸入：
`http://<樹莓派IP>:9547/`

### 遠端控制 API
您可以使用網頁上的按鈕，或是直接透過 `curl` / 瀏覽器呼叫以下端點：

- **開始系統（含自動校準）**：
  ```bash
  curl http://<樹莓派IP>:9547/start
  ```
- **結束系統（回到待機狀態）**：
  ```bash
  curl http://<樹莓派IP>:9547/end
  ```

## 📊 終端機 Debug 輸出

在執行時，終端機每秒會輸出一次當前狀態：
- **校準時**：`[CALIB] Calibrating... 9s remaining`
- **追蹤時**：`[TRACK] Focus: Focused | DistractRate: 5% | Posture: OK | PostureRate: 0%`
