#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import logging
import os
import re
import subprocess
from pathlib import Path

import pytest
import requests
import requests.exceptions

import tests.testlib as testlib
from tests.testlib.utils import (
    cmk_path,
    get_cmk_download_credentials,
    get_cmk_download_credentials_file,
)

import docker  # type: ignore[import]

build_path = os.path.join(testlib.repo_path(), "docker")
image_prefix = "docker-tests"
branch_name = os.environ.get("BRANCH", "master")

logger = logging.getLogger()


def build_version():
    return testlib.CMKVersion(
        version_spec=os.environ.get("VERSION", testlib.CMKVersion.DAILY),
        edition=os.environ.get("EDITION", testlib.CMKVersion.CEE),
        branch=branch_name,
    )


@pytest.fixture(scope="session")
def version():
    return build_version()


@pytest.fixture()
def client():
    return docker.DockerClient()


def _image_name(version):
    return "docker-tests/check-mk-%s-%s-%s" % (version.edition(), branch_name, version.version)


def _package_name(version: testlib.CMKVersion) -> str:
    return f"check-mk-{version.edition()}-{version.version}_0.buster_amd64.deb"


def _prepare_build():
    assert subprocess.run(["make", "needed-packages"], cwd=build_path, check=False).returncode == 0


def _prepare_package(version: testlib.CMKVersion):
    """On Jenkins copies a previously built package to the build path."""
    if "WORKSPACE" not in os.environ:
        logger.info("Not executed on CI: Do not prepare a Checkmk .deb in %s", build_path)
        return

    source_package_path = Path(
        os.environ["WORKSPACE"], "packages", version.version, _package_name(version)
    )
    test_package_path = Path(build_path, _package_name(version))

    logger.info("Executed on CI: Preparing package %s", test_package_path)

    if (
        test_package_path.exists()
        and test_package_path.stat().st_mtime >= source_package_path.stat().st_mtime
    ):
        logger.info("File already exists - Fine")
        return

    _cleanup_old_packages()

    logger.info("Copying from %s", source_package_path)
    test_package_path.write_bytes(source_package_path.read_bytes())


def _cleanup_old_packages() -> None:
    """Cleanup files created by _prepare_package during previous job executions"""
    for p in Path(build_path).glob("*.deb"):
        logger.info("Cleaning up old package %s", p)
        p.unlink()


def resolve_image_alias(alias):
    """Resolves given "Docker image alias" using the common `resolve.sh` and returns an image
    name which can be used with `docker run`
    >>> image = resolve_image_alias("IMAGE_CMK_BASE")
    >>> assert image and isinstance(image, str)
    """
    return subprocess.check_output(
        [os.path.join(cmk_path(), "buildscripts/docker_image_aliases/resolve.sh"), alias],
        universal_newlines=True,
    ).split("\n", maxsplit=1)[0]


def _build(request, client, version, prepare_package=True):
    _prepare_build()

    if prepare_package:
        _prepare_package(version)

    logger.info("Starting helper container for build secrets")
    secret_container = client.containers.run(
        image="busybox",
        command=["timeout", "180", "httpd", "-f", "-p", "8000", "-h", "/files"],
        detach=True,
        remove=True,
        volumes={get_cmk_download_credentials_file(): {"bind": "/files/secret", "mode": "ro"}},
    )
    request.addfinalizer(lambda: secret_container.remove(force=True))

    logger.info("Building docker image (or reuse existing): %s", _image_name(version))
    try:
        image, build_logs = client.images.build(
            path=build_path,
            tag=_image_name(version),
            network_mode="container:%s" % secret_container.id,
            buildargs={
                "CMK_VERSION": version.version,
                "CMK_EDITION": version.edition(),
                "CMK_DL_CREDENTIALS": ":".join(get_cmk_download_credentials()),
                "IMAGE_CMK_BASE": resolve_image_alias("IMAGE_CMK_BASE"),
            },
        )
    except docker.errors.BuildError as e:
        logger.error("= Build log ==================")
        for entry in e.build_log:
            if "stream" in entry:
                logger.error(entry["stream"])
            elif "errorDetail" in entry:
                continue  # Is already part of the exception message
            else:
                logger.error("UNEXPECTED FORMAT: %r", entry)
        logger.error("= Build log ==================")
        raise

    logger.info("(Set pytest log level to DEBUG (--log-cli-level=DEBUG) to see the build log)")
    for entry in build_logs:
        if "stream" in entry:
            logger.debug(entry["stream"].rstrip())
        elif "aux" in entry:
            logger.debug(entry["aux"])
        else:
            logger.debug("UNEXPECTED FORMAT: %r", entry)
    logger.debug("= Build log ==================")

    # TODO: Enable this on CI system. Removing during development slows down testing
    # request.addfinalizer(lambda: client.images.remove(image.id, force=True))

    logger.info("Built image: %s", image.short_id)
    attrs = image.attrs
    config = attrs["Config"]

    assert config["Labels"] == {
        "org.opencontainers.image.vendor": "tribe29 GmbH",
        "org.opencontainers.image.version": version.version,
        "maintainer": "feedback@checkmk.com",
        "org.opencontainers.image.description": "Checkmk is a leading tool for Infrastructure & Application Monitoring",
        "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",
        "org.opencontainers.image.title": "Checkmk",
        "org.opencontainers.image.url": "https://checkmk.com/",
    }

    assert config["Env"] == [
        "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "CMK_SITE_ID=cmk",
        "CMK_LIVESTATUS_TCP=",
        "CMK_PASSWORD=",
        "MAIL_RELAY_HOST=",
    ]

    assert "Healthcheck" in config

    assert attrs["ContainerConfig"]["Entrypoint"] == ["/docker-entrypoint.sh"]

    assert attrs["ContainerConfig"]["ExposedPorts"] == {
        "5000/tcp": {},
        "6557/tcp": {},
    }

    # 2018-11-14: 900 -> 920
    # 2018-11-22: 920 -> 940
    # 2019-04-10: 940 -> 950
    # 2019-07-12: 950 -> 1040 (python3)
    # 2019-07-27: 1040 -> 1054 (numpy)
    # 2019-11-15: Temporarily disabled because of Python2 => Python3 transition
    #    assert attrs["Size"] < 1110955410.0, \
    #        "Docker image size increased: Please verify that this is intended"

    assert len(attrs["RootFS"]["Layers"]) == 6

    return image, build_logs


