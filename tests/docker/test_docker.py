#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
import os
from pathlib import Path
from random import randint, sample

import docker  # type: ignore[import-untyped]
import pytest
import requests
import requests.exceptions
from pytest import LogCaptureFixture

from tests.testlib.docker import (
    build_checkmk,
    build_path,
    CheckmkApp,
    package_name,
    prepare_package,
)
from tests.testlib.version import CMKVersion, git_tag_exists, version_from_env

from cmk.ccc.version import Edition, Version, versions_compatible

# Apply the skipif marker to all tests in this file for SaaS edition
pytestmark = [
    pytest.mark.skipif(
        version_from_env().is_saas_edition(),
        reason="CSE has its own docker entrypoint which is covered in SaaS tests",
    )
]

logger = logging.getLogger()

old_version = CMKVersion(
    version_spec="2.4.0b1", edition=Edition.CRE, branch="2.4.0", branch_version="2.4.0"
)


def test_start_simple(checkmk: CheckmkApp) -> None:
    cmds = [p[-1] for p in checkmk.container.top()["Processes"]]
    assert "cron -f" in cmds

    # Check postfix / syslog not runnig by default
    assert "syslogd" not in cmds
    assert "/usr/lib/postfix/sbin/master" not in cmds

    # Check omd standard config
    exit_code, output_bytes = checkmk.container.exec_run(["omd", "config", "show"], user="cmk")
    output = output_bytes.decode("utf-8")
    assert "TMPFS: off" in output
    assert "APACHE_TCP_ADDR: 0.0.0.0" in output
    assert "APACHE_TCP_PORT: 5000" in output
    assert "MKEVENTD: on" in output

    if version_from_env().is_raw_edition():
        assert "CORE: nagios" in output
    else:
        assert "CORE: cmc" in output

    # check sites uid/gid
    assert checkmk.container.exec_run(["id", "-u", "cmk"])[1].decode("utf-8").rstrip() == "1000"
    assert checkmk.container.exec_run(["id", "-g", "cmk"])[1].decode("utf-8").rstrip() == "1000"

    assert exit_code == 0


def test_needed_packages(checkmk: CheckmkApp) -> None:
    """Ensure that important tools can be executed in the container"""
    assert checkmk.container.exec_run(["logrotate", "--version"])[0] == 0


def test_start_cmkadmin_password(client: docker.DockerClient) -> None:
    htpasswd = "/omd/sites/cmk/etc/htpasswd"
    cmk_admin = "cmkadmin"
    cmk_password = "blabla"
    with CheckmkApp(client, password=cmk_password) as cmk:
        assert (
            cmk.container.exec_run(["htpasswd", "-vb", htpasswd, cmk_admin, cmk_password])[0] == 0
        )
        assert (
            cmk.container.exec_run(["htpasswd", "-vb", htpasswd, cmk_admin, f"!{cmk_password}"])[0]
            == 3
        )


def test_start_custom_site_id(client: docker.DockerClient) -> None:
    with CheckmkApp(client, site_id="xyz") as cmk:
        assert cmk.container.exec_run(["omd", "status"], user="xyz")[0] == 0


def test_start_enable_livestatus(client: docker.DockerClient) -> None:
    with CheckmkApp(
        client,
        environment={"CMK_LIVESTATUS_TCP": "on"},
    ) as cmk:
        exit_code, output_bytes = cmk.container.exec_run(
            ["omd", "config", "show", "LIVESTATUS_TCP"], user="cmk"
        )
        assert exit_code == 0
        assert output_bytes.decode("utf-8") == "on\n"


def test_start_execute_custom_command(checkmk: CheckmkApp) -> None:
    exit_code, output_bytes = checkmk.container.exec_run(["echo", "1"], user="cmk")
    assert exit_code == 0
    assert output_bytes.decode("utf-8") == "1\n"


def test_start_with_custom_command(client: docker.DockerClient) -> None:
    image, _build_logs = build_checkmk(client, version_from_env())
    output = client.containers.run(
        image=image.id, detach=False, command=["bash", "-c", "echo 1"]
    ).decode("utf-8")

    assert "Created new site" in output
    assert output.endswith("1\n")


def test_start_setting_custom_timezone(client: docker.DockerClient) -> None:
    with CheckmkApp(
        client,
        environment={"TZ": "nonvalidatedvalue"},
    ) as cmk:
        config_file = "/omd/sites/cmk/etc/environment"
        exit_code, output_bytes = cmk.container.exec_run(
            ["grep", "^TZ=", config_file],
            user="cmk",
        )
        assert exit_code == 0, f"Did not find timezone setting in {config_file}"
        assert output_bytes.decode("utf-8") == 'TZ="nonvalidatedvalue"\n'


# Test that the local deb package is used by making the build fail because of an empty file
def test_build_using_local_deb(
    client: docker.DockerClient,
    caplog: LogCaptureFixture,
) -> None:
    pkg_version = version_from_env()
    pkg_name = package_name(pkg_version)
    pkg_path = Path(build_path, pkg_name)
    pkg_path_sav = Path(build_path, f"{pkg_name}.sav")
    try:
        os.rename(pkg_path, pkg_path_sav)
        pkg_path.write_bytes(b"")
        with pytest.raises(docker.errors.BuildError):
            caplog.set_level(logging.CRITICAL)  # avoid error messages in the log
            build_checkmk(client, pkg_version, prepare_pkg=False)
        os.unlink(pkg_path)
        prepare_package(pkg_version)
    finally:
        try:
            os.unlink(pkg_path)
        except FileNotFoundError:
            pass
        os.rename(pkg_path_sav, pkg_path)


