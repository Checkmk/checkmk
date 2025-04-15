#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import logging
import os
from pathlib import Path
from random import randint

import docker  # type: ignore[import]
import pytest
import requests
from pytest import LogCaptureFixture

from tests.testlib.docker import (
    build_checkmk,
    build_path,
    get_container_ip,
    package_name,
    prepare_package,
    start_checkmk,
)
from tests.testlib.version import CMKVersion, version_from_env

from cmk.utils.version import Edition, Version, versions_compatible, VersionsCompatible

logger = logging.getLogger()

old_version = CMKVersion(
    version_spec="2.2.0p8", edition=Edition.CRE, branch="2.2.0", branch_version="2.2.0"
)


def test_start_simple(checkmk: docker.models.containers.Container, version: CMKVersion) -> None:
    cmds = [p[-1] for p in checkmk.top()["Processes"]]
    assert "cron -f" in cmds

    # Check postfix / syslog not runnig by default
    assert "syslogd" not in cmds
    assert "/usr/lib/postfix/sbin/master" not in cmds

    # Check omd standard config
    exit_code, output_bytes = checkmk.exec_run(["omd", "config", "show"], user="cmk")
    output = output_bytes.decode("utf-8")
    assert "TMPFS: off" in output
    assert "APACHE_TCP_ADDR: 0.0.0.0" in output
    assert "APACHE_TCP_PORT: 5000" in output
    assert "MKEVENTD: on" in output

    if version.is_raw_edition():
        assert "CORE: nagios" in output
    else:
        assert "CORE: cmc" in output

    # check sites uid/gid
    assert checkmk.exec_run(["id", "-u", "cmk"])[1].decode("utf-8").rstrip() == "1000"
    assert checkmk.exec_run(["id", "-g", "cmk"])[1].decode("utf-8").rstrip() == "1000"

    assert exit_code == 0


def test_needed_packages(checkmk: docker.models.containers.Container) -> None:
    """Ensure that important tools can be executed in the container"""
    assert checkmk.exec_run(["logrotate", "--version"])[0] == 0


def test_start_cmkadmin_password(client: docker.DockerClient) -> None:
    with start_checkmk(
        client,
        environment={
            "CMK_PASSWORD": "blabla",
        },
    ) as c:
        assert (
            c.exec_run(["htpasswd", "-vb", "/omd/sites/cmk/etc/htpasswd", "cmkadmin", "blabla"])[0]
            == 0
        )
        assert (
            c.exec_run(["htpasswd", "-vb", "/omd/sites/cmk/etc/htpasswd", "cmkadmin", "blub"])[0]
            == 3
        )


def test_start_custom_site_id(client: docker.DockerClient) -> None:
    with start_checkmk(
        client,
        environment={
            "CMK_SITE_ID": "xyz",
        },
    ) as c:
        assert c.exec_run(["omd", "status"], user="xyz")[0] == 0


def test_start_enable_livestatus(client: docker.DockerClient) -> None:
    with start_checkmk(
        client,
        environment={
            "CMK_LIVESTATUS_TCP": "on",
        },
    ) as c:
        exit_code, output_bytes = c.exec_run(
            ["omd", "config", "show", "LIVESTATUS_TCP"], user="cmk"
        )
        assert exit_code == 0
        assert output_bytes.decode("utf-8") == "on\n"


def test_start_execute_custom_command(
    checkmk: docker.models.containers.Container,
) -> None:
    exit_code, output_bytes = checkmk.exec_run(["echo", "1"], user="cmk")
    assert exit_code == 0
    assert output_bytes.decode("utf-8") == "1\n"


def test_start_with_custom_command(client: docker.DockerClient, version: CMKVersion) -> None:
    image, _build_logs = build_checkmk(client, version)
    output = client.containers.run(
        image=image.id, detach=False, command=["bash", "-c", "echo 1"]
    ).decode("utf-8")

    assert "Created new site" in output
    assert output.endswith("1\n")


