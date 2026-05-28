# Chat Log

本檔案用來維護本專案的重要對話紀錄、決策脈絡、文件調整與後續待辦。  
採用「新紀錄放前面」的方式追加，避免覆寫既有歷史。

## 記錄規則

- 每次重要請求或一組連續修改，新增一個 session 區塊。
- 記錄重點放在需求、決策、修改內容、驗證方式與未完成事項。
- 保持精簡，但要足夠讓後續接手的人快速理解背景。
- 若只是小幅修字，可併入最近一次尚未結案的 session。

## Session Log

### 2026-05-28 Session 015

**Request**  
Node C 動態配置 Node A IP，方便樹莓派 IP 變動時不需改程式碼。

**Key Decisions**
- 採用 Vite 環境變數（`.env` 檔）方案：改 IP 只需修改 `.env` 重啟 dev server，不需動程式碼。
- `vite.config.ts` 改用 `defineConfig(({ mode }) => {...})` 函式形式，以 `loadEnv()` 讀取 `.env`，動態組合 proxy 目標。
- `.env` 加入 `.gitignore`（含 IP 資訊不外流）；`.env.example` 保留版控作為範本。

**Files Updated**
- `Node_C/.env` — 新建，預設 `VITE_NODE_A_HOST=localhost`（本機開發用）
- `Node_C/.env.example` — 新建，範本說明（版控）
- `Node_C/vite.config.ts` — 改為函式形式，讀取 env 動態設定 proxy 目標
- `.gitignore` — 新增 `Node_C/.env` 與 `Node_C/.env.local` 排除規則

**Usage**  
樹莓派部署時，修改 `Node_C/.env`：
```
VITE_NODE_A_HOST=192.168.x.x
```
重啟 `npm run dev` 即生效，所有 proxy（`/api`、`/start`、`/end`、`/stream.mjpg`、`/ws`）自動指向新 IP。

**Validation**
- `npm run build` 通過，0 TypeScript 錯誤，594 modules。

**Open Follow-ups**
- 無。

### 2026-05-28 Session 014

**Request**  
進入下一階段：確認 Node A 是否可直接上樹莓派（若不行則微調），並撰寫 ESP32 韌體（兩顆 LED + 無源蜂鳴器）。

**Key Decisions**

**Node A — 樹莓派相容性評估**
- 相機偵測邏輯已有三層 fallback（Picamera2 → OpenCV VideoCapture → RPiStreamCamera subprocess），架構上已支援樹莓派。
- 發現兩個問題需修正：
  1. `pyproject.toml` 的 `requires-python = ">=3.11,<3.13"` 過於嚴格，Pi OS Bookworm 預裝 3.11 沒問題，但未來版本可能更高，改為 `>=3.11`。
  2. Linux 上 USB 鏡頭原本直接走 `RPiStreamCamera`（subprocess rpicam-vid），但 USB 鏡頭應走 `cv2.VideoCapture`。修正為：先嘗試 `cv2.VideoCapture`，`isOpened()` 失敗才 fallback 到 `RPiStreamCamera`（CSI 鏡頭用）。
- 結論：**直接上樹莓派，不需另建版本**，兩個小修正後即可。

**Node B — ESP32 韌體設計**
- 採用 HTTP 輪詢 `/api/status`（每 3 秒），不需 WebSocket，降低韌體複雜度。
- 判斷邏輯：`distraction_ratio > 0.4` 觸發分心告警；`posture_ratio > 0.4` 觸發坐姿告警；兩者同時觸發雙重告警。
- 告警行為：分心 → 紅色 LED 閃 3 次 + 短響 × 2；坐姿 → 黃色 LED 閃 3 次 + 長響；同時 → 交替閃爍 + 雙音。
- 無源蜂鳴器用 PWM 驅動（`ledcSetup`），分心 2000Hz、坐姿 1500Hz，音調不同方便區分。
- 加入開機自檢（依序亮燈 + 短響）與 WiFi 連線狀態指示（成功/失敗各有不同 LED 行為）。

**Files Updated**
- `Combine_System/pyproject.toml` — `requires-python` 放寬為 `>=3.11`
- `Combine_System/src/combine_system/app.py` — Linux 上 USB 鏡頭優先走 `cv2.VideoCapture`，失敗才 fallback RPiStreamCamera
- `Node_B/esp32/aiot_esp32.ino` — 新建 ESP32 Arduino 韌體
- `Node_B/esp32/README.md` — 新建接線說明、燒錄步驟、告警行為表

