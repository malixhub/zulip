#!/usr/bin/env python3
"""Import an ASDPolicy review manifest into an EXISTING Zulip organization.

SAFE BY DEFAULT: preview and validation only. Requires --execute to post.
Only one migration account sends messages; original author/date remain in text.
The Zulip message send API cannot backdate the message or impersonate authors.

Workflow:
  1. python3 prepare_archive.py --source-dir /path/to/fresh-export
  2. python3 import_existing_org.py --manifest asdpolicy-import-review/messages.jsonl
  3. Set ZULIP_EMAIL, ZULIP_API_KEY in the process environment.
  4. python3 import_existing_org.py --manifest ... --execute --max-messages 10
  5. Review Zulip, then repeat without max-messages.

The script creates NO channels. Create nine target channels and subscribe the
migration account before --execute. A durable checkpoint prevents re-sending
already acknowledged source IDs on later runs. It does not dedupe an existing
Zulip archive created by another tool. Back up both systems before execution.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import base64

HOST = "https://chat.asdpolicy.org"
def read_manifest(path):
    records = []
    seen = set()
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        rec = json.loads(line)
        srcid = str(rec.get("source_id", ""))
        if not srcid or srcid in seen:
            raise ValueError(f"Missing or duplicate source_id at manifest line {idx}")
        seen.add(srcid)
        for field in ["channel", "topic", "content", "original_date", "original_author"]:
            if not rec.get(field):
                raise ValueError(f"Missing {field} at line {idx}")
        records.append(rec)
    return records

def api(method, path, email, key, data=None):
    url = HOST + "/api/v1/" + path
    payload = None if data is None else urlencode(data).encode("utf-8")
    auth = base64.b64encode(f"{email}:{key}".encode()).decode()
    request = Request(url, data=payload, method=method, headers={
        "Authorization": "Basic " + auth,
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "ASDPolicyHistoricalArchive/1.0",
    })
    with urlopen(request, timeout=30) as resp:
        output = json.loads(resp.read().decode("utf-8"))
    if output.get("result") != "success":
        raise RuntimeError(f"Zulip API rejected request: {output.get('msg', 'unknown error')}")
    return output

def checkpoint_load(path):
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Invalid checkpoint: expected JSON object")
    return data

def checkpoint_save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, default=Path("asdpolicy-import-checkpoint.json"))
    parser.add_argument("--execute", action="store_true", help="Actually send archive records")
    parser.add_argument("--max-messages", type=int, default=0, help="Only send N new messages this run (0 = all)")
    parser.add_argument("--delay", type=float, default=0.5, help="Seconds between messages")
    args = parser.parse_args()
    records = read_manifest(args.manifest)
    checkpoint = checkpoint_load(args.checkpoint)
    pending = [r for r in records if r["source_id"] not in checkpoint]
    print("Archive records:", len(records))
    print("Already acknowledged:", len(records) - len(pending))
    print("Pending:", len(pending))
    print("Pending by channel:", dict(collections.Counter(r["channel"] for r in pending)))
    if not args.execute:
        print("DRY RUN. No Zulip messages or channels were changed.")
        print("Verify message content, authors and timestamps in the manifest first.")
        return

    email = os.getenv("ZULIP_EMAIL")
    key = os.getenv("ZULIP_API_KEY")
    if not email or not key:
        parser.error("ZULIP_EMAIL and ZULIP_API_KEY are required for --execute. Never paste keys into chat.")
    channels_result = api("GET", "streams", email, key)
    existing_channels = {c["name"] for c in channels_result.get("streams", [])}
    missing = sorted({r["channel"] for r in records} - existing_channels)
    if missing:
        parser.error("Create these channels before importing: " + ", ".join(missing))
    # First run should be deliberately limited to 10 messages for approval.
    if not checkpoint and args.max_messages == 0:
        parser.error("First execution requires --max-messages 10 (or another positive number), to preview Zulip output.")
    limit = args.max_messages if args.max_messages > 0 else len(pending)
    sent = 0
    for r in pending[:limit]:
        try:
            out = api("POST", "messages", email, key, {
                "type": "stream",
                "to": r["channel"],
                "topic": r["topic"],
                "content": r["content"],
            })
        except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
            print(f"Stopped before completing record {r['source_id']}: {exc}", file=sys.stderr)
            print("Review last posted message: a timeout may have posted successfully without a response.", file=sys.stderr)
            sys.exit(2)
        checkpoint[r["source_id"]] = {
            "zulip_message_id": out.get("id"),
            "channel": r["channel"],
            "original_date": r["original_date"],
        }
        checkpoint_save(args.checkpoint, checkpoint)
        sent += 1
        if sent < limit:
            time.sleep(max(0, args.delay))
    print(f"Posted {sent} archival messages. Checkpoint: {args.checkpoint}")
    print("Original historical timestamps and authors appear in message text, not Zulip's native sender/date fields.")

if __name__ == "__main__":
    main()
