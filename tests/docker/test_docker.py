#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# pylint: disable=redefined-outer-name

import sys
import os
import subprocess
import pytest  # type: ignore
import docker  # type: ignore

import testlib

build_path = os.path.join(testlib.repo_path(), "docker")
image_prefix = "docker-tests"
branch_name = os.environ.get("BRANCH", "master")


def build_version():
    return testlib.CMKVersion(version=testlib.CMKVersion.DAILY,
                              edition=testlib.CMKVersion.CEE,
                              branch=branch_name)


@pytest.fixture(scope="session")
def version():
    return build_version()


@pytest.fixture()
def client():
    return docker.DockerClient(base_url="tcp://127.0.0.1:2376")


def _image_name(version):
    return "docker-tests/check-mk-%s-%s-%s" % (version.edition(), branch_name, version.version)


def _prepare_build():
    assert subprocess.Popen(["make", "needed-packages"], cwd=build_path).wait() == 0


def _build(request, client, version, add_args=None):
    _prepare_build()

    print "Building docker image: %s" % _image_name(version)
    try:
        image, build_logs = client.images.build(path=build_path,
                                                tag=_image_name(version),
                                                buildargs={
                                                    "CMK_VERSION": version.version,
                                                    "CMK_EDITION": version.edition(),
                                                    "CMK_DL_CREDENTIALS": ":".join(
                                                        testlib.get_cmk_download_credentials()),
                                                })
    except docker.errors.BuildError as e:
        sys.stdout.write("= Build log ==================\n")
        for entry in e.build_log:
            if "stream" in entry:
                sys.stdout.write(entry["stream"])
            elif "errorDetail" in entry:
                continue  # Is already part of the exception message
            else:
                sys.stdout.write("UNEXPECTED FORMAT: %r\n" % entry)
        sys.stdout.write("= Build log ==================\n")
        raise

    # TODO: Enable this on CI system. Removing during development slows down testing
    #request.addfinalizer(lambda: client.images.remove(image.id, force=True))

    attrs = image.attrs
    config = attrs["Config"]

    assert config["Labels"] == {
        u'org.opencontainers.image.vendor': u'tribe29 GmbH',
        u'org.opencontainers.image.version': version.version,
        u'maintainer': u'feedback@checkmk.com',
        u'org.opencontainers.image.description': u'Checkmk is a leading tool for Infrastructure & Application Monitoring',
        u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
        u'org.opencontainers.image.title': u'Checkmk',
        u'org.opencontainers.image.url': u'https://checkmk.com/'
    }

    assert config["Env"] == [
        u'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
        u'CMK_SITE_ID=cmk',
        u'CMK_LIVESTATUS_TCP=',
        u'CMK_PASSWORD=',
        u'MAIL_RELAY_HOST=',
    ]

    assert "Healthcheck" in config

    assert attrs["ContainerConfig"]["Entrypoint"] == [u'/docker-entrypoint.sh']

    assert attrs["ContainerConfig"]["ExposedPorts"] == {
        u'5000/tcp': {},
        u'6557/tcp': {},
    }

    # 2018-11-14: 900 -> 920
    # 2018-11-22: 920 -> 940
    # 2019-04-10: 940 -> 950
    assert attrs["Size"] < 950 * 1024 * 1024, \
        "Docker image size increased: Please verify that this is intended"

    assert len(attrs["RootFS"]["Layers"]) == 6

    return image, build_logs


def _pull(client, version):
    if version.edition() != "raw":
        raise Exception("Can only fetch raw edition at the moment")

    print "Downloading docker image: checkmk/check-mk-raw:%s" % version.version
    return client.images.pull("checkmk/check-mk-raw", tag=version.version)


def _start(request, client, version=None, is_update=False, **kwargs):
    if version is None:
        version = build_version()

    if version.version == build_version().version:
        _image, _build_logs = _build(request, client, version)
    else:
        # In case the given version is not the current branch version, don't
        # try to build it. Download it instead!
        _image = _pull(client, version)

    c = client.containers.run(image=_image.id, detach=True, **kwargs)

    try:
        site_id = kwargs.get("environment", {}).get("CMK_SITE_ID", "cmk")

        request.addfinalizer(lambda: c.remove(force=True))

        testlib.wait_until(lambda: c.exec_run(["omd", "status"], user=site_id)[0] == 0, timeout=120)
        output = c.logs()

        if not is_update:
            assert "Created new site" in output
            assert "cmkadmin with password:" in output
        else:
            assert "Created new site" not in output
            assert "cmkadmin with password:" not in output

        assert "STARTING SITE" in output
        assert "### CONTAINER STARTED" in output
    finally:
        print "Log so far: %s" % c.logs()

    return c


