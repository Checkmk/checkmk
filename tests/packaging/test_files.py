#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import csv
import io
import json
import logging
import os
import re
import subprocess
from datetime import date
from functools import cache
from pathlib import Path, PosixPath

import pytest

LOGGER = logging.getLogger()


def _get_omd_version(cmk_version: str, package_path: str) -> str:
    # Extract the files edition
    edition_short = _edition_short_from_pkg_path(package_path)
    return f"{cmk_version}.{edition_short}"


def _edition_short_from_pkg_path(package_path: str) -> str:
    file_name = os.path.basename(package_path)
    if file_name.startswith("check-mk-raw-"):
        return "cre"
    if file_name.startswith("check-mk-enterprise-"):
        return "cee"
    if file_name.startswith("check-mk-managed-"):
        return "cme"
    if file_name.startswith("check-mk-free-"):
        return "cfe"
    if file_name.startswith("check-mk-cloud-"):
        return "cce"
    if file_name.startswith("check-mk-saas-"):
        return "cse"
    raise NotImplementedError("Could not get edition from package path: %s" % package_path)


def _file_exists_in_package(package_path: str, cmk_version: str, version_rel_path: str) -> bool:
    omd_version = _get_omd_version(cmk_version, package_path)

    file_list = _get_paths_from_package(package_path)

    if package_path.endswith(".deb") or package_path.endswith(".rpm"):
        return f"/opt/omd/versions/{omd_version}/{version_rel_path}" in file_list

    if package_path.endswith(".cma"):
        return f"{omd_version}/{version_rel_path}" in file_list

    raise NotImplementedError()


def _get_file_from_package(package_path: str, cmk_version: str, version_rel_path: str) -> bytes:
    omd_version = _get_omd_version(cmk_version, package_path)

    if package_path.endswith(".rpm"):
        rpm2cpio = subprocess.run(["rpm2cpio", package_path], stdout=subprocess.PIPE, check=False)
        return subprocess.check_output(
            [
                "cpio",
                "-i",
                "--quiet",
                "--to-stdout",
                f"./opt/omd/versions/{omd_version}/{version_rel_path}",
            ],
            input=rpm2cpio.stdout,
        )

    if package_path.endswith(".deb"):
        return subprocess.check_output(
            ["tar", "xOf", "-", f"./opt/omd/versions/{omd_version}/{version_rel_path}"],
            input=subprocess.run(
                ["dpkg", "--fsys-tarfile", package_path], stdout=subprocess.PIPE, check=False
            ).stdout,
        )

    if package_path.endswith(".cma"):
        return subprocess.check_output(
            ["tar", "xOzf", package_path, f"{omd_version}/{version_rel_path}"]
        )

    if package_path.endswith(".tar.gz"):
        return subprocess.check_output(
            [
                "tar",
                "xOzf",
                package_path,
                f"{Path(package_path).name.removesuffix('.tar.gz')}/{version_rel_path}",
            ]
        )

    raise NotImplementedError()


# In case packages grow/shrink this check has to be changed.
@pytest.mark.parametrize(
    "pkg_format,min_size,max_size",
    [
        ("rpm", 196 * 1024 * 1024, 229 * 1024 * 1024),
        ("deb", 150 * 1024 * 1024, 165 * 1024 * 1024),
        ("cma", 290 * 1024 * 1024, 302 * 1024 * 1024),
        ("tar.gz", 350 * 1024 * 1024, 380 * 1024 * 1024),
    ],
)
@pytest.mark.skip("skip for now until our build chaos has settled...")
def test_package_sizes(package_path: str, pkg_format: str, min_size: int, max_size: int) -> None:
    if not package_path.endswith(".%s" % pkg_format):
        pytest.skip("%s is another package type" % os.path.basename(package_path))

    if not os.path.basename(package_path).startswith("check-mk-enterprise-"):
        pytest.skip("only testing enterprise packages")

    size = os.stat(package_path).st_size
    assert min_size <= size <= max_size, (
        f"Package {package_path} size {size} not between {min_size} and {max_size} bytes."
    )


