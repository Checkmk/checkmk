#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Builds .venv in /git and stages it for the system test image, as it is laid out in
# the image:
#   <stage dir>/git/.venv          the venv
#   <stage dir>/opt/venv-python    the Python interpreter it runs on
#
# Run it in /git, in a container of the distro the image is for: the console
# scripts' shebangs point to /git/.venv, so the venv has to be built where it
# is used. Its interpreter is the hermetic Python Bazel fetched, wherever the
# rc files put that (output base, or the repo contents cache that
# /etc/ci.bazelrc moves onto the node's shared mount). It is moved to
# /opt/venv-python, and the venv's two absolute references to it, the
# bin/python symlink and the home line of pyvenv.cfg, follow.
#
# Used by the venv stage of Dockerfile.

set -euo pipefail

stage="${1:?usage: $0 <stage dir>}"

if [ "$(pwd -P)" != /git ]; then
    echo "$0: run this in /git, not in $(pwd -P)" >&2
    exit 1
fi

make .venv

python="$(readlink .venv/bin/python)"
python_home="$(dirname "$(dirname "${python}")")"
if ! grep -qx "home = ${python_home}/bin" .venv/pyvenv.cfg; then
    echo "$0: .venv/pyvenv.cfg does not point to ${python_home}/bin" >&2
    exit 1
fi

rm -rf "${stage}"
mkdir -p "${stage}/git" "${stage}/opt/venv-python"
cp -a "${python_home}/." "${stage}/opt/venv-python/"
cp -a .venv "${stage}/git/"
ln -sfn "/opt/venv-python/bin/$(basename "${python}")" "${stage}/git/.venv/bin/python"
sed -i "s|^home = .*|home = /opt/venv-python/bin|" "${stage}/git/.venv/pyvenv.cfg"
chmod -R a+rX "${stage}"
