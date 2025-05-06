#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import os
from collections.abc import Sequence
from pathlib import Path

import pytest
from cryptography.x509 import load_pem_x509_certificate
from cryptography.x509.oid import NameOID
from pytest_mock import MockerFixture

import omdlib
import omdlib.main
import omdlib.utils
from omdlib.contexts import SiteContext

from cmk.ccc import version


def test_initialize_site_ca(
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    site_id = "tested"
    ca_path = tmp_path / site_id / "etc" / "ssl"
    ca_path.mkdir(parents=True, exist_ok=True)
    ca_pem = ca_path / "ca.pem"
    site_pem = ca_path / "sites" / ("%s.pem" % site_id)

    mocker.patch(
        "omdlib.main.cert_dir",
        return_value=ca_path,
    )

    assert not site_pem.exists()
    omdlib.main.initialize_site_ca(SiteContext(site_id), site_key_size=1024, root_key_size=1024)

    assert ca_pem.exists()
    ca_cert = load_pem_x509_certificate(ca_pem.read_bytes())
    assert (
        ca_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].rfc4514_string()
        == f"CN=Site '{site_id}' local CA"
    )

    assert site_pem.exists()
    site_cert = load_pem_x509_certificate(site_pem.read_bytes())
    assert (
        site_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].rfc4514_string()
        == f"CN={site_id}"
    )


def test_hostname() -> None:
    assert omdlib.main.hostname() == os.popen("hostname").read().strip()


def test_main_help(capsys: pytest.CaptureFixture[str]) -> None:
    omdlib.main.main_help()
    stdout = capsys.readouterr()[0]
    assert "omd COMMAND -h" in stdout


@pytest.mark.parametrize("edition", list(version.Edition))
def test_get_edition(edition: version._EditionValue) -> None:
    assert omdlib.main._get_edition(f"1.2.3.{edition.short}") != "unknown"


def test_permission_action_new_link_triggers_no_action() -> None:
    assert (
        omdlib.main.permission_action(
            site_home="/tmp",
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
            site_home="/tmp",
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
            site_home="/tmp",
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
            site_home="/tmp",
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
            site_home="/tmp",
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
            site_home="/tmp",
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
            site_home="/tmp",
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
            site_home="/tmp",
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
            site_home="/tmp",
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
            site_home="/tmp",
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
            site_home="/tmp",
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
            site_home="/tmp",
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
            site_home="/tmp",
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
            site_home="/tmp",
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


def test_permission_action_directory_was_removed_in_target() -> None:
    assert (
        omdlib.main.permission_action(
            site_home="/tmp",
            conflict_mode="ask",
            relpath="etc/ssl/private",
            old_type="dir",
            new_type=None,
            user_type="dir",
            old_perm=123,
            new_perm=0,
            user_perm=123,
        )
        is None
    )


def test_permission_action_directory_was_removed_in_both() -> None:
    assert (
        omdlib.main.permission_action(
            site_home="/tmp",
            conflict_mode="ask",
            relpath="etc/ssl/private",
            old_type="dir",
            new_type=None,
            user_type=None,
            old_perm=123,
            new_perm=0,
            user_perm=123,
        )
        is None
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
            site_home="/tmp",
            conflict_mode="ask",
            relpath=relpath,
            old_type="dir",
            new_type="dir",
            user_type="dir",
            old_perm=0o775,
            new_perm=0o770,
            user_perm=0o750,
        )
        == "default"
    )


@pytest.mark.parametrize(
    "version, expected",
    [
        ("2.0.0p39.cee", ["check-mk-enterprise-2.0.0p39"]),
        ("2.1.0p45.cee", ["check-mk-enterprise-2.1.0p45"]),
        ("2.3.0.cee", ["check-mk-enterprise-2.3.0"]),
        ("2.3.0p10.cce", ["check-mk-cloud-2.3.0p10"]),
        ("2.3.0p10.cme", ["check-mk-managed-2.3.0p10"]),
        ("2.3.0-2024.07.16.cee", ["check-mk-enterprise-2.3.0-2024.07.16"]),
        ("2.4.0-2024.07.16.cee", ["check-mk-enterprise-2.4.0-2024.07.16"]),
    ],
)
def test_select_matching_packages(version: str, expected: Sequence[str]) -> None:
    installed_packages = [
        "check-mk-agent",
        "check-mk-cloud-2.3.0p10",
        "check-mk-cloud-2.3.0p8",
        "check-mk-enterprise-2.0.0p39",
        "check-mk-enterprise-2.1.0p45",
        "check-mk-enterprise-2.2.0p11",
        "check-mk-enterprise-2.2.0p23",
        "check-mk-enterprise-2.3.0",
        "check-mk-enterprise-2.3.0-2024.07.16",
        "check-mk-enterprise-2.3.0p9",
        "check-mk-enterprise-2.4.0-2024.07.16",
        "check-mk-free-2.1.0p40",
        "check-mk-free-2.1.0p41",
        "check-mk-managed-2.3.0p10",
        "check-mk-managed-2.3.0p7",
        "check-mk-raw-2.2.0p26",
        "check-mk-raw-2.3.0p7",
        "check-mk-raw-2.4.0-2024.03.18",
        "check-mk-raw-2.4.0-2024.04.16",
        "cheese",
    ]
    assert omdlib.main.select_matching_packages(version, installed_packages) == expected
