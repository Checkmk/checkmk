#!/bin/bash
set -x -e

GCC_MAJOR="8"
GCC_MINOR="2"
GCC_PATCHLEVEL="0"
BINUTILS_VERSION="2.32"
GDB_VERSION="8.2.1"

GCC_VERSION="${GCC_MAJOR}.${GCC_MINOR}.${GCC_PATCHLEVEL}"
PREFIX="/opt/gcc-${GCC_VERSION}"

BUILD_DIR=/tmp/build-gcc-toolchain

#NEXUS="http://nexus.lan.tribe29.com/repository/archives/"
NEXUS="http://devrechner.lan.mathias-kettner.de:8081/repository/archives/"
#NEXUS="http://10.9.1.101:8081/repository/archives/"

function download-sources {
    # To avoid repeated downloads of the sources + the prerequisites, we
    # pre-package things together:
    # wget https://ftp.gnu.org/gnu/binutils/binutils-${BINUTILS_VERSION}.tar.gz

    if ! wget ${NEXUS}/binutils-${BINUTILS_VERSION}.tar.gz; then
        wget https://sourceware.org/pub/binutils/releases/binutils-${BINUTILS_VERSION}.tar.gz
        curl -v -u ${USERNAME}:${PASSWORD} --upload-file binutils-${BINUTILS_VERSION}.tar.gz ${NEXUS}
    fi
    if ! wget ${NEXUS}/gcc-${GCC_VERSION}-with-prerequisites.tar.gz; then
        wget ftp://ftp.gwdg.de/pub/misc/gcc/releases/gcc-${GCC_VERSION}/gcc-${GCC_VERSION}.tar.gz
        tar xzf gcc-${GCC_VERSION}.tar.gz
       ( cd gcc-${GCC_VERSION} && ./contrib/download_prerequisites )
        tar czf gcc-${GCC_VERSION}-with-prerequisites.tar.gz gcc-${GCC_VERSION}
        curl -v -u ${USERNAME}:${PASSWORD} --upload-file gcc-${GCC_VERSION}-with-prerequisites.tar.gz ${NEXUS}
    fi
    if ! wget ${NEXUS}/gdb-${GDB_VERSION}.tar.gz; then
        wget ftp://sourceware.org/pub/gdb/releases/gdb-${GDB_VERSION}.tar.gz
        curl -v -u ${USERNAME}:${PASSWORD} --upload-file gdb-${GDB_VERSION}.tar.gz ${NEXUS}
    fi
}

function build-binutils {
    cd ${BUILD_DIR}
    tar xzf binutils-${BINUTILS_VERSION}.tar.gz
    mkdir binutils-${BINUTILS_VERSION}-build
    cd binutils-${BINUTILS_VERSION}-build
    ../binutils-${BINUTILS_VERSION}/configure \
        --prefix=${PREFIX}
    make -j8
    make install
}

function build-gcc {
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
    make -j8
    make install
}
    
function build-gdb {
    cd ${BUILD_DIR}
    tar xzf gdb-${GDB_VERSION}.tar.gz
    mkdir gdb-${GDB_VERSION}-build
    cd gdb-${GDB_VERSION}-build
    ../gdb-${GDB_VERSION}/configure \
        --prefix=${PREFIX} \
        CC=${PREFIX}/bin/gcc-${GCC_MAJOR} \
        CXX=${PREFIX}/bin/g++-${GCC_MAJOR} \
        $(python -V 2>&1 | grep -q 'Python 2\.4\.' && echo "--with-python=no")
    make -j8
    make install
}

function set-symlinks {
    cd ${BUILD_DIR}
    ln -sf ${PREFIX}/bin/* /usr/bin
    ln -sf ${PREFIX}/bin/gcc-${GCC_MAJOR} /usr/bin/gcc
    ln -sf ${PREFIX}/bin/g++-${GCC_MAJOR} /usr/bin/g++
    rm -rf ${BUILD_DIR}
}

function build-all {
    mkdir -p ${BUILD_DIR}
    cd ${BUILD_DIR}
    download-sources
    build-binutils
    build-gcc
    build-gdb
    set-symlinks
}

while getopts ":hdbucgs" opt; do
  case ${opt} in
    h ) echo "Usage: cmd [-d] [-b] [-h]"
        echo "\t-d\tdownload sources"
        echo "\t-b\tbuild toolchain"
      ;;
    d ) download-sources
      ;;
    b ) build-all
      ;;
    u ) build-binutils
      ;;
    c ) build-gcc
      ;;
    g ) build-gdb
      ;;
    s ) set-symlinks
      ;;
    \? ) echo "Usage: cmd [-d] [-b] [-h]"
      ;;
  esac
done
