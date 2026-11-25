#!/usr/bin/env python3
"""Offline validation of original Collaboratory records; never writes to Zulip."""
import argparse
import collections
import datetime as dt
import hashlib
import json
from pathlib import Path

FILES = ("messages-archive-1.json", "messages.json", "channels.json", "backlog.json")
def read(root):
    hashes, data = {}, {}
    for name in FILES:
        raw = (root / name).read_bytes()
        hashes[name] = hashlib.sha256(raw).hexdigest()
        data[name] = json.loads(raw)
        if not isinstance(data[name], list):
            raise ValueError(f"{name}: expected array")
    channels = {c["id"] for c in data["channels.json"]}
    records, duplicates = {}, []
    identities = collections.defaultdict(set)
    dates = {}
    for name in FILES[:2]:
        for m in data[name]:
            for key in ("id", "channel", "author", "role", "text", "created_at"):
                if not isinstance(m.get(key), str) or (key != "text" and not m[key]):
                    raise ValueError(f"{name}: invalid {key}")
            ident = m["id"]
            if m["channel"] not in channels:
                raise ValueError(f"{ident}: unknown channel")
            stamp = dt.datetime.fromisoformat(m["created_at"].replace("Z", "+00:00"))
            if stamp.utcoffset() is None:
                raise ValueError(f"{ident}: timezone missing")
            if ident in records:
                if records[ident] != m:
                    raise ValueError(f"{ident}: conflicting duplicate")
                duplicates.append(ident)
                continue
            records[ident] = m
            dates[ident] = stamp
            identities[m["author"]].add(m["role"])
    ordered = sorted(records, key=lambda i: (dates[i], i))
    report = {
        "hashes": hashes, "messages": len(records), "exact_duplicate_ids": duplicates,
        "channels": sorted(channels), "messages_by_channel": dict(collections.Counter(m["channel"] for m in records.values())),
        "identities": {k: sorted(v) for k,v in sorted(identities.items())},
        "first": dates[ordered[0]].isoformat() if ordered else None,
        "last": dates[ordered[-1]].isoformat() if ordered else None,
        "blank_ids": [i for i in ordered if not records[i]["text"].strip()],
        "backlog_items": len(data["backlog.json"]),
        "message_fields": sorted({k for m in records.values() for k in m}),
    }
    return records, report

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-dir", type=Path, required=True)
    p.add_argument("--compare-dir", type=Path, help="Fresh live-host snapshot to compare against source")
    a = p.parse_args()
    source, report = read(a.source_dir)
    result = {"source": report, "zulip_writes": False}
    if a.compare_dir:
        live, live_report = read(a.compare_dir)
        result["live"] = live_report
        result["difference"] = {
            "live_only_ids": sorted(live.keys() - source.keys()),
            "snapshot_only_ids": sorted(source.keys() - live.keys()),
            "changed_ids": sorted(i for i in source.keys() & live.keys() if source[i] != live[i]),
            "live_newer_than_snapshot": bool(report["last"] and live_report["last"] and dt.datetime.fromisoformat(live_report["last"]) > dt.datetime.fromisoformat(report["last"])),
        }
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
