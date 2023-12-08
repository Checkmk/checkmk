#!/bin/bash
#
# This script performs version 04 ("SHA256_MAC") and version 05 ("PBKDF2_MAC"),
# of the agent legacy encryption.
#
#
# Usage:
#   echo "Agent output message" | ./encrypt.sh v05 "super secret password"
#
#
# The output is raw binary, so consider piping it to hexdump if you want to
# look at it.
# Note that this script does not insert a timestamp behind the version marker,
# so it cannot be used to emulate real-time-check output.
#
#
# The encryption scheme is as follows:
#
#   salt    <- random_salt()
#   key, IV <- version_specific_kdf( salt, password )
#
#   ciphertext <- aes_256_cbc_encrypt( key, IV, message )
#   mac        <- hmac_sha256( key, iv:ciphertext )
#
#   // The output blob is formed as:
#   // - 2 bytes version
#   // - 8 bytes salt
#   // - 32 bytes MAC
#   // - the ciphertext
#   result <- [version:salt:mac:ciphertext]
#

encrypt_then_mac() {
    # Encrypt the input data, calculate a MAC over IV and ciphertext, then
    # print mac and ciphertext.
    local salt_hex="$1"
    local key_hex="$2"
    local iv_hex="$3"
    local ciphertext_b64

    # We need the ciphertext twice: for the mac and for the output. But we can only store it in
    # encoded form because it can contain null bytes.
    ciphertext_b64=$(openssl enc -aes-256-cbc -K "$key_hex" -iv "$iv_hex" | openssl enc -base64)

    (
        hex_decode "$iv_hex"
        echo "$ciphertext_b64" | openssl enc -base64 -d
    ) | openssl dgst -sha256 -mac HMAC -macopt hexkey:"$key_hex" -binary

    echo "$ciphertext_b64" | openssl enc -base64 -d
}

main() {
    local version="$1"
    local passwd="$2"

    if [[ -z "$version" ]] || [[ -z "$passwd" ]]; then
        echo >&2 "Error: password and version must be set."
        exit 1
    fi

    if [ "$version" = "v05" ]; then
        local salt_hex key_hex iv_hex
        read -r salt_hex key_hex iv_hex <<<"$(
            parse_kdf_output "$(openssl enc -aes-256-cbc -md sha256 -pbkdf2 -iter 600000 -k "${passwd}" -P)"
        )"

        printf "05"
        hex_decode "$salt_hex"
        encrypt_then_mac "$salt_hex" "$key_hex" "$iv_hex"

    elif [ "$version" = "v04" ]; then
        local salt_hex key_hex iv_hex
        read -r salt_hex key_hex iv_hex <<<"$(
            parse_kdf_output "$(openssl enc -aes-256-cbc -md sha256 -k "${passwd}" -P)"
        )"

        printf "04"
        hex_decode "$salt_hex"
        encrypt_then_mac "$salt_hex" "$key_hex" "$iv_hex"

    else
        echo >&2 "Error: invalid version."
        exit 1
    fi
}

# shellcheck source=doc/treasures/agent_legacy_encryption/common.sh
. "$(dirname "${BASH_SOURCE[0]}")"/common.sh
main "$@"
