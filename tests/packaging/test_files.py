#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"

import atexit
import csv
import io
import json
import logging
import os
import re
import subprocess
import tarfile
from collections.abc import Sequence
from functools import cache
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import NamedTuple

import pytest

LOGGER = logging.getLogger()

# Cache for Docker container IDs: package_path -> container_id
_docker_container_cache: dict[str, str] = {}

# Cache for Docker manifest.json: package_path -> (image_tag, manifest_data)
_docker_manifest_cache: dict[str, tuple[str, dict]] = {}


def _cleanup_docker_containers() -> None:
    for container_id in _docker_container_cache.values():
        subprocess.run(
            ["docker", "rm", "-v", container_id],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


atexit.register(_cleanup_docker_containers)


def _get_or_create_docker_container(package_path: str) -> str:
    """Get or create a Docker container from a Docker OCI image tar.gz.

    Returns the container ID.
    The container and image are cached for reuse during runtime - as we'll repeatedly retrieve
    files from the image / container.
    """
    # Get or read the manifest to find the image tag (with caching)
    if package_path in _docker_manifest_cache:
        image_tag, _ = _docker_manifest_cache[package_path]
    else:
        manifest_json = json.loads(
            subprocess.check_output(["tar", "xOzf", package_path, "manifest.json", "-O"])
        )
        # we should have only one image in the tarball
        image_tag = manifest_json[0]["RepoTags"][0]
        _docker_manifest_cache[package_path] = (image_tag, manifest_json)

        assert len(manifest_json) == 1, "Multiple images in the docker container tarball"

    # Get or create container (with caching)
    if package_path in _docker_container_cache:
        return _docker_container_cache[package_path]

    # Ensure image is loaded
    image_exists = (
        subprocess.run(
            ["docker", "image", "inspect", image_tag],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )

    if not image_exists:
        LOGGER.info("Loading docker image %s...", package_path)
        subprocess.check_call(["docker", "load", "-i", package_path])

    container_id = subprocess.check_output(["docker", "create", image_tag]).strip().decode("utf-8")
    _docker_container_cache[package_path] = container_id
    return container_id


def _get_package_dependencies(package_path: str) -> Sequence[str]:
    if package_path.endswith(".deb"):
        return [
            dep.strip()
            for dep in [
                line
                for line in subprocess.check_output(
                    ["dpkg", "-I", package_path], encoding="utf-8"
                ).splitlines()
                if "Depends:" in line
            ][0]
            .split("Depends:")[1]
            .split(",")
        ]
    if package_path.endswith(".rpm"):
        return subprocess.check_output(["rpm", "-qpR", package_path], encoding="utf-8").splitlines()
    raise NotImplementedError(f"Unsupported package type for dependency extraction: {package_path}")


def _get_omd_version(cmk_version: str, package_path: str) -> str:
    """Extract the files edition"""
    edition = _edition_from_pkg_path(package_path)
    return f"{cmk_version}.{edition}"


def _edition_from_pkg_path(package_path: str) -> str:
    file_name = os.path.basename(package_path)
    if file_name.startswith("check-mk-community-"):
        return "community"
    if file_name.startswith("check-mk-pro-"):
        return "pro"
    if file_name.startswith("check-mk-ultimatemt-"):
        return "ultimatemt"
    if file_name.startswith("check-mk-ultimate-"):
        return "ultimate"
    if file_name.startswith("check-mk-cloud-"):
        return "cloud"
    raise NotImplementedError("Could not get edition from package path: %s" % package_path)


def _get_file_from_docker_package(
    package_path: str, omd_version: str, version_rel_path: str
) -> bytes:
    """Extract a file from a Docker OCI image tar.gz using docker cp from a container.

    This function loads the Docker image, creates a container, and uses docker cp
    to extract files. The container is cached for subsequent extractions.
    """
    container_id = _get_or_create_docker_container(package_path)

    # Copy file out using 'docker cp'
    target_path = f"/opt/omd/versions/{omd_version}/{version_rel_path}"

    proc = subprocess.Popen(
        ["docker", "cp", f"{container_id}:{target_path}", "-"],
        stdout=subprocess.PIPE,
    )

    if proc.stdout is None:
        raise RuntimeError("Failed to open stdout pipe for 'docker cp'")

    # read file from the stdout stream of tarfile
    with tarfile.open(fileobj=proc.stdout, mode="r|*") as tar:
        for member in tar:
            if member.isfile():
                f = tar.extractfile(member)
                if f:
                    content = f.read()
                    proc.stdout.close()
                    proc.wait()
                    return content

        # If we get here, we didn't find a file in the tar stream
        proc.wait()
        raise FileNotFoundError(f"File {version_rel_path} not found in {package_path}")

    # This shouldn't be reached, but just in case
    raise FileNotFoundError(f"File {version_rel_path} not found in {package_path}")


def _file_exists_in_package(package_path: str, cmk_version: str, version_rel_path: str) -> bool:
    omd_version = _get_omd_version(cmk_version, package_path)

    file_list = _get_paths_from_package(package_path)

    if package_path.endswith(".deb"):
        return f"opt/omd/versions/{omd_version}/{version_rel_path}" in file_list

    if package_path.endswith(".rpm"):
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
            ["tar", "xOf", "-", f"opt/omd/versions/{omd_version}/{version_rel_path}"],
            input=subprocess.run(
                ["dpkg", "--fsys-tarfile", package_path], stdout=subprocess.PIPE, check=False
            ).stdout,
        )

    if package_path.endswith(".cma"):
        return subprocess.check_output(
            ["tar", "xOzf", package_path, f"{omd_version}/{version_rel_path}"]
        )

    if package_path.endswith(".tar.gz"):
        if "-docker-" in package_path:
            return _get_file_from_docker_package(package_path, omd_version, version_rel_path)
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

    if not os.path.basename(package_path).startswith("check-mk-pro-"):
        pytest.skip("only testing pro packages")

    size = os.stat(package_path).st_size
    assert min_size <= size <= max_size, (
        f"Package {package_path} size {size} not between {min_size} and {max_size} bytes."
    )


def test_files_not_in_version_path(package_path: str, cmk_version: str) -> None:
    if not package_path.endswith(".rpm") and not package_path.endswith(".deb"):
        pytest.skip("%s is another package type" % os.path.basename(package_path))

    paths = _get_paths_from_package(package_path)

    prefix = ""
    if package_path.endswith(".rpm"):
        prefix = "/"

    version_allowed_patterns = [
        "%sopt/omd/versions/?$" % prefix,
        "%sopt/omd/versions/###OMD_VERSION###/?$" % prefix,
    ]

    # All files below the standard directories are allowed
    for basedir in ["bin", "etc", "include", "lib", "local", "share", "skel", "tmp", "var"]:
        version_allowed_patterns += [
            f"{prefix}opt/omd/versions/###OMD_VERSION###/{basedir}/?$",
            f"{prefix}opt/omd/versions/###OMD_VERSION###/{basedir}/.*",
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
            "$",
            "opt/$",
            "opt/omd/$",
            "opt/omd/apache/$",
            "opt/omd/sites/$",
            "usr/$",
            "usr/share/$",
            "usr/share/man/$",
            "usr/share/man/man8/$",
            "usr/share/doc/$",
            "usr/share/doc/check-mk-(community|pro|ultimatemt|ultimate|cloud)-.*/$",
            "usr/share/doc/check-mk-(community|pro|ultimatemt|ultimate|cloud)-.*/changelog.gz$",
            "usr/share/doc/check-mk-(community|pro|ultimatemt|ultimate|cloud)-.*/COPYING.gz$",
            "usr/share/doc/check-mk-(community|pro|ultimatemt|ultimate|cloud)-.*/TEAM$",
            "usr/share/doc/check-mk-(community|pro|ultimatemt|ultimate|cloud)-.*/copyright$",
            "usr/share/doc/check-mk-(community|pro|ultimatemt|ultimate|cloud)-.*/README.md$",
            "etc/$",
            "etc/init.d/$",
            "etc/init.d/check-mk-(community|pro|ultimatemt|ultimate|cloud)-.*$",
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

    disallowed_pattern = [
        ".*/.f12$",
        ".*/OWNERS$",
        ".*/BUILD$",
        r".*/BUILD\..*$",
    ]
    disallowed_paths = [
        path for path in paths if any(re.match(p, path) for p in disallowed_pattern)
    ]
    assert not disallowed_paths, f"Found unwanted files in {package_path}: {disallowed_paths}"


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

    if path_to_package.endswith(".tar.gz"):
        if "-docker-" in path_to_package:
            # Docker OCI image: use docker container to list files
            container_id = _get_or_create_docker_container(path_to_package)

            # Use docker export to get all files
            proc = subprocess.Popen(
                ["docker", "export", container_id],
                stdout=subprocess.PIPE,
            )

            if proc.stdout is None:
                raise RuntimeError("Failed to open stdout pipe for docker export")

            # List files from the tar stream
            paths_output = subprocess.check_output(
                ["tar", "t"],
                input=proc.stdout.read(),
            )
            proc.wait()

            all_paths = [
                "/" + path if not path.startswith("/") else path
                for path in paths_output.decode("utf-8").splitlines()
            ]

            return all_paths

        # source package
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
    """test that there are no dev files are packed"""

    if not package_path.endswith(".tar.gz"):
        pytest.skip("%s is not a source package" % os.path.basename(package_path))

    unwanted_files = [
        path
        for line in subprocess.check_output(
            ["tar", "tvf", package_path], encoding="utf-8"
        ).splitlines()
        if (path := Path(line.split()[5])).name in {".f12", "OWNERS"}
    ]
    assert not unwanted_files, (
        f"Found files in {package_path} which should not be there:"
        f" {','.join(map(str, unwanted_files))}"
    )


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

    for line in subprocess.check_output(
        ["tar", "tvf", package_path], encoding="utf-8"
    ).splitlines():
        path = line.split()[5]
        if path != "%s/pro/" % prefix and path.startswith("%s/pro/" % prefix):
            enterprise_files.append(path)
        if path != "%s/ultimatemt/" % prefix and path.startswith("%s/ultimatemt/" % prefix):
            managed_files.append(path)
        if path != "%s/ultimate/" % prefix and path.startswith("%s/ultimate/" % prefix):
            cloud_files.append(path)
        if path != "%s/cloud/" % prefix and path.startswith("%s/cloud/" % prefix):
            saas_files.append(path)
        if path != "%s/tests/qa-test-data/" % prefix and path.startswith(
            "%s/tests/qa-test-data/" % prefix
        ):
            test_data.append(path)
        if path != "%s/non-free/" % prefix and path.startswith("%s/non-free/" % prefix):
            non_free_files.append(path)

    assert not enterprise_files
    assert not managed_files
    assert not cloud_files
    assert not saas_files

    assert not test_data
    assert not non_free_files


def test_community_not_contains_nonfree_files(package_path: str) -> None:
    """community packages should NOT contain non-free (formerly cee/enterprise) files"""
    if not Path(package_path).name.startswith("check-mk-community-"):
        pytest.skip("%s is not a community package" % os.path.basename(package_path))
    if package_path.endswith(".tar.gz") and "-docker-" in package_path:
        pytest.skip("%s is a docker OCI image - can't handle here" % os.path.basename(package_path))

    files_in_package = _get_paths_from_package(package_path)
    non_free_files = [f for f in files_in_package if re.search(r"(non-free|nonfree)", f)]
    assert not non_free_files, (
        f"Found {len(non_free_files)} non-free files in community package (only first 10): {non_free_files[:10]}"
    )


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

    if _edition_from_pkg_path(package_path) != "community":
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
@pytest.mark.skip(
    "Skip bom synchronous check while Bazel work is ongoing. "
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
        filename = f"{prefix}.py"
        assert _file_exists_in_package(
            package_path, cmk_version, f"share/check_mk/agents/plugins/{filename}"
        ), f"File {filename} is missing in {package_path}"


def test_relay_install_script_file(package_path: str, cmk_version: str) -> None:
    if package_path.endswith(".tar.gz"):
        pytest.skip("Skipping test for source package.")

    if _edition_from_pkg_path(package_path) == "ultimate":
        assert _file_exists_in_package(
            package_path, cmk_version, "share/check_mk/relays/install_relay.sh"
        ), f"File share/check_mk/relays/install_relay.sh is missing in {package_path}"


class UnwantedDependency(NamedTuple):
    dependency: str
    reason: str

    def printable(self) -> str:
        return f"Unwanted dependency '{self.dependency}': {self.reason}"


def test_unwanted_package_dependencies(package_path: str) -> None:
    """
    This test should ensure that our deb/rpm packages do not depend on unwanted packages.
    Background information:
    * depending on the used installation mechanism, needed dependencies will be installed automatically
    * in some case this may break an existing configuration or there are other reasons why we do not want to depend on a package
    * so this test should ensure/remind us to not add unwanted dependencies to our packages
    """
    if package_path.endswith(".cma"):
        pytest.skip(
            "Skipping test for cma package - it is based on another distro (at time of writing: debian-12)"
        )

    if package_path.endswith(".tar.gz"):
        pytest.skip(
            "Skipping test for source package as it is more interessting for the install-able packages."
        )

    unwanted_dependencies = [
        UnwantedDependency(
            dependency="sendmail",
            reason="The installation of sendmail would e.g. overwrite existing mail configuration. For details see discussions in https://jira.lan.tribe29.com/browse/BETA-84",
        ),
        UnwantedDependency(
            dependency="git",
            reason="git is only needed for track the WATO config and only used by power users",
        ),
        UnwantedDependency(
            dependency="ipmitool",
            reason="impitool is only needed by power users",
        ),
    ]
    package_dependencies = _get_package_dependencies(package_path)

    actual_unwanted_dependencies: list[UnwantedDependency] = []
    for unwanted in unwanted_dependencies:
        for p in package_dependencies:
            # Check for the substring and not exact match bc version definition might break
            # exact matching, e.g.: rpmlib(CompressedFileNames) <= 3.0.4-1
            if unwanted.dependency in p:
                actual_unwanted_dependencies.append(unwanted)

    assert not actual_unwanted_dependencies, "\n" + "\n".join(
        [u.printable() for u in actual_unwanted_dependencies]
    )


# files that are not signed (and where it's OK, because we don't build them ourselves)
FILES_UNSIGNED = [
    # -- treasures --
    # ...is explicitly not maintained (provided as-is)
    re.compile(r".*/share/doc/check_mk/treasures/.*\.(exe|dll)$"),
    # -- exe files --
    # python files not built by us
    re.compile(r".*/lib/python3\.\d+/site-packages/.*\.exe$"),
    # todo: add code signing and verification for robotmk, then remove from this list CMK-26814
    re.compile(r".*/share/check_mk/agents/windows/plugins/robotmk_agent_plugin.exe$"),
    re.compile(r".*/share/check_mk/agents/windows/robotmk_ext.exe$"),
    re.compile(r".*/share/check_mk/agents/robotmk/windows/rcc.exe$"),
    re.compile(r".*/share/check_mk/agents/robotmk/windows/micromamba.exe$"),  # only 2.5.0
    re.compile(r".*/share/check_mk/agents/robotmk/windows/robotmk_scheduler.exe$"),
    # -- dll files --
]
FILE_PATTERNS_SIGNABLE = [
    re.compile(r".*\.exe$"),
    re.compile(r".*\.dll$"),
    re.compile(r".*\.msi$"),
]


def _should_be_signed(path: str) -> bool:
    if not any(pattern.match(path) for pattern in FILE_PATTERNS_SIGNABLE):
        return False
    if any(pattern.match(path) for pattern in FILES_UNSIGNED):
        return False
    return True


def _verify_signature(file_path: Path, file_name: str) -> None | str:
    try:
        assert file_path.exists(), f"File to verify does not exist: {file_path}"
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
    except FileNotFoundError:
        # osslsigncode not found - it should be available in CI (via test-packaging Makefile target)
        # -> should only occur in local test environments
        LOGGER.error("osslsigncode not found in PATH")
        if os.environ.get("CI"):
            LOGGER.error("THIS SHOULD NOT HAPPEN in CI! PLEASE REPORT!")
        else:
            LOGGER.warning("Please build it locally via bazel (and add it to your PATH), e.g.:")
            LOGGER.warning(
                "  bazel: export PATH=$PATH:$(bazel run //bazel/tools:bazel_env print-path)"
            )
        raise
    LOGGER.info(
        "Signature verification of '%s': %s - %s",
        file_name,
        "PASS" if result.returncode == 0 else "FAIL",
        result.stderr.strip(),
    )
    if result.returncode != 0:
        return f"{file_name}: " + result.stderr
    return None


@pytest.mark.parametrize(
    "is_no_source,path_prefix_agents,non_msi_files",
    [
        (
            True,
            "share/check_mk/agents/windows",
            [
                "share/check_mk/agents/windows/mk-sql.exe",
                "lib/python3/cmk/plugins/oracle/agents/mk-oracle.exe",
            ],
        ),
        (
            False,
            "agents/windows",
            [
                "agents/windows/mk-sql.exe",
                # todo: check why mk-oracle.exe is missing in source tar.gz CMK-26785
            ],
        ),
    ],
    ids=["deb_rpm_cma_docker", "tar_gz_source"],
)
def test_windows_artifacts_are_signed(
    package_path: str,
    cmk_version: str,
    is_no_source: bool,
    path_prefix_agents: str,
    non_msi_files: list[str],
) -> None:
    # Skip mismatched package types
    actual_is_source = package_path.endswith(".tar.gz") and "-docker-" not in package_path

    if actual_is_source != (not is_no_source):
        if is_no_source:
            pytest.skip(
                f"Expected binary package but got source: '{os.path.basename(package_path)}'"
            )
        else:
            pytest.skip(
                f"Expected source package but got binary: '{os.path.basename(package_path)}'"
            )

    signing_failures = []
    paths_checked = []

    # Check non-msi files first (exe, dll)
    for non_msi_file in non_msi_files:
        with NamedTemporaryFile() as non_msi_file_temp:
            non_msi_file_temp.flush()
            non_msi_file_temp.write(_get_file_from_package(package_path, cmk_version, non_msi_file))
            signing_failures.append(_verify_signature(Path(non_msi_file_temp.name), non_msi_file))
            paths_checked.append(non_msi_file)

    # check msi and files inside msi
    # TODO: Clarify why the msi is missing in the source.tar.gz CMK-26785
    if is_no_source:
        with NamedTemporaryFile() as msi_file:
            msi_file.write(
                _get_file_from_package(
                    package_path, cmk_version, f"{path_prefix_agents}/check_mk_agent.msi"
                )
            )
            msi_file.flush()
            signing_failures.append(
                _verify_signature(Path(msi_file.name), f"{path_prefix_agents}/check_mk_agent.msi")
            )
            paths_checked.append(f"{path_prefix_agents}/check_mk_agent.msi")
            with TemporaryDirectory() as msi_content:
                try:
                    subprocess.run(
                        ["msiextract", "-C", msi_content, msi_file.name],
                        check=False,
                        stdout=subprocess.DEVNULL,
                    )
                except FileNotFoundError:
                    LOGGER.error("msiextract not found in PATH")
                    LOGGER.error("IF IN CI - THIS SHOULD NOT HAPPEN! PLEASE REPORT!")
                    LOGGER.warning("can be installed locally")
                    LOGGER.warning("  ubuntu: sudo apt install msitools")
                    raise
                for file in ("check_mk_agent.exe", "cmk-agent-ctl.exe"):
                    signing_failures.append(
                        _verify_signature(
                            Path(msi_content + "/Program Files/checkmk/service/" + file),
                            f"check_mk_agent.msi/Program Files/checkmk/service/{file}",
                        )
                    )

    # check for additional files in the package
    # (so we don't forget to add them to the signing process)
    if is_no_source:
        paths = _get_paths_from_package(package_path)
        omd_version = _get_omd_version(cmk_version, package_path)
        paths_signable = [
            # remove prefixes of paths to make it comparable
            #   * opt/omd/versions/{omd_version}/...  (for deb)
            #   * /opt/omd/versions/{omd_version}/...  (for rpm/docker)
            #   * {omd_version}/...  (for cma)
            path.removeprefix("/")
            .removeprefix(f"opt/omd/versions/{omd_version}/")
            .removeprefix(f"{omd_version}/")
            for path in paths
            if _should_be_signed(path)
        ]
        LOGGER.debug("Found %d signable files: %s", len(paths_signable), paths_signable)
        LOGGER.debug("Checked %d files: %s", len(paths_checked), paths_checked)

        paths_unchecked = sorted(set(paths_signable) - set(paths_checked))
        if paths_unchecked:
            LOGGER.warning("Found %d unchecked files:", len(paths_unchecked))
            for p in paths_unchecked:
                LOGGER.warning("  - %s", p)
            # note: we're not checking whether those files are actually signed or not,
            #       just whether we forgot to include them in this test
            raise AssertionError(f"Found {len(paths_unchecked)} unchecked files: {paths_unchecked}")
        else:
            LOGGER.info("PASS: No further signable files* found (excluding ignored).")

    assert not any(signing_failures)
