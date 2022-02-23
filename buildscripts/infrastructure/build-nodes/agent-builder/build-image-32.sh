#!/bin/bash -ex
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

### Build a docker image for ubuntu i386.

### settings
ARCHITECTURE="i386"
DISTRO="feisty"
CHROOT_PATH="/var/chroot/$DISTRO"
MIRROR='http://old-releases.ubuntu.com/ubuntu'
docker_image="32bit/ubuntu:$DISTRO"

### make sure that the required tools are installed
packages="debootstrap schroot apparmor"
# which docker || packages="$packages docker.io"
# apt-get install -y $packages

### install a minbase system with debootstrap
export DEBIAN_FRONTEND=noninteractive
package_names=(
    "make"
    "openssl"
    "libssl-dev"
    "libreadline5-dev"
    "libsqlite3-dev"
    "libbz2-dev"
    "ca-certificates"
    "gcc"
    "locales"
    "pkg-config"
    "wget"
)
packages=$(
    IFS=,
    echo "${package_names[*]}"
)
# TODO: Would use --force-check-gpg, but not supported on wheezy (root server)
debootstrap \
    --components=main,universe \
    --include="$packages" \
    --arch $ARCHITECTURE $DISTRO $CHROOT_PATH $MIRROR

## Nun ein kleiner Hack um zu verhindern, dass beim Installieren der Pakete
# die Daemonen der Pakete gestartet werden. Ist nicht dramatisch, erzeugt
# aber doofe Fehlermeldungen.
echo exit 101 >$CHROOT_PATH/usr/sbin/policy-rc.d
chmod +x $CHROOT_PATH/usr/sbin/policy-rc.d

cp /etc/resolv.conf $CHROOT_PATH/etc/resolv.conf

## kill any processes that are running on chroot
chroot_pids=$(for p in /proc/*/root; do ls -l "$p"; done | grep $CHROOT_PATH | cut -d'/' -f3)
# shellcheck disable=SC2086
test -z "$chroot_pids" || (
    kill -9 $chroot_pids
    sleep 2
)

### unmount /proc
umount $CHROOT_PATH/proc || echo "Already unmounted"

### create a tar archive from the chroot directory
tar cfz ubuntu.tgz -C $CHROOT_PATH .

### import this tar archive into a docker image:
# shellcheck disable=SC2002
cat ubuntu.tgz | docker import - $docker_image --message "Build with https://github.com/docker-32bit/ubuntu"

# ### push image to Docker Hub
# docker push $docker_image

### cleanup
rm ubuntu.tgz
rm -rf $CHROOT_PATH
