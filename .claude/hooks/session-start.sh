#!/bin/bash
set -euo pipefail

# Only run this setup in Claude Code on the web (remote) sessions.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# Install project dependencies so lint/build/dev scripts work out of the box.
npm install

# Install omniroute globally so it's available in every session without
# needing to be reinstalled manually each time.
npm install -g omniroute
