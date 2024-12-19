#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import re
import sys
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

import yaml

TRADITIONAL_UUID: Final = "{BAEBF560-7308-4D53-B426-903EA74B1D7E}"
MSI_PACKAGE_CODE_MARKER: Final = "Intel;1033"
MSI_PACKAGE_CODE_OFFSET: Final = len("Intel;1033") + 10
_UUID_REGEX: Final = re.compile(
    "^{[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}}", re.I
)

# TODO(sk): remove 600 after all builds will be green, we need 600 temporary
_EXPECTED_WIN_VERSIONS: Final = ["600", "601"]  # Vist & 7: must be in sync with product.wxs
_MSI_WIN_VERSION_TEMPLATE: Final = "( VersionNT >= {} )"  # must be in sync with product.wxs


@dataclass
class _Parameters:
    mode: Literal["win_ver", "code", "1033"]
    file_name: Path
    mode_parameter: str


def parse_command_line(argv: Sequence[str]) -> _Parameters:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["win_ver", "code", "1033"], type=str)
    parser.add_argument("file_name", type=Path)
    parser.add_argument("mode_parameter", nargs="?")
    result = parser.parse_args(argv[1:])
    return _Parameters(
        mode=result.mode,
        file_name=result.file_name,
        mode_parameter=result.mode_parameter or "",
    )


def generate_uuid() -> str:
    return ("{%s}" % uuid.uuid1()).upper()


def generate_uuid_from_base(base: str) -> str:
    """converts any text to SHA-1 based uuid"""
    return ("{%s}" % uuid.uuid5(uuid.NAMESPACE_DNS, base)).upper()


def write_state_file(path_to_state: Path | None, pos: int, code: str) -> None:
    if path_to_state is None:
        return

    state = {"msi_info": {"package_code_pos": pos, "package_code_value": code}}
    with path_to_state.open("w", encoding="utf-8") as f:
        yaml.dump(state, f, encoding="utf-8", allow_unicode=True)


def load_state_file(path_to_state: Path | None) -> tuple[int, str]:
    """returns offset and value if found, offset is -1 - not found"""

    if path_to_state is not None and path_to_state.exists():
        with path_to_state.open(encoding="utf-8") as f:
            result = yaml.safe_load(f)
            if result is not None:
                root = result["msi_info"]
                return root["package_code_pos"], root["package_code_value"]

    return -1, ""


def patch_package_code(
    file_name: Path,
    *,
    old_code: str,
    new_code: str | None,
    state_file: Path | None,
) -> bool:
    """
    Reserve engine to patch MSI file with new code.
    This engine is universal(!) and used for debugging and testing purposes.

    Args:
        file_name: file to patch
        old_code: search for, if empty uses TRADITIONAL_UUID
        new_code: patch with, if None uses generate random code
        state_file: save results to if not None

    Returns:
        True on success
    """

    if not file_name.exists():
        return False

    data = file_name.read_bytes()
    old_uuid_data = (old_code or TRADITIONAL_UUID).encode("ascii")
    pos = data.find(old_uuid_data)
    if pos == -1:
        write_state_file(state_file, -1, "")
        return False

    new_uuid = new_code or generate_uuid()
    ret = data.replace(old_uuid_data, new_uuid.encode("ascii"), 1)
    file_name.write_bytes(ret)

    write_state_file(state_file, pos, new_uuid)

    return True


def patch_windows_version(
    f_name: Path,
    *,
    new_version: str,
) -> bool:
    """
    Patches the allowed Windows version in MSI file.

    Args:
        f_name: file to patch
        new_version: new version for example '602' or '610'

    Returns:
        true on success

    Some configurations may not work on the older Windows: we must prevent
    an installation by patching allowed Windows version.

    VersionNT is from
        https://docs.microsoft.com/de-at/windows/win32/msi/operating-system-property-values
        https://tarma.com/support/im9/using/symbols/variables/versionnt.htm

    ATTENTION: the values above are not always valid
        VersionNT is 600 allows Windows Vista(Server 2008) higher
        VersionNT is 602 allows Windows 8(Server 2012) or higher

    Conditions:
        The string _MSI_WIN_VERSION_TEMPLATE must be presented.
        Must be called to set 602 if Python module 3.8.7 or newer is added to the MSI.
    """

    if len(new_version) != 3:
        sys.stdout.write("New version must have size 3\n")
        return False

    p = f_name
    if not p.exists():
        sys.stdout.write(f"The file {p} isn't found\n")
        return False

    data = p.read_bytes()
    for version in _EXPECTED_WIN_VERSIONS:
        expected_blob = _MSI_WIN_VERSION_TEMPLATE.format(version).encode("ascii")
        if data.find(expected_blob) != -1:
            required_blob = _MSI_WIN_VERSION_TEMPLATE.format(new_version).encode("ascii")
            ret = data.replace(expected_blob, required_blob, 1)
            p.write_bytes(ret)
            return True

    sys.stdout.write("VersionNT matrix isn't found, impossible to patch\n")
    return False


def valid_uuid(uuid_value: str) -> bool:
    match = _UUID_REGEX.match(uuid_value)
    return bool(match)


def patch_package_code_by_marker(
    file_name: Path,
    *,
    new_uuid: str | None,
    state_file: Path | None,
) -> bool:
    """
    Main engine to patch MSI file with new code.
    Search for 'Intel;1033' marker, add offset and patch code

    Args:
        file_name: file to patch
        new_uuid: patch with, if None then generate random code, if not uuid: special generation(!)
        state_file: save results to if not None

    Returns:
        True on success
    """
    if not file_name.exists():
        return False

    if new_uuid is None:
        new_uuid = generate_uuid()
    elif not valid_uuid(new_uuid):
        new_uuid = generate_uuid_from_base(new_uuid)

    data = file_name.read_bytes()
    location = data.find(MSI_PACKAGE_CODE_MARKER.encode("ascii"))
    if location == -1:
        return False

    location += MSI_PACKAGE_CODE_OFFSET
    if data[location : location + 1] != b"{":
        return False

    start = location
    end = start + len(new_uuid)
    out = data[:start] + new_uuid.encode("ascii") + data[end:]
    file_name.write_bytes(out)

    write_state_file(state_file, start, new_uuid)
    return True


# we want to use this module in Windows to patch files in production
# py -2 msi_patch.py code -v ../../artefacts/check_mk_agent.msi
# MAIN:
if __name__ == "__main__":
    params = parse_command_line(sys.argv)
    match params.mode:
        case "win_ver":
            success = patch_windows_version(params.file_name, new_version=params.mode_parameter)
            sys.exit(0 if success else 1)

        case "code":
            success = patch_package_code(
                params.file_name, old_code=params.mode_parameter, new_code=None, state_file=None
            )
            sys.exit(0 if success else 1)

        case "1033":
            out_state_file = None if params.mode_parameter == "" else Path(params.mode_parameter)
            success = patch_package_code_by_marker(
                params.file_name, new_uuid=None, state_file=out_state_file
            )
            sys.exit(0 if success else 1)
        case _:
            sys.stdout.write(f"Invalid mode '{params.mode}'\n")

    sys.exit(1)
