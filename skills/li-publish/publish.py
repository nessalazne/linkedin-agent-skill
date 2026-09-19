#!/usr/bin/env python3
"""
publish.py - post or schedule an approved LinkedIn draft through Blotato.

Blotato is an approved LinkedIn partner, so this is the one route to a personal
profile that does not involve browser automation. The script never decides to
post: the skill that calls it has already collected an explicit "publish".

    python3 publish.py draft.txt                       # post now
    python3 publish.py draft.txt --schedule next_slot  # Blotato's next free slot
    python3 publish.py draft.txt --schedule 2026-09-22T22:15:00Z
    python3 publish.py draft.txt --image cover.png     # upload an image first
    python3 publish.py draft.txt --dry-run             # print the payload, no network
    python3 publish.py --check                         # confirm the pinned account is LinkedIn

Keys come from ~/.claude/linkedin/.env (or --env PATH), falling back to the
process environment:

    BLOTATO_API_KEY=...
    BLOTATO_ACCOUNT_LINKEDIN=4441

Only `requests` is needed beyond the standard library.
"""

import argparse
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("publish.py needs the requests package: pip install requests")

MCP_URL = "https://mcp.blotato.com/mcp"
DEFAULT_ENV = Path.home() / ".claude" / "linkedin" / ".env"
LOG_PATH = Path.home() / ".claude" / "linkedin" / "log.md"
LINKEDIN_LIMIT = 3000
TERMINAL = ("published", "scheduled", "failed", "completed")


# ── env ───────────────────────────────────────────────────────────────────────

def load_env(path: Path):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def require(key: str) -> str:
    val = os.environ.get(key, "").strip()
    if not val:
        sys.exit(f"{key} is not set. Put it in {DEFAULT_ENV} or pass --env.")
    return val


# ── Blotato MCP ───────────────────────────────────────────────────────────────

_rpc_id = 0


def _blotato_headers() -> dict:
    return {
        "blotato-api-key": require("BLOTATO_API_KEY"),
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }


def _parse_rpc_body(text: str) -> dict:
    text = text.strip()
    if text.startswith("{"):
        return json.loads(text)
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload and payload != "[DONE]":
                return json.loads(payload)
    raise RuntimeError(f"Unparseable MCP response: {text[:200]}")


def _rpc(tool: str, arguments: dict, timeout: int = 60):
    global _rpc_id
    _rpc_id += 1
    resp = requests.post(
        MCP_URL,
        headers=_blotato_headers(),
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
            "id": _rpc_id,
        },
        timeout=timeout,
    )
    if not resp.ok:
        raise RuntimeError(f"Blotato MCP {tool} HTTP {resp.status_code}: {resp.text[:300]}")
    data = _parse_rpc_body(resp.text)
    if data.get("error"):
        raise RuntimeError(f"Blotato MCP {tool} error: {data['error']}")
    result = data.get("result", {})
    if result.get("isError"):
        raise RuntimeError(f"Blotato MCP {tool} tool error: {result}")
    content = result.get("content") or []
    if content and content[0].get("type") == "text":
        raw = content[0]["text"]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return result


def upload_media(path: Path) -> str:
    size_mb = path.stat().st_size / 1024 / 1024
    print(f"Uploading {path.name} ({size_mb:.1f} MB) to Blotato...")
    res = _rpc("blotato_create_presigned_upload_url", {"filename": path.name}, timeout=30)
    presigned = res.get("presignedUrl") or res.get("uploadUrl")
    public = res.get("publicUrl") or res.get("url")
    if not presigned or not public:
        sys.exit(f"Blotato presigned URL response missing expected fields: {res}")
    put = requests.put(presigned, data=path.read_bytes(), timeout=600)
    if not put.ok:
        sys.exit(f"Upload PUT failed {put.status_code}: {put.text[:200]}")
    print("Upload complete.")
    return public


def _poll_until_terminal(submission_id: str, max_wait: int = 600) -> dict:
    deadline = time.time() + max_wait
    last = {}
    while time.time() < deadline:
        time.sleep(20)
        try:
            data = _rpc("blotato_get_post_status", {"postSubmissionId": str(submission_id)})
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        last = data
        status = str(data.get("status", "")).lower()
        if status in TERMINAL:
            return data
        print(f"  status: {status or 'in-progress'} ...", flush=True)
    last.setdefault("status", "timeout")
    return last


# ── account check ─────────────────────────────────────────────────────────────

def _accounts() -> list:
    res = _rpc("blotato_list_accounts", {}, timeout=30)
    if isinstance(res, dict):
        for key in ("accounts", "items", "data"):
            if isinstance(res.get(key), list):
                return res[key]
    return res if isinstance(res, list) else []


def check_account(account_id: str) -> dict:
    for acc in _accounts():
        if str(acc.get("id")) == str(account_id):
            return acc
    return {}


# ── helpers ───────────────────────────────────────────────────────────────────

def read_text(source: str) -> str:
    text = sys.stdin.read() if source == "-" else Path(source).read_text()
    return text.strip("\n")


