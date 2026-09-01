#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Runs inside a plain ubuntu:24.04 container (see test.sh). Expects TARGET
# and TARBALL_NAME in the environment, the tarball's directory bind-mounted
# read-only at /input, and an output directory bind-mounted at /output.
# GDB_TARBALL_NAME is also expected; its tarball is only staged if present
# at /input/${GDB_TARBALL_NAME}.
set -e -o pipefail

apt-get update -qq
apt-get install -y -qq --no-install-recommends xz-utils >/dev/null

cd /tmp
tar xf "/input/${TARBALL_NAME}"
toolchain_dir="/tmp/${TARGET}"
sysroot="${toolchain_dir}/${TARGET}/sysroot"

cat >hello.c <<'EOF'
int main(void) { return 0; }
EOF
cat >hello.cpp <<'EOF'
#include <iostream>
int main() { std::cout << "hello" << std::endl; return 0; }
EOF

"${toolchain_dir}/bin/${TARGET}-gcc" --sysroot="${sysroot}" -o /output/hello_c hello.c
# Static: the floor distro's own (older) libstdc++ can't satisfy this toolchain's dynamic one.
"${toolchain_dir}/bin/${TARGET}-g++" --sysroot="${sysroot}" \
    -static-libstdc++ -static-libgcc \
    -o /output/hello_cpp hello.cpp

if [ -f "/input/${GDB_TARBALL_NAME}" ]; then
    tar xf "/input/${GDB_TARBALL_NAME}" -C /output
fi
