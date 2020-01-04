#!/bin/bash

set -e -o pipefail

GCC_MAJOR="8"
GCC_MINOR="2"
GCC_PATCHLEVEL="0"
BINUTILS_VERSION="2.33.1"
GDB_VERSION="8.3.1"

MIRROR_URL="https://sourceware.org/pub/"

GCC_VERSION="${GCC_MAJOR}.${GCC_MINOR}.${GCC_PATCHLEVEL}"
PREFIX="/opt/gcc-${GCC_VERSION}"

BUILD_DIR=/tmp/build-gcc-toolchain


function log() {
    echo "+++ $1"
}

function download-sources() {
    log "Dowload parameters: NEXUS=[${NEXUS_ARCHIVES_URL}], USERNAME=[${USERNAME//?/X}], PASSWORD=[${PASSWORD//?/X}]"

    log "Downloading binutils-${BINUTILS_VERSION}"
    if curl -s -O "${NEXUS_ARCHIVES_URL}binutils-${BINUTILS_VERSION}.tar.gz"; then
        log "Using ${NEXUS_ARCHIVES_URL}binutils-${BINUTILS_VERSION}.tar.gz"
    else
        log "File not available from ${NEXUS_ARCHIVES_URL}binutils-${BINUTILS_VERSION}.tar.gz, downloading from ${MIRROR_URL}binutils/releases/binutils-${BINUTILS_VERSION}.tar.gz"
        curl -s -O ${MIRROR_URL}binutils/releases/binutils-${BINUTILS_VERSION}.tar.gz
        log "Uploading binutils-${BINUTILS_VERSION}.tar.gz to ${NEXUS_ARCHIVES_URL}"
        curl -s -u "${USERNAME}:${PASSWORD}" --upload-file "binutils-${BINUTILS_VERSION}.tar.gz" "${NEXUS_ARCHIVES_URL}"
        log "Upload of binutils done"
    fi

    log "Downloading gcc-${GCC_VERSION}"
    if curl -s -O "${NEXUS_ARCHIVES_URL}gcc-${GCC_VERSION}-with-prerequisites.tar.gz"; then
        log "Using ${NEXUS_ARCHIVES_URL}gcc-${GCC_VERSION}-with-prerequisites.tar.gz"
    else
        log "File not available from ${NEXUS_ARCHIVES_URL}gcc-${GCC_VERSION}-with-prerequisites.tar.gz, downloading from ${MIRROR_URL}gcc/releases/gcc-${GCC_VERSION}/gcc-${GCC_VERSION}.tar.gz"
        curl -s -O ${MIRROR_URL}gcc/releases/gcc-${GCC_VERSION}/gcc-${GCC_VERSION}.tar.gz
        # To avoid repeated downloads of the sources + the prerequisites, we pre-package things together.
        log "Downloading and merging prerequisites"
        tar xzf gcc-${GCC_VERSION}.tar.gz
        (cd gcc-${GCC_VERSION} && ./contrib/download_prerequisites)
        tar czf gcc-${GCC_VERSION}-with-prerequisites.tar.gz gcc-${GCC_VERSION}
        log "Uploading gcc-${GCC_VERSION}-with-prerequisites.tar.gz to ${NEXUS_ARCHIVES_URL}"
        curl -s -u "${USERNAME}:${PASSWORD}" --upload-file "gcc-${GCC_VERSION}-with-prerequisites.tar.gz" "${NEXUS_ARCHIVES_URL}"
        log "Upload of gcc done"
    fi

    log "Downloading gdb-${GDB_VERSION}"
    if curl -s -O "${NEXUS_ARCHIVES_URL}gdb-${GDB_VERSION}.tar.gz"; then
        log "Using ${NEXUS_ARCHIVES_URL}gdb-${GDB_VERSION}.tar.gz"
    else
        log "File not available from ${NEXUS_ARCHIVES_URL}gdb-${GDB_VERSION}.tar.gz, downloading from ${MIRROR_URL}gdb/releases/gdb-${GDB_VERSION}.tar.gz"
        curl -s -O ${MIRROR_URL}gdb/releases/gdb-${GDB_VERSION}.tar.gz
        log "Uploading gdb-${GDB_VERSION}.tar.gz ${NEXUS_ARCHIVES_URL}"
        curl -s -u "${USERNAME}:${PASSWORD}" --upload-file "gdb-${GDB_VERSION}.tar.gz" "${NEXUS_ARCHIVES_URL}"
        log "Upload of gdb done"
    fi
}

function build-binutils() {
    log "Build binutils-${BINUTILS_VERSION}"
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
    log "Build gcc-${GCC_VERSION}"
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
    log "Build gdb-${GDB_VERSION}"
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
        NEXUS_ARCHIVES_URL="${OPTARG}repository/archives/"
        ;;
    \?)
        echo "Usage: cmd [-d] [-b] [-h]"
        ;;
    esac
done
