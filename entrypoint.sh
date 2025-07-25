#!/usr/bin/env sh
set -e

# If no SECRET_KEY in env, generate one
if [ -z "$SECRET_KEY" ]; then
  echo "➜  No SECRET_KEY provided, generating a new one..."
  export SECRET_KEY="$(openssl rand -hex 32)"
fi

# Exec the main process
exec "$@"
