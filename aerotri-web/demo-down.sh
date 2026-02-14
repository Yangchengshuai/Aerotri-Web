#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="${ROOT_DIR}/.demo-runtime"
STATE_FILE="${RUNTIME_DIR}/state.env"

if [[ ! -f "${STATE_FILE}" ]]; then
  echo "No demo runtime state found: ${STATE_FILE}"
  echo "If demo services are still running, stop them manually."
  exit 0
fi

# shellcheck disable=SC1090
source "${STATE_FILE}"

stop_pid() {
  local pid="$1"
  local name="$2"
  if [[ -z "${pid:-}" ]]; then
    return 0
  fi
  if kill -0 "${pid}" >/dev/null 2>&1; then
    kill "${pid}" >/dev/null 2>&1 || true
    sleep 1
    if kill -0 "${pid}" >/dev/null 2>&1; then
      kill -9 "${pid}" >/dev/null 2>&1 || true
    fi
    echo "Stopped ${name} (pid=${pid})"
  else
    echo "${name} already stopped (pid=${pid})"
  fi
}

stop_pid "${TUNNEL_PID:-}" "cloudflared tunnel"
stop_pid "${BACKEND_PID:-}" "backend"

rm -f "${STATE_FILE}" >/dev/null 2>&1 || true
echo "Demo runtime state cleared."
