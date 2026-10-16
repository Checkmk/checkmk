#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Builds the Windows agent MSI on Linux: WiX under Wine

set -euo pipefail

# shellcheck disable=SC1090,SC1091 # bazel/rules/xcomp/package_msi.sh, see package_msi.bzl
source "$1"
shift
package_msi_init "$@"

link_msi() {
    # See Product.wxs. Unsigned: the scripts are not signed on Linux yet.
    export SignedPluginsFolder='plugins'

    cd "$STAGE/agents/wnx/install"
    mkdir -p obj bin plugins
    tar xf plugins.tar -C plugins
    wix "$CANDLE" -ext WixUtilExtension -out 'obj\InstallMainDialog.wixobj' InstallMainDialog.wxs
    wix "$CANDLE" -ext WixUtilExtension -out 'obj\InstallFolderDialog.wixobj' InstallFolderDialog.wxs
    # -sw1091: Package/@Id is pinned on purpose, patch_msi() replaces the package code after linking.
    wix "$CANDLE" -sw1091 -ext WixUtilExtension -out 'obj\Product.wixobj' Product.wxs
    # -sval: We require a real windows to run ICE custom actions see CMK-37488.
    wix "$LIGHT" -ext WixUIExtension -ext WixUtilExtension -sval -spdb \
        -o 'bin\check_mk_agent.msi' \
        'obj\Product.wixobj' 'obj\InstallMainDialog.wixobj' 'obj\InstallFolderDialog.wixobj'
    cd - >/dev/null
    stop_wine
}

patch_agent_msi() {
    local package_code

    # Fresh per build, Product.wxs pins a fixed marker GUID (see NOTE 2 in Product.wxs).
    package_code="{$(tr '[:lower:]' '[:upper:]' </proc/sys/kernel/random/uuid)}"

    patch_msi "$STAGE/agents/wnx/install/bin/check_mk_agent.msi" "$package_code" \
        -q "UPDATE Property SET Property.Value='${CMK_VERSION}' WHERE Property.Property='ProductVersion'"
}

main() {
    normalize_stage_mtimes
    setup_wine_prefix
    link_msi
    patch_agent_msi

    cp "$STAGE/agents/wnx/install/bin/check_mk_agent.msi" "$OUT_MSI"
}

main
