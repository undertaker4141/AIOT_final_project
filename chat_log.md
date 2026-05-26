# Chat Log

本檔案用來維護本專案的重要對話紀錄、決策脈絡、文件調整與後續待辦。  
採用「新紀錄放前面」的方式追加，避免覆寫既有歷史。

## 記錄規則

- 每次重要請求或一組連續修改，新增一個 session 區塊。
- 記錄重點放在需求、決策、修改內容、驗證方式與未完成事項。
- 保持精簡，但要足夠讓後續接手的人快速理解背景。
- 若只是小幅修字，可併入最近一次尚未結案的 session。

## Session Log

### 2026-05-26 Session 004

**Request**  
將 `Combine_System/README.md` 的 Web 埠號說明修正成與實作一致。

**Key Decisions**  
- README 中所有對外使用說明都對齊 `Combine_System` 目前實作的預設埠號 `9547`。
- 只修正文檔中的埠號描述，不變更程式設定與其他行為。

**Files Updated**  
- `Combine_System/README.md`
- `chat_log.md`

**Summary of Changes**  
- 將 README 內的預設埠號由 `8000` 改為 `9547`。
- 同步更新網頁監看網址與 `/start`、`/end` 的 `curl` 範例。

**Validation**  
- 人工檢查 `Combine_System/README.md` 中所有 `8000` 相關敘述並完成對齊。
- 本次未重新執行程式；埠號依據先前 Windows 端實測結果與 `config.py` 內容同步。

**Open Follow-ups**  
- 若後續還要補齊 README，可再加入 Windows 開發端的 `uv sync --no-dev` 與測試說明。

### 2026-05-26 Session 003

**Request**  
在 Windows 開發端測試 `Combine_System` 是否正常，並依需求直接在 `Combine_System` 內重建 `uv` 環境後執行測試。

**Key Decisions**  
- 直接在 `Combine_System` 目錄重建 `.venv`，不沿用已失效的舊虛擬環境。
- 以專案內的 `.uv-cache` 避開原本使用者目錄下 `uv` cache 的權限問題。
- 先完成執行期依賴同步，再做 Windows 端 smoke test，避免被 dev 依賴阻塞。

**Files Updated**  
- `chat_log.md`

**Summary of Changes**  
- 重建 `Combine_System/.venv`，並以 Python 3.11 重新完成 `uv sync --no-dev`。
- 驗證 `cv2`、`mediapipe`、`requests` 可正常匯入，`face_landmarker.task` 可正常載入。
- 驗證 Windows 端相機可讀取，並成功輸出 `test_cam_0.jpg`。
- 啟動 `Combine_System` 後，確認 `GET /`、`GET /start`、`GET /end` 在 Windows 上可正常回應。

**Validation**  
- 執行 `.\\.venv\\Scripts\\python.exe --version`，確認為 Python `3.11.10`。
- 執行 `.\\.venv\\Scripts\\python.exe test.py`，相機索引 `0` 測試通過。
- 執行 `VisionEstimator` 初始化測試，模型載入成功。
- 啟動 `python -m combine_system.app`，實測 `http://127.0.0.1:9547/` 回傳 `200`，`/start` 與 `/end` 皆回傳 `200` 與預期內容。

**Open Follow-ups**  
- 目前 `Combine_System/README.md` 仍寫預設埠號 `8000`，但實作與測試結果實際為 `9547`，建議後續補齊文件。
- Windows 啟動時會出現 `Picamera2` fallback 與 MediaPipe / protobuf 警告，但不影響 OpenCV 攝影機模式與基本功能測試。

### 2026-05-26 Session 002

**Request**  
先理解目前專案與 repo 內的 skill，再將 `node A` 替換成整合不專心系統與坐姿矯正系統的 `Combine_System`，並依此修改 `spec.md`，同時維護 `chat_log.md`。

**Key Decisions**  
- 這次以 repo 內現有的 `Combine_System` 實作為 Node A 的真實基礎，而不再沿用舊的 `focus_system` 敘述。
- `spec.md` 改為描述整合式 Node A，將專注偵測、姿勢分析、Web 串流、`/start` `/end` 控制與 HTTP 告警都納入同一節點責任。
- 保留 Broker、Node B、Node C 作為外部整合層，但明確標註目前需要事件轉接層才能把 `Combine_System` 接到 MQTT 或其他訊息系統。

**Files Updated**  
- `spec.md`
- `chat_log.md`

**Summary of Changes**  
- 重寫 `spec.md` 的專案定位、系統架構與 Node A 子系統設計，將核心從 `focus_system` 改為 `Combine_System`。
- 更新功能需求，加入整合式專注與姿勢判定、Web 監看、遠端啟停與非同步 HTTP 告警。
- 更新事件資料格式建議，改為同時涵蓋 `attention_state` 與 `posture_metrics` 的結構。

**Validation**  
- 人工比對 `Combine_System` 的 `README.md`、`config.py`、`pose.py`、`calibration.py`、`state_machine.py`、`models.py`、`app.py` 後再回寫規格。
- 未執行程式測試；本次工作為文件更新與規格同步。

**Open Follow-ups**  
- 若後續要讓 Node B 或 Node C 直接吃即時事件，需補上 `Combine_System` 的 JSON / MQTT / WebSocket 事件輸出層。
- `Combine_System/README.md` 目前仍有部分描述與程式預設值不完全一致，例如 Web 埠號，後續可再補一次文件對齊。

### 2026-05-26 Session 001

**Request**  
理解 `spec.md` 與 `focus_system`，依照新的不專心偵測系統微調 spec、調整整體專案架構與展示內容，重點改寫 Node A，修正 Markdown 格式，並建立一個可供 Codex 與 Cloud Code 共用的 chat log 維護 skill。

**Key Decisions**  
- 專案定位從「坐姿監修」調整為「專注度/不專心偵測輔助系統」。
- Node A 改以 `focus_system` 為核心，重點資料改為 head pose、gaze、fatigue、distraction，而非頸部角度與肩膀高低差。
- Node C 儀表板內容改為顯示狀態、專注區、分心秒數、長期分心比例與事件通知。
- 在 repo 內建立 `skills/chat-log-maintainer`，方便跟著專案一起版本控管。

**Files Updated**  
- `spec.md`
- `focus_system/README.md`
- `focus_system/focus_system_analysis.md`
- `chat_log.md`
- `skills/chat-log-maintainer/SKILL.md`
- `skills/chat-log-maintainer/agents/openai.yaml`
- `skills/chat-log-maintainer/references/chat-log-format.md`

**Summary of Changes**  
- 重寫 `spec.md`，將系統需求改為以 `focus_system` 為核心的 Node A 架構。
- 更新展示層需求，從姿勢矯正圖表改為專注狀態事件與分心統計。
- 修正 `focus_system` 文件中和實作不一致的描述。
- 建立可重用的 chat log skill 與 Markdown 模板。

**Validation**  
- 人工比對 `focus_system` 的 `config.py`、`pose.py`、`calibration.py`、`state_machine.py`、`app.py` 後再回寫文件。
- 已手動檢查 `skills/chat-log-maintainer` 的 `SKILL.md` frontmatter、`agents/openai.yaml` 與 reference 結構。
- 嘗試執行官方 `quick_validate.py`，但目前環境缺少 `PyYAML`，因此未完成自動驗證。

**Open Follow-ups**  
- 若後續真的要讓 Node B / Node C 直接吃 MQTT，需再補上 broker topic、payload 與後端 API 細節。
- `focus_system` 目前尚未內建歷史資料持久化與 WebSocket/MQTT 發布，需要在外層系統補齊。
