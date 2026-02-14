#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"
RUNTIME_DIR="${ROOT_DIR}/.demo-runtime"
STATE_FILE="${RUNTIME_DIR}/state.env"

# Optional local overrides
if [[ -f "${ROOT_DIR}/.env.demo" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env.demo"
fi

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
BACKEND_START_CMD="${BACKEND_START_CMD:-uvicorn app.main:app --host ${BACKEND_HOST} --port ${BACKEND_PORT}}"
CF_PAGES_PROJECT="${CF_PAGES_PROJECT:-aerotri-web-demo}"
CF_PAGES_BRANCH="${CF_PAGES_BRANCH:-demo}"
DEMO_SKIP_BACKEND_START="${DEMO_SKIP_BACKEND_START:-0}"

BACKEND_LOG="$(mktemp -t aerotri-backend.XXXXXX.log)"
TUNNEL_LOG="$(mktemp -t aerotri-tunnel.XXXXXX.log)"
PAGES_LOG="$(mktemp -t aerotri-pages.XXXXXX.log)"
BACKEND_PID=""
TUNNEL_PID=""

cleanup() {
  if [[ -n "${TUNNEL_PID}" ]]; then
    kill "${TUNNEL_PID}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${BACKEND_PID}" ]]; then
    kill "${BACKEND_PID}" >/dev/null 2>&1 || true
  fi
  rm -f "${STATE_FILE}" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

need_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "Missing required command: ${cmd}"
    exit 1
  fi
}

need_cmd cloudflared
need_cmd npx
need_cmd python3
need_cmd grep
need_cmd awk

mkdir -p "${RUNTIME_DIR}"

echo "[1/5] Checking Cloudflare auth..."
if ! (cd "${FRONTEND_DIR}" && npx wrangler whoami >/dev/null 2>&1); then
  echo "Wrangler is not authenticated. Run: npx wrangler login"
  exit 1
fi

if [[ "${DEMO_SKIP_BACKEND_START}" != "1" ]]; then
  echo "[2/5] Starting backend on ${BACKEND_HOST}:${BACKEND_PORT}..."
  (
    cd "${BACKEND_DIR}"
    exec bash -lc "${BACKEND_START_CMD}"
  ) >"${BACKEND_LOG}" 2>&1 &
  BACKEND_PID=$!
  sleep 2
else
  echo "[2/5] Skipping backend start (DEMO_SKIP_BACKEND_START=1)."
fi

echo "[3/5] Creating public API tunnel..."
cloudflared tunnel --url "http://${BACKEND_HOST}:${BACKEND_PORT}" --no-autoupdate >"${TUNNEL_LOG}" 2>&1 &
TUNNEL_PID=$!

API_PUBLIC_URL=""
for _ in {1..120}; do
  API_PUBLIC_URL="$(grep -Eo 'https://[-a-z0-9]+\.trycloudflare\.com' "${TUNNEL_LOG}" | head -n1 || true)"
  if [[ -n "${API_PUBLIC_URL}" ]]; then
    break
  fi
  sleep 1
done

if [[ -z "${API_PUBLIC_URL}" ]]; then
  echo "Failed to obtain trycloudflare URL."
  echo "Tunnel logs: ${TUNNEL_LOG}"
  exit 1
fi

cat >"${STATE_FILE}" <<EOF
BACKEND_PID=${BACKEND_PID}
TUNNEL_PID=${TUNNEL_PID}
BACKEND_LOG=${BACKEND_LOG}
TUNNEL_LOG=${TUNNEL_LOG}
PAGES_LOG=${PAGES_LOG}
API_PUBLIC_URL=${API_PUBLIC_URL}
EOF

echo "[4/5] Building frontend with VITE_API_BASE_URL=${API_PUBLIC_URL}/api ..."
if command -v pnpm >/dev/null 2>&1; then
  (
    cd "${FRONTEND_DIR}"
    [[ -d node_modules ]] || pnpm install --frozen-lockfile
    VITE_API_BASE_URL="${API_PUBLIC_URL}/api" pnpm build
  )
else
  (
    cd "${FRONTEND_DIR}"
    [[ -d node_modules ]] || npm ci
    VITE_API_BASE_URL="${API_PUBLIC_URL}/api" npm run build
  )
fi

echo "[5/5] Deploying frontend to Cloudflare Pages..."
(
  cd "${FRONTEND_DIR}"
  npx wrangler pages deploy dist \
    --project-name "${CF_PAGES_PROJECT}" \
    --branch "${CF_PAGES_BRANCH}"
) >"${PAGES_LOG}" 2>&1

PAGES_URL="$(grep -Eo 'https://[a-zA-Z0-9.-]+\.pages\.dev' "${PAGES_LOG}" | tail -n1 || true)"

if [[ -z "${PAGES_URL}" ]]; then
  echo "Pages deploy finished, but no pages.dev URL was parsed."
  echo "Pages logs: ${PAGES_LOG}"
  exit 1
fi

echo
echo "Demo is live:"
echo "Frontend: ${PAGES_URL}"
echo "Backend : ${API_PUBLIC_URL}"
echo
echo "The backend tunnel must stay running during the demo."
echo "Press Ctrl+C to stop backend+tunnel."

wait "${TUNNEL_PID}"
