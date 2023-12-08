hex_decode() {
    # take a parameter to mimick agent's hex_decode function
    local in="$1"
    printf '%s' "$in" | xxd -r -p
}

hex_encode() {
    hexdump -v -e '16/1 "%02x"' | tr -d ' '
}

parse_kdf_output() {
    local kdf_output="$1"
    local salt_hex key_hex iv_hex
    salt_hex=$(echo "$kdf_output" | grep -oP "(?<=salt=)[0-9A-F]+")
    key_hex=$(echo "$kdf_output" | grep -oP "(?<=key=)[0-9A-F]+")
    iv_hex=$(echo "$kdf_output" | grep -oP "(?<=iv =)[0-9A-F]+")
    # Make sure this rather brittle grepping worked. For example, some openssl update might decide
    # to remove that odd-looking space behind 'iv'.
    # Note that the expected LENGTHS ARE DOUBLED because the values are hex encoded.
    if [ ${#salt_hex} -ne 16 ] || [ ${#key_hex} -ne 64 ] || [ ${#iv_hex} -ne 32 ]; then
        encryption_panic
    fi
    echo "$salt_hex" "$key_hex" "$iv_hex"
}
