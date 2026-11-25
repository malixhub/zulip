#!/usr/bin/env python3
"""Convert ASDPolicy Collaboratory JSON into a Zulip archive import manifest.

Default operation is OFFLINE and read-only: generate review files, no Zulip writes.
For an existing Zulip organization, standard send-message API cannot backdate messages
or impersonate historical authors. The manifest keeps the original author/time in
message text and source metadata, and marks seeded/agent content clearly.
"""
from __future__ import annotations
import argparse
import collections
import datetime as dt
import json
import pathlib
import urllib.request
import urllib.error

BASE = "https://raw.githubusercontent.com/malixhub/sharepro/main/asdpolicy/backend/v2/data/"
SOURCES = ["messages-archive-1.json", "messages.json"]
LABELS = {
    "seeded": "SIMULATED / SEEDED HISTORICAL CONTENT",
    "agent": "AI-AGENT ARCHIVE CONTENT",
}
def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))

def timestamp(s: str) -> str:
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, AttributeError):
        return "Unrecorded date"

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-dir", type=pathlib.Path, help="Folder containing exported JSON data. Preferred for up-to-date data.")
    ap.add_argument("--output", type=pathlib.Path, default=pathlib.Path("asdpolicy-import-review"))
    ap.add_argument("--allow-repository-snapshot", action="store_true", help="Fetch GitHub's public repository copy; may be older than live PHP host.")
    args = ap.parse_args()
    if not args.source_dir and not args.allow_repository_snapshot:
        ap.error("Provide --source-dir with a fresh export, or explicitly use --allow-repository-snapshot.")
    args.output.mkdir(parents=True, exist_ok=True)

    def fetch(name):
        if args.source_dir:
            return load(args.source_dir / name)
        with urllib.request.urlopen(BASE + name, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    channels = fetch("channels.json")
    data = []
    for src in SOURCES:
        for m in fetch(src):
            m = dict(m)
            m["_source_file"] = src
            data.append(m)
    seen = set()
    out = []
    for m in sorted(data, key=lambda m: (m.get("created_at", ""), m.get("id", ""))):
        identifier = str(m.get("id", ""))
        if not identifier:
            raise ValueError("Message without source ID")
        if identifier in seen:
            continue
        seen.add(identifier)
        channel = str(m.get("channel", "general"))
        day = str(m.get("created_at", "unknown"))[:7]
        topic = f"Collaboratory archive | {day}"
        kind = str(m.get("kind", "unknown"))
        author = str(m.get("author", "Unknown author"))
        preface = f"**[ARCHIVED {LABELS.get(kind, kind.upper())}]**\n"
        preface += f"**Original author/agent:** {author}\n"
        preface += f"**Original date:** {timestamp(str(m.get('created_at','')))}\n"
        preface += f"**Source record ID:** `{identifier}`\n\n"
        body = str(m.get("text", ""))
        if not body.strip():
            continue
        out.append({
            "source_id": identifier,
            "source_file": m["_source_file"],
            "channel": channel,
            "topic": topic,
            "original_author": author,
            "original_date": m.get("created_at"),
            "original_kind": kind,
            "content": preface + body,
        })
    with (args.output / "messages.jsonl").open("w", encoding="utf-8") as f:
        for m in out:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    (args.output / "channels.json").write_text(json.dumps(channels, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        backlog = fetch("backlog.json")
        (args.output / "backlog.json").write_text(json.dumps(backlog, indent=2, ensure_ascii=False), encoding="utf-8")
    except (FileNotFoundError, urllib.error.HTTPError):
        backlog = []
    stats = {
        "source": str(args.source_dir or BASE),
        "messages": len(out),
        "channels": collections.Counter(m["channel"] for m in out),
        "authors": collections.Counter(m["original_author"] for m in out),
        "kinds": collections.Counter(m["original_kind"] for m in out),
        "backlog_items": len(backlog),
        "import_performed": False,
        "notes": [
            "This is a review manifest, not a Zulip import executed against the server.",
            "Historical authors and timestamps cannot be preserved as native Zulip metadata through the standard send-message API.",
            "Seeded and AI-agent content remains clearly labeled.",
            "Only public repo snapshot if --allow-repository-snapshot was used; compare with live host export before importing.",
        ]
    }
    (args.output / "summary.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    print(f"Created files in {args.output.resolve()} (NO messages sent to Zulip).")

if __name__ == "__main__":
    main()
