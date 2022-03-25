#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# this is a simple wrapper over next windows msi build tools
# - lcab
# - msiinfo
# - msibuild

# TODO: The refactoring is mandatory.

import os
import re
import shutil
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Final

import cmk.utils.obfuscate as obfuscate
from cmk.utils import msi_patch

AGENT_MSI_FILE: Final = "check_mk_agent_unsigned.msi"

opt_verbose = True


def verbose(text):
    if opt_verbose:
        sys.stdout.write(text + "\n")


def bail_out(text):
    sys.stderr.write("ERROR: %s\n" % text)
    sys.exit(1)


def msi_file_table():
    # we have to sort the table, the table is created by MSI installer
    return ["check_mk_install_yml", "checkmk.dat", "plugins_cap", "python_3.cab"]


def msi_component_table():
    # we have to sort the table, the table is created by MSI installer too
    return ["check_mk_install_yml_", "checkmk.dat", "plugins_cap_", "python_3.cab"]


def remove_cab(path_to_msibuild, msi):
    verbose("Removing product.cab from %s" % msi)
    cmd_line = (
        path_to_msibuild + "msibuild %s -q \"DELETE FROM _Streams where Name = 'product.cab'\""
    ) % msi

    if os.system(cmd_line) != 0:  # nosec
        bail_out("msibuild is failed on remove cab")


def create_new_cab(working_dir, file_dir):
    verbose("Generating new product.cab")

    files = ""
    for f in msi_file_table():
        files += "%s/%s " % (file_dir, f)

    cmd_line = "lcab -n %s %s/product.cab > nul" % (files, working_dir)

    if os.system(cmd_line) != 0:  # nosec
        bail_out("lcab is failed in create new cab")


def add_cab(path_to_msibuild, new_msi_filename, working_dir):
    verbose("Add modified product.cab")
    cmd_line = (path_to_msibuild + "msibuild %s -a product.cab %s/product.cab") % (
        new_msi_filename,
        working_dir,
    )

    if os.system(cmd_line) != 0:  # nosec
        bail_out("msi build is failed")


# tested
def update_package_code(new_msi_file, package_code_hash=None):
    if not msi_patch.patch_package_code_by_marker(new_msi_file, package_code=package_code_hash):
        raise Exception("Failed to patch package code")


def read_file_as_lines(f_to_read):
    with f_to_read.open("r", newline="", encoding="utf8") as in_file:
        return in_file.readlines()


def patch_msi_files(dir_name, version_build):
    use_dir = Path(dir_name)

    name = "File.idt"
    lines_file_idt = read_file_as_lines(use_dir / name)

    with (use_dir / (name + ".new")).open("w", newline="", encoding="utf8") as out_file:
        # first three lines of the table write back
        to_write = "".join(lines_file_idt[:3])
        out_file.write(to_write)

        for l in lines_file_idt[3:]:
            words = l.split("\t")
            filename = words[0]
            # check every file from the table whether it should be replaced
            for file_to_replace in msi_file_table():  # sorted(cabinet_files):
                if file_to_replace == filename:
                    work_file = use_dir / filename
                    if work_file.exists():
                        file_stats = work_file.stat()
                        new_size = file_stats.st_size
                        words[3] = str(new_size)
                    else:
                        verbose("'{}' doesn't exist".format(work_file))
                    break  # always leaving internal loop

            # The version of this file is different from the msi installer version !
            words[4] = version_build if words[4] else ""
            out_file.write("\t".join(words))


def patch_msi_components(dir_name):
    use_dir = Path(dir_name)

    name = "Component.idt"
    lines_component_idt = read_file_as_lines(use_dir / name)

    with (use_dir / (name + ".new")).open("w", newline="", encoding="utf8") as out_file:
        out_file.write("".join(lines_component_idt[:3]))

        for l in lines_component_idt[3:]:
            words = l.split("\t")
            if words[0] in msi_component_table():
                words[1] = ("{%s}" % uuid.uuid1()).upper()
            out_file.write("\t".join(words))


