#!/usr/bin/env bash
# =============================================================
#  AIOT Node A — 樹莓派一鍵安裝與開機自啟動設定腳本
#  用法：在樹莓派上執行  bash setup_rpi.sh
#  需要 sudo 權限（用於寫入 systemd service）
# =============================================================
set -euo pipefail

# ── 顏色輸出 ──────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*"; exit 1; }

# ── 基本檢查 ──────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && error "請以 sudo 執行：sudo bash setup_rpi.sh"
[[ "$(uname -m)" != aarch64 && "$(uname -m)" != armv7l ]] && \
    warn "非 ARM 架構（$(uname -m)），仍繼續執行..."

# ── 路徑設定 ──────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMBINE_DIR="$SCRIPT_DIR"
SERVICE_NAME="aiot-node-a"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

# 執行 Node A 的使用者（預設 pi，可改）
RUN_USER="${SUDO_USER:-pi}"
RUN_HOME=$(eval echo "~$RUN_USER")

echo -e "\n${BOLD}=== AIOT Node A 樹莓派安裝腳本 ===${RESET}"
echo -e "  專案目錄：${COMBINE_DIR}"
echo -e "  執行使用者：${RUN_USER}"
echo -e "  Service 名稱：${SERVICE_NAME}\n"

# ── Step 1：安裝系統依賴 ──────────────────────────────────────
info "Step 1/5：安裝系統依賴..."
apt-get update -qq
apt-get install -y -qq \
    python3 python3-pip python3-venv \
    libcamera-apps libcamera-dev \
    libopencv-dev \
    curl git 2>/dev/null || true
success "系統依賴安裝完成"

# ── Step 2：安裝 uv ───────────────────────────────────────────
info "Step 2/5：安裝 uv 套件管理器..."
if command -v uv &>/dev/null; then
    success "uv 已安裝（$(uv --version)），跳過"
else
    # 安裝到執行使用者的 home，避免 root 環境污染
    sudo -u "$RUN_USER" bash -c \
        'curl -LsSf https://astral.sh/uv/install.sh | sh'
    # 讓 root 也能找到 uv（systemd 需要）
    UV_BIN="$RUN_HOME/.local/bin/uv"
    if [[ ! -f "$UV_BIN" ]]; then
        UV_BIN="$RUN_HOME/.cargo/bin/uv"
    fi
    ln -sf "$UV_BIN" /usr/local/bin/uv 2>/dev/null || true
    success "uv 安裝完成"
fi

UV_CMD=$(command -v uv || echo "$RUN_HOME/.local/bin/uv")

# ── Step 3：安裝 Python 依賴 ──────────────────────────────────
info "Step 3/5：安裝 Python 依賴（uv sync）..."
cd "$COMBINE_DIR"
sudo -u "$RUN_USER" "$UV_CMD" sync --no-dev
success "Python 依賴安裝完成"

# 取得 venv 內的 python 路徑
VENV_PYTHON="$COMBINE_DIR/.venv/bin/python"
[[ ! -f "$VENV_PYTHON" ]] && error ".venv/bin/python 不存在，uv sync 可能失敗"

# ── Step 4：建立 systemd service ─────────────────────────────
info "Step 4/5：建立 systemd service..."

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=AIOT Node A — 學習專注與坐姿監測系統
After=network.target
Wants=network.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${COMBINE_DIR}
ExecStart=${UV_CMD} run python -m combine_system.app
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
# 讓 MediaPipe / OpenCV 可以存取攝影機
SupplementaryGroups=video

[Install]
WantedBy=multi-user.target
EOF

success "Service 檔案已寫入：${SERVICE_FILE}"

# ── Step 5：啟用並啟動 service ────────────────────────────────
info "Step 5/5：啟用開機自啟動並立即啟動..."
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

# 等待 3 秒確認狀態
sleep 3
if systemctl is-active --quiet "$SERVICE_NAME"; then
    success "Service 已啟動並設定為開機自啟動！"
else
    warn "Service 啟動失敗，請查看 log："
    echo -e "  ${YELLOW}journalctl -u ${SERVICE_NAME} -n 30 --no-pager${RESET}"
    systemctl status "$SERVICE_NAME" --no-pager || true
    exit 1
fi

# ── 完成摘要 ──────────────────────────────────────────────────
PI_IP=$(hostname -I | awk '{print $1}')
echo -e "\n${BOLD}${GREEN}=== 安裝完成 ===${RESET}"
echo -e "  Node A 已在背景執行，開機後自動啟動"
echo -e ""
echo -e "  ${BOLD}常用指令：${RESET}"
echo -e "  查看狀態：  ${CYAN}sudo systemctl status ${SERVICE_NAME}${RESET}"
echo -e "  查看 log：  ${CYAN}journalctl -u ${SERVICE_NAME} -f${RESET}"
echo -e "  停止服務：  ${CYAN}sudo systemctl stop ${SERVICE_NAME}${RESET}"
echo -e "  重新啟動：  ${CYAN}sudo systemctl restart ${SERVICE_NAME}${RESET}"
echo -e "  取消自啟：  ${CYAN}sudo systemctl disable ${SERVICE_NAME}${RESET}"
echo -e ""
echo -e "  ${BOLD}存取位址（區域網路）：${RESET}"
echo -e "  監看頁面：  ${CYAN}http://${PI_IP}:9547/${RESET}"
echo -e "  API 狀態：  ${CYAN}http://${PI_IP}:9547/api/status${RESET}"
echo -e "  WebSocket： ${CYAN}ws://${PI_IP}:9548${RESET}"
echo -e ""
echo -e "  ${YELLOW}提示：Node C 的 vite.config.ts proxy 目標需改為 http://${PI_IP}:9547${RESET}"
