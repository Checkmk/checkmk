#!/usr/bin/env python

import sys
from pathlib2 import Path
import cmk.werks

werk_dir = Path(sys.argv[1])
dest_file = Path(sys.argv[2])
edition_short = sys.argv[3] if len(sys.argv) > 3 else None

if not werk_dir.exists():
    raise Exception("Requested werk directory does not exist: %s" % werk_dir)

werks = cmk.werks.load_raw_files(werk_dir)

if edition_short:
    werks = {
        werk["id"]: werk  #
        for werk in werks.itervalues()
        if werk["edition"] == edition_short
    }

cmk.werks.write_precompiled_werks(dest_file, werks)
