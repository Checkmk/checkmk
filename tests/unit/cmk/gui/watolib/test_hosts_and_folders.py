#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import datetime
import os
import pprint
import shutil
import sys
import time
import uuid
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from itertools import count
from typing import cast
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
import time_machine
from pytest import MonkeyPatch
from redis import ConnectionError as RedisConnectionError
from redis import Redis
from redis import TimeoutError as RedisTimeoutError

import cmk.ruleset_matcher.tags
import cmk.utils.paths
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui import userdb
from cmk.gui.config import get_default_config, make_config_object
from cmk.gui.exceptions import MKUserError
from cmk.gui.logged_in import LoggedInSuperUser
from cmk.gui.logged_in import user as logged_in_user
from cmk.gui.search.matchers import MatchItem
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib import hosts_and_folders
from cmk.gui.watolib.audit_log import AuditLogStore, make_audit_log_change_hook
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.host_match_item_generator import MatchItemGeneratorHosts
from cmk.gui.watolib.hosts_and_folders import (
    all_folder_title_paths,
    EffectiveAttributes,
    Folder,
    folder_title_path,
    FolderTree,
    make_folder_tree,
)
from cmk.gui.watolib.pending_changes import NoopPendingChangesStore, PendingChanges
from cmk.livestatus_client import SiteConfigurations
from cmk.utils.redis import disable_redis

# Cheap in-memory acting user with all permissions. Avoids the expensive
# with_admin_login fixture (which creates a real user on disk) for tests that
# only need *an* authorized acting_user, not the request-global login.
_SUPERUSER = LoggedInSuperUser()


def _noop_pending_changes() -> PendingChanges:
    return PendingChanges(
        activation_sites=SiteConfigurations({}),
        local_site=SiteId("NO_SITE"),
        acting_user=None,
        store=NoopPendingChangesStore(),
        hooks=(make_audit_log_change_hook(use_git=False),),
    )


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
def tree() -> Iterator[FolderTree]:
    # Build the tree explicitly instead of using the request-global
    # folder_tree(), so no Flask request context is needed at all.
    # Computing effective attributes loads the users to determine the network
    # scan "run_as" default. Ensure the profile dir exists (usually done by
    # the load_config fixture).
    cmk.utils.paths.profile_dir.mkdir(parents=True, exist_ok=True)
    raw_config = get_default_config()
    raw_config["tags"] = cmk.ruleset_matcher.tags.get_effective_tag_config(raw_config["wato_tags"])
    # Tests may allow_redis, but our bookkeeping shall not use it: building
    # the tree with redis disabled makes it pick the null folder cache. Tests
    # exercising the redis cache inject their own (see
    # get_fake_setup_redis_client).
    with disable_redis():
        tree = make_folder_tree(make_config_object(raw_config))
        tree.invalidate_caches()

    yield tree

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
def test_host_tags(
    attributes: HostAttributes, expected_tags: dict[str, str], tree: FolderTree
) -> None:
    folder = tree.root_folder()
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
def test_host_is_ping_host(attributes: HostAttributes, result: bool, tree: FolderTree) -> None:
    folder = tree.root_folder()
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
def test_write_and_read_host_attributes(attributes: HostAttributes, tree: FolderTree) -> None:
    # Used to write the data
    write_data_folder = hosts_and_folders.Folder.load(
        tree=tree, name="testfolder", parent_folder=tree.root_folder()
    )

    # Used to read the previously written data
    read_data_folder = hosts_and_folders.Folder.load(
        tree=tree, name="testfolder", parent_folder=tree.root_folder()
    )

    # Write data
    write_data_folder.create_hosts(
        [(HostName("testhost"), attributes, [])],
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
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


def test_create_multiple_hosts(tree: FolderTree) -> None:
    root = tree.root_folder()
    subfolder = root.create_subfolder(
        "subfolder",
        "subfolder",
        {},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )

    root.create_hosts(
        [(HostName("host-1"), {}, [])],
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    subfolder.create_hosts(
        [(HostName("host-2"), {}, [])],
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )

    all_hosts = root.all_hosts_recursively()
    # to ensure that new folder instances contain the new hosts
    all_hosts_new = tree.root_folder().all_hosts_recursively()

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


def test_create_nested_folders(tree: FolderTree) -> None:
    with in_chdir("/"):
        root = tree.root_folder()

        folder1 = hosts_and_folders.Folder.new(tree=tree, name="folder1", parent_folder=root)
        folder1.save_folder_attributes()

        folder2 = hosts_and_folders.Folder.new(tree=tree, name="folder2", parent_folder=folder1)
        folder2.save_folder_attributes()

        shutil.rmtree(os.path.dirname(folder1.wato_info_path()))


def test_eq_operation(tree: FolderTree) -> None:
    with in_chdir("/"):
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


def test_mgmt_inherit_credentials_explicit_host_snmp(tree: FolderTree) -> None:
    folder = tree.root_folder()
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
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )

    data = folder._load_hosts_file()
    assert data is not None
    assert data["management_protocol"]["test-host"] == "snmp"
    assert data["management_snmp_credentials"]["test-host"] == "HOST"

    assert _not_in_latest_log("HOST")


def test_mgmt_inherit_credentials_explicit_host_ipmi(tree: FolderTree) -> None:
    folder = tree.root_folder()
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
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )

    data = folder._load_hosts_file()
    assert data is not None
    assert data["management_protocol"]["test-host"] == "ipmi"
    assert data["management_ipmi_credentials"]["test-host"] == {
        "username": "USER",
        "password": "PASS",
    }

    assert _not_in_latest_log("PASS")


