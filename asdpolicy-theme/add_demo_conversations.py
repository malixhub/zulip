#!/usr/bin/env python3
"""Add clearly fictional conversations to an existing ASDPolicy Zulip demo workspace.
No database edits; only documented Zulip REST endpoints. Resumable without duplicates.
"""
import base64
import getpass
import json
import sys
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

HOST = "https://chat.asdpolicy.org"
STATE = Path.home() / ".asdpolicy-demo-conversations-v2.json"
BOTS = ["Research Reviewer (Demo)", "Policy Analyst (Demo)",
        "Data Specialist (Demo)", "Editorial Lead (Demo)"]

# Each exchange is an actual sequence of messages from different bot accounts.
# Actors: 0 researcher, 1 policy, 2 data, 3 editor.
THREADS = [
 ("announcements", "DEMO | Welcome to the Collaboratory", [
 (0, "**DEMO EXCHANGE** I have a question about the workspace. Should the research channel hold every literature discussion, or should we create separate channels per project?"),
 (1, "I'd keep one research channel for now, with a **topic for each question or project**. That gives us a much cleaner sidebar."),
 (3, "Agreed. And it means I can follow a topic like the ADDM methodology without receiving every research notification."),
 (2, "What about datasets? I often need to attach codebooks and tables."),
 (0, "Good point. Put the dataset-specific discussion in #data-sources and link the thread back to research."),
 (2, "That works. I'll use a separate topic for each source, starting with CDC ADDM."),
 (3, "One more thing: should we keep the 'DEMO' prefix?"),
 (1, "Yes, until we replace the sample content with actual collaborator discussions. That makes the distinction obvious."),
 ]),
 ("research", "DEMO | Social touch and electrodermal response", [
 (0, "**DEMO EXCHANGE** Can we revisit the proposed skin-conductance study? I'm concerned our hypothesis doesn't distinguish arousal from positive affect."),
 (2, "I agree. SCR amplitude indicates sympathetic activation, but it doesn't tell us whether the participant liked the stimulus."),
 (1, "So should the comfort questionnaire be treated as a separate outcome rather than evidence that SCR is positive or negative?"),
 (0, "Exactly. We can report the association without assuming a specific emotional interpretation."),
 (3, "For the manuscript, I'd put that caveat directly under the hypothesis, not bury it in limitations."),
 (2, "Also, what baseline window are we proposing before each clip? We should specify it in advance."),
 (0, "Let's document the stimulus timing and baseline correction in the protocol first."),
 (3, "I'll set up a methods checklist. **This is a proposed study, not collected data.**"),
 ]),
 ("policy-analysis", "DEMO | Fragmented autism policy information", [
 (1, "**DEMO EXCHANGE** How do we make the fragmentation argument testable instead of simply saying resources are scattered?"),
 (0, "We could audit discoverability and comparability across a defined sample of public resources."),
 (2, "I'd suggest fields for geographic scope, update year, data provenance, policy domain, and links to primary sources."),
 (3, "Do we risk overstating the problem? There are already organizations aggregating autism data."),
 (1, "We should acknowledge those resources explicitly and identify which gaps remain. A nuanced argument is stronger."),
 (0, "Right. Our central question isn't 'does a website exist?' but whether policy-relevant information can be located and compared reliably."),
 (2, "I can draft a reproducible coding rubric. That will also help identify where our own judgments enter the audit."),
 (3, "Then the article can present methods, findings, and limitations without sounding like an advertisement for ASDPolicy."),
 ]),
 ("data-sources", "DEMO | ADDM site coverage", [
 (2, "**DEMO EXCHANGE** The map note still needs to clarify that an ADDM surveillance site is not necessarily an entire state."),
 (1, "Would 'site-level surveillance catchment area' be clear enough for a general policymaker?"),
 (0, "It is accurate, but I think we need a short example explaining the difference."),
 (3, "Can we make the caption concise and move the detailed explanation to the methodology panel?"),
 (2, "Yes. Caption: 'Dots identify surveillance sites; values describe their reported catchment areas, not statewide estimates.'"),
 (1, "Good. Then we should avoid wording such as 'top states' in the report."),
 (3, "I'll update the editorial checklist to flag state-versus-site language."),
 (0, "Let's review a mobile screenshot before finalizing the caption."),
 ]),
 ("editorial", "DEMO | Chart captions", [
 (3, "**DEMO EXCHANGE** Can someone review this caption for a bar chart of early evaluations by 36 months?"),
 (2, "The caption should state the reporting cohort and site-level basis. Otherwise readers may assume statewide estimates."),
 (1, "We also need to avoid implying that higher values automatically mean better overall policy performance."),
 (3, "Understood. What about naming the median in the caption?"),
 (2, "Yes, if we specify that it's the median **across the displayed sites**."),
 (0, "I agree. And include a direct source reference with the surveillance year."),
 (3, "Thanks. I'll incorporate those changes and post a revision for another pass."),
 ]),
 ("general", "DEMO | Workspace usability feedback", [
 (3, "**DEMO EXCHANGE** I tried reviewing the longer research thread. The conversation is clearer now, but I'd like more contrast on the active topic."),
 (0, "Same here. The purple sidebar helps distinguish navigation from content, but the topic selection should stand out."),
 (2, "I find the message area comfortable. One question: can the composer be more prominent without hiding content?"),
 (1, "We should test that at laptop width as well as desktop. The sidebar can get crowded."),
 (3, "Agreed. I'll record this as a UI experiment rather than a product requirement."),
 (0, "Let's compare two visual variations before applying another live stylesheet."),
 ]),
]

