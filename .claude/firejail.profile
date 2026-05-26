# claude.firejail.profile

# ============================================================================
# SUPPRESS DEBUG MESSAGES
# ============================================================================

quiet

# ============================================================================
# SECURITY HARDENING
# ============================================================================

# Drop all capabilities - Claude doesn't need elevated privileges
caps.drop all

# Prevent privilege escalation
nonewprivs
noroot

# Enable seccomp syscall filtering with default blocklist
seccomp

# Disable potentially dangerous features
nodvd
nosound
no3d
notv
nou2f
novideo
nogroups

# Memory protections
# memory-deny-write-execute  # Uncomment if Claude works with it

# ============================================================================
# FILESYSTEM ISOLATION
# ============================================================================

# Start with a restrictive base
noblacklist ${HOME}/.gitconfig
noblacklist ${HOME}/.config/git
noblacklist ${HOME}/.ssh          # needed for known_hosts whitelist to work
noblacklist /usr/bin/ssh          # needed if you want git over SSH
include disable-common.inc
include disable-programs.inc
# include disable-shell.inc # Claude relies on this so disabled

# Private temporary filesystem (isolated /tmp)
private-tmp

# Minimal /dev (only null, zero, full, random, urandom, tty, etc.)
private-dev

# Disable access to removable media
disable-mnt

# ============================================================================
# WHITELIST - WRITABLE PATHS
# ============================================================================

# Claude's configuration and state directory
whitelist ${HOME}/.claude
mkdir ${HOME}/.claude

whitelist ${HOME}/.claude.json
mkfile ${HOME}/.claude.json

# Allow Bazelisk to download, persist, and execute Bazel binaries
whitelist ${HOME}/.cache/bazelisk
mkdir ${HOME}/.cache/bazelisk

# Allow Bazel to utilize its build and output cache
whitelist ${HOME}/.cache/bazel
mkdir ${HOME}/.cache/bazel

# Allow Java to run inside the sandbox
whitelist ${HOME}/.java-caller
mkdir ${HOME}/.java-caller

# NPM cache for package operations
whitelist ${HOME}/.npm
mkdir ${HOME}/.npm

# Pre-commit hook environments cache
whitelist ${HOME}/.cache/pre-commit
mkdir ${HOME}/.cache/pre-commit

# If you leverage git worktrees as part of your daily routine
# we recommend adding your whitelist entries to ~/.config/firejail/claude.local
# instead of editing this file. Firejail automatically includes claude.local
# after this profile, so your customizations survive profile updates.
#
# Example ~/.config/firejail/claude.local:
#   whitelist ${HOME}/git/checkmk
#   mkdir ${HOME}/git/checkmk
#
#   whitelist ${HOME}/git/checkmk-claude
#   mkdir ${HOME}/git/checkmk-claude


# ============================================================================
# WHITELIST - READ-ONLY PATHS
# ============================================================================

# Git configuration
whitelist-ro ${HOME}/.gitconfig
whitelist-ro ${HOME}/.config/git

# SSH configuration (mostly for git operations)
whitelist-ro ${HOME}/.ssh/known_hosts
# To allow SSH push or NETRC access, add entries to ~/.config/firejail/claude.local, e.g.:
#   whitelist-ro ${HOME}/.ssh/id_ed25519
#   whitelist-ro ${HOME}/.ssh/id_rsa
#   whitelist-ro ${HOME}/.netrc

# Node.js version managers (read-only access to runtime)
whitelist-ro ${HOME}/.nvm
whitelist-ro ${HOME}/.volta
whitelist-ro ${HOME}/.local

# pyenv - Python version manager (provides pre-commit and other Python tools)
whitelist-ro ${HOME}/.pyenv


# ============================================================================
# CUSTOM USER CONFIGURATION
# ============================================================================

include ${HOME}/.config/firejail/claude.local

# ============================================================================
# NETWORK
# ============================================================================

# Network access is REQUIRED for Claude API calls
# Do not add: net none

# DNS access
# (enabled by default)

# ============================================================================
# ENVIRONMENT
# ============================================================================

# Preserve essential environment variables
# (firejail preserves most by default, but we're explicit)

# ============================================================================
# D-BUS
# ============================================================================

# Disable D-Bus access (Claude doesn't need desktop integration)
dbus-user none
dbus-system none

# ============================================================================
# ADDITIONAL HARDENING (OPTIONAL)
# ============================================================================

# Uncomment these for additional security at potential cost of functionality:

# Disable all network except specific hosts:
# netfilter /etc/firejail/claude-net.filter

# Private /etc (may break some functionality):
# private-etc alternatives,ca-certificates,crypto-policies,host.conf,hostname,hosts,ld.so.cache,ld.so.conf,ld.so.conf.d,ld.so.preload,locale,locale.alias,locale.conf,localtime,login.defs,mime.types,nsswitch.conf,passwd,pki,protocols,resolv.conf,rpc,services,ssl,xdg

# Restrict /proc information:
# private-proc
