#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
from omdlib.contexts import SiteContext
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


def test_hostname() -> None:
    assert omdlib.main.hostname() == os.popen("hostname").read().strip()


def test_main_help(
    site_context: SiteContext, capsys: pytest.CaptureFixture[str], version_info: VersionInfo
) -> None:
    omdlib.main.main_help(version_info, site_context)
    stdout = capsys.readouterr()[0]
    assert "omd COMMAND -h" in stdout


def test_main_version_of_current_site(
    site_context: SiteContext,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    version_info: VersionInfo,
) -> None:
    monkeypatch.setattr(omdlib, "__version__", "1.2.3p4")
    global_opts = omdlib.main.default_global_options()
    args: omdlib.main.Arguments = []
    options: CommandOptions = {}
    omdlib.main.main_version(version_info, site_context, global_opts, args, options)

    stdout = capsys.readouterr()[0]
    assert stdout == "OMD - Open Monitoring Distribution Version 1.2.3p4\n"


def test_main_version_root(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, version_info: VersionInfo
) -> None:
    monkeypatch.setattr(omdlib, "__version__", "1.2.3p4")
    global_opts = omdlib.main.default_global_options()
    args: omdlib.main.Arguments = []
    options: CommandOptions = {}
    omdlib.main.main_version(version_info, omdlib.main.RootContext(), global_opts, args, options)

    stdout = capsys.readouterr()[0]
    assert stdout == "OMD - Open Monitoring Distribution Version 1.2.3p4\n"


def test_main_version_root_not_existing_site(version_info: VersionInfo) -> None:
    with pytest.raises(SystemExit, match="No such site: testsite"):
        omdlib.main.main_version(
            version_info,
            omdlib.main.RootContext(),
            omdlib.main.default_global_options(),
            ["testsite"],
            {},
        )


def test_main_version_root_specific_site_broken_version(
    tmp_path: Path, version_info: VersionInfo
) -> None:
    tmp_path.joinpath("omd/sites/testsite").mkdir(parents=True)
    with pytest.raises(SystemExit, match="Failed to determine site version"):
        omdlib.main.main_version(
            version_info,
            omdlib.main.RootContext(),
            omdlib.main.default_global_options(),
            ["testsite"],
            {},
        )


def test_main_version_root_specific_site(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    version_info: VersionInfo,
) -> None:
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


def test_main_version_root_specific_site_bare(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    version_info: VersionInfo,
) -> None:
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


def test_main_versions(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    version_info: VersionInfo,
) -> None:
    tmp_path.joinpath("omd/versions/1.2.3p4").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/1.6.0p4").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/1.6.0p14").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/default").symlink_to("1.6.0p4")
    omdlib.main.main_versions(
        version_info, omdlib.main.RootContext(), omdlib.main.default_global_options(), [], {}
    )

    stdout = capsys.readouterr()[0]
    assert stdout == "1.2.3p4\n1.6.0p14\n1.6.0p4 (default)\n"


def test_main_versions_bare(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    version_info: VersionInfo,
) -> None:
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


def test_default_version(tmp_path: Path) -> None:
    tmp_path.joinpath("omd/versions").mkdir(parents=True)
    tmp_path.joinpath("omd/versions/default").symlink_to("2019.12.11.cee")
    assert omdlib.main.default_version() == "2019.12.11.cee"
    assert isinstance(omdlib.main.default_version(), str)


def test_omd_versions(tmp_path: Path) -> None:
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


def test_version_exists(tmp_path: Path) -> None:
    tmp_path.joinpath("omd/versions/1.6.0p7").mkdir(parents=True)
    assert omdlib.main.version_exists("1.6.0p7") is True
    assert omdlib.main.version_exists("1.6.0p6") is False


def test_main_sites(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    version_info: VersionInfo,
) -> None:
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


def test_sitename_must_be_valid_ok(tmp_path: Path) -> None:
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
def test_sitename_must_be_valid_regex(tmp_path: Path, name: str, expected_result: bool) -> None:
    tmp_path.joinpath("omd/sites/lala").mkdir(parents=True)

    if expected_result:
        assert omdlib.main.sitename_must_be_valid(omdlib.main.SiteContext(name)) is None
    else:
        with pytest.raises(SystemExit, match="Invalid site name"):
            omdlib.main.sitename_must_be_valid(omdlib.main.SiteContext(name))


def test_sitename_must_be_valid_already_exists(tmp_path: Path) -> None:
    tmp_path.joinpath("omd/sites/lala").mkdir(parents=True)

    with pytest.raises(SystemExit, match="already existing"):
        omdlib.main.sitename_must_be_valid(omdlib.main.SiteContext("lala"))


def test_get_orig_working_directory(tmp_path: Path) -> None:
    orig_wd = os.getcwd()
    try:
        base_path = tmp_path.joinpath("lala")
        base_path.mkdir(parents=True)
        os.chdir(str(base_path))
        assert omdlib.main._get_orig_working_directory() == str(base_path)
    finally:
        os.chdir(orig_wd)


def test_get_orig_working_directory_not_existing(tmp_path: Path) -> None:
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


def test_permission_action_new_link_triggers_no_action() -> None:
    assert (
        omdlib.main.permission_action(
            site=omdlib.main.SiteContext("bye"),
            conflict_mode="ask",
            relpath="my/file",
            old_type="link",
            new_type="link",
            user_type="link",
            old_perm=123,
            new_perm=125,
            user_perm=124,
        )
        is None
    )
    assert (
        omdlib.main.permission_action(
            site=omdlib.main.SiteContext("bye"),
            conflict_mode="ask",
            relpath="my/file",
            old_type="file",
            new_type="link",
            user_type="file",
            old_perm=123,
            new_perm=125,
            user_perm=124,
        )
        is None
    )
    assert (
        omdlib.main.permission_action(
            site=omdlib.main.SiteContext("bye"),
            conflict_mode="ask",
            relpath="my/file",
            old_type="link",
            new_type="file",
            user_type="link",
            old_perm=123,
            new_perm=125,
            user_perm=124,
        )
        is None
    )