**Validation**
- `ast.parse()` 語法檢查：app.py 通過。
- ESP32 韌體需在實體硬體上燒錄驗證。

**Open Follow-ups**
- 燒錄前需修改 `aiot_esp32.ino` 頂部的 `WIFI_SSID`、`WIFI_PASSWORD`、`NODE_A_IP`。
- GPIO 5 在部分 ESP32 板子上是 SPI CLK，若有衝突可改用 GPIO 18 或 GPIO 19。
- 樹莓派部署：`uv sync --no-dev` 後 `uv run python -m combine_system.app`，建議後續加 systemd service。



### 2026-05-27 Session 013

**Request**  
建立 `.gitignore`，排除不需要推到 git 的檔案，並清理已被 tracked 的產生物。

**Key Decisions**  
- 根目錄新建 `.gitignore`，涵蓋 Python、Node.js、執行期資料、OS/編輯器產物。
- 對已被 tracked 的產生物執行 `git rm --cached`，讓 `.gitignore` 規則生效（本地檔案保留）。
- `uv.lock` 保留版控（確保跨機器依賴一致）；`models/face_landmarker.task` 保留（模型檔需隨 repo 分發）。

**Files Updated**  
- `.gitignore` — 新建

**Removed from git index (git rm --cached)**  
- `Combine_System/src/combine_system/__pycache__/` — Python bytecode（12 個 .pyc）
- `Combine_System/src/combine_system.egg-info/` — pip 安裝產物（5 個檔案）
- `Combine_System/events.db` — SQLite 執行期資料庫
- `Combine_System/.tmp_app_stdout.log` / `.tmp_app_stderr.log` — 暫存 log
- `Combine_System/test_cam_0.jpg` — 測試用影像

**Validation**  
- `git ls-files --others --exclude-standard` 只剩 `.gitignore` 本身，無其他漏網檔案。
- `git status` 確認所有產生物已標記為 `D`（待從 index 移除）。

**Open Follow-ups**  
- 下次 commit 時記得把 `.gitignore` 一起加入（`git add .gitignore`）。
- 下一階段：Node A 部署到 Raspberry Pi（systemd service）。



### 2026-05-27 Session 012

**Request**  
根據目前修復完後的狀況更新 README.md。

**Key Decisions**  
- 對齊所有已修復的實際行為，不保留過時描述。

**Files Updated**  
- `README.md`

**Summary of Changes**  
- Node B 端點表格：新增 `/test?type=distraction`、`/test?type=posture`；`/status` 說明更新為新結構（含 counts、last_alert）；自動刷新從 5 秒改為 2 秒。
- `config.py` 範例中 alert URL 改為 `http://localhost:9549/...`（預設已指向本地 Node B）。
- Node C 說明改為中文 UI 描述，加入校準 banner 與連線狀態提示說明。
- 使用流程：改為三節點依序啟動（Node B → Node A → Node C）；加入 Node B 測試方式說明；按鈕文字改為「開始」/「結束」。
- ESP32 接線：修正告警 URL（舊版誤寫為 9547，正確為 Node B 的 9549）；加入 `config.py` 修改範例。
- 技術棧：`http.server` 改為 `ThreadingHTTPServer`（串流修復後的實際實作）。
- 新增「Windows 開發注意事項」區塊：重啟提醒、port 衝突排查、ANSI 色彩終端需求。

**Validation**  
- 人工比對 README 與目前各檔案實際內容，確認一致。

**Open Follow-ups**  
- 下一階段：Node A 部署到 Raspberry Pi（systemd service）。



### 2026-05-27 Session 011

**Request**  
Node B 無法使用（瀏覽器顯示 ERR_CONNECTION_REFUSED），進行 debug QA。

**Root Cause Analysis**  
1. **舊版 process 殘留**：Node B 跑的是修改前的舊版 `server.py`（英文 HTML），因為從未重啟。
2. **雙重 process 衝突**：port 9549 同時有兩個 Python process 在 LISTENING（PID 34360、45260），Windows `SO_REUSEADDR` 允許 bind 但請求隨機分配，造成行為不穩定。
3. **`UnicodeEncodeError: 'gbk'`（主要 bug）**：`_log_alert()` 的 `print()` 含有 Unicode emoji `⚠`（`⚠`），Windows terminal 預設 GBK 編碼無法編碼此字元，handler 拋出例外後連線被強制關閉，導致所有告警端點（`/notfocus`、`/badposture`、`/test`）全部回傳連線中斷。

