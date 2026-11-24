#!/usr/bin/env python3
"""Seed a clearly labeled ASDPolicy demonstration workspace in a real Zulip organization.
Uses the documented Zulip REST API; does not modify the Zulip database directly.
Only runs after the operator confirms the target hostname.
"""
import getpass
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://chat.asdpolicy.org"
STATE = Path.home() / ".asdpolicy-zulip-demo-seed-v1.json"
BOTS = [
    ("reviewer-demo", "Research Reviewer (Demo)"),
    ("policy-demo", "Policy Analyst (Demo)"),
    ("data-demo", "Data Specialist (Demo)"),
    ("editor-demo", "Editorial Lead (Demo)"),
]

# Each message uses one of the four explicitly identified demo bots.
CHANNELS = {
    "announcements": {
        "description": "Workspace announcements, onboarding and milestones. Demo threads are labeled.",
        "topics": {
            "DEMO | Welcome to the Collaboratory": [
                (0, "**DEMO CONVERSATION** Welcome to the ASDPolicy research workspace. This thread is sample content to test how a busy Zulip discussion reads."),
                (3, "The workspace is organized into channels for research, policy analysis, data, editorial work, and general discussion."),
                (1, "For the first review, let's focus on readability: author names, avatars, dates, topic titles, and channel navigation."),
                (2, "I will check whether tables, citations, and datasets display comfortably in long threads."),
            ],
            "DEMO | Release notes": [
                (3, "**Demo release note 01:** Slack-inspired sidebar skin installed, channel organization being tested."),
                (0, "Please add comments on message density, hover states, and whether the channel/topic hierarchy feels intuitive."),
                (1, "I'd also like to test the difference between a short reply and a longer policy discussion."),
            ],
        },
    },
    "research": {
        "description": "Research questions, literature reviews, hypotheses and study designs.",
        "topics": {
            "DEMO | Social touch and electrodermal response": [
                (0, "Working question: how might affective social touch cues relate to skin conductance responses in different populations? **Demo discussion, not a reported study result.**"),
                (2, "We should separate the hypothesis from observed evidence and document the measurement protocol before interpreting SCR amplitude."),
                (1, "A useful methods note could identify possible confounds such as baseline arousal, video content, and participant preferences."),
                (3, "For publication, we'll want a clear distinction between a proposed study, a protocol, and empirical findings."),
            ],
            "DEMO | Literature review workflow": [
                (3, "Proposal: build a shared bibliography organized by methods, outcomes, populations, and unresolved questions."),
                (0, "Agreed. Each summary should include the original source and a note about study limitations."),
                (2, "It would help to capture sample sizes and whether the design is observational or experimental."),
            ],
        },
    },
    "policy-analysis": {
        "description": "Neutral analysis of autism policy structures and public information access.",
        "topics": {
            "DEMO | Fragmented autism policy information": [
                (1, "The question is whether existing resources make autism policy information sufficiently discoverable, comparable, and transparent across jurisdictions."),
                (0, "Let's avoid claiming that no centralized resource exists. We can instead document the specific gaps that remain."),
                (3, "Potential paper structure: background, resource audit, limitations, and implications for policymakers."),
                (2, "A reproducible audit table would be stronger than a list of anecdotal examples."),
            ],
            "DEMO | Policy resource audit": [
                (2, "Candidate audit dimensions: geographic coverage, reporting year, accessibility, methodology, policy domain, and update frequency."),
                (1, "We should define inclusion rules before examining resources to reduce selection bias."),
                (0, "Let's also distinguish original data sources from websites that aggregate other organizations' datasets."),
            ],
        },
    },
    "data-sources": {
        "description": "CDC ADDM, NSCH, IDEA and methodological data notes.",
        "topics": {
            "DEMO | ADDM site coverage": [
                (2, "Reminder: ADDM surveillance areas should not be treated as equivalent to whole states. **Demo methods note.**"),
                (0, "The visualization should explicitly distinguish site-level surveillance data from statewide indicators."),
                (1, "Comparisons also need clear notes on evaluation thresholds and diagnostic timing."),
                (3, "I'll ensure those distinctions survive when the chart is shown at mobile sizes."),
            ],
            "DEMO | Data quality flags": [
                (2, "Suggested checklist: reference period, missingness, uncertainty interval, geographic unit, provenance, and update cycle."),
                (0, "For survey-derived estimates, wide confidence intervals should remain visible to readers."),
                (1, "Yes. We should document what can and cannot be inferred from each dataset."),
            ],
        },
    },
    "editorial": {
        "description": "Editorial review, reports, figures, and publication planning.",
        "topics": {
            "DEMO | Report editorial review": [
                (3, "Draft review checklist: title, claim accuracy, chart captions, citation completeness, accessibility, and caveats."),
                (1, "Please keep policy implications separate from descriptive findings."),
                (0, "I'll check that our copy stays neutral and avoids implying a state ranking."),
            ],
            "DEMO | Chart captions": [
                (3, "A useful caption should define the unit of analysis before describing the finding."),
                (2, "Include the reporting year and whether values are site-level or statewide."),
                (1, "And make limitations visible without requiring readers to open a separate methodology page."),
            ],
        },
    },
    "general": {
        "description": "Informal team discussion and workspace usability feedback.",
        "topics": {
            "DEMO | Workspace usability feedback": [
                (0, "The Slack-inspired theme is intended to feel familiar, but we still want Zulip's topics to remain easy to follow."),
                (3, "I like the compact channel list. Can we keep the message composer prominent?"),
                (2, "Longer data discussions will test scrolling and scanning better than empty channels."),
                (1, "The selected channel and topic should both be clear, particularly with a long sidebar."),
            ],
            "DEMO | Weekly check-in": [
                (1, "This is a sample weekly thread for testing discussion density."),
                (2, "Data review: documenting variable definitions and comparability notes."),
                (3, "Editorial review: checking summaries and chart captions."),
                (0, "Next step: gather UI feedback before any broader structural changes."),
            ],
        },
    },
}