def test_files_not_in_version_path(package_path: str, cmk_version: str) -> None:
    if not package_path.endswith(".rpm") and not package_path.endswith(".deb"):
        pytest.skip("%s is another package type" % os.path.basename(package_path))

    paths = _get_paths_from_package(package_path)

    version_allowed_patterns = [
        "/opt/omd/versions/?$",
        "/opt/omd/versions/###OMD_VERSION###/?$",
    ]

    # All files below the standard directories are allowed
    for basedir in ["bin", "etc", "include", "lib", "local", "share", "skel", "tmp", "var"]:
        version_allowed_patterns += [
            "/opt/omd/versions/###OMD_VERSION###/%s/?$" % basedir,
            "/opt/omd/versions/###OMD_VERSION###/%s/.*" % basedir,
        ]

    if package_path.endswith(".rpm"):
        allowed_patterns = [
            "/opt$",
            "/opt/omd$",
            "/opt/omd/apache$",
            "/opt/omd/sites$",
            "/var/lock/mkbackup$",
        ] + version_allowed_patterns
    elif package_path.endswith(".deb"):
        allowed_patterns = [
            "/$",
            "/opt/$",
            "/opt/omd/$",
            "/opt/omd/apache/$",
            "/opt/omd/sites/$",
            "/usr/$",
            "/usr/share/$",
            "/usr/share/man/$",
            "/usr/share/man/man8/$",
            "/usr/share/doc/$",
            "/usr/share/doc/check-mk-(raw|free|enterprise|managed|cloud|saas)-.*/$",
            "/usr/share/doc/check-mk-(raw|free|enterprise|managed|cloud|saas)-.*/changelog.gz$",
            "/usr/share/doc/check-mk-(raw|free|enterprise|managed|cloud|saas)-.*/COPYING.gz$",
            "/usr/share/doc/check-mk-(raw|free|enterprise|managed|cloud|saas)-.*/TEAM$",
            "/usr/share/doc/check-mk-(raw|free|enterprise|managed|cloud|saas)-.*/copyright$",
            "/usr/share/doc/check-mk-(raw|free|enterprise|managed|cloud|saas)-.*/README.md$",
            "/etc/$",
            "/etc/init.d/$",
            "/etc/init.d/check-mk-(raw|free|enterprise|managed|cloud|saas)-.*$",
        ] + version_allowed_patterns
    else:
        raise NotImplementedError()

    LOGGER.info("Testing %s", package_path)

    omd_version = _get_omd_version(cmk_version, package_path)
    LOGGER.info("Checking OMD version: %s", omd_version)

    for path in paths:
        is_allowed = any(
            re.match(p.replace("###OMD_VERSION###", omd_version), path) for p in allowed_patterns
        )
        assert is_allowed, f"Found unexpected global file: {path} in {package_path}"


@cache
def _get_paths_from_package(path_to_package: str) -> list[str]:
    if path_to_package.endswith(".rpm"):
        return subprocess.check_output(
            ["rpm", "-qlp", path_to_package], encoding="utf-8"
        ).splitlines()

    if path_to_package.endswith(".deb"):
        return [
            line.split()[5].lstrip(".")
            for line in subprocess.check_output(
                ["dpkg", "-c", path_to_package], encoding="utf-8"
            ).splitlines()
        ]
    if path_to_package.endswith(".cma"):
        return [
            line
            for line in subprocess.check_output(
                ["tar", "tzf", path_to_package], encoding="utf-8"
            ).splitlines()
        ]

    raise NotImplementedError()


def test_cma_only_contains_version_paths(package_path: str, cmk_version: str) -> None:
    if not package_path.endswith(".cma"):
        pytest.skip("%s is another package type" % os.path.basename(package_path))

    omd_version = _get_omd_version(cmk_version, package_path)
    files = [
        line.split()[5]
        for line in subprocess.check_output(
            ["tar", "tvf", package_path], encoding="utf-8"
        ).splitlines()
    ]
    assert len(files) > 1000
    for file_path in files:
        assert file_path.startswith(omd_version + "/")


def test_cma_specific_files(package_path: str, cmk_version: str) -> None:
    if not package_path.endswith(".cma"):
        pytest.skip("%s is another package type" % os.path.basename(package_path))

    omd_version = _get_omd_version(cmk_version, package_path)
    files = [
        line.split()[5]
        for line in subprocess.check_output(
            ["tar", "tvf", package_path], encoding="utf-8"
        ).splitlines()
    ]
    assert "%s/cma.info" % omd_version in files
    assert "%s/skel/etc/apache/conf.d/cma.conf" % omd_version in files
    assert "%s/lib/cma/post-install" % omd_version in files

    cma_info = subprocess.check_output(
        ["tar", "xOvzf", package_path, "%s/cma.info" % omd_version], encoding="utf-8"
    )
    assert "DEMO=1" not in cma_info


def test_src_only_contains_relative_version_paths(
    package_path: str,
) -> None:
    if not package_path.endswith(".tar.gz"):
        pytest.skip("%s is not a source package" % os.path.basename(package_path))

    prefix = os.path.basename(package_path).replace(".tar.gz", "")
    for line in subprocess.check_output(
        ["tar", "tvf", package_path], encoding="utf-8"
    ).splitlines():
        path = line.split()[5]
        assert path.startswith(prefix + "/")


