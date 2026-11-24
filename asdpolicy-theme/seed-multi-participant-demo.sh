#!/usr/bin/env bash
# Adds a clearly labelled multi-participant demo discussion to Zulip.
# Requires three "Generic bot" accounts created in Zulip's Bots settings.
# Each message is sent with the API identity of the indicated demo bot.
set -euo pipefail
HOST="https://chat.asdpolicy.org"
CHANNEL="general"
TOPIC="UI DEMO | Team discussion (sample)"
echo "Create 3 Generic bots in Zulip first, named:"
echo "  Research Reviewer (Demo), Policy Editor (Demo), Data Analyst (Demo)"
echo "Find their API email addresses and keys under Personal settings > Bots."
echo
declare -a emails keys
for i in 0 1 2; do
  case "$i" in
    0) label="Research Reviewer (Demo)";;
    1) label="Policy Editor (Demo)";;
    2) label="Data Analyst (Demo)";;
  esac
  printf "%s API email: " "$label"; IFS= read -r emails[$i]
  printf "%s API key (hidden): " "$label"; IFS= read -rs keys[$i]; printf '\n'
  [[ -n "${emails[$i]}" && -n "${keys[$i]}" ]] || { echo "Missing credentials. Nothing posted."; exit 1; }
done
post() {
  local i="$1" message="$2" result
  result="$(curl -fsS -u "${emails[$i]}:${keys[$i]}" \
     --data-urlencode "type=stream" \
     --data-urlencode "to=$CHANNEL" \
     --data-urlencode "topic=$TOPIC" \
     --data-urlencode "content=$message" \
     "$HOST/api/v1/messages")" || { echo "Posting failed. Verify channel permissions and bot credentials."; exit 1; }
  if [[ "$result" != *'"result":"success"'* && "$result" != *'"result": "success"'* ]]; then
    printf 'Unexpected API response: %s\n' "$result"; exit 1
  fi
}
post 0 "**[DESIGN SAMPLE | NOT A REAL TEAM EXCHANGE]**\nI've looked at the latest autism surveillance chart. The biggest question is whether the site-level observations are easy to distinguish from statewide estimates."
post 1 "Agreed. Could we add a one-sentence explanation immediately below the chart? I'd like a reader to understand the geographical limits before interpreting the numbers."
post 2 "The underlying data supports that. We can include the reporting year and surveillance coverage next to each figure. I suggest an expandable methods note for details."
post 0 "That would help. Let's also check whether the label *early evaluation* is clear to someone without a research background."
post 1 "Maybe: **Children evaluated by age 36 months**. Then an information note can explain the exact definition used in the source."
post 2 "Good. For the next revision, I'll prepare two chart captions and a note explaining missing data. We should avoid treating missing values as zero."
post 0 "One more thing: can the publication draft link back to the corresponding data definitions?"
post 1 "Yes. The editorial structure could be **Finding → Context → Limitations → Data source**. It keeps the report neutral and actionable."
post 2 "**Design-review summary:** Nine messages from three clearly labeled demo accounts. This is test content, created to evaluate avatars, spacing, sender names, and reply flow."
unset keys
printf '\nPosted 9 sample messages from 3 demo bot accounts in #%s, topic: %s\n' "$CHANNEL" "$TOPIC"
