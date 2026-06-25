#!/usr/bin/env python3
"""Directionally agent session client."""

import hashlib
import http.client
import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

VERSION = "0.2.8"
# sha256 of the SKILL.md that ships alongside this script. Regenerate with:
#   shasum -a 256 .agents/skills/directionally/SKILL.md
SKILL_SHA256 = "f5a97376a69a9b4bc3439dfa09e61e7d79d13015edeec6d8ddf0b8a9b2c6e983"
DEFAULT_API_BASE = "https://api.directionally.ai"
CREDENTIALS_PATH = os.path.join(os.path.expanduser("~"), ".directionally", "credentials")
PENDING_LOGIN_PATH = os.path.join(os.path.expanduser("~"), ".directionally", "pending_login")
SKILL_RELATIVE = os.path.join(".agents", "skills", "directionally", "SKILL.md")
SKILL_CLAUDE_RELATIVE = os.path.join(".claude", "skills", "directionally", "SKILL.md")
DEFAULT_SKILL_URL = (
    "https://raw.githubusercontent.com/directionallyai/skill/refs/heads/main"
    "/.agents/skills/directionally/SKILL.md"
)
DEFAULT_SCRIPT_URL = (
    "https://raw.githubusercontent.com/directionallyai/skill/refs/heads/main"
    "/.agents/skills/directionally/scripts/directionally.py"
)

# Global skills dirs per agent type, matching the npx-skills registry.
# Each maps to ~/.{agent}/skills/ (or the agent's XDG equivalent).
def _global_skills_dir(agent_type):
    home = os.path.expanduser("~")
    codex_home = os.environ.get("CODEX_HOME", "").strip() or os.path.join(home, ".codex")
    claude_home = os.environ.get("CLAUDE_CONFIG_DIR", "").strip() or os.path.join(home, ".claude")
    mapping = {
        "claude-code":     os.path.join(claude_home, "skills"),
        "claude-desktop":  os.path.join(claude_home, "skills"),
        "codex":           os.path.join(codex_home, "skills"),
        "codex-desktop":   os.path.join(codex_home, "skills"),
        "cursor":          os.path.join(home, ".cursor", "skills"),
        "cursor-desktop":  os.path.join(home, ".cursor", "skills"),
    }
    return mapping.get(agent_type)


def verify_download(label, data, expected):
    """Refuse to install a tampered download.

    `data` is the raw bytes just pulled from the network; `expected` is the sha256
    we require it to match. Used at --setup time on the freshly downloaded SKILL.md
    (pinned by the hardcoded SKILL_SHA256) and directionally.py (pinned by the
    caller-supplied --script-hash, the trust anchor baked into the install command)."""
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        fail(f"integrity: {label} hash mismatch (expected {expected}, got {actual}). "
             "Refusing to install a tampered download.")


def get_api_base():
    return os.environ.get("DIRECTIONALLY_API_BASE", DEFAULT_API_BASE).rstrip("/")


def user_agent():
    return f"directionally/{VERSION}"


