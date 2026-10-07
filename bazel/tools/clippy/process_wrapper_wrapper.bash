#!/bin/bash
set -euo pipefail

# Run the rustc process wrapper, but:
# - Instead of forwarding the exit code of the child process, capture it.
# - Instead of passing --stderr-file to the process wrapper, capture the output and write to that file after everything has finished, with the following format:
#   ```
#   <exit code of process wrapper>
#   <stderr of process wrapper>
#   ```

# --- begin runfiles.bash initialization v3 ---
# Copy-pasted from the Bazel Bash runfiles library v3.
set -uo pipefail; set +e; f=bazel_tools/tools/bash/runfiles/runfiles.bash
# shellcheck disable=SC1090
source "${RUNFILES_DIR:-/dev/null}/$f" 2>/dev/null || \
  source "$(grep -sm1 "^$f " "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -f2- -d' ')" 2>/dev/null || \
  source "$0.runfiles/$f" 2>/dev/null || \
  source "$(grep -sm1 "^$f " "$0.runfiles_manifest" | cut -f2- -d' ')" 2>/dev/null || \
  source "$(grep -sm1 "^$f " "$0.exe.runfiles_manifest" | cut -f2- -d' ')" 2>/dev/null || \
  { echo>&2 "ERROR: cannot find $f"; exit 1; }; f=; set -e
# --- end runfiles.bash initialization v3 ---

process_wrapper_path=$(rlocation "rules_rust/util/process_wrapper/process_wrapper")

stderr_file=""
cmd=("${process_wrapper_path}")

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --stderr-file)
      if [[ $# -lt 2 ]]; then
        echo "Error: --stderr-file requires a value" >&2
        exit 1
      fi
      stderr_file="$2"
      shift 2
      ;;
    *)
      cmd+=("$1")
      shift
      ;;
  esac
done


# Ensure that _some_ command is left
if [[ ${#cmd[@]} -eq 0 ]]; then
  echo "Error: no command to execute" >&2
  exit 1
fi

set +e # We allow failing for this command as we want to capture the exit code

out=$(${cmd[@]} 2>&1)
exit_code="$?"

set -e

cat <<EOF > "${stderr_file}"
${exit_code}
${out}
EOF