def test_start_setting_custom_timezone(client: docker.DockerClient) -> None:
    with start_checkmk(
        client,
        environment={
            "TZ": "nonvalidatedvalue",
        },
    ) as c:
        config_file = "/omd/sites/cmk/etc/environment"
        exit_code, output_bytes = c.exec_run(
            ["grep", "^TZ=", config_file],
            user="cmk",
        )
        assert exit_code == 0, f"Did not find timezone setting in {config_file}"
        assert output_bytes.decode("utf-8") == 'TZ="nonvalidatedvalue"\n'


# Test that the local deb package is used by making the build fail because of an empty file
def test_build_using_local_deb(
    client: docker.DockerClient,
    version: CMKVersion,
    caplog: LogCaptureFixture,
) -> None:
    pkg_name = package_name(version)
    pkg_path = Path(build_path, pkg_name)
    pkg_path_sav = Path(build_path, f"{pkg_name}.sav")
    try:
        os.rename(pkg_path, pkg_path_sav)
        pkg_path.write_bytes(b"")
        with pytest.raises(docker.errors.BuildError):
            caplog.set_level(logging.CRITICAL)  # avoid error messages in the log
            build_checkmk(client, version, prepare_pkg=False)
        os.unlink(pkg_path)
        prepare_package(version)
    finally:
        try:
            os.unlink(pkg_path)
        except FileNotFoundError:
            pass
        os.rename(pkg_path_sav, pkg_path)


# Test that the local GPG file is used by making the build fail because of an empty file
def test_build_using_local_gpg_pubkey(
    client: docker.DockerClient,
    version: CMKVersion,
    caplog: LogCaptureFixture,
) -> None:
    key_name = "Check_MK-pubkey.gpg"
    key_path = Path(build_path, key_name)
    key_path_sav = Path(build_path, f"{key_name}.sav")
    try:
        os.rename(key_path, key_path_sav)
        key_path.write_text("")
        with pytest.raises(docker.errors.BuildError):
            caplog.set_level(logging.CRITICAL)  # avoid error messages in the log
            build_checkmk(client, version)
    finally:
        os.unlink(key_path)
        os.rename(key_path_sav, key_path)


def test_start_enable_mail(client: docker.DockerClient) -> None:
    with start_checkmk(
        client,
        environment={
            "MAIL_RELAY_HOST": "mailrelay.mydomain.com",
        },
        hostname="myhost.mydomain.com",
    ) as c:
        cmds = [p[-1] for p in c.top()["Processes"]]

        assert "syslogd" in cmds
        # Might have a param like `-w`
        assert "/usr/lib/postfix/sbin/master" in " ".join(cmds)

        assert c.exec_run(["which", "mail"], user="cmk")[0] == 0

        assert (
            c.exec_run(["postconf", "myorigin"])[1].decode("utf-8").rstrip()
            == "myorigin = myhost.mydomain.com"
        )
        assert (
            c.exec_run(["postconf", "relayhost"])[1].decode("utf-8").rstrip()
            == "relayhost = mailrelay.mydomain.com"
        )


def test_http_access_base_redirects_work(
    checkmk: docker.models.containers.Container,
) -> None:
    ip = get_container_ip(checkmk)

    for url, expectedLocation in {
        f"http://{ip}:5000": f"http://{ip}:5000/cmk/",
        f"http://{ip}:5000/cmk": f"http://{ip}:5000/cmk/check_mk/",
    }.items():
        for checkUrl in (f"{url}", f"{url}/"):
            response = requests.get(
                checkUrl,
                allow_redirects=False,
                timeout=10,
            )
            assert response.headers["Location"] == expectedLocation