def _pull(client, version):
    if version.edition() != "raw":
        raise Exception("Can only fetch raw edition at the moment")

    logger.info("Downloading docker image: checkmk/check-mk-raw:%s", version.version)
    return client.images.pull("checkmk/check-mk-raw", tag=version.version)


def _start(request, client, version=None, is_update=False, **kwargs):
    if version is None:
        version = build_version()

    try:
        if version.version == build_version().version:
            _image, _build_logs = _build(request, client, version)
        else:
            # In case the given version is not the current branch version, don't
            # try to build it. Download it instead!
            _image = _pull(client, version)
    except requests.exceptions.ConnectionError as e:
        raise Exception(
            "Failed to access docker socket (Permission denied). You need to be member of the "
            'docker group to get access to the socket (e.g. use "make -C docker setup") to '
            "fix this, then restart your computer and try again."
        ) from e

    c = client.containers.run(image=_image.id, detach=True, **kwargs)
    logger.info("Starting container %s from image %s", c.short_id, _image.short_id)

    try:
        site_id = kwargs.get("environment", {}).get("CMK_SITE_ID", "cmk")

        request.addfinalizer(lambda: c.remove(force=True))

        testlib.wait_until(lambda: "### CONTAINER STARTED" in c.logs().decode("utf-8"), timeout=120)
        output = c.logs().decode("utf-8")

        if not is_update:
            assert "Created new site" in output
            assert "cmkadmin with password:" in output
        else:
            assert "Created new site" not in output
            assert "cmkadmin with password:" not in output

        assert "STARTING SITE" in output

        exit_code, status_output = _exec_run(c, ["omd", "status"], user=site_id)
        assert exit_code == 0, f"Status is {exit_code}. Output: {status_output}"
    finally:
        logger.debug("Log so far: %s", c.logs().decode("utf-8"))

    return c


def _exec_run(c, *args, **kwargs):
    exit_code, output = c.exec_run(*args, **kwargs)
    return exit_code, output.decode("utf-8")


def test_start_simple(request, client, version) -> None:
    c = _start(request, client)

    cmds = [p[-1] for p in c.top()["Processes"]]
    assert "cron -f" in cmds

    # Check postfix / syslog not runnig by default
    assert "syslogd" not in cmds
    assert "/usr/lib/postfix/sbin/master" not in cmds

    # Check omd standard config
    exit_code, output = _exec_run(c, ["omd", "config", "show"], user="cmk")
    assert "TMPFS: off" in output
    assert "APACHE_TCP_ADDR: 0.0.0.0" in output
    assert "APACHE_TCP_PORT: 5000" in output
    assert "MKEVENTD: on" in output

    if version.is_raw_edition():
        assert "CORE: nagios" in output
    else:
        assert "CORE: cmc" in output

    # check sites uid/gid
    assert _exec_run(c, ["id", "-u", "cmk"])[1].rstrip() == "1000"
    assert _exec_run(c, ["id", "-g", "cmk"])[1].rstrip() == "1000"

    assert exit_code == 0


