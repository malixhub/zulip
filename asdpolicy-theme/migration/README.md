# ASDPolicy Collaboratory → Zulip 13.3 migration

## Goal
Preserve 1,540 historical messages from the Collaboratory's nine channels.
The user has confirmed these are **real historical discussion transcripts**.
Do not treat the legacy `kind=seeded` source field as evidence of simulation.

## Source of record
The PHP application reads `data/messages.json`, `data/messages-archive-1.json`,
`data/channels.json`, and `data/backlog.json`.
The GitHub files are a snapshot; export the *current live PHP host* data before
executing any migration, because messages may have changed since the last commit.

## Option A: Existing Zulip organization (prepared, safe, archive-style)
1. Back up the source JSON and the Zulip organization.
2. Export the four JSON files from the PHP host into a local directory.
3. Run:
   `python3 prepare_archive.py --source-dir /path/to/export`
   This creates `asdpolicy-import-review/messages.jsonl`, `channels.json`,
   `backlog.json`, and `summary.json`. It does **not** post anything.
4. Review message totals, author mappings, original dates and topics.
5. Create the channels indicated in `channels.json` in the existing Zulip
   organization, with appropriate privacy settings. Do not assume imported
   content is safe for public channels.
6. Use a clearly named migration/archivist account. Set `ZULIP_EMAIL` and
   `ZULIP_API_KEY` as environment variables (do not commit credentials).
7. Preview:
   `python3 import_existing_org.py --manifest asdpolicy-import-review/messages.jsonl`
8. Small approval batch:
   `python3 import_existing_org.py --manifest asdpolicy-import-review/messages.jsonl --execute --max-messages 10`
9. Review Zulip; only after approval, rerun with `--execute` to continue.
   The checkpoint records successfully acknowledged messages and avoids duplicate
   sends across normal reruns. Review failures/timeouts before retrying.

**Limitations:** The normal message API creates a new Zulip timestamp and
attributes each post to the migration account; the archived original author
and date are preserved in the message's body and manifest. Records are grouped
by channel and original YYYY-MM month, in chronological order.

## Option B: Native-history reconstruction (research plan, NOT implemented)
Zulip's supported third-party import pipeline can create a *new organization*.
A custom conversion would need to build a validated Zulip data-import bundle,
including user identities, channel subscriptions, messages, topic names, and
historical Unix timestamps. Test it against a clean, isolated Zulip 13.3 server
or organization first. Do not use `manage.py import` against the user's
existing production organization: it does not merge imported history.

If the native-history path is chosen:
- Make an audited identity mapping for Mali, Che, Phill and three agents; confirm
  exact user identities and whether agents should be bots.
- Preserve the exact original message timestamps, stable IDs in a mapping,
  channels, and chronological content; keep a provenance audit log.
- Compare imported message counts and sample threads to the source export.
- Preserve the original organization and its user accounts until the
  replacement environment is validated and a rollback plan is approved.
- Plan the hostname cutover carefully; do not switch `EXTERNAL_HOST` or edit
  the live Zulip database as a shortcut.

## Safety / confidentiality
This material is organizational conversation history and may contain private
communications. Do not publish the migration manifests or source exports to a
public GitHub repository. Only scripts and generic schema guidance belong here.
Review channel permissions before posting, and retain offline backups.
