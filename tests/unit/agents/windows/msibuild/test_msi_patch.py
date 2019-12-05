# pylint: disable=redefined-outer-name
import pytest  # type: ignore

import shutil
import os

from pathlib2 import Path

import cmk.utils.paths
from agents.windows.msibuild import msi_patch


def test_parse_command_line():
    try:
        mode, f, param = msi_patch.parse_command_line(
            ["/path/to/executable", "mode", "msi", "param"])
    except Exception as _:
        assert False

    assert mode == "mode"
    assert f == "msi"
    assert param == "param"

    try:
        mode, f, param = msi_patch.parse_command_line(["/path/to/executable", "mode", "msi"])
    except Exception as _:
        assert False

    assert mode == "mode"
    assert f == "msi"
    assert param == ""

    try:
        mode = msi_patch.parse_command_line(["/path/to/executable", "mode"])
        assert False
    except Exception as _:
        assert True


def test_patch_package_code(conf_dir, cmk_dir):
    # prepare file to tests
    if not cmk_dir.exists():
        pytest.skip("cmk_dir is not good")
    fname = u"test_bin.tst"
    src = cmk_dir / u"agents/wnx/test_files/msibuild/msi" / fname
    if not src.exists():
        pytest.skip("Path with MSI doesn't exist")

    uuid = msi_patch.generate_uuid()

    # prepare test file
    dst = conf_dir / fname
    shutil.copy(str(src), str(dst))
    base_content = dst.read_bytes()
    assert base_content.find(msi_patch.TRADITIONAL_UUID.encode('ascii')) != -1

    # patch 1
    assert msi_patch.patch_package_code(f_name=dst, mask="", package_code=uuid)

    new_content = dst.read_bytes()
    assert new_content.find(msi_patch.TRADITIONAL_UUID.encode('ascii')) == -1
    assert new_content.find(uuid.encode('ascii')) != -1

    # prepare test file
    shutil.copy(str(src), str(dst))
    # patch 2
    assert msi_patch.patch_package_code(f_name=dst, mask=msi_patch.TRADITIONAL_UUID)

    new_content = dst.read_bytes()
    assert new_content.find(msi_patch.TRADITIONAL_UUID.encode('ascii')) == -1

    # prepare test file
    shutil.copy(str(src), str(dst))
    # patch 3
    assert not msi_patch.patch_package_code(f_name=dst, mask="Cant/Be/Found/In")

    new_content = dst.read_bytes()
    assert new_content.find(msi_patch.TRADITIONAL_UUID.encode('ascii')) != -1