**Fixes Applied**  
- `Node_B/src/node_b/server.py`：
  - 頂部加入 `io.TextIOWrapper` 強制 stdout/stderr 為 UTF-8（`errors='replace'` 防止後續任何 Unicode 字元造成 crash）
  - 移除 `print()` 中的 `⚠` emoji，改為純 ASCII `!!`
  - 移除 HTML 按鈕中的 `🔴`/`🟡` emoji（f-string 在 GBK terminal 同樣危險）
  - 新增 `import io, sys`

**Process Cleanup**  
- 手動 kill 舊版 PID 34360、45260，確保 port 9549 只有一個 process。

**Validation**  
- `GET /test?type=distraction` → 200，回傳「[測試] 已手動觸發：分心警報」
- `GET /test?type=posture` → 200，回傳「[測試] 已手動觸發：坐姿不良警報」
- `GET /status` → 200，JSON 含 `counts: {distraction:1, posture:1}` 與 `last_alert` 時間戳
- `GET /` → 200，HTML 含中文標題「Node B — 警報監控」

**Open Follow-ups**  
- 每次修改 Node B 後需手動重啟（`python src/node_b/server.py`），建議後續加入啟動腳本統一管理三個 node。
- 下一階段：Node A 部署到 Raspberry Pi（systemd service）。



### 2026-05-27 Session 010

**Request**  
Node B 難以確認是否正常運作，改成更明顯的 mock 方式方便測試。

**Key Decisions**  
- `config.py` 的 `alert_distraction_url` / `alert_posture_url` 從外部 URL 改指向本地 `http://localhost:9549/notfocus` 與 `http://localhost:9549/badposture`，讓 Node A 的告警直接打到 Node B，串接可即時驗證。
- Node B 新增 `/test?type=distraction` 與 `/test?type=posture` 端點，可在瀏覽器直接點擊手動觸發，不需等 Node A 真的觸發告警。
- 首頁加入兩個大型計數器（分心 / 坐姿不良各一），顯示累計次數與最後觸發時間，一眼就能確認是否有收到告警。
- console 輸出改為大框線 + BOLD 彩色 + terminal bell，告警發生時視覺聽覺都明顯。
- `/status` 端點回傳結構改為 `{counts, last_alert, log}`，方便程式化查詢。
- 頁面自動刷新從 5 秒縮短為 2 秒，計數器幾乎即時更新。

**Files Updated**  
- `Combine_System/src/combine_system/config.py` — alert URL 改指向本地 Node B
- `Node_B/src/node_b/server.py` — 全面強化：計數器、大字 banner、`/test` 端點、2 秒自動刷新、terminal bell、`/status` 結構化回應

**Validation**  
- `ast.parse()` 語法檢查通過。
- 測試流程：啟動 Node B → 瀏覽器開啟 `http://localhost:9549/` → 點擊「手動觸發：分心」→ 計數器 +1，console 出現大框線警報，即可確認 Node B 正常。
- Node A 啟動後觸發告警時，同樣會在 Node B 頁面看到計數增加。

**Open Follow-ups**  
- 實體 ESP32 部署時，將 `config.py` 的 alert URL 改回外部 URL 或 ESP32 IP。
- 下一階段：Node A 部署到 Raspberry Pi（systemd service）。



### 2026-05-27 Session 009

**Request**  
將前端頁面（Node C）與後端警報伺服器（Node B）所有顯示文字改為中文，方便閱讀。

**Key Decisions**  
- 狀態值（`idle`、`focused` 等）為後端 enum 的英文 key，不修改資料層，改在前端建立對照表（`STATE_LABELS`、`ATTENTION_ZH`、`REASON_ZH`）做顯示轉換，保持資料與顯示分離。
- 坐姿問題原因（`Forward Head`、`Slouching` 等）同樣在 `PosturePanel` 建立 `REASON_ZH` 對照表，`translateReasons()` 函式負責轉換。
- Node B 的 `_TYPE_ZH` 對照表讓 HTML 頁面顯示中文警報類型，console 輸出也改為中文標籤。
- 時間格式統一改為 `toLocaleTimeString('zh-TW')`。