def test_mgmt_inherit_credentials_snmp(tree: FolderTree) -> None:
    folder = tree.root_folder()
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
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )

    data = folder._load_hosts_file()
    assert data is not None
    assert data["management_protocol"]["mgmt-host"] == "snmp"
    assert data["management_snmp_credentials"]["mgmt-host"] == "FOLDER"

    assert _not_in_latest_log("FOLDER")


def test_mgmt_inherit_credentials_ipmi(tree: FolderTree) -> None:
    folder = tree.root_folder()
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
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )

    data = folder._load_hosts_file()
    assert data is not None
    assert data["management_protocol"]["mgmt-host"] == "ipmi"
    assert data["management_ipmi_credentials"]["mgmt-host"] == {
        "username": "FOLDERUSER",
        "password": "FOLDERPASS",
    }

    assert _not_in_latest_log("FOLDERPASS")


def test_mgmt_inherit_protocol_explicit_host_snmp(tree: FolderTree) -> None:
    folder = tree.root_folder()
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
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )

    data = folder._load_hosts_file()
    assert data is not None
    assert data["management_protocol"]["mgmt-host"] == "snmp"
    assert data["management_snmp_credentials"]["mgmt-host"] == "HOST"

    assert _not_in_latest_log("HOST")


def test_mgmt_inherit_protocol_explicit_host_ipmi(tree: FolderTree) -> None:
    folder = tree.root_folder()
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
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
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

    def may(self_, _permission, _acting_user):
        return getattr(self_, "_may_see", True)

    mocker.patch.object(hosts_and_folders.PermissionChecker, "may", may)


def only_root(tree: FolderTree) -> hosts_and_folders.Folder:
    root_folder = tree.root_folder()
    root_folder._loaded_subfolders = {}
    return root_folder


