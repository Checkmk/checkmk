#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys
from pathlib import Path

import cmk.utils.werks


def create_changelog(dest_file_path, precompiled_werk_files):
    werks = load_werks(precompiled_werk_files)

    with open(dest_file_path, "w", encoding="utf-8") as f:
        cmk.utils.werks.write_as_text(werks, f)

        # Append previous werk changes
        if os.path.exists(dest_file_path + ".in"):
            f.write("\n\n")
            f.write(open(dest_file_path + ".in").read())


def load_werks(precompiled_werk_files):
    werks = {}
    for path in precompiled_werk_files:
        werks.update(cmk.utils.werks.load_precompiled_werks_file(path))
    return werks


#
# MAIN
#

if len(sys.argv) < 3:
    sys.stderr.write("ERROR: Call like this: create-changelog CHANGELOG WERK_DIR...\n")
    sys.exit(1)

dest_file, arg_precompiled_werk_files = sys.argv[1], sys.argv[2:]
create_changelog(dest_file, [Path(p) for p in arg_precompiled_werk_files])
