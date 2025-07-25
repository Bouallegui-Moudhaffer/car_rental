#!/usr/bin/env sh
set -e

# Generate a SECRET_KEY if not provided
if [ -z "$SECRET_KEY" ]; then
  echo "No SECRET_KEY supplied—generating one..."
  export SECRET_KEY="$(openssl rand -hex 32)"
fi

# You can log it or persist it if you need—but beware printing secrets.
# echo "Using SECRET_KEY=${SECRET_KEY}"

exec "$@"