# TODO: Test with all editions (daily for enterprise + last stable for raw/managed)
@pytest.mark.parametrize(
    "edition",
    [
        #    "raw",
        "enterprise",
        #    "managed",
    ])
def test_start_simple(request, client, edition):
    c = _start(request, client)

    cmds = [p[-1] for p in c.top()["Processes"]]
    assert "cron -f" in cmds

    # Check postfix / syslog not runnig by default
    assert "syslogd" not in cmds
    assert "/usr/lib/postfix/sbin/master" not in cmds

    # Check omd standard config
    exit_code, output = c.exec_run(["omd", "config", "show"], user="cmk")
    assert "TMPFS: off" in output
    assert "APACHE_TCP_ADDR: 0.0.0.0" in output
    assert "APACHE_TCP_PORT: 5000" in output
    assert "MKEVENTD: on" in output

    if edition != "raw":
        assert "CORE: cmc" in output
    else:
        assert "CORE: nagios" in output

    # check sites uid/gid
    assert c.exec_run(["id", "-u", "cmk"])[1].rstrip() == "1000"
    assert c.exec_run(["id", "-g", "cmk"])[1].rstrip() == "1000"

    assert exit_code == 0


def test_start_cmkadmin_passsword(request, client):
    c = _start(request, client, environment={
        "CMK_PASSWORD": "blabla",
    })

    assert c.exec_run(["htpasswd", "-vb", "/omd/sites/cmk/etc/htpasswd", "cmkadmin",
                       "blabla"])[0] == 0

    assert c.exec_run(["htpasswd", "-vb", "/omd/sites/cmk/etc/htpasswd", "cmkadmin",
                       "blub"])[0] == 3


def test_start_custom_site_id(request, client):
    c = _start(request, client, environment={
        "CMK_SITE_ID": "xyz",
    })

    assert c.exec_run(["omd", "status"], user="xyz")[0] == 0


def test_start_enable_livestatus(request, client):
    c = _start(request, client, environment={
        "CMK_LIVESTATUS_TCP": "on",
    })

    exit_code, output = c.exec_run(["omd", "config", "show", "LIVESTATUS_TCP"], user="cmk")
    assert exit_code == 0
    assert output == "on\n"


def test_start_execute_custom_command(request, client):
    c = _start(request, client)

    exit_code, output = c.exec_run(["echo", "1"], user="cmk")
    assert exit_code == 0
    assert output == "1\n"


def test_start_with_custom_command(request, client, version):
    image, _build_logs = _build(request, client, version)
    output = client.containers.run(image=image.id, detach=False, command=["bash", "-c", "echo 1"])

    assert "Created new site" in output
    assert output.endswith("1\n")


# Test that the local deb package is used by making the build fail because of an empty file
def test_build_using_local_deb(request, client, version):
    pkg_path = os.path.join(build_path, version.package_name_of_distro("stretch"))
    try:
        with open(pkg_path, "w") as f:
            f.write("")

        with pytest.raises(docker.errors.BuildError):
            _build(request, client, version)
    finally:
        os.unlink(pkg_path)


# Test that the local GPG file is used by making the build fail because of an empty file
def test_build_using_local_gpg_pubkey(request, client, version):
    pkg_path = os.path.join(build_path, "Check_MK-pubkey.gpg")
    try:
        with open(pkg_path, "w") as f:
            f.write("")

        with pytest.raises(docker.errors.BuildError):
            _build(request, client, version)
    finally:
        os.unlink(pkg_path)


