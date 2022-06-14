#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
import os
import re
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

import omdlib
import omdlib.main
import omdlib.utils
from omdlib.type_defs import CommandOptions
from omdlib.version_info import VersionInfo

from cmk.utils import version


def _strip_ansi(s):
    ansi_escape = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")
    return ansi_escape.sub("", s)


def test_initialize_site_ca(
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    site_id = "tested"
    ca_path = tmp_path / site_id / "etc" / "ssl"
    ca_path.mkdir(parents=True, exist_ok=True)

    mocker.patch(
        "omdlib.main.cert_dir",
        return_value=ca_path,
    )

    omdlib.main.initialize_site_ca(omdlib.main.SiteContext(site_id))
    assert (ca_path / "ca.pem").exists()
    assert (ca_path / "sites" / ("%s.pem" % site_id)).exists()


@pytest.fixture(autouse=True)
def omd_base_path(monkeypatch, tmp_path):
    monkeypatch.setattr(omdlib.utils, "omd_base_path", lambda: str(tmp_path))


@pytest.fixture()
def version_info():
    return VersionInfo(omdlib.__version__)


def test_hostname() -> None:
    assert omdlib.main.hostname() == os.popen("hostname").read().strip()


def test_main_help(site_context, capsys, version_info) -> None:
    omdlib.main.main_help(version_info, site_context)
    stdout = capsys.readouterr()[0]
    assert "omd COMMAND -h" in stdout


def test_main_version_of_current_site(site_context, capsys, monkeypatch, version_info) -> None:
    monkeypatch.setattr(omdlib, "__version__", "1.2.3p4")
    global_opts = omdlib.main.default_global_options()
    args: omdlib.main.Arguments = []
    options: CommandOptions = {}
    omdlib.main.main_version(version_info, site_context, global_opts, args, options)

    stdout = capsys.readouterr()[0]
    assert stdout == "OMD - Open Monitoring Distribution Version 1.2.3p4\n"


def test_main_version_root(capsys, monkeypatch, version_info) -> None:
    monkeypatch.setattr(omdlib, "__version__", "1.2.3p4")
    global_opts = omdlib.main.default_global_options()
    args: omdlib.main.Arguments = []
    options: CommandOptions = {}
    omdlib.main.main_version(version_info, omdlib.main.RootContext(), global_opts, args, options)

    stdout = capsys.readouterr()[0]
    assert stdout == "OMD - Open Monitoring Distribution Version 1.2.3p4\n"


def test_main_version_root_not_existing_site(version_info) -> None:
    with pytest.raises(SystemExit, match="No such site: testsite"):
        omdlib.main.main_version(
            version_info,
            omdlib.main.RootContext(),
            omdlib.main.default_global_options(),
            ["testsite"],
            {},
        )


def test_main_version_root_specific_site_broken_version(tmp_path, version_info) -> None:
    tmp_path.joinpath("omd/sites/testsite").mkdir(parents=True)
    with pytest.raises(SystemExit, match="Failed to determine site version"):
        omdlib.main.main_version(
            version_info,
            omdlib.main.RootContext(),
            omdlib.main.default_global_options(),
            ["testsite"],
            {},
        )


def test_main_version_root_specific_site(tmp_path, capsys, monkeypatch, version_info) -> None:
    tmp_path.joinpath("omd/sites/testsite").mkdir(parents=True)
    tmp_path.joinpath("omd/sites/testsite/version").symlink_to("../../versions/1.2.3p4")
    tmp_path.joinpath("omd/versions/1.2.3p4").mkdir(parents=True)
    omdlib.main.main_version(
        version_info,
        omdlib.main.RootContext(),
        omdlib.main.default_global_options(),
        ["testsite"],
        {},
    )

    stdout = capsys.readouterr()[0]
    assert stdout == "OMD - Open Monitoring Distribution Version 1.2.3p4\n"


def test_main_version_root_specific_site_bare(tmp_path, capsys, monkeypatch, version_info) -> None:
    tmp_path.joinpath("omd/sites/testsite").mkdir(parents=True)
    tmp_path.joinpath("omd/sites/testsite/version").symlink_to("../../versions/1.2.3p4")
    tmp_path.joinpath("omd/versions/1.2.3p4").mkdir(parents=True)
    omdlib.main.main_version(
        version_info,
        omdlib.main.RootContext(),
        omdlib.main.default_global_options(),
        ["testsite"],
        {"bare": None},
    )

    stdout = capsys.readouterr()[0]
    assert stdout == "1.2.3p4\n"


def test_main_versions(tmp_path, capsys, monkeypatch, version_info) -> None:
    tmp_path.joinpath("omd/versions/1.2.3p4").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/1.6.0p4").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/1.6.0p14").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/default").symlink_to("1.6.0p4")
    omdlib.main.main_versions(
        version_info, omdlib.main.RootContext(), omdlib.main.default_global_options(), [], {}
    )

    stdout = capsys.readouterr()[0]
    assert stdout == "1.2.3p4\n1.6.0p14\n1.6.0p4 (default)\n"


def test_main_versions_bare(tmp_path, capsys, monkeypatch, version_info) -> None:
    tmp_path.joinpath("omd/versions/1.2.3p4").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/1.6.0p4").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/1.6.0p14").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/default").symlink_to("1.6.0p4")
    omdlib.main.main_versions(
        version_info,
        omdlib.main.RootContext(),
        omdlib.main.default_global_options(),
        [],
        {"bare": None},
    )

    stdout = capsys.readouterr()[0]
    assert stdout == "1.2.3p4\n1.6.0p14\n1.6.0p4\n"


