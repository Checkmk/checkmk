#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import re
import subprocess

import pytest

LOGGER = logging.getLogger()


def _get_omd_version(cmk_version, package_path):
    # Extract the files edition
    edition_short = _edition_short_from_pkg_path(package_path)
    return "%s.%s" % (cmk_version, edition_short)


def _is_demo(package_path):
    return _edition_short_from_pkg_path(package_path) == "cfe"


def _edition_short_from_pkg_path(package_path):
    file_name = os.path.basename(package_path)
    if file_name.startswith("check-mk-raw-"):
        return "cre"
    if file_name.startswith("check-mk-enterprise-"):
        return "cee"
    if file_name.startswith("check-mk-managed-"):
        return "cme"
    if file_name.startswith("check-mk-free-"):
        return "cfe"
    if file_name.startswith("check-mk-plus-"):
        return "cpe"
    raise NotImplementedError("Could not get edition from package path: %s" % package_path)


def _get_file_from_package(package_path, cmk_version, version_rel_path):
    omd_version = _get_omd_version(cmk_version, package_path)

    if package_path.endswith(".rpm"):
        rpm2cpio = subprocess.run(["rpm2cpio", package_path], stdout=subprocess.PIPE, check=False)
        return subprocess.check_output(
            [
                "cpio",
                "-i",
                "--quiet",
                "--to-stdout",
                "./opt/omd/versions/%s/%s" % (omd_version, version_rel_path),
            ],
            input=rpm2cpio.stdout,
        )

    if package_path.endswith(".deb"):
        return subprocess.check_output(
            ["tar", "xOf", "-", "./opt/omd/versions/%s/%s" % (omd_version, version_rel_path)],
            input=subprocess.run(
                ["dpkg", "--fsys-tarfile", package_path], stdout=subprocess.PIPE, check=False
            ).stdout,
        )

    if package_path.endswith(".cma"):
        return subprocess.check_output(
            ["tar", "xOzf", package_path, "%s/%s" % (omd_version, version_rel_path)]
        )

    if package_path.endswith(".tar.gz"):
        raise NotImplementedError()

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
def test_package_sizes(package_path, pkg_format, min_size, max_size):
    if not package_path.endswith(".%s" % pkg_format):
        pytest.skip("%s is another package type" % os.path.basename(package_path))

    if not os.path.basename(package_path).startswith("check-mk-enterprise-"):
        pytest.skip("only testing enterprise packages")

    size = os.stat(package_path).st_size
    assert min_size <= size <= max_size, "Package %s size %s not between %s and %s bytes." % (
        package_path,
        size,
        min_size,
        max_size,
    )


def test_files_not_in_version_path(package_path, cmk_version):
    if not package_path.endswith(".rpm") and not package_path.endswith(".deb"):
        pytest.skip("%s is another package type" % os.path.basename(package_path))

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
            "/usr/share/doc/check-mk-(raw|free|enterprise|managed|plus)-.*/$",
            "/usr/share/doc/check-mk-(raw|free|enterprise|managed|plus)-.*/changelog.gz$",
            "/usr/share/doc/check-mk-(raw|free|enterprise|managed|plus)-.*/COPYING.gz$",
            "/usr/share/doc/check-mk-(raw|free|enterprise|managed|plus)-.*/TEAM$",
            "/usr/share/doc/check-mk-(raw|free|enterprise|managed|plus)-.*/copyright$",
            "/usr/share/doc/check-mk-(raw|free|enterprise|managed|plus)-.*/README.md$",
            "/etc/$",
            "/etc/init.d/$",
            "/etc/init.d/check-mk-(raw|free|enterprise|managed|plus)-.*$",
        ] + version_allowed_patterns

        paths = []
        for line in subprocess.check_output(
            ["dpkg", "-c", package_path], encoding="utf-8"
        ).splitlines():
            paths.append(line.split()[5].lstrip("."))
    else:
        raise NotImplementedError()

    LOGGER.info("Testing %s", package_path)

    omd_version = _get_omd_version(cmk_version, package_path)
    LOGGER.info("Checking OMD version: %s", omd_version)

    for path in paths:
        is_allowed = any(
            re.match(p.replace("###OMD_VERSION###", omd_version), path) for p in allowed_patterns
        )
        assert is_allowed, "Found unexpected global file: %s in %s" % (path, package_path)


def test_cma_only_contains_version_paths(package_path, cmk_version):
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


def test_cma_specific_files(package_path, cmk_version):
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
    if _is_demo(package_path):
        assert "DEMO=1" in cma_info
    else:
        assert "DEMO=1" not in cma_info


def test_src_only_contains_relative_version_paths(package_path):
    if not package_path.endswith(".tar.gz"):
        pytest.skip("%s is not a source package" % os.path.basename(package_path))

    prefix = os.path.basename(package_path).replace(".tar.gz", "")
    for line in subprocess.check_output(
        ["tar", "tvf", package_path], encoding="utf-8"
    ).splitlines():
        path = line.split()[5]
        assert path.startswith(prefix + "/")


def test_src_not_contains_enterprise_sources(package_path):
    if not package_path.endswith(".tar.gz"):
        pytest.skip("%s is not a source package" % os.path.basename(package_path))

    prefix = os.path.basename(package_path).replace(".tar.gz", "")
    enterprise_files = []
    managed_files = []
    plus_files = []

    for line in subprocess.check_output(
        ["tar", "tvf", package_path], encoding="utf-8"
    ).splitlines():
        path = line.split()[5]
        if path != "%s/enterprise/" % prefix and path.startswith("%s/enterprise/" % prefix):
            enterprise_files.append(path)
        if path != "%s/managed/" % prefix and path.startswith("%s/managed/" % prefix):
            managed_files.append(path)
        if path != "%s/plus/" % prefix and path.startswith("%s/plus/" % prefix):
            plus_files.append(path)

    assert enterprise_files == []
    assert managed_files == []
    assert plus_files == []


def test_demo_modifications(package_path, cmk_version):
    if package_path.endswith(".tar.gz"):
        pytest.skip("%s do not test source packages" % os.path.basename(package_path))

    if _edition_short_from_pkg_path(package_path) != "cre":
        cmc_bin = _get_file_from_package(package_path, cmk_version, version_rel_path="bin/cmc")
        if _is_demo(package_path):
            assert b"THIS IS A DEMO" in cmc_bin
        else:
            assert b"THIS IS A DEMO" not in cmc_bin

    nagios_bin = _get_file_from_package(package_path, cmk_version, version_rel_path="bin/nagios")
    if _is_demo(package_path):
        assert b"in this demo" in nagios_bin
    else:
        assert b"in this demo" not in nagios_bin
