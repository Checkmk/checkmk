#!/bin/sh
set -x

echo ${PWD}
INTERPRETER="$(realpath $(find -name python3 | grep -v copy | grep -v omd_packages))"
PY_LIB_DIR="$(realpath $(dirname ${INTERPRETER}))/../lib"
PY_INCLUDE_DIR="$(realpath $(find -name Python.h | grep -v copy | grep -v omd_packages))"

export OPENSSL_LIB_DIR="$(realpath $(dirname $(find -name libssl.so | grep -v copy | grep -v omd_packages)))"
export OPENSSL_INCLUDE_DIR="$OPENSSL_LIB_DIR/../include/openssl"

FREETDS_LIB_DIR="$(realpath $(dirname $(find -name libct.so | grep -v copy | grep -v omd_packages)))"
FREETDS_INCLUDE_DIR="$FREETDS_LIB_DIR/../include"

export LD_LIBRARY_PATH="${PY_LIB_DIR}:${OPENSSL_LIB_DIR}:$LD_LIBRARY_PATH"

export CPATH="$PY_INCLUDE_DIR:$OPENSSL_INCLUDE_DIR"

export CFLAGS="-I${OPENSSL_INCLUDE_DIR} -I${PY_INCLUDE_DIR} -I${FREETDS_INCLUDE_DIR}"
export LDFLAGS="-L${OPENSSL_LIB_DIR} -L${PY_LIB_DIR} -L${FREETDS_LIB_DIR}"

${INTERPRETER} "$@"

