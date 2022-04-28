#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import pprint
import shutil
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Union

import pytest
from _pytest.monkeypatch import MonkeyPatch
from mock import MagicMock

import cmk.utils.paths
from cmk.utils.type_defs import ContactgroupName, UserId

import cmk.gui.watolib.hosts_and_folders as hosts_and_folders
from cmk.gui import userdb
from cmk.gui.config import active_config
from cmk.gui.ctx_stack import g
from cmk.gui.exceptions import MKUserError
from cmk.gui.watolib.bakery import has_agent_bakery
from cmk.gui.watolib.search import MatchItem


@pytest.fixture(autouse=True)
def test_env(with_admin_login: UserId, load_config: None) -> Iterator[None]:
    # Ensure we have clean folder/host caches
    hosts_and_folders.Folder.invalidate_caches()

    yield

    # Cleanup WATO folders created by the test
    shutil.rmtree(hosts_and_folders.Folder.root_folder().filesystem_path(), ignore_errors=True)
    os.makedirs(hosts_and_folders.Folder.root_folder().filesystem_path())


@pytest.fixture(autouse=True)
def fake_start_bake_agents(monkeypatch: MonkeyPatch) -> None:
    if not has_agent_bakery():
        return

    import cmk.gui.cee.plugins.wato.agent_bakery.misc as agent_bakery  # pylint: disable=no-name-in-module

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
                "agent": "no-agent",
                "ip-v4": "ip-v4",
                "piggyback": "auto-piggyback",
                "ping": "ping",
                "site": "ding",
                "snmp_ds": "no-snmp",
            },
        ),
        (
            {
                "tag_snmp": "no-snmp",
                "tag_agent": "no-agent",
                "tag_address_family": "no-ip",
            },
            {
                "address_family": "no-ip",
                "agent": "no-agent",
                "piggyback": "auto-piggyback",
                "site": "NO_SITE",
                "snmp_ds": "no-snmp",
            },
        ),
        (
            {
                "site": False,
            },
            {
                "address_family": "ip-v4-only",
                "agent": "cmk-agent",
                "checkmk-agent": "checkmk-agent",
                "ip-v4": "ip-v4",
                "piggyback": "auto-piggyback",
                "site": "",
                "snmp_ds": "no-snmp",
                "tcp": "tcp",
            },
        ),
    ],
)
def test_host_tags(attributes: dict, expected_tags: dict[str, str]) -> None:
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
def test_host_is_ping_host(attributes: dict[str, str], result: bool) -> None:
    folder = hosts_and_folders.Folder.root_folder()
    host = hosts_and_folders.Host(folder, "test-host", attributes, cluster_nodes=None)

    assert host.is_ping_host() == result


@pytest.mark.parametrize(
    "attributes",
    [
        {
            "tag_snmp_ds": "no-snmp",
            "tag_agent": "no-agent",
            "alias": "testalias",
            "parents": ["ding", "dong"],
        }
    ],
)
def test_write_and_read_host_attributes(
    tmp_path: Path, attributes: dict[str, Union[str, list[str]]]
) -> None:
    folder_path = str(tmp_path)
    # Used to write the data
    write_data_folder = hosts_and_folders.Folder(
        "testfolder", folder_path=folder_path, parent_folder=None
    )

    # Used to read the previously written data
    read_data_folder = hosts_and_folders.Folder(
        "testfolder", folder_path=folder_path, parent_folder=None
    )

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


@contextmanager
def in_chdir(directory) -> Iterator[None]:
    cur = os.getcwd()
    os.chdir(directory)
    yield
    os.chdir(cur)


def test_create_nested_folders(request_context: None) -> None:
    with in_chdir("/"):
        root = hosts_and_folders.Folder.root_folder()

        folder1 = hosts_and_folders.Folder("folder1", parent_folder=root)
        folder1.persist_instance()

        folder2 = hosts_and_folders.Folder("folder2", parent_folder=folder1)
        folder2.persist_instance()

        shutil.rmtree(os.path.dirname(folder1.wato_info_path()))


