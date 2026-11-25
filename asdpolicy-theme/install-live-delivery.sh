#!/usr/bin/env bash
# One-time installation of ASDPolicy's independent, refreshable CSS layer.
# Target: self-hosted Zulip 13.3 on srv2192145.
# No Zulip database or compiled webpack files are modified.
set -euo pipefail

if [[ "$(id -u)" != 0 ]]; then echo "Run as root on the Zulip VPS."; exit 1; fi
NGINX_SITE="/etc/nginx/sites-enabled/zulip-enterprise"
INCLUDE="/etc/nginx/zulip-include/asdpolicy-ui-dev.conf"
SYNC="/usr/local/sbin/asdpolicy-sync-css"
CRON="/etc/cron.d/asdpolicy-ui"
DIR="/var/lib/asdpolicy-ui"
if [[ ! -f "$NGINX_SITE" ]]; then echo "Zulip Nginx virtual host missing; aborting."; exit 1; fi
if ! nginx -V 2>&1 | grep -q -- '--with-http_sub_module'; then
  echo "Nginx sub_filter module unavailable. No changes made."; exit 1
fi
mkdir -p "$DIR"
chmod 755 "$DIR"
cat > "$SYNC" <<'SYNC_SCRIPT'
#!/usr/bin/env bash
set -euo pipefail
DIR="/var/lib/asdpolicy-ui"
DEST="$DIR/theme.css"
TMP="$(mktemp "$DIR/.theme.XXXXXXXX")"
trap 'rm -f "$TMP"' EXIT
URL="https://raw.githubusercontent.com/malixhub/zulip/asdpolicy-ui/asdpolicy-theme/live-overrides.css?bust=$(date +%s)"
curl --fail --silent --show-error --location --max-time 20 "$URL" -o "$TMP"
grep -q "ASDPolicy Collaboratory UI for Zulip 13.3" "$TMP" || { echo "CSS validation failed"; exit 1; }
[[ "$(wc -c < "$TMP")" -lt 100000 ]] || { echo "Unexpectedly large CSS"; exit 1; }
chmod 644 "$TMP"
if [[ ! -e "$DEST" ]] || ! cmp -s "$TMP" "$DEST"; then
  mv -f "$TMP" "$DEST"
  echo "$(date -Is) ASDPolicy CSS updated"
fi
SYNC_SCRIPT
chmod 755 "$SYNC"

# Download and validate the CSS before touching Nginx.
"$SYNC"

if [[ ! -f "$INCLUDE" ]]; then
  cat > "$INCLUDE" <<'NGINX_CONF'
# ASDPolicy CSS-only customization (one layer after Zulip's default CSS)
# sub_filter applies to text/html responses, adding the independent stylesheet.
sub_filter_once on;
sub_filter '</head>' '<link rel="stylesheet" href="/asdpolicy-dev.css"></head>';
location = /asdpolicy-dev.css {
    alias /var/lib/asdpolicy-ui/theme.css;
    default_type text/css;
    add_header Cache-Control "no-store, max-age=0" always;
    add_header X-Content-Type-Options nosniff always;
}
NGINX_CONF
fi

SITE_BACKUP="/etc/nginx/zulip-enterprise.before-asdpolicy-$(date +%Y%m%d-%H%M%S)"
cp -pL "$NGINX_SITE" "$SITE_BACKUP"

if ! grep -Fq "include $INCLUDE;" "$NGINX_SITE"; then
  python3 - "$NGINX_SITE" "$INCLUDE" <<'PY'
from pathlib import Path
import sys
site=Path(sys.argv[1]); include=sys.argv[2]
source=site.read_text()
marker="listen 443 ssl http2;"
i=source.find(marker)
if i < 0:
    raise SystemExit("Expected Zulip HTTPS server block not found.")
target="    include /etc/nginx/zulip-include/app;"
j=source.find(target, i)
if j < 0:
    raise SystemExit("Expected HTTPS Zulip app include not found.")
source=source[:j]+f"    include {include};\n"+source[j:]
site.write_text(source)
PY
fi
if ! nginx -t; then
  cp -p "$SITE_BACKUP" "$NGINX_SITE"
  nginx -t || true
  echo "Nginx config invalid; original configuration restored."
  exit 1
fi
systemctl reload nginx

cat > "$CRON" <<'CRON_FILE'
# Check the public GitHub stylesheet once per minute; keep existing copy if unavailable.
* * * * * root /usr/local/sbin/asdpolicy-sync-css >> /var/log/asdpolicy-ui-sync.log 2>&1
CRON_FILE
chmod 644 "$CRON"

echo
echo "Installed ASDPolicy CSS delivery and GitHub polling."
echo "Check the stylesheet: https://chat.asdpolicy.org/asdpolicy-dev.css"
echo "Then refresh the Zulip workspace once."
echo "Nginx backup: $SITE_BACKUP"
echo "Future CSS commits on asdpolicy-ui are picked up by the minute cron job."