def test_src_does_not_contain_dev_files(
    package_path: str,
) -> None:
    """test that there are no dev files (currently only .f12 files) are packed"""

    if not package_path.endswith(".tar.gz"):
        pytest.skip("%s is not a source package" % os.path.basename(package_path))

    for line in subprocess.check_output(
        ["tar", "tvf", package_path], encoding="utf-8"
    ).splitlines():
        path = Path(line.split()[5])
        assert path.name != ".f12"


def test_src_not_contains_enterprise_sources(package_path: str) -> None:
    if not package_path.endswith(".tar.gz"):
        pytest.skip("%s is not a source package" % os.path.basename(package_path))

    # package_path may indicate that we're having a release candidate but all files inside
    # the package paths should not contain a rc information anymore.
    prefix = os.path.basename(package_path).replace(".tar.gz", "").split("-rc")[0]
    enterprise_files = []
    managed_files = []
    cloud_files = []
    saas_files = []

    for line in subprocess.check_output(
        ["tar", "tvf", package_path], encoding="utf-8"
    ).splitlines():
        path = line.split()[5]
        if path != "%s/enterprise/" % prefix and path.startswith("%s/enterprise/" % prefix):
            enterprise_files.append(path)
        if path != "%s/managed/" % prefix and path.startswith("%s/managed/" % prefix):
            managed_files.append(path)
        if path != "%s/cloud/" % prefix and path.startswith("%s/cloud/" % prefix):
            cloud_files.append(path)
        if path != "%s/saas/" % prefix and path.startswith("%s/saas/" % prefix):
            saas_files.append(path)

    assert not enterprise_files
    assert not managed_files
    assert not cloud_files
    assert not saas_files


def test_package_is_identifiable_by_commit(package_path: str, cmk_version: str) -> None:
    commit = _get_file_from_package(
        package_path,
        cmk_version,
        version_rel_path="COMMIT" if package_path.endswith(".tar.gz") else "share/doc/COMMIT",
    )
    assert (
        subprocess.check_output(["git", "rev-parse", "HEAD"], encoding="utf-8").strip()
        == commit.strip().decode()
    )


def test_monitoring_cores_packaging(package_path: str, cmk_version: str) -> None:
    if package_path.endswith(".tar.gz"):
        pytest.skip("%s do not test source packages" % os.path.basename(package_path))

    if _edition_short_from_pkg_path(package_path) != "cre":
        assert (
            len(_get_file_from_package(package_path, cmk_version, version_rel_path="bin/cmc")) > 0
        )

    assert len(_get_file_from_package(package_path, cmk_version, version_rel_path="bin/nagios")) > 0


def test_not_rc_tag(package_path: str, cmk_version: str) -> None:
    msi_file_path = os.path.join(
        os.path.dirname(__file__), "../../agents/windows/check_mk_agent.msi"
    )
    assert os.path.isfile(msi_file_path)

    if os.stat(msi_file_path).st_size == 0:
        pytest.skip(
            f"The file {msi_file_path} was most likely faked by fake-artifacts, "
            f"so there is no reason to check it with msiinfo"
        )
    properties = {
        name: value
        for line in subprocess.check_output(
            ["msiinfo", "export", msi_file_path, "Property"], text=True
        ).splitlines()
        if "\t" in line
        for name, value in (line.split("\t", 1),)
    }

    assert "ProductVersion" in properties
    assert properties["ProductVersion"] == cmk_version
    assert not re.match(r".*-rc\d+$", properties["ProductVersion"])


def test_python_files_are_precompiled_pycs(package_path: str, cmk_version: str) -> None:
    if not package_path.endswith((".rpm", ".deb")):
        pytest.skip("%s is another package type" % os.path.basename(package_path))

    LOGGER.info("Testing %s", package_path)

    paths = _get_paths_from_package(package_path)

    omd_version = _get_omd_version(cmk_version, package_path)
    LOGGER.info("Checking OMD version: %s", omd_version)

    def _get_shipped_python_binary_name(paths: list[str]) -> str:
        """
        Get name for the shipped Python binary.

        Will look for a name with major and minor included, e.g. python3.12
        """
        for path in paths:
            if not path.startswith(f"/opt/omd/versions/{omd_version}/bin/python3"):
                continue

            # We might encounter binaries like python3.12-config.
            # Skip those by checking if we end in a number
            if not path.endswith(tuple(map(str, range(10)))):
                continue

            p = PosixPath(path)

            # We need a major.minor version, not just python3
            if "." not in p.name:
                continue

            return p.name

        raise ValueError("Unable to find shipped Python version")

    def expected_pyc_path(python_file_path: str, python3_version: str) -> str:
        # In: /opt/omd/versions/2.4.0-2025.02.06.cee/lib/python3/cmk/automations/__init__.py
        # Out: /opt/omd/versions/2.4.0-2025.02.06.cee/lib/python3/cmk/automations/__pycache__/__init__.cpython-312.pyc
        path = PosixPath(python_file_path)

        cachedir = path.parent / "__pycache__"

        filename = path.name.removesuffix(path.suffix)
        filename = f"{filename}.cpython-{python3_version}.pyc"

        return str(cachedir / filename)

    python_binary = _get_shipped_python_binary_name(paths)
    shortened_python_version = python_binary.replace("python", "").replace(".", "")

    python_paths = {
        path for path in paths if path.startswith(f"/opt/omd/versions/{omd_version}/lib/python3")
    }
    python_files = [path for path in python_paths if path.endswith(".py")]
    assert python_files, f"Didn't find Python files in package {package_path}"

    missing_pycs = set()
    for path in python_files:
        expected_path = expected_pyc_path(path, shortened_python_version)

        if expected_path not in python_paths:
            missing_pycs.add(path)

    assert not missing_pycs, f"The following files aren't precompiled: {', '.join(missing_pycs)}"


