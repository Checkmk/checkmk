#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import os
import shutil

import pytest  # type: ignore[import]
from werkzeug.test import create_environ

from testlib.utils import DummyApplication

import cmk.utils.paths

import cmk.gui.config as config
import cmk.gui.htmllib as htmllib
import cmk.gui.watolib as watolib
import cmk.gui.watolib.hosts_and_folders as hosts_and_folders
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import AppContext, RequestContext
from cmk.gui.http import Request
from cmk.gui.watolib.search import MatchItem
from cmk.gui.watolib.utils import has_agent_bakery


@pytest.fixture(name="mocked_user")
def fixture_mocked_user(monkeypatch):
    # Write/Read operations always require a valid user
    monkeypatch.setattr(config, "user", config.LoggedInSuperUser())


@pytest.fixture(autouse=True)
def test_env(mocked_user, load_config, load_plugins):
    # Ensure we have clean folder/host caches
    hosts_and_folders.Folder.invalidate_caches()

    yield

    # Cleanup WATO folders created by the test
    shutil.rmtree(hosts_and_folders.Folder.root_folder().filesystem_path(), ignore_errors=True)
    os.makedirs(hosts_and_folders.Folder.root_folder().filesystem_path())


@pytest.fixture(autouse=True)
def fake_start_bake_agents(monkeypatch):
    if not has_agent_bakery():
        return

    import cmk.gui.cee.plugins.wato.agent_bakery.misc as agent_bakery

    def _fake_start_bake_agents(host_names, signing_credentials):
        pass

    monkeypatch.setattr(agent_bakery, "start_bake_agents", _fake_start_bake_agents)


@pytest.mark.parametrize(
    "attributes,expected_tags",
    [
        (
            {
                "tag_snmp": "no-snmp",
                "tag_agent": "no-agent",
                "site": "ding",
            },
            {
                "address_family": "ip-v4-only",
                "ip-v4": "ip-v4",
                "agent": "no-agent",
                "snmp_ds": "no-snmp",
                "ping": "ping",
                "site": "ding",
                "piggyback": "auto-piggyback",
            },
        ),
        (
            {
                "tag_snmp": "no-snmp",
                "tag_agent": "no-agent",
                "tag_address_family": "no-ip",
            },
            {
                "agent": "no-agent",
                "address_family": "no-ip",
                "snmp_ds": "no-snmp",
                "site": "NO_SITE",
                "piggyback": "auto-piggyback",
            },
        ),
        (
            {
                "site": False,
            },
            {
                "agent": "cmk-agent",
                "address_family": "ip-v4-only",
                "ip-v4": "ip-v4",
                "snmp_ds": "no-snmp",
                "site": "",
                "tcp": "tcp",
                "piggyback": "auto-piggyback",
            },
        ),
    ],
)
def test_host_tags(attributes, expected_tags):
    folder = hosts_and_folders.Folder.root_folder()
    host = hosts_and_folders.Host(folder, "test-host", attributes, cluster_nodes=None)

    assert host.tag_groups() == expected_tags


@pytest.mark.parametrize(
    "attributes,result",
    [
        (
            {
                "tag_snmp_ds": "no-snmp",
                "tag_agent": "no-agent",
            },
            True,
        ),
        (
            {
                "tag_snmp_ds": "no-snmp",
                "tag_agent": "cmk-agent",
            },
            False,
        ),
        (
            {
                "tag_snmp_ds": "no-snmp",
                "tag_agent": "no-agent",
                "tag_address_family": "no-ip",
            },
            False,
        ),
    ],
)
def test_host_is_ping_host(attributes, result):
    folder = hosts_and_folders.Folder.root_folder()
    host = hosts_and_folders.Host(folder, "test-host", attributes, cluster_nodes=None)

    assert host.is_ping_host() == result


