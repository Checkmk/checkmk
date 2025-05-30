#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import datetime
import os
import pprint
import shutil
import sys
import time
import uuid
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from itertools import count
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
import time_machine
from pytest import MonkeyPatch

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId

from cmk.utils.redis import disable_redis

from cmk.gui import userdb
from cmk.gui.config import active_config
from cmk.gui.ctx_stack import g
from cmk.gui.exceptions import MKUserError
from cmk.gui.logged_in import user as logged_in_user
from cmk.gui.watolib import hosts_and_folders
from cmk.gui.watolib.audit_log import AuditLogStore
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.host_match_item_generator import MatchItemGeneratorHosts
from cmk.gui.watolib.hosts_and_folders import EffectiveAttributes, Folder, folder_tree
from cmk.gui.watolib.search import MatchItem


def test_effective_attributes() -> None:
    counter = count()

    def compute_attributes() -> HostAttributes:
        return {"alias": str(next(counter))}

    attributes = EffectiveAttributes(compute_attributes)
    first_attributes = attributes()
    assert first_attributes == attributes()

    attributes.drop_caches()
    assert first_attributes != attributes()


@pytest.fixture(autouse=True)
def test_env(with_admin_login: UserId, load_config: None) -> Iterator[None]:
    # Ensure we have clean folder/host caches
    tree = folder_tree()
    tree.invalidate_caches()

    yield

    # Cleanup WATO folders created by the test
    shutil.rmtree(tree.root_folder().filesystem_path(), ignore_errors=True)
    os.makedirs(tree.root_folder().filesystem_path())


