#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
import shutil
import tarfile
import ast
import json
from io import BytesIO

if sys.version_info[0] >= 3:
    from pathlib import Path  # noqa: F401 # pylint: disable=import-error,unused-import
else:
    from pathlib2 import Path  # noqa: F401 # pylint: disable=import-error,unused-import

import pytest  # type: ignore[import]
import six

from cmk.utils.i18n import _
import cmk.utils.paths
import cmk.utils.packaging as packaging


def _read_package_info(pacname):
    # type: (packaging.PackageName) -> packaging.PackageInfo
    package_info = packaging.read_package_info(pacname)
    assert package_info is not None
    return package_info


@pytest.fixture(autouse=True)
def package_dir():
    packaging.package_dir().mkdir(parents=True, exist_ok=True)
    yield
    shutil.rmtree(str(packaging.package_dir()))


@pytest.fixture(autouse=True)
def clean_dirs():
    for part in packaging.get_package_parts():
        Path(part.path).mkdir(parents=True, exist_ok=True)

    yield

    for part in packaging.get_package_parts():
        shutil.rmtree(part.path)


def test_package_parts():
    assert sorted(packaging.get_package_parts()) == sorted([
        packaging.PackagePart("agent_based", _("Agent based plugins (Checks, Inventory)"),
                              str(cmk.utils.paths.local_agent_based_plugins_dir)),
        packaging.PackagePart('checks', _('Legacy check plugins'),
                              str(cmk.utils.paths.local_checks_dir)),
        packaging.PackagePart('notifications', _('Notification scripts'),
                              str(cmk.utils.paths.local_notifications_dir)),
        packaging.PackagePart('inventory', _('Legacy inventory plugins'),
                              str(cmk.utils.paths.local_inventory_dir)),
        packaging.PackagePart('checkman', _("Checks' man pages"),
                              str(cmk.utils.paths.local_check_manpages_dir)),
        packaging.PackagePart('agents', _('Agents'), str(cmk.utils.paths.local_agents_dir)),
        packaging.PackagePart('web', _('GUI extensions'), str(cmk.utils.paths.local_web_dir)),
        packaging.PackagePart('pnp-templates', _('PNP4Nagios templates'),
                              str(cmk.utils.paths.local_pnp_templates_dir)),
        packaging.PackagePart('doc', _('Documentation files'), str(cmk.utils.paths.local_doc_dir)),
        packaging.PackagePart('locales', _('Localizations'), str(cmk.utils.paths.local_locale_dir)),
        packaging.PackagePart('bin', _('Binaries'), str(cmk.utils.paths.local_bin_dir)),
        packaging.PackagePart('lib', _('Libraries'), str(cmk.utils.paths.local_lib_dir)),
        packaging.PackagePart('mibs', _('SNMP MIBs'), str(cmk.utils.paths.local_mib_dir)),
        packaging.PackagePart('alert_handlers', _('Alert handlers'),
                              str(cmk.utils.paths.local_share_dir.joinpath('alert_handlers'))),
    ])


def test_config_parts():
    assert packaging.get_config_parts() == [
        packaging.PackagePart("ec_rule_packs", "Event Console rule packs",
                              "%s/mkeventd.d/mkp/rule_packs" % cmk.utils.paths.default_config_dir)
    ]


def test_get_permissions_unknown_path():
    with pytest.raises(packaging.PackageException):
        assert packaging._get_permissions("lala")


@pytest.mark.parametrize("path,expected", [
    (str(cmk.utils.paths.local_checks_dir), 0o644),
    (str(cmk.utils.paths.local_bin_dir), 0o755),
])
def test_get_permissions(path, expected):
    assert packaging._get_permissions(path) == expected


def test_package_dir():
    assert isinstance(packaging.package_dir(), Path)


def test_get_config_parts():
    assert [p.ident for p in packaging.get_config_parts()] == ["ec_rule_packs"]


