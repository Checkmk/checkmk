#!/bin/bash
#
# This script decrypts version 04 ("SHA256_MAC") and version 05 ("PBKDF2_MAC"), agent legacy encryption.
# Note: This does not work with real-time-check output!
#
#
# Usage:
#   echo "Agent output message" | ./encrypt.sh v05 "super secret password" | ./decrypt.sh "super secret password"
# or
#   cmk-agent-ctl dump | ./decrypt.sh "super secret password"
#
#
# The decryption scheme is as follows:
#
#   password, [version:salt:mac:ciphertext] <- args
#
#   key, IV <- version_specific_kdf( salt, password )
#
#   validate_hmac_sha256( key, iv:ciphertext, mac )
#   // Abort if MAC validation failed.
#
#   result <- aes_256_cbc_decrypt( key, IV, ciphertext )

split_blob() {
    local blob="$1"
    local version_hex salt_hex mac_hex ct_hex

    # Split the BLOB: [ 2 bytes version : 8 bytes salt : 32 bytes mac : ciphertext ]
    # Doubled for hex encoding.
    version_hex="${blob:0:4}"
    salt_hex="${blob:4:16}"
    mac_hex="${blob:20:64}"
    ct_hex="${blob:84}"

    echo "$version_hex" "$salt_hex" "$mac_hex" "$ct_hex"
}

check_mac_and_decrypt() {
    local mac_hex="$1"
    local ct_hex="$2"
    local key_hex="$3"
    local iv_hex="$4"

    local new_mac
    new_mac=$(hex_decode "$iv_hex$ct_hex" |
        openssl dgst -sha256 -mac HMAC -macopt hexkey:"$key_hex" -hex | awk '{print $2}')

    if [ "$new_mac" != "$mac_hex" ]; then
        echo >&2 "Error: HMAC verification failed."
        exit 1
    fi

    hex_decode "$ct_hex" | openssl enc -aes-256-cbc -d -K "$key_hex" -iv "$iv_hex"
}

kdf_v04() {
    local passwd="$1"
    local salt_hex="$2"

    parse_kdf_output "$(openssl enc -aes-256-cbc -md sha256 -k "$passwd" -S "$salt_hex" -P)"
}

kdf_v05() {
    local passwd="$1"
    local salt_hex="$2"

    parse_kdf_output "$(openssl enc -aes-256-cbc -md sha256 -pbkdf2 -iter 600000 -k "$passwd" -S "$salt_hex" -P)"
}

main() {
    local passwd="$1"
    if [ -z "$passwd" ]; then
        echo >&2 "No password provided. Aborting."
        exit 1
    fi

    read -r version_hex salt_hex mac_hex ct_hex <<<"$(split_blob "$(cat | hex_encode)")"

    local key_hex iv_hex
    if [ "$version_hex" -eq "3035" ]; then
        OPENSSL_VERSION=$(openssl version | awk '{print $2}' | awk -F . '{print (($1 * 100) + $2) * 100+ $3}')
        if [ ! "${OPENSSL_VERSION}" -ge 10101 ]; then
            echo >&2 "OpenSSL version 1.1.1 or greater is required. Found $(openssl version)."
            exit 1
        fi

        read -r _ key_hex iv_hex <<<"$(kdf_v05 "$passwd" "$salt_hex")"

    elif [ "$version_hex" -eq "3034" ]; then
        OPENSSL_VERSION=$(openssl version | awk '{print $2}' | awk -F . '{print (($1 * 100) + $2) * 100+ $3}')
        if [ ! "${OPENSSL_VERSION}" -ge 10000 ]; then
            echo >&2 "OpenSSL version 1.0.0 or greater is required. Found $(openssl version)."
            exit 1
        fi

        read -r _ key_hex iv_hex <<<"$(kdf_v04 "$passwd" "$salt_hex")"

    else
        echo >&2 "Invalid encryption scheme version."
        exit 1
    fi

    check_mac_and_decrypt "$mac_hex" "$ct_hex" "$key_hex" "$iv_hex"
}

# shellcheck source=doc/treasures/agent_legacy_encryption/common.sh
. "$(dirname "${BASH_SOURCE[0]}")"/common.sh
main "$@"
