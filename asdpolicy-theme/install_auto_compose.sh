#!/usr/bin/env bash
# Reversible production experiment for default-open Zulip composer.
set -euo pipefail
ROOT="https://raw.githubusercontent.com/malixhub/zulip/asdpolicy-ui/asdpolicy-theme"
NGINX="/etc/nginx/sites-enabled/zulip-enterprise"
SNIPPET="/etc/nginx/asdpolicy-compose-injection.conf"
JS="/home/zulip/prod-static/asdpolicy-auto-compose-v1.js"
BACKUP="$NGINX.before-asdpolicy-composer-$(date +%Y%m%d-%H%M%S)"
curl -fsSL "$ROOT/auto_open_composer.js" -o "$JS"
chmod 644 "$JS"
cp -p "$NGINX" "$BACKUP"
cat > "$SNIPPET" <<'EOF'
sub_filter_once on;
sub_filter '</body>' '<script defer src="/static/asdpolicy-auto-compose-v1.js"></script></body>';
EOF
python3 - "$NGINX" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
incl = "    include /etc/nginx/asdpolicy-compose-injection.conf;\n"
if incl not in s:
    needle = "    include /etc/nginx/zulip-include/app;\n"
    index = s.rfind(needle)
    if index < 0:
        raise SystemExit("Expected server block not found; configuration unchanged.")
    s = s[:index+len(needle)] + incl + s[index+len(needle):]
    p.write_text(s)
PY
if nginx -t; then
    systemctl reload nginx
    echo "Composer auto-open experiment installed; visit https://chat.asdpolicy.org"
else
    cp -p "$BACKUP" "$NGINX"
    nginx -t || true
    echo "Restored original Nginx configuration after failed validation."
    exit 1
fi
echo "Rollback: cp -p '$BACKUP' '$NGINX' && systemctl reload nginx"