**Files Updated**  
- `Node_C/src/components/StatusBadge.tsx` — 加入 `STATE_LABELS` 對照表，badge 顯示中文
- `Node_C/src/components/GazeTracker.tsx` — 標題「視線追蹤」
- `Node_C/src/components/AttentionPanel.tsx` — 所有標籤中文化（俯仰角、偏航角、翻滾角、眼睛開合度、離開專注區時間、對應區域、佇列大小、分心率）
- `Node_C/src/components/PosturePanel.tsx` — 標籤中文化 + `REASON_ZH` 坐姿原因對照表
- `Node_C/src/components/VideoStream.tsx` — 「串流無法連線」、「重試」
- `Node_C/src/components/ControlButtons.tsx` — 「開始」、「結束」、「啟動中…」、「停止中…」、錯誤訊息中文化
- `Node_C/src/pages/Dashboard.tsx` — 頁首、連線狀態、校準 banner、最後更新時間全部中文化
- `Node_C/src/pages/History.tsx` — 篩選條件、圖表標題、表格欄位、分頁按鈕、空資料提示全部中文化；加入 `ATTENTION_ZH` 對照表
- `Node_B/src/node_b/server.py` — HTML 頁面標題、表格欄位、console 輸出改為中文；加入 `_TYPE_ZH` 對照表

**Validation**  
- `npm run build` 0 TypeScript 錯誤，594 modules，build 通過。

**Open Follow-ups**  
- 下一階段：Node A 部署到 Raspberry Pi（systemd service）。



### 2026-05-27 Session 008

**Request**  
修正 Combine_System 串流卡住的 bug：不切換視窗刷新就會卡死，導致系統當機。

**Key Decisions**  
- 根本原因：`HTTPServer` 是單執行緒，`/stream.mjpg` 的無限迴圈永遠佔用唯一的 handler 執行緒，所有其他請求（`/start`、`/end`、`/api/status`）全部被阻塞，直到串流連線中斷才解除。
- 修法一：`HTTPServer` → `ThreadingHTTPServer`，每個連線各自在獨立執行緒中處理，串流不再鎖死整個 server。
- 修法二：移除 `time.sleep(0.05)` polling，改用 `threading.Condition`（`_cond`）：`update_frame()` 每次寫入新 frame 後呼叫 `notify_all()`，streaming handler 以 `wait(timeout=2.0)` 阻塞等待，有新 frame 才推送，無 frame 時不佔 CPU，timeout 防止永久 hang。
- 同時移除舊的 `lock = threading.Lock()`，統一由 `_cond`（內建 lock）保護 `frame_bytes`。

**Files Updated**  
- `Combine_System/src/combine_system/app.py` — `HTTPServer` → `ThreadingHTTPServer`；`lock` → `_cond`；streaming loop 改用 `_cond.wait()`；`update_frame` 改用 `_cond.notify_all()`

**Summary of Changes**  
- 串流連線現在在獨立執行緒中運行，不再阻塞 `/start`、`/end`、`/api/status` 等端點。
- 串流推送改為事件驅動（Condition），不再每 50ms 輪詢，CPU 使用率降低，延遲更低。
- 新 USB 鏡頭（樹莓派）接入後此修正同樣有效，不依賴鏡頭品質。

**Validation**  
- `ast.parse()` 語法檢查通過。
- 邏輯驗證：`ThreadingHTTPServer` 為 Python stdlib 標準類別，`threading.Condition.notify_all()` / `wait()` 為標準同步原語，無外部依賴。
- 完整端到端驗證需在有攝影機的環境執行（Windows 開發端或樹莓派）。

**Open Follow-ups**  
- 建議在樹莓派 + USB 鏡頭環境實測串流穩定性。
- 下一階段：Node A 部署到 Raspberry Pi（systemd service）。



### 2026-05-27 Session 007

**Request**  
對整個系統進行深度 QA（系統層 + UI 層），要求在 Windows 開發端 demo 全部功能無誤後再進入下一階段（樹莓派 / 實體 ESP32 / 生產部署）。本次聚焦於修復所有已知 bug，確保三節點串接可正常運作。

