# pylint: disable=redefined-outer-name
import pytest  # type: ignore

import shutil
import os

from pathlib2 import Path

import cmk.utils.paths
from agents.windows.msibuild import msi_update


def test_parse_command_line():
    msi_file, source_dir, revision, version_name = msi_update.parse_command_line(
        ["stub", "msi", "dir", "rev", "vers"])
    assert msi_file == "msi"
    assert source_dir == "dir"
    assert revision == "rev"
    assert version_name == "vers"
    assert not msi_update.opt_verbose
    msi_file, source_dir, revision, version_name = msi_update.parse_command_line(
        ["stub", "-v", "msi", "dir", "rev", "vers"])
    assert msi_file == "msi"
    assert source_dir == "dir"
    assert revision == "rev"
    assert version_name == "vers"
    assert msi_update.opt_verbose


def test_export_msi_file(conf_dir, cmk_dir):
    # prepare file to tests
    if not cmk_dir.exists():
        pytest.skip("cmk_dir is not good")
    src = cmk_dir.joinpath(u"agents/wnx/test_files/msibuild/msi/check_mk_agent.msi")
    if not src.exists():
        pytest.skip("Path with MSI doesn't exist")

    out_dir = conf_dir.joinpath('idts')
    try:
        out_dir.mkdir()
        for entry in ["File", "Property", "Component"]:
            msi_update.export_msi_file("agents/windows/msibuild/", entry, src.__fspath__(),
                                       out_dir.__fspath__())
            f = out_dir.joinpath(entry + ".idt")
            assert f.exists()
    finally:
        if out_dir.exists():
            shutil.rmtree(out_dir.__fspath__())


def test_update_package_code(conf_dir, cmk_dir):
    if not cmk_dir.exists():
        pytest.skip("cmk_dir '{}' is not good".format(cmk_dir))
    src = cmk_dir.joinpath(u"agents/wnx/test_files/msibuild/msi/check_mk_agent.msi")
    if not src.exists():
        pytest.skip("Path '{}' with MSI doesn't exist".format(src))
    # prepare file to tests
    tgt = conf_dir.joinpath("check_mk_agent.msi")
    try:
        src = cmk_dir.joinpath(u"agents/wnx/test_files/msibuild/msi/check_mk_agent.msi")
        assert src.exists()
        content = src.read_bytes()
        assert content.find(b"BAEBF560-7308-4") != -1
        if tgt.exists():
            tgt.unlink()

        assert not tgt.exists()
        assert msi_update.copy_file_safe(src, tgt)
        msi_update.update_package_code(src.name, tgt.__fspath__())
        content = tgt.read_bytes()
        assert content.find(b"BAEBF560-7308-4") == -1
    finally:
        if tgt.exists():
            tgt.unlink()


def test_msi_file_table():
    a = msi_update.msi_file_table()
    assert len(a) == 4  # size for now(ini, yml, dat & cap)
    a_sorted = sorted(a)
    assert a == a_sorted  # array should be sorted


def test_msi_component_table():
    a = msi_update.msi_component_table()
    assert len(a) == 4  # size now(ini, yml, dat & cap)
    a_sorted = sorted(a)
    assert a == a_sorted  # array should be sorted


def test_copy_or_create(conf_dir):
    src_file = Path(conf_dir).joinpath("temp.x.in")
    dst_file = Path(conf_dir).joinpath("temp.x.out")

    # file doesn't exist, check file created
    msi_update.copy_or_create(src_file, dst_file, u"!!!")
    assert dst_file.exists()
    content = dst_file.read_text()
    assert content == "!!!"

    # files exists check file copied
    src_file.write_text(u"+++")
    msi_update.copy_or_create(src_file, dst_file, u"!!!")
    assert dst_file.exists()
    content = dst_file.read_text()
    assert content == "+++"


def test_generate_product_versions():
    test = [["1.7.0i1", "1.7.0.xxx"], ["1.2.5i4p1", "1.2.5.xxx"], ["2015.04.12", "15.4.12.xxx"]]

    for in_data, result in test:
        a = msi_update.generate_product_version(in_data, "xxx")
        assert a == result


def test_make_msi_copy(conf_dir):
    src_file = Path(conf_dir).joinpath("temp.in")
    with src_file.open('w') as s:
        s.write("+++".decode("utf8"))
    dst_file = Path(conf_dir).joinpath("temp.out")
    assert msi_update.copy_file_safe(src_file, dst_file)
    assert dst_file.exists()
    with dst_file.open('r') as d:
        content = d.read()
    assert content == "+++"


def test_msi_file(conf_dir, session_info):
    assert True
