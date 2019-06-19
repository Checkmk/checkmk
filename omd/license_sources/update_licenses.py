#!/usr/bin/env python
"""
usage: ./update_licenses [-h] [-v] cmk_path

Script for helping you update the list of licenses for any given CheckMK
source repository

positional arguments:
  cmk_path       path to a CheckMK source repository

optional arguments:
  -h, --help     show this help message and exit
  -v, --verbose  display found package paths that could not be matched

The update_licenses script is used to simplify updating the list of licenses
found under omd/Licenses.ods within the checkmk-Git.
It basically takes all the listed packages from that list's underlying csv file
and checks whether a given CheckMK repository holds the listed package paths. It
then returns the list's entries for which the exact package path could not be
found. Also, it finds similar package paths, e.g. holding the package name but a
different version number, and outputs them among the respectively detected
license and version as follows:

package_name
Listed path:    path/as/listed
Found path:     path/as/found -- license -- version

Finally, the script tells you how many package paths that were found in the
CheckMK repository could not be matched and thus are not yet listed in the csv
file. By calling the script with the --verbose [-v] option it outputs all these
unmatched files.
Based on the script output the Licenses.ods file can be updated from hand and
then saved to the Licenses.csv file.
For any output of the kind "[License|Version] UNKN" one has to dig into the
respective package oneself to find the wanted information.
"""

import sys
import os
import traceback
import re
import argparse
import fnmatch
from pathlib2 import Path

ZIP_ENDINGS = [".tar.gz", ".zip", ".tar.bz2", ".tar.xz"]


def find(pattern, path):
    '''Simple function for finding all files under path that include
    pattern within their file name (similar to grep -r)'''
    result = []
    path = "%s/" % path
    for root, dirs, files in os.walk(path):
        for name in files:
            if isinstance(pattern, list):
                for patt in pattern:
                    if fnmatch.fnmatch(name, patt):
                        result.append(os.path.join(root, name).replace(path, ""))
            else:
                if fnmatch.fnmatch(name, pattern):
                    result.append(os.path.join(root, name).replace(path, ""))
    return result


def print_separator():
    print "---------------------------------------------------"


def dir_from_zipped(file_string):
    for ending in ZIP_ENDINGS:
        if ending in file_string:
            return file_string.rstrip(ending) + "/"
    return file_string


def available_files(pkg_dir, needles):
    found_files = []
    for needle in needles:
        #TODO: Handle this loop using pathlib2
        for d in os.listdir(pkg_dir):
            if needle.lower() in d.lower():
                found_files.append(d)
    return found_files


def detect_license(pkg_dir):
    '''Return the license for a given package directory pkg_dir if it can be
    obtained from available license files'''
    license_needles = ["LICENSE", "COPYING", "PKG-INFO", "README"]
    license_files = available_files(pkg_dir, license_needles)
    for lf in license_files:
        if os.path.isdir(pkg_dir + lf):
            return detect_license(pkg_dir + lf + "/")
        with open(pkg_dir + lf, "r") as lfile:
            # lower case string for comparisons
            ltxt = lfile.read().lower()
            # MPL
            if "mozilla public license" in ltxt:
                if "version 2.0" in ltxt:
                    return "MPL-2.0"
                elif "version 1.1" in ltxt:
                    return "MPL-1.1"
            # GPL
            elif "gnu general public license" in ltxt:
                if "version 3" in ltxt:
                    return "GPL-3.0"
                elif "version 2" in ltxt:
                    return "GPL-2.0"
                elif "version 1" in ltxt:
                    return "GPL-1.0"
                return "GPL-UNKN"
            # Apache
            elif "apache license" in ltxt:
                if "version 2.0" in ltxt:
                    return "Apache-2.0"
                return "Apache-UNKN"
            # BSD
            elif "redistribution and use in source and binary forms" in ltxt:
                if "redistributions of source code must" in ltxt and \
                        "redistributions in binary form must" in ltxt:
                    if "all advertising materials mentioning features" in ltxt:
                        if "neither the name of the copyright" in ltxt:
                            return "BSD-4-Clause"
                        return "BSD-3-Clause"
                    return "BSD-2-Clause"
                return "BSD-UNKN"
            # BSL
            elif "boost software license" in ltxt:
                if "version 1.0" in ltxt:
                    return "BSL-1.0"
                return "BSL-UNKN"
            # MIT - CMU style
            elif "permission to use, copy, modify and distribute this" in ltxt:
                return "MIT - CMU style"
            # MIT
            elif "permission is hereby granted, free of charge, to" in ltxt:
                return "MIT"
            # Artistic
            elif "artistic" in ltxt:
                if "license 1.0" in ltxt or \
                   "\"package\" refers to the collection of files" in ltxt:
                    return "Artistic-1.0"
                elif "license 2.0" in ltxt or \
                     "everyone is permitted to copy and distribute" in ltxt:
                    return "Artistic-2.0"
                return "Artistic-UNKN"
            # CC0 1.0
            elif "cc0 1.0" in ltxt:
                return "CC0 1.0"
            # CDDL 1.0
            elif "cddl" in ltxt or "common development and distribution license" in ltxt:
                if "version 1.0" in ltxt:
                    return "CDDL-1.0"
                return "CDDL-UNKN"
            # ISC
            elif "isc license" in ltxt:
                return "ISC"
            # LGPL
            elif "gnu lesser general public license" in ltxt:
                if "version 3" in ltxt:
                    return "LGPL-3.0"
                elif "version 2.1" in ltxt:
                    return "LGPL-2.1"
                elif "version 2" in ltxt:
                    return "LGPL-2.0"
                return "LGPL-UNKN"
            # OML
            elif "open market permits you to use, copy" in ltxt:
                return "OML"
            # PIL
            elif "python imaging library" in ltxt:
                return "PIL"
            # Python
            elif "python software foundation" in ltxt:
                if "version 2" in ltxt:
                    return "Python-2.0"
                return "Python-UNKN"
            # X11
            elif "x11 license" in ltxt:
                return "X11"
    return "License UNKN"