def patch_msi_properties(dir_name, product_code, version_build):
    use_dir = Path(dir_name)

    name = "Property.idt"
    lines_property_idt = read_file_as_lines(use_dir / name)
    with (use_dir / (name + ".new")).open("w", newline="", encoding="utf8") as out_file:
        out_file.write("".join(lines_property_idt[:3]))

        for line in lines_property_idt[3:]:
            tokens = line.split("\t")
            if tokens[0] == "ProductName":
                tokens[1] = "Check MK Agent 2.0\r\n"
            # The upgrade code defines the product family. Do not change it!
            #    elif tokens[0] == "UpgradeCode":
            #        tokens[1] = upgrade_code
            elif tokens[0] == "ProductCode":
                tokens[1] = product_code
            elif tokens[0] == "ProductVersion":
                tokens[1] = "%s\r\n" % ".".join(version_build.split(".")[:4])
            out_file.write("\t".join(tokens))


# tested
def copy_file_safe(s, d):
    try:
        shutil.copy(str(s), str(d))
        return True
    except IOError as ex:
        verbose("exception in copy safe {}".format(ex))
    return False


# tested
def copy_or_create(src_file, dst_file, text):
    if src_file.exists():
        copy_file_safe(src_file, dst_file)
        return

    # fallback
    with dst_file.open("w", newline="", encoding="utf8") as d:
        d.write(text)


# tested
def generate_product_version(version, revision_text):
    major, minor, build = "1", "0", "0"
    try:
        major, minor, build = [x.lstrip("0") for x in version.split("-")[0].split(".")[:3]]
        minor = "0" if minor == "" else minor
        build = "0" if build == "" else build
        if len(major) > 3:
            # Looks like a daily build.. 2015.03.05
            major = major[2:].lstrip("0")
    except Exception:
        pass

    product_version = "%s.%s.%s" % (major, minor, build)

    # Remove any traces of i, p, b versions. Windows can't handle them...
    # The revision should be enough to uniquely identify this build
    # The original version name is also still visible in the list of programs
    match = re.search("[a-z]", product_version)
    if match:
        result = product_version[: match.start(0)]
        if result[-1] == ".":
            result += "0"
        result += ".%s" % revision_text
        return result

    return "%s.%s" % (product_version, revision_text)


# tested
def export_msi_file(exe_path_prefix, entry_in, msi_in, out_dir):
    verbose("Export table %s from file %s" % (entry_in, msi_in))
    exe = exe_path_prefix + "msiinfo"
    if not Path(exe).exists():
        bail_out("{} is absent".format(exe))

    command = (exe + " export %(msi_file)s %(property)s > %(work_dir)s/%(property)s.idt") % {
        "msi_file": msi_in,
        "property": entry_in,
        "work_dir": out_dir,
    }
    result = os.system(command)  # nosec
    if result != 0:
        bail_out(
            "Failed to unpack msi table {} from {}, code is {}".format(entry_in, msi_in, result)
        )


# tested
def parse_command_line(argv):
    try:
        global opt_verbose
        if argv[1] == "-v":
            opt_verbose = True
            del argv[1]
        else:
            opt_verbose = False

        # MSI container to modify
        msi = argv[1]

        # Directory where the sources are contained
        from_dir = argv[2]

        # Revision (from build_version)
        revision_param = argv[3]

        # TODO: complete overhaul of version generation
        # Official version name, e.g
        # 1.2.5i4p1
        # 2015.04.12
        # 1.2.6-2015.04.12
        version_param = argv[4]

        if len(argv) > 5:
            package_code_hash = argv[5]  # aghash normally {...-...-..-...-...}
        else:
            package_code_hash = None

        return msi, from_dir, revision_param, version_param, package_code_hash

    except Exception as ex:
        bail_out(
            "Usage: {} msi_file_name.msi SourceDir BuildNumber VersionText [aghash], '{}'".format(
                sys.argv[0], ex
            )
        )


