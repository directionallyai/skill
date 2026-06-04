#!/usr/bin/env bash
set -euo pipefail

API_BASE="https://api.dev.directionally.ai"
POLL_TIMEOUT=${POLL_TIMEOUT:-120}
SUBSESSION="test_run_$(date +%s)"
PASS=0
FAIL=0

dir() {
  env DIRECTIONALLY_API_BASE="$API_BASE" npx -y directionally@0.2.4 "$@"
}

# macOS ships without GNU coreutils timeout; fall back to perl alarm
if ! command -v timeout &>/dev/null; then
  timeout() {
    local t=$1; shift
    perl -e "alarm($t); exec @ARGV" -- "$@"
  }
fi

poll() {
  # Wraps poll with a timeout so a non-returning long-poll doesn't stall the suite
  timeout "$POLL_TIMEOUT" env DIRECTIONALLY_API_BASE="$API_BASE" npx -y directionally@0.2.4 "$@" 2>&1 || true
}

pass() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

assert_field() {
  local label=$1 json=$2 field=$3 expected=$4
  local actual
  actual=$(echo "$json" | jq -r "$field" 2>/dev/null)
  if [[ "$actual" == "$expected" ]]; then
    pass "$label ($field = $expected)"
  else
    fail "$label (expected $field = $expected, got $actual)"
  fi
}

# ── Test 1: --first ──────────────────────────────────────────────────────────
echo "=== Test: --first creates a session ==="
FIRST_OUT=$(dir --first --subsession-id "$SUBSESSION" "test: explain this codebase" 2>&1)

BRIDGE_LINE=$(echo "$FIRST_OUT" | grep '"kind":"bridge_started"' | head -1)
if [[ -z "$BRIDGE_LINE" ]]; then
  fail "bridge_started line not found in --first output"
  echo "$FIRST_OUT"
  exit 1
fi

assert_field "bridge_started.kind"       "$BRIDGE_LINE" '.kind'       "bridge_started"
assert_field "bridge_started.sequence"   "$BRIDGE_LINE" '.sequence'   "0"
assert_field "bridge_started.project_id" "$BRIDGE_LINE" '.project_id' "schellingsh/skill"

SESSION_ID=$(echo "$BRIDGE_LINE" | jq -r '.session_id')
if [[ "$SESSION_ID" == sess_* ]]; then
  pass "session_id has sess_ prefix ($SESSION_ID)"
else
  fail "session_id unexpected format: $SESSION_ID"
  exit 1
fi

# ── Test 2: basic poll ───────────────────────────────────────────────────────
echo ""
echo "=== Test: --session poll returns polled event (timeout ${POLL_TIMEOUT}s) ==="
POLL_OUT=$(poll --session "$SESSION_ID" --after 0)

POLLED_LINE=$(echo "$POLL_OUT" | grep '"kind":"polled"' | head -1) || true
if [[ -z "$POLLED_LINE" ]]; then
  fail "polled event not found (may have timed out after ${POLL_TIMEOUT}s)"
  echo "$POLL_OUT"
else
  assert_field "polled.kind"  "$POLLED_LINE" '.kind'  "polled"
  assert_field "polled.after" "$POLLED_LINE" '.after' "0"
  COUNT=$(echo "$POLLED_LINE" | jq -r '.count')
  if [[ "$COUNT" =~ ^[0-9]+$ ]]; then
    pass "polled.count is numeric ($COUNT)"
  else
    fail "polled.count is not numeric: $COUNT"
  fi
fi

# ── Test 3: elaborating op ───────────────────────────────────────────────────
echo ""
echo "=== Test: elaborating op round-trips ==="
ELAB_PAYLOAD=$(jq -nc --arg sub "$SUBSESSION" \
  '{"op":"elaborating","subsession_id":$sub,"text":"test elaboration"}')
ELAB_OUT=$(poll --session "$SESSION_ID" --after 1 "$ELAB_PAYLOAD")

if echo "$ELAB_OUT" | grep -q '"kind":"polled"'; then
  pass "poll after elaborating returns polled event"
else
  fail "no polled event after elaborating"
  echo "$ELAB_OUT"
fi

# ── Test 4: report + outcome close-out ──────────────────────────────────────
echo ""
echo "=== Test: report + outcome close-out ==="
REPORT=$(jq -nc --arg sub "$SUBSESSION" \
  '{"op":"report","subsession_id":$sub,"did":"ran test suite","issues":"none"}')
OUTCOME=$(jq -nc --arg sub "$SUBSESSION" \
  '{"op":"outcome","subsession_id":$sub,"value":"no_context"}')
CLOSE_OUT=$(poll --session "$SESSION_ID" --after 2 "$REPORT" "$OUTCOME")

if echo "$CLOSE_OUT" | grep -q '"kind":"polled"'; then
  pass "poll after report+outcome returns polled event"
else
  fail "no polled event after report+outcome"
  echo "$CLOSE_OUT"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "================================"
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
