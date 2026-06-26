#!/usr/bin/env bash
# One-shot setup for the opt-in Claude firejail sandbox: installs the firejail
# profile and registers the "claude-firejail" provider in ~/.paseo/config.json.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
installer="${repo_root}/buildscripts/infrastructure/build-nodes/scripts/install-development.sh"

command -v jq >/dev/null || {
    echo "error: jq is required (apt install jq)." >&2
    exit 1
}

# The profile and the paseo provider belong to the human running paseo, not to
# root. Resolve the invoking user even when this script itself is started via
# sudo, so a stray `sudo ./setup-claude-firejail.sh` does not register the
# provider in root's home.
user="${SUDO_USER:-${USER}}"
home="$(getent passwd "${user}" | cut -d: -f6)"
[[ -n "${home}" ]] || {
    echo "error: cannot resolve home directory for '${user}'." >&2
    exit 1
}
config="${home}/.paseo/config.json"

# --- 1. Install firejail + the claude profile (needs root) -------------------
# Only this step needs root, so escalate just here instead of forcing the whole
# script to run as root. install-development.sh reads cwd-relative paths, so it
# must run from the repo root.
if [[ ${EUID} -eq 0 ]]; then
    (cd "${repo_root}" && "${installer}" --profile aisandbox --only)
elif command -v sudo >/dev/null; then
    echo "Installing the firejail profile needs root privileges; prompting for sudo..."
    sudo -v # prompt up front and fail fast on bad/declined credentials
    (cd "${repo_root}" && sudo "${installer}" --profile aisandbox --only)
else
    echo "error: root privileges are required, but 'sudo' is not installed." >&2
    echo "       re-run this script as root." >&2
    exit 1
fi

# --- 2. Register the "claude-firejail" provider (idempotent) -----------------
# Always write the config as ${user} so it stays owned by them even under sudo.
register_provider() {
    local config="$1" cmd="$2" tmp
    mkdir -p "$(dirname "${config}")"
    [[ -f "${config}" ]] || echo '{}' >"${config}"
    tmp="$(mktemp)"
    jq --arg cmd "${cmd}" '
        .agents.providers["claude-firejail"] = {
            extends: "claude",
            label: "Claude (firejail)",
            command: [$cmd]
        }
    ' "${config}" >"${tmp}" && mv "${tmp}" "${config}"
}

if [[ ${EUID} -eq 0 && "${user}" != "root" ]]; then
    sudo -u "${user}" bash -c \
        "$(declare -f register_provider); register_provider \"\$1\" \"\$2\"" \
        _ "${config}" "${script_dir}/claude-firejail"
else
    register_provider "${config}" "${script_dir}/claude-firejail"
fi

echo "Registered the \"Claude (firejail)\" provider in ${config}."

# --- 3. Offer to whitelist sensitive credentials (idempotent) ----------------
# The profile masks everything under ${HOME} it does not whitelist, so secrets
# like ~/.netrc and SSH private keys are invisible to Claude unless the user
# opts in. Offer to add them to the user-editable claude.local; firejail expands
# ${HOME} there, so write the lines literally.
local_config="${home}/.config/firejail/claude.local"

append_local_lines() {
    local config="$1" line
    shift
    mkdir -p "$(dirname "${config}")"
    touch "${config}"
    for line in "$@"; do
        grep -qxF "${line}" "${config}" || printf '%s\n' "${line}" >>"${config}"
    done
}

write_local_lines() {
    if [[ ${EUID} -eq 0 && "${user}" != "root" ]]; then
        sudo -u "${user}" bash -c \
            "$(declare -f append_local_lines); append_local_lines \"\$@\"" \
            _ "${local_config}" "$@"
    else
        append_local_lines "${local_config}" "$@"
    fi
}

confirm() {
    local answer
    read -r -p "$1 [Y/n] " answer </dev/tty || return 1
    [[ ! "${answer}" =~ ^[Nn] ]]
}

lines=()
if [[ -r /dev/tty ]]; then
    if [[ -f "${home}/.netrc" ]] &&
        confirm "Whitelist ~/.netrc (jira/artifacts/git-over-HTTPS credentials) for Claude?"; then
        # ${HOME} stays literal on purpose: firejail expands it in claude.local.
        # shellcheck disable=SC2016
        lines+=('whitelist-ro ${HOME}/.netrc')
    fi

    ssh_keys=()
    for key in id_ed25519 id_ecdsa id_rsa id_dsa; do
        [[ -f "${home}/.ssh/${key}" ]] && ssh_keys+=("${key}")
    done
    if [[ ${#ssh_keys[@]} -gt 0 ]] &&
        confirm "Whitelist SSH private keys (${ssh_keys[*]}) for git push over SSH?"; then
        for key in "${ssh_keys[@]}"; do
            lines+=("whitelist-ro \${HOME}/.ssh/${key}")
        done
        # SSH also needs these to function: known_hosts for host-key
        # verification, config for identity/host mappings. Without them git over
        # SSH fails or hangs on an undeliverable prompt.
        lines+=("whitelist-ro \${HOME}/.ssh/known_hosts")
        [[ -f "${home}/.ssh/config" ]] && lines+=("whitelist-ro \${HOME}/.ssh/config")
    fi

    if [[ ${#lines[@]} -gt 0 ]]; then
        write_local_lines "${lines[@]}"
        echo "Whitelisted ${#lines[@]} credential path(s) in ${local_config}."
    fi
else
    echo "Non-interactive shell; skipping the optional credential whitelist prompts."
    echo "Add e.g. 'whitelist-ro \${HOME}/.netrc' to ${local_config} manually if Claude needs it."
fi

echo "Restart paseo (it reads the config only at startup), then pick \"Claude (firejail)\" instead of \"Claude\" when creating a new workspace."