def guard_length(text: str) -> str:
    if len(text) <= LINKEDIN_LIMIT:
        return text
    cut = text[: LINKEDIN_LIMIT - 1].rsplit(" ", 1)[0]
    print(
        f"WARNING: draft is {len(text):,} characters, LinkedIn allows {LINKEDIN_LIMIT:,}. "
        f"Truncated at a word boundary to {len(cut):,}. Shorten it and rerun if that matters.",
        file=sys.stderr,
    )
    return cut


def build_payload(account_id: str, text: str, schedule: str, media_url: str | None) -> dict:
    args = {"accountId": account_id, "platform": "linkedin", "text": text}
    if media_url:
        args["mediaUrls"] = [media_url]
    if schedule == "next_slot":
        args["useNextFreeSlot"] = True
    elif schedule and schedule != "now":
        # Blotato wants ISO 8601 UTC, e.g. 2026-09-22T22:15:00Z
        try:
            dt.datetime.fromisoformat(schedule.replace("Z", "+00:00"))
        except ValueError:
            sys.exit(f"--schedule must be now, next_slot, or an ISO 8601 UTC time, got {schedule!r}")
        args["scheduledTime"] = schedule
    return args


def append_log(text: str, status: str, url: str, schedule: str):
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        first = text.strip().splitlines()[0][:140] if text.strip() else ""
        stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        with LOG_PATH.open("a") as fh:
            fh.write(f"- {stamp} | li-publish | {status} | {schedule} | {url or '-'} | {first}\n")
    except OSError as exc:
        print(f"(could not write {LOG_PATH}: {exc})", file=sys.stderr)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Post or schedule a LinkedIn draft through Blotato.")
    ap.add_argument("draft", nargs="?", help="path to the approved draft, or - for stdin")
    ap.add_argument("--schedule", default="now", help="now (default), next_slot, or ISO 8601 UTC time")
    ap.add_argument("--image", type=Path, help="image to upload and attach")
    ap.add_argument("--env", type=Path, default=DEFAULT_ENV, help=f"env file (default {DEFAULT_ENV})")
    ap.add_argument("--dry-run", action="store_true", help="print the payload and exit without any network call")
    ap.add_argument("--check", action="store_true", help="confirm the pinned account is a LinkedIn account and exit")
    ap.add_argument("--max-wait", type=int, default=600, help="seconds to poll for a terminal status")
    args = ap.parse_args()

    load_env(args.env)

    if args.check:
        account_id = require("BLOTATO_ACCOUNT_LINKEDIN")
        acc = check_account(account_id)
        if not acc:
            sys.exit(f"Account {account_id} not found in this Blotato workspace.")
        platform = str(acc.get("platform", "")).lower()
        name = acc.get("fullname") or acc.get("displayName") or acc.get("username") or "?"
        if platform != "linkedin":
            sys.exit(f"Account {account_id} is {platform or 'unknown'}, not LinkedIn ({name}).")
        print(f"OK: account {account_id} is LinkedIn ({name}).")
        return

    if not args.draft:
        ap.error("draft path is required unless --check is given")

    text = guard_length(read_text(args.draft))
    if not text.strip():
        sys.exit("The draft is empty.")

    account_id = os.environ.get("BLOTATO_ACCOUNT_LINKEDIN", "").strip() or ("<BLOTATO_ACCOUNT_LINKEDIN>" if args.dry_run else require("BLOTATO_ACCOUNT_LINKEDIN"))

    if args.dry_run:
        media = f"<upload of {args.image}>" if args.image else None
        print(json.dumps(build_payload(account_id, text, args.schedule, media), indent=2, ensure_ascii=False))
        return

    media_url = None
    if args.image:
        if not args.image.exists():
            sys.exit(f"Image not found: {args.image}")
        media_url = upload_media(args.image)

    payload = build_payload(account_id, text, args.schedule, media_url)
    print(f"Submitting to LinkedIn (account {account_id}, schedule={args.schedule})...")
    try:
        res = _rpc("blotato_create_post", payload, timeout=60)
    except Exception as exc:
        append_log(text, "failed", "", args.schedule)
        sys.exit(f"FAILED {exc}")

    sub_id = None
    if isinstance(res, dict):
        sub_id = res.get("postSubmissionId") or res.get("submissionId") or res.get("id")
    if not sub_id:
        append_log(text, "submitted", "", args.schedule)
        print(f"SUBMITTED (no submission id returned): {str(res)[:300]}")
        return

    print(f"Submission {sub_id}, polling...")
    final = _poll_until_terminal(sub_id, max_wait=args.max_wait)
    status = str(final.get("status", "")).lower()
    url = final.get("publicUrl") or final.get("url") or ""
    append_log(text, status, url, args.schedule)

    if status in ("published", "completed"):
        print(f"PUBLISHED {url or '(no public URL returned yet, check Blotato)'}")
    elif status == "scheduled":
        when = final.get("scheduledTime") or payload.get("scheduledTime") or "next free slot"
        print(f"SCHEDULED {when}")
    else:
        err = final.get("errorMessage") or final.get("error") or json.dumps(final)[:300]
        sys.exit(f"FAILED {status}: {err}")


if __name__ == "__main__":
    main()
