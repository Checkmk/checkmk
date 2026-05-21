#!/bin/bash
# PreToolUse hook (Bash): gate `git commit` with lint on staged files.
#
# Format runs per-edit via format.sh. Lint runs here, at commit time,
# because:
# - Per-edit lint would block each Edit/Write 5-30s on the Bazel server.
# - The previous async lint never fed findings back to the agent as a
#   tool error.
# - A Stop-hook lint would fire AFTER `git commit`, too late to gate.
# - At commit time there are no concurrent edits, so lint --fix is safe.
#
# Behavior:
# - The hook fires on every Bash call. Anything that isn't `git commit`
#   exits in milliseconds.
# - On a `git commit` invocation, run lint via .pre-commit-scripts/run-
#   lint-bazel on the staged files. Gated on the script's executable
#   bit so the existing `chmod -x` toggle (used to suppress Bazel
#   sandbox events during OMD-syncer-sensitive work) also disables
#   lint here.
# - On lint failure (findings or applied fixes), re-stage any working-
#   tree changes and exit 2. Claude Code surfaces the bazel output as
#   a tool error and blocks the commit. The agent re-runs git commit
#   with the fixed content.
set -euo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only intercept `git commit` (incl. --amend) and the `gc` shell alias.
# Status/diff/log/push pass through. False matches on `git commit-tree`
# are excluded because "commit" must be followed by space or end-of-
# string. `gc` requires a non-word-char (or start) before and a space /
# end / shell operator after, so it doesn't match `gcid`, `gca`, `gcc`,
# paths containing `gc`, etc. — only the bare `gc` command alias.
[[ "$COMMAND" =~ (^|[[:space:]])git[[:space:]]+commit([[:space:]]|$) ]] ||
    [[ "$COMMAND" =~ (^|[^[:alnum:]_-])gc([[:space:]]|$|;|\&|\|) ]] ||
    exit 0

# shellcheck source=.pre-commit-scripts/lib-precommit
source "$(cd "$(dirname "$0")/../.." && pwd)/.pre-commit-scripts/lib-precommit"
[[ ! -f "${GIT_ROOT}/MODULE.bazel" ]] && exit 0

LINT_SCRIPT="${GIT_ROOT}/.pre-commit-scripts/run-lint-bazel"
[[ ! -x "$LINT_SCRIPT" ]] && exit 0

cd "$GIT_ROOT"

mapfile -t STAGED < <(git diff --cached --name-only --diff-filter=ACMR | while read -r p; do
    [[ -n "$p" && -f "$p" ]] && echo "$p"
done)
[[ ${#STAGED[@]} -eq 0 ]] && exit 0

# bazel lint silently skips .py files that aren't in any target's srcs,
# so a new file at repo root or one not yet wired into a BUILD would
# pass through unchecked. Verify coverage before invoking run-lint-bazel.
declare -A PKG_OF
declare -a PY_FILES
for f in "${STAGED[@]}"; do
    [[ "$f" == *.py ]] || continue
    PY_FILES+=("$f")
    d=$(dirname "$f")
    while [[ "$d" != "." && "$d" != "/" ]]; do
        [[ -f "${GIT_ROOT}/${d}/BUILD.bazel" || -f "${GIT_ROOT}/${d}/BUILD" ]] && break
        d=$(dirname "$d")
    done
    PKG_OF["$f"]="$d"
done

if [[ ${#PY_FILES[@]} -gt 0 ]]; then
    declare -a PKG_LABELS
    for f in "${PY_FILES[@]}"; do
        pkg="${PKG_OF[$f]}"
        if [[ "$pkg" == "." ]]; then
            PKG_LABELS+=("//:all")
        else
            PKG_LABELS+=("//${pkg}:all")
        fi
    done
    mapfile -t PKG_LABELS < <(printf '%s\n' "${PKG_LABELS[@]}" | sort -u)
    joined=$(
        IFS=" + "
        echo "${PKG_LABELS[*]}"
    )
    ALL_SRCS=$(bazel query "labels(srcs, ${joined})" 2>/dev/null || true)

    declare -a UNCOVERED
    for f in "${PY_FILES[@]}"; do
        pkg="${PKG_OF[$f]}"
        if [[ "$pkg" == "." ]]; then
            label="//:${f}"
        else
            label="//${pkg}:${f#${pkg}/}"
        fi
        grep -Fxq -- "$label" <<<"$ALL_SRCS" || UNCOVERED+=("$f")
    done

    if [[ ${#UNCOVERED[@]} -gt 0 ]]; then
        echo "commit gate: ${#UNCOVERED[@]} staged Python file(s) not in any Bazel target's srcs — bazel lint would skip them:" >&2
        printf '  - %s\n' "${UNCOVERED[@]}" >&2
        echo "Add them to a BUILD.bazel srcs= (or unstage) before committing." >&2
        exit 2
    fi
fi

echo "commit gate: lint ${#STAGED[@]} staged file(s)" >&2
if ! "$LINT_SCRIPT" "${STAGED[@]}" >&2; then
    # run-lint-bazel exits non-zero when it applied auto-fixes to the
    # working tree. Re-stage them and block this commit so the agent
    # re-runs git commit with the fixed content.
    git add -- "${STAGED[@]}"
    echo "commit gate: lint applied fixes — re-run git commit to pick them up" >&2
    exit 2
fi