# Would like to test this from the outside of the container, but this is not possible
# because most of our systems already have something listening on port 80
def test_redirects_work_with_standard_port(
    checkmk: docker.models.containers.Container,
) -> None:
    # Use no explicit port
    assert "Location: http://127.0.0.1/cmk/\r\n" in checkmk.exec_run(
        [
            "curl",
            "-D",
            "-",
            "-s",
            "--connect-to",
            "127.0.0.1:80:127.0.0.1:5000",
            "http://127.0.0.1",
        ],
    )[-1].decode("utf-8")

    # Use explicit standard port
    assert "Location: http://127.0.0.1/cmk/\r\n" in checkmk.exec_run(
        [
            "curl",
            "-D",
            "-",
            "-s",
            "--connect-to",
            "127.0.0.1:80:127.0.0.1:5000",
            "http://127.0.0.1:80",
        ],
    )[-1].decode("utf-8")

    # Use explicit host header with standard port
    assert "Location: http://127.0.0.1/cmk/\r\n" in checkmk.exec_run(
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
    )[-1].decode("utf-8")


def test_redirects_work_with_custom_port(client: docker.DockerClient) -> None:
    # Use some free address port to be able to bind to. For the moment there is no
    # conflict with others, since this test is executed only once at the same time.
    # TODO: We'll have to use some branch specific port in the future.
    address = ("127.3.3.7", 8555)
    address_txt = ":".join(map(str, address))

    with start_checkmk(
        client,
        ports={
            "5000/tcp": address,
        },
    ):
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


@pytest.mark.skipif(
    version_from_env().is_saas_edition(),
    reason="Saas edition replaced the login screen",
)
def test_http_access_login_screen(checkmk: docker.models.containers.Container) -> None:
    ip = get_container_ip(checkmk)

    response = requests.get(
        f"http://{ip}:5000/cmk/check_mk/login.py?_origtarget=index.py",
        allow_redirects=False,
        timeout=10,
    )

    assert response.status_code == 200, "Invalid HTTP status code!"
    assert 'name="_login"' in response.text, "Login field not found!"


@pytest.mark.skip(reason="Saas edition requires cognito config")
# @pytest.mark.skipif(not version_from_env().is_saas_edition(), reason="Saas check saas login")
def test_http_access_login_screen_saas(
    checkmk: docker.models.containers.Container,
) -> None:
    ip = get_container_ip(checkmk)

    response = requests.get(
        f"http://{ip}:5000/cmk/check_mk/login.py?_origtarget=index.py",
        allow_redirects=False,
        timeout=10,
    )
    # saas login redirects to external service
    assert response.status_code == 302
    assert "cognito_sso.py" in response.headers["location"]


def test_container_agent(checkmk: docker.models.containers.Container) -> None:
    # Is the agent installed and executable?
    assert checkmk.exec_run(["check_mk_agent"])[-1].decode("utf-8").startswith("<<<check_mk>>>\n")

    # Check whether the agent port is opened
    assert ":::6556" in checkmk.exec_run(["netstat", "-tln"])[-1].decode("utf-8")


def test_update(client: docker.DockerClient, version: CMKVersion) -> None:
    container_name = f"checkmk-{version.branch}_{randint(10000000, 99999999)}-monitoring"

    assert isinstance(
        versions_compatible(
            Version.from_str(old_version.version), Version.from_str(version.version)
        ),
        VersionsCompatible,
    )

    # 1. create container with old version and add a file to mark the pre-update state
    container_volumes = [f"{container_name}:/omd/sites"]
    with start_checkmk(
        client, version=old_version, name=container_name, volumes=container_volumes
    ) as c_orig:
        assert (
            c_orig.exec_run(["touch", "pre-update-marker"], user="cmk", workdir="/omd/sites/cmk")[0]
            == 0
        )

        # 2. stop the container
        c_orig.stop()

        # 3. rename old container
        c_orig.rename("%s-old" % container_name)

        # 4. create new container
        with start_checkmk(
            client,
            version=version,
            is_update=True,
            name=container_name,
            volumes=container_volumes,
        ) as c_new:
            # 5. verify result
            c_new.exec_run(["omd", "version"], user="cmk")[1].decode("utf-8").endswith(
                "%s\n" % version.omd_version()
            )
            assert (
                c_new.exec_run(
                    ["test", "-f", "pre-update-marker"],
                    user="cmk",
                    workdir="/omd/sites/cmk",
                )[0]
                == 0
            )


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    import doctest

    assert not doctest.testmod().failed
    pytest.main(["-T=docker", "-vvsx", __file__])
