#!/bin/sh
#
# Build Wine from source and publish the tarball pinned by @wine_linux_x86_64
# to the CI binary-artifacts S3 bucket. This is the from-source replacement for
# the prebuilt Kron4ek binary.
#
# The actual build lives in third_party/wine/create-archive; this script
# handles the "build once, publish, skip if already published" plumbing.
#
# It runs in the wine-builder image (third_party/wine/Dockerfile) which has the
# Wine build toolchain and the AWS CLI baked in on top of the AlmaLinux 8 base
# (glibc floor 2.28), so no privileged/yum step is needed here. See
# buildscripts/scripts/build-wine-from-source.groovy.
#
# The corresponding LGPL source (wine-<version>.tar.xz) is published under the
# same prefix as the binary, so a download of the binary is accompanied by its
# source (LGPL-2.1 section 4).
#
#
# Schema on S3 (mirrors buildscripts/scripts/extract_llvm.sh)
#
# dl/<publisher>/<name>/<version>/<platform>/<arch>/<variant>/<file>
#
#
# Examples
#
# dl/wine/wine/11.0/linux/amd64/wow64/wine-11.0-amd64-wow64.tar.xz
# dl/wine/wine/11.0/linux/amd64/wow64/wine-11.0.tar.xz

set -eu

WINE_VERSION="11.0"
# Keep ARCH and VARIANT in sync with OUT in third_party/wine/create-archive.
ARCH="amd64"
VARIANT="wow64"
ARCHIVE_NAME="wine-${WINE_VERSION}-${ARCH}-${VARIANT}.tar.xz"
# Corresponding LGPL source, published alongside the binary.
SOURCE_NAME="wine-${WINE_VERSION}.tar.xz"

PUBLISHER="wine"
NAME="wine"
PLATFORM="linux"

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CREATE_ARCHIVE="${REPO_ROOT}/third_party/wine/create-archive"

if [ -n "${WORKDIR:-}" ]; then
    # For local debugging, won't clean-up after itself.
    mkdir -p "$WORKDIR"
else
    WORKDIR="$(mktemp -d)"
    trap 'rm -rf "$WORKDIR"' EXIT
fi

_aws_path() {
    echo "dl/$PUBLISHER/$NAME/$WINE_VERSION/$PLATFORM/$ARCH/$VARIANT/$1"
}

_public_url() {
    echo "https://${AWS_BUCKET_NAME}.s3.${AWS_DEFAULT_REGION}.amazonaws.com/$(_aws_path "$1")"
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
        --key "$(_aws_path "$1")" \
        --region "$AWS_DEFAULT_REGION" \
        --checksum-mode ENABLED \
        --query 'ChecksumSHA256' \
        >/dev/null 2>&1
}

all_uploaded() {
    _aws_exists "$ARCHIVE_NAME" || return 1
    _aws_exists "$SOURCE_NAME" || return 1
}

upload() {
    file="$(basename "$1")"
    dest="$(_aws_path "$file")"

    # Published artifacts are immutable: a rebuild must never overwrite a name
    # MODULE.bazel already pins, so skip what is already there.
    if _aws_exists "$file"; then
        printf "Skip (already published): %s\n" "$dest"
        return 0
    fi

    printf "Upload: %s -> %s\n" "$1" "$dest"

    # `aws s3 cp` has no --checksum-algorithm option; only the s3api commands do.
    aws s3api put-object \
        --bucket "$AWS_BUCKET_NAME" \
        --key "$dest" \
        --body "$1" \
        --checksum-algorithm SHA256 \
        --region "$AWS_DEFAULT_REGION" \
        >/dev/null
}

main() {
    require_aws
    require_credentials

    if all_uploaded; then
        printf "Nothing to do: Wine %s %s artifacts already present.\n" \
            "$WINE_VERSION" "$VARIANT"
        return 0
    fi

    (cd "$WORKDIR" && "$CREATE_ARCHIVE")

    # Binary artifact + its corresponding LGPL source.
    upload "$WORKDIR/$ARCHIVE_NAME"
    upload "$WORKDIR/$SOURCE_NAME"

    printf "Pin in MODULE.bazel: %s\n" "$(_public_url "$ARCHIVE_NAME")"
}

main "$@"
