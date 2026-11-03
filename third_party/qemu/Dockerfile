# Build environment for the static QEMU (create-archive). Only the toolchain
# comes from Alpine (musl libc.a and libgcc end up in the binaries); every
# library linked into QEMU is built from a pinned source tarball (sources.txt).
# curl fetches the sources and publishes the result.
#
# Built with kaniko by buildscripts/scripts/build-qemu-builder-image.groovy
# and pushed to Harbor; the QEMU build runs in the image pinned in
# builder-image.txt, never in a fresh build of this file. The base is pinned
# by digest in Harbor too (Alpine 3.22.0).
FROM int-registry.lan.checkmk.net/ci-qemu/alpine:3.22.0@sha256:e9e9d51e25e4343f56b64d5ef1717234ec62241d93bf59734c53b4108b5c19ca

RUN apk add --no-cache \
    bash \
    binutils \
    bison \
    bzip2 \
    coreutils \
    curl \
    file \
    flex \
    gcc \
    linux-headers \
    make \
    meson \
    musl-dev \
    musl-libintl \
    perl \
    pkgconf \
    py3-packaging \
    py3-pip \
    py3-setuptools \
    py3-wheel \
    python3 \
    samurai \
    tar \
    xz \
    zstd