def detect_version(pkg_dir, name=""):
    '''Return the version for a given package directory pkg_dir and package
    name name if it can be obtained from available files'''
    version_needles = ["PKG-INFO", "VERSION", "FAQ", "README"]
    version_files = available_files(pkg_dir, version_needles)
    for vf in version_files:
        if os.path.isdir(pkg_dir + vf):
            return detect_version(pkg_dir + vf + "/")
        with open(pkg_dir + vf, "r") as vfile:
            # lower case string for comparisons
            #vtxt = vfile.read().lower()
            lines = vfile.readlines()
            for line in lines:
                if re.match("version: ", line.lower()):
                    return re.sub(r"^[^:]*:\ ", "", line).rstrip("\n")
            for line in lines:
                if "version: " in line.lower():
                    return re.sub(r"^[^:]*:\ ", "", line).rstrip("\n")

    version = ""
    if name:
        needle = name.replace("Perl module: ", "").replace("Python module: ", "").replace(" ", "")
        if needle in pkg_dir:
            version = pkg_dir.lstrip(needle).lstrip("-").rstrip("/")
        elif needle.lower() in pkg_dir:
            version = pkg_dir.lstrip(needle.lower()).lstrip("-").rstrip("/")

    if version:
        return version + " (from path)"
    else:
        return "Version UNKN"


def parse_arguments():
    '''Argument parser for update licenses script handling the following arguments:
    cmk_path        path to a CheckMK source repository
    -v --verbose    display found package paths that could not be matched'''
    parser = argparse.ArgumentParser(
        description="Script for helping you update the list of licenses for any " +\
            "given CheckMK source repository",
        usage="./update_licenses [-h] [-v] cmk_path")
    parser.add_argument("cmk_path", help="path to a CheckMK source repository")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="display found package paths that could not be matched")
    return parser.parse_args()


