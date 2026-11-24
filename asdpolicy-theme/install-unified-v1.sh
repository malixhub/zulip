#!/usr/bin/env bash
# Replace prior Zulip 13.3 live CSS experiments with ONE ASDPolicy theme.
# Must run on srv2192145; affects static appearance only, not Zulip data.
set -euo pipefail
CSS="/home/zulip/prod-static/webpack-bundles/app.e53787ae69151c6feb21.css"
BASE="${CSS}.before-slack"
STAMP="$(date +%Y%m%d-%H%M%S)"
THEME_URL="https://raw.githubusercontent.com/malixhub/zulip/asdpolicy-ui/asdpolicy-theme/collaboratory-unified-v1.css"
[[ -f "$CSS" ]] || { echo "Expected Zulip 13.3 CSS not found; stopping."; exit 1; }
[[ -f "$BASE" ]] || { echo "Original .before-slack backup not found; stopping to avoid corrupting CSS. Send the output of: ls -1 ${CSS}*"; exit 1; }
[[ -f "$CSS.gz" ]] || { echo "Missing compressed CSS; stopping."; exit 1; }
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
curl -fsSL "$THEME_URL" -o "$TMP"
grep -q 'ASDPolicy Collaboratory UI for Zulip 13.3' "$TMP" || { echo "Theme download did not validate."; exit 1; }
# Avoid restoring an unexpected backup from a different build.
if ! grep -q 'message_row' "$BASE"; then echo "Backup doesn't resemble compiled Zulip CSS. Stopping."; exit 1; fi
cp -p "$CSS" "${CSS}.pre-unified-${STAMP}"
cp -p "$CSS.gz" "${CSS}.gz.pre-unified-${STAMP}"
cat "$BASE" "$TMP" > "${CSS}.new"
chmod --reference="$CSS" "${CSS}.new"
chown --reference="$CSS" "${CSS}.new"
mv "${CSS}.new" "$CSS"
gzip -n -c "$CSS" > "${CSS}.gz.new"
chmod --reference="$CSS.gz" "${CSS}.gz.new"
chown --reference="$CSS.gz" "${CSS}.gz.new"
mv "${CSS}.gz.new" "$CSS.gz"
echo "Installed unified ASDPolicy theme from clean pre-experiment backup."
echo "Older appended Slack/contrast styles have been replaced, not stacked."
echo "Keep the pre-unified backups for rollback."
