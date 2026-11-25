# Native historical reconstruction (Zulip 13.3)

Source records are actual historical discussion transcripts. Preserve raw files privately, including legacy provenance fields; do not use those fields to characterize the discussions.

## Gates
1. Obtain authenticated, consistent live PHP snapshot of all four JSON files. Run native_preflight.py --source-dir SNAPSHOT --compare-dir LIVE. Resolve changed/missing IDs manually; never silently discard records.
2. Build a custom converter against the exact upstream 13.3 tag, using zerver/data_import helpers and existing converters as references. Preserve source text without archival prefixes, UTC timestamps, channel descriptions, and deterministic ordering by timestamp then source ID. Use a single explicitly migration-assigned topic "Historical discussion" per channel if no genuine topic metadata is found. Keep original records and source-to-import ID crosswalk privately. Backlog items are separate objects, not messages.
3. Confirm human email mapping (Mali, Che, Phill) and agent bot ownership (State Tracker, Policy Analyst, Source Verifier). Do not invent real email addresses or enable historical agent automation. Confirm channel access explicitly; source channel member counts do not identify members.
4. Create an isolated Zulip 13.3 installation with matching database migrations; use separate storage, secrets and hostname, disable outbound email/webhooks/integrations. Run a small native import first, then full import into a fresh realm. Validate exact sender, timestamp, text, channel, topic, counts, and ID crosswalk. Verify access and bot state. No production SQL writes.
5. Back up production with manage.py backup, retain off-host encrypted copy and test restore with matching Zulip/PostgreSQL versions. Back up custom theme separately. Inventory current realms, messages, settings, users, permissions and integrations.
6. Prefer importing validated historical realm alongside existing production realms under an unused realm identifier; 13.3 import accepts nonempty databases by default but checks subdomain availability. Never use --destroy-rebuild-database. No merge into existing realm is supported. Keep old realm available. If one unified realm at the original hostname is essential, design and test a distinct merge on a restored clone, accounting for all existing messages/settings/IDs; do not cut over until verified and explicitly approved. Freeze writes for final synchronization and maintain rollback routing; avoid restoring a stale backup over newly received production messages.

References:
- https://github.com/zulip/zulip/blob/13.3/zerver/management/commands/import.py
- https://github.com/zulip/zulip/blob/13.3/zerver/data_import/slack.py
- https://github.com/zulip/zulip/blob/13.3/docs/production/export-and-import.md

Status: preflight implemented, converter and staging execution not yet implemented. Live source freshness unverified. No production import performed.
