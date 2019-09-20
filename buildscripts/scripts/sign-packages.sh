#!/bin/bash
set -e

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

if [[ "$FILE_PATH" == *rpm ]]; then
    echo "+ Sign RPM packages..."
    echo "$GPG_PASSPHRASE" |
        rpm \
            -D "%_signature gpg" \
            -D "%_gpg_path $GNUPGHOME" \
            -D "%_gpg_name $KEY_DESC" \
            -D "%__gpg /usr/bin/gpg " -D "%_gpg_sign_cmd_extra_args --batch --passphrase-fd=0 --passphrase-repeat=0 --pinentry-mode loopback" \
            --resign \
            "$FILE_PATH"

    echo "Verify signed RPM packages..."
    rpm -qp "$FILE_PATH" --qf='%-{NAME} %{SIGPGP:pgpsig}\n'
    if ! rpm -qp "$FILE_PATH" --qf='%-{NAME} %{SIGPGP:pgpsig}\n' | grep -i "Key ID $KEY_ID"; then
        echo "ERROR: RPM not signed: $FILE_PATH"
        exit 1
    fi
    exit 0
fi

if [[ "$FILE_PATH" == *deb ]]; then
    echo "+ Sign DEB packages..."
    echo "$GPG_PASSPHRASE" |
        dpkg-sig -p \
            -g '--batch --no-tty --passphrase-fd=0 --passphrase-repeat=0 --pinentry-mode loopback' \
            --sign builder -k $KEY_ID \
            "$FILE_PATH"

    echo "Verify singed DEB packages..."
    dpkg-sig --verify "$FILE_PATH"

    exit 0
fi

# TODO
## Hashes der kopierten Dateien ablegen (werden später auf der Webseite angezeigt)
#echo "+ Create HASHES file..."
#sha256sum -- $TARGET/*.cma >>$TARGET/HASHES || true
#sha256sum -- $TARGET/*.tar.gz >>$TARGET/HASHES || true
#sha256sum -- $TARGET/*.rpm >>$TARGET/HASHES || true
#sha256sum -- $TARGET/*.deb >>$TARGET/HASHES || true
#sha256sum -- $TARGET/*.cmk >>$TARGET/HASHES || true