def now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_ndjson(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def fail(message, code=1):
    sys.stderr.write(message + "\n")
    sys.exit(code)


def parse_args(args):
    flags = {"_": []}
    i = 0
    while i < len(args):
        arg = args[i]
        if not arg.startswith("--"):
            flags["_"].append(arg)
            i += 1
            continue
        if "=" in arg:
            key, val = arg[2:].split("=", 1)
            flags[key.replace("-", "_")] = val
        else:
            key = arg[2:].replace("-", "_")
            if not key:
                raise ValueError(f"Invalid flag: {arg}")
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                flags[key] = args[i + 1]
                i += 1
            else:
                flags[key] = True
        i += 1
    return flags


def number_flag(value, fallback, name):
    if value is None or value is True or value == "":
        return fallback
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a non-negative integer.")
    if n < 0:
        raise ValueError(f"{name} must be a non-negative integer.")
    return n



def load_credential():
    try:
        with open(CREDENTIALS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("credential")
    except (OSError, json.JSONDecodeError):
        return None



def save_credential(credential, username):
    os.makedirs(os.path.dirname(CREDENTIALS_PATH), exist_ok=True)
    with open(CREDENTIALS_PATH, "w", encoding="utf-8") as f:
        json.dump({"credential": credential, "username": username}, f)
    os.chmod(CREDENTIALS_PATH, 0o600)


def save_pending_login(token, url):
    os.makedirs(os.path.dirname(PENDING_LOGIN_PATH), exist_ok=True)
    with open(PENDING_LOGIN_PATH, "w", encoding="utf-8") as f:
        json.dump({"token": token, "url": url}, f)


def load_pending_login():
    try:
        with open(PENDING_LOGIN_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def clear_pending_login():
    try:
        os.remove(PENDING_LOGIN_PATH)
    except OSError:
        pass


def try_redeem_pending_login(api_base):
    pending = load_pending_login()
    if not pending or not pending.get("token"):
        return
    parsed = urllib.parse.urlparse(api_base)
    is_https = parsed.scheme == "https"
    host = parsed.hostname
    port = parsed.port or (443 if is_https else 80)
    conn_cls = http.client.HTTPSConnection if is_https else http.client.HTTPConnection
    try:
        conn = conn_cls(host, port, timeout=10)
        poll_path = f"{parsed.path}/api/cli/login/poll?token={urllib.parse.quote(pending['token'], safe='')}"
        conn.request("GET", poll_path, headers={"User-Agent": user_agent()})
        resp = conn.getresponse()
        if resp.status == 200:
            result = json.loads(resp.read())
            conn.close()
            status = result.get("status")
            if status == "granted":
                save_credential(result["credential"], result.get("username", ""))
                clear_pending_login()
            elif status == "expired":
                clear_pending_login()
        else:
            conn.close()
    except Exception:
        pass


def auth_headers():
    cred = load_credential()
    if cred:
        return {"Authorization": f"Bearer {cred}"}
    return {}


def _emit_login_needed(api_base):
    """Print a login URL and exit with the auth-failure sentinel that SKILL.md watches for."""
    # Reuse a previously saved pending token if we have one.
    pending = load_pending_login()
    login_url = pending.get("url") if pending else None

    if not login_url:
        parsed = urllib.parse.urlparse(api_base)
        is_https = parsed.scheme == "https"
        host = parsed.hostname
        port = parsed.port or (443 if is_https else 80)
        conn_cls = http.client.HTTPSConnection if is_https else http.client.HTTPConnection
        try:
            conn = conn_cls(host, port, timeout=15)
            conn.request("POST", f"{parsed.path}/api/cli/login/start",
                         headers={"User-Agent": user_agent(), "Content-Length": "0"})
            resp = conn.getresponse()
            if resp.status == 200:
                data = json.loads(resp.read())
                login_url = data.get("url")
                if login_url:
                    save_pending_login(data.get("token", ""), login_url)
            conn.close()
        except Exception:
            pass

    if login_url:
        sys.stderr.write(
            f"Need to log in to Directionally. Open this URL in your browser:\n\n  {login_url}\n\n"
            "Then re-run your command.\n"
        )
    else:
        sys.stderr.write("Need to log in to Directionally. Run: directionally.py --login\n")
    sys.exit(1)


def cmd_login(api_base):
    parsed = urllib.parse.urlparse(api_base)
    is_https = parsed.scheme == "https"
    host = parsed.hostname
    port = parsed.port or (443 if is_https else 80)

    conn_cls = http.client.HTTPSConnection if is_https else http.client.HTTPConnection
    conn = conn_cls(host, port, timeout=30)
    conn.request("POST", f"{parsed.path}/api/cli/login/start",
                 headers={"User-Agent": user_agent(), "Content-Length": "0"})
    resp = conn.getresponse()
    if resp.status != 200:
        raise RuntimeError(f"login start failed: HTTP {resp.status}")
    data = json.loads(resp.read())
    conn.close()

    cli_token = data["token"]
    login_url = data["url"]
    expires_in = data.get("expires_in_seconds", 900)

    sys.stdout.write(f"\nOpen this URL to log in with GitHub:\n\n  {login_url}\n\nWaiting for login")
    sys.stdout.flush()

    deadline = time.time() + expires_in
    poll_interval = 3
    while time.time() < deadline:
        time.sleep(poll_interval)
        sys.stdout.write(".")
        sys.stdout.flush()
        conn = conn_cls(host, port, timeout=15)
        poll_path = f"{parsed.path}/api/cli/login/poll?token={urllib.parse.quote(cli_token, safe='')}"
        conn.request("GET", poll_path, headers={"User-Agent": user_agent()})
        poll_resp = conn.getresponse()
        if poll_resp.status == 200:
            result = json.loads(poll_resp.read())
            conn.close()
            status = result.get("status")
            if status == "granted":
                sys.stdout.write("\n")
                save_credential(result["credential"], result.get("username", ""))
                sys.stdout.write(f"Logged in as {result.get('username', 'unknown')}.\n")
                sys.stdout.write(f"Credential saved to {CREDENTIALS_PATH}\n")
                return
            if status == "expired":
                raise RuntimeError("Login expired. Run --login again.")
        else:
            conn.close()

    raise RuntimeError("Login timed out. Run --login again.")



def write_if_changed(file_path, content):
    existed = os.path.exists(file_path)
    if existed:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                if f.read() == content:
                    return {"path": file_path, "action": "unchanged"}
        except OSError:
            pass
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return {"path": file_path, "action": "updated" if existed else "created"}


def download_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": user_agent()})
    with urllib.request.urlopen(req, timeout=15) as resp:
        if resp.status != 200:
            raise ValueError(f"Could not download {url}: HTTP {resp.status}")
        return resp.read()


def download_skill(url):
    return download_url(url).decode("utf-8")


def exchange_install_token(api_base, token):
    """Exchange a one-time install token (embedded in the install command) for a
    long-lived CLI credential and save it. No separate --login step needed."""
    parsed = urllib.parse.urlparse(api_base)
    is_https = parsed.scheme == "https"
    host = parsed.hostname
    port = parsed.port or (443 if is_https else 80)
    conn_cls = http.client.HTTPSConnection if is_https else http.client.HTTPConnection

    body = json.dumps({"token": token}).encode("utf-8")
    conn = conn_cls(host, port, timeout=30)
    try:
        conn.request(
            "POST",
            f"{parsed.path}/api/cli/install-token/exchange",
            body=body,
            headers={
                "User-Agent": user_agent(),
                "Content-Type": "application/json",
                "Content-Length": str(len(body)),
            },
        )
        resp = conn.getresponse()
        if resp.status != 200:
            err = resp.read(200).decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Install token exchange failed: HTTP {resp.status}{': ' + err if err else ''}"
            )
        data = json.loads(resp.read())
    finally:
        conn.close()

    credential = data.get("credential")
    if not credential:
        raise RuntimeError("Install token exchange returned no credential.")
    username = data.get("username", "")
    save_credential(credential, username)
    return username


def find_session_trace():
    """Locate the current agent run's trace file from the host's session env var.

    Returns (trace_path_or_None, session_id_or_None, agent_type_or_None).
    Claude Code stores traces at ~/.claude/projects/<slug>/<CLAUDE_CODE_SESSION_ID>.jsonl;
    Codex stores them at ~/.codex/sessions/<Y>/<M>/<D>/rollout-*-<CODEX_THREAD_ID>.jsonl.
    """
    home = os.path.expanduser("~")
    claude_sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()
    codex_tid = os.environ.get("CODEX_THREAD_ID", "").strip()

    if claude_sid:
        claude_home = os.environ.get("CLAUDE_CONFIG_DIR", "").strip() or os.path.join(home, ".claude")
        projects = os.path.join(claude_home, "projects")
        target = f"{claude_sid}.jsonl"
        for root, _dirs, files in os.walk(projects):
            if target in files:
                return os.path.join(root, target), claude_sid, "claude-code"
        return None, claude_sid, "claude-code"

    if codex_tid:
        codex_home = os.environ.get("CODEX_HOME", "").strip() or os.path.join(home, ".codex")
        sessions = os.path.join(codex_home, "sessions")
        for root, _dirs, files in os.walk(sessions):
            for name in files:
                if codex_tid in name and name.endswith(".jsonl"):
                    return os.path.join(root, name), codex_tid, "codex"
        return None, codex_tid, "codex"

    return None, None, None


def submit_trace(api_base, agent, trace_bytes):
    """POST a raw trace to the Directionally backend, authenticated with the CLI JWT.

    The backend stores it at v3/users/{email}/traces/{agent}/{sha256} and returns
    the storage key. `agent` is "claude" or "codex"."""
    parsed = urllib.parse.urlparse(api_base)
    is_https = parsed.scheme == "https"
    host = parsed.hostname
    port = parsed.port or (443 if is_https else 80)
    conn_cls = http.client.HTTPSConnection if is_https else http.client.HTTPConnection

    path = f"{parsed.path}/submit_trace?agent={urllib.parse.quote(agent, safe='')}"
    conn = conn_cls(host, port, timeout=120)
    try:
        conn.request(
            "POST",
            path,
            body=trace_bytes,
            headers={
                "Content-Type": "application/x-ndjson",
                "User-Agent": user_agent(),
                "Content-Length": str(len(trace_bytes)),
                **auth_headers(),
            },
        )
        resp = conn.getresponse()
        status = resp.status
        body = resp.read()
    finally:
        conn.close()

    if status == 401:
        _emit_login_needed(api_base)
    if status < 200 or status >= 300:
        err = body.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"submit_trace failed: HTTP {status}{': ' + err if err else ''}")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {}


def cmd_upload(api_base, flags):
    """Upload the current session's raw trace to the Directionally backend.

    Used when the user explicitly asks to share the session for review. Requires
    CLAUDE_CODE_SESSION_ID or CODEX_THREAD_ID in env to locate the trace."""
    trace_path, session_id, agent_type = find_session_trace()
    if not session_id:
        fail("upload: neither CLAUDE_CODE_SESSION_ID nor CODEX_THREAD_ID is set; "
             "cannot identify the session trace.")
    if not trace_path or not os.path.exists(trace_path):
        fail(f"upload: could not find a trace file for {agent_type} session {session_id}.")

    # Backend expects "claude" or "codex"; CLAUDE maps to claude-code internally.
    agent = "claude" if agent_type == "claude-code" else agent_type

    with open(trace_path, "rb") as f:
        trace_bytes = f.read()

    result = submit_trace(api_base, agent, trace_bytes)
    write_ndjson({
        "kind": "uploaded",
        "agent": agent,
        "session_id": session_id,
        "trace": trace_path,
        "hash": result.get("hash"),
        "key": result.get("key"),
        "received_at": now_iso(),
    })


def cmd_setup(flags):
    agent_type = flags.get("setup")
    if agent_type is True:
        agent_type = None

    # A one-time token embedded in the install command (DIR-83): exchange it for a
    # CLI credential before doing anything else, so identity is set up in one command.
    token = flags.get("token")
    if token and token is not True:
        username = exchange_install_token(get_api_base(), token)
        sys.stdout.write(
            f"Authenticated as {username}.\n" if username else "Authenticated.\n"
        )

    # Expected sha256 of the directionally.py we are about to download, baked into
    # the install command by the trusted backend. Optional, but when present every
    # downloaded script is verified against it before being installed.
    script_hash = flags.get("script_hash")
    if script_hash is True or script_hash == "":
        script_hash = None

    skill_url = os.environ.get("DIRECTIONALLY_SKILL_URL", DEFAULT_SKILL_URL)
    skill_body = download_skill(skill_url)
    # The downloaded SKILL.md must match what this script expects (hardcoded).
    verify_download("SKILL.md", skill_body.encode("utf-8"), SKILL_SHA256)

    global_dir = _global_skills_dir(agent_type) if agent_type else None
    if agent_type and not global_dir:
        raise ValueError(f"Unknown agent type: {agent_type!r}. Supported: claude-code, claude-desktop, codex, codex-desktop, cursor, cursor-desktop.")

    files = []

    if global_dir:
        skill_dest = os.path.join(global_dir, "directionally", "SKILL.md")
        script_dest = os.path.join(global_dir, "directionally", "scripts", "directionally.py")

        script_url = os.environ.get("DIRECTIONALLY_SCRIPT_URL", DEFAULT_SCRIPT_URL)
        script_body = download_url(script_url)
        if script_hash:
            verify_download("directionally.py", script_body, script_hash)

        files.append({**write_if_changed(skill_dest, skill_body), "abs": skill_dest})
        files.append({**write_if_changed(script_dest, script_body.decode("utf-8")), "abs": script_dest})
        # Make the script directly executable so SKILL.md can invoke it via its
        # shebang (scripts/directionally.py …) without a python3 prefix.
        try:
            os.chmod(script_dest, 0o755)
        except OSError:
            pass

        lines = [f"Agent:  {agent_type}", f"Global: {global_dir}", ""]
        for f in files:
            lines.append(f"  {f['action']:<9} {f['abs']}")
        sys.stdout.write("\n".join(lines) + "\n")
    else:
        # No agent type: install into current project directory (legacy behaviour)
        cwd = flags.get("cwd")
        if not cwd or cwd is True:
            cwd = os.getcwd()
        target_root = os.path.realpath(cwd)

        files = [
            {**write_if_changed(os.path.join(target_root, SKILL_RELATIVE), skill_body), "rel": SKILL_RELATIVE},
            {**write_if_changed(os.path.join(target_root, SKILL_CLAUDE_RELATIVE), skill_body), "rel": SKILL_CLAUDE_RELATIVE},
        ]

        lines = [f"Root: {target_root}", ""]
        for f in files:
            lines.append(f"  {f['action']:<9} {f['rel']}")
        sys.stdout.write("\n".join(lines) + "\n")


def open_first_session(api_base, initial_message):
    project_id = "v3/me"
    parsed = urllib.parse.urlparse(api_base)
    is_https = parsed.scheme == "https"
    host = parsed.hostname
    port = parsed.port or (443 if is_https else 80)
    path = f"{parsed.path}/sessions/{urllib.parse.quote(project_id, safe='')}"

    conn_cls = http.client.HTTPSConnection if is_https else http.client.HTTPConnection
    conn = conn_cls(host, port, timeout=120)

    body_parts = []
    if initial_message:
        body_parts.append(json.dumps(initial_message) + "\n")
    body = "".join(body_parts).encode("utf-8")

    conn.request(
        "POST",
        path,
        body=body or None,
        headers={
            "Content-Type": "application/x-ndjson",
            "Accept": "application/x-ndjson",
            "User-Agent": user_agent(),
            "Content-Length": str(len(body)),
            **auth_headers(),
        },
    )
    resp = conn.getresponse()

    if resp.status == 401:
        resp.read()
        conn.close()
        _emit_login_needed(api_base)

    if resp.status < 200 or resp.status >= 300:
        err_body = resp.read(500).decode("utf-8", errors="replace")
        write_ndjson({
            "kind": "bridge_error",
            "error": f"HTTP {resp.status} {resp.reason}{': ' + err_body if err_body else ''}",
            "received_at": now_iso(),
        })
        sys.exit(1)

    sequence = 0

    while True:
        raw = resp.readline()
        if not raw:
            break
        line = raw.decode("utf-8", errors="replace").strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("kind") == "event_received" and isinstance(obj.get("sequence"), int):
            sequence = obj["sequence"]
            continue
        if obj.get("kind") == "session_started":
            write_ndjson({
                "kind": "bridge_started",
                "api_base": api_base,
                "session_id": obj["session_id"],
                "sequence": sequence,
                "received_at": now_iso(),
            })
            conn.close()
            return
        write_ndjson(obj)

    write_ndjson({
        "kind": "bridge_error",
        "error": "session stream ended before session_started",
        "received_at": now_iso(),
    })
    sys.exit(1)


def send_ops(session_id, api_base, ops):
    parsed = urllib.parse.urlparse(api_base)
    is_https = parsed.scheme == "https"
    host = parsed.hostname
    port = parsed.port or (443 if is_https else 80)
    path = f"{parsed.path}/session/resume/{urllib.parse.quote(session_id, safe='')}"
    body = ("\n".join(json.dumps(op) for op in ops) + "\n").encode("utf-8")

    conn_cls = http.client.HTTPSConnection if is_https else http.client.HTTPConnection
    conn = conn_cls(host, port, timeout=30)
    try:
        conn.request(
            "POST",
            path,
            body=body,
            headers={
                "Content-Type": "application/x-ndjson",
                "User-Agent": user_agent(),
                "Content-Length": str(len(body)),
                **auth_headers(),
            },
        )
        resp = conn.getresponse()
        if resp.status < 200 or resp.status >= 300:
            err_body = resp.read(200).decode("utf-8", errors="replace")
            sys.stderr.write(f"directionally: ops not sent: HTTP {resp.status}{': ' + err_body if err_body else ''}\n")
        else:
            resp.readline()  # read first line then close; stream stays open server-side
    except Exception as e:
        sys.stderr.write(f"directionally: ops not sent: {e}\n")
    finally:
        conn.close()


def poll_session(api_base, flags):
    project_id = "v3/me"
    session_id = flags.get("session", "")
    if session_id is True or not session_id:
        raise ValueError("--session requires a session id.")
    session_id = str(session_id).strip()

    after = number_flag(flags.get("after"), 0, "--after")
    wait = number_flag(flags.get("wait"), 0, "--wait")
    limit = number_flag(flags.get("limit"), 100, "--limit")

    ops = []
    for arg in flags.get("_", []):
        try:
            ops.append(json.loads(arg))
        except json.JSONDecodeError:
            pass
    if ops:
        send_ops(session_id, api_base, ops)

    params = urllib.parse.urlencode({"after": after, "wait": wait, "limit": limit})
    url = (
        f"{api_base}/sessions/{urllib.parse.quote(project_id, safe='')}"
        f"/{urllib.parse.quote(session_id, safe='')}/events.ndjson?{params}"
    )
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/x-ndjson", "User-Agent": user_agent(), **auth_headers()},
    )
    try:
        with urllib.request.urlopen(req, timeout=wait + 10) as resp:
            text = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} {e.reason}{chr(10) + err_body if err_body else ''}")

    if text:
        if not text.endswith("\n"):
            text += "\n"
        sys.stdout.write(text)
        sys.stdout.flush()
    count = len([l for l in text.strip().splitlines() if l.strip()]) if text.strip() else 0
    write_ndjson({"kind": "polled", "count": count, "after": after, "received_at": now_iso()})


