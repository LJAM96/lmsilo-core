#!/bin/sh
# runtime-config.sh - Injects environment variables into the static build at runtime

# Create config.js with runtime environment variables
cat <<EOF > /usr/share/nginx/html/config.js
window.__LMSILO_CONFIG__ = {
  PORTAL_TICKER: "${PORTAL_TICKER:-Welcome to LMSilo - Your Local AI Suite}"
};
EOF

# Start nginx
exec nginx -g 'daemon off;'
