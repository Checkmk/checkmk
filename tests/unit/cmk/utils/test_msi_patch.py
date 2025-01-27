#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import os
import shutil
from pathlib import Path
from typing import Final

import pytest

from cmk.utils import msi_patch


@pytest.fixture(name="conf_dir")
def fixture_conf_dir(tmp_path: Path) -> Path:
    path = tmp_path / "temp"
    path.mkdir(parents=True)
    return path


AAA_MARKER: Final = b"{AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA}"
MARKER: Final = msi_patch.TRADITIONAL_UUID.encode("ascii")
TEST_FILE: Final = Path("test_bin.tst")


def _get_test_file(fname: Path) -> Path:
    # we want to check that files are present
    # This check is mostly required to keep the test with BUILD in sync: scm checkout valid dirs,
    # directory tree, etc.
    root_path = Path(__file__).parent / "test-files"
    assert root_path.exists(), f"test dir is absent, work dir is '{os.getcwd()}'"
    src = root_path / fname
    assert src.exists(), f"test file '{src}' is absent, work dir is '{os.getcwd()}'"
    return src


def _find_uuid(content: bytes, the_uuid: str) -> bool:
    return content.find(the_uuid.encode("ascii")) != -1


def _marker_loc(file_name: Path, marker: bytes) -> int:
    return file_name.read_bytes().find(marker)


@pytest.fixture(name="state_file")
def fixture_state_file(conf_dir: Path) -> Path:
    return conf_dir / "msi_state.yml"


@pytest.fixture(name="work_file")
def fixture_work_file(conf_dir: Path) -> Path:
    src = _get_test_file(TEST_FILE)
    dst = conf_dir / TEST_FILE
    shutil.copy(str(src), str(dst))
    return dst


def test_parse_command_line() -> None:
    try:
        params = msi_patch.parse_command_line(["/path/to/executable", "win_ver", "msi", "param"])
        assert params == msi_patch._Parameters(
            mode="win_ver",
            file_name=Path("msi"),
            mode_parameter="param",
        )
    except Exception as _:
        raise AssertionError() from _

    try:
        params = msi_patch.parse_command_line(["/path/to/executable", "code", "msi"])
        assert params == msi_patch._Parameters(
            mode="code",
            file_name=Path("msi"),
            mode_parameter="",
        )
    except Exception as _:
        raise AssertionError() from _


def test_parse_command_line_invalid() -> None:
    with pytest.raises(SystemExit):
        msi_patch.parse_command_line(["/path/to/executable", "1033"])
    with pytest.raises(SystemExit):
        msi_patch.parse_command_line(["/path/to/executable", "1033", "msi", "a", "b"])


def test_critical_consts(conf_dir: Path) -> None:
    assert msi_patch.MSI_PACKAGE_CODE_OFFSET == 20
    assert msi_patch.MSI_PACKAGE_CODE_MARKER == "Intel;1033"


def test_low_level_api(conf_dir: Path, state_file: Path) -> None:
    assert msi_patch.generate_uuid() != msi_patch.generate_uuid()
    assert len(msi_patch.generate_uuid()) == 38
    msi_patch.write_state_file(state_file, 12, "12")
    assert (12, "12") == msi_patch.load_state_file(state_file)


def test_validate_content(work_content: bytes) -> None:
    assert work_content.find(MARKER) != -1


@pytest.mark.parametrize(
    "old_code, success, loc",
    [
        ("", True, 4),
        ("trashy", False, -1),
    ],
)
def test_patch_package_code_with_state(
    work_file: Path,
    work_content: bytes,
    state_file: Path,
    old_code: str,
    success: bool,
    loc: int,
) -> None:
    uuid = msi_patch.generate_uuid()
    assert (
        msi_patch.patch_package_code(
            work_file, old_code=old_code, new_code=uuid, state_file=state_file
        )
        == success
    )

    original_file = _get_test_file(TEST_FILE)
    assert work_file.stat().st_size == original_file.stat().st_size

    new_content = work_file.read_bytes()
    assert _find_uuid(new_content, uuid) == success
    assert (loc, uuid if success else "") == msi_patch.load_state_file(state_file)


