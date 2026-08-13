#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import atexit
import logging
import os
import re
import subprocess
from collections import Counter
from functools import cache
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
        return list(
            subprocess.check_output(["tar", "tzf", path_to_package], encoding="utf-8").splitlines()
        )

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
    re.compile(r".*/share/check_mk/agents/windows/rcc.exe$"),
    re.compile(r".*/share/check_mk/agents/windows/robotmk_scheduler.exe$"),
    # -- dll files --
]
FILE_PATTERNS_SIGNABLE = [
    re.compile(r".*\.exe$"),
    re.compile(r".*\.dll$"),
    re.compile(r".*\.msi$"),
]

# signable files expected inside check_mk_agent.msi (paths as installed by msiexec);
# additions are verified automatically, but must be acknowledged here. CMK-37147
# check_mk_svc32.exe/check_mk_svc64.exe are the File table identifiers of the two
# service binaries: both install as check_mk_agent.exe (selected by the VersionNT64
# condition), so they are extracted under their identifier - see
# _msi_signable_file_names - to get both signatures verified.
MSI_EMBEDDED_SIGNED_FILES = (
    "Program Files/checkmk/service/check_mk_svc32.exe",
    "Program Files/checkmk/service/check_mk_svc64.exe",
    "Program Files/checkmk/service/cmk-agent-ctl.exe",
)


def _should_be_signed(path: str) -> bool:
    if not any(pattern.match(path) for pattern in FILE_PATTERNS_SIGNABLE):
        return False
    if any(pattern.match(path) for pattern in FILES_UNSIGNED):
        return False
    return True


def _msi_signable_file_names(msi_path: Path) -> list[str]:
    """Signable File table entries of an MSI, one name per row, made extractable.

    The FileName column is `8.3|long` - keep the long variant. The MSI may
    install several File table rows under the same target name (here:
    check_mk_svc32.exe/check_mk_svc64.exe both install as check_mk_agent.exe,
    selected by the VersionNT64 condition), which msiextract silently collapses
    into a single file, leaving all but one of them unverified. Rename such
    rows to their unique File identifier (SQL UPDATE on the extraction copy)
    so every row is extracted - and signature-verified - separately.

    Such duplicates only exist on branches <= 2.4.0 (2.5.0 ships a single
    combined service binary); there the renaming is simply a no-op.
    """
    table = subprocess.check_output(["msiinfo", "export", str(msi_path), "File"], text=True)
    rows = [
        (columns[0], columns[2].split("|")[-1])
        for line in table.splitlines()
        if len(columns := line.split("\t")) >= 3
    ]
    name_counts = Counter(name for _, name in rows)
    signable_names = []
    for file_id, file_name in rows:
        if not any(pattern.match(file_name) for pattern in FILE_PATTERNS_SIGNABLE):
            continue
        if name_counts[file_name] == 1:
            signable_names.append(file_name)
            continue
        assert any(pattern.match(file_id) for pattern in FILE_PATTERNS_SIGNABLE), (
            f"File table row '{file_id}' shares its target name '{file_name}' with "
            "another row, but its identifier does not look signable - extracting it "
            "under that identifier would skip its signature verification"
        )
        subprocess.check_call(
            [
                "msibuild",
                str(msi_path),
                "-q",
                f"UPDATE `File` SET `FileName` = '{file_id}' WHERE `File` = '{file_id}'",  # nosec B608 # BNS:fa3c6c
            ]
        )
        signable_names.append(file_id)
    return sorted(signable_names)


_TRUSTED_ROOTS_DIR = Path(__file__).parent / "certs"


@cache
def _signing_ca_bundle() -> str:
    """Return a CA bundle trusting every Windows signing path we produce.

    Built purely from the roots committed under certs/, so signature verification does not
    depend on the CI image's CA store (osslsigncode's -CAfile replaces the default trust
    store anyway):
      - Comodo AAA Certificate Services              -> YubiKey/Sectigo code signing
      - USERTrust RSA Certification Authority        -> Sectigo timestamp chain
      - Microsoft Identity Verification Root CA 2020 -> Azure Trusted Signing
                                                        (code signing + timestamp)
    The same bundle serves -TSA-CAfile too, since it covers the timestamp chains.
    """
    roots = sorted(_TRUSTED_ROOTS_DIR.glob("*.pem"))
    if not roots:
        raise RuntimeError(f"No trusted roots committed under {_TRUSTED_ROOTS_DIR}")
    parts = [root.read_text() for root in roots]

    with NamedTemporaryFile(
        mode="w", prefix="cmk-signing-ca-", suffix=".pem", delete=False
    ) as bundle:
        bundle.write("\n".join(parts))
        bundle_path = bundle.name
    atexit.register(lambda: Path(bundle_path).unlink(missing_ok=True))
    return bundle_path


