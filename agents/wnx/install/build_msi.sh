#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Builds the Windows agent MSI on Linux: WiX under Wine

set -euo pipefail

# Stage the workspace layout Product.wxs expects (its File Sources are
# relative paths like ..\..\..\cmk\plugins\...).
stage_workspace() {
    mkdir -p "$STAGE/agents/wnx" "$STAGE/agents/windows" "$STAGE/cmk" \
        "$STAGE/packages/cmk-plugins/cmk"
    cp -rL agents/wnx/install "$STAGE/agents/wnx/install"
    cp -rL agents/windows/plugins "$STAGE/agents/windows/plugins"
    cp -rL cmk/plugins "$STAGE/cmk/plugins"
    cp -rL packages/cmk-plugins/cmk/plugins "$STAGE/packages/cmk-plugins/cmk/plugins"
    chmod -R u+w "$STAGE"

    mkdir -p "$STAGE/agents/wnx/build/check_mk_service/x64/Release" "$STAGE/artefacts"
    cp -L "$SERVICE_EXE" "$STAGE/agents/wnx/build/check_mk_service/x64/Release/check_mk_service.exe"
    cp -L "$AGENT_CTL_EXE" "$STAGE/artefacts/cmk-agent-ctl.exe"

    # Normalize the staged mtimes to keep the artifact deterministic.
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

link_msi() {
    export SignedPluginsFolder="Z:${STAGE//\//\\}\\agents\\windows\\plugins" # See Product.wxs.

    cd "$STAGE/agents/wnx/install"
    mkdir -p obj bin
    wix "$CANDLE" -ext WixUtilExtension -out 'obj\InstallMainDialog.wixobj' InstallMainDialog.wxs
    wix "$CANDLE" -ext WixUtilExtension -out 'obj\InstallFolderDialog.wixobj' InstallFolderDialog.wxs
    # -sw1091: Package/@Id is pinned on purpose, patch_msi() replaces the package code after linking.
    wix "$CANDLE" -sw1091 -ext WixUtilExtension -out 'obj\Product.wixobj' Product.wxs
    # -sval: We require a real windows to run ICE custom actions see CMK-37488.
    wix "$LIGHT" -ext WixUIExtension -ext WixUtilExtension -sval -spdb \
        -o 'bin\check_mk_agent.msi' \
        'obj\Product.wixobj' 'obj\InstallMainDialog.wixobj' 'obj\InstallFolderDialog.wixobj'
    cd - >/dev/null

    "$(dirname "$WINE")/wineserver" -k >/dev/null 2>&1 || true
}

patch_msi() {
    local msi="$STAGE/agents/wnx/install/bin/check_mk_agent.msi"
    local cmk_version package_code

    cmk_version="$(cat "$VERSION_FILE")"
    # Fresh per build, Product.wxs pins a fixed marker GUID (see NOTE 2 in Product.wxs).
    package_code="{$(tr '[:lower:]' '[:upper:]' </proc/sys/kernel/random/uuid)}"

    # An IDT: three header lines, then tab-separated rows.
    # Importing _SummaryInformation merges with the existing property stream.
    {
        printf 'PropertyId\tValue\r\n'
        printf 'i2\tl255\r\n'
        printf '_SummaryInformation\tPropertyId\r\n'
        printf '9\t%s\r\n' "$package_code" # the package code
        # The creating application: light under wine fails to determine
        # its own FileVersion (keep in sync with the @wix3 pin).
        printf '18\tWindows Installer XML Toolset (3.14.1.8722)\r\n'
    } >"$TMP/_SummaryInformation.idt"

    LD_LIBRARY_PATH="$MSIBUILD_LIBS" "$MSIBUILD" "$msi" \
        -q "UPDATE Property SET Property.Value='${cmk_version}' WHERE Property.Property='ProductVersion'" \
        -i "$TMP/_SummaryInformation.idt"
}

main() {
    OUT_MSI="$1"
    # The WiX tools stay inside @wix3: they are managed assemblies that probe for
    # wix.dll and the extensions next to the exe they were launched from.
    CANDLE="$(realpath "$2")"   # @wix3//:candle
    LIGHT="$(realpath "$3")"    # @wix3//:light
    SERVICE_EXE="$4"            # cross-built check_mk_service.exe
    AGENT_CTL_EXE="$5"          # cross-built cmk-agent-ctl.exe
    MONO_MSI="$(realpath "$6")" # @wine_mono//file
    WINE="$(realpath "$7")"     # @wine_linux_x86_64//:wine_bin
    VERSION_FILE="$8"           # the Checkmk version, stamped from --cmk_version
    MSIBUILD="$(realpath "$9")" # @msitools//:msibuild, for the post-link patching
    # ${10}...: directories with msibuild's non-system runtime libraries
    # (libmsi, libgsf); joined into its LD_LIBRARY_PATH, absolutized to
    # survive the cd.
    local dir
    MSIBUILD_LIBS=""
    for dir in "${@:10}"; do
        MSIBUILD_LIBS="${MSIBUILD_LIBS:+${MSIBUILD_LIBS}:}$(realpath "$dir")"
    done

    # Run headless even on a desktop: with a display reachable,
    # winex11/winewayland would connect to it (and can flash windows or
    # pull in GUI state).
    unset DISPLAY WAYLAND_DISPLAY

    TMP=$(mktemp -d)
    trap 'rm -rf "$TMP"' EXIT
    STAGE="$TMP/stage"

    stage_workspace
    setup_wine_prefix
    link_msi
    patch_msi

    cp "$STAGE/agents/wnx/install/bin/check_mk_agent.msi" "$OUT_MSI"
}

main "$@"
