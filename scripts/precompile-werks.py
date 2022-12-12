#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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

werks_list = cmk.utils.werks.load_raw_files(werk_dir)

werks = {
    werk.id: werk
    for werk in werks_list
    if edition_short is None
    # we don't know if we have a WerkV1 or WerkV2, so we test for both:
    or werk.edition == edition_short or werk.edition == cmk.utils.werks.werk.Edition(edition_short)
}

cmk.utils.werks.write_precompiled_werks(dest_file, werks)