def test_default_version(tmp_path) -> None:
    tmp_path.joinpath("omd/versions").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/default").symlink_to("2019.12.11.cee")
    assert omdlib.main.default_version() == "2019.12.11.cee"
    assert isinstance(omdlib.main.default_version(), str)


def test_omd_versions(tmp_path) -> None:
    tmp_path.joinpath("omd/versions").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/2019.12.11.cee").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/1.6.0p7").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/1.6.0i1").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/1.6.0i10").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/1.2.0p23").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/default").symlink_to("2019.12.11.cee")

    assert omdlib.main.omd_versions() == [
        "1.2.0p23",
        "1.6.0i1",
        "1.6.0i10",
        "1.6.0p7",
        "2019.12.11.cee",
    ]


def test_version_exists(tmp_path) -> None:
    tmp_path.joinpath("omd/versions/1.6.0p7").mkdir(parents=True)
    assert omdlib.main.version_exists("1.6.0p7") is True
    assert omdlib.main.version_exists("1.6.0p6") is False


def test_main_sites(tmp_path, capsys, monkeypatch, version_info) -> None:
    tmp_path.joinpath("omd/versions/1.2.3p4").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/1.6.0p4").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/1.6.0p14").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/default").symlink_to("1.6.0p4")

    # Empty site directory
    tmp_path.joinpath("omd/sites/empty").mkdir(parents=True)
    tmp_path.joinpath("omd/apache").mkdir(parents=True)
    tmp_path.joinpath("omd/apache/empty.conf").open("w").close()

    # Site with version
    tmp_path.joinpath("omd/sites/xyz").mkdir(parents=True)
    tmp_path.joinpath("omd/sites/xyz/version").symlink_to("../../versions/1.2.3p4")
    tmp_path.joinpath("omd/apache/xyz.conf").open("w").close()

    # Site with not existing version
    tmp_path.joinpath("omd/sites/broken").mkdir(parents=True)
    tmp_path.joinpath("omd/sites/broken/version").symlink_to("../../versions/1.0.0")
    tmp_path.joinpath("omd/apache/broken.conf").open("w").close()

    # Site with default version
    tmp_path.joinpath("omd/sites/default").mkdir(parents=True)
    tmp_path.joinpath("omd/sites/default/version").symlink_to("../../versions/1.6.0p4")
    tmp_path.joinpath("omd/apache/default.conf").open("w").close()

    # Disabled site
    tmp_path.joinpath("omd/sites/disabled").mkdir(parents=True)
    tmp_path.joinpath("omd/sites/disabled/version").symlink_to("../../versions/1.6.0p4")

    omdlib.main.main_sites(
        version_info, omdlib.main.RootContext(), omdlib.main.default_global_options(), [], {}
    )

    stdout = _strip_ansi(capsys.readouterr()[0])
    assert (
        stdout == "broken           1.0.0             \n"
        "default          1.6.0p4          default version \n"
        "disabled         1.6.0p4          default version, disabled \n"
        "empty            (none)           empty site dir \n"
        "xyz              1.2.3p4           \n"
    )


def test_sitename_must_be_valid_ok(tmp_path) -> None:
    tmp_path.joinpath("omd/sites/lala").mkdir(parents=True)
    assert omdlib.main.sitename_must_be_valid(omdlib.main.SiteContext("lulu")) is None


@pytest.mark.parametrize(
    "name,expected_result",
    [
        ("0asd", False),
        ("asd0", True),
        ("", False),
        ("aaaaaaaaaaaaaaaa", True),
        ("aaaaaaaaaaaaaaaaa", False),
    ],
)
def test_sitename_must_be_valid_regex(tmp_path, name, expected_result) -> None:
    tmp_path.joinpath("omd/sites/lala").mkdir(parents=True)

    if expected_result:
        assert omdlib.main.sitename_must_be_valid(omdlib.main.SiteContext(name)) is None
    else:
        with pytest.raises(SystemExit, match="Invalid site name"):
            omdlib.main.sitename_must_be_valid(omdlib.main.SiteContext(name))


def test_sitename_must_be_valid_already_exists(tmp_path) -> None:
    tmp_path.joinpath("omd/sites/lala").mkdir(parents=True)

    with pytest.raises(SystemExit, match="already existing"):
        omdlib.main.sitename_must_be_valid(omdlib.main.SiteContext("lala"))


def test_get_orig_working_directory(tmp_path) -> None:
    orig_wd = os.getcwd()
    try:
        base_path = tmp_path.joinpath("lala")
        base_path.mkdir(parents=True)
        os.chdir(str(base_path))
        assert omdlib.main._get_orig_working_directory() == str(base_path)
    finally:
        os.chdir(orig_wd)


def test_get_orig_working_directory_not_existing(tmp_path) -> None:
    orig_wd = os.getcwd()
    try:
        test_dir = tmp_path.joinpath("lala")
        test_dir.mkdir()

        os.chdir(str(test_dir))
        assert os.getcwd() == str(test_dir)

        test_dir.rmdir()
        assert not test_dir.exists()

        assert omdlib.main._get_orig_working_directory() == "/"
    finally:
        os.chdir(orig_wd)


@pytest.mark.parametrize("edition", list(version.Edition))
def test_get_edition(edition: version._EditionValue) -> None:
    assert omdlib.main._get_edition(f"1.2.3.{edition.short}") != "unknown"
