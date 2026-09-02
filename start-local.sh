#!/usr/bin/env bash
# TCS Biospecimen Platform — Mac local setup
# Does not need Docker, Homebrew, or admin rights.
# Runtimes are downloaded into .local-runtime/ in this project.
#
#   ./start-local.sh
#   ./start-local.sh --reset
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
RUNTIME="$ROOT/.local-runtime"
RESEED=0
PGPORT="${PGPORT:-54329}"
PGUSER="biospecimen"
PGPASSWORD="biospecimen"
PGDATABASE="biospecimen"
export PGPASSWORD

PYTHON_BIN=""
NODE_BIN_DIR=""
PG_BIN=""
BACKEND_PID=""
FRONTEND_PID=""
PG_STARTED=0

for arg in "$@"; do
  case "$arg" in
    --reset) RESEED=1 ;;
    --no-brew) ;; # kept for compatibility; brew is never required
    -h|--help)
      sed -n '2,8p' "$0"
      exit 0
      ;;
  esac
done

log() { printf '\n\033[0;36m==>\033[0m %s\n' "$*"; }
ok() { printf '\033[0;32m    %s\033[0m\n' "$*"; }
die() { printf '\033[0;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "macOS is missing '$1'. It is a built-in tool and should already be present."
}

cpu_triple() {
  case "$(uname -m)" in
    arm64) echo "aarch64-apple-darwin" ;;
    x86_64) echo "x86_64-apple-darwin" ;;
    *) die "Unsupported Mac CPU: $(uname -m)" ;;
  esac
}

node_arch() {
  case "$(uname -m)" in
    arm64) echo "darwin-arm64" ;;
    x86_64) echo "darwin-x64" ;;
    *) die "Unsupported Mac CPU: $(uname -m)" ;;
  esac
}

unquarantine() {
  xattr -dr com.apple.quarantine "$1" 2>/dev/null || true
}

download() {
  local url="$1" dest="$2"
  curl -fL --retry 3 --retry-delay 2 -o "$dest" "$url"
}

cleanup() {
  trap - EXIT INT TERM
  if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    kill "${BACKEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${FRONTEND_PID}" ]] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    kill "${FRONTEND_PID}" 2>/dev/null || true
  fi
  if [[ "$PG_STARTED" -eq 1 && -n "$PG_BIN" && -x "$PG_BIN/pg_ctl" ]]; then
    "$PG_BIN/pg_ctl" -D "$RUNTIME/pgdata" -m fast stop >/dev/null 2>&1 || true
  fi
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

find_existing_python() {
  local candidate version
  for candidate in \
    "$BACKEND/.venv/bin/python" \
    "$(command -v python3.12 2>/dev/null || true)" \
    "$(command -v python3 2>/dev/null || true)"; do
    [[ -n "$candidate" && -x "$candidate" ]] || continue
    version="$("$candidate" -c 'import sys; print("%d.%d"%sys.version_info[:2])' 2>/dev/null || true)"
    if [[ "$version" == "3.12" || "$version" == "3.13" ]]; then
      PYTHON_BIN="$candidate"
      return 0
    fi
  done
  return 1
}

ensure_python() {
  if find_existing_python; then
    ok "Using Python $($PYTHON_BIN --version) at $PYTHON_BIN"
    return
  fi

  log "Python 3.12 is not on this Mac. Installing a user-local copy (no Homebrew, no admin)"
  mkdir -p "$RUNTIME/uv"
  if [[ ! -x "$RUNTIME/uv/uv" ]]; then
    curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$RUNTIME/uv" UV_NO_MODIFY_PATH=1 sh
  fi
  unquarantine "$RUNTIME/uv"
  "$RUNTIME/uv/uv" python install 3.12
  PYTHON_BIN="$("$RUNTIME/uv/uv" python find 3.12)"
  [[ -x "$PYTHON_BIN" ]] || die "Failed to install a user-local Python 3.12"
  ok "User-local Python ready: $PYTHON_BIN"
}

