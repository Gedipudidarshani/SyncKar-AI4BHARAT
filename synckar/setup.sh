#!/usr/bin/env bash
# setup.sh — One-shot SyncKar deployment script for AWS EC2.
#
# Run this ONCE on the EC2 instance to deploy the full stack:
#   bash setup.sh
#
# What it does:
#   1. Checks prerequisites (git, docker, docker compose)
#   2. Clones the repo (or pulls latest if already cloned)
#   3. Writes .env from .env.ec2 template
#   4. Builds and starts all 5 containers with docker compose
#   5. Waits for the API to become healthy
#   6. Runs database migrations
#   7. Seeds demo data
#   8. Prints the dashboard URL
#
# Prerequisites on the EC2 instance:
#   - git
#   - docker (with docker compose plugin)
#   - Port 18080 open in the EC2 security group

set -euo pipefail

# ─── Config ───────────────────────────────────────────────────────────────────
REPO_URL="https://github.com/SANTHAN-KUMAR/SyncKar-AI4BHARAT.git"
REPO_DIR="$HOME/SyncKar-AI4BHARAT"
SYNCKAR_DIR="$REPO_DIR/synckar"
HEALTH_URL="http://localhost:18080/health"
HEALTH_RETRIES=30
HEALTH_INTERVAL=5

# ─── Colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
step()  { echo -e "\n${CYAN}━━━ $* ━━━${NC}"; }

# ─── Step 1: Prerequisites ────────────────────────────────────────────────────
step "Checking prerequisites"

for cmd in git docker curl; do
  if ! command -v "$cmd" &>/dev/null; then
    error "$cmd is not installed. Please install it and re-run."
    exit 1
  fi
done

if ! docker compose version &>/dev/null; then
  error "docker compose plugin not found."
  error "Install it with: sudo apt-get install docker-compose-plugin"
  exit 1
fi

info "git:    $(git --version)"
info "docker: $(docker --version)"
info "compose: $(docker compose version)"

# ─── Step 2: Clone or pull repo ───────────────────────────────────────────────
step "Setting up repository"

if [ -d "$REPO_DIR/.git" ]; then
  info "Repository already exists at $REPO_DIR — pulling latest..."
  git -C "$REPO_DIR" pull
else
  info "Cloning $REPO_URL into $REPO_DIR..."
  git clone "$REPO_URL" "$REPO_DIR"
fi

if [ ! -d "$SYNCKAR_DIR" ]; then
  error "Expected synckar/ subdirectory not found at $SYNCKAR_DIR"
  error "Check that the repo structure is correct."
  exit 1
fi

info "Repository ready at $SYNCKAR_DIR"

# ─── Step 3: Write .env ───────────────────────────────────────────────────────
step "Configuring environment"

ENV_FILE="$SYNCKAR_DIR/.env"
ENV_TEMPLATE="$SYNCKAR_DIR/.env.ec2"

if [ -f "$ENV_FILE" ]; then
  info ".env already exists — skipping copy (delete it to reset)."
else
  if [ ! -f "$ENV_TEMPLATE" ]; then
    error ".env.ec2 template not found at $ENV_TEMPLATE"
    error "The template should be committed to the repo. Check your git pull."
    exit 1
  fi
  info "Copying .env.ec2 → .env..."
  cp "$ENV_TEMPLATE" "$ENV_FILE"
fi

# Warn if RSA key is not set (demo will still work — container auto-generates)
if ! grep -qE "^RSA_PRIVATE_KEY_BASE64=.+" "$ENV_FILE" 2>/dev/null; then
  warn "RSA_PRIVATE_KEY_BASE64 is not set in .env."
  warn "The container will auto-generate a fresh RSA key pair at build time."
  warn "This is fine for a demo. To use your own key:"
  warn "  echo \"RSA_PRIVATE_KEY_BASE64=\$(base64 -w 0 $SYNCKAR_DIR/keys/private.pem)\" >> $ENV_FILE"
fi

# ─── Step 4: Start the stack ──────────────────────────────────────────────────
step "Building and starting Docker Compose stack"
info "This may take 3–8 minutes on first run (building images)..."

cd "$SYNCKAR_DIR"

docker compose \
  -f docker-compose.yml \
  -f docker-compose.override.yml \
  up --build -d

info "Containers started. Waiting for services to become healthy..."

# ─── Step 5: Wait for API health ──────────────────────────────────────────────
step "Waiting for synckar-api to become healthy"

healthy=false
for i in $(seq 1 $HEALTH_RETRIES); do
  if curl -sf "$HEALTH_URL" >/dev/null 2>&1; then
    healthy=true
    break
  fi
  printf "  Attempt %d/%d — not ready yet, waiting %ds...\n" "$i" "$HEALTH_RETRIES" "$HEALTH_INTERVAL"
  sleep "$HEALTH_INTERVAL"
done

if [ "$healthy" = false ]; then
  error "synckar-api did not become healthy after $((HEALTH_RETRIES * HEALTH_INTERVAL)) seconds."
  error "Check the logs: docker compose logs synckar-api"
  error "Common causes: image build failure, missing env var, port conflict."
  exit 1
fi

info "synckar-api is healthy!"

# ─── Step 6: Run migrations ───────────────────────────────────────────────────
step "Running database migrations"

docker compose exec -T synckar-api python scripts/run_migrations.py
info "Migrations complete."

# ─── Step 7: Seed demo data ───────────────────────────────────────────────────
step "Seeding demo data"

docker compose exec -T synckar-api python scripts/seed_data.py
info "Demo data seeded."

# ─── Step 8: Print summary ────────────────────────────────────────────────────
step "Deployment complete"

# Fetch public IP from EC2 instance metadata service (IMDSv1)
EC2_IP=$(curl -sf --connect-timeout 2 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "")
if [ -z "$EC2_IP" ]; then
  # Fallback: try to get the external IP another way
  EC2_IP=$(curl -sf --connect-timeout 2 https://checkip.amazonaws.com 2>/dev/null || echo "<EC2_PUBLIC_IP>")
fi

DASHBOARD_URL="http://${EC2_IP}:18080/dashboard"
HEALTH_ENDPOINT="http://${EC2_IP}:18080/health"
DOCS_URL="http://${EC2_IP}:18080/docs"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         ✅  SyncKar deployment complete!                     ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════════════╣${NC}"
printf "${GREEN}║${NC}  Dashboard : %-47s${GREEN}║${NC}\n" "$DASHBOARD_URL"
printf "${GREEN}║${NC}  Health    : %-47s${GREEN}║${NC}\n" "$HEALTH_ENDPOINT"
printf "${GREEN}║${NC}  API docs  : %-47s${GREEN}║${NC}\n" "$DOCS_URL"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

info "Container status:"
docker compose ps

echo ""
info "To run demo scenarios:"
echo "  docker compose exec synckar-api python scripts/demo_scenario_a.py"
echo "  docker compose exec synckar-api python scripts/demo_scenario_b.py"
echo "  docker compose exec synckar-api python scripts/demo_scenario_c.py"
echo ""
info "To reset and re-seed between demos:"
echo "  docker compose exec synckar-api python scripts/reset_state.py"
echo "  docker compose exec synckar-api python scripts/seed_data.py"
echo ""
info "To watch live logs:"
echo "  docker compose logs -f synckar-api"