def test_start_enable_mail(request, client):
    c = _start(request,
               client,
               environment={
                   "MAIL_RELAY_HOST": "mailrelay.mydomain.com",
               },
               hostname="myhost.mydomain.com")

    cmds = [p[-1] for p in c.top()["Processes"]]

    assert "syslogd" in cmds
    assert "/usr/lib/postfix/sbin/master" in cmds

    assert c.exec_run(["which", "mail"], user="cmk")[0] == 0

    assert c.exec_run(["postconf", "myorigin"])[1].rstrip() == "myorigin = myhost.mydomain.com"
    assert c.exec_run(["postconf", "relayhost"])[1].rstrip() == "relayhost = mailrelay.mydomain.com"


def test_http_access(request, client):
    c = _start(request, client)

    assert "Location: http://127.0.0.1:5000/cmk/\r\n" in c.exec_run(
        ["curl", "-D", "-", "-s", "http://127.0.0.1:5000"])[-1]
    assert "Location: http://127.0.0.1:5000/cmk/\r\n" in c.exec_run(
        ["curl", "-D", "-", "-s", "http://127.0.0.1:5000/"])[-1]
    assert "Location: http://127.0.0.1:5000/cmk/check_mk/\r\n" in c.exec_run(
        ["curl", "-D", "-", "-s", "http://127.0.0.1:5000/cmk"])[-1]
    assert "Location: /cmk/check_mk/login.py?_origtarget=index.py\r\n" in c.exec_run(
        ["curl", "-D", "-", "http://127.0.0.1:5000/cmk/check_mk/"])[-1]

    assert "Location: \r\n" not in c.exec_run(
        ["curl", "-D", "-", "http://127.0.0.1:5000/cmk/check_mk/login.py?_origtarget=index.py"])[-1]
    assert "name=\"_login\"" in c.exec_run(
        ["curl", "-D", "-", "http://127.0.0.1:5000/cmk/check_mk/login.py?_origtarget=index.py"])[-1]


def test_container_agent(request, client):
    c = _start(request, client)
    # Is the agent installed and executable?
    assert c.exec_run(["check_mk_agent"])[-1].startswith("<<<check_mk>>>\n")

    # Check whether or not the agent port is opened
    assert ":::6556" in c.exec_run(["netstat", "-tln"])[-1]


def test_update(request, client, version):
    container_name = "%s-monitoring" % branch_name

    # Pick a random old version that we can use to the setup the initial site with
    # Later this site is being updated to the current daily build
    old_version = testlib.CMKVersion(
        version="1.5.0p5",
        branch="1.5.0",
        edition=testlib.CMKVersion.CRE,
    )

    # 1. create container with old version and add a file to mark the pre-update state
    c_orig = _start(request,
                    client,
                    version=old_version,
                    name=container_name,
                    volumes=["/omd/sites"],
                    tmpfs=["/omd/sites/cmk/tmp"])
    assert c_orig.exec_run(["touch", "pre-update-marker"], user="cmk",
                           workdir="/omd/sites/cmk")[0] == 0

    # Until we have a "old version" with .version_meta directory that we can update
    # from produce this directory manually here.
    # TODO: Once we update from a 1.6 version this can be dropped
    assert c_orig.exec_run(["mkdir", ".version_meta"], user="cmk", workdir="/omd/sites/cmk")[0] == 0
    assert c_orig.exec_run(["cp", "-pr", "version/skel", ".version_meta/"],
                           user="cmk",
                           workdir="/omd/sites/cmk")[0] == 0
    assert c_orig.exec_run(["cp", "-pr", "version/share/omd/skel.permissions", ".version_meta/"],
                           user="cmk",
                           workdir="/omd/sites/cmk")[0] == 0
    assert c_orig.exec_run(
        ["bash", "-c",
         "echo '%s' > .version_meta/version" % old_version.omd_version()],
        user="cmk",
        workdir="/omd/sites/cmk")[0] == 0

    # 2. stop the container
    c_orig.stop()

    # 3. rename old container
    c_orig.rename("%s-old" % container_name)

    # 4. create new container
    c_new = _start(request,
                   client,
                   version=version,
                   is_update=True,
                   name=container_name,
                   volumes_from=c_orig.id)

    # 5. verify result
    c_new.exec_run(["omd", "version"], user="cmk")[1].endswith("%s\n" % version.omd_version())
    assert c_new.exec_run(["test", "-f", "pre-update-marker"], user="cmk",
                          workdir="/omd/sites/cmk")[0] == 0