def test_start_cmkadmin_passsword(request, client) -> None:
    c = _start(
        request,
        client,
        environment={
            "CMK_PASSWORD": "blabla",
        },
    )

    assert (
        _exec_run(c, ["htpasswd", "-vb", "/omd/sites/cmk/etc/htpasswd", "cmkadmin", "blabla"])[0]
        == 0
    )

    assert (
        _exec_run(c, ["htpasswd", "-vb", "/omd/sites/cmk/etc/htpasswd", "cmkadmin", "blub"])[0] == 3
    )


def test_start_custom_site_id(request, client) -> None:
    c = _start(
        request,
        client,
        environment={
            "CMK_SITE_ID": "xyz",
        },
    )

    assert _exec_run(c, ["omd", "status"], user="xyz")[0] == 0


def test_start_enable_livestatus(request, client) -> None:
    c = _start(
        request,
        client,
        environment={
            "CMK_LIVESTATUS_TCP": "on",
        },
    )

    exit_code, output = _exec_run(c, ["omd", "config", "show", "LIVESTATUS_TCP"], user="cmk")
    assert exit_code == 0
    assert output == "on\n"


def test_start_execute_custom_command(request, client) -> None:
    c = _start(request, client)

    exit_code, output = _exec_run(c, ["echo", "1"], user="cmk")
    assert exit_code == 0
    assert output == "1\n"


def test_start_with_custom_command(request, client, version) -> None:
    image, _build_logs = _build(request, client, version)
    output = client.containers.run(
        image=image.id, detach=False, command=["bash", "-c", "echo 1"]
    ).decode("utf-8")

    assert "Created new site" in output
    assert output.endswith("1\n")


# Test that the local deb package is used by making the build fail because of an empty file
def test_build_using_local_deb(request, client, version) -> None:
    package_path = Path(build_path, _package_name(version))
    package_path.write_bytes(b"")
    with pytest.raises(docker.errors.BuildError):
        _build(request, client, version, prepare_package=False)
    os.unlink(str(package_path))
    _prepare_package(version)


# Test that the deb package from the download server is used.
# Works only with daily enterprise builds.
def test_build_using_package_from_download_server(request, client, version) -> None:
    if not (
        version.edition() == "enterprise" and re.match(r"^\d\d\d\d\.\d\d\.\d\d$", version.version)
    ):
        pytest.skip("only enterprise daily packages are available on the download server")
    package_path = Path(build_path, _package_name(version))
    # make sure no local package is used.
    if package_path.exists():
        os.unlink(str(package_path))
    _build(request, client, version, prepare_package=False)


# Test that the local GPG file is used by making the build fail because of an empty file
def test_build_using_local_gpg_pubkey(request, client, version) -> None:
    pkg_path = os.path.join(build_path, "Check_MK-pubkey.gpg")
    pkg_path_sav = os.path.join(build_path, "Check_MK-pubkey.gpg.sav")
    try:
        os.rename(pkg_path, pkg_path_sav)

        with open(pkg_path, "w") as f:
            f.write("")

        with pytest.raises(docker.errors.BuildError):
            _build(request, client, version)
    finally:
        os.unlink(pkg_path)
        os.rename(pkg_path_sav, pkg_path)


def test_start_enable_mail(request, client) -> None:
    c = _start(
        request,
        client,
        environment={
            "MAIL_RELAY_HOST": "mailrelay.mydomain.com",
        },
        hostname="myhost.mydomain.com",
    )

    cmds = [p[-1] for p in c.top()["Processes"]]

    assert "syslogd" in cmds
    assert "/usr/lib/postfix/sbin/master" in cmds

    assert _exec_run(c, ["which", "mail"], user="cmk")[0] == 0

    assert _exec_run(c, ["postconf", "myorigin"])[1].rstrip() == "myorigin = myhost.mydomain.com"
    assert (
        _exec_run(c, ["postconf", "relayhost"])[1].rstrip() == "relayhost = mailrelay.mydomain.com"
    )


def test_http_access_base_redirects_work(request, client) -> None:
    c = _start(request, client)

    assert (
        "Location: http://127.0.0.1:5000/cmk/\r\n"
        in _exec_run(c, ["curl", "-D", "-", "-s", "http://127.0.0.1:5000"])[-1]
    )
    assert (
        "Location: http://127.0.0.1:5000/cmk/\r\n"
        in _exec_run(c, ["curl", "-D", "-", "-s", "http://127.0.0.1:5000/"])[-1]
    )
    assert (
        "Location: http://127.0.0.1:5000/cmk/check_mk/\r\n"
        in _exec_run(c, ["curl", "-D", "-", "-s", "http://127.0.0.1:5000/cmk"])[-1]
    )
    assert (
        "Location: /cmk/check_mk/login.py?_origtarget=index.py\r\n"
        in _exec_run(c, ["curl", "-D", "-", "http://127.0.0.1:5000/cmk/check_mk/"])[-1]
    )


