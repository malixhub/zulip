#!/usr/bin/env bash
# ASDPolicy Zulip 13.3 CSS delivery repair.
# Reuse the existing compose/navigation HTML injection.
# No CSS bundle edits; no additional sub_filter directives.
set -euo pipefail
SITE=/etc/nginx/sites-available/zulip-enterprise
COMPOSE=/etc/nginx/asdpolicy-compose-injection.conf
ROUTE=/etc/nginx/zulip-include/asdpolicy-ui-dev.conf
CSS=/var/lib/asdpolicy-ui/theme.css
SYNC=/usr/local/sbin/asdpolicy-sync-css
BACKUPS=/root/asdpolicy-nginx-backups
LINK='<link rel="stylesheet" href="/asdpolicy-dev.css">'
[[ "$(id -u)" -eq 0 ]] || { echo "Run as root"; exit 1; }
[[ -f "$SITE" && -f "$COMPOSE" ]] || { echo "Expected Zulip configs missing; no changes"; exit 1; }
mkdir -p "$BACKUPS" /var/lib/asdpolicy-ui
if [[ -x "$SYNC" ]]; then "$SYNC"; fi
[[ -s "$CSS" ]] || { echo "Downloaded CSS missing ($CSS); stopping"; exit 1; }
grep -q 'ASDPolicy Collaboratory UI for Zulip 13.3' "$CSS" || { echo "Unexpected CSS content; stopping"; exit 1; }

STAMP="$(date +%Y%m%d-%H%M%S)"
cp -p "$SITE" "$BACKUPS/zulip-enterprise.$STAMP"
cp -p "$COMPOSE" "$BACKUPS/asdpolicy-compose-injection.$STAMP"
[[ ! -f "$ROUTE" ]] || cp -p "$ROUTE" "$BACKUPS/asdpolicy-ui-dev.$STAMP"
rollback() {
  cp -p "$BACKUPS/zulip-enterprise.$STAMP" "$SITE"
  cp -p "$BACKUPS/asdpolicy-compose-injection.$STAMP" "$COMPOSE"
  if [[ -f "$BACKUPS/asdpolicy-ui-dev.$STAMP" ]]; then
    cp -p "$BACKUPS/asdpolicy-ui-dev.$STAMP" "$ROUTE"
  else
    rm -f "$ROUTE"
  fi
  echo "Restored Nginx config files. Nginx was not reloaded."
}
trap 'echo "Installation failed."; rollback' ERR

cat > "$ROUTE" <<'NGINX'
# CSS only. No sub_filter directives: uses the existing compose injection.
location = /asdpolicy-dev.css {
    alias /var/lib/asdpolicy-ui/theme.css;
    default_type text/css;
    add_header Cache-Control "no-store, max-age=0" always;
    add_header X-Content-Type-Options "nosniff" always;
}
NGINX

python3 - "$SITE" "$COMPOSE" <<'PY'
from pathlib import Path
import sys
site, compose = map(Path, sys.argv[1:])
s = site.read_text()
inc = "    include /etc/nginx/zulip-include/asdpolicy-ui-dev.conf;"
existing = "    include /etc/nginx/asdpolicy-compose-injection.conf;"
if existing not in s:
    raise SystemExit("Can't find existing injection include; stopping")
if inc not in s:
    s = s.replace(existing, inc + "\n" + existing, 1)
    site.write_text(s)
c = compose.read_text()
link = '<link rel="stylesheet" href="/asdpolicy-dev.css">'
if link not in c:
    if "</body>" not in c:
        raise SystemExit("Can't find existing </body> sub_filter; stopping")
    c = c.replace("</body>", link + "</body>", 1)
    compose.write_text(c)
PY

nginx -t
systemctl reload nginx
trap - ERR
echo
echo "Nginx accepted the config and reloaded."
echo "CSS: https://chat.asdpolicy.org/asdpolicy-dev.css"
echo "Backups: $BACKUPS/*.$STAMP"
echo "Verification:"
curl -sS -o /dev/null -w 'CSS HTTP %{http_code} (%{content_type})\n' https://chat.asdpolicy.org/asdpolicy-dev.css
curl -sS https://chat.asdpolicy.org/ | grep -o 'asdpolicy-dev.css' | head -1 || true
