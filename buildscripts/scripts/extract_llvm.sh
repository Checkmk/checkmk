#!/bin/sh
#
# Download LLVM from upstream, upload clang-tidy, clang-format, clang's
# resource-dir headers, and the toolchain bundle consumed by the hermetic
# cc toolchains to our S3 bucket.
#
#
# Schema on S3
#
# dl/<publisher>/<name>/<version>/<platform>/<arch>/<variant>/<file>
#
#   <name>: logical artifact name, e.g., `clang-format`
#   <version>: upstream or internal release version, e.g., 21.1.8
#   <platform>: linux, macos, windows
#   <arch>: amd64, arm64, armv7
#   <variant>: debian, ubuntu22.04, centos7, suse15, static, musl
#   <file>: final executable or archive filename
#
#
# Examples
#
# dl/llvm/clang-tidy/21.1.8/linux/amd64/static/bin
# dl/llvm/clang-format/21.1.8/linux/amd64/static/bin
# dl/llvm/clang-resource-headers/21.1.8/linux/amd64/static/clang-resource-headers.tar.gz
# dl/llvm/llvm-toolchain/21.1.8/linux/amd64/static/llvm-toolchain.tar.gz

set -eu

LLVM_VERSION="19.1.7"
CLANG_TIDY_BIN="clang-tidy"
CLANG_FORMAT_BIN="clang-format"
CLANG_RESOURCE_HEADERS_NAME="clang-resource-headers"
CLANG_RESOURCE_HEADERS_ARCHIVE="clang-resource-headers.tar.gz"
# Clang's resource dir (containing e.g. stddef.h, mmintrin.h) is named after
# the major version only, e.g. lib/clang/19/include for LLVM_VERSION 19.1.7.
CLANG_RESOURCE_VERSION="${LLVM_VERSION%%.*}"

LLVM_ARCHIVE_BASE="LLVM-$LLVM_VERSION-Linux-X64"
LLVM_ARCHIVE_NAME="$LLVM_ARCHIVE_BASE.tar.xz"

URL="https://github.com/llvm/llvm-project/releases/download/llvmorg-${LLVM_VERSION}/${LLVM_ARCHIVE_NAME}"
SHA256="4a5ec53951a584ed36f80240f6fbf8fdd46b4cf6c7ee87cc2d5018dc37caf679"

CLANG_TIDY="${LLVM_ARCHIVE_BASE}/bin/$CLANG_TIDY_BIN"
CLANG_FORMAT="${LLVM_ARCHIVE_BASE}/bin/$CLANG_FORMAT_BIN"
CLANG_RESOURCE_HEADERS="${LLVM_ARCHIVE_BASE}/lib/clang/${CLANG_RESOURCE_VERSION}/include"

TOOLCHAIN_NAME="llvm-toolchain"
TOOLCHAIN_ARCHIVE="llvm-toolchain.tar.gz"
TOOLCHAIN_PATHS="
    bin/clang
    bin/clang++
    bin/clang-21
    bin/clang-cl
    bin/ld.lld
    bin/ld64.lld
    bin/lld
    bin/lld-link
    bin/llvm-ar
    bin/llvm-lib
    bin/llvm-objcopy
    bin/llvm-objdump
    bin/llvm-rc
    bin/llvm-readobj
    bin/llvm-strip
    include/c++
    include/x86_64-unknown-linux-gnu
    lib/clang/$CLANG_RESOURCE_VERSION/include
    lib/clang/$CLANG_RESOURCE_VERSION/lib/x86_64-unknown-linux-gnu
    lib/x86_64-unknown-linux-gnu
"

if [ -n "${WORKDIR:-}" ]; then
    # For local debugging, won't clean-up after itself.
    mkdir -p "$WORKDIR"
else
    WORKDIR="$(mktemp -d)"
    trap 'rm -rf "$WORKDIR"' EXIT
fi

LLVM_ARCHIVE="$WORKDIR/$LLVM_ARCHIVE_NAME"
DESTDIR="$WORKDIR/out"

