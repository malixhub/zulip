#!/usr/bin/env bash
# ASDPolicy demonstration messages for a real Zulip organization.
# Posts to an existing channel as the authenticated user, never impersonates others.
set -euo pipefail
HOST="https://chat.asdpolicy.org"
printf "Zulip API email (your login email): "
read -r EMAIL
printf "Zulip API key (hidden): "
read -rs API_KEY
printf "\nChannel name [general]: "
read -r CHANNEL
CHANNEL="${CHANNEL:-general}"
if [[ -z "$EMAIL" || -z "$API_KEY" ]]; then
  echo "Email and API key are required. Nothing sent."
  exit 1
fi
send() {
  local topic="$1" content="$2" response
  response="$(curl --silent --show-error --fail-with-body -u "$EMAIL:$API_KEY" \
    --data-urlencode "type=stream" \
    --data-urlencode "to=$CHANNEL" \
    --data-urlencode "topic=$topic" \
    --data-urlencode "content=$content" \
    "$HOST/api/v1/messages")" || { echo "Message failed; check the channel and your credentials."; exit 1; }
  if [[ "$response" != *'"result":"success"'* && "$response" != *'"result": "success"'* ]]; then
    printf "API response: %s\n" "$response"; exit 1
  fi
}
send "UI demo | Research workflow" "**[SAMPLE CONTENT | FOR DESIGN REVIEW]**\nWe are testing how research conversations read in the redesigned workspace. The goal is to keep discussions easy to scan without losing substantive context."
send "UI demo | Research workflow" "**Question:** Should the first research brief emphasize early evaluation by 36 months, or focus on median diagnostic age?\n\nBoth measures are useful, but they describe different parts of the diagnostic pathway."
send "UI demo | Research workflow" "**Proposed direction:** Explain both measures, describe differences in surveillance coverage, and avoid interpreting catchment-area observations as statewide rankings."
send "UI demo | Policy sources" "**[SAMPLE CONTENT | FOR DESIGN REVIEW]**\nOur policy inventory needs a clear source hierarchy: CDC ADDM surveillance, state agencies, IDEA data, and peer-reviewed studies."
send "UI demo | Policy sources" "**Review note:** Display reporting year, geographic coverage, definition, and uncertainty alongside every chart. That context matters as much as the central estimate."
send "UI demo | Publication" "**[SAMPLE CONTENT | FOR DESIGN REVIEW]**\nDraft working title: *Fragmentation of Autism Policy Information in the United States*.\n\nPotential article type: Perspective or structured policy-resource analysis."
send "UI demo | Publication" "**Next question:** Which claims can we support through a repeatable audit of existing public resources, and which should remain clearly identified as interpretation?"
echo "Posted 7 clearly labeled sample messages in #$CHANNEL."
unset API_KEY