def test_permission_action_changed_type_triggers_no_action() -> None:
    assert (
        omdlib.main.permission_action(
            site=omdlib.main.SiteContext("bye"),
            conflict_mode="ask",
            relpath="my/file",
            old_type="dir",
            new_type="file",
            user_type="dir",
            old_perm=123,
            new_perm=125,
            user_perm=124,
        )
        is None
    )
    assert (
        omdlib.main.permission_action(
            site=omdlib.main.SiteContext("bye"),
            conflict_mode="ask",
            relpath="my/file",
            old_type="file",
            new_type="dir",
            user_type="file",
            old_perm=123,
            new_perm=125,
            user_perm=124,
        )
        is None
    )


def test_permission_action_same_target_permission_triggers_no_action() -> None:
    assert (
        omdlib.main.permission_action(
            site=omdlib.main.SiteContext("bye"),
            conflict_mode="ask",
            relpath="my/file",
            old_type="file",
            new_type="file",
            user_type="file",
            old_perm=123,
            new_perm=125,
            user_perm=125,
        )
        is None
    )
    assert (
        omdlib.main.permission_action(
            site=omdlib.main.SiteContext("bye"),
            conflict_mode="ask",
            relpath="my/file",
            old_type="dir",
            new_type="dir",
            user_type="dir",
            old_perm=123,
            new_perm=125,
            user_perm=125,
        )
        is None
    )


def test_permission_action_user_and_new_changed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(omdlib.main, "user_confirms", lambda *a: True)
    assert (
        omdlib.main.permission_action(
            site=omdlib.main.SiteContext("bye"),
            conflict_mode="ask",
            relpath="my/file",
            old_type="file",
            new_type="file",
            user_type="file",
            old_perm=123,
            new_perm=124,
            user_perm=125,
        )
        == "keep"
    )


def test_permission_action_user_and_new_changed_set_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(omdlib.main, "user_confirms", lambda *a: False)
    assert (
        omdlib.main.permission_action(
            site=omdlib.main.SiteContext("bye"),
            conflict_mode="ask",
            relpath="my/file",
            old_type="file",
            new_type="file",
            user_type="file",
            old_perm=123,
            new_perm=124,
            user_perm=125,
        )
        == "default"
    )


def test_permission_action_new_changed_set_default() -> None:
    assert (
        omdlib.main.permission_action(
            site=omdlib.main.SiteContext("bye"),
            conflict_mode="ask",
            relpath="my/file",
            old_type="file",
            new_type="file",
            user_type="file",
            old_perm=123,
            new_perm=124,
            user_perm=123,
        )
        == "default"
    )


def test_permission_action_user_changed_no_action() -> None:
    assert (
        omdlib.main.permission_action(
            site=omdlib.main.SiteContext("bye"),
            conflict_mode="ask",
            relpath="my/file",
            old_type="file",
            new_type="file",
            user_type="file",
            old_perm=123,
            new_perm=123,
            user_perm=124,
        )
        is None
    )


def test_permission_action_old_and_new_changed_set_to_new() -> None:
    assert (
        omdlib.main.permission_action(
            site=omdlib.main.SiteContext("bye"),
            conflict_mode="ask",
            relpath="my/file",
            old_type="file",
            new_type="file",
            user_type="file",
            old_perm=123,
            new_perm=124,
            user_perm=123,
        )
        == "default"
    )


def test_permission_action_all_changed_incl_type_ask(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(omdlib.main, "user_confirms", lambda *a: True)
    assert (
        omdlib.main.permission_action(
            site=omdlib.main.SiteContext("bye"),
            conflict_mode="ask",
            relpath="my/file",
            old_type="file",
            new_type="dir",
            user_type="dir",
            old_perm=123,
            new_perm=124,
            user_perm=125,
        )
        == "keep"
    )


def test_permission_action_all_changed_incl_type_ask_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(omdlib.main, "user_confirms", lambda *a: False)
    assert (
        omdlib.main.permission_action(
            site=omdlib.main.SiteContext("bye"),
            conflict_mode="ask",
            relpath="my/file",
            old_type="file",
            new_type="dir",
            user_type="dir",
            old_perm=123,
            new_perm=124,
            user_perm=125,
        )
        == "default"
    )


# In 2.2 we removed world permissions from all the skel files. Some sites
# had permissions that were different from previous defaults, resulting in
# repeated questions to users which they should not be asked. See CMK-12090.
@pytest.mark.parametrize(
    "relpath",
    [
        "local/share/nagvis/htdocs/userfiles/images/maps",
        "local/share/nagvis/htdocs/userfiles/images/shapes",
        "etc/check_mk/multisite.d",
        "etc/check_mk/conf.d",
        "etc/check_mk/conf.d/wato",
        "etc/ssl/private",
        "etc/ssl/certs",
    ],
)
def test_permission_action_all_changed_streamline_standard_directories(relpath: str) -> None:
    assert (
        omdlib.main.permission_action(
            site=omdlib.main.SiteContext("bye"),
            conflict_mode="ask",
            relpath=relpath,
            old_type="dir",
            new_type="dir",
            user_type="dir",
            old_perm=int(0o775),
            new_perm=int(0o770),
            user_perm=int(0o750),
        )
        == "default"
    )