ensure_node() {
  local node npm
  node="$(command -v node 2>/dev/null || true)"
  npm="$(command -v npm 2>/dev/null || true)"
  if [[ -n "$node" && -n "$npm" ]]; then
    NODE_BIN_DIR="$(dirname "$node")"
    ok "Using Node $($node -v) from $NODE_BIN_DIR"
    return
  fi

  local ver="v20.19.0"
  local arch name dir
  arch="$(node_arch)"
  name="node-${ver}-${arch}"
  dir="$RUNTIME/node"
  if [[ ! -x "$dir/bin/node" ]]; then
    log "Node.js is not on this Mac. Downloading $name into the project (no Homebrew)"
    mkdir -p "$RUNTIME"
    download "https://nodejs.org/dist/${ver}/${name}.tar.gz" "$RUNTIME/node.tar.gz"
    rm -rf "$dir"
    mkdir -p "$dir"
    tar -xzf "$RUNTIME/node.tar.gz" -C "$RUNTIME"
    mv "$RUNTIME/$name" "$dir"
    rm -f "$RUNTIME/node.tar.gz"
    unquarantine "$dir"
  fi
  NODE_BIN_DIR="$dir/bin"
  [[ -x "$NODE_BIN_DIR/node" && -x "$NODE_BIN_DIR/npm" ]] || die "Failed to install a user-local Node.js"
  export PATH="$NODE_BIN_DIR:$PATH"
  ok "User-local Node $($NODE_BIN_DIR/node -v) ready"
}

find_pg_bin_from() {
  local dir="$1"
  if [[ -x "$dir/initdb" && -x "$dir/pg_ctl" && -x "$dir/psql" ]]; then
    PG_BIN="$dir"
    return 0
  fi
  return 1
}

locate_existing_postgres() {
  local dir
  if find_pg_bin_from "$RUNTIME/postgres/bin"; then
    return 0
  fi
  for dir in \
    /Applications/Postgres.app/Contents/Versions/latest/bin \
    /Applications/Postgres.app/Contents/Versions/16/bin \
    "$HOME/Applications/Postgres.app/Contents/Versions/latest/bin" \
    /opt/homebrew/opt/postgresql@16/bin \
    /usr/local/opt/postgresql@16/bin; do
    if find_pg_bin_from "$dir"; then
      return 0
    fi
  done
  if command -v initdb >/dev/null 2>&1 && command -v pg_ctl >/dev/null 2>&1 && command -v psql >/dev/null 2>&1; then
    PG_BIN="$(dirname "$(command -v pg_ctl)")"
    return 0
  fi
  return 1
}

ensure_postgres_binaries() {
  if locate_existing_postgres; then
    ok "Using PostgreSQL tools in $PG_BIN"
    return
  fi

  local ver="16.15.0"
  local triple name
  triple="$(cpu_triple)"
  name="postgresql-${ver}-${triple}"
  log "PostgreSQL is not on this Mac. Downloading $name into the project (no Homebrew)"
  mkdir -p "$RUNTIME"
  download "https://github.com/theseus-rs/postgresql-binaries/releases/download/${ver}/${name}.tar.gz" "$RUNTIME/postgres.tar.gz"
  rm -rf "$RUNTIME/postgres"
  mkdir -p "$RUNTIME/postgres"
  tar -xzf "$RUNTIME/postgres.tar.gz" -C "$RUNTIME/postgres"
  rm -f "$RUNTIME/postgres.tar.gz"
  if [[ -x "$RUNTIME/postgres/bin/pg_ctl" ]]; then
    PG_BIN="$RUNTIME/postgres/bin"
  else
    PG_BIN="$(find "$RUNTIME/postgres" -type f -name pg_ctl | head -n 1 | xargs dirname)"
  fi
  [[ -n "$PG_BIN" && -x "$PG_BIN/pg_ctl" ]] || die "Failed to unpack user-local PostgreSQL"
  unquarantine "$RUNTIME/postgres"
  ok "User-local PostgreSQL ready: $PG_BIN"
}

wait_pg() {
  local i
  for i in $(seq 1 50); do
    if "$PG_BIN/pg_isready" -h 127.0.0.1 -p "$PGPORT" -q; then
      return 0
    fi
    sleep 0.3
  done
  return 1
}

