#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
usage: ./update_licenses [-h] [-v] [--path] [--version]

Script for updating the list of licenses omd/Licenses.csv in the current Git
repository for a specific Checkmk version

optional arguments:
  -h, --help        Show this help message and exit
  -v, --verbose     Write updated and missing package information to the terminal
      --path        Provide a path to a local CheckMK source repository (instead of downloading)
      --version     Set the Checkmk version for which licenses shall be updated


The update_licenses script is used to update the list of licenses found under
omd/Licenses.csv within the Checkmk-Git. Based on the required argument
"version" the source package for the respective Checkmk version is downloaded
from download.checkmk.com as user "d-intern" (see wiki page "How to download")
and extracted to a folder holding the sources. These are now searched for
extractable packages and all findings are written directly to Licenses.csv with
the detected name, version and license.
For any entries of the kind "[License|Version] UNKN" the respective information
could not be found and one has to dig into the package (see package path)
oneself to find it.
Also, the JS dependencies listed in Licenses.csv are updated using npx
license-checker.

The obtained data can then be copy-pasted from Licenses.csv to the matching
sections in Licenses.ods to have both package listing and detailed license
information in one document and to make things look better (colored headings).
"""

import argparse
import csv
import fnmatch
import json
import os
import re
import sys
import traceback
from datetime import date
from pathlib import Path
from shutil import rmtree
from typing import Dict, List, Optional

from pipfile import Pipfile

ZIP_ENDINGS = [".tar.gz", ".zip", ".tar.bz2", ".tar.xz", ".cab"]
license_links_file = "License_links.csv"


def find(pattern, path, find_dirs=False) -> List[str]:
    """Simple function for finding all files under path that include
    pattern within their file name (similar to shell command "find -name")"""
    result = []
    for root, dirs, files in os.walk(path):
        if find_dirs:
            files = dirs
        for name in files:
            full_path_str = "%s/%s" % (root, name)
            if isinstance(pattern, list):
                for patt in pattern:
                    if fnmatch.fnmatch(name, patt):
                        result.append(full_path_str.replace("%s/" % path, ""))
            else:
                if fnmatch.fnmatch(name, pattern):
                    result.append(full_path_str.replace("%s/" % path, ""))
    return result


def print_separator():
    print("\n---------------------------------------------------\n")


def path_from_zipped(file_string) -> Path:
    for ending in ZIP_ENDINGS:
        if file_string.endswith(ending):
            return file_string[: -len(ending)] + "/"
    return Path(file_string)


def available_files(pkg_dir: Path, needles) -> List[Path]:
    found_files = []
    for needle in needles:
        for f in pkg_dir.iterdir():
            if needle.lower() in str(f).lower():
                found_files.append(f)
    return found_files


def detect_license(pkg_dir: Path) -> str:
    """Return the license for a given package directory pkg_dir if it can be
    obtained from available license files"""
    license_needles = ["LICENSE", "LICENCE", "COPYING", "PKG-INFO", "README", "METADATA"]
    license_files = available_files(pkg_dir, license_needles)
    for lf in license_files:
        if lf.is_dir():
            return detect_license(lf)
        return license_from_file(lf)
    return "License UNKN"


def license_from_file(file_path: Path) -> str:
    with open(file_path, "r", encoding="utf-8") as lfile:
        try:
            # lower case string for comparisons
            ltxt = lfile.read().lower()
        except UnicodeDecodeError:
            print("Could not read file %s." % file_path)
            return "License ERR"
        # MPL
        if "mozilla public license" in ltxt:
            if "version 2.0" in ltxt:
                return "MPL-2.0"
            if "version 1.1" in ltxt:
                return "MPL-1.1"
        # Python
        if "python software foundation" in ltxt:
            if "version 2" in ltxt:
                return "Python-2.0"
            return "Python-UNKN"
        # GPL
        if "gnu general public license" in ltxt:
            if "version 3" in ltxt:
                return "GPL-3.0"
            if "version 2" in ltxt:
                return "GPL-2.0"
            if "version 1" in ltxt:
                return "GPL-1.0"
            return "GPL-UNKN"
        # Apache
        if "apache license" in ltxt:
            if "version 2.0" in ltxt:
                return "Apache-2.0"
            return "Apache-UNKN"
        # BSD
        if "redistribution and use in source and binary forms" in ltxt:
            if (
                "redistributions of source code must" in ltxt
                and "redistributions in binary form must" in ltxt
            ):
                if "neither the name of" in ltxt:
                    if "all advertising materials mentioning features" in ltxt:
                        return "BSD-4-Clause"
                    return "BSD-3-Clause"
                return "BSD-2-Clause"
            return "BSD-UNKN"
        # BSL
        if "boost software license" in ltxt:
            if "version 1.0" in ltxt:
                return "BSL-1.0"
            return "BSL-UNKN"
        # MIT - CMU style
        if "permission to use, copy, modify, and distribute this" in ltxt:
            return "MIT-CMU"
        # MIT
        if "permission is hereby granted, free of charge, to" in ltxt:
            return "MIT"
        # Artistic
        if "artistic" in ltxt:
            if "license 1.0" in ltxt or '"package" refers to the collection of files' in ltxt:
                return "Artistic-1.0"
            if "license 2.0" in ltxt or "everyone is permitted to copy and distribute" in ltxt:
                return "Artistic-2.0"
            return "Artistic-UNKN"
        # CC0 1.0
        if "cc0 1.0" in ltxt:
            return "CC0 1.0"
        # CDDL 1.0
        if "cddl" in ltxt or "common development and distribution license" in ltxt:
            if "version 1.0" in ltxt:
                return "CDDL-1.0"
            return "CDDL-UNKN"
        # ISC
        if "isc license" in ltxt:
            return "ISC"
        # LGPL
        if "gnu lesser general public license" in ltxt:
            if "version 3" in ltxt:
                return "LGPL-3.0"
            if "version 2.1" in ltxt:
                return "LGPL-2.1"
            if "version 2" in ltxt:
                return "LGPL-2.0"
            return "LGPL-UNKN"
        # OML
        if "open market permits you to use, copy" in ltxt:
            return "OML"
        # PIL
        if "python imaging library" in ltxt:
            return "PIL"
        # X11
        if "x11 license" in ltxt:
            return "X11"

    return "License UNKN"


def detect_version(pkg_dir: Path, name="") -> str:
    """Return the version for a given package directory pkg_dir and package
    name name if it can be obtained from available files"""
    version_needles = ["PKG-INFO", "VERSION", "FAQ", "README", "METADATA"]
    version_files: List[Path] = available_files(pkg_dir, version_needles)
    for vf in version_files:
        if vf.is_dir():
            return detect_version(vf)
        with open(vf, "r") as vfile:
            try:
                lines = vfile.readlines()
            except UnicodeDecodeError:
                print("Could not read file %s." % vf)
                # sys.stderr.write(traceback.format_exc())
                return "Version ERR"
            for line in lines:
                if re.match("version: ", line.lower()):
                    return re.sub(r"^[^:]*:\ ", "", line).rstrip("\n")

    if name:
        dir_name = str(pkg_dir)
        needle = re.sub(r"Perl module: |Python module: | ", "", name)
        if needle in dir_name:
            return dir_name.lstrip("TMP/" + needle).lstrip("-")
        if needle.lower() in dir_name:
            return dir_name.lstrip("TMP/" + needle.lower()).lstrip("-")

    return "Version UNKN"


def detect_name(pkg_dir: Path, case_sensitive_names) -> str:
    name_files: List[Path] = available_files(pkg_dir, ["PKG-INFO", "METADATA"])
    name = ""
    for nf in name_files:
        with open(nf, "r") as file_:
            lines = file_.readlines()
            for line in lines:
                if re.match("name: ", line.lower()):
                    name = re.sub(r"^[^:]*:\ ", "", line).rstrip("\n").strip()
            if name:
                break

    if not name:
        dir_name = str(pkg_dir)
        if ".dist-info" in dir_name or ".egg-info" in dir_name:
            name = re.sub(r"-[a-z\d\.]*-info$", "", dir_name.lstrip("TMP/")).split("/")[-1]
        else:
            name = re.sub(r"-[a-z\d\.]*$", "", dir_name.lstrip("TMP/"))

    if name.lower() in case_sensitive_names:
        return case_sensitive_names[name.lower()]
    return name


def prepend_name(name, path) -> str:
    if "perl-modules/" in path:
        return "Perl module: %s" % name
    if "python3-modules/" in path:
        return "Python module: %s" % name
    if "agents" in path and "windows" in path:
        return "PyWinAg module: %s" % name
    return name


def download_cmk_sources(version) -> Path:
    if version == "master":
        version = re.sub("-", ".", str(date.today()))
    file_name = "check-mk-enterprise-%s.cee.tar.gz" % version

    print_separator()
    print("Downloading sources package %s from download.checkmk.com\n" % file_name)
    os.system(
        "wget --user d-intern https://download.checkmk.com/checkmk/%s/%s --ask-password"
        % (version, file_name)
    )
    return Path(file_name)


def get_license_links() -> Dict[str, str]:
    """Returns a dict with license id as key and license link as value based on the
    specified license links CSV file"""
    license_links = {}
    with open(license_links_file, "r") as csv_file:
        csv_file.readline()  # Drop line of headers
        reader = csv.reader(csv_file)
        for line in reader:
            license_links[line[0]] = line[1]
    return license_links


def update_py3_modules(
    rows: List[List[str]], py3_modules: Dict[str, str], verbose: bool = False
) -> List[List[str]]:
    pm_rows = [row for row in rows if row[0].startswith("Python module: ")]
    py_module_str_tag: str = "Python module: "

    drop_rows: List[List[str]] = []
    for row in pm_rows:
        name = re.sub(f"^{py_module_str_tag}", "", row[0])
        listed_version: str = row[1]
        found_version: Optional[str] = py3_modules.get(name, None)

        if not found_version:
            if verbose:
                print(
                    "Removing package: %s, %s" % (row[0], row[1])
                    + (" (%s)" % row[4] if len(row) > 4 else "")
                )
            drop_rows.append(row)
        elif found_version != listed_version:
            if verbose:
                print("Removing package: %s, %s (%s)" % (row[0], row[1], row[2]))
                print("Adding package: %s, %s (License UNKN)" % (row[0], found_version))
            drop_rows.append(row)
            rows.append([row[0], found_version, "License UNKN", "", "", ""])
            del py3_modules[name]
        else:
            del py3_modules[name]

    for name, version in py3_modules.items():
        name = py_module_str_tag + name
        if verbose:
            print("Adding package: %s, %s (License UNKN)" % (name, version))
        rows.append([name, version, "License UNKN", "", "", ""])

    rows = [x for x in rows if not x in drop_rows]
    return rows


def update_py_packages(
    rows: List[List[str]], path_cmk_dir: Path, verbose: bool = False
) -> List[List[str]]:
    print_separator()
    print('Inspecting Checkmk repository "%s" for python package update\n' % path_cmk_dir)

    # Find all package paths within the given Checkmk sources repository
    found_packages: List[str] = find(["*" + ze for ze in ZIP_ENDINGS], path_cmk_dir)
    if not found_packages:
        print('For the given Checkmk repository "%s" no package paths were found.' % path_cmk_dir)
        sys.exit()

    # Get all python 3 modules from Pipfile and update them separately
    py3_modules: Dict[str, str] = get_packages_from_pipfile(path_cmk_dir)
    rows = update_py3_modules(
        rows,
        py3_modules,
        verbose,
    )

    # Exceptional package paths that cannot be matched via package name
    # TODO: Keep these up to date or rather get rid of these altogether
    exceptions: Dict[str, str] = {
        "GNU patch": "omd/packages/patch/patch-2.7.6.tar.gz",
        "Heirloom Packaging Tools": "omd/packages/heirloom-pkgtools/heirloom-pkgtools-070227.tar.bz2",
        "Perl module: DateTime::TimeZone": "omd/packages/perl-modules/src/DateTime-TimeZone-1.88.tar.gz",
        "Perl module: Iperl module: O": "omd/packages/perl-modules/src/IO-1.25.tar.gz",
    }

    case_sensitive_names: Dict[str, str] = {}
    drop_rows: List[List[str]] = []
    pywinag_entries: List[List[str]] = []
    # Go through all packages already listed and try to match them with
    # the exceptions and the found package paths
    for row in rows:
        name: str = row[0]
        case_sensitive_names[name.lower()] = name
        path: str = row[4]

        if "PyWinAg" in name:
            pywinag_entries.append(row)
            continue

        if "Python module: " in name:
            continue

        # Match the exceptional package paths first
        if name in exceptions and exceptions[name] in found_packages:
            found_packages.remove(exceptions[name])
            continue

        path_match = False
        for fpath in found_packages:
            if path == fpath:
                found_packages.remove(fpath)
                path_match = True
                break
        if not path_match:
            if verbose:
                print("Removing package: %s (%s)" % (name, path))
            drop_rows.append(row)

    rows = [x for x in rows if not x in drop_rows]

    license_links = get_license_links()

    pywinag_matches = []
    path_tmp_dir = Path("TMP")
    for path in found_packages:
        rmtree(path_tmp_dir, ignore_errors=True)
        os.mkdir(path_tmp_dir)
        match_path = path_cmk_dir / path
        if "tar" in path:
            os.system("tar xf %s --directory %s" % (match_path, path_tmp_dir))
        elif "zip" in path:
            os.system("unzip -oq %s -d %s" % (match_path, path_tmp_dir))
        elif "cab" in path:
            os.system("cabextract -q %s -d %s" % (match_path, path_tmp_dir))
        else:
            if verbose:
                print("No extractable file found under: %s" % path)
            continue

        unzipped_dir: Path = path_tmp_dir / path_from_zipped(os.path.basename(path))
        search_dirs: List[Path] = [unzipped_dir]
        is_pywinag = False
        if not os.path.isdir(unzipped_dir):
            # Handle Python packages included in the Windows agent
            if re.search(r"agents/.*[windows|wnx].*python-", path):
                is_pywinag = True

                # Update the Python package itself
                pywinag_match = False
                for row in pywinag_entries:
                    if path == row[4]:
                        pywinag_matches.append(row)
                        pywinag_match = True

                if not pywinag_match:
                    name = "Python for Windows agent (PyWinAg)"
                    version = re.sub(
                        r"python-|%s" % "|".join(ZIP_ENDINGS), "", os.path.basename(path)
                    )
                    license_ = "Python-2.0"
                    license_link = license_links[license_] if license_ in license_links else ""
                    if verbose:
                        print("Adding package: %s, %s (%s)" % (name, version, path))
                    rows.append([name, version, license_, license_link, path])

                # Search for *.dist-info and *.egg-info directories within the Python package
                search_dirs = [
                    path_tmp_dir / d for d in find("*-info", path_tmp_dir, find_dirs=True)
                ]
                path = "included in " + path
            else:
                print("Unextractable/Unknown package on path: %s" % path)
                continue

        for path_pkg_dir in search_dirs:
            license_ = detect_license(path_pkg_dir)
            license_link = license_links[license_] if license_ in license_links else ""
            name = detect_name(path_pkg_dir, case_sensitive_names)
            if name == "check_mk":
                if verbose:
                    print("Skipping package: %s (%s)" % (name, path))
                continue
            version = detect_version(path_pkg_dir, name)
            name = prepend_name(name, path)

            if is_pywinag:
                pywinag_match = False
                for row in pywinag_entries:
                    if [name, version] == row[:2] and path == row[4]:
                        pywinag_matches.append(row)
                        pywinag_match = True
                if pywinag_match:
                    continue

            if verbose:
                print("Adding package: %s, %s (%s)" % (name, version, path))
                if "UNKN" in version or "UNKN" in license_:
                    print("\t- unknown version or license: %s, %s" % (version, license_))
            rows.append([name, version, license_, license_link, path])

    rmtree(path_tmp_dir)

    for row in pywinag_entries:
        if row not in pywinag_matches:
            if verbose:
                print("Removing package: %s (%s)" % (row[0], row[4]))
            rows.remove(row)

    return sorted(rows, key=lambda x: x[0].lower())


def update_js_dependencies(rows: List[List[str]], verbose: bool = False) -> List[List[str]]:
    print_separator()
    print(
        'Inspecting current Checkmk git on branch "%s" for js dependency update\n'
        % os.popen("git branch --show-current").read().rstrip("\n")
    )
    license_links = get_license_links()

    with os.popen("npx license-checker --json --start ../../") as os_output:
        license_json = json.loads(os_output.read())

    found_rows: List[List[str]] = []
    for key, data in license_json.items():
        name = re.sub(r"@[^@]*$", "", key)
        version = re.sub(r"^.+@", "", key)
        license_ = data["licenses"]
        license_link = license_links[license_] if license_ in license_links else ""
        found_rows.append([name, version, license_, license_link, ""])

    drop_rows: List[List[str]] = []
    match: bool
    frow: Optional[List[str]]
    for row in rows:
        match = False
        frow = None
        for frow in found_rows:
            if row[:2] == frow[:2]:
                match = True
                break
            if row[0] == frow[0]:
                if verbose:
                    print("Removing package: %s, %s (%s)" % (row[0], row[1], row[2]))
                    print("Adding package: %s, %s (%s)" % (frow[0], frow[1], frow[2]))
                drop_rows.append(row)
                rows.append(frow)
                match = True
                break
        if match:
            if frow:
                found_rows.remove(frow)
        else:
            if verbose:
                print("Removing package: %s, %s (%s)" % (row[0], row[1], row[2]))
            drop_rows.append(row)

    for frow in found_rows:
        if verbose:
            print("Adding package: %s, %s (%s)" % (frow[0], frow[1], frow[2]))
        rows.append(frow)

    return sorted([x for x in rows if not x in drop_rows], key=lambda x: x[0].lower())


def write_to_csv(data, licenses_csv):
    with open(licenses_csv, "w", newline="", encoding="utf-8") as ofile:
        writer = csv.writer(ofile, lineterminator="\n")
        for row in data:
            writer.writerow(row[0])
            writer.writerows(row[1])
            if not data.index(row) == len(data) - 1:
                writer.writerow([""] * len(row[1][0]))


def parse_arguments():
    """Argument parser for update licenses script handling the following arguments:
    version     Set the Checkmk version for which licenses shall be updated.
    path        Provide a path to a local CheckMK source repository (instead of downloading)
    """
    parser = argparse.ArgumentParser(
        description="Script for helping you update the list of licenses for any "
        + "given Checkmk source repository",
        usage="./update_licenses [-h] [-v] [--path] [--version]",
    )
    parser.add_argument(
        "--version", help="Set the Checkmk version for which licenses shall be updated."
    )
    parser.add_argument(
        "--path",
        help="Provide a path to a local CheckMK source repository (instead of downloading)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Write updated and missing package information to the terminal",
    )
    parsed = parser.parse_args()
    if not parsed.path and not parsed.version:
        print("Either argument --path or --version needed. None given.\n")
        parser.print_help()
        sys.exit(2)

    return parsed


def get_packages_from_pipfile(path_sources_dir) -> Dict[str, str]:
    pipfile_path: Path = Path(path_sources_dir / "Pipfile")
    pipfile = Pipfile.load(filename=pipfile_path)
    data: Dict[str, str] = pipfile.data["default"]
    delete_keys: List[str] = []

    for k, d in data.items():
        if isinstance(d, str) and d.startswith("=="):
            data[k] = re.sub("^==", "", d)
        else:
            delete_keys.append(k)

    for k in delete_keys:
        del data[k]

    return data


def main(args):
    try:
        path_omd = Path(__file__).resolve().parent.parent
        if args.path:
            path_sources_dir = Path(args.path)
        else:
            path_sources_pkg: Path = download_cmk_sources(args.version)
            if not path_sources_pkg.is_file():
                print("Download file %s not found. Check version and password." % path_sources_pkg)
                return
            os.system("tar xf %s" % path_sources_pkg)
            path_sources_dir = Path(re.sub(".tar.gz", "/", str(path_sources_pkg)))
        licenses_csv = Path(path_omd / "Licenses.csv")
    except:
        if not args.path and path_sources_pkg.is_file():
            os.unlink(path_sources_pkg)
            if path_sources_dir.is_dir():
                rmtree(path_sources_dir)
        if Path("TMP").is_dir():
            rmtree("TMP")
        raise OSError

    old_data = []
    with open(licenses_csv, "r") as csv_file:
        for line in csv.reader(csv_file):
            old_data.append(line)

    section_needles = [
        ["Name", "Version"],  # Python packages
        ["Icons", ""],
        ["JavaScript and CSS", ""],
        ["JavaScript dependencies", ""],  # JS dependencies
    ]
    data_per_section = []
    section_idx = 0
    for idx, line in enumerate(old_data):
        needle = section_needles[section_idx]
        if set(needle) <= set(line):  # if A is a subset of B
            if section_idx > 0:
                data_per_section[section_idx - 1].append(old_data[start : idx - 1])
            start = idx + 1
            data_per_section.append([line])
            if section_idx == len(section_needles) - 1:
                data_per_section[section_idx] = [line, old_data[start:]]
                break
            section_idx += 1

    data_per_section[0][1] = update_py_packages(
        data_per_section[0][1], path_sources_dir, args.verbose
    )
    data_per_section[3][1] = update_js_dependencies(data_per_section[3][1], args.verbose)
    write_to_csv(data_per_section, licenses_csv)

    if not args.path:
        os.unlink(path_sources_pkg)
        rmtree(path_sources_dir)


if __name__ == "__main__":
    try:
        args = parse_arguments()
        main(args)
        sys.exit(0)
    except Exception:
        sys.stderr.write(traceback.format_exc())
        sys.exit(1)
