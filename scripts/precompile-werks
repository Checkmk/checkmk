#!/usr/bin/env python

import os
import sys
import cmk.werks

werk_dir, dest_file = sys.argv[1:]

werks = cmk.werks.load_raw_files(werk_dir)
cmk.werks.write_precompiled_werks(dest_file, werks)