@pytest.mark.parametrize(
    "attributes",
    [{
        "tag_snmp_ds": "no-snmp",
        "tag_agent": "no-agent",
        "alias": "testalias",
        "parents": ["ding", "dong"],
    }],
)
def test_write_and_read_host_attributes(tmp_path, attributes, monkeypatch):
    folder_path = str(tmp_path)
    # Write/Read operations always require a valid user
    monkeypatch.setattr(config, "user", config.LoggedInSuperUser())

    # Used to write the data
    write_data_folder = watolib.Folder("testfolder", folder_path=folder_path, parent_folder=None)

    # Used to read the previously written data
    read_data_folder = watolib.Folder("testfolder", folder_path=folder_path, parent_folder=None)

    environ = dict(create_environ(), REQUEST_URI="")
    with AppContext(DummyApplication(environ,
                                     None)), RequestContext(htmllib.html(Request(environ))):
        # Write data
        # Note: The create_hosts function modifies the attributes dict, adding a meta_data key inplace
        write_data_folder.create_hosts([("testhost", attributes, [])])
        write_folder_hosts = write_data_folder.hosts()
        assert len(write_folder_hosts) == 1

        # Read data back
        read_folder_hosts = read_data_folder.hosts()
        assert len(read_folder_hosts) == 1
        for _, host in read_folder_hosts.items():
            assert host.attributes() == attributes


@contextlib.contextmanager
def in_chdir(directory):
    cur = os.getcwd()
    os.chdir(directory)
    yield
    os.chdir(cur)


def test_create_nested_folders(register_builtin_html):
    with in_chdir("/"):
        root = watolib.Folder.root_folder()

        folder1 = watolib.Folder("folder1", parent_folder=root)
        folder1.persist_instance()

        folder2 = watolib.Folder("folder2", parent_folder=folder1)
        folder2.persist_instance()

        shutil.rmtree(os.path.dirname(folder1.wato_info_path()))


def test_eq_operation(register_builtin_html):
    with in_chdir("/"):
        root = watolib.Folder.root_folder()
        folder1 = watolib.Folder("folder1", parent_folder=root)
        folder1.persist_instance()

        folder1_new = watolib.Folder("folder1")
        folder1_new.load_instance()

        assert folder1 == folder1_new
        assert id(folder1) != id(folder1_new)
        assert folder1 in [folder1_new]

        folder2 = watolib.Folder("folder2", parent_folder=folder1)
        folder2.persist_instance()

        assert folder1 not in [folder2]


@pytest.mark.parametrize(
    "protocol,host_attribute,base_variable,credentials,folder_credentials",
    [
        (
            "snmp",
            "management_snmp_community",
            "management_snmp_credentials",
            "HOST",
            "FOLDER",
        ),
        (
            "ipmi",
            "management_ipmi_credentials",
            "management_ipmi_credentials",
            {
                "username": "USER",
                "password": "PASS",
            },
            {
                "username": "FOLDERUSER",
                "password": "FOLDERPASS",
            },
        ),
    ],
)
def test_mgmt_inherit_credentials_explicit_host(protocol, host_attribute, base_variable,
                                                credentials, folder_credentials):

    folder = hosts_and_folders.Folder.root_folder()
    folder.set_attribute(host_attribute, folder_credentials)

    folder.create_hosts([(
        "test-host",
        {
            "ipaddress": "127.0.0.1",
            "management_protocol": protocol,
            host_attribute: credentials,
        },
        [],
    )])

    data = folder._load_hosts_file()
    assert data["management_protocol"]["test-host"] == protocol
    assert data[base_variable]["test-host"] == credentials


