from __future__ import annotations

import collections
import io
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

# Force UTF-8 output on Windows (default is GBK which can't encode many Unicode chars)
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

_PORT = 9549
_lock = threading.Lock()
_alert_log: collections.deque = collections.deque(maxlen=50)
_counts: dict[str, int] = {"distraction": 0, "posture": 0}
_last_alert: dict[str, str] = {}

# ANSI color codes
_RED    = "\033[91m"
_YELLOW = "\033[93m"
_GREEN  = "\033[92m"
_CYAN   = "\033[96m"
_BOLD   = "\033[1m"
_RESET  = "\033[0m"

_TYPE_ZH = {
    "distraction": "分心警報",
    "posture":     "坐姿不良警報",
}

_BELL = "\a"  # terminal bell


def _log_alert(alert_type: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = {"timestamp": ts, "type": alert_type}
    with _lock:
        _alert_log.append(entry)
        _counts[alert_type] = _counts.get(alert_type, 0) + 1
        _last_alert[alert_type] = ts
        count = _counts[alert_type]

    color = _RED if alert_type == "distraction" else _YELLOW
    label = "分心" if alert_type == "distraction" else "坐姿不良"
    print(f"\n{color}{_BOLD}{'='*50}{_RESET}")
    print(f"{color}{_BOLD}  !! [{label}] 第 {count} 次  !!{_RESET}")
    print(f"{color}{_BOLD}  時間：{ts}{_RESET}")
    print(f"{color}{_BOLD}  模擬 LED 閃爍 + 蜂鳴器響起{_RESET}")
    print(f"{color}{_BOLD}{'='*50}{_RESET}\n")
    print(_BELL, end="", flush=True)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/notfocus", "/notfocus/"):
            _log_alert("distraction")
            self._ok("已收到警報：分心")

        elif self.path in ("/badposture", "/badposture/"):
            _log_alert("posture")
            self._ok("已收到警報：坐姿不良")

        elif self.path.startswith("/test"):
            # /test?type=distraction  or  /test?type=posture  (預設 distraction)
            t = "posture" if "posture" in self.path else "distraction"
            _log_alert(t)
            self._ok(f"[測試] 已手動觸發：{_TYPE_ZH[t]}")

        elif self.path == "/status":
            with _lock:
                data = {
                    "counts": dict(_counts),
                    "last_alert": dict(_last_alert),
                    "log": list(_alert_log),
                }
            self._json(data)

        elif self.path == "/":
            self._html()

        else:
            self.send_error(404)

    def _ok(self, msg: str) -> None:
        body = msg.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data: Any) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self) -> None:
        with _lock:
            d_count = _counts.get("distraction", 0)
            p_count = _counts.get("posture", 0)
            d_last  = _last_alert.get("distraction", "—")
            p_last  = _last_alert.get("posture", "—")
            rows = "".join(
                f'<tr class="{e["type"]}">'
                f'<td>{e["timestamp"]}</td>'
                f'<td>{_TYPE_ZH.get(e["type"], e["type"])}</td>'
                f'</tr>'
                for e in reversed(list(_alert_log))
            )

        html = f"""<!DOCTYPE html>
<html>
<head>
  <title>Node B — 警報監控</title>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="2">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #0d0d0d; color: #eee; font-family: 'Courier New', monospace; padding: 24px; }}
    h1 {{ color: #f90; font-size: 1.4rem; margin-bottom: 4px; }}
    .sub {{ color: #666; font-size: 0.8rem; margin-bottom: 20px; }}

    .counters {{ display: flex; gap: 16px; margin-bottom: 20px; }}
    .counter-box {{
      flex: 1; border-radius: 10px; padding: 16px 20px; text-align: center;
      border: 2px solid;
    }}
    .counter-box.distraction {{ border-color: #ef4444; background: #1a0000; }}
    .counter-box.posture     {{ border-color: #f59e0b; background: #1a1000; }}
    .counter-box .num  {{ font-size: 3rem; font-weight: bold; line-height: 1; }}
    .counter-box .lbl  {{ font-size: 0.85rem; margin-top: 4px; opacity: 0.8; }}
    .counter-box .last {{ font-size: 0.7rem; margin-top: 6px; color: #888; }}
    .distraction .num {{ color: #ef4444; }}
    .posture     .num {{ color: #f59e0b; }}

    .test-btns {{ display: flex; gap: 12px; margin-bottom: 20px; }}
    .test-btns a {{
      display: inline-block; padding: 10px 24px; border-radius: 6px;
      font-weight: bold; font-size: 0.9rem; text-decoration: none; color: #fff;
    }}
    .btn-d {{ background: #b91c1c; }}
    .btn-d:hover {{ background: #ef4444; }}
    .btn-p {{ background: #b45309; }}
    .btn-p:hover {{ background: #f59e0b; color: #000; }}

    table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
    th, td {{ border: 1px solid #333; padding: 7px 12px; text-align: left; }}
    th {{ background: #1a1a1a; color: #f90; }}
    tr.distraction td {{ color: #fca5a5; }}
    tr.posture     td {{ color: #fcd34d; }}
    tr:nth-child(even) {{ background: #111; }}
    .empty {{ color: #555; text-align: center; padding: 20px; }}
  </style>
</head>
<body>
  <h1>Node B — ESP32 警報模擬器</h1>
  <p class="sub">port {_PORT} ｜ 每 2 秒自動刷新 ｜
    端點：<code>/notfocus</code> <code>/badposture</code>
    <code>/test?type=distraction</code> <code>/test?type=posture</code>
    <code>/status</code>
  </p>

  <div class="counters">
    <div class="counter-box distraction">
      <div class="num">{d_count}</div>
      <div class="lbl">分心警報</div>
      <div class="last">最後：{d_last}</div>
    </div>
    <div class="counter-box posture">
      <div class="num">{p_count}</div>
      <div class="lbl">坐姿不良警報</div>
      <div class="last">最後：{p_last}</div>
    </div>
  </div>

  <div class="test-btns">
    <a class="btn-d" href="/test?type=distraction">[!] 手動觸發：分心</a>
    <a class="btn-p" href="/test?type=posture">[!] 手動觸發：坐姿不良</a>
  </div>

  <table>
    <tr><th>時間</th><th>警報類型</th></tr>
    {rows or '<tr><td colspan="2" class="empty">尚無警報紀錄</td></tr>'}
  </table>
</body>
</html>"""
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def main() -> None:
    server = HTTPServer(("0.0.0.0", _PORT), Handler)
    print(f"{_CYAN}{_BOLD}[Node B] 警報模擬伺服器已啟動：http://0.0.0.0:{_PORT}{_RESET}")
    print(f"{_CYAN}  端點：/notfocus  /badposture  /test?type=distraction  /test?type=posture  /status  /{_RESET}")
    print(f"{_GREEN}  瀏覽器開啟 http://localhost:{_PORT}/ 可即時查看警報計數{_RESET}\n")
    server.serve_forever()


if __name__ == "__main__":
    main()
