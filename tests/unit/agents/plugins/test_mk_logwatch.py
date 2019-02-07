# -*- encoding: utf-8
import os
import sys
import pytest
from testlib import cmk_path  # pylint: disable=import-error
from re import compile

import imp
mk_logwatch = imp.load_source("mk_logwatch",
                              os.path.join(cmk_path(), 'agents', 'plugins', 'mk_logwatch'))
import mk_logwatch  # pylint: disable=import-error,wrong-import-position

# consistent to check_mk/agents/cfg_examples/logwatch.cfg
LOGWATCH_CONFIG_CONTENT = """
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

# logwatch.cfg
# This file configures mk_logwatch. Define your logfiles
# and patterns to be looked for here.

# Name one or more logfiles
/var/log/messages
# Patterns are indented with one space are prefixed with:
# C: Critical messages
# W: Warning messages
# I: ignore these lines (OK)
# R: Rewrite the output previous match. You can use \1, \2 etc. for refer to groups (.*) of this match
# The first match decided. Lines that do not match any pattern
# are ignored
 C Fail event detected on md device
 I mdadm.*: Rebuild.*event detected
 W mdadm\[
 W ata.*hard resetting link
 W ata.*soft reset failed (.*FIS failed)
 W device-mapper: thin:.*reached low water mark
 C device-mapper: thin:.*no free space
 C Error: (.*)

/var/log/auth.log
 W sshd.*Corrupted MAC on input

/var/log/syslog /var/log/kern.log
 I registered panic notifier
 C panic
 C Oops
 W generic protection rip
 W .*Unrecovered read error - auto reallocate failed

# Globbing patterns are allowed:
# /sapdata/*/saptrans.log
#  C ORA-

# Configuration of remote ips to a cluster name:
# - cluster: A line containing "cluster" defines the scope of a cluster mapping.
#   For more information refer to werk 7032.
#   For the logwatch configuration of a host several cluster configurtions are allowed.
#   All cluster mapping definitions in the logwatch configuration must have unique cluster names (name).
#   Every cluster definition scope must end with at least one empty line.
# - name: For every cluster it is only one line allowed for defining the cluster name.
#   Whitespaces are supported and result in corresponding underscore replacements in the
#   logwatch config file. The line defining the cluster name must begin with " name ".
# - ips: For every cluster max. 4 ips are allowed. Lines defining an ip must begin with " - ".
CLUSTER my_cluster
 192.168.1.1
 192.168.1.2
 192.168.1.3
 192.168.1.4

CLUSTER another_cluster
 192.168.1.5
 192.168.1.6
 1762:0:0:0:0:B03:1:AF18"""


def test_get_config_files(tmpdir):
    fake_config_dir = tmpdir.mkdir("test")
    fake_custom_config_file = fake_config_dir.mkdir("logwatch.d").join("custom.cfg")
    fake_custom_config_file.write("blub")
    print(fake_config_dir)
    fake_config_dir_path = str(fake_config_dir)
    paths = [
        p.replace(fake_config_dir_path, "")
        for p in mk_logwatch.get_config_files(fake_config_dir_path)
    ]
    assert paths == ['/logwatch.cfg', '/logwatch.d/custom.cfg']


