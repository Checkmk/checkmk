#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import re
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import pytest

logger = logging.getLogger()


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
                ["dpkg", "--fsys-tarfile", package_path],
                stdout=subprocess.PIPE,
                check=False,
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
    assert min_size <= size <= max_size, "Package {} size {} not between {} and {} bytes.".format(
        package_path,
        size,
        min_size,
        max_size,
    )


def test_files_not_in_version_path(package_path: str, cmk_version: str) -> None:
    if not package_path.endswith(".rpm") and not package_path.endswith(".deb"):
        pytest.skip("%s is another package type" % os.path.basename(package_path))

    version_allowed_patterns = [
        "/opt/omd/versions/?$",
        "/opt/omd/versions/###OMD_VERSION###/?$",
    ]

    # All files below the standard directories are allowed
    for basedir in [
        "bin",
        "etc",
        "include",
        "lib",
        "local",
        "share",
        "skel",
        "tmp",
        "var",
    ]:
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

        paths = subprocess.check_output(
            ["rpm", "-qlp", package_path], encoding="utf-8"
        ).splitlines()
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

        paths = []
        for line in subprocess.check_output(
            ["dpkg", "-c", package_path], encoding="utf-8"
        ).splitlines():
            paths.append(line.split()[5].lstrip("."))
    else:
        raise NotImplementedError()

    logger.info("Testing %s", package_path)

    omd_version = _get_omd_version(cmk_version, package_path)
    logger.info("Checking OMD version: %s", omd_version)

    for path in paths:
        is_allowed = any(
            re.match(p.replace("###OMD_VERSION###", omd_version), path) for p in allowed_patterns
        )
        assert is_allowed, f"Found unexpected global file: {path} in {package_path}"


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
    test_data = []
    non_free_files = []
    cmc_files = []

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
        if path != "%s/tests/qa-test-data/" % prefix and path.startswith(
            "%s/tests/qa-test-data/" % prefix
        ):
            test_data.append(path)
        if path != "%s/non-free/" % prefix and path.startswith("%s/non-free/" % prefix):
            non_free_files.append(path)
        if path != "%s/packages/cmc/" % prefix and path.startswith("%s/packages/cmc/" % prefix):
            cmc_files.append(path)

    assert not enterprise_files
    assert not managed_files
    assert not cloud_files
    assert not saas_files

    assert not test_data
    assert not non_free_files
    assert not cmc_files


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
            f"The file {msi_file_path} was most likely faked by fake-windows-artifacts, "
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


def _verify_signature(file_path: Path, file_name: str) -> None | str:
    result = subprocess.run(
        [
            "osslsigncode",
            "verify",
            file_path,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return f"{file_name}: " + result.stderr
    return None


def test_windows_artifacts_are_signed(package_path: str, cmk_version: str) -> None:
    signing_failures = []

    mk_sql = "mk-sql.exe"
    path_prefix = (
        "agents/windows" if package_path.endswith(".tar.gz") else "share/check_mk/agents/windows"
    )

    with NamedTemporaryFile() as mk_sql_temp:
        mk_sql_temp.write(
            _get_file_from_package(package_path, cmk_version, f"{path_prefix}/{mk_sql}")
        )
        mk_sql_temp.flush()
        signing_failures.append(_verify_signature(Path(mk_sql_temp.name), mk_sql))

    # TODO: Clarify why the msi is missing in the source.tar.gz CMK-26785
    if not package_path.endswith(".tar.gz"):
        with NamedTemporaryFile() as msi_file:
            msi_file.write(
                _get_file_from_package(
                    package_path, cmk_version, f"{path_prefix}/check_mk_agent.msi"
                )
            )
            msi_file.flush()
            signing_failures.append(_verify_signature(Path(msi_file.name), "check_mk_agent.msi"))
            with TemporaryDirectory() as msi_content:
                subprocess.run(
                    ["msiextract", "-C", msi_content, msi_file.name],
                    check=False,
                    stdout=subprocess.DEVNULL,
                )
                for file in ("check_mk_agent.exe", "cmk-agent-ctl.exe"):
                    signing_failures.append(
                        _verify_signature(
                            Path(msi_content + "/Program Files/checkmk/service/" + file), file
                        )
                    )

    assert not any(signing_failures)
