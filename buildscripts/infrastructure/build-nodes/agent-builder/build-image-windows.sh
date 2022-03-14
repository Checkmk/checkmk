#!/bin/bash -ex
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

### Build a docker image from Ubuntu 18.04 to build the Legacy Windows agent

DISTRO="bionic"
MIRROR="http://de.archive.ubuntu.com/ubuntu"
CHROOT_PATH="/var/chroot/$DISTRO"
docker_image="agent-builder-windows"

HOSTNAME=cmk-windows-agent-chroot
LC_ALL=en_US.UTF-8 LANGUAGE=en_US.UTF-8 LANG=en_US.UTF-8

export CHROOT_BUILD_DIR="/mnt"

cleanup_chroot() {
    PIDS=$(lsof -Fp $CHROOT_PATH 2>/dev/null | cut -dp -f2)
    # shellcheck disable=2086
    [ -n "$PIDS" ] && kill -9 $PIDS 2>&1

    [ -e $CHROOT_PATH/dev/pts/ptmx ] && umount $CHROOT_PATH/dev/pts && sleep 2
    [ -e $CHROOT_PATH/dev/sda ] && umount $CHROOT_PATH/dev && sleep 2
    [ -e $CHROOT_PATH/proc/self ] && umount $CHROOT_PATH/proc && sleep 2
    [ -e $CHROOT_PATH/mnt ] && umount $CHROOT_PATH/mnt && sleep 2

    if mount | grep $CHROOT_PATH >/dev/null; then
        echo "Error: There are still mounts below $CHROOT_PATH. Terminating."
        exit 1
    fi
}

unset LANG

echo "+ CLEANING UP CHROOT"
cleanup_chroot
rm -rf ${CHROOT_PATH:?}/*

export DEBIAN_FRONTEND=noninteractive
package_names=(
    autoconf
    automake
    build-essential
    ca-certificates
    cabextract
    curl
    gcc
    gettext
    language-pack-en
    lcab
    lcov
    libauthen-sasl-perl
    libc6-dev
    libencode-locale-perl
    libfile-listing-perl
    libfont-afm-perl
    libglib2.0-dev
    libgsf-1-dev
    libgtk2.0-dev
    libhtml-form-perl
    libhtml-format-perl
    libhtml-parser-perl
    libhtml-tagset-perl
    libhtml-tree-perl
    libhttp-cookies-perl
    libhttp-daemon-perl
    libhttp-date-perl
    libhttp-message-perl
    libhttp-negotiate-perl
    libio-html-perl
    libio-socket-ssl-perl
    liblwp-mediatypes-perl
    liblwp-protocol-https-perl
    libmailtools-perl
    libnet-http-perl
    libnet-smtp-ssl-perl
    libnet-ssleay-perl
    libperl-dev
    libpython-stdlib
    libtimedate-perl
    libtool
    liburi-perl
    libwww-perl
    libwww-robotrules-perl
    libxml-parser-perl
    linux-base
    locales
    make
    mingw-w64
    mono-devel
    mono-xbuild
    openssh-client
    openssl
    patch
    perl-openssl-defaults
    pkg-config
    python
    python-minimal
    python-pytest
    python2.7
    ssh-askpass
    unzip
    uuid-dev
    # TODO: Need to install wine separately in order to use --force-overwrite, see
    # https://bugs.launchpad.net/ubuntu/+source/sane-backends/+bug/1725928/
    # Cannot pass --force-overwrite through debootstrap.
    #    wine-stable
)
packages=$(
    IFS=,
    echo "${package_names[*]}"
)

echo "+ INSTALLING SYSTEM (PHASE 1)"

# TODO: Would use --force-check-gpg, but not supported on wheezy (root server)
debootstrap \
    --components=main,universe \
    --include="$packages" \
    --arch amd64 $DISTRO $CHROOT_PATH $MIRROR

echo "+ INSTALLING SYSTEM (PHASE 2)"

# "Disable" apt privilege dropping in chroot
cat $CHROOT_PATH/etc/passwd
sed -ri 's/^_apt:x:[0-9]+:/_apt:x:0:/g' $CHROOT_PATH/etc/passwd
cat $CHROOT_PATH/etc/passwd

# Need to be installed for installation.
cat <<EOF >$CHROOT_PATH/etc/fstab
# created by container build script
/dev/sda1 / ext2 rw,noatime,nodiratime,errors=continue 0 1
EOF

# Prevent startup of daemons during package installation
echo exit 101 >$CHROOT_PATH/usr/sbin/policy-rc.d
chmod +x $CHROOT_PATH/usr/sbin/policy-rc.d

cp /etc/resolv.conf $CHROOT_PATH/etc/resolv.conf

# Deploy fake hostname binary
if [ ! -e $CHROOT_PATH/bin/hostname.bin ]; then
    mv $CHROOT_PATH/bin/hostname{,.bin}
fi
cat <<EOF >$CHROOT_PATH/bin/hostname
echo $HOSTNAME
EOF
chmod +x $CHROOT_PATH/bin/hostname

# Cope with the known bug with libsane1 that wine depends on.
# https://bugs.launchpad.net/ubuntu/+source/sane-backends/+bug/1725928/
# Need to use --force-overwrite with apt-get. This option cannot be passed
# through debootstrap.
chroot $CHROOT_PATH /usr/bin/env bash -c 'apt-get -y -o Dpkg::Options::="--force-overwrite" install wine-stable'

# We need to enable 32bit Wine
chroot $CHROOT_PATH /usr/bin/env bash -c 'dpkg --add-architecture i386 && apt-get update && apt-get -o Dpkg::Options::="--force-overwrite" -y install wine32'

cat <<EOF >$CHROOT_PATH/root/.bashrc
debian_chroot=$(hostname)
PS1='\${debian_chroot:+(\$debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\\$ '
PS1="\[\e]0;\${debian_chroot:+(\$debian_chroot)}\u@\h: \w\a\]\$PS1"
EOF

# Debian pkg installation does not seem to link python executable
if [ ! -h $CHROOT_PATH/usr/bin/python ]; then
    ln -sf python2.7 $CHROOT_PATH/usr/bin/python
fi

mount -o bind . $CHROOT_PATH/$CHROOT_BUILD_DIR/

# Build Google Test and Google Mock
chroot $CHROOT_PATH /usr/bin/env bash -c "$CHROOT_BUILD_DIR/agents/windows/test/build-googletest"

# Extract necessary boost headers
chroot $CHROOT_PATH /usr/bin/env bash -c "$CHROOT_BUILD_DIR/agents/windows/extract-simpleini"

echo "+ CLEANING UP"

# Raeume apt-cache auf
{
    ls $CHROOT_PATH/var/cache/apt/archives/*.deb >/dev/null 2>&1 &&
        rm $CHROOT_PATH/var/cache/apt/archives/*.deb 2>&1
} || true

# Alle Prozesse aus dem chroot killen
cleanup_chroot

### create a tar archive from the chroot directory
tar cfz $docker_image.tgz -C $CHROOT_PATH .

### import this tar archive into a docker image:
# shellcheck disable=SC2002
cat $docker_image.tgz | docker import - $docker_image

### cleanup
rm $docker_image.tgz
rm -rf $CHROOT_PATH
