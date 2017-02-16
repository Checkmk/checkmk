#!/usr/bin/env python

import sys
import os
import cmk.werks


def create_changelog(dest_file, precompiled_werk_files):
    werks = load_werks(precompiled_werk_files)

    with open(dest_file, "w") as f:
        cmk.werks.write_as_text(werks, f)

        # Append previous werk changes
        if os.path.exists(dest_file + ".in"):
            f.write("\n\n")
            f.write(file(dest_file + ".in").read())


def load_werks(precompiled_werk_files):
    werks = {}
    for path in precompiled_werk_files:
        werks.update(cmk.werks.load_precompiled_werks_file(path))
    return werks


#
# MAIN
#

if len(sys.argv) < 3:
    sys.stderr.write("ERROR: Call like this: create-changelog CHANGELOG WERK_DIR...\n")
    sys.exit(1)

dest_file, precompiled_werk_files = sys.argv[1], sys.argv[2:]
create_changelog(dest_file, precompiled_werk_files)
