#!/usr/bin/env python

import os
import sys
import cmk.werks

werk_dir, dest_file = sys.argv[1:3]

if len(sys.argv) > 3:
    edition_short = sys.argv[3]
else:
    edition_short = None

if not os.path.exists(werk_dir):
    raise Exception("Requested werk directory does not exist: %s" % werk_dir)

werks = cmk.werks.load_raw_files(werk_dir)

if edition_short:
    edition_werks = {}
    for werk in werks.values():
        if werk["edition"] == edition_short:
            edition_werks[werk["id"]] = werk

    werks = edition_werks

cmk.werks.write_precompiled_werks(dest_file, werks)