def _verify_signature(file_path: Path, file_name: str) -> None | str:
    try:
        assert file_path.exists(), f"File to verify does not exist: {file_path}"
        bundle = _signing_ca_bundle()
        # requires to build osslsigncode via bazel (or install locally) beforehand:
        #   export PATH=$$PATH:$$(bazel run //bazel/tools:bazel_env print-path)
        # (see tests/Makefile -> tests-packaging)
        result = subprocess.run(
            [
                "osslsigncode",
                "verify",
                "-ignore-cdp",
                "-ignore-crl",
                "-CAfile",
                bundle,
                "-TSA-CAfile",
                bundle,
                file_path,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        # osslsigncode not found - it should be available in CI (via test-packaging Makefile target)
        # -> should only occur in local test environments
        logger.error("osslsigncode not found in PATH")
        if os.environ.get("CI"):
            logger.error("THIS SHOULD NOT HAPPEN in CI! PLEASE REPORT!")
        else:
            logger.warning("Please build it locally via bazel (and add it to your PATH), e.g.:")
            logger.warning(
                "  bazel: export PATH=$PATH:$(bazel run //bazel/tools:bazel_env print-path)"
            )
        raise
    logger.info(
        "Signature verification of '%s': %s - %s",
        file_name,
        "PASS" if result.returncode == 0 else "FAIL",
        result.stderr.strip(),
    )
    if result.returncode != 0:
        return f"{file_name}: " + result.stderr
    return None


@pytest.mark.parametrize(
    "is_no_tar,path_prefix_agents,non_msi_files",
    [
        (
            True,
            "share/check_mk/agents/windows",
            [
                "share/check_mk/agents/windows/mk-sql.exe",
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
    ids=["deb_rpm_cma", "tar_gz_source"],
)
def test_windows_artifacts_are_signed(
    package_path: str,
    cmk_version: str,
    is_no_tar: bool,
    path_prefix_agents: str,
    non_msi_files: list[str],
) -> None:
    # Skip mismatched package types
    actual_is_no_tar = not package_path.endswith(".tar.gz")
    if actual_is_no_tar != is_no_tar:
        expected_ext = ".deb/.rpm/.cma" if is_no_tar else ".tar.gz"
        actual_ext = os.path.splitext(package_path)[1]
        pytest.skip(f"Package type mismatch: expected '{expected_ext}' but got '{actual_ext}'")

    if package_path.endswith(".tar.gz") and "-docker-" in package_path:
        # todo: implement test for docker images, e.g. in tests/docker/test_docker.py - CMK-26808
        pytest.skip("Can't verify signatures in docker OCI images")

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
    if is_no_tar:
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
            # after the MSI's own signature is verified: rename colliding File table
            # rows in the temporary copy so msiextract writes every signable row
            # (duplicates only exist on branches <= 2.4.0)
            msi_table_names = _msi_signable_file_names(Path(msi_file.name))
            with TemporaryDirectory() as msi_content:
                try:
                    subprocess.run(
                        ["msiextract", "-C", msi_content, msi_file.name],
                        check=False,
                        stdout=subprocess.DEVNULL,
                    )
                except FileNotFoundError:
                    logger.error("msiextract not found in PATH")
                    logger.error("IF IN CI - THIS SHOULD NOT HAPPEN! PLEASE REPORT!")
                    logger.warning("can be installed locally")
                    logger.warning("  ubuntu: sudo apt install msitools")
                    raise
                extracted_signable = sorted(
                    path
                    for path in Path(msi_content).rglob("*")
                    if path.is_file() and _should_be_signed(str(path))
                )
                for extracted_file in extracted_signable:
                    signing_failures.append(
                        _verify_signature(
                            extracted_file,
                            f"check_mk_agent.msi/{extracted_file.relative_to(msi_content)}",
                        )
                    )
                extracted_names = sorted(
                    str(path.relative_to(msi_content)) for path in extracted_signable
                )
                assert extracted_names == sorted(MSI_EMBEDDED_SIGNED_FILES), (
                    "Signable files inside check_mk_agent.msi changed - if intended, "
                    f"update MSI_EMBEDDED_SIGNED_FILES. Found: {extracted_names}"
                )
                # One extracted file per signable File table row - catches rows
                # that still collapse or get lost on extraction.
                assert msi_table_names == sorted(path.name for path in extracted_signable), (
                    "File table of check_mk_agent.msi does not match the extracted "
                    f"files - signable entries were collapsed or lost: {msi_table_names}"
                )

    # check for additional files in the package
    # (so we don't forget to add them to the signing process)
    if is_no_tar:
        paths = _get_paths_from_package(package_path)
        omd_version = _get_omd_version(cmk_version, package_path)
        paths_signable = [
            # remove prefixes of paths to make it comparable
            #   * /opt/omd/versions/{omd_version}/...
            #   * {omd_version}/...  (for cma)
            path.removeprefix(f"/opt/omd/versions/{omd_version}/").removeprefix(f"{omd_version}/")
            for path in paths
            if _should_be_signed(path)
        ]
        logger.debug("Found %d signable files: %s", len(paths_signable), paths_signable)
        logger.debug("Checked %d files: %s", len(paths_checked), paths_checked)

        paths_unchecked = sorted(set(paths_signable) - set(paths_checked))
        if paths_unchecked:
            logger.warning("Found %d unchecked files:", len(paths_unchecked))
            for p in paths_unchecked:
                logger.warning("  - %s", p)
            # note: we're not checking whether those files are actually signed or not,
            #       just whether we forgot to include them in this test
            raise AssertionError(f"Found {len(paths_unchecked)} unchecked files: {paths_unchecked}")
        logger.info("PASS: No further signable files* found (excluding ignored).")

    assert not any(signing_failures)


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
        for suffix in (".py", "_2.py"):
            filename = f"{prefix}{suffix}"
            assert _file_exists_in_package(
                package_path, cmk_version, f"share/check_mk/agents/plugins/{filename}"
            ), f"File {filename} is missing in {package_path}"
