#!/usr/bin/env python3
"""
fetch.py - read public LinkedIn data through Apify, for /li-engagers and /li-hooks.

Optional. Every skill in the pack works without it by asking you to paste the
text instead. With a token it fetches for you, using no-cookie actors, so your
LinkedIn login is never involved.

    python3 fetch.py --check                               # is the token valid?
    python3 fetch.py post URL                              # one post's text + stats
    python3 fetch.py engagers URL [URL ...] --max 100      # likers + commenters
    python3 fetch.py engagers URL --types likers --dry-run # show the plan, spend nothing
    python3 fetch.py engagers URL --from-file raw.json     # normalise a saved actor dump

Keys come from ~/.claude/linkedin/.env (or --env PATH), falling back to the
process environment:

    APIFY_TOKEN=apify_api_...

Standard library only. Actor choices and input shapes adapted from
sergebulaev/linkedin-skills (MIT).
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_ENV = Path.home() / ".claude" / "linkedin" / ".env"
API = "https://api.apify.com/v2"
POST_ACTOR = "apimaestro~linkedin-post-detail"
ENGAGERS_ACTOR = "scraping_solutions~linkedin-posts-engagers-likers-and-commenters-no-cookies"
ENGAGER_TYPES = ("likers", "commenters", "reshares")
COST_PER_ENGAGER = 0.005  # $5 per 1,000 records
COST_PER_POST = 0.001     # $1 per 1,000 records


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


def token() -> str:
    val = os.environ.get("APIFY_TOKEN", "").strip()
    if not val:
        sys.exit(
            f"APIFY_TOKEN is not set. Put it in {DEFAULT_ENV}, or paste the text "
            "into Claude instead. The skills work either way."
        )
    return val


# ── Apify ─────────────────────────────────────────────────────────────────────


def call(method: str, path: str, payload=None, timeout: float = 180.0):
    # The token goes in the Authorization header, never the URL, so it stays
    # out of shell history, proxy logs and error traces.
    req = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        method=method,
        headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        sys.exit(f"Apify HTTP {e.code}: {e.read()[:400].decode(errors='replace')}")
    except urllib.error.URLError as e:
        sys.exit(f"Could not reach Apify: {e.reason}")
    if isinstance(data, dict) and "error" in data:
        sys.exit(f"Apify actor failed: {data['error']}")
    return data


def run_actor(actor: str, payload: dict) -> list:
    data = call("POST", f"/acts/{actor}/run-sync-get-dataset-items", payload)
    return data if isinstance(data, list) else []


# ── Normalisers ───────────────────────────────────────────────────────────────


def normalise_post(raw: dict) -> dict:
    # apimaestro nests everything; flatten it to what the skills read. Inputs
    # that are already flat (a saved, normalised dump) pass through.
    if "post" not in raw and "text" in raw:
        return {k: v for k, v in raw.items() if not k.startswith("_")}
    post, author, stats = raw.get("post") or {}, raw.get("author") or {}, raw.get("stats") or {}
    return {
        "url": post.get("url"),
        "text": post.get("text"),
        "authorName": author.get("name"),
        "authorHeadline": author.get("headline"),
        "authorProfileUrl": author.get("profile_url"),
        "numLikes": stats.get("total_reactions"),
        "numComments": stats.get("comments"),
        "numShares": stats.get("shares"),
        "postedAt": (post.get("created_at") or {}).get("date"),
    }


def normalise_engager(raw: dict, kind: str, post_url: str) -> dict:
    return {
        "type": raw.get("type") or kind,
        "name": raw.get("name"),
        "subtitle": raw.get("subtitle"),
        "profile": raw.get("url_profile"),
        "comment": raw.get("content"),
        "post": post_url,
    }


def dedupe(rows: list) -> list:
    """One row per person across every post, with what they did and where."""
    people = {}
    for r in rows:
        key = r["profile"] or r["name"]
        p = people.setdefault(key, {**r, "types": set(), "posts": set()})
        p["types"].add(r["type"])
        p["posts"].add(r["post"])
        if r.get("comment") and not p.get("comment"):
            p["comment"] = r["comment"]
    out = []
    for p in people.values():
        p["types"] = sorted(p.pop("types"))
        p["posts"] = sorted(p.pop("posts"))
        p["posts_engaged"] = len(p["posts"])
        p.pop("type", None)
        p.pop("post", None)
        out.append(p)
    return sorted(out, key=lambda p: (-p["posts_engaged"], "commenters" not in p["types"]))


# ── Commands ──────────────────────────────────────────────────────────────────


def cmd_check(_):
    me = call("GET", "/users/me", timeout=30).get("data") or {}
    print(f"OK  Apify user: {me.get('username')}  plan: {(me.get('plan') or {}).get('id', '?')}")


def cmd_post(a):
    if a.from_file:
        raw = json.loads(Path(a.from_file).read_text())
        raw = raw[0] if isinstance(raw, list) else raw
    else:
        items = run_actor(POST_ACTOR, {"post_urls": [a.url]})
        if not items:
            sys.exit(f"No post returned for {a.url}. It may be private or removed. Paste the text instead.")
        raw = items[0]
    post = normalise_post(raw)
    if not post.get("text") and not post.get("authorName"):
        sys.exit("Post not retrievable (private, removed or login-walled). Paste the text instead.")
    emit(post, a.out)


def cmd_engagers(a):
    types = tuple(dict.fromkeys(t.strip() for t in a.types.split(",") if t.strip()))
    bad = [t for t in types if t not in ENGAGER_TYPES]
    if not types or bad:
        sys.exit(f"--types must be a comma list from {', '.join(ENGAGER_TYPES)}")
    # The actor answers for one audience per run, so the budget is split per
    # type and per post. Total spend is capped by --max, whatever you ask for.
    per_run = max(1, a.max // (len(types) * len(a.urls)))
    runs = [(u, t) for u in a.urls for t in types]
    est = per_run * len(runs) * COST_PER_ENGAGER
    if not a.from_file:
        print(f"{len(runs)} actor run(s), up to {per_run} records each, "
              f"est. max ${est:.2f}", file=sys.stderr)

    if a.dry_run:
        for u, t in runs:
            print(json.dumps({"actor": ENGAGERS_ACTOR,
                              "input": {"urls": [u], "resultsLimit": per_run, "type": t}}))
        return

    rows = []
    if a.from_file:
        raw = json.loads(Path(a.from_file).read_text())
        rows = [normalise_engager(r, r.get("type", "likers"), r.get("post_Link") or a.urls[0])
                for r in raw if isinstance(r, dict)]
    else:
        for u, t in runs:
            items = run_actor(ENGAGERS_ACTOR, {"urls": [u], "resultsLimit": per_run, "type": t})
            rows += [normalise_engager(r, t, u) for r in items if isinstance(r, dict)]
            print(f"  {t:<11} {len(items):>4}  {u}", file=sys.stderr)
    people = dedupe(rows)
    print(f"{len(rows)} records, {len(people)} people, "
          f"{sum(p['posts_engaged'] > 1 for p in people)} on 2+ posts", file=sys.stderr)
    emit(people, a.out)


def emit(data, out):
    text = json.dumps(data, indent=2, ensure_ascii=False)
    if out:
        Path(out).expanduser().write_text(text + "\n")
        print(f"wrote {out}", file=sys.stderr)
    else:
        print(text)


def main():
    ap = argparse.ArgumentParser(description="Read public LinkedIn data through Apify.")
    ap.add_argument("--env", default=str(DEFAULT_ENV))
    ap.add_argument("--check", action="store_true", help="validate APIFY_TOKEN and exit")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("post", help="fetch one post's text and stats")
    p.add_argument("url")
    p.add_argument("--out")
    p.add_argument("--from-file", help="normalise a saved actor dump instead of calling Apify")

    e = sub.add_parser("engagers", help="fetch the people who engaged with one or more posts")
    e.add_argument("urls", nargs="+")
    e.add_argument("--max", type=int, default=100, help="total records across all runs (default 100)")
    e.add_argument("--types", default="likers,commenters")
    e.add_argument("--out")
    e.add_argument("--dry-run", action="store_true", help="print the actor calls and cost, send nothing")
    e.add_argument("--from-file", help="normalise a saved actor dump instead of calling Apify")

    a = ap.parse_args()
    load_env(Path(a.env).expanduser())
    if a.check:
        return cmd_check(a)
    if a.cmd == "post":
        return cmd_post(a)
    if a.cmd == "engagers":
        return cmd_engagers(a)
    ap.print_help()


if __name__ == "__main__":
    main()
