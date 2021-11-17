#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shutil
from pathlib import Path

import pytest

from tests.testlib.site import Site

import cmk.utils.msi_engine as msi_engine

MSI_LOCATION = "share/check_mk/agents/windows"

EXPECTED_EXECUTABLES = ["msiinfo", "msibuild", "lcab"]

EXPECTED_TEST_FILES = ["check_mk_agent.msi", "check_mk.user.yml"]

# check base files are presented
# binaries and test files


@pytest.mark.parametrize("executable", EXPECTED_EXECUTABLES)
def test_executables(site: Site, executable):
    bin_path = Path(site.path("bin"))
    assert Path(bin_path / executable).exists(), "path: '{}' exe: '{}'".format(bin_path, executable)


@pytest.mark.parametrize("test_file", EXPECTED_TEST_FILES)
def test_files(site: Site, test_file):
    msi_path = Path(site.path(MSI_LOCATION))
    assert Path(msi_path / test_file).exists(), "path: '{}' file: '{}'".format(msi_path, test_file)


def _get_msi_file_path(site: Site):
    msi_path = Path(site.path(MSI_LOCATION))
    return msi_path / "check_mk_agent.msi"


# check the export with site/bin tools
def test_export_msi_file(site: Site, tmp_path):
    msi_file = _get_msi_file_path(site=site)

    out_dir = tmp_path / "idts"
    bin_path = site.path("bin/")
    try:
        out_dir.mkdir()
        for entry in ["File", "Property", "Component"]:
            msi_engine.export_msi_file(bin_path, entry, str(msi_file), str(out_dir))
            f = out_dir / (entry + ".idt")
            assert f.exists(), "Ups for [{}] {}".format(entry, f)
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
        content = src.read_bytes()
        pos_initial = content.find(b"4E18343A-5E32-1")
        assert pos_initial != -1
        if tgt.exists():
            tgt.unlink()

        # random uuid
        assert not tgt.exists()
        assert msi_engine.copy_file_safe(src, tgt)
        msi_engine.update_package_code(tgt)
        tgt_content = tgt.read_bytes()
        assert tgt_content.find(b"4E18343A-5E32-1") == -1

        if tgt.exists():
            tgt.unlink()

        # case for the uuid in command line
        assert not tgt.exists()
        assert msi_engine.copy_file_safe(src, tgt)
        msi_engine.update_package_code(tgt, "{01234567-1234-1234-1234-012345678901}")
        tgt_content = tgt.read_bytes()
        pos = tgt_content.find(b"01234567-1234-1234")
        assert pos == pos_initial

        if tgt.exists():
            tgt.unlink()

        # case for the hash
        assert not tgt.exists()
        assert msi_engine.copy_file_safe(src, tgt)
        msi_engine.update_package_code(tgt, "012")
        tgt_content = tgt.read_bytes()
        pos = tgt_content.find(b"21FAC8EF-8042-50CA-8C85-FBCA566E726E")

        assert pos == pos_initial
    finally:
        if tgt.exists():
            tgt.unlink()


def test_copy_or_create(tmp_path: Path) -> None:
    src_file = tmp_path / "temp.x.in"
    dst_file = tmp_path / "temp.x.out"

    # file doesn't exist, check file created
    msi_engine.copy_or_create(src_file, dst_file, "!!!")
    assert dst_file.exists()
    content = dst_file.read_text()
    assert content == "!!!"

    # files exists check file copied
    src_file.write_text("+++")
    msi_engine.copy_or_create(src_file, dst_file, "!!!")
    assert dst_file.exists()
    content = dst_file.read_text()
    assert content == "+++"


def test_generate_product_versions():
    test = [
        ["1.7.0i1", "1.7.0.xxx"],
        ["1.2.5i4p1", "1.2.5.xxx"],
        ["2015.04.12", "15.4.12.xxx"],
        ["2.0.0i1", "2.0.0.xxx"],
        ["1.6.0-2020.02.20", "1.6.0.xxx"],
    ]

    for in_data, result in test:
        a = msi_engine.generate_product_version(in_data, "xxx")
        assert a == result


def test_make_msi_copy(tmp_path: Path) -> None:
    src_file = Path(tmp_path, "temp.in")
    with src_file.open("w") as s:
        s.write("+++")
    dst_file = Path(tmp_path, "temp.out")
    assert msi_engine.copy_file_safe(src_file, dst_file)
    assert dst_file.exists()
    with dst_file.open("r") as d:
        content = d.read()
    assert content == "+++"
