#!/usr/bin/env python

import shutil
import tarfile
import ast
import json
from io import BytesIO
import pytest  # type: ignore
from pathlib2 import Path

import cmk.utils.paths
import cmk.utils.packaging as packaging


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

    package_info = _create_simple_test_package("aaa")
    assert package_info["version"] == "1.0"

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


def test_install_package():
    # Create
    _create_simple_test_package("aaa")
    package_info = packaging.read_package_info("aaa")

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
    package_info = packaging.read_package_info("aaa")
    assert package_info["version"] == "1.0"
    assert package_info["files"]["checks"] == ["aaa"]
    assert cmk.utils.paths.local_checks_dir.joinpath("aaa").exists()


def test_install_package_by_path(tmp_path):
    # Create
    _create_simple_test_package("aaa")
    package_info = packaging.read_package_info("aaa")

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
    package_info = packaging.read_package_info("aaa")
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

    info = ast.literal_eval(tar.extractfile("info").read())
    assert info["name"] == "aaa"

    info2 = json.loads(tar.extractfile("info.json").read())
    assert info2["name"] == "aaa"


def test_remove_package():
    package_info = _create_simple_test_package("aaa")
    packaging.remove_package(package_info)
    assert packaging._package_exists("aaa") is False


def test_unpackaged_files_none():
    assert packaging.unpackaged_files() == {
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

    assert packaging.unpackaged_files() == {
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
    package_info = packaging.read_package_info("optional")

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
