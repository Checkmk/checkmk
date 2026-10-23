#!/bin/bash
# Fails if one of the given PowerShell scripts contains a non-ASCII byte.
#
# The agent runs plugins with Windows PowerShell 5.1, which reads a script
# without BOM in the machine's ANSI code page. Authenticode hashes the script
# as decoded text, so a signature made for one decoding (UTF-8 on Linux, or the
# signing host's code page) fails with HashMismatch on hosts that decode it
# differently. Use escapes like "N$([char]0x00E4)chste" instead.
set -euo pipefail

status=0
for script in "$@"; do
    case "$script" in
        *.ps1) ;;
        *) continue ;;
    esac
    if LC_ALL=C grep -Hn '[^[:print:][:space:]]' "$script"; then
        status=1
    fi
done

if [ "$status" -ne 0 ]; then
    echo "error: the lines above contain non-ASCII characters" >&2
fi
exit "$status"