@pytest.mark.parametrize(
    "protocol,host_attribute,base_variable,folder_credentials",
    [
        ("snmp", "management_snmp_community", "management_snmp_credentials", "FOLDER"),
        (
            "ipmi",
            "management_ipmi_credentials",
            "management_ipmi_credentials",
            {
                "username": "FOLDERUSER",
                "password": "FOLDERPASS",
            },
        ),
    ],
)
def test_mgmt_inherit_credentials(protocol, host_attribute, base_variable, folder_credentials):
    folder = hosts_and_folders.Folder.root_folder()
    folder.set_attribute(host_attribute, folder_credentials)

    folder.create_hosts([(
        "mgmt-host",
        {
            "ipaddress": "127.0.0.1",
            "management_protocol": protocol,
        },
        [],
    )])

    data = folder._load_hosts_file()
    assert data["management_protocol"]["mgmt-host"] == protocol
    assert data[base_variable]["mgmt-host"] == folder_credentials


@pytest.mark.parametrize(
    "protocol,host_attribute,base_variable,credentials,folder_credentials",
    [
        (
            "snmp",
            "management_snmp_community",
            "management_snmp_credentials",
            "HOST",
            "FOLDER",
        ),
        (
            "ipmi",
            "management_ipmi_credentials",
            "management_ipmi_credentials",
            {
                "username": "USER",
                "password": "PASS",
            },
            {
                "username": "FOLDERUSER",
                "password": "FOLDERPASS",
            },
        ),
    ],
)
def test_mgmt_inherit_protocol_explicit_host(protocol, host_attribute, base_variable, credentials,
                                             folder_credentials):
    folder = hosts_and_folders.Folder.root_folder()
    folder.set_attribute("management_protocol", None)
    folder.set_attribute(host_attribute, folder_credentials)

    folder.create_hosts([(
        "mgmt-host",
        {
            "ipaddress": "127.0.0.1",
            "management_protocol": protocol,
            host_attribute: credentials,
        },
        [],
    )])

    data = folder._load_hosts_file()
    assert data["management_protocol"]["mgmt-host"] == protocol
    assert data[base_variable]["mgmt-host"] == credentials


@pytest.mark.parametrize(
    "protocol,host_attribute,base_variable,folder_credentials",
    [
        ("snmp", "management_snmp_community", "management_snmp_credentials", "FOLDER"),
        (
            "ipmi",
            "management_ipmi_credentials",
            "management_ipmi_credentials",
            {
                "username": "FOLDERUSER",
                "password": "FOLDERPASS",
            },
        ),
    ],
)
def test_mgmt_inherit_protocol(protocol, host_attribute, base_variable, folder_credentials):
    folder = hosts_and_folders.Folder.root_folder()
    folder.set_attribute("management_protocol", protocol)
    folder.set_attribute(host_attribute, folder_credentials)

    folder.create_hosts([(
        "mgmt-host",
        {
            "ipaddress": "127.0.0.1",
        },
        [],
    )])

    data = folder._load_hosts_file()
    assert data["management_protocol"]["mgmt-host"] == protocol
    assert data[base_variable]["mgmt-host"] == folder_credentials


@pytest.fixture(name="make_folder")
def fixture_make_folder(mocker):
    """
    Returns a function to create patched folders for tests. Note that the global setting
    "Hide folders without read permissions" will currently always be set during setup.
    """
    mocker.patch.object(
        hosts_and_folders.config,
        "wato_hide_folders_without_read_permissions",
        True,
        create=True,
    )

    def prefixed_title(self_, current_depth, pretty):
        return "_" * current_depth + self_.title()

    mocker.patch.object(hosts_and_folders.Folder, "_prefixed_title", prefixed_title)

    def may(self_, _permission):
        return self_._may_see

    mocker.patch.object(hosts_and_folders.Folder, "may", may)

    # convenience method NOT present in Folder
    def add_subfolders(self_, folders):
        for folder in folders:
            self_._subfolders[folder.name()] = folder
            folder._parent = self_
        return self_

    mocker.patch.object(hosts_and_folders.Folder, "add_subfolders", add_subfolders, create=True)

    def f(name, title, root_dir="/", parent_folder=None, may_see=True):
        folder = hosts_and_folders.Folder(
            name,
            folder_path=None,
            parent_folder=parent_folder,
            title=title,
            root_dir=root_dir,
        )
        # Attribute only used for testing
        folder._may_see = may_see  # type: ignore[attr-defined]
        return folder

    return f


