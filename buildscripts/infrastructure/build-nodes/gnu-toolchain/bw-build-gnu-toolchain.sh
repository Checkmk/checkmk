#!/bin/bash

set -e -o pipefail

GCC_MAJOR="8"
GCC_MINOR="3"
GCC_PATCHLEVEL="0"
BINUTILS_VERSION="2.33.1"
GDB_VERSION="8.3.1"

MIRROR_URL="https://sourceware.org/pub/"

GCC_VERSION="${GCC_MAJOR}.${GCC_MINOR}.${GCC_PATCHLEVEL}"
PREFIX="/opt/gcc-${GCC_VERSION}"

BUILD_DIR=/tmp/build-gcc-toolchain


log() {
    echo "+++ $1"
}

download-from-nexus() {
    DOWNLOAD_URL="${NEXUS_ARCHIVES_URL}$1"
    log "Downloading ${DOWNLOAD_URL}"
    curl --silent --fail --remote-name "${DOWNLOAD_URL}" || return
    log "Using ${DOWNLOAD_URL}"
}

download-from-mirror() {
    FILE=$1
    DOWNLOAD_URL=$2
    log "File not available from ${NEXUS_ARCHIVES_URL}${FILE}, downloading from ${DOWNLOAD_URL}"
    curl --silent --fail --remote-name "${DOWNLOAD_URL}"
}

upload-to-nexus() {
    FILE=$1
    log "Uploading ${FILE} to ${NEXUS_ARCHIVES_URL}"
    curl --silent --user "${USERNAME}:${PASSWORD}" --upload-file "${FILE}" "${NEXUS_ARCHIVES_URL}"
    log "Upload of ${FILE} done"
}

download-sources() {
    log "Dowload parameters: NEXUS_ARCHIVES_URL=[${NEXUS_ARCHIVES_URL}], USERNAME=[${USERNAME//?/X}], PASSWORD=[${PASSWORD//?/X}]"

    FILE="binutils-${BINUTILS_VERSION}.tar.gz"
    if ! download-from-nexus "${FILE}"; then
        download-from-mirror "${FILE}" "${MIRROR_URL}binutils/releases/${FILE}"
        upload-to-nexus "${FILE}"
    fi

    FILE="gcc-${GCC_VERSION}-with-prerequisites.tar.gz"
    if ! download-from-nexus "${FILE}"; then
        download-from-mirror "${FILE}" "${MIRROR_URL}gcc/releases/gcc-${GCC_VERSION}/gcc-${GCC_VERSION}.tar.gz"
        # To avoid repeated downloads of the sources + the prerequisites, we pre-package things together.
        log "Downloading and merging prerequisites"
        tar xzf gcc-${GCC_VERSION}.tar.gz
        (cd gcc-${GCC_VERSION} && ./contrib/download_prerequisites)
        tar czf ${FILE} gcc-${GCC_VERSION}
        upload-to-nexus "${FILE}"
    fi

    FILE="gdb-${GDB_VERSION}.tar.gz"
    if ! download-from-nexus "${FILE}"; then
        download-from-mirror "${FILE}" "${MIRROR_URL}gdb/releases/${FILE}"
        upload-to-nexus "${FILE}"
    fi
}

build-binutils() {
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

build-gcc() {
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

build-gdb() {
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

set-symlinks() {
    log "Set symlink"
    cd ${BUILD_DIR}
    ln -sf ${PREFIX}/bin/* /usr/bin
    ln -sf ${PREFIX}/bin/gcc-${GCC_MAJOR} /usr/bin/gcc
    ln -sf ${PREFIX}/bin/g++-${GCC_MAJOR} /usr/bin/g++
    rm -rf ${BUILD_DIR}
}

build-all() {
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