def test_eq_operation(request_context: None) -> None:
    with in_chdir("/"):
        root = hosts_and_folders.Folder.root_folder()
        folder1 = hosts_and_folders.Folder("folder1", parent_folder=root)
        folder1.persist_instance()

        folder1_new = hosts_and_folders.Folder("folder1")
        folder1_new.load_instance()

        assert folder1 == folder1_new
        assert id(folder1) != id(folder1_new)
        assert folder1 in [folder1_new]

        folder2 = hosts_and_folders.Folder("folder2", parent_folder=folder1)
        folder2.persist_instance()

        assert folder1 not in [folder2]


@pytest.mark.parametrize(
    "protocol,host_attribute,base_variable,credentials,folder_credentials",
    [
        ("snmp", "management_snmp_community", "management_snmp_credentials", "HOST", "FOLDER"),
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
def test_mgmt_inherit_credentials_explicit_host(
    protocol: str,
    host_attribute: str,
    base_variable: str,
    credentials: Union[str, dict[str, str]],
    folder_credentials: Union[str, dict[str, str]],
) -> None:

    folder = hosts_and_folders.Folder.root_folder()
    folder.set_attribute(host_attribute, folder_credentials)

    folder.create_hosts(
        [
            (
                "test-host",
                {
                    "ipaddress": "127.0.0.1",
                    "management_protocol": protocol,
                    host_attribute: credentials,
                },
                [],
            )
        ]
    )

    data = folder._load_hosts_file()
    assert data is not None
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
def test_mgmt_inherit_credentials(
    protocol: str,
    host_attribute: str,
    base_variable: str,
    folder_credentials: Union[str, dict[str, str]],
) -> None:
    folder = hosts_and_folders.Folder.root_folder()
    folder.set_attribute(host_attribute, folder_credentials)

    folder.create_hosts(
        [
            (
                "mgmt-host",
                {
                    "ipaddress": "127.0.0.1",
                    "management_protocol": protocol,
                },
                [],
            )
        ]
    )

    data = folder._load_hosts_file()
    assert data is not None
    assert data["management_protocol"]["mgmt-host"] == protocol
    assert data[base_variable]["mgmt-host"] == folder_credentials


@pytest.mark.parametrize(
    "protocol,host_attribute,base_variable,credentials,folder_credentials",
    [
        ("snmp", "management_snmp_community", "management_snmp_credentials", "HOST", "FOLDER"),
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
def test_mgmt_inherit_protocol_explicit_host(
    protocol: str,
    host_attribute: str,
    base_variable: str,
    credentials: Union[str, dict[str, str]],
    folder_credentials: Union[str, dict[str, str]],
) -> None:
    folder = hosts_and_folders.Folder.root_folder()
    folder.set_attribute("management_protocol", None)
    folder.set_attribute(host_attribute, folder_credentials)

    folder.create_hosts(
        [
            (
                "mgmt-host",
                {
                    "ipaddress": "127.0.0.1",
                    "management_protocol": protocol,
                    host_attribute: credentials,
                },
                [],
            )
        ]
    )

    data = folder._load_hosts_file()
    assert data is not None
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
def test_mgmt_inherit_protocol(
    protocol: str,
    host_attribute: str,
    base_variable: str,
    folder_credentials: Union[str, dict[str, str]],
) -> None:
    folder = hosts_and_folders.Folder.root_folder()
    folder.set_attribute("management_protocol", protocol)
    folder.set_attribute(host_attribute, folder_credentials)

    folder.create_hosts(
        [
            (
                "mgmt-host",
                {
                    "ipaddress": "127.0.0.1",
                },
                [],
            )
        ]
    )

    data = folder._load_hosts_file()
    assert data is not None
    assert data["management_protocol"]["mgmt-host"] == protocol
    assert data[base_variable]["mgmt-host"] == folder_credentials


def test_load_hosts_cleanup_pre_210_hostname_attribute() -> None:
    # Simulate a configuration that has been created with a previous "host diagnostic" in a
    # previous version. The field "hostname" is added to the attributes dict.
    folder = hosts_and_folders.Folder.root_folder()
    folder.create_hosts(
        [
            (
                "test-host",
                {
                    "ipaddress": "127.0.0.1",
                    "hostname": "test-host",
                },
                [],
            )
        ]
    )

    hosts_and_folders.Folder.invalidate_caches()
    folder = hosts_and_folders.Folder.root_folder()

    # Verify that it has been saved with the wrong attribute
    data = folder._load_hosts_file()
    assert data is not None
    assert data["host_attributes"]["test-host"]["hostname"] == "test-host"

    # Now ensure that it is being cleaned up
    hosts = folder.hosts()
    assert "hostname" not in hosts["test-host"].attributes()


@pytest.fixture(name="make_folder")
def fixture_make_folder(mocker: MagicMock) -> Callable:
    """
    Returns a function to create patched folders for tests. Note that the global setting
    "Hide folders without read permissions" will currently always be set during setup.
    """
    mocker.patch.object(
        hosts_and_folders.active_config,
        "wato_hide_folders_without_read_permissions",
        True,
        create=True,
    )

    def prefixed_title(self_, current_depth: int, pretty) -> str:
        return "_" * current_depth + self_.title()

    mocker.patch.object(hosts_and_folders.Folder, "_prefixed_title", prefixed_title)

    def may(self_, _permission):
        return self_._may_see

    mocker.patch.object(hosts_and_folders.Folder, "may", may)

    # convenience method NOT present in Folder
    def add_subfolders(self_, folders):
        self_._loaded_subfolders = {}
        for folder in folders:
            self_._loaded_subfolders[folder.name()] = folder
            folder._parent = self_
        return self_

    mocker.patch.object(hosts_and_folders.Folder, "add_subfolders", add_subfolders, create=True)

    def f(name, title, root_dir="/", parent_folder=None, may_see=True):
        folder = hosts_and_folders.Folder(
            name, folder_path=None, parent_folder=parent_folder, title=title, root_dir=root_dir
        )
        # Attribute only used for testing
        folder._may_see = may_see  # type: ignore[attr-defined]
        return folder

    return f


def only_root(folder):
    root_folder = folder("", title="Main")
    root_folder._loaded_subfolders = {}
    return root_folder


def three_levels(folder):
    return folder("", title="Main").add_subfolders(
        [
            folder("a", title="A").add_subfolders(
                [
                    folder("c", title="C"),
                    folder("d", title="D"),
                ]
            ),
            folder("b", title="B").add_subfolders(
                [
                    folder("e", title="E").add_subfolders(
                        [
                            folder("f", title="F"),
                        ]
                    ),
                ]
            ),
        ]
    )


def three_levels_leaf_permissions(folder):
    return folder("", title="Main", may_see=False).add_subfolders(
        [
            folder("a", title="A", may_see=False).add_subfolders(
                [
                    folder("c", title="C", may_see=False),
                    folder("d", title="D"),
                ]
            ),
            folder("b", title="B", may_see=False).add_subfolders(
                [
                    folder("e", title="E", may_see=False).add_subfolders(
                        [
                            folder("f", title="F"),
                        ]
                    ),
                ]
            ),
        ]
    )


@pytest.mark.parametrize(
    "actual_builder,expected",
    [
        (only_root, [("", "Main")]),
        (
            three_levels,
            [
                ("", "Main"),
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
                ("", "Main"),
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


def test_recursive_subfolder_choices_function_calls(mocker: MagicMock, make_folder):
    """Every folder should only be visited once"""
    spy = mocker.spy(hosts_and_folders.Folder, "_walk_tree")

    tree = three_levels_leaf_permissions(make_folder)
    tree.recursive_subfolder_choices()

    assert spy.call_count == 7


def test_subfolder_creation() -> None:
    folder = hosts_and_folders.Folder.root_folder()
    folder.create_subfolder("foo", "Foo Folder", {})

    # Upon instantiation, all the subfolders should be already known.
    folder = hosts_and_folders.Folder.root_folder()
    assert len(folder._subfolders) == 1


def test_match_item_generator_hosts() -> None:
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
        ).generate_match_items()
    ) == [
        MatchItem(
            title="host",
            topic="Hosts",
            url="some_url",
            match_texts=["host", "alias", "1.2.3.4", "5.6.7.8"],
        )
    ]


@dataclass
class _TreeStructure:
    path: str
    attributes: Dict[str, Any]
    subfolders: List["_TreeStructure"]
    num_hosts: int = 0


def make_monkeyfree_folder(tree_structure, parent=None) -> hosts_and_folders.CREFolder:
    new_folder = hosts_and_folders.CREFolder(
        tree_structure.path,
        parent_folder=parent,
        title=f"Title of {tree_structure.path}",
        attributes=tree_structure.attributes,
    )

    # Small monkeys :(
    new_folder._num_hosts = tree_structure.num_hosts
    new_folder._path_existing_folder = tree_structure.path

    for subtree_structure in tree_structure.subfolders:
        new_folder._subfolders[subtree_structure.path] = make_monkeyfree_folder(
            subtree_structure, new_folder
        )
        new_folder._path_existing_folder = tree_structure.path

    return new_folder


def dump_wato_folder_structure(wato_folder: hosts_and_folders.CREFolder):
    # Debug function to have a look at the internal folder tree structure
    sys.stdout.write("\n")

    def dump_structure(wato_folder: hosts_and_folders.CREFolder, indent=0):
        indent_space = " " * indent * 6
        sys.stdout.write(f"{indent_space + '->' + str(wato_folder):80} {wato_folder.path()}\n")
        sys.stdout.write(
            "\n".join(
                f"{indent_space}  {x}" for x in pprint.pformat(wato_folder.attributes()).split("\n")
            )
            + "\n"
        )
        for subfolder in wato_folder.subfolders():
            dump_structure(subfolder, indent + 1)

    dump_structure(wato_folder)


@pytest.mark.parametrize(
    "structure,testfolder_expected_groups",
    [
        # Basic inheritance
        (
            _TreeStructure(
                "",
                {
                    "contactgroups": {
                        "groups": ["group1"],
                        "recurse_perms": False,
                        "use": False,
                        "use_for_services": False,
                        "recurse_use": False,
                    }
                },
                [
                    _TreeStructure("sub1", {}, [_TreeStructure("testfolder", {}, [])]),
                ],
            ),
            {"group1"},
        ),
        # Blocked inheritance by sub1
        (
            _TreeStructure(
                "",
                {
                    "contactgroups": {
                        "groups": ["group1"],
                        "recurse_perms": False,
                        "use": False,
                        "use_for_services": False,
                        "recurse_use": False,
                    }
                },
                [
                    _TreeStructure(
                        "sub1",
                        {
                            "contactgroups": {
                                "groups": [],
                                "recurse_perms": False,
                                "use": False,
                                "use_for_services": False,
                                "recurse_use": False,
                            }
                        },
                        [_TreeStructure("testfolder", {}, [])],
                    ),
                ],
            ),
            set(),
        ),
        # Used recurs_perms(bypasses inheritance)
        (
            _TreeStructure(
                "",
                {
                    "contactgroups": {
                        "groups": ["group1"],
                        "recurse_perms": True,
                        "use": False,
                        "use_for_services": False,
                        "recurse_use": False,
                    }
                },
                [
                    _TreeStructure(
                        "sub1",
                        {
                            "contactgroups": {
                                "groups": [],
                                "recurse_perms": False,
                                "use": False,
                                "use_for_services": False,
                                "recurse_use": False,
                            }
                        },
                        [_TreeStructure("testfolder", {}, [])],
                    ),
                ],
            ),
            {"group1"},
        ),
        # Used recurs_perms (bypasses inheritance), test multiple groups
        (
            _TreeStructure(
                "",
                {
                    "contactgroups": {
                        "groups": ["group1"],
                        "recurse_perms": True,
                        "use": False,
                        "use_for_services": False,
                        "recurse_use": False,
                    }
                },
                [
                    _TreeStructure(
                        "sub1",
                        {
                            "contactgroups": {
                                "groups": ["group2"],
                                "recurse_perms": False,
                                "use": False,
                                "use_for_services": False,
                                "recurse_use": False,
                            }
                        },
                        [_TreeStructure("testfolder", {}, [])],
                    ),
                ],
            ),
            {"group1", "group2"},
        ),
    ],
)
def test_folder_permissions(structure, testfolder_expected_groups):
    wato_folder = make_monkeyfree_folder(structure)
    # dump_wato_folder_structure(wato_folder)
    testfolder = wato_folder._subfolders["sub1"]._subfolders["testfolder"]
    permitted_groups_cre_folder, _host_contact_groups, _use_for_service = testfolder.groups()
    assert permitted_groups_cre_folder == testfolder_expected_groups

    all_folders = _convert_folder_tree_to_all_folders(wato_folder)
    permitted_groups_bulk = hosts_and_folders._get_permitted_groups_of_all_folders(all_folders)
    assert permitted_groups_bulk["sub1/testfolder"].actual_groups == testfolder_expected_groups


def _convert_folder_tree_to_all_folders(
    root_folder,
) -> Dict[hosts_and_folders.PathWithoutSlash, hosts_and_folders.CREFolder]:
    all_folders = {}

    def parse_folder(folder):
        all_folders[folder.path()] = folder
        for subfolder in folder.subfolders():
            parse_folder(subfolder)

    parse_folder(root_folder)
    return all_folders


@dataclass
class _UserTest:
    contactgroups: List[ContactgroupName]
    hide_folders_without_permission: bool
    expected_num_hosts: int
    fix_legacy_visibility: bool = False


@contextmanager
def hide_folders_without_permission(do_hide) -> Iterator[None]:
    old_value = active_config.wato_hide_folders_without_read_permissions
    try:
        active_config.wato_hide_folders_without_read_permissions = do_hide
        yield
    finally:
        active_config.wato_hide_folders_without_read_permissions = old_value


def _default_groups(configured_groups: List[ContactgroupName]):
    return {
        "contactgroups": {
            "groups": configured_groups,
            "recurse_perms": False,
            "use": False,
            "use_for_services": False,
            "recurse_use": False,
        }
    }


group_tree_structure = _TreeStructure(
    "",
    _default_groups(["group1"]),
    [
        _TreeStructure(
            "sub1.1",
            {},
            [
                _TreeStructure(
                    "sub2.1",
                    _default_groups(["supersecret_group"]),
                    [],
                    100,
                ),
            ],
            8,
        ),
        _TreeStructure(
            "sub1.2",
            _default_groups(["group2"]),
            [],
            3,
        ),
        _TreeStructure(
            "sub1.3",
            _default_groups(["group1", "group3"]),
            [],
            1,
        ),
    ],
    5,
)

group_tree_test = (
    group_tree_structure,
    [
        _UserTest([], True, 0, True),
        _UserTest(["nomatch"], True, 0, True),
        _UserTest(["group2"], True, 3, True),
        _UserTest(["group1", "group2"], True, 17, False),
        _UserTest(["group1", "group2"], False, 117, False),
    ],
)


@pytest.mark.usefixtures("with_user_login")
@pytest.mark.parametrize(
    "structure, user_tests",
    [group_tree_test],
)
def test_num_hosts_normal_user(structure, user_tests, monkeypatch):
    for user_test in user_tests:
        _run_num_host_test(
            structure,
            user_test,
            user_test.expected_num_hosts,
            False,
            monkeypatch,
        )


@pytest.mark.usefixtures("with_admin_login")
@pytest.mark.parametrize(
    "structure, user_tests",
    [group_tree_test],
)
def test_num_hosts_admin_user(structure, user_tests, monkeypatch):
    for user_test in user_tests:
        _run_num_host_test(structure, user_test, 117, True, monkeypatch)


def _run_num_host_test(structure, user_test, expected_host_count, is_admin, monkeypatch):
    wato_folder = make_monkeyfree_folder(structure)
    with hide_folders_without_permission(user_test.hide_folders_without_permission):
        # The algorithm implemented in CREFolder actually computes the num_hosts_recursively wrong.
        # It does not exclude hosts in the questioned base folder, even when it should adhere
        # the visibility permissions. This error is not visible in the GUI since another(..)
        # function filters those folders in advance
        legacy_base_folder_host_offset = (
            0
            if (not user_test.fix_legacy_visibility or is_admin)
            else (structure.num_hosts if user_test.hide_folders_without_permission else 0)
        )

        # Old mechanism
        monkeypatch.setattr(userdb, "contactgroups_of_user", lambda u: user_test.contactgroups)
        assert (
            wato_folder.num_hosts_recursively()
            == expected_host_count + legacy_base_folder_host_offset
        )

        # New mechanism
        with get_fake_setup_redis_client(
            monkeypatch,
            _convert_folder_tree_to_all_folders(wato_folder),
            [_fake_redis_num_hosts_answer(wato_folder)],
        ):
            assert wato_folder.num_hosts_recursively() == expected_host_count


def _fake_redis_num_hosts_answer(wato_folder: hosts_and_folders.CREFolder):
    redis_answer = []
    for folder in _convert_folder_tree_to_all_folders(wato_folder).values():
        redis_answer.extend([",".join(folder.groups()[0]), str(folder._num_hosts)])
    return [redis_answer]


@contextmanager
def get_fake_setup_redis_client(monkeypatch, all_folders, redis_answers: List):
    monkeypatch.setattr(hosts_and_folders, "may_use_redis", lambda: True)
    mock_redis_client = MockRedisClient(redis_answers)
    monkeypatch.setattr(hosts_and_folders._RedisHelper, "_cache_integrity_ok", lambda x: True)
    redis_helper = hosts_and_folders.get_wato_redis_client()
    monkeypatch.setattr(redis_helper, "_client", mock_redis_client)
    monkeypatch.setattr(redis_helper, "_folder_paths", [f"{x}/" for x in all_folders.keys()])
    monkeypatch.setattr(
        redis_helper,
        "_folder_metadata",
        {
            f"{x}/": hosts_and_folders.FolderMetaData(f"{x}/", "nix", "nix", [])
            for x in all_folders.keys()
        },
    )
    yield mock_redis_client
    monkeypatch.setattr(hosts_and_folders, "may_use_redis", lambda: False)
    # I have no idea if this is actually working..
    monkeypatch.undo()


class MockRedisClient:
    def __init__(self, answers: List[List[str]]):
        class FakePipeline:
            def __init__(self, answers):
                self._answers = answers

            def execute(self):
                return self._answers.pop(0)

            def __getattr__(self, name):
                return lambda *args, **kwargs: None

        self._fake_pipeline = FakePipeline(answers)
        self._answers = answers

    def __getattr__(self, name):
        if name == "pipeline":
            return lambda: self._fake_pipeline

        return lambda *args, **kwargs: lambda *args, **kwargs: None


@pytest.mark.usefixtures("with_admin_login")
def test_load_redis_folders_on_demand(monkeypatch):
    wato_folder = make_monkeyfree_folder(group_tree_structure)
    with get_fake_setup_redis_client(
        monkeypatch, _convert_folder_tree_to_all_folders(wato_folder), []
    ):
        hosts_and_folders.CREFolder.all_folders()
        # Check if wato_folders class matches
        assert isinstance(g.wato_folders, hosts_and_folders.WATOFoldersOnDemand)
        # Check if item is None
        assert g.wato_folders._raw_dict.__getitem__("sub1.1") is None
        # Check if item is generated on access
        assert isinstance(g.wato_folders["sub1.1"], hosts_and_folders.CREFolder)
        # Check if item is now set in dict
        assert isinstance(
            g.wato_folders._raw_dict.__getitem__("sub1.1"), hosts_and_folders.CREFolder
        )

        # Check if other folder is still None
        assert g.wato_folders._raw_dict.__getitem__("sub1.2") is None
        # Check if parent(main) folder got instantiated as well
        assert isinstance(g.wato_folders._raw_dict.__getitem__(""), hosts_and_folders.CREFolder)


def test_folder_exists(mocker: MagicMock, tmp_path: Path) -> None:
    mocker.patch.object(cmk.utils.paths, "check_mk_config_dir", str(tmp_path))
    (tmp_path / "wato" / "foo" / "bar").mkdir(parents=True)
    assert hosts_and_folders.Folder.folder_exists("foo")
    assert hosts_and_folders.Folder.folder_exists("foo/bar")
    assert not hosts_and_folders.Folder.folder_exists("bar")
    assert not hosts_and_folders.Folder.folder_exists("foo/foobar")
    with pytest.raises(MKUserError):
        hosts_and_folders.Folder.folder_exists("../wato")
