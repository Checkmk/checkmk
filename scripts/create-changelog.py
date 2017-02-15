#!/usr/bin/env python

import sys
import os
import cmk.werks


def create_changelog(dest_file, precompiled_werk_files):
    werks = load_werks(precompiled_werk_files)

    with open(dest_file, "w") as f:
        write_changelog(werks, f)

        # Append previous werk changes
        if os.path.exists(dest_file + ".in"):
            f.write("\n\n")
            f.write(file(dest_file + ".in").read())


def load_werks(precompiled_werk_files):
    werks = {}
    for path in precompiled_werk_files:
        werks.update(cmk.werks.load_precompiled_werks_file(path))
    return werks


def write_changelog(werks, f):
    version, component = None, None
    for werk in cmk.werks.sort_by_version_and_component(werks.values()):
        if version != werk["version"]:
            if version is not None:
                f.write("\n\n")

            version, component = werk["version"], None

            f.write("%s:\n" % werk["version"])

        if component != werk["component"]:
            if component is not None:
                f.write("\n")

            component = werk["component"]

            f.write("    %s:\n" % \
                cmk.werks.werk_components().get(component, component))

        write_changelog_line(f, werk)


def write_changelog_line(f, werk):
    prefix = ""
    if werk["class"] == "fix":
        prefix = " FIX:"
    elif werk["class"] == "security":
        prefix = " SEC:"

    if werk.get("description") and len(werk["description"]) > 3:
        omit = "..."
    else:
        omit = ""

    f.write("    * %04d%s %s%s\n" %
        (werk["id"], prefix, werk["title"].encode("utf-8"), omit))

    if werk["compatible"] == "incomp":
        f.write("            NOTE: Please refer to the migration notes!\n")


#
# MAIN
#

if len(sys.argv) < 3:
    sys.stderr.write("ERROR: Call like this: create-changelog CHANGELOG WERK_DIR...\n")
    sys.exit(1)

dest_file, precompiled_werk_files = sys.argv[1], sys.argv[2:]
create_changelog(dest_file, precompiled_werk_files)
