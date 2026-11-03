#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Runs WiX under the pinned wine to link MSIs on Linux. Sourced by the
# per-package scripts of package_msi.bzl, which consume the rule's arguments
# with:
#
#   source "$1"
#   shift
#   package_msi_init "$@"
#   set -- "${PACKAGE_MSI_ARGS[@]}"
#
# package_msi_init stages the inputs to $STAGE and sets OUT_MSI, CMK_VERSION
# and MSI_PACKAGE (the Bazel package of the rule); the script then runs
# setup_wine_prefix, wix and stop_wine, and maybe patch_msi.

# shellcheck disable=SC2034 # sets the variables for the sourcing scripts
package_msi_init() {
    # The WiX tools stay inside @wix3: they are managed assemblies that probe for
    # wix.dll and the extensions next to the exe they were launched from.
    CANDLE="$(realpath "$1")"   # @wix3//:candle
    LIGHT="$(realpath "$2")"    # @wix3//:light
    MONO_MSI="$(realpath "$3")" # @wine_mono//file
    WINE="$(realpath "$4")"     # @wine_linux_x86_64//:wine_bin
    MSIBUILD="$(realpath "$5")" # @msitools//:msibuild, for the post-link patching
    # Colon-separated directories with msibuild's non-system runtime libraries
    # (libmsi, libgsf); absolutized to survive a cd.
    local dir dirs
    MSIBUILD_LIBS=""
    IFS=: read -ra dirs <<<"$6"
    for dir in "${dirs[@]}"; do
        MSIBUILD_LIBS="${MSIBUILD_LIBS:+${MSIBUILD_LIBS}:}$(realpath "$dir")"
    done
    OUT_MSI="$(realpath -m "$7")"
    CMK_VERSION="$(cat "$8")"
    MSI_PACKAGE="$9"
    local count="${10}"
    shift 10

    # Run headless even on a desktop: with a display reachable,
    # winex11/winewayland would connect to it (and can flash windows or
    # pull in GUI state).
    unset DISPLAY WAYLAND_DISPLAY

    TMP=$(mktemp -d)
    trap 'rm -rf "$TMP"' EXIT

    # Stage the workspace layout the WiX sources expect (their File Sources
    # are relative paths like ../script/install_relay.sh).
    STAGE="$TMP/stage"
    local i
    for ((i = 0; i < count; i++)); do
        mkdir -p "$(dirname "$STAGE/$2")"
        cp -L "$1" "$STAGE/$2"
        shift 2
    done
    chmod -R u+w "$STAGE"

    PACKAGE_MSI_ARGS=("$@")
}

# Call after the last change to the stage, before linking.
normalize_stage_mtimes() {
    # Keeps the artifact deterministic.
    find "$STAGE" -exec touch -t 202601010000.00 {} +
}

setup_wine_prefix() {
    export WINEPREFIX="$TMP/wineprefix" WINEDEBUG=-all HOME="$TMP"
    export XDG_RUNTIME_DIR="$TMP/xdg"
    mkdir -p "$XDG_RUNTIME_DIR"
    chmod 700 "$XDG_RUNTIME_DIR"

    # WINEDLLOVERRIDES silences the "Mono is not installed" dialog during the init.
    WINEDLLOVERRIDES="mscoree=" "$WINE" wineboot --init >"$TMP/wineboot.log" 2>&1 || true
    if ! "$WINE" msiexec /i "$MONO_MSI" /qn >"$TMP/wine-mono.log" 2>&1; then
        echo "error: installing wine-mono failed; wineboot + msiexec output:" >&2
        cat "$TMP/wineboot.log" "$TMP/wine-mono.log" >&2
        exit 1
    fi
}

wix() {
    # Drop wine's own chatter; WiX errors still fail via exit code.
    "$WINE" "$@" \
        2> >(grep -viE "^wine:|fixme:|err:(mscoree|winediag|hid|setupapi)" >&2 || true)
}

stop_wine() {
    "$(dirname "$WINE")/wineserver" -k >/dev/null 2>&1 || true
}

# Usage: patch_msi <msi> <package code or ""> [msibuild args...]
patch_msi() {
    local msi="$1" package_code="$2"
    shift 2

    # An IDT: three header lines, then tab-separated rows.
    # Importing _SummaryInformation merges with the existing property stream.
    {
        printf 'PropertyId\tValue\r\n'
        printf 'i2\tl255\r\n'
        printf '_SummaryInformation\tPropertyId\r\n'
        if [ -n "$package_code" ]; then
            printf '9\t%s\r\n' "$package_code"
        fi
        # The creating application: light under wine fails to determine
        # its own FileVersion (keep in sync with the @wix3 pin).
        printf '18\tWindows Installer XML Toolset (3.14.1.8722)\r\n'
    } >"$TMP/_SummaryInformation.idt"

    LD_LIBRARY_PATH="$MSIBUILD_LIBS" "$MSIBUILD" "$msi" "$@" \
        -i "$TMP/_SummaryInformation.idt"
}
