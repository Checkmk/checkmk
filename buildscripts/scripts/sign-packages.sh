#!/bin/bash
set -e -o pipefail

FILE_PATH=$1
KEY_ID=434DAC48C4503261
KEY_DESC="Check_MK Software Release Signing Key (2018) <feedback@check-mk.org>"

if [ -z "$FILE_PATH" ]; then
    echo "Call with: $0 FILE_PATH"
    echo "Example: $0 /path/to/check-mk-enterprise-1.6.0b1.demo_0.bionic_amd64.deb"
    exit 1
fi

if [ -z "$GPG_PASSPHRASE" ]; then
    echo "ERROR: \$GPG_PASSPHRASE must be given via environment"
    exit 1
fi

# /bauwelt/etc/.gnupg is mounted in RO mode, but the following gpg commands need RW access
# to the directory. Copy the contents to the container for exclusive + RW access
cp -a /bauwelt/etc/.gnupg /gnupg
export GNUPGHOME=/gnupg

function is_already_signed() {
    if [[ "$FILE_PATH" == *rpm ]]; then
        if rpm -qp "$FILE_PATH" --qf='%-{NAME} %{SIGPGP:pgpsig}\n' | grep -i "Key ID $KEY_ID"; then
            return 0
        fi
        return 1
    elif [[ "$FILE_PATH" == *deb ]]; then
        if dpkg-sig --verify "$FILE_PATH" >/dev/null; then
            return 0
        fi
        return 1
    fi

    echo "ERROR: Unknown package type: $FILE_PATH"
    exit 1
}

function sign_package() {
    if [[ "$FILE_PATH" == *rpm ]]; then
        echo "$GPG_PASSPHRASE" |
            rpm \
                -D "%_signature gpg" \
                -D "%_gpg_path $GNUPGHOME" \
                -D "%_gpg_name $KEY_DESC" \
                -D "%__gpg /usr/bin/gpg " -D "%_gpg_sign_cmd_extra_args --batch --passphrase-fd=0 --passphrase-repeat=0 --pinentry-mode loopback" \
                --resign \
                "$FILE_PATH"
        return 0
    elif [[ "$FILE_PATH" == *deb ]]; then
        if ! echo "$GPG_PASSPHRASE" |
            dpkg-sig -p \
                -g '--passphrase-fd=0 --passphrase-repeat=0 --pinentry-mode loopback' \
                --sign builder -k $KEY_ID "$FILE_PATH"; then
            return 1
        fi
        return 0
    fi

    echo "ERROR: Unknown package type: $FILE_PATH"
    exit 1
}

#
# MAIN
#

if [[ "$FILE_PATH" == *cma ]]; then
    echo "+ Not signing CMA packages at the moment"
    exit 0
fi

if is_already_signed; then
    echo "+ No need to sign $FILE_PATH, is already signed"
    exit 0
fi

for TRY in $(seq 5); do
    echo "+ Signing $FILE_PATH (Try $TRY)..."
    if ! sign_package; then
        echo "ERROR: Signing failed"
        sleep 1
        continue
    fi

    echo "+ Verify signature of $FILE_PATH..."
    if is_already_signed; then
        echo "$FILE_PATH has been signed"
        break
    fi

    echo "ERROR: $FILE_PATH not signed"
    if [ "$TRY" -eq 5 ]; then
        echo "Giving up."
        exit 1
    fi

    sleep 1
done

# TODO
## Hashes der kopierten Dateien ablegen (werden später auf der Webseite angezeigt)
#echo "+ Create HASHES file..."
#sha256sum -- $TARGET/*.cma >>$TARGET/HASHES || true
#sha256sum -- $TARGET/*.tar.gz >>$TARGET/HASHES || true
#sha256sum -- $TARGET/*.rpm >>$TARGET/HASHES || true
#sha256sum -- $TARGET/*.deb >>$TARGET/HASHES || true
#sha256sum -- $TARGET/*.cmk >>$TARGET/HASHES || true
