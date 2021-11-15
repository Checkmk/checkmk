#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from pathlib import Path

import cmk.utils.werks

werk_dir = Path(sys.argv[1])
dest_file = Path(sys.argv[2])
edition_short = sys.argv[3] if len(sys.argv) > 3 else None

if not werk_dir.exists():
    raise Exception("Requested werk directory does not exist: %s" % werk_dir)

werks = cmk.utils.werks.load_raw_files(werk_dir)

if edition_short:
    werks = {werk["id"]: werk for werk in werks.values() if werk["edition"] == edition_short}

cmk.utils.werks.write_precompiled_werks(dest_file, werks)
