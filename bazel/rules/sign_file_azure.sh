#!/usr/bin/env bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The action of sign_file_azure (sign_azure.bzl): Authenticode-signs a copy of a
# file via Azure Artifact Signing.
#
# Usage: sign_file_azure.sh LIB PSIGN OSSLSIGNCODE CREDENTIALS_FILE IN OUT ROOT_PEM...
#
# CREDENTIALS_FILE holds one KEY=VALUE line per AZURE_ARTIFACT_SIGNING_* setting
# (see azure_signing.sh).
set -euo pipefail

lib="$1"
psign="$2"
osslsigncode="$3"
credentials_file="$4"
in_file="$5"
out_file="$6"
shift 6

# shellcheck disable=SC1090,SC1091 # azure_signing.sh, passed in by the caller
source "$lib"

azure_signing_load_credentials "$credentials_file"

WORK="$(mktemp -d)" # 0700
trap 'rm -rf "$WORK"' EXIT
azure_signing_init "$psign" "$osslsigncode" "$WORK" "$@"

# Keep the file name: psign may derive the file type from it.
mkdir "$WORK/file"
signed="$WORK/file/$(basename "$out_file")"
cp "$in_file" "$signed"
chmod u+w "$signed"
azure_sign_files "$signed"
cp "$signed" "$out_file"