def main(args):
    try:
        path_omd = Path("%s/git/check_mk/omd/" % Path.home())
        path_cmk_dir = Path(args.cmk_path + ("/" if args.cmk_path[-1] != "/" else ""))
        fn_csv = str(path_omd / "Licenses.csv")
    except:
        raise OSError

    print "Inspecting CheckMK repository \"%s\"" % path_cmk_dir

    # Find all package paths within the given CheckMK sources repository
    found_paths = find(["*" + ze for ze in ZIP_ENDINGS], path_cmk_dir)
    if not found_paths:
        print "\nFor the given CheckMK repository \"%s\" no package paths were found." \
            % path_cmk_dir
        sys.exit()
    n_found = str(len(found_paths))

    # Exceptional package paths that cannot be matched via package name
    # TODO: Keep these up to date
    exceptions = {
        "GNU patch": "omd/packages/patch/patch-2.7.6.tar.gz",
        "Heirloom Packaging Tools": "omd/packages/heirloom-pkgtools/heirloom-pkgtools-070227.tar.bz2",
        "Monitoring Plugins": "omd/packages/monitoring-plugins/monitoring-plugins-2.2.tar.gz",
        "Perl module: DateTime::TimeZone": "omd/packages/perl-modules/src/DateTime-TimeZone-1.88.tar.gz",
        "Perl module: ExtUtils-Cbuilder": "omd/packages/perl-modules/src/ExtUtils-CBuilder-0.280220.tar.gz",
        "Perl module: Iperl module: O": "omd/packages/perl-modules/src/IO-1.25.tar.gz",
        "Perl module: libnetPerl module:": "omd/packages/perl-modules/src/libnet-3.05.tar.gz",
        "Perl module: Spreadsheet::WriteExcel": "omd/packages/perl-modules/src/Spreadsheet-WriteExcel-2.40.tar.gz"
    }

    no_path_match = []
    with open(fn_csv, "r") as csv:
        # Drop first line of headers (name, version, ...)
        csv.readline()

        # Go through all packages already listed and try to match them with
        # the found package paths
        for line in csv:
            # End of packages
            if line == ",,,,,,,,\n":
                break

            [name, _, _, _, path] = line.split(",")[:5]
            [name, path] = [i.strip() for i in [name, path]]
            # Needle to look for within the haystack of package paths
            needle = name.replace("Perl module: ", "").replace("Python module: ", "").replace(
                " ", "")

            # Match the exceptional package paths first
            if name in exceptions and exceptions[name] in found_paths:
                found_paths.remove(exceptions[name])
                continue

            matches = []  # Name matches when there's no exact path match
            path_match = False
            for fpath in found_paths:
                if needle in fpath:
                    if path == fpath:
                        found_paths.remove(fpath)
                        path_match = True
                        break
                    else:
                        matches.append(fpath)
                elif needle.lower() in fpath:
                    if path == fpath:
                        found_paths.remove(fpath)
                        path_match = True
                        break
                    else:
                        matches.append(fpath)
            if not path_match:
                no_path_match.append((name, path, matches))

    # Remove all matches from no_path_match that were exactly matched to some
    # different package - thus are not in found_paths anymore
    no_path_match = [(n, p, set(m).intersection(set(found_paths))) for n, p, m in no_path_match]

    # Generate output
    # Packages from fn_csv that could not be matched
    if no_path_match:
        print "\n\nThe following entries in \"%s\" need to be\nlooked at and potentially updated as no matching package path was found under\n\"%s\":\n[Found path:\tpath/to/package -- license -- version]\n" % (
            fn_csv, path_cmk_dir)
        for (name, path, matches) in no_path_match:
            print_separator()
            print name
            print "Listed path:\t" + path
            if matches:
                output = []
                # Unpack each matching path and try to detect the respective license
                # and version
                for match in matches:
                    if "tar" in match:
                        os.system("tar xf %s/%s" % (path_cmk_dir, match))
                    elif "zip" in match:
                        os.system("unzip -oq %s/%s" % (path_cmk_dir, match))
                    else:
                        output.append(match)
                        continue
                    pkg_dir = dir_from_zipped(os.path.basename(match))
                    license = detect_license(pkg_dir)
                    version = detect_version(pkg_dir, name)
                    output.append(" -- ".join([match, license, version]))
                    os.system("rm -rf " + pkg_dir)
                print "Found path" + ("s" if len(matches) > 1 else "") + ":\t" +\
                    "\n\t\t".join(output)
            else:
                print "No matching path"
        print_separator()
    else:
        print "\n\nAll entries of \"" + fn_csv + "\" were successfully\n" +\
            "matched to package paths existing within \"%s\"" % path_cmk_dir

    # Remaining package paths found for path_cmk_dir
    n_remaining = str(len(found_paths))
    if not n_remaining == "0":
        print "\n\n" + ("The following " if args.verbose else "") + n_remaining +\
            " out of " + n_found + " found paths could not be matched to any " +\
            "of the packages\nlisted in \"" + fn_csv + "\""
        if args.verbose:
            print "[path/to/package -- license -- version]"
            output = []
            for path in found_paths:
                if "tar" in path:
                    os.system("tar xf %s/%s" % (path_cmk_dir, path))
                elif "zip" in path:
                    os.system("unzip -oq %s/%s" % (path_cmk_dir, path))
                else:
                    output.append(path)
                    continue
                pkg_dir = dir_from_zipped(os.path.basename(path))
                license = detect_license(pkg_dir)
                version = detect_version(pkg_dir)
                output.append(" -- ".join([path, license, version]))
                os.system("rm -rf " + pkg_dir)
            print "\n" + "\n".join(output)
    else:
        print "\n\nAll " + n_found + " found paths were successfully matched to " +\
            "the respective package\nlisted in \"" + fn_csv + "\""


if __name__ == "__main__":
    try:
        args = parse_arguments()
        main(args)
        sys.exit(0)
    except Exception:
        sys.stderr.write(traceback.format_exc())
        sys.exit(1)