Bom = dict


@pytest.fixture(name="bom_json", scope="module")
def load_bom(package_path: str, cmk_version: str) -> Bom:
    return json.loads(
        _get_file_from_package(
            package_path,
            cmk_version,
            "omd/bill-of-materials.json"
            if package_path.endswith(".tar.gz")
            else "share/doc/bill-of-materials.json",
        )
    )


@pytest.fixture(name="license_csv_rows", scope="module")
def load_license_csv(package_path: str, cmk_version: str) -> list[dict[str, str]]:
    license_file = io.StringIO(
        _get_file_from_package(
            package_path,
            cmk_version,
            "omd/bill-of-materials.csv"
            if package_path.endswith(".tar.gz")
            else "share/doc/bill-of-materials.csv",
        ).decode("utf-8")
    )
    reader = csv.DictReader(license_file)
    return list(reader)


def test_bom(bom_json: Bom) -> None:
    """Check that there is a BOM and it contains dependencies from various eco-systems"""
    purls_wo_version = {c["purl"].split("@", 1)[0] for c in bom_json["components"] if "purl" in c}

    # These are manually picked and should represent dependencies from our various ecosystems.
    # I chose dependencies that are unlikely to be removed...
    assert "pkg:cargo/clap" in purls_wo_version
    assert "pkg:npm/d3" in purls_wo_version
    assert "pkg:github/google/re2" in purls_wo_version
    assert "pkg:pypi/certifi" in purls_wo_version


# Unskip with https://jira.lan.tribe29.com/browse/CMK-23389
@pytest.mark.skipif(
    date.today() < date(2025, 10, 1),
    reason="Skip bom synchronous check for some time. "
    "At the moment there is a lot of rework regarding WORKSPACE/MODULE.bazel (see CMK-20349)."
    "That's why the bom generation is mostly wrong at the moment.",
)
def test_bom_csv_synchronous(bom_json: Bom, license_csv_rows: list[dict[str, str]]) -> None:
    """test that the csv and bom contain the same versions

    let's just check for certifi and openssl since I know they are updated constantly"""

    openssl_version: str | None = None
    # we have multiple certifis (agent updater 2x and in a site)
    certifi_versions: set[str] = set()

    for component in bom_json["components"]:
        if component["name"] == "openssl" and "cpe" in component:
            openssl_version = component["version"]
        if component.get("purl", "").startswith("pkg:pypi/certifi@"):
            certifi_versions.add(component["version"])

    assert openssl_version is not None
    assert certifi_versions

    for row in license_csv_rows:
        if row["Name"] == "openssl":
            assert row["Version"] == openssl_version
        if row["Name"] == "Python module: certifi":
            assert row["Version"] in certifi_versions


AGENT_PLUGINS_PREFIX = [
    "apache_status",
    "isc_dhcpd",
    "mk_ceph",
    "mk_docker",
    "mk_filestats",
    "mk_inotify",
    "mk_jolokia",
    "mk_logwatch",
    "mk_mongodb",
    "mk_postgres",
    "mk_sap",
    "mk_tinkerforge",
    "mtr",
    "nginx_status",
    "plesk_backups",
    "plesk_domains",
    "unitrends_replication",
]


def test_python_agent_plugins(package_path: str, cmk_version: str) -> None:
    if package_path.endswith(".tar.gz"):
        pytest.skip(
            "Skipping test for source package as it is more interessting for the install-able packages."
        )

    for prefix in AGENT_PLUGINS_PREFIX:
        for suffix in (".py", "_2.py"):
            filename = f"{prefix}{suffix}"
            assert _file_exists_in_package(
                package_path, cmk_version, f"share/check_mk/agents/plugins/{filename}"
            ), f"File {filename} is missing in {package_path}"