# Would like to test this from the outside of the container, but this is not possible
# because most of our systems already have something listening on port 80
def test_redirects_work_with_standard_port(request, client) -> None:
    c = _start(request, client)

    # Use no explicit port
    assert (
        "Location: http://127.0.0.1/cmk/\r\n"
        in _exec_run(
            c,
            [
                "curl",
                "-D",
                "-",
                "-s",
                "--connect-to",
                "127.0.0.1:80:127.0.0.1:5000",
                "http://127.0.0.1",
            ],
        )[-1]
    )

    # Use explicit standard port
    assert (
        "Location: http://127.0.0.1/cmk/\r\n"
        in _exec_run(
            c,
            [
                "curl",
                "-D",
                "-",
                "-s",
                "--connect-to",
                "127.0.0.1:80:127.0.0.1:5000",
                "http://127.0.0.1:80",
            ],
        )[-1]
    )

    # Use explicit host header with standard port
    assert (
        "Location: http://127.0.0.1/cmk/\r\n"
        in _exec_run(
            c,
            [
                "curl",
                "-D",
                "-",
                "-s",
                "-H",
                "Host: 127.0.0.1:80",
                "--connect-to",
                "127.0.0.1:80:127.0.0.1:5000",
                "http://127.0.0.1",
            ],
        )[-1]
    )


def test_redirects_work_with_custom_port(request, client) -> None:
    # Use some free address port to be able to bind to. For the moment there is no
    # conflict with others, since this test is executed only once at the same time.
    # TODO: We'll have to use some branch specific port in the future.
    address = ("127.3.3.7", 8555)
    address_txt = ":".join(map(str, address))

    _start(
        request,
        client,
        ports={
            "5000/tcp": address,
        },
    )

    # Use explicit port
    response = requests.get("http://%s" % address_txt, allow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "http://%s/cmk/" % address_txt

    # Use explicit port and host header with port
    response = requests.get(
        "http://%s" % address_txt,
        allow_redirects=False,
        headers={
            "Host": address_txt,
        },
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "http://%s/cmk/" % address_txt

    # Use explicit port and host header without port
    response = requests.get(
        "http://%s" % address_txt,
        allow_redirects=False,
        headers={
            "Host": address[0],
        },
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "http://%s/cmk/" % address[0]


def test_http_access_login_screen(request, client) -> None:
    c = _start(request, client)

    assert (
        "Location: \r\n"
        not in _exec_run(
            c,
            ["curl", "-D", "-", "http://127.0.0.1:5000/cmk/check_mk/login.py?_origtarget=index.py"],
        )[-1]
    )
    assert (
        'name="_login"'
        in _exec_run(
            c,
            ["curl", "-D", "-", "http://127.0.0.1:5000/cmk/check_mk/login.py?_origtarget=index.py"],
        )[-1]
    )


def test_container_agent(request, client) -> None:
    c = _start(request, client)
    # Is the agent installed and executable?
    assert _exec_run(c, ["check_mk_agent"])[-1].startswith("<<<check_mk>>>\n")

    # Check whether or not the agent port is opened
    assert ":::6556" in _exec_run(c, ["netstat", "-tln"])[-1]


def test_update(request, client, version) -> None:
    container_name = "%s-monitoring" % branch_name

    # Pick a random old version that we can use to the setup the initial site with
    # Later this site is being updated to the current daily build
    old_version = testlib.CMKVersion(
        version_spec="2.1.0b3",
        branch="2.1.0",
        edition=testlib.CMKVersion.CRE,
    )

    # 1. create container with old version and add a file to mark the pre-update state
    c_orig = _start(
        request, client, version=old_version, name=container_name, volumes=["/omd/sites"]
    )
    assert (
        c_orig.exec_run(["touch", "pre-update-marker"], user="cmk", workdir="/omd/sites/cmk")[0]
        == 0
    )

    # 2. stop the container
    c_orig.stop()

    # 3. rename old container
    c_orig.rename("%s-old" % container_name)

    # 4. create new container
    c_new = _start(
        request,
        client,
        version=version,
        is_update=True,
        name=container_name,
        volumes_from=c_orig.id,
    )

    # 5. verify result
    _exec_run(c_new, ["omd", "version"], user="cmk")[1].endswith("%s\n" % version.omd_version())
    assert (
        _exec_run(c_new, ["test", "-f", "pre-update-marker"], user="cmk", workdir="/omd/sites/cmk")[
            0
        ]
        == 0
    )


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    import doctest

    assert not doctest.testmod().failed
    pytest.main(["-T=docker", "-vvsx", __file__])
