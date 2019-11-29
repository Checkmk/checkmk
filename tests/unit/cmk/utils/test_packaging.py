#!/usr/bin/env python

import pytest  # type: ignore
import shutil
from pathlib2 import Path

import cmk.utils.paths
import cmk.utils.packaging as packaging


@pytest.fixture(autouse=True)
def package_dir():
    packaging.package_dir().mkdir(parents=True, exist_ok=True)
    yield
    shutil.rmtree(str(packaging.package_dir()))


def test_package_parts():
    assert packaging.get_package_parts() == [
        packaging.PackagePart('checks', 'Checks', 'local/share/check_mk/checks'),
        packaging.PackagePart('notifications', 'Notification scripts',
                              'local/share/check_mk/notifications'),
        packaging.PackagePart('inventory', 'Inventory plugins', 'local/share/check_mk/inventory'),
        packaging.PackagePart('checkman', "Checks' man pages", 'local/share/check_mk/checkman'),
        packaging.PackagePart('agents', 'Agents', 'local/share/check_mk/agents'),
        packaging.PackagePart('web', 'Multisite extensions', 'local/share/check_mk/web'),
        packaging.PackagePart('pnp-templates', 'PNP4Nagios templates',
                              'local/share/check_mk/pnp-templates'),
        packaging.PackagePart('doc', 'Documentation files', 'local/share/doc/check_mk'),
        packaging.PackagePart('locales', 'Localizations', 'local/share/check_mk/locale'),
        packaging.PackagePart('bin', 'Binaries', 'local/bin'),
        packaging.PackagePart('lib', 'Libraries', 'local/lib'),
        packaging.PackagePart('mibs', 'SNMP MIBs', 'local/share/snmp/mibs'),
        packaging.PackagePart('alert_handlers', 'Alert handlers',
                              'local/share/check_mk/alert_handlers'),
    ]


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
    cmk.utils.paths.local_checks_dir.mkdir(parents=True, exist_ok=True)
    with cmk.utils.paths.local_checks_dir.joinpath(pacname).open("w", encoding="utf-8") as f:
        f.write(u"lala\n")

    package_info = packaging.get_initial_package_info(pacname)
    packaging.create_package(package_info)


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
    assert packaging.read_package_info("aaa")["version"] == "1.0"


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

    _create_simple_test_package("aaa")
    assert packaging.read_package_info("aaa")["version"] == "1.0"

    packaging.edit_package("aaa", new_package_info)

    assert packaging.read_package_info("aaa")["version"] == "2.0"


def test_edit_package_rename():
    new_package_info = packaging.get_initial_package_info("bbb")

    _create_simple_test_package("aaa")

    packaging.edit_package("aaa", new_package_info)

    assert packaging.read_package_info("bbb")["name"] == "bbb"
    assert packaging.read_package_info("aaa") is None


def test_edit_package_rename_conflict():
    new_package_info = packaging.get_initial_package_info("bbb")
    _create_simple_test_package("aaa")
    _create_simple_test_package("bbb")

    with pytest.raises(packaging.PackageException):
        packaging.edit_package("aaa", new_package_info)


# TODO
#def test_install_package_by_path()
#def test_install_package()
#def test_release_package():
#def test_create_mkp_file():
#def test_remove_package()
#def test_get_all_package_infos()
#def test_unpackaged_files()
#def test_package_part_info()
#def test_unpackaged_files_in_dir()
#def test_packaged_files_in_dir()
#def test_all_package_names()
#def test_write_package_info()


def test_parse_package_info_pre_160():
    assert packaging.parse_package_info(repr({"name": "aaa"}))["version.usable_until"] is None


def test_parse_package_info():
    info_str = repr(packaging.get_initial_package_info("pkgname"))
    assert packaging.parse_package_info(info_str)["name"] == "pkgname"
