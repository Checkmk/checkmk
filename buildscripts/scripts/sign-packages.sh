#!/bin/bash
set -e

TARGET=.
VERSION=$CMK_VERS
KEY_ID=434DAC48C4503261
KEY_DESC="Check_MK Software Release Signing Key (2018) <feedback@check-mk.org>"

if [ -z "$VERSION" ]; then
    echo "set CMK_VERS VERSION"
    echo "Beispiel: CMK_VERS=2018.01.19 $0"
    exit 1
fi

if [ -z "$GPG_PASSPHRASE" ]; then
    echo "ERROR: \$GPG_PASSPHRASE must be given via environment"
    exit 1
fi

export GNUPGHOME=/bauwelt/etc/.gnupg

echo "Sign RPM packages..."
echo "$GPG_PASSPHRASE" | \
    rpm \
    	-D "%_signature gpg" \
        -D "%_gpg_path $GNUPGHOME" \
        -D "%_gpg_name Check_MK Software Release Signing Key (2018) <feedback@check-mk.org>" \
	-D "%__gpg /usr/bin/gpg " -D "%_gpg_sign_cmd_extra_args --batch --passphrase-fd=0 --passphrase-repeat=0 --pinentry-mode loopback" \
	--resign \
	$TARGET/*.rpm

echo "Verify signed RPM packages..."
for RPM in $TARGET/$VERSION/*.rpm; do
    rpm -qp $RPM --qf='%-{NAME} %{SIGPGP:pgpsig}\n'
    if ! rpm -qp $RPM --qf='%-{NAME} %{SIGPGP:pgpsig}\n' | grep -i "Key ID $KEY_ID"; then
        echo "ERROR: RPM not signed: $RPM"
    fi
done

echo "Sign DEB packages..."
(
    echo set timeout -1;\
    echo spawn dpkg-sig -p --sign builder -k $KEY_ID $TARGET/$VERSION/*.deb; \
    echo expect -exact \"The passphrase for ${KEY_ID}:\";\
    echo send -- \"$GPG_PASSPHRASE\\r\";\
    echo expect eof;\
) | expect

echo "Verify singed DEB packages..."
for DEB in $TARGET/*.deb; do
    dpkg-sig --verify $DEB
done

# Hashes der kopierten Dateien ablegen
# (werden später auf der Webseite angezeigt)
echo "Create HASHES file..."
sha256sum *.{cma,tar.gz,rpm,deb,cmk} > HASHES
