"""Run via manage.py shell on an ISOLATED Zulip 13.3 installation only.

No database writes: creates a native import directory and separate private audit.
See NATIVE_MIGRATION.md. Mapping and live-source review are mandatory.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

from native_preflight import read
from zerver.data_import.import_util import (
    build_message, build_realm, build_recipient, build_stream, build_subscription,
    build_user_profile, build_zerver_realm, create_converted_data_files,
    make_subscriber_map, make_user_messages, validate_user_emails_for_import,
)
from zerver.lib.export import do_common_export_processes
from zerver.models import Recipient, UserProfile

AGENTS = {"State Tracker", "Policy Analyst", "Source Verifier"}
TOPIC = "Historical discussion"

def convert(source_dir, mapping_path, output, audit, limit=0):
    os.umask(0o077)
    records, report = read(source_dir)
    mapping = json.loads(mapping_path.read_text())
    users = mapping["users"]
    access = mapping["channel_members"]
    channels = json.loads((source_dir / "channels.json").read_text())
    if set(users) != set(report["identities"]):
        raise ValueError("Mapping must cover exactly the historical authors")
    if set(access) != set(report["channels"]):
        raise ValueError("Explicit access list required for each channel")
    if report["blank_ids"]:
        raise ValueError("Blank messages require manual resolution")
    if any(len(roles) != 1 for roles in report["identities"].values()):
        raise ValueError("Conflicting source roles require manual review")
    owner = mapping["owner"]
    if owner not in users or owner in AGENTS:
        raise ValueError("Owner must be an approved human participant")
    emails = [v["email"] for v in users.values()]
    if len({e.casefold() for e in emails}) != len(emails):
        raise ValueError("Duplicate email")
    validate_user_emails_for_import(emails)
    if limit < 0:
        raise ValueError("Limit must be nonnegative")
    if output.exists() or audit.exists() or output.resolve() in audit.resolve().parents:
        raise ValueError("Use new output and separate audit paths")
    for channel, names in access.items():
        if not isinstance(names, list) or len(names) != len(set(names)) or not set(names) <= set(users):
            raise ValueError(f"Invalid channel membership: {channel}")
    for m in records.values():
        if m["author"] not in access[m["channel"]]:
            raise ValueError(f"Sender not in approved channel access: {m['id']}")
        if "\x00" in m["text"]:
            raise ValueError(f"Null byte in {m['id']}")
    def stamp(m):
        return dt.datetime.fromisoformat(m["created_at"].replace("Z", "+00:00")).timestamp()
    ordered = sorted(records.values(), key=lambda m: (stamp(m), m["id"]))
    if not ordered:
        raise ValueError("No messages")
    first = stamp(ordered[0])
    selected = ordered[:limit] if limit else ordered
    user_ids = {name: i for i, name in enumerate(sorted(users), 1)}
    realm_id = 0
    realm = build_realm(build_zerver_realm(realm_id, "", first, "ASDPolicy Collaboratory"),
                        realm_id, mapping["domain"], import_source="asdpolicy")
    realm["zerver_realm"][0]["name"] = "ASDPolicy Collaboratory Historical Discussions"
    realm["zerver_userprofile"] = []
    for name, uid in user_ids.items():
        bot = name in AGENTS
        email = users[name]["email"]
        u = build_user_profile(avatar_source="G", date_joined=first,
            delivery_email=email, email=email, full_name=name, id=uid,
            is_active=not bot, role=UserProfile.ROLE_REALM_OWNER if name == owner else UserProfile.ROLE_MEMBER,
            is_mirror_dummy=False, realm_id=realm_id, short_name=name, timezone="UTC",
            is_bot=bot, bot_type=1 if bot else None)
        if bot:
            u["bot_owner"] = user_ids[owner]
        realm["zerver_userprofile"].append(u)
    for key in ("zerver_stream", "zerver_recipient", "zerver_subscription", "zerver_defaultstream"):
        realm[key] = []
    recipients = {}
    for i, c in enumerate(sorted(channels, key=lambda c: c["id"]), 1):
        cid = c["id"]
        realm["zerver_stream"].append(build_stream(first, realm_id, c["name"], c["description"], i, invite_only=True))
        realm["zerver_recipient"].append(build_recipient(i, i, Recipient.STREAM))
        recipients[cid] = i
        for name in sorted(access[cid]):
            subs = realm["zerver_subscription"]
            subs.append(build_subscription(i, user_ids[name], len(subs)+1))
    messages, crosswalk = [], []
    for i, m in enumerate(selected, 1):
        row = build_message(topic_name=TOPIC, date_sent=stamp(m), message_id=i,
            content=m["text"], rendered_content=None, user_id=user_ids[m["author"]],
            recipient_id=recipients[m["channel"]], realm_id=realm_id,
            is_channel_message=True, has_attachment=False, is_direct_message_type=False)
        if row["content"] != m["text"]:
            raise ValueError(f"Zulip normalization altered {m['id']}; review required")
        messages.append(row)
        crosswalk.append({"source_id":m["id"], "bundle_message_id":i,
            "source_timestamp":m["created_at"], "author":m["author"], "channel":m["channel"],
            "text_sha256":hashlib.sha256(m["text"].encode()).hexdigest()})
    user_messages = make_user_messages(messages, make_subscriber_map(realm["zerver_subscription"]),
                                       {m["id"]:set() for m in messages})
    output.mkdir(mode=0o700, parents=True)
    def write(path, data):
        create_converted_data_files(data, str(output), "/" + path)
    write("realm.json", realm)
    write("messages-000001.json", {"zerver_message":messages,"zerver_usermessage":user_messages})
    write("attachment.json", {"zerver_attachment":[]})
    for folder in ("avatars", "uploads", "emoji", "realm_icons"):
        write(folder + "/records.json", [])
    do_common_export_processes(str(output))
    audit.mkdir(mode=0o700, parents=True)
    (audit / "crosswalk.json").write_text(json.dumps(crosswalk, indent=2))
    (audit / "report.json").write_text(json.dumps({"source":report,"selected":len(messages),
        "topic_assignment":TOPIC,"channel_privacy":"all private, explicit subscribers",
        "backlog":"retained in original source, not converted into messages"}, indent=2))
    print(f"Created {len(messages)} native message rows; NO import performed.")

def main():
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("source-dir", "mapping", "output", "audit"):
        p.add_argument("--"+arg, type=Path, required=True)
    p.add_argument("--limit", type=int, default=0)
    a = p.parse_args()
    convert(a.source_dir, a.mapping, a.output, a.audit, a.limit)

if __name__ == "__main__":
    main()
