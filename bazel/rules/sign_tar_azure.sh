#!/usr/bin/env bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The action of sign_tar_azure (sign_azure.bzl): Authenticode-signs every file of
# a flat tar via Azure Artifact Signing and packs the signed files into a new tar.
#
# Usage: sign_tar_azure.sh LIB PSIGN OSSLSIGNCODE CREDENTIALS_FILE IN_TAR OUT_TAR ROOT_PEM...
#
# CREDENTIALS_FILE holds one KEY=VALUE line per AZURE_ARTIFACT_SIGNING_* setting
# (see azure_signing.sh). It is read here, never sourced, and its contents are
# never printed.
set -euo pipefail

lib="$1"
psign="$2"
osslsigncode="$3"
credentials_file="$4"
in_tar="$5"
out_tar="$(pwd)/$6"
shift 6

# shellcheck disable=SC1090,SC1091 # azure_signing.sh, passed in by the caller
source "$lib"

if [ ! -f "$credentials_file" ]; then
    echo "error: Azure signing credentials file does not exist: $credentials_file" >&2
    exit 2
fi
while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
        "" | "#"*) continue ;;
    esac
    key="${line%%=*}"
    if [[ " ${AZURE_SIGNING_VARS[*]} " != *" $key "* ]]; then
        echo "error: unexpected key in $credentials_file: $key" >&2
        exit 2
    fi
    export "$key=${line#*=}"
done <"$credentials_file"

WORK="$(mktemp -d)" # 0700
trap 'rm -rf "$WORK"' EXIT
azure_signing_init "$psign" "$osslsigncode" "$WORK" "$@"

mkdir "$WORK/files"
tar -xf "$in_tar" -C "$WORK/files"
mapfile -t files < <(find "$WORK/files" -type f | sort)
azure_sign_files "${files[@]}"

# Same layout as the input: flat, no directory entries.
(
    cd "$WORK/files"
    find . -type f -printf '%P\n' | sort |
        tar --owner=0 --group=0 --numeric-owner --mtime='2026-01-01 00:00:00Z' \
            -cf "$out_tar" -T -
)