**Key Decisions**  
- 修復優先順序：先修 Node A 的 MJPEG 協定錯誤（影響影像串流）與事件缺失（IDLE/CALIBRATING 無事件導致儀表板空白），再修 WebSocket 啟動競爭，最後修 Node C UI 邏輯問題。
- WS 啟動競爭改用 `threading.Event(_loop_ready)` 同步：asyncio thread 啟動後設 `_loop_ready.set()`，`start()` 函式以 `_loop_ready.wait()` 阻塞直到 server ready 才啟動 bridge thread，徹底消除啟動期間事件遺失。
- ControlButtons 加入 `systemState` prop，calibrating/tracking 時禁用 Start 按鈕，並顯示 fetch 失敗的紅色錯誤訊息。
- Dashboard 加入「Connecting…」黃色 banner 與「Calibrating…」倒數計時青色 banner，秒數來自 CALIBRATING 事件的 `seconds_outside_zone` 欄位。
- History 圖表 X 軸改為固定最多 8 個標籤（`interval = floor(len/8)`），避免大量資料點時標籤重疊。

**Files Updated**  
- `Combine_System/src/combine_system/ws_server.py` — 加入 `_loop_ready` Event，修正啟動競爭
- `Node_C/src/components/ControlButtons.tsx` — state-aware 禁用、loading 文字、fetch 錯誤顯示
- `Node_C/src/pages/Dashboard.tsx` — 傳遞 systemState 給 ControlButtons、加入 Connecting/Calibrating banner
- `Node_C/src/pages/History.tsx` — X 軸 interval 動態計算，最多 8 標籤

**Summary of Changes**  
- Node A app.py（前次 session）已修正 MJPEG raw bytes、IDLE heartbeat、CALIBRATING progress event。
- ws_server.py 修正 bridge 在 loop 尚未就緒前就開始發送事件的競爭問題。
- Node C Dashboard 在三種系統狀態（connecting / calibrating / tracking）下都有明確的視覺反饋。
- ControlButtons 防止在已啟動時重複點擊 Start，並顯示錯誤訊息。

**Validation**  
- `npm run build` 0 TypeScript 錯誤，594 modules，build 通過。
- `curl http://localhost:9549/status` → 回傳 JSON 告警記錄（Node B 運作中）。
- `curl http://localhost:9547/api/status` → 回傳完整 TRACKING 事件 JSON，包含 head_pose、eye_state、posture_metrics。
- Node A 實際以攝影機運行，`/api/status` 顯示 `tracking` + `focused`，確認事件流正常。

**Open Follow-ups**  
- 下一階段：Node A 部署到 Raspberry Pi（systemd service）
- 下一階段：實體 ESP32 韌體（訂閱 `/notfocus`、`/badposture` URL）
- 下一階段：Node C 生產部署（`npm run build` + nginx 或 serve dist/）
- Node C chunk size 超過 500KB（recharts），可後續用 dynamic import 拆分（非阻塞性問題）



### 2026-05-27 Session 006

**Request**  
對現有整個系統進行詳細測試，確保功能完整性，撰寫 README.md，並規劃下一步（Node A 上樹莓派、實體 ESP32、電腦端網頁顯示）。

**Key Decisions**  
- 測試策略：靜態分析 + 模組單元測試 + 端到端整合測試（不需攝影機）。
- 發現並修正兩個 bug：`state_machine.py` 缺少 `Any` import；`db.query_history` 在 db 檔案不存在時會 crash（改為回傳空陣列）。
- README.md 以繁體中文撰寫，涵蓋架構圖、快速開始、使用流程、API 參考、部署說明。

**Files Updated**  
- `Combine_System/src/combine_system/state_machine.py` — 補上 `Any` import
- `Combine_System/src/combine_system/db.py` — `query_history` 加入 db 不存在的 graceful fallback
- `README.md` — 新建

**Summary of Changes**  
- 執行 7 項測試全部通過：event_bus、db 寫入/查詢、ws_server 端到端、HTTP API 端點、Node B 三個端點、Node C TypeScript build。
- 修正 `state_machine.py` 的 `Any` 未 import 問題（會在 Python 3.11 嚴格模式下 NameError）。
- 修正 `db.query_history` 在 db 尚未建立時的 OperationalError。