def three_levels(tree: FolderTree) -> hosts_and_folders.Folder:
    main = tree.root_folder()

    a = main.create_subfolder(
        "a",
        title="A",
        attributes={},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    a.create_subfolder(
        "c",
        title="C",
        attributes={},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    a.create_subfolder(
        "d",
        title="D",
        attributes={},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )

    b = main.create_subfolder(
        "b",
        title="B",
        attributes={},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    e = b.create_subfolder(
        "e",
        title="E",
        attributes={},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    e.create_subfolder(
        "f",
        title="F",
        attributes={},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )

    return main


def three_levels_leaf_permissions(tree: FolderTree) -> hosts_and_folders.Folder:
    main = tree.root_folder()

    # Attribute only used for testing
    main.permissions._may_see = False  # type: ignore[attr-defined]

    a = main.create_subfolder(
        "a",
        title="A",
        attributes={},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    a.permissions._may_see = False  # type: ignore[attr-defined]
    c = a.create_subfolder(
        "c",
        title="C",
        attributes={},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    c.permissions._may_see = False  # type: ignore[attr-defined]
    a.create_subfolder(
        "d",
        title="D",
        attributes={},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )

    b = main.create_subfolder(
        "b",
        title="B",
        attributes={},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    b.permissions._may_see = False  # type: ignore[attr-defined]
    e = b.create_subfolder(
        "e",
        title="E",
        attributes={},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    e.permissions._may_see = False  # type: ignore[attr-defined]
    e.create_subfolder(
        "f",
        title="F",
        attributes={},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )

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
    actual_builder: Callable[[FolderTree], hosts_and_folders.Folder],
    expected: list[tuple[str, str]],
    tree: FolderTree,
) -> None:
    folder = actual_builder(tree)
    with hide_folders_without_permission(tree, True):
        assert folder.recursive_subfolder_choices(pretty=True, acting_user=_SUPERUSER) == expected


@pytest.mark.usefixtures("patch_may")
def test_recursive_subfolder_choices_function_calls(mocker: MagicMock, tree: FolderTree) -> None:
    """Every folder should only be visited once"""
    spy = mocker.spy(hosts_and_folders.Folder, "_walk_tree")
    main = three_levels_leaf_permissions(tree)
    with hide_folders_without_permission(tree, True):
        main.recursive_subfolder_choices(pretty=True, acting_user=_SUPERUSER)
    assert spy.call_count == 7


def _make_unreadable(tree: FolderTree, *paths: str) -> None:
    """Mark folders unreadable, on the objects the tree itself hands out.

    `three_levels_leaf_permissions` flags the folders it creates, but a lookup through the tree may
    answer with freshly loaded ones, and the functions under test look up by path. So the flags go
    on afterwards, where `patch_may` will read them.
    """
    for path in paths:
        tree.folder(path).permissions._may_see = False  # type: ignore[attr-defined]


# Only "a/d" and "b/e/f" stay readable, the shape `three_levels_leaf_permissions` builds.
_UNREADABLE = ("", "a", "a/c", "b", "b/e")


def test_folder_title_path_gives_the_titles_down_to_the_folder(tree: FolderTree) -> None:
    three_levels(tree)

    assert folder_title_path(tree, "", _SUPERUSER) == "Main"
    assert folder_title_path(tree, "a", _SUPERUSER) == "A"
    assert folder_title_path(tree, "b/e/f", _SUPERUSER) == "B / E / F"


def test_folder_title_path_of_a_folder_this_setup_does_not_know(tree: FolderTree) -> None:
    """A host of a remote site keeping a hierarchy of its own names a folder there is none of."""
    three_levels(tree)

    assert folder_title_path(tree, "nowhere", _SUPERUSER) is None


@pytest.mark.usefixtures("patch_may")
def test_folder_title_paths_are_titled_whoever_may_read_them(tree: FolderTree) -> None:
    """Read permissions are Setup's business until an installation asks for them to be ours."""
    three_levels(tree)
    _make_unreadable(tree, *_UNREADABLE)

    assert folder_title_path(tree, "a/c", _SUPERUSER) == "A / C"
    assert set(all_folder_title_paths(tree, _SUPERUSER)) == {
        "",
        "a",
        "a/c",
        "a/d",
        "b",
        "b/e",
        "b/e/f",
    }


@pytest.mark.usefixtures("patch_may")
def test_a_folder_no_one_may_read_is_not_titled_where_folders_are_hidden(tree: FolderTree) -> None:
    three_levels(tree)
    _make_unreadable(tree, *_UNREADABLE)

    with hide_folders_without_permission(tree, True):
        assert folder_title_path(tree, "a/c", _SUPERUSER) is None
        assert "a/c" not in all_folder_title_paths(tree, _SUPERUSER)


@pytest.mark.usefixtures("patch_may")
def test_a_folder_is_titled_while_a_readable_one_sits_below_it(tree: FolderTree) -> None:
    """The rule `_walk_tree` goes by, which Setup's own folder choices go by as well."""
    three_levels(tree)
    _make_unreadable(tree, *_UNREADABLE)

    with hide_folders_without_permission(tree, True):
        # Neither is readable, and both are titled: "a/d" below the one, "b/e/f" below the other.
        assert folder_title_path(tree, "a", _SUPERUSER) == "A"
        assert folder_title_path(tree, "b/e", _SUPERUSER) == "B / E"


@pytest.mark.usefixtures("patch_may")
def test_the_root_folder_is_titled_whatever_its_permissions_say(tree: FolderTree) -> None:
    three_levels(tree)
    _make_unreadable(tree, *_UNREADABLE)

    with hide_folders_without_permission(tree, True):
        assert folder_title_path(tree, "", _SUPERUSER) == "Main"
        assert all_folder_title_paths(tree, _SUPERUSER)[""] == "Main"


def test_subfolder_creation(tree: FolderTree) -> None:
    folder = tree.root_folder()
    folder.create_subfolder(
        "foo",
        "Foo Folder",
        {},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )

    # Upon instantiation, all the subfolders should be already known.
    folder = tree.root_folder()
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
        ).generate_match_items(UserPermissions({}, {}, {}, []))
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
    subfolders: list[_TreeStructure]
    num_hosts: int = 0


def make_monkeyfree_folder(
    tree: FolderTree, tree_structure: _TreeStructure, parent: hosts_and_folders.Folder | None = None
) -> hosts_and_folders.Folder:
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
            tree, subtree_structure, new_folder
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
    structure: _TreeStructure, testfolder_expected_groups: set[str], tree: FolderTree
) -> None:
    with disable_redis():
        wato_folder = make_monkeyfree_folder(tree, structure)
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
def hide_folders_without_permission(tree: FolderTree, do_hide: bool) -> Iterator[None]:
    old_config = tree.config
    try:
        tree.config = replace(old_config, wato_hide_folders_without_read_permissions=do_hide)
        yield
    finally:
        tree.config = old_config


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


@pytest.mark.usefixtures("with_user_login", "allow_redis")
@pytest.mark.parametrize(
    "structure, user_tests",
    [group_tree_test],
)
def test_num_hosts_normal_user(
    structure: _TreeStructure,
    user_tests: list[_UserTest],
    monkeypatch: MonkeyPatch,
    tree: FolderTree,
) -> None:
    with disable_redis():
        for user_test in user_tests:
            _run_num_host_test(
                tree,
                structure,
                user_test,
                user_test.expected_num_hosts,
                False,
                monkeypatch,
            )


@pytest.mark.usefixtures("with_admin_login", "allow_redis")
@pytest.mark.parametrize(
    "structure, user_tests",
    [group_tree_test],
)
def test_num_hosts_admin_user(
    structure: _TreeStructure,
    user_tests: list[_UserTest],
    monkeypatch: MonkeyPatch,
    tree: FolderTree,
) -> None:
    with disable_redis():
        for user_test in user_tests:
            _run_num_host_test(tree, structure, user_test, 117, True, monkeypatch)


def _run_num_host_test(
    tree: FolderTree,
    structure: _TreeStructure,
    user_test: _UserTest,
    expected_host_count: int,
    is_admin: bool,
    monkeypatch: MonkeyPatch,
) -> None:
    wato_folder = make_monkeyfree_folder(tree, structure)
    with hide_folders_without_permission(tree, user_test.hide_folders_without_permission):
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
                wato_folder.num_hosts_recursively(logged_in_user)
                == expected_host_count + legacy_base_folder_host_offset
            )

        # New mechanism
        monkeypatch.setattr(userdb, "contactgroups_of_user", lambda u: user_test.contactgroups)
        with get_fake_setup_redis_client(
            tree,
            monkeypatch,
            _convert_folder_tree_to_all_folders(wato_folder),
            [_fake_redis_num_hosts_answer(wato_folder)],
        ):
            assert wato_folder.num_hosts_recursively(logged_in_user) == expected_host_count


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
    tree: FolderTree,
    monkeypatch: MonkeyPatch,
    all_folders: dict[hosts_and_folders.PathWithoutSlash, hosts_and_folders.Folder],
    redis_answers: list[list[list[str]]],
) -> Iterator[MockRedisClient]:
    try:
        mock_redis_client = MockRedisClient(redis_answers)
        monkeypatch.setattr(hosts_and_folders._RedisHelper, "_cache_integrity_ok", lambda x: True)
        cache = hosts_and_folders.RedisFolderCache(tree, cast(Redis, mock_redis_client))
        monkeypatch.setattr(tree, "cache", cache)
        redis_helper = cache._redis
        monkeypatch.setattr(redis_helper, "_folder_paths", [f"{x}/" for x in all_folders])
        monkeypatch.setattr(
            redis_helper,
            "_folder_metadata",
            {
                f"{x}/": hosts_and_folders.FolderMetaData(tree, f"{x}/", "nix", "nix", [])
                for x in all_folders
            },
        )
        yield mock_redis_client
    finally:
        monkeypatch.undo()


@pytest.mark.usefixtures("with_admin_login", "allow_redis")
def test_load_redis_folders_on_demand(monkeypatch: MonkeyPatch, tree: FolderTree) -> None:
    wato_folder = make_monkeyfree_folder(tree, group_tree_structure)
    tree.invalidate_caches()
    with get_fake_setup_redis_client(
        tree, monkeypatch, _convert_folder_tree_to_all_folders(wato_folder), []
    ):
        wato_folders = tree.all_folders()
        # Check if wato_folders class matches
        assert isinstance(wato_folders, hosts_and_folders.WATOFoldersOnDemand)
        # Check if item is None
        assert wato_folders._raw_dict["sub1.1"] is None
        # Check if item is generated on access
        assert isinstance(wato_folders["sub1.1"], hosts_and_folders.Folder)
        # Check if item is now set in dict
        assert isinstance(wato_folders._raw_dict["sub1.1"], hosts_and_folders.Folder)

        # Check if other folder is still None
        assert wato_folders._raw_dict["sub1.2"] is None  # type: ignore[unreachable]
        # Check if parent(main) folder got instantiated as well
        assert isinstance(wato_folders._raw_dict[""], hosts_and_folders.Folder)


class UnusableRedisClient:
    """Redis client that fails on any interaction"""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def __getattr__(self, _name: str) -> object:
        raise self._error


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(
            # The socket is gone, e.g. during an `omd reload`
            RedisConnectionError(
                "Error 2 connecting to /omd/sites/heute/tmp/run/redis. No such file or directory."
            ),
            id="connection_error",
        ),
        pytest.param(
            # Redis is up, but another client keeps it busy past the socket timeout
            RedisTimeoutError("Timeout reading from socket"),
            id="timeout_error",
        ),
    ],
)
@pytest.mark.usefixtures("with_admin_login", "allow_redis")
def test_redis_folder_cache_degrades_when_redis_is_unusable(
    monkeypatch: MonkeyPatch, tree: FolderTree, error: Exception
) -> None:
    subfolder = tree.root_folder().create_subfolder(
        "sub",
        "sub",
        {},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    tree.invalidate_caches()
    cache = hosts_and_folders.RedisFolderCache(tree, cast(Redis, UnusableRedisClient(error)))
    monkeypatch.setattr(tree, "cache", cache)

    # Queries miss instead of raising, so the callers fall back to disk
    assert cache.all_folders() is None
    assert cache.folder_metadata("sub") is None
    assert cache.num_hosts_recursively("sub/", _SUPERUSER) is None
    assert cache.choices_for_moving("sub", hosts_and_folders._MoveType.Folder, _SUPERUSER) is None
    assert cache.recursive_subfolders_for_path("sub/") is None

    # Updates are dropped. They only advance the last_update timestamp, so the
    # next integrity check rebuilds the cache from scratch anyway.
    cache.folder_updated(subfolder.filesystem_path())
    cache.save_folder_info(subfolder)

    # The failed helper is not kept around, the next query reconnects
    assert cache._helper is None

    assert set(tree.all_folders()) == {"", "sub"}


def test_folder_exists(tree: FolderTree) -> None:
    tree.root_folder().create_subfolder(
        "foo",
        "foo",
        {},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    ).create_subfolder(
        "bar",
        "bar",
        {},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    assert tree.folder_exists("foo")
    assert tree.folder_exists("foo/bar")
    assert not tree.folder_exists("bar")
    assert not tree.folder_exists("foo/foobar")
    with pytest.raises(MKUserError):
        tree.folder_exists("../wato")


def test_folder_access(tree: FolderTree) -> None:
    tree.root_folder().create_subfolder(
        "foo",
        "foo",
        {},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    ).create_subfolder(
        "bar",
        "bar",
        {},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    assert isinstance(tree.folder("foo/bar"), hosts_and_folders.Folder)
    assert isinstance(tree.folder(""), hosts_and_folders.Folder)
    with pytest.raises(MKGeneralException):
        tree.folder("unknown_folder")


def test_new_empty_folder(monkeypatch: pytest.MonkeyPatch, tree: FolderTree) -> None:
    monkeypatch.setattr(uuid, "uuid4", lambda: uuid.UUID("a8098c1a-f86e-11da-bd1a-00112444be1e"))
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


def test_new_loaded_folder(monkeypatch: pytest.MonkeyPatch, tree: FolderTree) -> None:
    monkeypatch.setattr(uuid, "uuid4", lambda: uuid.UUID("c6bda767ae5c47038f73d8906fb91bb4"))

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
    tree: FolderTree,
) -> None:
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


def test_folder_times(tree: FolderTree) -> None:
    root = tree.root_folder()

    with time_machine.travel(datetime.datetime(2020, 2, 2, 2, 2, 2)):
        current = time.time()
        Folder.new(tree=tree, name="test", parent_folder=root).save_folder_attributes()
        tree.invalidate_caches()
        folder = Folder.load(tree=tree, name="test", parent_folder=root)
        folder.save_folder_attributes()
        tree.invalidate_caches()

    meta_data = folder.attributes["meta_data"]
    assert int(meta_data["created_at"]) == int(current)
    assert int(meta_data["updated_at"]) == int(current)

    folder.save_folder_attributes()
    assert int(meta_data["updated_at"]) > int(current)


def test_subfolder_attributes_are_cached(tree: FolderTree) -> None:
    # GIVEN folder with cached attributes
    root = tree.root_folder()
    subfolder = root.create_subfolder(
        "sub1",
        "sub1",
        {"alias": "sub1"},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    subfolder.effective_attributes()

    # WHEN
    subfolder.attributes["alias"] = "other_alias"

    # THEN return cached attribute
    assert subfolder.effective_attributes()["alias"] == "sub1"


def test_subfolder_cache_invalidated(tree: FolderTree) -> None:
    # GIVEN folder with cached attributes
    subfolder = tree.root_folder().create_subfolder(
        "sub1",
        "sub1",
        {"alias": "sub1"},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    subfolder.effective_attributes()

    # WHEN cache is invalidated from folder_tree and attribute is updated
    tree.invalidate_caches()
    subfolder.attributes["alias"] = "other_alias"

    # THEN we read updated attribute
    # There is a bug when invalidating cache from folder_tree(), not all
    # subfolders are part of the tree
    with pytest.raises(AssertionError):
        assert subfolder.effective_attributes()["alias"] == "other_alias"


def test_host_action_menu_registry_keys_by_ident() -> None:
    registry = hosts_and_folders.HostActionMenuRegistry()

    entry = hosts_and_folders.HostActionMenuEntry(
        ident="show_demo_link",
        is_shown=lambda _host, _folder: True,
        render=lambda _host_name, _form_name: None,
    )
    registry.register(entry)

    assert registry["show_demo_link"] is entry
    assert list(registry.values()) == [entry]


def test_folder_attributes_for_base_config_without_bake_attribute(tree: FolderTree) -> None:
    folder = hosts_and_folders.Folder.new(
        tree=tree,
        name="no_baking",
        parent_folder=tree.root_folder(),
        attributes=HostAttributes({"cmk_agent_connection": "push-agent"}),
    )

    assert folder._folder_attributes_for_base_config() == {}


def test_folder_attributes_for_base_config_defaults_to_pull_mode(tree: FolderTree) -> None:
    folder = hosts_and_folders.Folder.new(
        tree=tree,
        name="baking",
        parent_folder=tree.root_folder(),
        attributes=HostAttributes({"bake_agent_package": True}),
    )

    attributes = folder._folder_attributes_for_base_config()[folder.path_for_rule_matching()]
    assert attributes["bake_agent_package"] is True
    # the attribute's default value may or may not be filled in, depending on
    # whether the edition under test registers the attribute
    assert attributes.get("cmk_agent_connection", "pull-agent") == "pull-agent"


def test_folder_attributes_for_base_config_exports_inherited_agent_connection(
    tree: FolderTree,
) -> None:
    parent = hosts_and_folders.Folder.new(
        tree=tree,
        name="push_folder",
        parent_folder=tree.root_folder(),
        attributes=HostAttributes({"cmk_agent_connection": "push-agent"}),
    )
    folder = hosts_and_folders.Folder.new(
        tree=tree,
        name="baking",
        parent_folder=parent,
        attributes=HostAttributes({"bake_agent_package": True}),
    )

    assert folder._folder_attributes_for_base_config() == {
        folder.path_for_rule_matching(): {
            "bake_agent_package": True,
            "cmk_agent_connection": "push-agent",
        },
    }
