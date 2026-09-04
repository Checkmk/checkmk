#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Upload gcc-toolchain tarballs to our public S3 bucket.
#
# Schema on S3
#
# dl/<publisher>/<name>/<version>/<platform>/<arch>/<variant>/<file>
#
#   <name>: logical artifact name, e.g., `gcc-toolchain`
#   <version>: upstream or internal release version, e.g., gcc14.4.0-glibc2.28
#   <platform>: linux, macos, windows
#   <arch>: x86_64, amd64, arm64, armv7
#   <variant>: debian, ubuntu22.04, centos7, suse15, static, musl
#   <file>: final executable or archive filename
#
#
# Examples
#
# dl/gnu/gcc-toolchain/gcc14.4.0-glibc2.28-df6cc09a/linux/x86_64/almalinux8/x86_64-checkmk-linux-gnu-gcc14.4.0-glibc2.28.tar.xz
# dl/gnu/gdb/gcc14.4.0-glibc2.28-df6cc09a/linux/x86_64/static/x86_64-checkmk-linux-gnu-gdb.tar.xz

set -eu -o pipefail

# shellcheck source=buildscripts/scripts/gcc-toolchain/common.sh
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"

TOOLCHAIN_NAME="gcc-toolchain"
TOOLCHAIN_VARIANT="almalinux8"
GDB_NAME="gdb"
GDB_VARIANT="static"

usage() {
    echo "Usage: $0 <output-dir>" >&2
    exit 1
}

_aws_path() {
    echo "dl/gnu/$1/$2/linux/x86_64/$3/$4"
}

require_aws() {
    command -v aws >/dev/null 2>&1 || {
        echo "Error: aws CLI not found" >&2
        exit 1
    }
}

require_credentials() {
    if [ -z "${AWS_DEFAULT_REGION:-}" ] || [ -z "${AWS_ACCESS_KEY_ID:-}" ] ||
        [ -z "${AWS_SECRET_ACCESS_KEY:-}" ] || [ -z "${AWS_BUCKET_NAME:-}" ]; then
        echo "Error: Credentials missing" >&2
        exit 1
    fi
}

_aws_exists() {
    aws s3api head-object \
        --bucket "$AWS_BUCKET_NAME" \
        --key "$1" \
        --region "$AWS_DEFAULT_REGION" \
        --checksum-mode ENABLED \
        --query 'ChecksumSHA256' \
        >/dev/null 2>&1
}

all_uploaded() {
    _aws_exists "$(_aws_path "$TOOLCHAIN_NAME" "$TOOLCHAIN_VERSION" "$TOOLCHAIN_VARIANT" "$TARBALL_NAME")" || return 1
    _aws_exists "$(_aws_path "$GDB_NAME" "$TOOLCHAIN_VERSION" "$GDB_VARIANT" "$GDB_TARBALL_NAME")" || return 1
}

upload() {
    local file="$1" name="$2" version="$3" variant="$4" filename="$5"
    local dest
    dest="$(_aws_path "$name" "$version" "$variant" "$filename")"

    printf "Upload: %s -> %s\n" "$file" "$dest"

    # `aws s3 cp` has no --checksum-algorithm option; only the s3api commands do.
    aws s3api put-object \
        --bucket "$AWS_BUCKET_NAME" \
        --key "$dest" \
        --body "$file" \
        --checksum-algorithm SHA256 \
        --region "$AWS_DEFAULT_REGION" \
        >/dev/null
}

main() {
    [ $# -eq 1 ] || usage
    local output_dir
    output_dir="$(readlink -e "$1")"

    require_aws
    require_credentials

    if all_uploaded; then
        printf "Nothing to do: %s artifacts already present.\n" "$TOOLCHAIN_VERSION"
        return 0
    fi

    upload "${output_dir}/${TARBALL_NAME}" "$TOOLCHAIN_NAME" "$TOOLCHAIN_VERSION" "$TOOLCHAIN_VARIANT" "$TARBALL_NAME"
    upload "${output_dir}/${GDB_TARBALL_NAME}" "$GDB_NAME" "$TOOLCHAIN_VERSION" "$GDB_VARIANT" "$GDB_TARBALL_NAME"
}

main "$@"