download() {
    printf "Download: %s @ %s -> %s\n" "$1" "$2" "$3"
    [ -f "$3" ] || curl -L "$1" --output "$3"
    if [ -n "$2" ]; then
        actual="$(sha256sum "$3" | cut -d' ' -f1)"
        if [ "$actual" != "$2" ]; then
            printf "Error: checksum mismatch for %s: expected %s, got %s\n" "$3" "$2" "$actual" >&2
            exit 1
        fi
    else
        sha256sum "$3"
        echo "Error: Missing checksum" >&2
        exit 1
    fi
}

extract() {
    printf "Extract: %s %s -> $DESTDIR\n" "$1" "$2"
    mkdir -p "$DESTDIR"
    strip_components=$(printf '%s\n' "$2" | tr -cd '/' | wc -c)
    tar -xf "$1" --strip-components="$strip_components" -C "$DESTDIR" "$2"
}

extract_toolchain() {
    printf "Extract: %s toolchain paths -> $DESTDIR/toolchain\n" "$1"
    mkdir -p "$DESTDIR/toolchain"
    for path in $TOOLCHAIN_PATHS; do
        printf '%s/%s\n' "$LLVM_ARCHIVE_BASE" "$path"
    done | tar -xf "$1" -C "$DESTDIR/toolchain" --strip-components=1 --files-from=-
}

# Deterministic archive
pack() {
    out="$1"
    dir="$2"
    shift 2
    printf "Pack: %s -> %s\n" "$dir" "$out"
    tar -C "$dir" \
        --sort=name --owner=0 --group=0 --numeric-owner --mtime=@0 \
        -cf - "$@" | gzip -n >"$out"
    sha256sum "$out"
}

_aws_path() {
    # Hard code linux/amd64/static:  That's where we run the linters.
    echo "dl/llvm/$1/$LLVM_VERSION/linux/amd64/static/$2"
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
    for name in "$CLANG_TIDY_BIN" "$CLANG_FORMAT_BIN"; do
        _aws_exists "$(_aws_path "$name" bin)" || return 1
    done
    _aws_exists "$(_aws_path "$CLANG_RESOURCE_HEADERS_NAME" "$CLANG_RESOURCE_HEADERS_ARCHIVE")" || return 1
    _aws_exists "$(_aws_path "$TOOLCHAIN_NAME" "$TOOLCHAIN_ARCHIVE")" || return 1
}

upload() {
    dest="$(_aws_path "$2" "$3")"

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
        printf "Nothing to do: LLVM %s artifacts already present.\n" "$LLVM_VERSION"
        return 0
    fi

    download "$URL" "$SHA256" "$LLVM_ARCHIVE"

    extract "$LLVM_ARCHIVE" "$CLANG_TIDY"
    upload "$DESTDIR/$CLANG_TIDY_BIN" "$CLANG_TIDY_BIN" "bin"

    extract "$LLVM_ARCHIVE" "$CLANG_FORMAT"
    upload "$DESTDIR/$CLANG_FORMAT_BIN" "$CLANG_FORMAT_BIN" "bin"

    extract "$LLVM_ARCHIVE" "$CLANG_RESOURCE_HEADERS"
    pack "$WORKDIR/$CLANG_RESOURCE_HEADERS_ARCHIVE" "$DESTDIR" include
    upload "$WORKDIR/$CLANG_RESOURCE_HEADERS_ARCHIVE" "$CLANG_RESOURCE_HEADERS_NAME" "$CLANG_RESOURCE_HEADERS_ARCHIVE"

    extract_toolchain "$LLVM_ARCHIVE"
    pack "$WORKDIR/$TOOLCHAIN_ARCHIVE" "$DESTDIR/toolchain" bin include lib
    upload "$WORKDIR/$TOOLCHAIN_ARCHIVE" "$TOOLCHAIN_NAME" "$TOOLCHAIN_ARCHIVE"
}

main "$@"