def usage(code=0):
    msg = "\n".join([
        "Usage:",
        "  directionally.py --login",
        "  directionally.py --setup <agent-type> [--token <tok>] [--script-hash <sha256>]  # global install (claude-code, codex, cursor, …)",
        "  directionally.py --setup [--cwd <path>] # project install (no agent type)",
        "  directionally.py upload  # gist the current session trace (needs CLAUDE_CODE_SESSION_ID/CODEX_THREAD_ID)",
        "  directionally.py --first --subsession-id <id> <text>",
        "  directionally.py --session <session_id> [--after <seq>] [--wait <secs>] [--limit <n>]",
        "",
        "  --setup verifies the downloaded SKILL.md against the hardcoded SKILL_SHA256,",
        "  and (when --script-hash is given) the downloaded directionally.py against it.",
        "",
        "Env:",
        f"  DIRECTIONALLY_API_BASE   Override API base URL (default: {DEFAULT_API_BASE})",
        "  DIRECTIONALLY_SKILL_URL  Override SKILL.md source URL used by --setup",
    ])
    (sys.stdout if code == 0 else sys.stderr).write(msg + "\n")
    sys.exit(code)


def main():
    ping_dir = os.path.join(os.path.expanduser("~"), ".directionally")
    os.makedirs(ping_dir, exist_ok=True)
    with open(os.path.join(ping_dir, "ping"), "w") as _f:
        _f.write(str(random.randint(0, 2**31 - 1)))

    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        usage(0)

    try:
        flags = parse_args(args)

        if flags.get("setup"):
            cmd_setup(flags)
            return

        api_base = get_api_base()
        try_redeem_pending_login(api_base)

        if flags.get("_") and flags["_"][0] == "upload":
            cmd_upload(api_base, flags)
            return

        if flags.get("login"):
            cmd_login(api_base)
            return

        if flags.get("first"):
            subsession_id = flags.get("subsession_id")
            if subsession_id is True:
                subsession_id = None
            text = " ".join(flags["_"]) if flags.get("_") else None
            initial_message = (
                {"op": "elaborating", "subsession_id": subsession_id, "text": text}
                if subsession_id and text
                else None
            )
            open_first_session(api_base, initial_message)
            return

        if flags.get("session"):
            poll_session(api_base, flags)
            return

        usage(1)

    except ValueError as e:
        fail(str(e))
    except RuntimeError as e:
        fail(str(e))
    except Exception as e:
        fail(str(e))


if __name__ == "__main__":
    main()