**Validation**  
- `event_bus` publish/subscribe/unsubscribe：OK
- `db` init + writer thread + query（15 筆）：OK
- `ws_server` WebSocket 端到端（publish → client recv）：OK
- `api_handler` /api/status + /api/history：OK
- Node B /notfocus + /badposture + /status：OK
- Node C `npm run build`：OK（0 TypeScript 錯誤）
- `query_history` on missing db：OK（回傳 []）

**Open Follow-ups**  
- 下一步：Node A 部署到 Raspberry Pi（systemd service）
- 下一步：實體 ESP32 韌體（Arduino/MicroPython，訂閱告警 URL）
- 下一步：Node C 生產部署（`npm run build` + nginx 或直接 serve dist/）



### 2026-05-26 Session 005

**Request**  
根據 `spec.md` 開發完整套系統，包含 Node A 事件輸出層、Node A 歷史紀錄持久化、Node B mock server、Node C React 儀表板。

**Key Decisions**  
- Node A 新增 WebSocket server（port 9548）以 asyncio + `websockets` 庫廣播 `SystemEvent` JSON；透過 `event_bus.py` 解耦主迴圈與所有消費者。
- Node A 新增 SQLite 持久化（`events.db`），以獨立 daemon thread 批次寫入，每 10 筆或 5 秒 commit 一次。
- Node A 新增 `/api/status`（最新事件 JSON）與 `/api/history`（SQLite 查詢）REST 端點，並加入 CORS headers。
- Node B 以純 stdlib Python HTTP server 模擬 ESP32，接收 `/notfocus` 與 `/badposture` 告警，以 ANSI 彩色輸出模擬 LED/蜂鳴器，提供 `/status` 與 `/` 頁面。
- Node C 使用 Vite + React 18 + TypeScript + Tailwind CSS + recharts；Vite dev proxy 解決所有 CORS 問題（`/api`、`/ws`、`/stream.mjpg`、`/start`、`/end` 全部代理到 Node A）。
- WebSocket threading bridge 採用 `loop.call_soon_threadsafe(q.put_nowait, event)` 模式，避免阻塞 asyncio event loop。

**Files Updated**  
- `Combine_System/pyproject.toml` — 新增 `websockets>=12.0`
- `Combine_System/src/combine_system/config.py` — 新增 `ws_port`, `db_path` 欄位
- `Combine_System/src/combine_system/app.py` — 加入 event_bus.publish、ws_server.start、db.start、新 API 路由、CORS headers
- `Combine_System/src/combine_system/event_bus.py` — 新建
- `Combine_System/src/combine_system/ws_server.py` — 新建
- `Combine_System/src/combine_system/db.py` — 新建
- `Combine_System/src/combine_system/api_handler.py` — 新建
- `Node_B/pyproject.toml` — 新建
- `Node_B/src/node_b/__init__.py` — 新建
- `Node_B/src/node_b/server.py` — 新建
- `Node_C/` — 完整 Vite 專案（vite.config.ts、types.ts、hooks/、components/、pages/）

**Summary of Changes**  
- Node A 主迴圈在 TRACKING 狀態每幀呼叫 `event_bus.publish(event)`，由 event_bus 分發給 WebSocket broadcaster 與 SQLite writer。
- Node B 在 port 9549 接收告警，模擬實體提醒輸出。
- Node C Dashboard 頁面透過 WebSocket 即時顯示專注狀態、姿勢狀態、頭部姿態、視線追蹤、分心率、姿勢率；History 頁面提供日期範圍查詢與 recharts 折線圖。

**Validation**  
- `uv sync --no-dev` 成功安裝 `websockets==16.0`。
- `npm run build` 成功，TypeScript 無型別錯誤，Vite build 輸出 587KB JS + 15KB CSS。
- 未執行端到端整合測試（需要攝影機環境）。

**Open Follow-ups**  
- 需在有攝影機的環境執行端到端測試，驗證 WebSocket 事件流與 SQLite 寫入。
- Node B 的告警 URL 目前仍指向 `https://controller.nchuit.com/`；若要改用本地 Node B mock，需修改 `config.py` 的 `alert_distraction_url` 與 `alert_posture_url` 為 `http://localhost:9549/notfocus` 與 `http://localhost:9549/badposture`。
- Node C production build 的 chunk size 超過 500KB（recharts 造成），可後續用 dynamic import 拆分。
- Phase 3（Node B/C 串接）與 Phase 4（整體整合驗證）尚未完成。



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
