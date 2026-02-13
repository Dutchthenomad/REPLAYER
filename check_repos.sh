#!/bin/bash
# Convenience wrapper for checking repository status

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/scripts/check_repo_status.py" "$@"