def test_get_package_parts():
    assert sorted([p.ident for p in packaging.get_package_parts()]) == sorted([
        'agent_based',
        'agents',
        'alert_handlers',
        'bin',
        'checkman',
        'checks',
        'doc',
        'inventory',
        'lib',
        'locales',
        'mibs',
        'notifications',
        'pnp-templates',
        'web',
    ])


def _create_simple_test_package(pacname):
    _create_test_file(pacname)
    package_info = packaging.get_initial_package_info(pacname)

    package_info["files"] = {
        "checks": [pacname],
    }

    packaging.create_package(package_info)
    return packaging.read_package_info("aaa")


def _create_test_file(name):
    check_path = cmk.utils.paths.local_checks_dir.joinpath(name)
    with check_path.open("w", encoding="utf-8") as f:
        f.write(u"lala\n")


def test_create_package():
    assert packaging.all_package_names() == []
    _create_simple_test_package("aaa")
    assert packaging.all_package_names() == ["aaa"]


def test_create_package_twice():
    _create_simple_test_package("aaa")

    with pytest.raises(packaging.PackageException):
        _create_simple_test_package("aaa")


def test_read_package_info():
    _create_simple_test_package("aaa")
    assert _read_package_info("aaa")["version"] == "1.0"


def test_read_package_info_not_existing():
    assert packaging.read_package_info("aaa") is None


def test_edit_package_not_existing():
    new_package_info = packaging.get_initial_package_info("aaa")
    new_package_info["version"] = "2.0"

    with pytest.raises(packaging.PackageException):
        packaging.edit_package("aaa", new_package_info)


def test_edit_package():
    new_package_info = packaging.get_initial_package_info("aaa")
    new_package_info["version"] = "2.0"

    package_info = _create_simple_test_package("aaa")
    assert package_info["version"] == "1.0"

    packaging.edit_package("aaa", new_package_info)

    assert _read_package_info("aaa")["version"] == "2.0"


def test_edit_package_rename():
    new_package_info = packaging.get_initial_package_info("bbb")

    _create_simple_test_package("aaa")

    packaging.edit_package("aaa", new_package_info)

    assert _read_package_info("bbb")["name"] == "bbb"
    assert packaging.read_package_info("aaa") is None


def test_edit_package_rename_conflict():
    new_package_info = packaging.get_initial_package_info("bbb")
    _create_simple_test_package("aaa")
    _create_simple_test_package("bbb")

    with pytest.raises(packaging.PackageException):
        packaging.edit_package("aaa", new_package_info)


def test_install_package():
    # Create
    _create_simple_test_package("aaa")
    package_info = _read_package_info("aaa")

    # Build MKP in memory
    mkp = BytesIO()
    packaging.create_mkp_file(package_info, mkp)
    mkp.seek(0)

    # Remove files from local hierarchy
    packaging.remove_package(package_info)
    assert packaging._package_exists("aaa") is False

    # And now install the package from memory
    packaging.install_package(mkp)

    # Check result
    assert packaging._package_exists("aaa") is True
    package_info = _read_package_info("aaa")
    assert package_info["version"] == "1.0"
    assert package_info["files"]["checks"] == ["aaa"]
    assert cmk.utils.paths.local_checks_dir.joinpath("aaa").exists()


def test_install_package_by_path(tmp_path):
    # Create
    _create_simple_test_package("aaa")
    package_info = _read_package_info("aaa")

    # Write MKP file
    mkp_path = tmp_path.joinpath("aaa.mkp")
    with mkp_path.open("wb") as mkp:
        packaging.create_mkp_file(package_info, mkp)

    # Remove files from local hierarchy
    packaging.remove_package(package_info)
    assert packaging._package_exists("aaa") is False

    # And now install the package from memory
    packaging.install_package_by_path(mkp_path)

    # Check result
    assert packaging._package_exists("aaa") is True
    package_info = _read_package_info("aaa")
    assert package_info["version"] == "1.0"
    assert package_info["files"]["checks"] == ["aaa"]
    assert cmk.utils.paths.local_checks_dir.joinpath("aaa").exists()


