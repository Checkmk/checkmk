#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import sys
import uuid
from pathlib import Path
from typing import Optional, Tuple

import yaml

TRADITIONAL_UUID = "{BAEBF560-7308-4D53-B426-903EA74B1D7E}"
MSI_PACKAGE_CODE_MARKER = "Intel;1033"
MSI_PACKAGE_CODE_OFFSET = len("Intel;1033") + 10  #
# UUID regex
regex = re.compile("^{[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}}", re.I)

_expected_version = "600"  # this value must be in sync with Windows Agent Product.wxs
_matrix = "( VersionNT >= {} )"  # this string must be in sync with Windows Agent Product.wxs


# used normally only in Windows build chain to patch
def parse_command_line(argv):
    # mode of the
    patch_mode = argv[1]

    # Directory where the sources are contained
    f_name = argv[2]

    # anything
    mask = "" if len(argv) <= 3 else argv[3]

    return patch_mode, f_name, mask


def generate_uuid() -> str:
    return ("{%s}" % uuid.uuid1()).upper()


# converts any text to SHA-1 based uuid
def generate_uuid_from_base(base: str) -> str:
    return ("{%s}" % uuid.uuid5(uuid.NAMESPACE_DNS, base)).upper()


def write_state_file(path_to_state: Optional[Path], pos: int, code: str) -> None:
    if path_to_state is not None:
        state = {"msi_info": {"package_code_pos": pos, "package_code_value": code}}
        with path_to_state.open("w", encoding="utf-8") as f:
            yaml.dump(state, f, encoding="utf-8", allow_unicode=True)


def load_state_file(path_to_state: Optional[Path]) -> Tuple[int, str]:

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
def patch_package_code(
    f_name: str,
    mask: Optional[str] = None,
    package_code: Optional[str] = None,
    state_file: Optional[Path] = None,
) -> bool:

    p = Path(f_name)
    if not p.exists():
        return False

    if package_code is None or len(package_code) == 0:
        package_code = generate_uuid()

    if mask is None or len(mask) == 0:
        mask = TRADITIONAL_UUID

    data = p.read_bytes()
    pos = data.find(mask.encode("ascii"))
    if pos == -1:
        write_state_file(state_file, -1, "")
        return False

    ret = data.replace(mask.encode("ascii"), package_code.encode("ascii"), 1)
    p.write_bytes(ret)

    write_state_file(state_file, pos, package_code)

    return True


def patch_windows_version(
    f_name: Path,
    *,
    new_version: str,
) -> bool:
    """Patches the allowed Windows version in MSI file.
    Some configurations may not work on the older Windows operation systems, we want to prevent
    an installation by patching allowed Windows version.

    VersionNT is from
    https://docs.microsoft.com/de-at/windows/win32/msi/operating-system-property-values
    https://tarma.com/support/im9/using/symbols/variables/versionnt.htm

    But, ATTENTION, the values above are not always valid
    VersionNT is 600 allows Windows Vista(Server 2008) higher
    VersionNT is 602 allows Windows 8(Server 2012) or higher

    Conditions:
    The string _matrix with VersionNT 600 must be presented.
    Must be called to set 602 if Python module 3.8.7 or newer is added to the MSI.
    """

    if len(new_version) != 3:
        print("New version must have size 3")
        return False

    p = f_name
    if not p.exists():
        print(f"The file {p} isn't found")
        return False

    expected_blob = _matrix.format(_expected_version).encode("ascii")
    required_blob = _matrix.format(new_version).encode("ascii")
    data = p.read_bytes()
    pos = data.find(expected_blob)
    if pos == -1:
        print("VersionNT matrix isn't found, impossible to patch")
        return False

    ret = data.replace(expected_blob, required_blob, 1)
    p.write_bytes(ret)

    return True


# engine to patch MSI file using already existsing state file
def patch_package_code_by_state_file(
    f_name: str, state_file: Path, package_code: Optional[str] = None
) -> bool:

    p = Path(f_name)
    if not p.exists():
        return False

    pos, id_ = load_state_file(state_file)

    if pos == -1 or id_ == "":
        return False

    return patch_package_code(f_name, mask=id_, package_code=package_code)


def valid_uuid(uuid_value: str) -> bool:
    match = regex.match(uuid_value)
    return bool(match)


# engine to patch MSI file with new code
# search for 'Intel;1033' marker, add offset and patch code
def patch_package_code_by_marker(
    f_name: str, package_code: Optional[str] = None, state_file: Optional[Path] = None
) -> bool:

    p = Path(f_name)
    if not p.exists():
        return False

    if package_code is None:
        package_code = generate_uuid()
    elif not valid_uuid(package_code):
        package_code = generate_uuid_from_base(package_code)

    data = p.read_bytes()
    location = data.find(MSI_PACKAGE_CODE_MARKER.encode("ascii"))
    if location == -1:
        return False

    location += MSI_PACKAGE_CODE_OFFSET

    if data[location : location + 1] != b"{":
        return False

    start = location
    end = start + len(package_code)
    out = data[:start] + package_code.encode("ascii") + data[end:]
    p.write_bytes(out)

    write_state_file(state_file, start, package_code)

    return True


# we want to use this module in Windows to patch files in production
# py -2 msi_patch.py code -v ../../artefacts/check_mk_agent.msi
# MAIN:
if __name__ == "__main__":
    mode, file_name, param = parse_command_line(sys.argv)
    if mode == "win_ver":
        success = patch_windows_version(file_name, new_version=param)
        sys.exit(0 if success else 1)

    if mode == "code":
        success = patch_package_code(f_name=file_name, mask=param)
        sys.exit(0 if success else 1)

    if mode == "1033":
        out_state_file = None if param == "" else Path(param)
        success = patch_package_code_by_marker(f_name=file_name, state_file=out_state_file)
        sys.exit(0 if success else 1)

    print("Invalid mode '{}'".format(mode))
    sys.exit(1)