@pytest.mark.parametrize(
    "attributes,expected_tags",
    [
        (
            # Old key tag_snmp is mgrated to tag_snmp_ds
            HostAttributes(  # type: ignore[typeddict-unknown-key]
                {
                    "tag_snmp": "no-snmp",
                    "tag_agent": "no-agent",
                    "site": SiteId("ding"),
                }
            ),
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
            # Old key tag_snmp is mgrated to tag_snmp_ds
            HostAttributes(  # type: ignore[typeddict-unknown-key]
                {
                    "tag_snmp": "no-snmp",
                    "tag_agent": "no-agent",
                    "tag_address_family": "no-ip",
                }
            ),
            {
                "address_family": "no-ip",
                "agent": "no-agent",
                "piggyback": "auto-piggyback",
                "site": "NO_SITE",
                "snmp_ds": "no-snmp",
            },
        ),
        (
            HostAttributes(
                {
                    "site": SiteId(""),
                }
            ),
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
def test_host_tags(attributes: HostAttributes, expected_tags: dict[str, str]) -> None:
    folder = folder_tree().root_folder()
    host = hosts_and_folders.Host(folder, HostName("test-host"), attributes, cluster_nodes=None)

    assert host.tag_groups() == expected_tags


@pytest.mark.parametrize(
    "attributes,result",
    [
        (
            HostAttributes(
                {
                    "tag_snmp_ds": "no-snmp",
                    "tag_agent": "no-agent",
                }
            ),
            True,
        ),
        (
            HostAttributes(
                {
                    "tag_snmp_ds": "no-snmp",
                    "tag_agent": "cmk-agent",
                }
            ),
            False,
        ),
        (
            HostAttributes(
                {
                    "tag_snmp_ds": "no-snmp",
                    "tag_agent": "no-agent",
                    "tag_address_family": "no-ip",
                }
            ),
            False,
        ),
    ],
)
def test_host_is_ping_host(attributes: HostAttributes, result: bool) -> None:
    folder = folder_tree().root_folder()
    host = hosts_and_folders.Host(folder, HostName("test-host"), attributes, cluster_nodes=None)

    assert host.is_ping_host() == result


@pytest.mark.parametrize(
    "attributes",
    [
        HostAttributes(
            {
                "tag_snmp_ds": "no-snmp",
                "tag_agent": "no-agent",
                "alias": "testalias",
                "parents": [HostName("ding"), HostName("dong")],
            }
        )
    ],
)
def test_write_and_read_host_attributes(attributes: HostAttributes) -> None:
    tree = folder_tree()
    # Used to write the data
    write_data_folder = hosts_and_folders.Folder.load(
        tree=tree, name="testfolder", parent_folder=tree.root_folder()
    )

    # Used to read the previously written data
    read_data_folder = hosts_and_folders.Folder.load(
        tree=tree, name="testfolder", parent_folder=tree.root_folder()
    )

    # Write data
    write_data_folder.create_hosts([(HostName("testhost"), attributes, [])], pprint_value=False)
    write_folder_hosts = write_data_folder.hosts()
    assert len(write_folder_hosts) == 1

    # Read data back
    read_folder_hosts = read_data_folder.hosts()
    assert len(read_folder_hosts) == 1
    for _, host in read_folder_hosts.items():
        assert host.attributes == {
            "meta_data": host.attributes["meta_data"],
            **attributes,
        }


def test_create_multiple_hosts() -> None:
    root = folder_tree().root_folder()
    subfolder = root.create_subfolder("subfolder", "subfolder", {}, pprint_value=False)

    root.create_hosts([(HostName("host-1"), {}, [])], pprint_value=False)
    subfolder.create_hosts([(HostName("host-2"), {}, [])], pprint_value=False)

    all_hosts = root.all_hosts_recursively()
    # to ensure that new folder instances contain the new hosts
    all_hosts_new = folder_tree().root_folder().all_hosts_recursively()

    assert "host-1" in all_hosts
    assert "host-2" in all_hosts
    assert "host-1" in all_hosts_new
    assert "host-2" in all_hosts_new


@contextmanager
def in_chdir(directory: str) -> Iterator[None]:
    cur = os.getcwd()
    os.chdir(directory)
    try:
        yield
    finally:
        os.chdir(cur)


def test_create_nested_folders(request_context: None) -> None:
    with in_chdir("/"):
        tree = folder_tree()
        root = tree.root_folder()

        folder1 = hosts_and_folders.Folder.new(tree=tree, name="folder1", parent_folder=root)
        folder1.save_folder_attributes()

        folder2 = hosts_and_folders.Folder.new(tree=tree, name="folder2", parent_folder=folder1)
        folder2.save_folder_attributes()

        shutil.rmtree(os.path.dirname(folder1.wato_info_path()))


def test_eq_operation(request_context: None) -> None:
    with in_chdir("/"):
        tree = folder_tree()
        root = tree.root_folder()
        folder1 = hosts_and_folders.Folder.new(tree=tree, name="folder1", parent_folder=root)
        folder1.save_folder_attributes()

        folder1_new = hosts_and_folders.Folder.load(tree=tree, name="folder1", parent_folder=root)

        assert folder1 == folder1_new
        assert id(folder1) != id(folder1_new)
        assert folder1 in [folder1_new]

        folder2 = hosts_and_folders.Folder.new(tree=tree, name="folder2", parent_folder=folder1)
        folder2.save_folder_attributes()

        assert folder1 not in [folder2]


def _not_in_latest_log(secret: str) -> bool:
    """Check that the most recent entry does not contain the secret"""
    return secret not in (AuditLogStore().read()[-1].diff_text or "")


def test_mgmt_inherit_credentials_explicit_host_snmp() -> None:
    folder = folder_tree().root_folder()
    folder.attributes["management_snmp_community"] = "FOLDER"

    folder.create_hosts(
        [
            (
                HostName("test-host"),
                HostAttributes(
                    {
                        "ipaddress": HostAddress("127.0.0.1"),
                        "management_protocol": "snmp",
                        "management_snmp_community": "HOST",
                    }
                ),
                [],
            )
        ],
        pprint_value=False,
    )

    data = folder._load_hosts_file()
    assert data is not None
    assert data["management_protocol"]["test-host"] == "snmp"
    assert data["management_snmp_credentials"]["test-host"] == "HOST"

    assert _not_in_latest_log("HOST")


def test_mgmt_inherit_credentials_explicit_host_ipmi() -> None:
    folder = folder_tree().root_folder()
    folder.attributes["management_ipmi_credentials"] = {
        "username": "FOLDERUSER",
        "password": "FOLDERPASS",
    }

    folder.create_hosts(
        [
            (
                HostName("test-host"),
                HostAttributes(
                    {
                        "ipaddress": HostAddress("127.0.0.1"),
                        "management_protocol": "ipmi",
                        "management_ipmi_credentials": {
                            "username": "USER",
                            "password": "PASS",
                        },
                    }
                ),
                [],
            )
        ],
        pprint_value=False,
    )

    data = folder._load_hosts_file()
    assert data is not None
    assert data["management_protocol"]["test-host"] == "ipmi"
    assert data["management_ipmi_credentials"]["test-host"] == {
        "username": "USER",
        "password": "PASS",
    }

    assert _not_in_latest_log("PASS")


def test_mgmt_inherit_credentials_snmp() -> None:
    folder = folder_tree().root_folder()
    folder.attributes["management_snmp_community"] = "FOLDER"

    folder.create_hosts(
        [
            (
                HostName("mgmt-host"),
                {
                    "ipaddress": HostAddress("127.0.0.1"),
                    "management_protocol": "snmp",
                },
                [],
            )
        ],
        pprint_value=False,
    )

    data = folder._load_hosts_file()
    assert data is not None
    assert data["management_protocol"]["mgmt-host"] == "snmp"
    assert data["management_snmp_credentials"]["mgmt-host"] == "FOLDER"

    assert _not_in_latest_log("FOLDER")


def test_mgmt_inherit_credentials_ipmi() -> None:
    folder = folder_tree().root_folder()
    folder.attributes["management_ipmi_credentials"] = {
        "username": "FOLDERUSER",
        "password": "FOLDERPASS",
    }

    folder.create_hosts(
        [
            (
                HostName("mgmt-host"),
                {
                    "ipaddress": HostAddress("127.0.0.1"),
                    "management_protocol": "ipmi",
                },
                [],
            )
        ],
        pprint_value=False,
    )

    data = folder._load_hosts_file()
    assert data is not None
    assert data["management_protocol"]["mgmt-host"] == "ipmi"
    assert data["management_ipmi_credentials"]["mgmt-host"] == {
        "username": "FOLDERUSER",
        "password": "FOLDERPASS",
    }

    assert _not_in_latest_log("FOLDERPASS")


def test_mgmt_inherit_protocol_explicit_host_snmp() -> None:
    folder = folder_tree().root_folder()
    folder.attributes["management_protocol"] = None
    folder.attributes["management_snmp_community"] = "FOLDER"

    folder.create_hosts(
        [
            (
                HostName("mgmt-host"),
                {
                    "ipaddress": HostAddress("127.0.0.1"),
                    "management_protocol": "snmp",
                    "management_snmp_community": "HOST",
                },
                [],
            )
        ],
        pprint_value=False,
    )

    data = folder._load_hosts_file()
    assert data is not None
    assert data["management_protocol"]["mgmt-host"] == "snmp"
    assert data["management_snmp_credentials"]["mgmt-host"] == "HOST"

    assert _not_in_latest_log("HOST")


def test_mgmt_inherit_protocol_explicit_host_ipmi() -> None:
    folder = folder_tree().root_folder()
    folder.attributes["management_protocol"] = None
    folder.attributes["management_ipmi_credentials"] = {
        "username": "FOLDERUSER",
        "password": "FOLDERPASS",
    }

    folder.create_hosts(
        [
            (
                HostName("mgmt-host"),
                {
                    "ipaddress": HostAddress("127.0.0.1"),
                    "management_protocol": "ipmi",
                    "management_ipmi_credentials": {
                        "username": "USER",
                        "password": "PASS",
                    },
                },
                [],
            )
        ],
        pprint_value=False,
    )

    data = folder._load_hosts_file()
    assert data is not None
    assert data["management_protocol"]["mgmt-host"] == "ipmi"
    assert data["management_ipmi_credentials"]["mgmt-host"] == {
        "username": "USER",
        "password": "PASS",
    }

    assert _not_in_latest_log("PASS")


@pytest.fixture(name="patch_may")
def fixture_patch_may(mocker: MagicMock) -> None:
    def prefixed_title(self_: hosts_and_folders.Folder, current_depth: int, pretty: bool) -> str:
        return "_" * current_depth + self_.title()

    mocker.patch.object(hosts_and_folders.Folder, "_prefixed_title", prefixed_title)

    def may(self_, _permission):
        return getattr(self_, "_may_see", True)

    mocker.patch.object(hosts_and_folders.PermissionChecker, "may", may)


def only_root() -> hosts_and_folders.Folder:
    root_folder = folder_tree().root_folder()
    root_folder._loaded_subfolders = {}
    return root_folder


def three_levels() -> hosts_and_folders.Folder:
    main = folder_tree().root_folder()

    a = main.create_subfolder("a", title="A", attributes={}, pprint_value=False)
    a.create_subfolder("c", title="C", attributes={}, pprint_value=False)
    a.create_subfolder("d", title="D", attributes={}, pprint_value=False)

    b = main.create_subfolder("b", title="B", attributes={}, pprint_value=False)
    e = b.create_subfolder("e", title="E", attributes={}, pprint_value=False)
    e.create_subfolder("f", title="F", attributes={}, pprint_value=False)

    return main


def three_levels_leaf_permissions() -> hosts_and_folders.Folder:
    main = folder_tree().root_folder()

    # Attribute only used for testing
    main.permissions._may_see = False  # type: ignore[attr-defined]

    a = main.create_subfolder("a", title="A", attributes={}, pprint_value=False)
    a.permissions._may_see = False  # type: ignore[attr-defined]
    c = a.create_subfolder("c", title="C", attributes={}, pprint_value=False)
    c.permissions._may_see = False  # type: ignore[attr-defined]
    a.create_subfolder("d", title="D", attributes={}, pprint_value=False)

    b = main.create_subfolder("b", title="B", attributes={}, pprint_value=False)
    b.permissions._may_see = False  # type: ignore[attr-defined]
    e = b.create_subfolder("e", title="E", attributes={}, pprint_value=False)
    e.permissions._may_see = False  # type: ignore[attr-defined]
    e.create_subfolder("f", title="F", attributes={}, pprint_value=False)

    return main


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
@pytest.mark.usefixtures("patch_may")
def test_recursive_subfolder_choices(
    monkeypatch: MonkeyPatch,
    actual_builder: Callable[[], hosts_and_folders.Folder],
    expected: list[tuple[str, str]],
) -> None:
    with monkeypatch.context() as m:
        m.setattr(active_config, "wato_hide_folders_without_read_permissions", True)
        assert actual_builder().recursive_subfolder_choices() == expected


@pytest.mark.usefixtures("patch_may")
def test_recursive_subfolder_choices_function_calls(
    monkeypatch: MonkeyPatch, mocker: MagicMock
) -> None:
    """Every folder should only be visited once"""
    with monkeypatch.context() as m:
        m.setattr(active_config, "wato_hide_folders_without_read_permissions", True)
        spy = mocker.spy(hosts_and_folders.Folder, "_walk_tree")
        tree = three_levels_leaf_permissions()
        tree.recursive_subfolder_choices()
        assert spy.call_count == 7


def test_subfolder_creation() -> None:
    folder = folder_tree().root_folder()
    folder.create_subfolder("foo", "Foo Folder", {}, pprint_value=False)

    # Upon instantiation, all the subfolders should be already known.
    folder = folder_tree().root_folder()
    assert len(folder._subfolders) == 1


def test_match_item_generator_hosts() -> None:
    assert list(
        MatchItemGeneratorHosts(
            HostName("hosts"),
            lambda: {
                HostName("host"): {
                    "edit_url": "some_url",
                    "alias": "alias",
                    "ipaddress": HostAddress("1.2.3.4"),
                    "ipv6address": HostAddress(""),
                    "additional_ipv4addresses": [HostAddress("5.6.7.8")],
                    "additional_ipv6addresses": [],
                    "path": "",
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
    attributes: HostAttributes
    subfolders: list["_TreeStructure"]
    num_hosts: int = 0


def make_monkeyfree_folder(
    tree_structure: _TreeStructure, parent: hosts_and_folders.Folder | None = None
) -> hosts_and_folders.Folder:
    tree = hosts_and_folders.folder_tree()
    if parent is None:
        new_folder = tree.root_folder()
        new_folder.attributes = tree_structure.attributes
    else:
        new_folder = hosts_and_folders.Folder.new(
            tree=tree,
            name=tree_structure.path,
            parent_folder=parent,
            title=f"Title of {tree_structure.path}",
            attributes=tree_structure.attributes,
        )

    # Small monkeys :(
    new_folder._num_hosts = tree_structure.num_hosts
    new_folder._path = tree_structure.path

    for subtree_structure in tree_structure.subfolders:
        new_folder._subfolders[subtree_structure.path] = make_monkeyfree_folder(
            subtree_structure, new_folder
        )
        new_folder._path = tree_structure.path

    return new_folder


def dump_wato_folder_structure(wato_folder: hosts_and_folders.Folder) -> None:
    # Debug function to have a look at the internal folder tree structure
    sys.stdout.write("\n")

    def dump_structure(wato_folder: hosts_and_folders.Folder, indent: int = 0) -> None:
        indent_space = " " * indent * 6
        sys.stdout.write(f"{indent_space + '->' + str(wato_folder):80} {wato_folder.path()}\n")
        sys.stdout.write(
            "\n".join(
                f"{indent_space}  {x}" for x in pprint.pformat(wato_folder.attributes).split("\n")
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
def test_folder_permissions(
    structure: _TreeStructure, testfolder_expected_groups: set[str]
) -> None:
    with disable_redis():
        wato_folder = make_monkeyfree_folder(structure)
        # dump_wato_folder_structure(wato_folder)
        testfolder = wato_folder._subfolders["sub1"]._subfolders["testfolder"]
        permitted_groups_cre_folder, _host_contact_groups, _use_for_service = testfolder.groups()
        assert permitted_groups_cre_folder == testfolder_expected_groups

        all_folders = _convert_folder_tree_to_all_folders(wato_folder)
        permitted_groups_bulk = hosts_and_folders._get_permitted_groups_of_all_folders(all_folders)
        assert permitted_groups_bulk["sub1/testfolder"].actual_groups == testfolder_expected_groups


def _convert_folder_tree_to_all_folders(
    root_folder: hosts_and_folders.Folder,
) -> dict[hosts_and_folders.PathWithoutSlash, hosts_and_folders.Folder]:
    all_folders = {}

    def parse_folder(folder):
        all_folders[folder.path()] = folder
        for subfolder in folder.subfolders():
            parse_folder(subfolder)

    parse_folder(root_folder)
    return all_folders


@dataclass
class _UserTest:
    contactgroups: list[str]
    hide_folders_without_permission: bool
    expected_num_hosts: int
    fix_legacy_visibility: bool = False


@contextmanager
def hide_folders_without_permission(do_hide: bool) -> Iterator[None]:
    old_value = active_config.wato_hide_folders_without_read_permissions
    try:
        active_config.wato_hide_folders_without_read_permissions = do_hide
        yield
    finally:
        active_config.wato_hide_folders_without_read_permissions = old_value


def _default_groups(configured_groups: list[str]) -> HostAttributes:
    return HostAttributes(
        {
            "contactgroups": {
                "groups": configured_groups,
                "recurse_perms": False,
                "use": False,
                "use_for_services": False,
                "recurse_use": False,
            }
        }
    )


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
def test_num_hosts_normal_user(
    structure: _TreeStructure, user_tests: list[_UserTest], monkeypatch: MonkeyPatch
) -> None:
    with disable_redis():
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
def test_num_hosts_admin_user(
    structure: _TreeStructure, user_tests: list[_UserTest], monkeypatch: MonkeyPatch
) -> None:
    with disable_redis():
        for user_test in user_tests:
            _run_num_host_test(structure, user_test, 117, True, monkeypatch)


def _run_num_host_test(
    structure: _TreeStructure,
    user_test: _UserTest,
    expected_host_count: int,
    is_admin: bool,
    monkeypatch: MonkeyPatch,
) -> None:
    wato_folder = make_monkeyfree_folder(structure)
    with hide_folders_without_permission(user_test.hide_folders_without_permission):
        # The algorithm implemented in Folder actually computes the num_hosts_recursively wrong.
        # It does not exclude hosts in the questioned base folder, even when it should adhere
        # the visibility permissions. This error is not visible in the GUI since another(..)
        # function filters those folders in advance
        legacy_base_folder_host_offset = (
            0
            if (not user_test.fix_legacy_visibility or is_admin)
            else (structure.num_hosts if user_test.hide_folders_without_permission else 0)
        )

        # Old mechanism
        with patch.dict(logged_in_user.attributes, {"contactgroups": user_test.contactgroups}):
            assert (
                wato_folder.num_hosts_recursively()
                == expected_host_count + legacy_base_folder_host_offset
            )

        # New mechanism
        monkeypatch.setattr(userdb, "contactgroups_of_user", lambda u: user_test.contactgroups)
        with get_fake_setup_redis_client(
            monkeypatch,
            _convert_folder_tree_to_all_folders(wato_folder),
            [_fake_redis_num_hosts_answer(wato_folder)],
        ):
            assert wato_folder.num_hosts_recursively() == expected_host_count


def _fake_redis_num_hosts_answer(wato_folder: hosts_and_folders.Folder) -> list[list[str]]:
    redis_answer = []
    for folder in _convert_folder_tree_to_all_folders(wato_folder).values():
        redis_answer.extend([",".join(folder.groups()[0]), str(folder._num_hosts)])
    return [redis_answer]


class MockRedisClient:
    def __init__(self, answers: list[list[list[str]]]) -> None:
        class FakePipeline:
            def __init__(self, answers: list[list[list[str]]]) -> None:
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


@contextmanager
def get_fake_setup_redis_client(
    monkeypatch: MonkeyPatch,
    all_folders: dict[hosts_and_folders.PathWithoutSlash, hosts_and_folders.Folder],
    redis_answers: list[list[list[str]]],
) -> Iterator[MockRedisClient]:
    try:
        monkeypatch.setattr(hosts_and_folders, "may_use_redis", lambda: True)
        mock_redis_client = MockRedisClient(redis_answers)
        monkeypatch.setattr(hosts_and_folders._RedisHelper, "_cache_integrity_ok", lambda x: True)
        tree = folder_tree()
        redis_helper = hosts_and_folders.get_wato_redis_client(tree)
        monkeypatch.setattr(redis_helper, "_client", mock_redis_client)
        monkeypatch.setattr(redis_helper, "_folder_paths", [f"{x}/" for x in all_folders.keys()])
        monkeypatch.setattr(
            redis_helper,
            "_folder_metadata",
            {
                f"{x}/": hosts_and_folders.FolderMetaData(tree, f"{x}/", "nix", "nix", [])
                for x in all_folders.keys()
            },
        )
        yield mock_redis_client
    finally:
        monkeypatch.setattr(hosts_and_folders, "may_use_redis", lambda: False)
        # I have no idea if this is actually working..
        monkeypatch.undo()


@pytest.mark.usefixtures("with_admin_login")
def test_load_redis_folders_on_demand(monkeypatch: MonkeyPatch) -> None:
    wato_folder = make_monkeyfree_folder(group_tree_structure)
    folder_tree().invalidate_caches()
    with get_fake_setup_redis_client(
        monkeypatch, _convert_folder_tree_to_all_folders(wato_folder), []
    ):
        folder_tree().all_folders()
        # Check if wato_folders class matches
        assert isinstance(g.wato_folders, hosts_and_folders.WATOFoldersOnDemand)
        # Check if item is None
        assert g.wato_folders._raw_dict["sub1.1"] is None
        # Check if item is generated on access
        assert isinstance(g.wato_folders["sub1.1"], hosts_and_folders.Folder)
        # Check if item is now set in dict
        assert isinstance(g.wato_folders._raw_dict["sub1.1"], hosts_and_folders.Folder)

        # Check if other folder is still None
        assert g.wato_folders._raw_dict["sub1.2"] is None
        # Check if parent(main) folder got instantiated as well
        assert isinstance(g.wato_folders._raw_dict[""], hosts_and_folders.Folder)


def test_folder_exists() -> None:
    tree = folder_tree()
    tree.root_folder().create_subfolder("foo", "foo", {}, pprint_value=False).create_subfolder(
        "bar", "bar", {}, pprint_value=False
    )
    assert tree.folder_exists("foo")
    assert tree.folder_exists("foo/bar")
    assert not tree.folder_exists("bar")
    assert not tree.folder_exists("foo/foobar")
    with pytest.raises(MKUserError):
        tree.folder_exists("../wato")


def test_folder_access() -> None:
    tree = folder_tree()
    tree.root_folder().create_subfolder("foo", "foo", {}, pprint_value=False).create_subfolder(
        "bar", "bar", {}, pprint_value=False
    )
    assert isinstance(tree.folder("foo/bar"), hosts_and_folders.Folder)
    assert isinstance(tree.folder(""), hosts_and_folders.Folder)
    with pytest.raises(MKGeneralException):
        tree.folder("unknown_folder")


def test_new_empty_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uuid, "uuid4", lambda: uuid.UUID("a8098c1a-f86e-11da-bd1a-00112444be1e"))
    tree = folder_tree()
    with time_machine.travel(datetime.datetime(2018, 1, 10, 2, tzinfo=ZoneInfo("UTC")), tick=False):
        folder = Folder.new(
            tree=tree,
            name="bla",
            title="Bla",
            attributes={},
            parent_folder=tree.root_folder(),
        )
    assert folder.name() == "bla"
    assert folder.id() == "a8098c1af86e11dabd1a00112444be1e"
    assert folder.title() == "Bla"
    assert folder.attributes == {
        "meta_data": {
            "created_at": 1515549600.0,
            "created_by": None,
            "updated_at": 1515549600.0,
        }
    }


def test_new_loaded_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uuid, "uuid4", lambda: uuid.UUID("c6bda767ae5c47038f73d8906fb91bb4"))

    tree = folder_tree()
    with time_machine.travel(datetime.datetime(2018, 1, 10, 2, tzinfo=ZoneInfo("UTC")), tick=False):
        folder1 = Folder.new(tree=tree, name="folder1", parent_folder=tree.root_folder())
        folder1.save_folder_attributes()
        tree.invalidate_caches()

    folder = Folder.load(tree=tree, name="folder1", parent_folder=tree.root_folder())
    assert folder.name() == "folder1"
    assert folder.id() == "c6bda767ae5c47038f73d8906fb91bb4"
    assert folder.title() == "folder1"
    assert folder.attributes == {
        "meta_data": {
            "created_at": 1515549600.0,
            "created_by": None,
            "updated_at": 1515549600.0,
        }
    }


@pytest.mark.parametrize(
    "allowed,last_end,next_time",
    [
        (((0, 0), (24, 0)), None, 1515546000.0),
        (
            ((0, 0), (24, 0)),
            1515549600.0,
            1515549900.0,
        ),
        (((20, 0), (24, 0)), None, 1515610800.0),
        ([((0, 0), (2, 0)), ((20, 0), (22, 0))], None, 1515546000.0),
        ([((0, 0), (2, 0)), ((20, 0), (22, 0))], 1515621600.0, 1515625200.0),
    ],
)
def test_next_network_scan_at(
    allowed: Sequence[tuple[tuple[int, int], tuple[int, int]]],
    last_end: float | None,
    next_time: float,
) -> None:
    tree = folder_tree()
    folder = Folder.new(
        tree=tree,
        parent_folder=tree.root_folder(),
        name="bla",
        title="Bla",
        attributes=HostAttributes(
            {
                "network_scan": {
                    "exclude_ranges": [],
                    "ip_ranges": [("ip_range", ("10.3.1.1", "10.3.1.100"))],
                    "run_as": UserId("cmkadmin"),
                    "scan_interval": 300,
                    "set_ipaddress": True,
                    "tag_criticality": "offline",
                    "time_allowed": allowed,
                },
                "network_scan_result": {
                    "start": last_end - 10 if last_end is not None else None,
                    "end": last_end,
                    "state": True,
                    "output": "",
                },
            }
        ),
    )

    with time_machine.travel(datetime.datetime(2018, 1, 10, 2, tzinfo=ZoneInfo("CET")), tick=False):
        assert folder.next_network_scan_at() == next_time


@pytest.mark.usefixtures("request_context")
def test_folder_times() -> None:
    tree = folder_tree()
    root = tree.root_folder()

    with time_machine.travel(datetime.datetime(2020, 2, 2, 2, 2, 2)):
        current = time.time()
        Folder.new(tree=tree, name="test", parent_folder=root).save_folder_attributes()
        folder_tree().invalidate_caches()
        folder = Folder.load(tree=tree, name="test", parent_folder=root)
        folder.save_folder_attributes()
        folder_tree().invalidate_caches()

    meta_data = folder.attributes["meta_data"]
    assert int(meta_data["created_at"]) == int(current)
    assert int(meta_data["updated_at"]) == int(current)

    folder.save_folder_attributes()
    assert int(meta_data["updated_at"]) > int(current)


def test_subfolder_attributes_are_cached() -> None:
    # GIVEN folder with cached attributes
    root = folder_tree().root_folder()
    subfolder = root.create_subfolder("sub1", "sub1", {"alias": "sub1"}, pprint_value=False)
    subfolder.effective_attributes()

    # WHEN
    subfolder.attributes["alias"] = "other_alias"

    # THEN return cached attribute
    assert subfolder.effective_attributes()["alias"] == "sub1"


def test_subfolder_cache_invalidated() -> None:
    # GIVEN folder with cached attributes
    subfolder = (
        folder_tree()
        .root_folder()
        .create_subfolder("sub1", "sub1", {"alias": "sub1"}, pprint_value=False)
    )
    subfolder.effective_attributes()

    # WHEN cache is invalidated from folder_tree and attribute is updated
    folder_tree().invalidate_caches()
    subfolder.attributes["alias"] = "other_alias"

    # THEN we read updated attribute
    # There is a bug when invalidating cache from folder_tree(), not all
    # subfolders are part of the tree
    with pytest.raises(AssertionError):
        assert subfolder.effective_attributes()["alias"] == "other_alias"