def test_release_package_not_existing():
    with pytest.raises(packaging.PackageException):
        packaging.release_package("abc")


def test_release_package():
    _create_simple_test_package("aaa")
    assert packaging._package_exists("aaa") is True
    assert cmk.utils.paths.local_checks_dir.joinpath("aaa").exists()

    packaging.release_package("aaa")

    assert packaging._package_exists("aaa") is False
    assert cmk.utils.paths.local_checks_dir.joinpath("aaa").exists()


def test_create_mkp_file():
    package_info = _create_simple_test_package("aaa")

    mkp = BytesIO()
    packaging.create_mkp_file(package_info, mkp)
    mkp.seek(0)

    tar = tarfile.open(fileobj=mkp, mode="r:gz")
    assert sorted(tar.getnames()) == sorted(["info", "info.json", "checks.tar"])

    info_file = tar.extractfile("info")
    assert info_file is not None
    info = ast.literal_eval(six.ensure_str(info_file.read()))
    assert info["name"] == "aaa"

    info_json_file = tar.extractfile("info.json")
    assert info_json_file is not None
    info2 = json.loads(info_json_file.read())
    assert info2["name"] == "aaa"


def test_remove_package():
    package_info = _create_simple_test_package("aaa")
    packaging.remove_package(package_info)
    assert packaging._package_exists("aaa") is False


def test_unpackaged_files_none():
    assert packaging.unpackaged_files() == {
        'agent_based': [],
        'agents': [],
        'alert_handlers': [],
        'bin': [],
        'checkman': [],
        'checks': [],
        'doc': [],
        'ec_rule_packs': [],
        'inventory': [],
        'lib': [],
        'locales': [],
        'mibs': [],
        'notifications': [],
        'pnp-templates': [],
        'web': [],
    }


def test_unpackaged_files():
    _create_test_file("abc")

    p = cmk.utils.paths.local_doc_dir.joinpath("docxx")
    with p.open("w", encoding="utf-8") as f:
        f.write(u"lala\n")

    p = cmk.utils.paths.local_agent_based_plugins_dir.joinpath("dada")
    with p.open("w", encoding="utf-8") as f:
        f.write(u"huhu\n")

    assert packaging.unpackaged_files() == {
        'agent_based': ['dada'],
        'agents': [],
        'alert_handlers': [],
        'bin': [],
        'checkman': [],
        'checks': ['abc'],
        'doc': ["docxx"],
        'ec_rule_packs': [],
        'inventory': [],
        'lib': [],
        'locales': [],
        'mibs': [],
        'notifications': [],
        'pnp-templates': [],
        'web': [],
    }


# TODO:
#def test_get_all_package_infos()
#def test_package_part_info()


def test_get_optional_package_infos_none():
    assert packaging.get_optional_package_infos() == {}


def test_get_optional_package_infos(monkeypatch, tmp_path):
    mkp_dir = tmp_path.joinpath("optional_packages")
    mkp_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cmk.utils.paths, "optional_packages_dir", mkp_dir)

    # Create package
    _create_simple_test_package("optional")
    package_info = _read_package_info("optional")

    # Write MKP file
    mkp_path = mkp_dir.joinpath("optional.mkp")
    with mkp_path.open("wb") as mkp:
        packaging.create_mkp_file(package_info, mkp)

    assert packaging.get_optional_package_infos() == {"optional.mkp": package_info}


def test_parse_package_info_pre_160():
    assert packaging.parse_package_info(repr({"name": "aaa"}))["version.usable_until"] is None


def test_parse_package_info():
    info_str = repr(packaging.get_initial_package_info("pkgname"))
    assert packaging.parse_package_info(info_str)["name"] == "pkgname"