def only_root(folder):
    return folder("", title="Main directory")


def three_levels(folder):
    return folder("", title="Main directory").add_subfolders([
        folder("a", title="A").add_subfolders([
            folder("c", title="C"),
            folder("d", title="D"),
        ]),
        folder("b", title="B").add_subfolders([
            folder("e", title="E").add_subfolders([
                folder("f", title="F"),
            ]),
        ]),
    ])


def three_levels_leaf_permissions(folder):
    return folder("", title="Main directory", may_see=False).add_subfolders([
        folder("a", title="A", may_see=False).add_subfolders([
            folder("c", title="C", may_see=False),
            folder("d", title="D"),
        ]),
        folder("b", title="B", may_see=False).add_subfolders([
            folder("e", title="E", may_see=False).add_subfolders([
                folder("f", title="F"),
            ]),
        ]),
    ])


@pytest.mark.parametrize(
    "actual_builder,expected",
    [
        (only_root, [("", "Main directory")]),
        (
            three_levels,
            [
                ("", "Main directory"),
                ("a", "_A"),
                ("a/c", "__C"),
                ("a/d", "__D"),
                ("b", "_B"),
                ("b/e", "__E"),
                ("b/e/f", "___F"),
            ],
        ),
        (
            three_levels_leaf_permissions,
            [
                ("", "Main directory"),
                ("a", "_A"),
                ("a/d", "__D"),
                ("b", "_B"),
                ("b/e", "__E"),
                ("b/e/f", "___F"),
            ],
        ),
    ],
)
def test_recursive_subfolder_choices(make_folder, actual_builder, expected):
    actual = actual_builder(make_folder)
    assert actual.recursive_subfolder_choices() == expected


def test_recursive_subfolder_choices_function_calls(mocker, make_folder):
    """Every folder should only be visited once"""
    spy = mocker.spy(hosts_and_folders.Folder, "_walk_tree")

    tree = three_levels_leaf_permissions(make_folder)
    tree.recursive_subfolder_choices()

    assert spy.call_count == 7


def test_subfolder_creation():
    folder = hosts_and_folders.Folder.root_folder()
    folder.create_subfolder("foo", "Foo Folder", {})

    # Upon instantiation, all the subfolders should be already known.
    folder = hosts_and_folders.Folder.root_folder()
    assert len(folder._subfolders) == 1


def test_match_item_generator_hosts():
    assert list(
        hosts_and_folders.MatchItemGeneratorHosts(
            "hosts",
            lambda: {
                "host": {
                    "edit_url": "some_url",
                    "alias": "alias",
                    "ipaddress": "1.2.3.4",
                    "ipv6address": "",
                    "additional_ipv4addresses": ["5.6.7.8"],
                    "additional_ipv6addresses": [],
                },
            },
        ).generate_match_items()) == [
            MatchItem(
                title="host",
                topic="Hosts",
                url="some_url",
                match_texts=["host", "alias", "1.2.3.4", "5.6.7.8"],
            )
        ]


def test_folder_exists(mocker, tmp_path) -> None:
    mocker.patch.object(cmk.utils.paths, "check_mk_config_dir", str(tmp_path))
    (tmp_path / "wato" / "foo" / "bar").mkdir(parents=True)
    assert hosts_and_folders.Folder.folder_exists("foo")
    assert hosts_and_folders.Folder.folder_exists("foo/bar")
    assert not hosts_and_folders.Folder.folder_exists("bar")
    assert not hosts_and_folders.Folder.folder_exists("foo/foobar")
    with pytest.raises(MKUserError):
        hosts_and_folders.Folder.folder_exists("../wato")