def msi_update_core(msi_file_name, src_dir, revision_text, version, package_code_base=None):
    try:
        new_version_build = generate_product_version(version, revision_text)

        if "OMD_ROOT" in os.environ:
            path_prefix = os.environ["OMD_ROOT"] + "/bin/"
            tmp_dir = os.environ["OMD_ROOT"] + "/tmp"
        else:
            path_prefix = "./"
            tmp_dir = "."

        new_msi_file = src_dir + "/" + AGENT_MSI_FILE
        work_dir = tempfile.mkdtemp(prefix=tmp_dir + "/msi-update.")
        deobfuscated_file = Path(new_msi_file)

        if (
            error := obfuscate.deobfuscate_file(Path(msi_file_name), file_out=deobfuscated_file)
        ) != 0:
            bail_out(f"Deobfuscate returns error {error}")

        # When this script is run in the build environment then we need to specify
        # paths to the msitools. When running in an OMD site, these tools are in
        # our path

        # Export required idt files into work dir
        for entry in ["File", "Property", "Component"]:
            export_msi_file(path_prefix, entry, deobfuscated_file, work_dir)

        verbose("Modify extracted files..")

        # ==============================================
        # Modify File.idt

        # Convert Input Files to Internal-MSI Presentation
        file_dir = work_dir

        yml_file = Path(src_dir, "check_mk.install.yml")
        yml_target = Path(file_dir, "check_mk_install_yml")
        copy_or_create(
            yml_file, yml_target, "# test file\r\nglobal:\r\n  enabled: yes\r\n  install: no\r\n"
        )

        if src_dir != file_dir:
            shutil.copy(src_dir + "/checkmk.dat", file_dir + "/checkmk.dat")
        shutil.copy(src_dir + "/plugins.cap", file_dir + "/plugins_cap")
        shutil.copy(src_dir + "/python-3.cab", file_dir + "/python_3.cab")

        patch_msi_files(work_dir, new_version_build)
        patch_msi_components(work_dir)
        patch_msi_properties(work_dir, ("{%s}\r\n" % uuid.uuid1()).upper(), new_version_build)
        # ==============================================

        # Rename modified tables
        for entry in ["Property", "File", "Component"]:
            p = Path(work_dir, entry).with_suffix(".idt.new")
            p.rename(p.with_suffix(""))

        for entry in ["Property", "File", "Component"]:
            if (
                os.system(  # nosec
                    (path_prefix + "msibuild %(new_msi_file)s -i %(work_dir)s/%(file)s.idt")
                    % {"new_msi_file": new_msi_file, "work_dir": work_dir, "file": entry}
                )
                != 0
            ):
                bail_out("failed main msibuild")

        # Update summary info with new uuid (HACK! - the msibuild tool is not able to do this on all systems)
        # In this step we replace the package code with a new uuid. This uuid is important, because it is
        # the unqiue identifier for this package. Inside the package the uuid is split into two halfs.
        # Each of it is updated with the corresponding new package code.
        update_package_code(new_msi_file, package_code_hash=package_code_base)

        # Remove original product.cab from stream
        remove_cab(path_prefix, new_msi_file)

        # Prepare product.cab file
        create_new_cab(work_dir, file_dir)

        # Add modified product.cab
        add_cab(path_prefix, new_msi_file, work_dir)

        shutil.rmtree(work_dir)
        verbose("Successfully created file " + new_msi_file)
    except Exception as e:
        # if work_dir and os.path.exists(work_dir):
        #    shutil.rmtree(work_dir)
        bail_out("Error on creating msi file: {}, work_dir is {}".format(str(e), str(work_dir)))


# We could want to test this module too
# Normally should not be called as a process
# typical testing code
# msi-update -v ../../wnx/test_files/msibuild/msi/check_mk_agent.msi ../../wnx/test_files/msibuild . 1.7.0i1

# MAIN:
if __name__ == "__main__":
    # package code can be None: used in Windows Build machine to generate something random
    # in bakery we are sending aghash to generate package code
    msi_file, source_dir, revision, version_name, config_hash = parse_command_line(sys.argv)
    msi_update_core(msi_file, source_dir, revision, version_name, package_code_base=config_hash)
