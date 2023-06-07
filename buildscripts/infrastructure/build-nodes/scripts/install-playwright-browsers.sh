#!/bin/bash
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

# Previously we installed playwright via our .venv, but this is not yet available during building the
# docker images.
pip3 install playwright

# Invoking as a module is basically the same as using the full path:
# /opt/Python-${PYTHON_VERSION}/bin/playwright
python3 -m playwright install --with-deps chromium

# Clean up in order to remove unneeded stuff (playwright will be used anyway from the .venv later)
pip3 uninstall -y playwright