def request(path, email, key, method="GET", payload=None):
    import base64
    headers = {"Authorization": "Basic " + base64.b64encode((email + ":" + key).encode()).decode(),
               "User-Agent": "ASDPolicy-Demo-Seed/1.0"}
    data = None
    if payload is not None:
        data = urllib.parse.urlencode(payload).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(BASE + "/api/v1/" + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            result = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:350]
        raise RuntimeError(f"{method} {path}: HTTP {exc.code}: {detail}") from exc
    if result.get("result") != "success":
        raise RuntimeError(f"{path}: {result.get('msg', result)}")
    return result

def main():
    print("Target:", BASE)
    print("This creates six channels, four DEMO bots, and 42 fictional sample messages.")
    print("Existing conversations are never deleted or edited.")
    print("All new topic titles begin with DEMO.")
    if STATE.exists():
        print(f"Seed state exists: {STATE}. Refusing to run again to avoid duplicates.")
        return
    if input("Type SEED to populate this live workspace: ").strip() != "SEED":
        print("Cancelled.")
        return
    email = input("Your Zulip login email: ").strip()
    key = getpass.getpass("Your Zulip API key (input hidden, never saved): ").strip()
    me = request("users/me", email, key)
    print("Authenticated as:", me.get("full_name", email))
    # Reuse only matching bots owned by the authenticating account.
    existing = {b["full_name"]: b for b in request("bots", email, key)["bots"]}
    bot_auth = []
    for slug, full_name in BOTS:
        if full_name in existing:
            b = existing[full_name]
            bot_auth.append((b["username"], b["api_key"], b.get("user_id")))
            print("Reusing bot:", full_name)
        else:
            created = request("bots", email, key, "POST",
                              {"short_name": slug, "full_name": full_name, "bot_type": "1"})
            bot_user = request(f"users/{created['user_id']}", email, key)["user"]
            bot_auth.append((bot_user["email"], created["api_key"], created["user_id"]))
            print("Created bot:", full_name)
    # Resolve IDs for preexisting bots; GET /bots does not always expose user_id.
    members = {u["email"]: u["user_id"] for u in request("users", email, key)["members"]}
    bot_auth = [(bot_email, bot_key, uid or members[bot_email]) for bot_email, bot_key, uid in bot_auth]
    for name, spec in CHANNELS.items():
        request("users/me/subscriptions", email, key, "POST",
                {"subscriptions": json.dumps([{"name": name, "description": spec["description"]}])})
        request("users/me/subscriptions", email, key, "POST",
                {"subscriptions": json.dumps([{"name": name}]),
                 "principals": json.dumps([uid for _, _, uid in bot_auth])})
        print("Channel:", name)
    sent = 0
    for channel, spec in CHANNELS.items():
        for topic, messages in spec["topics"].items():
            for actor, content in messages:
                bot_email, bot_key, _ = bot_auth[actor]
                request("messages", bot_email, bot_key, "POST",
                        {"type": "stream", "to": json.dumps(channel),
                         "topic": topic, "content": content})
                sent += 1
            print("  Topic:", topic, "|", len(messages), "messages")
    STATE.write_text(json.dumps({"server": BASE, "messages_sent": sent, "channels": list(CHANNELS)}, indent=2))
    STATE.chmod(0o600)
    print(f"SUCCESS: {sent} demo messages, {len(CHANNELS)} channels, {len(BOTS)} demo bots.")
    print("Open " + BASE + " and select #announcements or #research.")
    print("This script does not produce historical timestamps or real human accounts.")

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, KeyError) as exc:
        print("Stopped:", exc, file=sys.stderr)
        sys.exit(1)