def test_read_config(tmpdir):
    """Fakes a single logwatch config files and checks if the agent plugin reads the configuration appropriately."""
    # setup
    fake_config_file = tmpdir.mkdir("test").join("logwatch.cfg")
    fake_config_file.write(LOGWATCH_CONFIG_CONTENT)
    files = [str(fake_config_file)]

    # execution
    actual_config = mk_logwatch.read_config(files)

    # expected logfiles config
    for lc in actual_config[:3]:
        assert isinstance(lc, mk_logwatch.LogfilesConfig)
    logfiles_config = actual_config[0]
    assert logfiles_config.files == ['/var/log/messages']
    assert [l[0] for l in logfiles_config.patterns] == ['C', 'I', 'W', 'W', 'W', 'W', 'C', 'C']
    patterns_first_logfiles_config = [
        "Fail event detected on md device", "mdadm.*: Rebuild.*event detected", "mdadm\[",
        "ata.*hard resetting link", "ata.*soft reset failed (.*FIS failed)",
        "device-mapper: thin:.*reached low water mark", "device-mapper: thin:.*no free space",
        "Error: (.*)"
    ]
    compiled_patterns = []
    for compiled, raw in zip([l[1] for l in logfiles_config.patterns],
                             patterns_first_logfiles_config):
        assert compiled.pattern == raw
    assert isinstance(logfiles_config.patterns[0][2],
                      list)  # no "A" pattern levels, empty continuation pattern list ok
    assert isinstance(logfiles_config.patterns[0][3],
                      list)  # no "R" pattern level, empty rewrite pattern list ok

    # expected cluster config
    for cc in actual_config[3:]:
        assert isinstance(cc, mk_logwatch.ClusterConfig)
    cluster_config = actual_config[3]
    assert cluster_config.name == "my_cluster"
    assert cluster_config.ips == ['192.168.1.1', '192.168.1.2', '192.168.1.3', '192.168.1.4']
    another_cluster = actual_config[4]
    assert another_cluster.name == "another_cluster"
    assert another_cluster.ips == ['192.168.1.5', '192.168.1.6', '1762:0:0:0:0:B03:1:AF18']


@pytest.mark.parametrize(
    "env_var, istty, statusfile",
    [
        ("192.168.2.1", False, "/path/to/config/logwatch.state.192.168.2.1"),  # tty doesnt matter
        ("::ffff:192.168.2.1", False,
         "/path/to/config/logwatch.state.__ffff_192.168.2.1"),  # tty doesnt matter
        ("192.168.1.4", False, "/path/to/config/logwatch.state.my_cluster"),
        ("1262:0:0:0:0:B03:1:AF18", False,
         "/path/to/config/logwatch.state.1262_0_0_0_0_B03_1_AF18"),
        ("1762:0:0:0:0:B03:1:AF18", False, "/path/to/config/logwatch.state.another_cluster"),
        ("", True, "/path/to/config/logwatch.state.local"),
        ("", False, "/path/to/config/logwatch.state"),
    ])
def test_get_status_filename(env_var, istty, statusfile, monkeypatch, mocker):
    """
    May not be executed with pytest option -s set. pytest stdout redirection would colide
    with stdout mock.
    """
    monkeypatch.setenv("REMOTE", env_var)
    monkeypatch.setenv("MK_VARDIR", '/path/to/config')
    stdout_mock = mocker.patch("mk_logwatch.sys.stdout")
    stdout_mock.isatty.return_value = istty
    fake_config = [
        mk_logwatch.ClusterConfig("my_cluster",
                                  ['192.168.1.1', '192.168.1.2', '192.168.1.3', '192.168.1.4']),
        mk_logwatch.ClusterConfig("another_cluster",
                                  ['192.168.1.5', '192.168.1.6', '1762:0:0:0:0:B03:1:AF18'])
    ]

    status_filename = mk_logwatch.get_status_filename(fake_config)
    assert status_filename == statusfile


def test_read_status(tmpdir):
    # setup
    fake_status_file = tmpdir.mkdir("test").join("logwatch.state.another_cluster")
    fake_status_file.write("""/var/log/messages|7767698|32455445
/var/test/x12134.log|12345|32444355""")
    file_path = str(fake_status_file)

    # execution
    actual_status = mk_logwatch.read_status(file_path)
    # comparing dicts (having unordered keys) is ok
    assert actual_status == {
        '/var/log/messages': (7767698, 32455445),
        '/var/test/x12134.log': (12345, 32444355)
    }


def test_save_status(tmpdir):
    fake_status_file = tmpdir.mkdir("test").join("logwatch.state.another_cluster")
    fake_status_file.write("")
    file_path = str(fake_status_file)
    fake_status = {
        '/var/log/messages': (7767698, 32455445),
        '/var/test/x12134.log': (12345, 32444355)
    }
    mk_logwatch.save_status(fake_status, file_path)
    assert sorted(fake_status_file.read().splitlines()) == [
        '/var/log/messages|7767698|32455445', '/var/test/x12134.log|12345|32444355'
    ]
