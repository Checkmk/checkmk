#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shutil
from pathlib import Path
from typing import Final

import pytest

from tests.testlib.site import Site

import cmk.utils.msi_engine as msi_engine
import cmk.utils.obfuscate as obfuscate

MSI_LOCATION: Final = "share/check_mk/agents/windows"
EXPECTED_EXECUTABLES: Final = ["msiinfo", "msibuild", "lcab"]
EXPECTED_TEST_FILES: Final = ["check_mk_agent.msi", msi_engine.AGENT_MSI_FILE, "check_mk.user.yml"]


@pytest.mark.parametrize("executable", EXPECTED_EXECUTABLES)
def test_executables(site: Site, executable) -> None:
    p = Path(site.path("bin")) / executable
    assert p.exists(), f"path: '{p}' exe: '{executable}'"


@pytest.mark.parametrize("test_file", EXPECTED_TEST_FILES)
def test_files(site: Site, test_file) -> None:
    p = Path(site.path(MSI_LOCATION)) / test_file
    assert p.exists(), f"path: '{p}' file: '{test_file}'"


def _get_msi_file_path_not_signed(site: Site) -> Path:
    return Path(site.path(MSI_LOCATION)) / msi_engine.AGENT_MSI_FILE


# check the export with site/bin tools
def test_export_msi_file(site: Site, tmp_path: Path) -> None:
    msi_file = _get_msi_file_path_not_signed(site=site)

    out_dir = tmp_path / "idts"
    bin_path = Path(site.path("bin/"))
    try:
        out_dir.mkdir()
        deobfuscated_file = out_dir / "deobfuscated.msi"
        obfuscate.deobfuscate_file(msi_file, file_out=deobfuscated_file)
        for name in ["File", "Property", "Component"]:
            msi_engine._export_msi_file_table(
                bin_path,
                name=name,
                msi_in=deobfuscated_file,
                out_dir=out_dir,
            )
            f = out_dir / (name + ".idt")
            assert f.exists(), f"Ups for [{name}] {f}"
    finally:
        if out_dir.exists():
            shutil.rmtree(str(out_dir))


def test_update_package_code(tmp_path: Path) -> None:
    # we use in this test msi file from the tst_files, not from site
    tgt = tmp_path / "check_mk_agent.msi"
    try:
        root_path = Path("agents/wnx/test_files/msibuild/msi")
        assert root_path.exists()
        src = root_path / "check_mk_agent.msi"
        assert src.exists()
        pos_initial = src.read_bytes().find(b"4E18343A-5E32-1")
        assert pos_initial != -1
        tgt.unlink(missing_ok=True)

        # random uuid
        assert not tgt.exists()
        assert msi_engine._copy_file_safe(src, d=tgt)
        msi_engine.update_package_code(tgt, package_code=None)
        tgt_content = tgt.read_bytes()
        assert tgt_content.find(b"4E18343A-5E32-1") == -1
        tgt.unlink(missing_ok=True)

        # case for the uuid in command line
        assert not tgt.exists()
        assert msi_engine._copy_file_safe(src, d=tgt)
        msi_engine.update_package_code(tgt, package_code="{01234567-1234-1234-1234-012345678901}")
        tgt_content = tgt.read_bytes()
        pos = tgt_content.find(b"01234567-1234-1234")
        assert pos == pos_initial
        tgt.unlink(missing_ok=True)

        # case for the hash
        assert not tgt.exists()
        assert msi_engine._copy_file_safe(src, d=tgt)
        msi_engine.update_package_code(tgt, package_code="012")
        tgt_content = tgt.read_bytes()
        pos = tgt_content.find(b"21FAC8EF-8042-50CA-8C85-FBCA566E726E")

        assert pos == pos_initial
    finally:
        tgt.unlink(missing_ok=True)


def test_copy_or_create(tmp_path: Path) -> None:
    src_file = tmp_path / "temp.x.in"
    dst_file = tmp_path / "temp.x.out"

    # file doesn't exist, check file created
    msi_engine.copy_or_create(src_file, dst_file=dst_file, text="!!!")
    assert dst_file.read_text() == "!!!"

    # files exists check file copied
    src_file.write_text("+++")
    msi_engine.copy_or_create(src_file, dst_file=dst_file, text="!!!")
    assert dst_file.read_text() == "+++"


def test_make_msi_copy(tmp_path: Path) -> None:
    src_file = Path(tmp_path, "temp.in")
    with src_file.open("w") as s:
        s.write("+++")
    dst_file = Path(tmp_path, "temp.out")
    assert msi_engine._copy_file_safe(src_file, d=dst_file)
    assert dst_file.exists()
    with dst_file.open("r") as d:
        content = d.read()
    assert content == "+++"
