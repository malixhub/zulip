#!/usr/bin/env bash
# Reversible ASDPolicy sidebar experiment on existing Zulip installation.
set -euo pipefail
ROOT="https://raw.githubusercontent.com/malixhub/zulip/asdpolicy-ui/asdpolicy-theme"
STATIC="/home/zulip/prod-static"
SNIPPET="/etc/nginx/asdpolicy-compose-injection.conf"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="/root/nginx-backups/asdpolicy-compose-injection.$STAMP.conf"
mkdir -p /root/nginx-backups
test -f "$SNIPPET" || { echo "Existing Zulip injection snippet not found; aborting."; exit 1; }
# Download all assets first. Existing composer v2 and selection-outline fix remain.
curl -fsSL "$ROOT/navigation_v1.js" -o "$STATIC/asdpolicy-navigation-v1.js"
curl -fsSL "$ROOT/navigation_v1.css" -o "$STATIC/asdpolicy-navigation-v1.css"
chmod 644 "$STATIC/asdpolicy-navigation-v1.js" "$STATIC/asdpolicy-navigation-v1.css"
cp -p "$SNIPPET" "$BACKUP"
# Preserve current sub_filter_once and replace its replacement target to
# additionally load navigation files, without dropping previous UI fixes.
python3 - "$SNIPPET" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
s = path.read_text()
extra = '<link rel="stylesheet" href="/static/asdpolicy-navigation-v1.css"><script defer src="/static/asdpolicy-navigation-v1.js"></script>'
if "asdpolicy-navigation-v1.js" in s:
    print("Navigation injection already configured")
elif "sub_filter '</body>' '" in s:
    s = s.replace("</body>';", extra + "</body>';")
    path.write_text(s)
else:
    raise SystemExit("Expected existing injection not found; refusing change.")
PY
if nginx -t; then
    systemctl reload nginx
    echo "ASDPolicy sidebar experiment enabled."
else
    cp -p "$BACKUP" "$SNIPPET"
    nginx -t || true
    echo "Original Nginx injection restored."
    exit 1
fi
echo "Restore: cp -p '$BACKUP' '$SNIPPET' && nginx -t && systemctl reload nginx"
