#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from __future__ import print_function
import sys
import uuid

from pathlib2 import Path

TRADITIONAL_UUID = "{BAEBF560-7308-4D53-B426-903EA74B1D7E}"


# used normally only in Windows build chain to patch
def parse_command_line(argv):
    # mode of the
    patch_mode = argv[1]

    # Directory where the sources are contained
    f_name = argv[2]

    # anything
    mask = "" if len(argv) <= 3 else argv[3]

    return patch_mode, f_name, mask


def generate_uuid():
    # type: () -> str
    return ("{%s}" % uuid.uuid1()).upper()


# engine to patch MSI file with new code
def patch_package_code(f_name, mask, package_code=""):
    # type: (str, str, str) -> bool

    p = Path(f_name)
    if not p.exists():
        return False

    if len(package_code) == 0:
        package_code = generate_uuid()

    if len(mask) == 0:
        mask = TRADITIONAL_UUID

    data = p.read_bytes()
    if data.find(mask.encode('ascii')) == -1:
        return False

    ret = data.replace(mask.encode('ascii'), package_code.encode('ascii'), 1)
    p.write_bytes(ret)
    return True


# we want oto use this module in Windows to patch files in production
# py -2 msi_patch.py code -v ../../artefacts/check_mk_agent.msi
# MAIN:
if __name__ == '__main__':
    mode, file_name, param = parse_command_line(sys.argv)
    if (mode == "code"):
        success = patch_package_code(f_name=file_name, mask=param)
        exit(0 if success else 1)

    print("Invalid mode '{}'".format(mode))
    exit(1)
