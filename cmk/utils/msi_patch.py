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
from typing import Optional, Tuple  # pylint: disable=unused-import

import sys
import re

import uuid
import yaml

# Explicitly check for Python 3 (which is understood by mypy)
if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path

TRADITIONAL_UUID = "{BAEBF560-7308-4D53-B426-903EA74B1D7E}"
MSI_PACKAGE_CODE_MARKER = "Intel;1033"
MSI_PACKAGE_CODE_OFFSET = len("Intel;1033") + 10  #
# UUID regex
regex = re.compile('^{[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}}', re.I)


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


# converts any text to SHA-1 based uuid
def generate_uuid_from_base(base):
    # type: (str) -> str
    return ("{%s}" % uuid.uuid5(uuid.NAMESPACE_DNS, base)).upper()


def write_state_file(path_to_state, pos, code):
    # type: (Optional[Path], int, str) -> None
    if path_to_state is not None:
        state = {"msi_info": {"package_code_pos": pos, "package_code_value": code}}
        with path_to_state.open("w", encoding="utf-8") as f:
            yaml.dump(state, f, encoding='utf-8', allow_unicode=True)


def load_state_file(path_to_state):
    # type: (Optional[Path]) -> Tuple[int, str]

    if path_to_state is not None and path_to_state.exists():
        with path_to_state.open("r", encoding="utf-8") as f:
            result = yaml.safe_load(f)
            if result is not None:
                root = result["msi_info"]
                return root["package_code_pos"], root["package_code_value"]

    return -1, ""


# engine to patch MSI file with new code
# optionally can save state file with results of patching
# by default amsk is TRADITIONAL
# by default uuid is generated
def patch_package_code(f_name, mask=None, package_code=None, state_file=None):
    # type: (str, Optional[str], Optional[str], Optional[Path]) -> bool

    p = Path(f_name)
    if not p.exists():
        return False

    if package_code is None or len(package_code) == 0:
        package_code = generate_uuid()

    if mask is None or len(mask) == 0:
        mask = TRADITIONAL_UUID

    data = p.read_bytes()  # type:ignore
    pos = data.find(mask.encode('ascii'))
    if pos == -1:
        write_state_file(state_file, -1, "")
        return False

    ret = data.replace(mask.encode('ascii'), package_code.encode('ascii'), 1)
    p.write_bytes(ret)  # type:ignore

    write_state_file(state_file, pos, package_code)

    return True


# engine to patch MSI file using already existsing state file
def patch_package_code_by_state_file(f_name, state_file, package_code=None):
    # type: (str, Path, Optional[str]) -> bool

    p = Path(f_name)
    if not p.exists():
        return False

    pos, id_ = load_state_file(state_file)

    if pos == -1 or id_ == "":
        return False

    return patch_package_code(f_name, mask=id_, package_code=package_code)


def valid_uuid(uuid_value):
    # type: (str) -> bool
    match = regex.match(uuid_value)
    return bool(match)


# engine to patch MSI file with new code
# search for 'Intel;1033' marker, add offset and patch code
def patch_package_code_by_marker(f_name, package_code=None, state_file=None):
    # type: (str, Optional[str], Optional[Path]) -> bool

    p = Path(f_name)
    if not p.exists():
        return False

    if package_code is None:
        package_code = generate_uuid()
    elif not valid_uuid(package_code):
        package_code = generate_uuid_from_base(package_code)

    data = p.read_bytes()  # type:ignore
    location = data.find(MSI_PACKAGE_CODE_MARKER.encode('ascii'))
    if location == -1:
        return False

    location += MSI_PACKAGE_CODE_OFFSET

    if data[location] != b"{":
        return False

    start = location
    end = start + len(package_code)
    out = data[:start] + package_code.encode('ascii') + data[end:]
    p.write_bytes(out)  # type:ignore

    write_state_file(state_file, start, package_code)

    return True


# we want oto use this module in Windows to patch files in production
# py -2 msi_patch.py code -v ../../artefacts/check_mk_agent.msi
# MAIN:
if __name__ == '__main__':
    mode, file_name, param = parse_command_line(sys.argv)

    if mode == "code":
        success = patch_package_code(f_name=file_name, mask=param)
        exit(0 if success else 1)

    if mode == "1033":
        out_state_file = None if param == "" else Path(param)
        success = patch_package_code_by_marker(f_name=file_name, state_file=out_state_file)
        exit(0 if success else 1)

    print("Invalid mode '{}'".format(mode))
    exit(1)
