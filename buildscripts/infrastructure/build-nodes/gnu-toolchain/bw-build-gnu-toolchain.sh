#!/bin/bash

set -e -o pipefail

GCC_MAJOR="8"
GCC_MINOR="2"
GCC_PATCHLEVEL="0"
BINUTILS_VERSION="2.32"
GDB_VERSION="8.2.1"

GCC_VERSION="${GCC_MAJOR}.${GCC_MINOR}.${GCC_PATCHLEVEL}"
PREFIX="/opt/gcc-${GCC_VERSION}"

BUILD_DIR=/tmp/build-gcc-toolchain


function log() {
    echo "+++ $1"
}

function download-sources() {
    # To avoid repeated downloads of the sources + the prerequisites, we
    # pre-package things together:
    # wget https://ftp.gnu.org/gnu/binutils/binutils-${BINUTILS_VERSION}.tar.gz

    log "Downloading binutils"
    if ! curl -s -O "${NEXUS}binutils-${BINUTILS_VERSION}.tar.gz"; then
        log "File not available from ${NEXUS}. Downloading from upstream"
        curl -s -O https://sourceware.org/pub/binutils/releases/binutils-${BINUTILS_VERSION}.tar.gz
        curl -s -u "${USERNAME}:${PASSWORD}" --upload-file "binutils-${BINUTILS_VERSION}.tar.gz" "${NEXUS}"
    fi

    log "Downloading gcc"
    if ! curl -s -O "${NEXUS}gcc-${GCC_VERSION}-with-prerequisites.tar.gz"; then
        log "File not available from ${NEXUS}. Downloading from upstream"
        curl -s -O ftp://ftp.gwdg.de/pub/misc/gcc/releases/gcc-${GCC_VERSION}/gcc-${GCC_VERSION}.tar.gz
        tar xzf gcc-${GCC_VERSION}.tar.gz
        (cd gcc-${GCC_VERSION} && ./contrib/download_prerequisites)
        tar czf gcc-${GCC_VERSION}-with-prerequisites.tar.gz gcc-${GCC_VERSION}
        curl -s -u "${USERNAME}:${PASSWORD}" --upload-file "gcc-${GCC_VERSION}-with-prerequisites.tar.gz" "${NEXUS}"
    fi

    log "Downloading gdb"
    if ! curl -s -O "${NEXUS}gdb-${GDB_VERSION}.tar.gz"; then
        log "File not available from ${NEXUS}. Downloading from upstream"
        curl -s -O ftp://sourceware.org/pub/gdb/releases/gdb-${GDB_VERSION}.tar.gz
        curl -s -u "${USERNAME}:${PASSWORD}" --upload-file "gdb-${GDB_VERSION}.tar.gz" "${NEXUS}"
    fi
}

function build-binutils() {
    log "Build binutils"
    cd ${BUILD_DIR}
    tar xzf binutils-${BINUTILS_VERSION}.tar.gz
    mkdir binutils-${BINUTILS_VERSION}-build
    cd binutils-${BINUTILS_VERSION}-build
    ../binutils-${BINUTILS_VERSION}/configure \
        --prefix=${PREFIX}
    make -j4
    make install
}

function build-gcc() {
    log "Build gcc"
    cd ${BUILD_DIR}
    tar xzf gcc-${GCC_VERSION}-with-prerequisites.tar.gz
    mkdir gcc-${GCC_VERSION}-build
    cd gcc-${GCC_VERSION}-build
    ../gcc-${GCC_VERSION}/configure \
        --prefix=${PREFIX} \
        --program-suffix=-${GCC_MAJOR} \
        --enable-linker-build-id \
        --disable-multilib \
        --enable-languages=c,c++
    make -j4
    make install
}

function build-gdb() {
    log "Build gdb"
    cd ${BUILD_DIR}
    tar xzf gdb-${GDB_VERSION}.tar.gz
    mkdir gdb-${GDB_VERSION}-build
    cd gdb-${GDB_VERSION}-build
    ../gdb-${GDB_VERSION}/configure \
        --prefix=${PREFIX} \
        CC=${PREFIX}/bin/gcc-${GCC_MAJOR} \
        CXX=${PREFIX}/bin/g++-${GCC_MAJOR} \
        $(python -V 2>&1 | grep -q 'Python 2\.4\.' && echo "--with-python=no")
    make -j4
    make install
}

function set-symlinks() {
    log "Set symlink"
    cd ${BUILD_DIR}
    ln -sf ${PREFIX}/bin/* /usr/bin
    ln -sf ${PREFIX}/bin/gcc-${GCC_MAJOR} /usr/bin/gcc
    ln -sf ${PREFIX}/bin/g++-${GCC_MAJOR} /usr/bin/g++
    rm -rf ${BUILD_DIR}
}

function build-all() {
    log "Build all"
    mkdir -p ${BUILD_DIR}
    cd ${BUILD_DIR}
    download-sources
    build-binutils
    build-gcc
    build-gdb
    set-symlinks
}

while getopts ":hdbucgsr:" opt; do
    case ${opt} in
    h)
        echo "Usage: cmd [-d] [-b] [-h]"
        echo "\t-d\tdownload sources"
        echo "\t-b\tbuild toolchain"
        ;;
    d)
        download-sources
        ;;
    b)
        build-all
        ;;
    u)
        build-binutils
        ;;
    c)
        build-gcc
        ;;
    g)
        build-gdb
        ;;
    s)
        set-symlinks
        ;;
    r)
        # Set URL to the repository where the binaries are stored
        NEXUS=${OPTARG}repository/archives/
        ;;
    \?)
        echo "Usage: cmd [-d] [-b] [-h]"
        ;;
    esac
done