# Test that the local GPG file is used by making the build fail because of an empty file
def test_build_using_local_gpg_pubkey(
    client: docker.DockerClient,
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
            build_checkmk(client, version_from_env())
    finally:
        os.unlink(key_path)
        os.rename(key_path_sav, key_path)


def test_start_enable_mail(client: docker.DockerClient) -> None:
    with CheckmkApp(
        client,
        environment={"MAIL_RELAY_HOST": "mailrelay.mydomain.com"},
        hostname="myhost.mydomain.com",
    ) as cmk:
        cmds = [p[-1] for p in cmk.container.top()["Processes"]]

        assert "syslogd" in cmds
        # Might have a param like `-w`
        assert "/usr/lib/postfix/sbin/master" in " ".join(cmds)

        assert cmk.container.exec_run(["which", "mail"], user="cmk")[0] == 0

        assert (
            cmk.container.exec_run(["postconf", "myorigin"])[1].decode("utf-8").rstrip()
            == "myorigin = myhost.mydomain.com"
        )
        assert (
            cmk.container.exec_run(["postconf", "relayhost"])[1].decode("utf-8").rstrip()
            == "relayhost = mailrelay.mydomain.com"
        )


def test_http_access_base_redirects_work(checkmk: CheckmkApp) -> None:
    for url, expectedLocation in {
        f"http://{checkmk.ip}:5000": f"http://{checkmk.ip}:5000/cmk/",
        f"http://{checkmk.ip}:5000/cmk": f"http://{checkmk.ip}:5000/cmk/check_mk/",
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
def test_redirects_work_with_standard_port(checkmk: CheckmkApp) -> None:
    # Use no explicit port
    assert "Location: http://127.0.0.1/cmk/\r\n" in checkmk.container.exec_run(
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
    assert "Location: http://127.0.0.1/cmk/\r\n" in checkmk.container.exec_run(
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
    assert "Location: http://127.0.0.1/cmk/\r\n" in checkmk.container.exec_run(
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
    # Use some random address and port to be able to bind to.
    # NOTE: In case we still run into conflicts, checking for
    # available ports may be required.
    rand_ip = ".".join(str(_) for _ in [127, 3] + sample(range(1, 255), 2))
    rand_port = randint(1024, 65535)
    address = (rand_ip, rand_port)
    address_txt = ":".join(map(str, address))

    with CheckmkApp(
        client,
        ports={"5000/tcp": address},
    ):
        # Use explicit port
        response = requests.get("http://%s" % address_txt, allow_redirects=False, timeout=10)
        assert response.status_code == 302
        assert response.headers["Location"] == "http://%s/cmk/" % address_txt

        # Use explicit port and host header with port
        response = requests.get(
            "http://%s" % address_txt,
            allow_redirects=False,
            headers={
                "Host": address_txt,
            },
            timeout=10,
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
            timeout=10,
        )
        assert response.status_code == 302
        assert response.headers["Location"] == "http://%s/cmk/" % address[0]


def test_http_access_login_screen(checkmk: CheckmkApp) -> None:
    response = requests.get(
        f"http://{checkmk.ip}:5000/cmk/check_mk/login.py?_origtarget=index.py",
        allow_redirects=False,
        timeout=10,
    )

    assert response.status_code == 200, "Invalid HTTP status code!"
    assert 'name="_login"' in response.text, "Login field not found!"


def test_container_agent(checkmk: CheckmkApp) -> None:
    # Is the agent installed and executable?
    assert (
        checkmk.container.exec_run(["check_mk_agent"])[-1]
        .decode("utf-8")
        .startswith("<<<check_mk>>>\n")
    )

    # Check whether the agent port is opened
    assert ":::6556" in checkmk.container.exec_run(["netstat", "-tln"])[-1].decode("utf-8")


@pytest.mark.skipif(
    not git_tag_exists(old_version),
    reason=f"Test is skipped until we have {old_version} available as git tag",
)
def test_update(client: docker.DockerClient) -> None:
    pkg_version = version_from_env()
    container_name = "%s-monitoring" % pkg_version.branch

    update_compatibility = versions_compatible(
        Version.from_str(old_version.version), Version.from_str(pkg_version.version)
    )
    assert update_compatibility.is_compatible, (
        f"Version {old_version} and {pkg_version} are incompatible, reason: {update_compatibility}"
    )

    # 1. create container with old version and add a file to mark the pre-update state
    with CheckmkApp(
        client, version=old_version, name=container_name, volumes=["/omd/sites"]
    ) as cmk_orig:
        assert (
            cmk_orig.container.exec_run(
                ["touch", "pre-update-marker"], user="cmk", workdir="/omd/sites/cmk"
            )[0]
            == 0
        )

        # 2. stop the container
        cmk_orig.container.stop()

        # 3. rename old container
        cmk_orig.container.rename("%s-old" % container_name)

        # 4. create new container
        with CheckmkApp(
            client,
            version=pkg_version,
            is_update=True,
            name=container_name,
            volumes_from=cmk_orig.container.id,
        ) as cmk_new:
            # 5. verify result
            cmk_new.container.exec_run(["omd", "version"], user="cmk")[1].decode("utf-8").endswith(
                "%s\n" % pkg_version.omd_version()
            )
            assert (
                cmk_new.container.exec_run(
                    ["test", "-f", "pre-update-marker"], user="cmk", workdir="/omd/sites/cmk"
                )[0]
                == 0
            )


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    import doctest

    assert not doctest.testmod().failed
    pytest.main(["-T=docker", "-vvsx", __file__])