ensure_database() {
  local data="$RUNTIME/pgdata"
  local sock="$RUNTIME/pgsocket"
  mkdir -p "$sock"

  log "Starting a project-local PostgreSQL on port $PGPORT"
  if [[ ! -f "$data/PG_VERSION" ]]; then
    "$PG_BIN/initdb" -D "$data" -U "$PGUSER" --auth=trust --encoding=UTF8 --locale=C
    ok "Initialized project-local database cluster"
  fi

  if ! "$PG_BIN/pg_isready" -h 127.0.0.1 -p "$PGPORT" -q; then
    if [[ -f "$data/postmaster.pid" ]]; then
      rm -f "$data/postmaster.pid"
    fi
    "$PG_BIN/pg_ctl" -D "$data" -l "$RUNTIME/postgres.log" -w start \
      -o "-p $PGPORT -k $sock --listen_addresses=127.0.0.1"
    PG_STARTED=1
  else
    ok "PostgreSQL already listening on $PGPORT"
  fi
  wait_pg || die "Project-local PostgreSQL did not start. See $RUNTIME/postgres.log"

  if ! "$PG_BIN/psql" -h 127.0.0.1 -p "$PGPORT" -U "$PGUSER" -d postgres -tAc \
      "SELECT 1 FROM pg_database WHERE datname='$PGDATABASE'" | grep -q 1; then
    "$PG_BIN/createdb" -h 127.0.0.1 -p "$PGPORT" -U "$PGUSER" "$PGDATABASE"
    ok "Created database $PGDATABASE"
  else
    ok "Database $PGDATABASE already exists"
  fi

  "$PG_BIN/psql" -h 127.0.0.1 -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
    -c "GRANT ALL ON SCHEMA public TO $PGUSER;" >/dev/null
}

write_backend_env() {
  cat > "$BACKEND/.env" <<EOF
APP_ENV=development
APP_NAME=TCS Biospecimen Platform
DATABASE_URL=postgresql+psycopg://${PGUSER}:${PGPASSWORD}@127.0.0.1:${PGPORT}/${PGDATABASE}
JWT_SECRET=change-me-in-production-use-a-long-random-string
JWT_EXPIRY_MINUTES=480
UPLOAD_DIR=./uploads
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
LOG_LEVEL=INFO
EOF
  ok "Wrote backend/.env for 127.0.0.1:${PGPORT}"
}

setup_backend() {
  log "Setting up Python API"
  mkdir -p "$BACKEND/uploads"
  if [[ ! -x "$BACKEND/.venv/bin/python" ]]; then
    "$PYTHON_BIN" -m venv "$BACKEND/.venv"
  fi
  # shellcheck disable=SC1091
  source "$BACKEND/.venv/bin/activate"
  pip install --upgrade pip >/dev/null
  pip install -r "$BACKEND/requirements.txt"
  (
    cd "$BACKEND"
    alembic upgrade head
    if [[ "$RESEED" -eq 1 ]]; then
      python -m app.seed --reset
    else
      python -m app.seed
    fi
  )
  ok "API dependencies, migrations, and seed data are ready"
}

setup_frontend() {
  log "Setting up React UI"
  export PATH="${NODE_BIN_DIR}:$PATH"
  (
    cd "$FRONTEND"
    npm install
  )
  ok "UI dependencies are ready"
}

port_in_use() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

wait_http() {
  local url="$1"
  local i
  for i in $(seq 1 50); do
    if curl -sf "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.4
  done
  return 1
}

start_services() {
  if port_in_use 8000; then
    die "Port 8000 is already in use. Stop that process and run this script again."
  fi
  if port_in_use 5173; then
    die "Port 5173 is already in use. Stop that process and run this script again."
  fi

  export PATH="${NODE_BIN_DIR}:$PATH"

  log "Starting API on http://127.0.0.1:8000"
  (
    cd "$BACKEND"
    exec "$BACKEND/.venv/bin/uvicorn" app.main:app --reload --host 127.0.0.1 --port 8000
  ) &
  BACKEND_PID=$!
  wait_http "http://127.0.0.1:8000/health" || die "API did not start. Check the output above."
  ok "API is healthy"

  log "Starting UI on http://127.0.0.1:5173"
  (
    cd "$FRONTEND"
    exec npm run dev -- --host 127.0.0.1 --port 5173
  ) &
  FRONTEND_PID=$!
  wait_http "http://127.0.0.1:5173" || die "UI did not start. Check the output above."

  cat <<EOF

----------------------------------------------------------------------
TCS Biospecimen Platform is running
(no Docker, no Homebrew required)

  UI:      http://localhost:5173
  API:     http://localhost:8000
  Swagger: http://localhost:8000/docs

  operator@biospecimen.local / LabOps@2026
  reviewer@biospecimen.local / LabOps@2026
  admin@biospecimen.local    / LabOps@2026

Press Ctrl+C to stop the UI, API, and local database.
----------------------------------------------------------------------

EOF
  wait
}

[[ "$(uname -s)" == "Darwin" ]] || die "This script is for macOS."
need_cmd curl
need_cmd tar
need_cmd lsof

mkdir -p "$RUNTIME"
log "Preparing a user-local environment (Homebrew is not required)"
ensure_python
ensure_node
ensure_postgres_binaries
ensure_database
write_backend_env
setup_backend
setup_frontend
start_services