# DMs are private demo conversations between bots, never sent to the user's account.
DMS = [
 (0, 2, "DEMO PRIVATE CHAT: Are the ADDM comparison notes ready for review?"),
 (2, 0, "Almost. I found a wording issue around surveillance sites versus states."),
 (0, 2, "Can you flag the exact caption? I'll review it with the methodology notes."),
 (2, 0, "Yes. I'll share the revised language in the #data-sources topic."),
 (3, 1, "DEMO PRIVATE CHAT: Did the policy-resource audit outline reach editorial review?"),
 (1, 3, "Yes, but I'd like to tighten the criteria before we describe any findings."),
 (3, 1, "That makes sense. Can you add the inclusion and exclusion rules?"),
 (1, 3, "Absolutely. I'll add them to the audit topic for a transparent review."),
]

def api(route, email, key, method="GET", fields=None):
    auth = base64.b64encode(f"{email}:{key}".encode()).decode()
    data = urllib.parse.urlencode(fields).encode() if fields is not None else None
    req = urllib.request.Request(
        HOST + "/api/v1/" + route, data=data, method=method,
        headers={"Authorization": "Basic " + auth,
                 "Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "ASDPolicy-Demo-Conversations-v2"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.load(resp)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{route}: {exc.code}: {exc.read().decode(errors='replace')[:300]}") from exc
    if result.get("result") != "success":
        raise RuntimeError(f"{route}: {result}")
    return result

def main():
    print("Target:", HOST)
    print("Adds", sum(len(x[2]) for x in THREADS), "channel replies plus", len(DMS), "private demo messages.")
    print("Uses existing demo bots; does not create users, delete messages or change settings.")
    if input("Type ADD to post these demo conversations: ").strip() != "ADD":
        print("Cancelled.")
        return
    email = input("Your Zulip email: ").strip()
    key = getpass.getpass("Your Zulip API key (hidden, not saved): ")
    print("Authenticated:", api("users/me", email, key).get("full_name"))
    bots = {b["full_name"]: b for b in api("bots", email, key)["bots"]}
    missing = [name for name in BOTS if name not in bots]
    if missing:
        raise RuntimeError("Demo bots missing: " + ", ".join(missing))
    actors = [(bots[name]["username"], bots[name]["api_key"]) for name in BOTS]
    state = json.loads(STATE.read_text()) if STATE.exists() else {"done": []}
    completed = set(state["done"])
    def post_once(identifier, actor, fields):
        if identifier in completed:
            return
        bot_email, bot_key = actors[actor]
        api("messages", bot_email, bot_key, "POST", fields)
        completed.add(identifier)
        STATE.write_text(json.dumps({"done": sorted(completed)}, indent=2))
        STATE.chmod(0o600)
    for channel, topic, lines in THREADS:
        for i, (actor, content) in enumerate(lines):
            post_once(f"channel:{channel}:{topic}:{i}", actor,
                      {"type": "stream", "to": json.dumps(channel),
                       "topic": topic, "content": content})
        print("Conversation:", channel, "/", topic)
    # Direct messages may be blocked by bot/organization policy; this is optional.
    dm_count = 0
    try:
        for i, (actor, recipient, content) in enumerate(DMS):
            post_once(f"dm:{i}", actor,
                      {"type": "private", "to": json.dumps([actors[recipient][0]]),
                       "content": content})
            dm_count += 1
    except RuntimeError as exc:
        print("Direct-message demo unavailable:", exc)
        print("Channel conversations have still been posted successfully.")
    print("Completed. Open #announcements and #research for real bot-to-bot exchanges.")
    print("If permitted, demo-bot private messages are visible to their participants, not to your personal Zulip inbox.")

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, KeyError, ValueError) as exc:
        print("Stopped:", exc, file=sys.stderr)
        sys.exit(1)