def test_patch_windows_version(conf_dir: Path) -> None:
    """Tests version patching using the test file from test directory"""

    fname: Final = Path("test_msi_patch_version.tst")
    result: Final = b"( VersionNT >= 602 )"

    # copy
    src = _get_test_file(fname)
    dst = conf_dir / fname
    shutil.copy(src, dst)

    # testing
    assert not msi_patch.patch_windows_version(dst / "xx", new_version="602")  # no file
    assert not msi_patch.patch_windows_version(dst, new_version="6")  # bad version
    assert not msi_patch.patch_windows_version(dst, new_version="6020")  # bad version
    assert msi_patch.patch_windows_version(dst, new_version="602")  # valid call -> success
    assert not msi_patch.patch_windows_version(dst, new_version="602")  # no matrix -> fail
    assert dst.stat().st_size == src.stat().st_size
    assert _marker_loc(dst, result) != -1


def _check_content(
    work_file: Path, *, base_content: bytes, pos: int, uuid: str, marker: bytes
) -> None:
    new_content = work_file.read_bytes()
    assert new_content.find(marker) == -1
    new_pos = new_content.decode("utf-8").find(uuid)
    assert new_pos == pos
    z = new_content[pos : pos + len(uuid)]
    assert z.decode("utf-8") == uuid
    assert new_content[:pos] == base_content[:pos]
    assert new_content[pos + len(uuid) :] == base_content[pos + len(uuid) :]


def test_uuid_api() -> None:
    # relative random set of data, probably better to divide data in few arrays
    assert not msi_patch.valid_uuid("")
    assert not msi_patch.valid_uuid("1")
    assert msi_patch.valid_uuid("{80312934-35F7-11EA-A177-0800271CD485}")
    assert msi_patch.valid_uuid("{80312934-35F7-11EA-A177-0800271CD485}".lower())
    assert not msi_patch.valid_uuid("{80312934-35F7-11EA-A177-0800271CD_85}")
    assert not msi_patch.valid_uuid("{80312934-35F7-11EA-A177-0800271CDX85}")
    assert not msi_patch.valid_uuid("80312934-35F7-11EA-A177-0800271CDX85")
    assert not msi_patch.valid_uuid("DEFADEFADEFA")


def test_uuid_base() -> None:
    assert "{21fac8ef-8042-50ca-8c85-fbca566e726e}".upper() == msi_patch.generate_uuid_from_base(
        "012"
    )


@pytest.fixture(name="work_content")
def fixture_work_content(work_file: Path) -> bytes:
    return work_file.read_bytes()


@pytest.fixture(name="marker_pos")
def fixture_marker_pos(work_content: bytes) -> int:
    return work_content.find(MARKER)


def test_patch_package_code_by_marker(work_file: Path, work_content: bytes) -> None:
    uuid = msi_patch.generate_uuid()
    assert (pos := work_content.find(AAA_MARKER)) != -1
    assert msi_patch.patch_package_code_by_marker(work_file, new_uuid=uuid, state_file=None)
    _check_content(work_file, base_content=work_content, pos=pos, uuid=uuid, marker=AAA_MARKER)


def test_patch_package_code_by_marker_with_state_file(conf_dir: Path, work_file: Path) -> None:
    uuid = msi_patch.generate_uuid()
    st_f = conf_dir / "state_file_2.yml"
    assert msi_patch.patch_package_code_by_marker(work_file, new_uuid=uuid, state_file=st_f)
    assert (_marker_loc(work_file, uuid.encode("ascii")), uuid) == msi_patch.load_state_file(st_f)


@pytest.mark.parametrize("old_code", ["", msi_patch.TRADITIONAL_UUID])
def test_patch_package_code(
    work_file: Path, work_content: bytes, marker_pos: int, old_code: str
) -> None:
    assert marker_pos != -1
    uuid = msi_patch.generate_uuid()
    assert msi_patch.patch_package_code(
        work_file,
        old_code=old_code,
        new_code=uuid,
        state_file=None,
    )
    _check_content(work_file, base_content=work_content, pos=marker_pos, uuid=uuid, marker=MARKER)


def test_patch_package_code_notfound(work_file: Path) -> None:
    uuid = msi_patch.generate_uuid()
    assert not msi_patch.patch_package_code(
        work_file, old_code="Cant/Be/Found/In", new_code=uuid, state_file=None
    )
    assert _marker_loc(work_file, MARKER) != -1
