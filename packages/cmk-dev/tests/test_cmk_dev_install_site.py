# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse

import pytest
from cmk_dev_site import cmk_dev_install as cmk_dev_install_module
from cmk_dev_site import cmk_dev_install_site
from cmk_dev_site import cmk_dev_site as cmk_dev_site_module
from cmk_dev_site.cmk_dev_install import ExitCode, InstallResult
from cmk_dev_site.cmk_dev_install_site import core, install_args, site_args
from cmk_dev_site.omd import Edition
from cmk_dev_site.utils.cli import resolve_argv


def test_install_args_forwards_version_and_edition() -> None:
    assert list(install_args("2.3", Edition.OLD_ENTERPRISE, "-v")) == [
        "2.3",
        "--edition",
        "cee",
        "-v",
    ]


def test_site_args_with_resolved_version() -> None:
    assert list(site_args("2.3.0-2026.07.10.cee", None, 0, "", None)) == [
        "2.3.0-2026.07.10.cee",
        "-f",
    ]


def test_site_args_appends_edition_suffix() -> None:
    assert list(site_args("3.0.0-2026-06-29", Edition.ULTIMATE, 0, "", None)) == [
        "3.0.0-2026-06-29.ultimate",
        "-f",
    ]


def test_site_args_without_version() -> None:
    assert list(site_args(None, None, 2, "-v", "mysite")) == [
        "--distributed",
        "2",
        "--name",
        "mysite",
        "-f",
        "-v",
    ]


def test_core_forwards_resolved_version_to_site(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The site step must use the version resolved by cmk-dev-install
    (e.g. "2.3" -> "2.3.0-2026.07.10.cee"), not the raw user input."""
    seen: dict[str, list[str]] = {}

    def fake_install(args: list[str]) -> InstallResult:
        seen["install"] = args
        return InstallResult(ExitCode.SUCCESS, "2.3.0-2026.07.10.cee")

    def fake_site(args: list[str]) -> int:
        seen["site"] = args
        return 0

    monkeypatch.setattr(cmk_dev_install_site, "cmk_dev_install", fake_install)
    monkeypatch.setattr(cmk_dev_install_site, "cmk_dev_site", fake_site)

    result = core(
        "2.3",
        None,
        site_distributed=0,
        site_name=None,
        dryrun=False,
        verbose=0,
        quiet=0,
    )

    assert result == 0
    assert seen["install"] == ["2.3"]
    assert seen["site"] == ["2.3.0-2026.07.10.cee", "-f"]
    assert "cmk-dev-site 2.3.0-2026.07.10.cee -f" in capsys.readouterr().out


def test_core_dryrun_does_not_execute(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail(_args: list[str]) -> int:
        raise AssertionError("must not be called in dryrun")

    monkeypatch.setattr(cmk_dev_install_site, "cmk_dev_install", fail)
    monkeypatch.setattr(cmk_dev_install_site, "cmk_dev_site", fail)

    result = core(
        "2.3",
        None,
        site_distributed=0,
        site_name=None,
        dryrun=True,
        verbose=0,
        quiet=0,
    )

    assert result == 0
    out = capsys.readouterr().out
    assert "cmk-dev-install 2.3" in out
    # the site command depends on the version cmk-dev-install would resolve,
    # so it cannot be previewed without actually running the install step
    assert "cmk-dev-site" not in out


def _parse_install(argv: list[str]) -> argparse.Namespace:
    parser = cmk_dev_install_module.create_parser()
    cmk_dev_install_module.setup_parser(parser)
    return parser.parse_args(argv)


def _parse_site(argv: list[str]) -> argparse.Namespace:
    parser = cmk_dev_site_module.create_parser()
    cmk_dev_site_module.setup_parser(parser)
    return parser.parse_args(argv)


def test_argv_built_for_a_bare_site_name_parses() -> None:
    """`cmk-dev-install-site -n foo`: the site name must reach cmk-dev-site
    only, and cmk-dev-install must accept the resulting empty argv."""
    install_argv = list(install_args(None, None, ""))
    site_argv = list(site_args(None, None, 0, "", "foo"))

    assert install_argv == []
    assert _parse_install(resolve_argv(install_argv, ["-n", "foo"])).build is None

    assert site_argv == ["--name", "foo", "-f"]
    assert _parse_site(resolve_argv(site_argv, ["-n", "foo"])).name == "foo"


def test_argv_built_for_a_resolved_version_parses() -> None:
    site_argv = list(site_args("2.3.0-2026.07.10.cee", None, 2, "-v", "foo"))

    args = _parse_site(resolve_argv(site_argv, ["-n", "foo"]))
    assert str(args.version) == "2.3.0-2026.07.10.cee"
    assert args.name == "foo"
    assert args.distributed == 2
    assert args.verbose == 1
