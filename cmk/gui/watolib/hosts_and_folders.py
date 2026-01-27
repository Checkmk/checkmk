#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"
# mypy: disable-error-code="unreachable"

from __future__ import annotations

import json
import operator
import os
import pickle
import pprint
import shutil
import subprocess
import time
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable, Collection, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Final, Literal, NamedTuple, NotRequired, Protocol, Self, TypedDict

from redis.client import Pipeline

from livestatus import SiteConfiguration

import cmk.utils.paths
from cmk.automations.results import ABCAutomationResult
from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.plugin_registry import Registry
from cmk.ccc.regex import regex, WATO_FOLDER_PATH_NAME_CHARS, WATO_FOLDER_PATH_NAME_REGEX
from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.user import UserId
from cmk.ccc.version import edition
from cmk.gui import hooks, userdb
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.config import active_config, Config
from cmk.gui.ctx_stack import g
from cmk.gui.exceptions import MKAuthException, MKUserError, RequestTimeout
from cmk.gui.groups import GroupName
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.log import logger
from cmk.gui.logged_in import LoggedInUser, user
from cmk.gui.page_menu import confirmed_form_submit_options
from cmk.gui.pages import PageContext
from cmk.gui.session import session
from cmk.gui.site_config import is_distributed_setup_remote_site
from cmk.gui.type_defs import (
    Choices,
    CustomHostAttrSpec,
    GlobalSettings,
    HTTPVariables,
    IconNames,
    SetOnceDict,
    StaticIcon,
)
from cmk.gui.utils import urls
from cmk.gui.utils.agent_registration import remove_tls_registration_help
from cmk.gui.utils.html import HTML
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.watolib.automations import (
    make_automation_config,
)
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.config_domain_name import (
    config_domain_registry,
    DomainSettings,
    generate_hosts_to_update_settings,
)
from cmk.gui.watolib.config_domain_name import CORE as CORE_DOMAIN
from cmk.gui.watolib.configuration_bundle_store import is_locked_by_quick_setup
from cmk.gui.watolib.host_attributes import (
    ABCHostAttribute,
    all_host_attributes,
    collect_attributes,
    get_host_attribute_default_value,
    host_attribute_matches,
    HostAttributes,
    HostContactGroupSpec,
    mask_attributes,
    MetaData,
)
from cmk.gui.watolib.objref import ObjectRef, ObjectRefType
from cmk.gui.watolib.predefined_conditions import PredefinedConditionStore
from cmk.gui.watolib.sidebar_reload import need_sidebar_reload
from cmk.gui.watolib.utils import wato_root_dir
from cmk.utils.automation_config import LocalAutomationConfig, RemoteAutomationConfig
from cmk.utils.global_ident_type import GlobalIdent
from cmk.utils.host_storage import (
    ABCHostsStorage,
    apply_hosts_file_to_object,
    FolderAttributesForBase,
    get_all_storage_readers,
    get_host_storage_loaders,
    get_hosts_file_variables,
    get_storage_format,
    GroupRuleType,
    HostsData,
    HostsStorageData,
    HostsStorageFieldsGenerator,
    make_experimental_hosts_storage,
    StandardHostsStorage,
    StorageFormat,
)
from cmk.utils.labels import Labels
from cmk.utils.object_diff import make_diff, make_diff_text
from cmk.utils.redis import get_redis_client, redis_enabled, redis_server_reachable
from cmk.utils.tags import TagConfig, TagGroupID, TagID

_ContactgroupName = str

SearchCriteria = Mapping[str, Any]


@dataclass(frozen=True)
class HostsAndFoldersConfig:
    """Configuration needed by the hosts_and_folders module."""

    config_storage_format: Literal["standard", "pickle", "raw", "anon"]
    wato_hide_folders_without_read_permissions: bool
    wato_host_attrs: Sequence[CustomHostAttrSpec]
    tags: TagConfig
    sites: dict[SiteId, SiteConfiguration]

    @classmethod
    def from_config(cls, config: Config) -> HostsAndFoldersConfig:
        return cls(
            config_storage_format=config.config_storage_format,
            wato_hide_folders_without_read_permissions=config.wato_hide_folders_without_read_permissions,
            wato_host_attrs=config.wato_host_attrs,
            tags=config.tags,
            sites=config.sites,
        )


class CollectedHostAttributes(HostAttributes):
    path: str
    # Seems to be added during runtime in some cases. Clean this up
    edit_url: NotRequired[str]


class WATOFolderInfo(TypedDict, total=False):
    """The dictionary that is saved in the folder's .wato file"""

    __id: str
    title: str
    attributes: HostAttributes
    num_hosts: int
    lock: bool
    lock_subfolders: bool


class FolderMetaData:
    """Stores meta information for one Folder.
    Usually this class is instantiated with data from Redis"""

    def __init__(
        self,
        tree: FolderTree,
        path: PathWithSlash,
        title: str,
        title_path_without_root: str,
        permitted_contact_groups: list[_ContactgroupName],
    ):
        self.tree: Final = tree
        self._path: Final = path
        self._title: Final = title
        self._title_path_without_root: Final[str] = title_path_without_root
        self._permitted_groups: Final[list[_ContactgroupName]] = permitted_contact_groups
        self._num_hosts_recursively: int | None = None

    @property
    def path(self) -> PathWithSlash:
        return self._path

    @property
    def title(self) -> str:
        return self._title

    @property
    def title_path_without_root(self) -> str:
        return self._title_path_without_root

    @property
    def path_titles(self) -> list[str]:
        return self._path.split("/")

    @property
    def permitted_groups(self) -> list[_ContactgroupName]:
        return self._permitted_groups

    @property
    def num_hosts_recursively(self) -> int:
        if self._num_hosts_recursively is None:
            if may_use_redis():
                self._num_hosts_recursively = self.tree.redis_client.num_hosts_recursively_lua(
                    self._path,
                    skip_permission_checks=(
                        user.may("wato.see_all_folders")
                        or not active_config.wato_hide_folders_without_read_permissions
                    ),
                    user_contact_groups=(
                        set(userdb.contactgroups_of_user(user.id)) if user.id is not None else set()
                    ),
                )
            else:
                self._num_hosts_recursively = self.tree.folder(
                    self._path.rstrip("/")
                ).num_hosts_recursively()
        return self._num_hosts_recursively


# Terms:
# create, delete   mean actual filesystem operations
# add, remove      mean just modifications in the data structures


class PermissionChecker:
    def __init__(self, check_permission: Callable[[Literal["read", "write"]], None]) -> None:
        self._check_permission = check_permission

    def may(self, how: Literal["read", "write"]) -> bool:
        try:
            self._check_permission(how)
            return True
        except MKAuthException:
            return False

    def reason_why_may_not(self, how: Literal["read", "write"]) -> str | None:
        try:
            self._check_permission(how)
            return None
        except MKAuthException as e:
            return str(e)

    def need_permission(self, how: Literal["read", "write"]) -> None:
        self._check_permission(how)


class _ContactGroupsInfo(NamedTuple):
    actual_groups: set[_ContactgroupName]
    configured_groups: list[_ContactgroupName] | None
    apply_to_subfolders: bool


PathWithSlash = str
PathWithoutSlash = str
PermittedGroupsOfFolder = Mapping[PathWithoutSlash, _ContactGroupsInfo]


def _get_permitted_groups_of_all_folders(
    all_folders: Mapping[PathWithoutSlash, Folder],
) -> PermittedGroupsOfFolder:
    def _compute_tokens(folder_path: PathWithoutSlash) -> tuple[PathWithoutSlash, ...]:
        """Create tokens for each folder. The main folder requires some special treatment
        since it is not '/' but just an empty string"""
        if _is_main_folder_path(folder_path):
            return (folder_path,)
        # Some subfolder, prefix root dir
        return tuple([""] + folder_path.split("/"))

    tokenized_folders = sorted(_compute_tokens(x) for x in all_folders.keys())
    effective_groups_per_folder: dict[tuple[str, ...], _ContactGroupsInfo] = {}

    for tokens in tokenized_folders:
        # Compute the groups we get from the parent folders
        # Either directly inherited (nearest parent wins) or enforce inherited through recurse_perms
        parents_all_subfolder_groups: set[_ContactgroupName] = set()
        parents_nearest_configured: list[_ContactgroupName] | None = None
        parent_tokens = tokens[:-1]
        while parent_tokens:
            contact_groups_info = effective_groups_per_folder[parent_tokens]
            if (
                parents_nearest_configured is None
                and contact_groups_info.configured_groups is not None
            ):
                parents_nearest_configured = contact_groups_info.configured_groups
            if contact_groups_info.apply_to_subfolders and contact_groups_info.configured_groups:
                parents_all_subfolder_groups.update(contact_groups_info.configured_groups)

            parent_tokens = parent_tokens[:-1]

        if contactgroups := all_folders["/".join(tokens[1:])].attributes.get("contactgroups"):
            assert isinstance(contactgroups, dict)
            configured_contactgroups = contactgroups.get("groups")
            inherit_groups = contactgroups["recurse_perms"]
        else:
            configured_contactgroups = None
            inherit_groups = False

        actual_groups = set()
        if configured_contactgroups is not None:
            actual_groups.update(configured_contactgroups)
        elif parents_nearest_configured is not None:
            actual_groups.update(parents_nearest_configured)
        actual_groups.update(parents_all_subfolder_groups)

        effective_groups_per_folder[tokens] = _ContactGroupsInfo(
            actual_groups, configured_contactgroups, inherit_groups
        )

    return {
        "/".join(path_tokens[1:]): groups_info
        for path_tokens, groups_info in effective_groups_per_folder.items()
    }


class _WATOFolderScanTimestamps(list):
    pass


class _MoveType(Enum):
    Host = "host"
    Folder = "folder"


class _RedisHelper:
    """
    This class
    - communicates with redis
    - handles the entire redis cache and checks its integrity
    - computes the metadata out of Folder instances and stores it in redis
    - provides functions to compute the number of hosts and fetch the metadata for folders
    """

    def __init__(self, tree: FolderTree) -> None:
        self.tree = tree
        self._client = get_redis_client()
        self._folder_metadata: dict[str, FolderMetaData] = {}

        self._loaded_wato_folders: Mapping[PathWithoutSlash, Folder] | None = None
        self._folder_paths: tuple[PathWithSlash, ...] | None = None

        if self._cache_integrity_ok():
            return

        # Store the fully loaded Setup folders. Maybe some process needs them later on
        latest_timestamp, wato_folders = self._get_latest_timestamp_and_folders()
        self._loaded_wato_folders = wato_folders
        self._folder_paths = tuple(f"{path}/" for path in self._loaded_wato_folders)
        self._create_cache_from_scratch(latest_timestamp, self._loaded_wato_folders)

    def _get_latest_timestamp_and_folders(self) -> tuple[str, Mapping[str, Folder]]:
        # Timestamp has to be determined first, otherwise unobserved changes can slip through
        latest_timestamp = self._get_latest_timestamps_from_disk()[-1]
        wato_folders = _get_fully_loaded_wato_folders(self.tree)
        return latest_timestamp, wato_folders

    @property
    def folder_paths(self) -> Sequence[PathWithSlash]:
        if self._folder_paths is None:
            lst = self._client.smembers("wato:folder_list")
            assert not isinstance(lst, Awaitable)
            self._folder_paths = tuple(lst)
        return self._folder_paths

    def recursive_subfolders_for_path(self, path: PathWithSlash) -> list[PathWithSlash]:
        return [x for x in self.folder_paths if x.startswith(path)]

    @property
    def loaded_wato_folders(self) -> Mapping[str, Folder] | None:
        return self._loaded_wato_folders

    def clear_cached_folders(self) -> None:
        self._loaded_wato_folders = None
        self._folder_paths = None

    def choices_for_moving(
        self,
        path: PathWithoutSlash,
        move_type: _MoveType,
        *,
        may_see_all_folders: bool,
        user_contact_groups: set[str],
    ) -> Choices:
        self._fetch_all_metadata()
        path_to_title = {x.path: x.title_path_without_root for x in self._folder_metadata.values()}

        # Remove self
        del path_to_title[f"{path}/"]

        # Folder sanity checks. A folder cannot be moved into its subfolders
        if move_type == _MoveType.Folder:
            if not _is_main_folder_path(path):
                # Remove move into parent (folder is already there)
                del path_to_title[f"{os.path.dirname(path)}/"]

            # Remove all subfolders (recursively)
            for possible_child_path in list(path_to_title.keys()):
                if possible_child_path.startswith(path):
                    del path_to_title[possible_child_path]

        # Check permissions
        if not may_see_all_folders:
            # Remove folders without permission
            for check_path in list(path_to_title.keys()):
                if permitted_groups := self._folder_metadata[check_path].permitted_groups:
                    if not user_contact_groups.intersection(set(permitted_groups)):
                        del path_to_title[check_path]

        return [(key.rstrip("/"), value) for key, value in path_to_title.items()]

    def folder_metadata(self, path: PathWithoutSlash) -> FolderMetaData | None:
        path_with_slash = f"{path}/"
        if path_with_slash not in self._folder_metadata:
            results = self._client.hmget(
                f"wato:folders:{path_with_slash}",
                [
                    "title",
                    "title_path_without_root",
                    "permitted_contact_groups",
                ],
            )
            if not results:
                return None
            assert not isinstance(results, Awaitable)

            # Redis hmget typing states that the field can be None
            # It won't happen if the key is found, adding fallbacks anyway.
            permitted_groups = results[2].split(",") if results[2] is not None else []
            self._folder_metadata[path_with_slash] = FolderMetaData(
                self.tree,
                path_with_slash,
                results[0] or path_with_slash,
                results[1] or path_with_slash,
                permitted_groups,
            )

        return self._folder_metadata.get(path_with_slash)

    def _fetch_all_metadata(self) -> None:
        pipeline = self._client.pipeline()
        all_metadata = self._client.register_script(
            """
            local cursor = 0;
            local values = {}
            repeat
                local result = redis.call("SSCAN", "wato:folder_list", cursor, "COUNT", 100000)
                cursor = tonumber(result[1])
                local data = result[2]
                for i=1, #data do
                    table.insert(values, data[i])
                    for i, v in ipairs(redis.call("HMGET", "wato:folders:" .. data[i], "title", "title_path_without_root", "permitted_contact_groups")) do
                        table.insert(values, v)
                    end
                end
            until cursor == 0;
            return values;
        """
        )
        all_metadata(client=pipeline)

        def pairwise(iterable: Iterable[str]) -> Iterator[tuple[str, str, str, str]]:
            """s -> (s0,s1,s2,s3), (s4,s5,s6,s7), ..."""
            a = iter(iterable)
            return zip(a, a, a, a)

        results = pipeline.execute()
        for (
            folder_path,
            title,
            title_path_without_root,
            permitted_contact_groups,
        ) in pairwise(results[0]):
            self._folder_metadata[folder_path] = FolderMetaData(
                self.tree,
                folder_path,
                title,
                title_path_without_root,
                permitted_contact_groups.split(","),
            )

    def _create_cache_from_scratch(
        self,
        update_timestamp: str,
        all_folders: Mapping[PathWithSlash, Folder],
    ) -> None:
        # Steps:
        #  1) create a log entry, this shouldn't happen to often, helps to track down other effects
        #  2) determine the latest timestamp from disk
        #  3) load folder hierarchy
        #  3) prepare pipeline
        #  4) cleanup redis -> pipeline
        #  5) compute new config -> pipeline
        #  7) execute pipeline
        # Note: Locking? Pipeline is an atomic operation

        logger.info("Creating wato folder cache")
        pipeline = self._client.pipeline()
        self._add_redis_cleanup_to_pipeline(pipeline)
        self._add_all_folder_details_to_pipeline(pipeline, all_folders)
        self._add_last_folder_update_to_pipeline(pipeline, update_timestamp)
        pipeline.execute()

    def _add_redis_cleanup_to_pipeline(self, pipeline: Pipeline) -> None:
        delete_keys = self._client.register_script(
            """
            local cursor = 0;
            redis.call("DEL", "wato:folder_list");
            redis.call("DEL", "wato:folder_list:last_update");
            repeat
                local result = redis.call("SCAN", cursor, "MATCH", "wato:folders:*", "COUNT", 100000);
                cursor = tonumber(result[1]);
                local data = result[2];
                for i=1, #data do
                    redis.call("DEL", data[i]);
                end
            until cursor == 0;
        """
        )
        delete_keys(client=pipeline)

    def _add_all_folder_details_to_pipeline(
        self, pipeline: Pipeline, all_folders: Mapping[PathWithoutSlash, Folder]
    ) -> None:
        folder_groups = _get_permitted_groups_of_all_folders(all_folders)
        folder_list_entries = []
        for folder_path, folder in all_folders.items():
            folder_list_entries.append(f"{folder_path}/")
            self._add_folder_details_to_pipeline(
                pipeline,
                folder_path,
                folder.num_hosts(),
                folder.title(),
                "/".join(str(p) for p in folder.title_path_without_root()),
                folder_groups[folder_path].actual_groups,
            )
        pipeline.sadd("wato:folder_list", *folder_list_entries)

    def _add_folder_details_to_pipeline(
        self,
        pipeline: Pipeline,
        path: PathWithoutSlash,
        num_hosts: int,
        title: str,
        title_path_without_root: str,
        permitted_contact_groups: set[_ContactgroupName],
    ) -> None:
        folder_key = f"wato:folders:{path}/"
        mapping = {
            "num_hosts": num_hosts,
            "title": title,
            "title_path_without_root": title_path_without_root,
            "permitted_contact_groups": ",".join(permitted_contact_groups),
        }
        pipeline.hset(folder_key, mapping=mapping)

    def _add_last_folder_update_to_pipeline(self, pipeline: Pipeline, timestamp: str) -> None:
        pipeline.set("wato:folder_list:last_update", timestamp)

    def num_hosts_recursively_lua(
        self,
        path_with_slash: PathWithSlash,
        *,
        skip_permission_checks: bool,
        user_contact_groups: set[str],
    ) -> int:
        """Returns the number of hosts in subfolder, excluding hosts not visible to the current user"""
        recursive_hosts = self._client.register_script(
            """
            local cursor = 0;
            local values = {}
            repeat
                local result = redis.call("SSCAN", "wato:folder_list", cursor, "MATCH", KEYS[1], "COUNT", 100000)
                cursor = tonumber(result[1])
                local data = result[2]
                for i=1, #data do
                    for i, v in ipairs(redis.call("HMGET", "wato:folders:" .. data[i], ARGV[1], ARGV[2])) do
                        table.insert(values, v)
                    end
                end
            until cursor == 0;
            return values;
        """
        )

        pipeline = self._client.pipeline()
        # For the root folder path_with_slash == "/", yet for first level subfolders path_with_slash
        # does not start with a slash, e.g. "subfolder/", "subfolder/subsubfolder/".
        # To gather all subfolders in case of the root folder we need to set ["*"] as keys here.
        keys = [f"{path_with_slash}*"] if not path_with_slash == "/" else ["*"]
        args = ["permitted_contact_groups", "num_hosts"]
        recursive_hosts(keys=keys, args=args, client=pipeline)
        results = pipeline.execute()

        total_hosts = 0
        if not results:
            return total_hosts

        if skip_permission_checks:
            return sum(map(int, results[0][1::2]))

        def pairwise(iterable: Iterable[str]) -> Iterator[tuple[str, str]]:
            """s -> (s0,s1), (s2,s3), (s4, s5), ..."""
            a = iter(iterable)
            return zip(a, a)

        for folder_cgs, num_hosts in pairwise(results[0]):
            cgs = set(folder_cgs.split(","))
            if user_contact_groups.intersection(cgs):
                total_hosts += int(num_hosts)

        return total_hosts

    def _cache_integrity_ok(self) -> bool:
        return self._get_latest_timestamps_from_disk()[-1] == self._get_last_update_from_redis()

    def _partial_data_update_possible(self, allowed_timestamps: list[str]) -> bool:
        """Checks whether a partial update is possible at all
        It is important that the in memory cache does not deviate from the data on disk.
        The fasted way to accomplish this (with a sufficient reliability) is to compare
        the latest changed timestamps from disk with
         - the latest known timestamp of the cache itself
         - the allowed timestamps, which reflect the file timestamps of the latest changed
           host/folder/rule files

        For example. Every time a .wato file is updated, the timestamp of the .wato file and its
        folder updates. To check whether a partial update is possible
        - Determine allowed_timestamps (.wato + folder)
        - Get last_update from redis
        - Get the latest few timestamps from disk and removed the allowed_timestamps from them
        - The remaining newest timestamp must be equal or older than the last update from redis
              If this condition is true, a partial update is possible since there were no
              unobserved changes, again -> with a sufficient reliability.
        """

        remaining_timestamps = [
            x for x in self._get_latest_timestamps_from_disk() if x not in allowed_timestamps
        ]

        if remaining_timestamps and remaining_timestamps[-1] > self._get_last_update_from_redis():
            return False

        return True

    def _get_allowed_folder_timestamps(self, folder: Folder) -> list[str]:
        wato_info_path = folder.wato_info_path()
        return sorted(
            [
                self._timestamp_to_fixed_precision_str(os.stat(wato_info_path).st_mtime),
                self._timestamp_to_fixed_precision_str(
                    os.stat(os.path.dirname(wato_info_path)).st_mtime
                ),
            ]
        )

    def folder_updated(self, filesystem_path: str) -> None:
        try:
            folder_timestamp = self._timestamp_to_fixed_precision_str(
                os.stat(filesystem_path).st_mtime
            )
        except FileNotFoundError:
            return

        pipeline = self._client.pipeline()
        self._add_last_folder_update_to_pipeline(pipeline, folder_timestamp)
        pipeline.execute()

    def save_folder_info(
        self,
        folder: Folder,
    ) -> None:
        allowed_timestamps = self._get_allowed_folder_timestamps(folder)
        if not self._partial_data_update_possible(allowed_timestamps):
            # Something unexpected was modified in the meantime, rewrite cache
            self._create_cache_from_scratch(*self._get_latest_timestamp_and_folders())

        pipeline = self._client.pipeline()
        self._add_folder_details_to_pipeline(
            pipeline,
            folder.path(),
            folder.num_hosts(),
            folder.title(),
            "/".join(str(p) for p in folder.title_path_without_root()),
            folder.groups()[0],
        )
        pipeline.sadd("wato:folder_list", f"{folder.path()}/")
        self._add_last_folder_update_to_pipeline(pipeline, allowed_timestamps[-1])
        pipeline.execute()

    def _timestamp_to_fixed_precision_str(self, timestamp: float) -> str:
        return "%.5f" % timestamp

    def _get_latest_timestamps_from_disk(self) -> _WATOFolderScanTimestamps:
        """Note: We are using the find command from the command line since it is considerable
        faster than any python implementation. For example 9k files:
        Path.glob             -> 1.12 seconds
        os.walk               -> 0.34 seconds
        find (+spawn process) -> 0.14 seconds
        """
        result = subprocess.run(  # nosec B602 # BNS:248184
            f"find {cmk.utils.paths.check_mk_config_dir / 'wato'} -type d -printf '%T@\n' -o -name .wato -printf '%T@\n' | sort -n | tail -6 | uniq",
            shell=True,
            capture_output=True,
            check=True,
            encoding="utf-8",
        )
        try:
            return _WATOFolderScanTimestamps(
                self._timestamp_to_fixed_precision_str(float(x))
                for x in result.stdout.split("\n")
                if x
            )
        except ValueError:
            fixed_zero = self._timestamp_to_fixed_precision_str(0.0)
            return _WATOFolderScanTimestamps([fixed_zero] * 3)

    def _get_last_update_from_redis(self) -> str:
        try:
            if (value := self._client.get("wato:folder_list:last_update")) is not None:
                assert not isinstance(value, Awaitable)
                return value
        except ValueError:
            pass
        return self._timestamp_to_fixed_precision_str(0.0)


def _get_fully_loaded_wato_folders(
    tree: FolderTree,
) -> Mapping[PathWithoutSlash, Folder]:
    wato_folders: dict[PathWithoutSlash, Folder] = {}
    Folder.load(tree=tree, name="", parent_folder=None).add_to_dictionary(wato_folders)
    return wato_folders


class _ABCWATOInfoStorage:
    def read(self, file_path: Path) -> WATOFolderInfo | None:
        raise NotImplementedError()

    def write(self, file_path: Path, data: WATOFolderInfo) -> None:
        raise NotImplementedError()


class _StandardWATOInfoStorage(_ABCWATOInfoStorage):
    def read(self, file_path: Path) -> WATOFolderInfo:
        return store.load_object_from_file(file_path, default={})

    def write(self, file_path: Path, data: WATOFolderInfo) -> None:
        store.save_object_to_file(file_path, data)


class _PickleWATOInfoStorage(_ABCWATOInfoStorage):
    def read(self, file_path: Path) -> WATOFolderInfo | None:
        pickle_path = self._add_suffix(file_path)
        if not pickle_path.exists() or not self._file_valid(pickle_path, file_path):
            return None
        return store.ObjectStore(
            pickle_path, serializer=store.PickleSerializer[WATOFolderInfo]()
        ).read_obj(default={})

    def _file_valid(self, pickle_path: Path, file_path: Path) -> bool:
        # The experimental file must not be older than the corresponding .wato
        # The file is also invalid if no matching .wato file exists
        if not file_path.exists():
            return False

        return file_path.stat().st_mtime <= pickle_path.stat().st_mtime

    def write(self, file_path: Path, data: WATOFolderInfo) -> None:
        pickle_store = store.ObjectStore(
            self._add_suffix(file_path),
            serializer=store.PickleSerializer[WATOFolderInfo](),
        )
        with pickle_store.locked():
            pickle_store.write_obj(data)

    def _add_suffix(self, path: Path) -> Path:
        return path.with_suffix(StorageFormat.PICKLE.extension())


class _WATOInfoStorageManager:
    """Handles read/write operations for the .wato file"""

    def __init__(self, storage_format: Literal["standard", "pickle", "raw", "anon"]) -> None:
        self._write_storages = self._get_write_storages(storage_format)
        self._read_storages = list(reversed(self._write_storages))

    def _get_write_storages(
        self, storage_format: Literal["standard", "pickle", "raw", "anon"]
    ) -> list[_ABCWATOInfoStorage]:
        storages: list[_ABCWATOInfoStorage] = [_StandardWATOInfoStorage()]
        if get_storage_format(storage_format) == StorageFormat.PICKLE:
            storages.append(_PickleWATOInfoStorage())
        return storages

    def read(self, store_file: Path) -> WATOFolderInfo:
        for storage in self._read_storages:
            if (storage_data := storage.read(store_file)) is not None:
                return storage_data
        return {}

    def write(self, store_file: Path, data: WATOFolderInfo) -> None:
        for storage in self._write_storages:
            storage.write(store_file, data)


class EffectiveAttributes:
    """A memoized access to the effective attributes of hosts and folders"""

    def __init__(self, compute_attributes: Callable[[], HostAttributes]) -> None:
        self._compute_attributes = compute_attributes
        self._effective_attributes: HostAttributes | None = None

    # Built this way to stay compatible with the former API.
    # Might be cleaned up in a follow up action.
    def __call__(self) -> HostAttributes:
        if self._effective_attributes is None:
            self._effective_attributes = self._compute_attributes()
        # Would be nice if we could avoid the copies here. But we would need stricter typing to be
        # sure the cached data is not modified by the call sites.
        return self._effective_attributes.copy()

    def drop_caches(self) -> None:
        self._effective_attributes = None


class FolderProtocol(Protocol):
    def is_disk_folder(self) -> bool: ...

    def is_search_folder(self) -> bool: ...

    def breadcrumb(self) -> Breadcrumb: ...

    def has_host(self, host_name: HostName) -> bool: ...

    def has_hosts(self) -> bool: ...

    def load_host(self, host_name: HostName) -> Host: ...

    def host_validation_errors(self) -> dict[HostName, list[str]]: ...


def rename_host_in_list(thelist: list[str], oldname: str, newname: str) -> bool:
    """Replace occurrences of *oldname* with *newname* (also for negated entries).

    Returns True if at least one replacement was made."""
    did_rename = False
    for nr, element in enumerate(thelist):
        if element == oldname:
            thelist[nr] = newname
            did_rename = True
        elif element == f"!{oldname}":
            thelist[nr] = f"!{newname}"
            did_rename = True
    return did_rename


def find_available_folder_name(candidate: str, parent: Folder) -> str:
    basename = _normalize_folder_name(candidate)
    c = 1
    name = basename
    while True:
        if parent.subfolder(name) is None:
            break
        c += 1
        name = "%s-%d" % (basename, c)
    return name


def _normalize_folder_name(name: str) -> str:
    """Transform the `name` to a filesystem friendly one.

    >>> _normalize_folder_name("abc")
    'abc'
    >>> _normalize_folder_name("Äbc")
    'aebc'
    >>> _normalize_folder_name("../Äbc")
    '___aebc'
    """
    converted = ""
    for c in name.lower():
        if c == "ä":
            converted += "ae"
        elif c == "ö":
            converted += "oe"
        elif c == "ü":
            converted += "ue"
        elif c == "ß":
            converted += "ss"
        elif c in "abcdefghijklmnopqrstuvwxyz0123456789-_":
            converted += c
        else:
            converted += "_"
    return converted


def _folder_breadcrumb(folder: Folder | SearchFolder) -> Breadcrumb:
    breadcrumb = Breadcrumb()

    for this_folder in parent_folder_chain(folder) + [folder]:
        breadcrumb.append(
            BreadcrumbItem(
                title=this_folder.title(),
                url=this_folder.url(),
            )
        )

    return breadcrumb


def update_metadata(
    attributes: HostAttributes,
    created_by: UserId | None = None,
) -> HostAttributes:
    """Update meta_data timestamps and set created_by if provided.

    Args:
        attributes: The attributes dictionary
        created_by: The user or script which created this object.

    Returns:
        The updated 'attributes' dictionary.

    Examples:

        >>> res = update_metadata(HostAttributes(meta_data=MetaData(updated_at=123)), created_by=UserId('Dog'))
        >>> assert res['meta_data']['created_by'] == 'Dog'
        >>> assert res['meta_data']['created_at'] == 123
        >>> assert 123 < res['meta_data']['updated_at'] <= time.time()

    Notes:

        New in 1.6:
            'meta_data' struct added.
        New in 1.7:
            Key 'updated_at' in 'meta_data' added for use in the REST API.

    """
    attributes = attributes.copy()
    meta_data = attributes.setdefault("meta_data", MetaData())
    now_ = time.time()
    meta_data.setdefault("created_at", meta_data.get("updated_at", now_))
    # NOTE: Something here is screwed up regarding None... :-/
    # if created_by is not None:
    meta_data.setdefault("created_by", created_by)
    meta_data["updated_at"] = now_
    return attributes


class WATOHosts(TypedDict):
    locked: bool
    host_attributes: Mapping[HostName, HostAttributes]
    all_hosts: list[HostName]
    clusters: dict[HostName, list[HostName]]


_REDIS_ENABLED_LOCALLY = True


def may_use_redis() -> bool:
    # Redis can't be used for certain scenarios. For example
    # - Redis server is not running during cmk_update_config.py
    # - Bulk operations which would update redis several thousand times, instead of just once
    #     There is a special context manager which allows to disable redis handling in this case
    return redis_enabled() and _REDIS_ENABLED_LOCALLY and _redis_available()


@request_memoize()
def _redis_available() -> bool:
    return redis_server_reachable(get_redis_client())


@contextmanager
def _disable_redis_locally() -> Iterator[None]:
    global _REDIS_ENABLED_LOCALLY
    last_value = _REDIS_ENABLED_LOCALLY
    _REDIS_ENABLED_LOCALLY = False
    try:
        yield
    finally:
        _REDIS_ENABLED_LOCALLY = last_value


def _wato_folders_factory(tree: FolderTree) -> Mapping[PathWithoutSlash, Folder]:
    if not may_use_redis():
        return _get_fully_loaded_wato_folders(tree)

    redis_client = tree.redis_client
    if redis_client.loaded_wato_folders is not None:
        # Folders were already completely loaded during cache generation -> use these
        return redis_client.loaded_wato_folders

    # Provide a dict where the values are generated on demand
    return WATOFoldersOnDemand(tree, {x.rstrip("/"): None for x in redis_client.folder_paths})


def _core_settings_hosts_to_update(hostnames: Sequence[HostName]) -> DomainSettings:
    return {CORE_DOMAIN: generate_hosts_to_update_settings(hostnames)}


class FolderTree:
    """Folder tree for organizing hosts in Setup"""

    def __init__(self, root_dir: str | None = None, *, config: HostsAndFoldersConfig) -> None:
        self._root_dir = _ensure_trailing_slash(root_dir if root_dir else str(wato_root_dir()))
        self._config = config
        self._all_host_attributes: dict[str, ABCHostAttribute] | None = None
        self._redis_client: _RedisHelper | None = None

    @property
    def redis_client(self) -> _RedisHelper:
        if self._redis_client is None:
            self._redis_client = _RedisHelper(self)
        return self._redis_client

    def all_folders(self) -> Mapping[PathWithoutSlash, Folder]:
        if "wato_folders" not in g:
            g.wato_folders = _wato_folders_factory(self)
        return g.wato_folders

    def folder_choices(self) -> Sequence[tuple[str, str]]:
        if "folder_choices" not in g:
            g.folder_choices = self.root_folder().recursive_subfolder_choices(pretty=True)
        return g.folder_choices

    def folder_choices_fulltitle(self) -> Sequence[tuple[str, str]]:
        if "folder_choices_full_title" not in g:
            g.folder_choices_full_title = self.root_folder().recursive_subfolder_choices(
                pretty=False
            )
        return g.folder_choices_full_title

    def folder(self, folder_path: PathWithoutSlash) -> Folder:
        if folder_path in (folders := self.all_folders()):
            return folders[folder_path]
        raise MKGeneralException("No Setup folder %s." % folder_path)

    def create_missing_folders(
        self, folder_path: PathWithoutSlash, *, pprint_value: bool, use_git: bool
    ) -> None:
        folder = self.root_folder()
        for subfolder_name in FolderTree._split_folder_path(folder_path):
            if (existing_folder := folder.subfolder(subfolder_name)) is None:
                folder = folder.create_subfolder(
                    subfolder_name, subfolder_name, {}, pprint_value=pprint_value, use_git=use_git
                )
            else:
                folder = existing_folder

    @staticmethod
    def _split_folder_path(folder_path: PathWithoutSlash) -> Iterable[str]:
        if not folder_path:
            return []
        return folder_path.split("/")

    def folder_exists(self, folder_path: str) -> bool:
        # We need the slash '/' here
        if regex(r"^[%s/]*$" % WATO_FOLDER_PATH_NAME_CHARS).match(folder_path) is None:
            raise MKUserError("folder", "Folder name is not valid.")
        return os.path.exists(self._root_dir + folder_path)

    def root_folder(self) -> Folder:
        return self.folder("")

    def invalidate_caches(self) -> None:
        # Attention: This will not invalidate all folder caches. (CMK-19211)
        # You might have some references in your code which are not part of the
        # root_folder() hierarchy since the root folder python object is
        # regenerated after calling this method (since we are dropping
        # "wato_folders"), losing all references to its subfolders. This leads
        # to the recursive .drop_caches missing them them.
        self.root_folder().drop_caches()
        if may_use_redis():
            self.redis_client.clear_cached_folders()
        g.pop("wato_folders", {})
        for cache_id in ["folder_choices", "folder_choices_full_title"]:
            g.pop(cache_id, None)
        self._all_host_attributes = None

    def reset_redis_client(self) -> None:
        self._redis_client = None

    def all_host_attributes(self) -> dict[str, ABCHostAttribute]:
        if self._all_host_attributes is None:
            self._all_host_attributes = all_host_attributes(
                self._config.wato_host_attrs, self._config.tags.get_tag_groups_by_topic()
            )
        return self._all_host_attributes

    def _by_id(self, identifier: str) -> Folder:
        """Return the Folder instance of this particular identifier.

        WARNING: This is very slow, don't use it in client code.

        Args:
            identifier (str): The unique key.

        Returns:
            The Folder-instance
        """
        folders = self._mapped_by_id()
        if identifier not in folders:
            raise MKUserError(None, _("Folder %s not found.") % (identifier,))
        return folders[identifier]

    def _mapped_by_id(self) -> dict[str, Folder]:
        """Map all reachable folders via their uuid.uuid4() id.

        This will essentially flatten all Folders into one dictionary, yet uniquely identifiable via
        their respective ids.
        """

        def _update_mapping(_folder: Folder, _mapping: dict[str, Folder]) -> None:
            if not _folder.is_root():
                _mapping[_folder.id()] = _folder
            for _sub_folder in _folder.subfolders():
                _update_mapping(_sub_folder, _mapping)

        mapping: dict[str, Folder] = SetOnceDict()
        _update_mapping(self.root_folder(), mapping)
        return mapping

    def get_root_dir(self) -> PathWithSlash:
        return self._root_dir

    # Dangerous operation! Only use this if you have a good knowledge of the internas
    def set_root_dir(self, root_dir: str) -> None:
        self._root_dir = _ensure_trailing_slash(root_dir)


# Hope that we can cleanup these request global objects one day
def folder_tree() -> FolderTree:
    if "folder_tree" not in g:
        g.folder_tree = FolderTree(config=HostsAndFoldersConfig.from_config(active_config))
    return g.folder_tree


# Hope that we can cleanup these request global objects one day
def folder_lookup_cache() -> FolderLookupCache:
    if "folder_lookup_cache" not in g:
        g.folder_lookup_cache = FolderLookupCache(folder_tree())
    return g.folder_lookup_cache


@request_memoize()
def folder_from_request(var_folder: str | None = None, host_name: str | None = None) -> Folder:
    """
    Return `Folder` that is specified by the current URL

    Optional you can specify the fetched var via calling this function.
    This is currently needed for the search that results in
    ModeEditHost._init_host() were the actual request is available (and not already was cached)
    """
    if var_folder is not None:
        try:
            folder = folder_tree().folder(var_folder)
        except MKGeneralException as e:
            raise MKUserError("folder", "%s" % e)
    else:
        folder = folder_tree().root_folder()
        if host_name is not None:  # find host with full scan. Expensive operation
            host = Host.host(HostName(host_name))
            if host:
                folder = host.folder()

    return folder


@request_memoize()
def disk_or_search_folder_from_request(
    var_folder: str | None = None, host_name: str | None = None
) -> Folder | SearchFolder:
    """Return `Folder` that is specified by the current URL

    This is either by a folder
    path in the variable "folder" or by a host name in the variable "host". In the
    latter case we need to load all hosts in all folders and actively search the host.
    Another case is the host search which has the "host_search" variable set. To handle
    the later case we call search_folder_from_request() to let it decide whether
    this is a host search. This method has to return a folder in all cases.
    """
    search_folder = _search_folder_from_request()
    if search_folder:
        return search_folder

    return folder_from_request(var_folder, host_name)


def _search_folder_from_request() -> SearchFolder | None:
    if request.has_var("host_search"):
        tree = folder_tree()
        base_folder = tree.folder(request.get_str_input_mandatory("folder", ""))
        search_criteria = {
            ".name": request.var("host_search_host"),
            **collect_attributes(
                tree.all_host_attributes(),
                "host_search",
                new=False,
                do_validate=False,
                varprefix="host_search_",
            ),
        }
        return SearchFolder(tree, base_folder, search_criteria)
    return None


def disk_or_search_base_folder_from_request(
    var_folder: str | None = None, host_name: str | None = None
) -> Folder:
    disk_or_search_folder = disk_or_search_folder_from_request(var_folder, host_name)
    if isinstance(disk_or_search_folder, Folder):
        return disk_or_search_folder

    folder = disk_or_search_folder.parent()
    assert isinstance(folder, Folder)
    return folder


class Folder(FolderProtocol):
    """This class represents a Setup folder that contains other folders and hosts."""

    @classmethod
    def new(
        cls,
        *,
        tree: FolderTree,
        name: str,
        parent_folder: Folder,
        title: str | None = None,
        attributes: HostAttributes | None = None,
    ) -> Folder:
        return cls(
            tree=tree,
            name=name,
            parent_folder=parent_folder,
            validators=folder_validators_registry[str(edition(cmk.utils.paths.omd_root))],
            folder_id=uuid.uuid4().hex,
            folder_path=(folder_path := os.path.join(parent_folder.path(), name)),
            title=title or _fallback_title(folder_path),
            attributes=update_metadata(attributes or HostAttributes()),
            locked=False,
            locked_subfolders=False,
            num_hosts=0,
            hosts={},
        )

    @classmethod
    def load(
        cls,
        *,
        tree: FolderTree,
        name: str,
        parent_folder: Folder | None,
    ) -> Folder:
        folder_path = os.path.join(parent_folder.path(), name) if parent_folder else name
        serialized = cls.wato_info_storage_manager().read(
            Path(_folder_wato_info_path(_folder_filesystem_path(tree.get_root_dir(), folder_path)))
        )

        return cls(
            tree=tree,
            name=name,
            parent_folder=parent_folder,
            validators=folder_validators_registry[str(edition(cmk.utils.paths.omd_root))],
            # Cleanup this compatibility code by adding a cmk-update-config action
            folder_id=serialized["__id"] if "__id" in serialized else uuid.uuid4().hex,
            folder_path=folder_path,
            title=serialized.get("title", _fallback_title(folder_path)),
            # Need to add parsing to get rid of this suppression
            attributes=HostAttributes(serialized.get("attributes", {})),  # type: ignore[misc]
            # Can either be set to True or a string (which will be used as host lock message)
            locked=serialized.get("lock", False),
            # Can either be set to True or a string (which will be used as host lock message)
            locked_subfolders=serialized.get("lock_subfolders", False),
            num_hosts=serialized.get("num_hosts", 0),
            # Collection of loaded hosts or None (load on demand)
            hosts=None,
        )

    def __init__(
        self,
        *,
        tree: FolderTree,
        name: str,
        folder_id: str,
        folder_path: str,
        parent_folder: Folder | None,
        validators: FolderValidators,
        title: str,
        attributes: HostAttributes,
        locked: bool,
        locked_subfolders: bool,
        num_hosts: int,
        hosts: dict[HostName, Host] | None,
    ):
        super().__init__()
        self.effective_attributes = EffectiveAttributes(self._compute_effective_attributes)
        self.permissions = PermissionChecker(self._user_needs_permission)
        self.validators = validators
        self.tree = tree
        self._name = name
        self._id = folder_id
        self._path = folder_path
        self._title = title
        self.attributes = attributes
        self._locked = locked
        self._locked_subfolders = locked_subfolders
        self._locked_hosts = False
        self._parent = parent_folder
        self._num_hosts = num_hosts
        self._hosts = hosts

        self._loaded_subfolders: dict[PathWithoutSlash, Folder] | None = None
        self._choices_for_moving_host: Choices | None = None

    @property
    def _subfolders(self) -> dict[PathWithoutSlash, Folder]:
        if self._loaded_subfolders is None:
            self._loaded_subfolders = self._load_subfolders()
        return self._loaded_subfolders

    def __repr__(self) -> str:
        return f"Folder({self.path()!r}, {self._title!r})"

    def breadcrumb(self) -> Breadcrumb:
        return _folder_breadcrumb(self)

    def parent(self) -> Folder | None:
        return self._parent

    def is_current_folder(self) -> bool:
        return self.is_same_as(
            folder_from_request(request.var("folder"), request.get_ascii_input("host"))
        )

    def is_transitive_parent_of(self, maybe_child: Folder) -> bool:
        if self.is_same_as(maybe_child):
            return True

        if not maybe_child.has_parent():
            return False

        if parent := maybe_child.parent():
            return self.is_transitive_parent_of(parent)

        return False

    def is_root(self) -> bool:
        return not self.has_parent()

    def is_disk_folder(self) -> bool:
        return True

    def _load_hosts_on_demand(self) -> None:
        if self._hosts is None:
            self._load_hosts()

    def _load_hosts(self) -> None:
        self._locked_hosts = False

        self._hosts = {}
        if (wato_hosts := self._load_wato_hosts()) is None:
            return

        # Can either be set to True or a string (which will be used as host lock message)
        self._locked_hosts = wato_hosts["locked"]

        # Build list of individual hosts
        for host_name in wato_hosts["host_attributes"].keys():
            # typing: Conversion to HostName shouldn't be necessary.
            host_name = HostName(host_name)
            host = self._create_host_from_variables(host_name, wato_hosts)
            self._hosts[host_name] = host

    def _create_host_from_variables(self, host_name: HostName, wato_hosts: WATOHosts) -> Host:
        cluster_nodes = wato_hosts["clusters"].get(host_name)
        return Host(self, host_name, wato_hosts["host_attributes"][host_name], cluster_nodes)

    def _load_hosts_file(self) -> HostsData | None:
        variables = get_hosts_file_variables()
        apply_hosts_file_to_object(
            Path(self.hosts_file_path_without_extension()),
            get_host_storage_loaders(
                get_storage_format(active_config.config_storage_format),
            ),
            variables,
        )
        return variables

    def _load_wato_hosts(self) -> WATOHosts | None:
        if (variables := self._load_hosts_file()) is None:
            return None
        return WATOHosts(
            locked=variables["_lock"],
            host_attributes=variables["host_attributes"],
            all_hosts=variables["all_hosts"],
            clusters=variables["clusters"],
        )

    def save_hosts(self, *, pprint_value: bool) -> None:
        self.need_unlocked_hosts()
        self.permissions.need_permission("write")
        if self._hosts is not None:
            # Clean up caches of all hosts in this folder, just to be sure. We could also
            # check out all call sites of save_hosts() and partially drop the caches of
            # individual hosts to optimize this.
            for host in self._hosts.values():
                host.drop_caches()

            self._save_hosts_file(
                storage_list=self.get_storage_formatters(), pprint_value=pprint_value
            )
            if may_use_redis():
                # Inform redis that the modified-timestamp of the folder has been updated.
                self.tree.redis_client.folder_updated(self.filesystem_path())

        call_hook_hosts_changed(self)

    def _save_hosts_file(
        self, *, storage_list: Sequence[ABCHostsStorage], pprint_value: bool
    ) -> None:
        Path(self.filesystem_path()).mkdir(mode=0o770, parents=True, exist_ok=True)
        exposed_folder_attributes_for_base = self._folder_attributes_for_base_config()
        if not self.has_hosts() and not exposed_folder_attributes_for_base:
            for storage in get_all_storage_readers():
                storage.remove(Path(self.hosts_file_path_without_extension()))
            return

        all_hosts: list[HostName] = []
        clusters: dict[HostName, Sequence[HostName]] = {}
        # collect value for attributes that are to be present in Nagios
        custom_macros: dict[str, dict[HostName, str]] = {}
        # collect value for attributes that are explicitly set for one host
        explicit_host_conf: dict[str, dict[HostName, str]] = {}
        cleaned_hosts = {}
        host_tags = {}
        host_labels = {}
        group_rules_list: list[tuple[list[GroupRuleType], bool]] = []

        attribute_mappings: Sequence[tuple[str, str, dict[str, Any]]] = [
            # host attr, cmk.base variable name, value
            ("ipaddress", "ipaddresses", {}),
            ("ipv6address", "ipv6addresses", {}),
            ("snmp_community", "explicit_snmp_communities", {}),
            ("management_snmp_community", "management_snmp_credentials", {}),
            ("management_ipmi_credentials", "management_ipmi_credentials", {}),
            ("management_protocol", "management_protocol", {}),
        ]

        host_attributes = self.tree.all_host_attributes()
        for hostname, host in sorted(self.hosts().items()):
            effective = host.effective_attributes()
            cleaned_hosts[hostname] = update_metadata(host.attributes, created_by=user.id)
            host_labels[hostname] = effective["labels"]

            tag_groups = host.tag_groups()
            if tag_groups:
                host_tags[hostname] = tag_groups

            if host.is_cluster():
                nodes = host.cluster_nodes()
                assert nodes is not None
                clusters[hostname] = nodes
            else:
                all_hosts.append(hostname)

            # Save the effective attributes of a host to the related attribute maps.
            # These maps are saved directly in the hosts.mk to transport the effective
            # attributes to Checkmk base.
            for (
                attribute_name,
                _cmk_var_name,
                dictionary,
            ) in attribute_mappings:
                value = effective.get(attribute_name)
                if value:
                    dictionary[hostname] = value

            # Create contact group rule entries for hosts with explicitly set
            # values Note: since the type if this entry is a list, not a single
            # contact group, all other list entries coming after this one will
            # be ignored. That way the host-entries have precedence over the
            # folder entries.
            #
            # LM: This comment is wrong. The folders create list entries,
            # but the hosts create string entries. This makes the hosts add
            # their contact groups in addition to the effective folder contact
            # groups I went back to ~2015 and it seems it was always working
            # this way. I won't change it now and leave the comment here for
            # reference.
            if "contactgroups" in host.attributes:
                cgconfig = host.attributes["contactgroups"]
                cgs = cgconfig["groups"]
                if cgs and cgconfig["use"]:
                    group_rules: list[GroupRuleType] = []
                    for cg in cgs:
                        group_rules.append(
                            {
                                "value": cg,
                                "condition": {"host_name": [hostname]},
                            }
                        )
                    group_rules_list.append((group_rules, cgconfig["use_for_services"]))

            for attrname, attr in host_attributes.items():
                if attrname in effective:
                    custom_varname = attr.nagios_name()
                    if custom_varname:
                        value = effective.get(attrname)
                        nagstring = attr.to_nagios(value)
                        if nagstring is not None:
                            if attr.is_explicit():
                                explicit_host_conf.setdefault(custom_varname, {})
                                explicit_host_conf[custom_varname][hostname] = nagstring
                            else:
                                custom_macros.setdefault(custom_varname, {})
                                custom_macros[custom_varname][hostname] = nagstring

        data = HostsStorageData(
            locked_hosts=False,
            all_hosts=all_hosts,
            clusters=clusters,
            attributes={
                cmk_var_name: values
                for _attribute_name, cmk_var_name, values in attribute_mappings
                if values
            },
            custom_macros=HostsStorageFieldsGenerator.custom_macros(custom_macros),
            host_tags=host_tags,
            host_labels=host_labels,
            contact_groups=HostsStorageFieldsGenerator.contact_groups(
                host_service_group_rules=group_rules_list,
                folder_host_service_group_rules=self.groups(),
                folder_path=self.path_for_rule_matching(),
            ),
            explicit_host_conf=explicit_host_conf,
            host_attributes=cleaned_hosts,
            folder_attributes=exposed_folder_attributes_for_base,
        )

        formatter = pprint.pformat if pprint_value else repr
        for storage_module in storage_list:
            storage_module.write(
                Path(self.hosts_file_path_without_extension()),
                data,
                formatter,
            )

    def get_storage_formatters(self) -> list[ABCHostsStorage]:
        storage_list: list[ABCHostsStorage] = [StandardHostsStorage()]
        if experimental_storage := make_experimental_hosts_storage(
            get_storage_format(active_config.config_storage_format)
        ):
            storage_list.append(experimental_storage)
        return storage_list

    def _folder_attributes_for_base_config(self) -> dict[str, FolderAttributesForBase]:
        # TODO:
        # At this time, this is the only attribute there is, at it only exists in the CEE.
        # This functionality should be moved to CEE specific code!
        if "bake_agent_package" in self.attributes:
            return {
                self.path_for_rule_matching(): {
                    "bake_agent_package": bool(self.attributes["bake_agent_package"]),
                },
            }
        return {}

    def save(self, *, pprint_value: bool) -> None:
        self.save_folder_attributes()
        self.tree.invalidate_caches()
        self.save_hosts(pprint_value=pprint_value)

    def serialize(self) -> WATOFolderInfo:
        return {
            "__id": self._id,
            "title": self._title,
            "attributes": self.attributes,
            "num_hosts": self._num_hosts,
            "lock": self._locked,
            "lock_subfolders": self._locked_subfolders,
        }

    def _load_subfolders(self) -> dict[PathWithoutSlash, Folder]:
        loaded_subfolders: dict[str, Folder] = {}

        root_dir = self.tree.get_root_dir()
        dir_path = root_dir + self.path()
        if not os.path.exists(dir_path):
            return loaded_subfolders

        for entry in os.listdir(dir_path):
            subfolder_dir = os.path.join(dir_path, entry)
            if os.path.isdir(subfolder_dir):
                loaded_subfolders[entry] = Folder.load(
                    tree=self.tree,
                    name=entry,
                    parent_folder=self,
                )

        return loaded_subfolders

    def wato_info_path(self) -> str:
        return _folder_wato_info_path(self.filesystem_path())

    def hosts_file_path(self) -> str:
        return self.hosts_file_path_without_extension() + ".mk"

    def hosts_file_path_without_extension(self) -> str:
        return self.filesystem_path() + "/hosts"

    def rules_file_path(self) -> Path:
        return Path(self.filesystem_path()) / "rules.mk"

    def add_to_dictionary(self, dictionary: dict[PathWithoutSlash, Folder]) -> None:
        dictionary[self.path()] = self
        for subfolder in self._subfolders.values():
            subfolder.add_to_dictionary(dictionary)

    def drop_caches(self) -> None:
        self.effective_attributes.drop_caches()
        self._choices_for_moving_host = None

        if self._hosts is not None:
            for host in self._hosts.values():
                host.drop_caches()

        if self._loaded_subfolders is None:
            return

        for subfolder in self._loaded_subfolders.values():
            subfolder.drop_caches()

    def id(self) -> str:
        """The unique identifier of this particular instance.

        Returns:
            The id.
        """
        # TODO: Improve the API + the typing, this is horrible...
        if self._id is None:
            raise ValueError("unique identifier not set")
        return self._id

    @classmethod
    def wato_info_storage_manager(cls) -> _WATOInfoStorageManager:
        if "wato_info_storage_manager" not in g:
            g.wato_info_storage_manager = _WATOInfoStorageManager(
                active_config.config_storage_format
            )
        return g.wato_info_storage_manager

    def save_folder_attributes(self) -> None:
        """Save the current state of the instance to a file."""
        self.attributes = update_metadata(self.attributes)
        Path(self.wato_info_path()).parent.mkdir(mode=0o770, parents=True, exist_ok=True)
        self.wato_info_storage_manager().write(Path(self.wato_info_path()), self.serialize())
        if may_use_redis():
            self.tree.redis_client.save_folder_info(self)

    def has_rules(self) -> bool:
        return self.rules_file_path().exists()

    def is_empty(self) -> bool:
        return not (self.has_hosts() or self.has_subfolders() or self.has_rules())

    def is_referenced(self) -> bool:
        conditions = PredefinedConditionStore().filter_by_path(self.path())
        return len(conditions) > 0

    # .-----------------------------------------------------------------------.
    # | ELEMENT ACCESS                                                        |
    # '-----------------------------------------------------------------------'

    def name(self) -> str:
        return self._name

    def title(self) -> str:
        return self._title

    def filesystem_path(self) -> PathWithoutSlash:
        return _folder_filesystem_path(self.tree.get_root_dir(), self.path())

    def ident(self) -> str:
        return self.path()

    def path(self) -> str:
        if may_use_redis() and self._path is not None:
            return self._path

        if (parent := self.parent()) and not parent.is_root() and not self.is_root():
            return _ensure_trailing_slash(parent.path()) + self.name()

        return self.name()

    def path_for_gui_rule_matching(self) -> PathWithSlash:
        if self.is_root():
            return "/"
        return "/wato/%s/" % self.path()

    def path_for_rule_matching(self) -> PathWithSlash:
        return self.make_path_for_rule_matching_from_path(self.path())

    # I'm adding these two static methods in self-defense.
    # Ít seems we have three ways to refer to a folder; all typed as strings.
    # What could possibly go wrong?
    @staticmethod
    def make_path_for_rule_matching_from_path(path: str) -> str:
        if path.startswith("/wato/"):
            raise ValueError(path)
        return f"/wato/{path}/" if path else "/wato/"

    @staticmethod
    def make_path_from_path_for_rule_matching(path_for_rule_matching: str) -> str:
        if not path_for_rule_matching.startswith("/wato/"):
            raise ValueError(path_for_rule_matching)
        return path_for_rule_matching[len("/wato/") :].rstrip("/")

    @classmethod
    def from_path_for_rule_matching(cls, path_for_rule_matching: str) -> Folder:
        return folder_tree().folder(
            cls.make_path_from_path_for_rule_matching(path_for_rule_matching)
        )

    def object_ref(self) -> ObjectRef:
        return ObjectRef(ObjectRefType.Folder, self.path())

    def host_names(self) -> Sequence[HostName]:
        return list(self.hosts().keys())

    def load_host(self, host_name: HostName) -> Host:
        try:
            return self.hosts()[host_name]
        except KeyError:
            raise MKUserError(None, f"The host {host_name} could not be found.")

    def host(self, host_name: HostName) -> Host | None:
        return self.hosts().get(host_name)

    def has_host(self, host_name: HostName) -> bool:
        return host_name in self.hosts()

    def has_hosts(self) -> bool:
        return len(self.hosts()) != 0

    def host_validation_errors(self) -> dict[HostName, list[str]]:
        return validate_all_hosts(self.tree, self.host_names())

    def has_parent(self) -> bool:
        return self.parent() is not None

    def is_same_as(self, folder: Folder | None) -> bool:
        if folder is None:
            return False
        return self == folder or self.path() == folder.path()

    def __eq__(self, other: object) -> bool:
        return id(self) == id(other) or (isinstance(other, Folder) and self.path() == other.path())

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Folder):
            return NotImplemented

        return self.path() < other.path()

    def __hash__(self) -> int:
        return id(self)

    def hosts(self) -> Mapping[HostName, Host]:
        self._load_hosts_on_demand()
        assert self._hosts is not None
        return self._hosts

    def num_hosts(self) -> int:
        # Do *not* load hosts here! This method must kept cheap
        return self._num_hosts

    def num_hosts_recursively(self) -> int:
        if may_use_redis():
            if folder_metadata := self.tree.redis_client.folder_metadata(self.path()):
                return folder_metadata.num_hosts_recursively
            return 0

        num = self.num_hosts()
        for subfolder in self.subfolders(only_visible=True):
            num += subfolder.num_hosts_recursively()
        return num

    def all_hosts_recursively(self) -> dict[HostName, Host]:
        hosts: dict[HostName, Host] = {}
        hosts.update(self.hosts())
        for subfolder in self.subfolders():
            hosts.update(subfolder.all_hosts_recursively())
        return hosts

    def subfolders_recursively(self, only_visible: bool = False) -> list[Folder]:
        def _add_folders(folder: Folder, collection: list[Folder]) -> None:
            collection.append(folder)
            for sub_folder in folder.subfolders(only_visible=only_visible):
                _add_folders(sub_folder, collection)

        folders: list[Folder] = []
        _add_folders(self, folders)
        return folders

    def subfolders(self, only_visible: bool = False) -> list[Folder]:
        """Filter subfolder collection by various means.

        Args:
            only_visible:
                Only show visible folders. Default is to show all folders.

        Returns:
            A dict with the keys being the relative subfolder-name, and the value
            being the Folder instance.
        """
        subfolders = list(self._subfolders.values())

        if only_visible:
            return [folder for folder in subfolders if folder.folder_should_be_shown("read")]

        return subfolders

    def subfolder(self, name: str) -> Folder | None:
        """Find a Folder by its name-part.

        Args:
            name (str): The basename of this Folder, not its path.

        Returns:
            The found Folder-instance or None.
        """
        with suppress(KeyError):
            return self._subfolders[name]
        return None

    def subfolder_by_title(self, title: str) -> Folder | None:
        """Find a Folder by its title.

        Args:
            title (str): The `title()` of the folder to retrieve.

        Returns:
            The found Folder-instance or None.

        """
        return next((f for f in self.subfolders() if f.title() == title), None)

    def has_subfolder(self, name: str) -> bool:
        return name in self._subfolders

    def has_subfolders(self) -> bool:
        return len(self._subfolders) > 0

    def subfolder_choices(self) -> list[tuple[str, str]]:
        choices = []
        for subfolder in sorted(
            self.subfolders(only_visible=True), key=operator.methodcaller("title")
        ):
            choices.append((subfolder.path(), subfolder.title()))
        return choices

    def _prefixed_title(self, current_depth: int, pretty: bool) -> str:
        if not pretty:
            return "/".join(str(p) for p in self.title_path_without_root())

        title_prefix = ("\u00a0" * 6 * current_depth) + "\u2514\u2500 " if current_depth else ""
        return title_prefix + self.title()

    def _walk_tree(
        self, results: list[tuple[str, str]], *, current_depth: int, pretty: bool
    ) -> bool:
        visible_subfolders = False
        for subfolder in sorted(
            self._subfolders.values(), key=operator.methodcaller("title"), reverse=True
        ):
            visible_subfolders = (
                subfolder._walk_tree(results, current_depth=current_depth + 1, pretty=pretty)
                or visible_subfolders
            )

        if (
            visible_subfolders
            or self.permissions.may("read")
            or self.is_root()
            or not active_config.wato_hide_folders_without_read_permissions
        ):
            results.append((self.path(), self._prefixed_title(current_depth, pretty)))
            return True

        return False

    def recursive_subfolder_choices(self, *, pretty: bool) -> Sequence[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        self._walk_tree(result, current_depth=0, pretty=pretty)
        result.reverse()
        return result

    def choices_for_moving_folder(self) -> Choices:
        return self._choices_for_moving("folder")

    def choices_for_moving_host(self) -> Choices:
        if self._choices_for_moving_host is not None:
            return self._choices_for_moving_host  # Cached

        self._choices_for_moving_host = self._choices_for_moving("host")
        return self._choices_for_moving_host

    def folder_should_be_shown(self, how: Literal["read", "write"]) -> bool:
        if not active_config.wato_hide_folders_without_read_permissions:
            return True

        has_permission = self.permissions.may(how)
        for subfolder in self.subfolders():
            if has_permission:
                break
            has_permission = subfolder.folder_should_be_shown(how)

        return has_permission

    def _choices_for_moving(self, what: str) -> Choices:
        choices: Choices = []

        if may_use_redis():
            return self._get_sorted_choices(
                self.tree.redis_client.choices_for_moving(
                    self.path(),
                    _MoveType(what),
                    may_see_all_folders=user.may("wato.all_folders"),
                    user_contact_groups=(
                        set(userdb.contactgroups_of_user(user.id)) if user.id is not None else set()
                    ),
                )
            )

        for folder in self.tree.all_folders().values():
            if not folder.permissions.may("write"):
                continue
            if folder.is_same_as(self):
                continue  # do not move into itself

            if what == "folder":
                if folder.is_same_as(self.parent()):
                    continue  # We are already in that folder
                if folder in folder.subfolders():
                    continue  # naming conflict
                if self.is_transitive_parent_of(folder):
                    continue  # we cannot be moved in our child folder

            choices.append(folder.as_choice_for_moving())

        return self._get_sorted_choices(choices)

    def _get_sorted_choices(self, choices: Choices) -> Choices:
        choices.sort(key=lambda x: x[1].lower())
        return choices

    def site_id(self) -> SiteId:
        """Returns the ID of the site that responsible for hosts in this folder

        - Use explicitly set site attribute
        - Go down the folder hierarchy to find a folder with set site attribute
        - Remote sites: Use "" -> Assigned to central site
        - Standalone and central sites: Use the ID of the local site
        """
        if "site" in self.attributes:
            return self.attributes["site"]
        if self.has_parent():
            parent = self.parent()
            assert parent is not None
            return parent.site_id()
        if not is_distributed_setup_remote_site(active_config.sites):
            return omd_site()

        # Placeholder for "central site". This is only relevant when using Setup on a remote site
        # and a host / folder has no site set.
        return SiteId("")

    def all_site_ids(self) -> list[SiteId]:
        site_ids: set[SiteId] = set()
        self._add_all_sites_to_set(site_ids)
        return list(site_ids)

    def title_path_with_links(self) -> list[HTML]:
        return [
            HTMLWriter.render_a(
                folder.title(),
                href=urls.makeuri_contextless(
                    request,
                    [("mode", "folder"), ("folder", folder.path())],
                    filename="wato.py",
                ),
            )
            for folder in parent_folder_chain(self) + [self]
        ]

    def title_path(self) -> list[str]:
        return [folder.title() for folder in parent_folder_chain(self) + [self]]

    def title_path_without_root(self) -> list[str]:
        if self.is_root():
            return [self.title()]
        return self.title_path()[1:]

    def alias_path(self, show_main: bool = True) -> str:
        tp = self.title_path() if show_main else self.title_path_without_root()
        return " / ".join(str(p) for p in tp)

    def as_choice_for_moving(self) -> tuple[str, str]:
        return self.path(), "/".join(str(p) for p in self.title_path_without_root())

    def _compute_effective_attributes(self) -> HostAttributes:
        effective = HostAttributes()
        for folder in parent_folder_chain(self):
            effective.update(folder.attributes)
        effective.update(self.attributes)

        # now add default values of attributes for all missing values
        for attrname, host_attribute in self.tree.all_host_attributes().items():
            if attrname not in effective:
                # Mypy can not help here with the dynamic key
                effective.setdefault(attrname, get_host_attribute_default_value(host_attribute))  # type: ignore[misc]

        return effective

    def groups(
        self, host: Host | None = None
    ) -> tuple[set[_ContactgroupName], set[_ContactgroupName], bool]:
        # CLEANUP: this method is also used for determining host permission
        # in behalv of Host::groups(). Not nice but was done for avoiding
        # code duplication
        permitted_groups = set()
        host_contact_groups = set()
        if host:
            effective_folder_attributes = host.effective_attributes()
        else:
            effective_folder_attributes = self.effective_attributes()
        cgconf = _get_cgconf_from_attributes(effective_folder_attributes)

        # First set explicit groups
        permitted_groups.update(cgconf["groups"])
        if cgconf["use"]:
            host_contact_groups.update(cgconf["groups"])

        parent: Folder | None
        if host:
            parent = self
        else:
            parent = self.parent()

        while parent:
            effective_folder_attributes = parent.effective_attributes()
            parconf = _get_cgconf_from_attributes(effective_folder_attributes)
            (
                parent_permitted_groups,
                parent_host_contact_groups,
                _parent_use_for_services,
            ) = parent.groups()

            if parconf["recurse_perms"]:  # Parent gives us its permissions
                permitted_groups.update(parent_permitted_groups)

            if parconf["recurse_use"]:  # Parent give us its contact groups
                host_contact_groups.update(parent_host_contact_groups)

            parent = parent.parent()

        return (
            permitted_groups,
            host_contact_groups,
            cgconf.get("use_for_services", False),
        )

    def find_host_recursively(self, host_name: HostName) -> Host | None:
        host: Host | None = self.host(host_name)
        if host:
            return host

        for subfolder in self.subfolders():
            host = subfolder.find_host_recursively(host_name)
            if host:
                return host
        return None

    def _user_needs_permission(self, how: Literal["read", "write"]) -> None:
        if how == "write" and user.may("wato.all_folders"):
            return

        if how == "read" and user.may("wato.see_all_folders"):
            return

        if self.is_contact(user):
            return

        permitted_groups, _folder_contactgroups, _use_for_services = self.groups()

        reason = _("Sorry, you have no permissions to the folder <b>%s</b>.") % self.alias_path()
        if not permitted_groups:
            reason += " " + _("The folder is not permitted for any contact group.")
        else:
            reason += " " + _("The folder's permitted contact groups are <b>%s</b>.") % ", ".join(
                permitted_groups
            )
            if user_contactgroups := user.contact_groups:
                reason += " " + _("Your contact groups are <b>%s</b>.") % ", ".join(
                    user_contactgroups
                )
            else:
                reason += " " + _("But you are not a member of any contact group.")
        reason += " " + _(
            "You may enter the folder as you might have permission on a subfolder, though."
        )
        raise MKAuthException(reason)

    def is_contact(self, user_: LoggedInUser) -> bool:
        permitted_groups, _host_contact_groups, _use_for_services = self.groups()
        return any(group in permitted_groups for group in user_.contact_groups)

    def need_recursive_permission(self, how: Literal["read", "write"]) -> None:
        self.permissions.need_permission(how)
        if how == "write":
            self.need_unlocked()
            self.need_unlocked_subfolders()
            self.need_unlocked_hosts()

        for subfolder in self.subfolders():
            subfolder.need_recursive_permission(how)

    def need_unlocked(self) -> None:
        if self.locked():
            raise MKAuthException(
                _("Sorry, you cannot edit the folder %s. It is locked.") % self.title()
            )

    def need_unlocked_hosts(self) -> None:
        if self.locked_hosts():
            raise MKAuthException(_("Sorry, the hosts in the folder %s are locked.") % self.title())

    def need_unlocked_subfolders(self) -> None:
        if self.locked_subfolders():
            raise MKAuthException(
                _("Sorry, the sub folders in the folder %s are locked.") % self.title()
            )

    def url(self, add_vars: HTTPVariables | None = None) -> str:
        if add_vars is None:
            add_vars = []

        url_vars: HTTPVariables = [("folder", self.path())]
        have_mode = False
        for varname, _value in add_vars:
            if varname == "mode":
                have_mode = True
                break
        if not have_mode:
            url_vars.append(("mode", "folder"))
        if request.var("debug") == "1":
            add_vars.append(("debug", "1"))
        url_vars += add_vars
        return urls.makeuri_contextless(request, url_vars, filename="wato.py")

    def edit_url(self, backfolder: Folder | None = None) -> str:
        if backfolder is None:
            if self.has_parent():
                parent = self.parent()
                assert parent is not None
                backfolder = parent
            else:
                backfolder = self
        return urls.makeuri_contextless(
            request,
            [
                ("mode", "editfolder"),
                ("folder", self.path()),
                ("backfolder", backfolder.path()),
            ],
            filename="wato.py",
        )

    def locked(self) -> bool | str:
        return self._locked

    def locked_subfolders(self) -> bool | str:
        return self._locked_subfolders

    def locked_hosts(self) -> bool | str:
        self._load_hosts_on_demand()
        return self._locked_hosts

    # Returns:
    #  None:      No network scan is enabled.
    #  timestamp: Next planned run according to config.
    def next_network_scan_at(self) -> float | None:
        if "network_scan" not in self.attributes:
            return None

        interval = self.attributes["network_scan"]["scan_interval"]
        last_end = self.attributes.get("network_scan_result", {}).get("end", None)
        if last_end is None:
            next_time = time.time()
        else:
            next_time = last_end + interval

        time_allowed = self.attributes["network_scan"].get("time_allowed")
        if time_allowed is None:
            return next_time  # No time frame limit

        # Transform pre 1.6 single time window to list of time windows
        times_allowed = [time_allowed] if isinstance(time_allowed, tuple) else time_allowed

        # Compute "next time" with all time windows individually and use earliest time
        next_allowed_times = []
        for time_allowed in times_allowed:
            # First transform the time given by the user to UTC time
            brokentime = time.localtime(next_time)
            start_tm_hour, start_tm_min = time_allowed[0]
            start_time = time.mktime(
                (
                    brokentime.tm_year,
                    brokentime.tm_mon,
                    brokentime.tm_mday,
                    start_tm_hour,
                    start_tm_min,
                    brokentime.tm_sec,
                    brokentime.tm_wday,
                    brokentime.tm_yday,
                    brokentime.tm_isdst,
                )
            )

            end_tm_hour, end_tm_min = time_allowed[1]
            end_time = time.mktime(
                (
                    brokentime.tm_year,
                    brokentime.tm_mon,
                    brokentime.tm_mday,
                    end_tm_hour,
                    end_tm_min,
                    brokentime.tm_sec,
                    brokentime.tm_wday,
                    brokentime.tm_yday,
                    brokentime.tm_isdst,
                )
            )

            # In case the next time is earlier than the allowed time frame at a day set
            # the time to the time frame start.
            # In case the next time is in the time frame leave it at it's value.
            # In case the next time is later then advance one day to the start of the
            # time frame.
            if next_time < start_time:
                next_allowed_times.append(start_time)
            elif next_time > end_time:
                next_allowed_times.append(start_time + 86400)
            else:
                next_allowed_times.append(next_time)

        return min(next_allowed_times)

    # .-----------------------------------------------------------------------.
    # | MODIFICATIONS                                                         |
    # |                                                                       |
    # | These methods are for being called by actual Setup modules when they  |
    # | want to modify folders and hosts. They all check permissions and      |
    # | locking. They may raise MKAuthException or MKUserError.               |
    # |                                                                       |
    # | Folder permissions: Creation and deletion of subfolders needs write   |
    # | permissions in the parent folder (like in Linux).                     |
    # |                                                                       |
    # | Locking: these methods also check locking. Locking is for preventing  |
    # | changes in files that are created by third party applications.        |
    # | A folder has three lock attributes:                                   |
    # |                                                                       |
    # | - locked_hosts() -> hosts.mk file in the folder must not be modified  |
    # | - locked()       -> .wato file in the folder must not be modified     |
    # | - locked_subfolders() -> No subfolders may be created/deleted         |
    # |                                                                       |
    # | Sidebar: some sidebar snap-ins show the Setup folder tree. Everytime  |
    # | the tree changes the sidebar needs to be reloaded. This is done here. |
    # |                                                                       |
    # | Validation: these methods do *not* validate the parameters for syntax.|
    # | This is the task of the actual Setup modes or the API.                |
    # '-----------------------------------------------------------------------'

    def create_subfolder(
        self,
        name: str,
        title: str,
        attributes: HostAttributes,
        *,
        pprint_value: bool,
        use_git: bool,
    ) -> Folder:
        """Create a subfolder of the current folder"""
        # 1. Check preconditions
        user.need_permission("wato.manage_folders")
        self.permissions.need_permission("write")
        self.need_unlocked_subfolders()
        self.validators.validate_create_subfolder(self, attributes)
        _must_be_in_contactgroups(_get_cgconf_from_attributes(attributes)["groups"])

        attributes = update_metadata(attributes, created_by=user.id)

        # 2. Actual modification
        new_subfolder = Folder.new(
            tree=self.tree,
            name=name,
            parent_folder=self,
            title=title,
            attributes=attributes,
        )
        self._subfolders[name] = new_subfolder
        new_subfolder.save(pprint_value=pprint_value)
        add_change(
            action_name="new-folder",
            text=_l("Created new folder %s") % new_subfolder.alias_path(),
            user_id=user.id,
            object_ref=new_subfolder.object_ref(),
            sites=[new_subfolder.site_id()],
            diff_text=diff_attributes({}, None, new_subfolder.attributes, None),
            use_git=use_git,
        )
        hooks.call("folder-created", new_subfolder)
        need_sidebar_reload()
        return new_subfolder

    def delete_subfolder(self, name: str, *, use_git: bool) -> None:
        # 1. Check preconditions
        user.need_permission("wato.manage_folders")
        self.permissions.need_permission("write")
        self.need_unlocked_subfolders()

        subfolder = self.subfolder(name)
        if subfolder is None:
            return

        # 2. Check if hosts can be deleted
        self._validate_delete_hosts(subfolder.all_hosts_recursively().keys())

        # 3. Actual modification
        hooks.call("folder-deleted", subfolder)
        add_change(
            action_name="delete-folder",
            text=_l("Deleted folder %s") % subfolder.alias_path(),
            user_id=user.id,
            object_ref=self.object_ref(),
            sites=subfolder.all_site_ids(),
            use_git=use_git,
        )
        del self._subfolders[name]
        shutil.rmtree(subfolder.filesystem_path())
        self.tree.invalidate_caches()
        need_sidebar_reload()
        folder_lookup_cache().delete()

    def move_subfolder_to(
        self, subfolder: Folder, target_folder: Folder, *, pprint_value: bool, use_git: bool
    ) -> None:
        # 1. Check preconditions
        user.need_permission("wato.manage_folders")
        self.permissions.need_permission("write")
        self.need_unlocked_subfolders()
        target_folder.permissions.need_permission("write")
        target_folder.need_unlocked_subfolders()
        subfolder.need_recursive_permission("write")  # Inheritance is changed
        self.validators.validate_move_subfolder_to(subfolder, target_folder)
        if os.path.exists(target_folder.filesystem_path() + "/" + subfolder.name()):
            raise MKUserError(
                None,
                _(
                    "Cannot move folder: A folder with this name already exists in the target folder."
                ),
            )

        if subfolder.path() == target_folder.path():
            raise MKUserError(
                None,
                _("Cannot move folder: A folder cannot be moved into itself."),
            )

        if self.path() == target_folder.path():
            raise MKUserError(
                None,
                _("Cannot move folder: A folder cannot be moved to its own parent folder."),
            )

        if subfolder in parent_folder_chain(target_folder):
            raise MKUserError(
                None,
                _("Cannot move folder: A folder cannot be moved into a folder within itself."),
            )

        original_alias_path = subfolder.alias_path()

        # 2. Actual modification
        affected_sites = subfolder.all_site_ids()
        old_filesystem_path = subfolder.filesystem_path()
        shutil.move(old_filesystem_path, target_folder.filesystem_path())

        self.tree.invalidate_caches()

        # Since redis only updates on the next request, we can no longer use it here
        # We COULD enforce a redis update here, but this would take too much time
        # After the move action, the request is finished anyway.
        with _disable_redis_locally():
            # Reload folder at new location and rewrite host files
            # Again, some special handling because of the missing slash in the main folder
            if not target_folder.is_root():
                moved_subfolder = self.tree.folder(f"{target_folder.path()}/{subfolder.name()}")
            else:
                moved_subfolder = self.tree.folder(subfolder.name())

            # Do not update redis while rewriting a plethora of host files
            # Redis automatically updates on the next request
            moved_subfolder.recursively_save_hosts(
                pprint_value=pprint_value
            )  # fixes changed inheritance

        affected_sites = list(set(affected_sites + moved_subfolder.all_site_ids()))
        add_change(
            action_name="move-folder",
            text=_l("Moved folder %s to %s") % (original_alias_path, target_folder.alias_path()),
            user_id=user.id,
            object_ref=moved_subfolder.object_ref(),
            sites=affected_sites,
            use_git=use_git,
        )
        need_sidebar_reload()
        folder_lookup_cache().delete()

    def edit(
        self,
        new_title: str,
        new_attributes: HostAttributes,
        *,
        pprint_value: bool,
        use_git: bool,
    ) -> None:
        # 1. Check preconditions
        user.need_permission("wato.edit_folders")
        self.permissions.need_permission("write")
        self.need_unlocked()
        self.validators.validate_edit_folder(self, new_attributes)

        # For changing contact groups user needs write permission on parent folder
        new_cgconf = _get_cgconf_from_attributes(new_attributes)
        old_cgconf = _get_cgconf_from_attributes(self.attributes)
        if new_cgconf != old_cgconf:
            _validate_contact_group_modification(old_cgconf["groups"], new_cgconf["groups"])

            if self.has_parent():
                parent = self.parent()
                assert parent is not None
                if not parent.permissions.may("write"):
                    raise MKAuthException(
                        _(
                            "Sorry. In order to change the permissions of a folder you need write "
                            "access to the parent folder."
                        )
                    )

        # 2. Actual modification

        # Due to a change in the attribute "site" a host can move from
        # one site to another. In that case both sites need to be marked
        # dirty. Therefore we first mark dirty according to the current
        # host->site mapping and after the change we mark again according
        # to the new mapping.
        affected_sites = self.all_site_ids()

        diff = diff_attributes(self.attributes, None, new_attributes, None)

        self._title = new_title
        self.attributes = new_attributes

        # Due to changes in folder/file attributes, host files
        # might need to be rewritten in order to reflect Changes
        # in Nagios-relevant attributes.
        self.save_folder_attributes()
        self.tree.invalidate_caches()
        self.recursively_save_hosts(pprint_value=pprint_value)

        affected_sites = list(set(affected_sites + self.all_site_ids()))
        add_change(
            action_name="edit-folder",
            text=_l("Edited properties of folder %s") % self.title(),
            user_id=user.id,
            object_ref=self.object_ref(),
            sites=affected_sites,
            diff_text=diff,
            use_git=use_git,
        )

    def prepare_create_hosts(self) -> None:
        user.need_permission("wato.manage_hosts")
        self.need_unlocked_hosts()
        self.permissions.need_permission("write")

    def create_hosts(
        self,
        entries: Iterable[tuple[HostName, HostAttributes, Sequence[HostName] | None]],
        *,
        pprint_value: bool,
        use_git: bool,
    ) -> None:
        """Create many hosts at once.

        Below are the expected Exceptions this function will throw (indirectly). Any other
        Exception is due to an error.

        Raises:
            - MKAuthException: When the user doesn't have the rights to see a (or any) host.
            - MKAuthException: When the user isn't in the contact group specified.
            - MKUserError: When the host is already there.
            - MKGeneralException: When something happened during permission check.

        """
        # 1. Check preconditions
        self.prepare_create_hosts()
        self.validators.validate_create_hosts(entries, self.site_id())

        self.create_validated_hosts(
            [
                (
                    host_name,
                    self.verify_and_update_host_details(
                        host_name,
                        attributes,
                    ),
                    _cluster_nodes,
                )
                for host_name, attributes, _cluster_nodes in entries
            ],
            pprint_value=pprint_value,
            use_git=use_git,
        )

    def create_validated_hosts(
        self,
        entries: Collection[tuple[HostName, HostAttributes, Sequence[HostName] | None]],
        *,
        pprint_value: bool,
        use_git: bool,
    ) -> None:
        # 2. Actual modification
        self._load_hosts_on_demand()
        for host_name, attributes, cluster_nodes in entries:
            self._propagate_hosts_changes(host_name, attributes, cluster_nodes, use_git=use_git)

        self.save(pprint_value=pprint_value)  # num_hosts has changed

        folder_path = self.path()
        folder_lookup_cache().add_hosts([(x[0], folder_path) for x in entries])

    @staticmethod
    def verify_and_update_host_details(
        name: HostName, attributes: HostAttributes
    ) -> HostAttributes:
        # MKAuthException, MKUserError
        _must_be_in_contactgroups(_get_cgconf_from_attributes(attributes)["groups"])
        validate_host_uniqueness("host", name)
        return update_metadata(attributes, created_by=user.id)

    def _propagate_hosts_changes(
        self,
        host_name: HostName,
        attributes: HostAttributes,
        cluster_nodes: Sequence[HostName] | None,
        use_git: bool,
    ) -> None:
        host = Host(self, host_name, attributes, cluster_nodes)
        assert self._hosts is not None
        self._hosts[host_name] = host
        self._num_hosts = len(self._hosts)

        add_change(
            action_name="create-host",
            text=_l("Created new host %s.") % host_name,
            user_id=user.id,
            object_ref=host.object_ref(),
            sites=[host.site_id()],
            diff_text=diff_attributes({}, None, host.attributes, host.cluster_nodes()),
            domains=[config_domain_registry[CORE_DOMAIN]],
            domain_settings=_core_settings_hosts_to_update([host_name]),
            use_git=use_git,
        )

    def user_may_delete_hosts(
        self,
        host_names: Sequence[HostName],
        *,
        allow_locked_deletion: bool = False,
    ) -> None:
        # Check preconditions
        user.need_permission("wato.manage_hosts")
        self.need_unlocked_hosts()
        self.permissions.need_permission("write")

        # Check if hosts can be deleted
        self._validate_delete_hosts(host_names, allow_locked_deletion)

    def delete_hosts(
        self,
        host_names: Sequence[HostName],
        *,
        automation: Callable[
            [LocalAutomationConfig | RemoteAutomationConfig, Sequence[HostName], bool],
            ABCAutomationResult,
        ],
        pprint_value: bool,
        debug: bool,
        use_git: bool,
        allow_locked_deletion: bool = False,
    ) -> None:
        # 1. Check preconditions and whether hosts can be deleted
        self.user_may_delete_hosts(host_names, allow_locked_deletion=allow_locked_deletion)

        # 2. Delete host specific files (caches, tempfiles, ...)
        self._delete_host_files(
            host_names,
            automation=automation,
            debug=debug,
        )

        # 3. Actual modification
        assert self._hosts is not None
        for host_name in host_names:
            host = self.hosts()[host_name]
            del self._hosts[host_name]
            self._num_hosts = len(self._hosts)
            add_change(
                action_name="delete-host",
                text=_l("Deleted host %s") % host_name,
                user_id=user.id,
                object_ref=host.object_ref(),
                sites=[host.site_id()],
                domains=[config_domain_registry[CORE_DOMAIN]],
                domain_settings=_core_settings_hosts_to_update([host.name()]),
                use_git=use_git,
            )

        self.save_folder_attributes()  # num_hosts has changed
        self.save_hosts(pprint_value=pprint_value)
        folder_lookup_cache().delete_hosts(host_names)

    def _validate_delete_hosts(
        self, host_names: Collection[HostName], allow_locked_deletion: bool = False
    ) -> None:
        # 1. check if hosts are locked by quick setup
        errors: list[str] = []
        if not allow_locked_deletion and (
            hosts := self._get_hosts_locked_by_quick_setup(host_names)
        ):
            errors.extend(_("%s is locked by Quick Setup.") % host_name for host_name in hosts)

        # 2. check if hosts have parents
        if hosts_with_children := self._get_parents_of_hosts(self.tree, host_names):
            errors.extend(
                _("%s is parent of %s.") % (parent, ", ".join(children))
                for parent, children in sorted(hosts_with_children.items())
            )

        if errors:
            raise MKUserError(
                "delete_host",
                _("You cannot delete these hosts: %s") % ", ".join(errors),
            )

    @staticmethod
    def _get_hosts_locked_by_quick_setup(
        host_names: Collection[HostName],
    ) -> list[HostName]:
        return [
            host_name
            for host_name in host_names
            if is_locked_by_quick_setup(Host.load_host(host_name).locked_by())
        ]

    @staticmethod
    def _get_parents_of_hosts(
        tree: FolderTree, host_names: Collection[HostName]
    ) -> dict[HostName, list[HostName]]:
        # Note: Deletion of chosen hosts which are parents
        # is possible if and only if all children are chosen, too.
        hosts_with_children: dict[HostName, list[HostName]] = {}
        for child_key, child in tree.root_folder().all_hosts_recursively().items():
            for host_name in host_names:
                if host_name in child.parents():
                    hosts_with_children.setdefault(host_name, [])
                    hosts_with_children[host_name].append(child_key)

        result: dict[HostName, list[HostName]] = {}
        for parent, children in hosts_with_children.items():
            if not set(children) < set(host_names):
                result.setdefault(parent, children)
        return result

    # Group the given host names by their site and delete their files
    def _delete_host_files(
        self,
        host_names: Sequence[HostName],
        *,
        automation: Callable[
            [LocalAutomationConfig | RemoteAutomationConfig, Sequence[HostName], bool],
            ABCAutomationResult,
        ],
        debug: bool,
    ) -> None:
        for site_id, site_host_names in self.get_hosts_by_site(host_names).items():
            automation(
                make_automation_config(active_config.sites[site_id]),
                site_host_names,
                debug,
            )

    def get_hosts_by_site(
        self, host_names: Sequence[HostName]
    ) -> Mapping[SiteId, Sequence[HostName]]:
        hosts_by_site: dict[SiteId, list[HostName]] = {}
        hosts = self.hosts()
        for host_name in host_names:
            host = hosts[host_name]
            hosts_by_site.setdefault(host.site_id(), []).append(host_name)
        return hosts_by_site

    def move_hosts(
        self,
        host_names: Collection[HostName],
        target_folder: Folder,
        *,
        pprint_value: bool,
        use_git: bool,
    ) -> None:
        # 1. Check preconditions
        user.need_permission("wato.manage_hosts")
        user.need_permission("wato.edit_hosts")
        user.need_permission("wato.move_hosts")
        self.permissions.need_permission("write")
        self.need_unlocked_hosts()
        target_folder.permissions.need_permission("write")
        target_folder.need_unlocked_hosts()
        self.validators.validate_move_hosts(self, host_names, target_folder)

        # 2. Actual modification
        for host_name in host_names:
            host = self.load_host(host_name)

            affected_sites = [host.site_id()]

            self._remove_host(host)
            target_folder._add_host(host)

            affected_sites = list(set(affected_sites + [host.site_id()]))
            old_folder_text = self.path() or self.tree.root_folder().title()
            new_folder_text = target_folder.path() or self.tree.root_folder().title()
            add_change(
                action_name="move-host",
                text=_l('Moved host from "%s" (ID: %s) to "%s" (ID: %s)')
                % (
                    old_folder_text,
                    self._id,
                    new_folder_text,
                    target_folder._id,
                ),
                user_id=user.id,
                object_ref=host.object_ref(),
                sites=affected_sites,
                use_git=use_git,
            )

        self.save_folder_attributes()  # num_hosts has changed
        self.save_hosts(pprint_value=pprint_value)

        target_folder.save_folder_attributes()
        target_folder.save_hosts(pprint_value=pprint_value)

        folder_path = target_folder.path()
        folder_lookup_cache().add_hosts([(x, folder_path) for x in host_names])

    def rename_host(
        self, oldname: HostName, newname: HostName, *, pprint_value: bool, use_git: bool
    ) -> None:
        # 1. Check preconditions
        user.need_permission("wato.manage_hosts")
        user.need_permission("wato.edit_hosts")
        self.need_unlocked_hosts()
        host = self.hosts()[oldname]
        host.permissions.need_permission("write")

        if is_locked_by_quick_setup(host.locked_by()):
            raise MKUserError(
                "rename-host",
                _('You cannot rename host "%s", because it is managed by Quick setup.') % oldname,
            )

        # 2. Actual modification
        host.rename(newname, use_git=use_git)
        assert self._hosts is not None
        del self._hosts[oldname]
        self._hosts[newname] = host

        folder_lookup_cache().delete_hosts([oldname])
        folder_lookup_cache().add_hosts([(newname, self.path())])

        self.save_hosts(pprint_value=pprint_value)

    def rename_parent(
        self, oldname: HostName, newname: HostName, *, pprint_value: bool, use_git: bool
    ) -> bool:
        # Must not fail because of auth problems. Auth is check at the
        # actually renamed host.
        new_parents = [str(p) for p in self.attributes["parents"]]
        changed = rename_host_in_list(new_parents, oldname, newname)
        if not changed:
            return False

        self.attributes["parents"] = [HostName(h) for h in new_parents]
        add_change(
            action_name="rename-parent",
            text=_l('Renamed parent from %s to %s in folder "%s"')
            % (oldname, newname, self.alias_path()),
            user_id=user.id,
            object_ref=self.object_ref(),
            sites=self.all_site_ids(),
            use_git=use_git,
        )
        self.save(pprint_value=pprint_value)
        return True

    def recursively_save_hosts(self, pprint_value: bool) -> None:
        self._load_hosts_on_demand()
        self.save_hosts(pprint_value=pprint_value)
        for subfolder in self.subfolders():
            subfolder.recursively_save_hosts(pprint_value=pprint_value)

    def _add_host(self, host: Host) -> None:
        self._load_hosts_on_demand()
        assert self._hosts is not None
        self._hosts[host.name()] = host
        host._folder = self
        self._num_hosts = len(self._hosts)

    def _remove_host(self, host: Host) -> None:
        self._load_hosts_on_demand()
        assert self._hosts is not None
        del self._hosts[host.name()]
        # host._folder = None
        self._num_hosts = len(self._hosts)

    def _add_all_sites_to_set(self, site_ids: set[SiteId]) -> None:
        site_ids.add(self.site_id())
        for host in self.hosts().values():
            site_ids.add(host.site_id())
        for subfolder in self.subfolders():
            subfolder._add_all_sites_to_set(site_ids)

    # .-----------------------------------------------------------------------.
    # | HTML Generation                                                       |
    # '-----------------------------------------------------------------------'

    def show_locking_information(self) -> None:
        self._load_hosts_on_demand()
        lock_messages: list[str] = []

        # Locked hosts
        if self._locked_hosts is True:
            lock_messages.append(
                _(
                    "Host attributes are locked (you cannot create, edit or delete hosts in this folder)"
                )
            )
        elif isinstance(self._locked_hosts, str) and self._locked_hosts:
            lock_messages.append(self._locked_hosts)

        # Locked folder attributes
        if self._locked is True:
            lock_messages.append(
                _("Folder attributes are locked (you cannot edit the attributes of this folder)")
            )
        elif isinstance(self._locked, str) and self._locked:
            lock_messages.append(self._locked)

        # Also subfolders are locked
        if self._locked_subfolders:
            lock_messages.append(
                _("Subfolders are locked (you cannot create or remove folders in this folder)")
            )
        elif isinstance(self._locked_subfolders, str) and self._locked_subfolders:
            lock_messages.append(self._locked_subfolders)

        if lock_messages:
            if len(lock_messages) == 1:
                lock_message = lock_messages[0]
            else:
                li_elements = "".join(["<li>%s</li>" % m for m in lock_messages])
                lock_message = "<ul>" + li_elements + "</ul>"
            html.show_message(lock_message)


def _is_main_folder_path(folder_path: str) -> bool:
    return folder_path == ""


def _fallback_title(folder_path: str) -> str:
    if _is_main_folder_path(folder_path):
        return _("Main")
    return os.path.basename(folder_path)


def _folder_wato_info_path(base_dir: str) -> str:
    return base_dir + "/.wato"


def _folder_filesystem_path(root_dir: str, folder_path: str) -> PathWithoutSlash:
    return (root_dir + folder_path).rstrip("/")


class FolderLookupCache:
    """Helps to find hosts faster in the folder hierarchy"""

    def __init__(self, tree: FolderTree) -> None:
        self._folder_tree = tree

    def _path(self) -> Path:
        return cmk.utils.paths.tmp_dir / "wato/wato_host_folder_lookup.cache"

    def get(self, host_name: HostName) -> Host | None:
        """This function tries to create a host object using its name from a lookup cache.
        If this does not work (cache miss), the regular search for the host is started.
        If the host was found by the regular search, the lookup cache is updated accordingly.
        """

        try:
            cache = self.get_cache()
            folder_hint = cache.get(host_name)
            if folder_hint is not None and self._folder_tree.folder_exists(folder_hint):
                folder_instance = self._folder_tree.folder(folder_hint)
                host_instance = folder_instance.host(host_name)
                if host_instance is not None:
                    return host_instance

            # The hostname was not found in the lookup cache
            # Use find_host_recursively to search this host in the configuration
            host_instance = self._folder_tree.root_folder().find_host_recursively(host_name)
            if not host_instance:
                return None

            # Save newly found host instance to cache
            cache[host_name] = host_instance.folder().path()
            self._save(cache)
            return host_instance
        except RequestTimeout:
            raise
        except Exception:
            logger.warning(
                "Unexpected exception in FolderLookupCache.get. Falling back to recursive host lookup",
                exc_info=True,
            )
            return self._folder_tree.root_folder().find_host_recursively(host_name)

    def get_cache(self) -> dict[HostName, str]:
        if "folder_lookup_cache_dict" not in g:
            cache_path = self._path()
            if not cache_path.exists() or cache_path.stat().st_size == 0:
                self.build()
            try:
                g.folder_lookup_cache_dict = store.load_object_from_pickle_file(
                    cache_path, default={}
                )
            except (TypeError, pickle.UnpicklingError) as e:
                logger.warning("Unable to read folder_lookup_cache from disk: %s", str(e))
                g.folder_lookup_cache_dict = {}
        return g.folder_lookup_cache_dict

    def rebuild_outdated(self, max_age: int) -> None:
        cache_path = self._path()
        if cache_path.exists() and time.time() - cache_path.stat().st_mtime < max_age:
            return

        # Touch the file. The cronjob interval might be faster than the file creation
        # Note: If this takes longer than the RequestTimeout -> Problem
        #       On very big configurations, e.g. 300MB this might take 30-50 seconds
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.touch()
        self.build()

    def build(self) -> None:
        store.acquire_lock(self._path())
        folder_lookup = {}
        for host_name, host in self._folder_tree.root_folder().all_hosts_recursively().items():
            folder_lookup[host_name] = host.folder().path()
        self._save(folder_lookup)

    def _save(self, folder_lookup: Mapping[HostName, str]) -> None:
        store.save_bytes_to_file(self._path(), pickle.dumps(folder_lookup))

    def delete(self) -> None:
        self._path().unlink(missing_ok=True)

    def add_hosts(self, host2path_list: Iterable[tuple[HostName, str]]) -> None:
        cache = self.get_cache()
        for hostname, folder_path in host2path_list:
            cache[hostname] = folder_path
        self._save(cache)

    def delete_hosts(self, hostnames: Iterable[HostName]) -> None:
        cache = self.get_cache()
        for hostname in hostnames:
            try:
                del cache[hostname]
            except KeyError:
                pass
        self._save(cache)


class WATOFoldersOnDemand(Mapping[PathWithoutSlash, Folder]):
    def __init__(self, tree: FolderTree, values: dict[PathWithoutSlash, Folder | None]) -> None:
        self.tree = tree
        self._raw_dict: dict[PathWithoutSlash, Folder | None] = values

    def __getitem__(self, path_without_slash: PathWithoutSlash) -> Folder:
        item: Folder | None = self._raw_dict[path_without_slash]
        if item is None:
            item = self._create_folder(path_without_slash)
            self._raw_dict.__setitem__(path_without_slash, item)
        return item

    def __iter__(self) -> Iterator[PathWithoutSlash]:
        return iter(self._raw_dict)

    def __len__(self) -> int:
        return len(self._raw_dict)

    def _create_folder(self, folder_path: PathWithoutSlash) -> Folder:
        parent_folder = None
        if not _is_main_folder_path(folder_path):
            parent_folder = self[str(Path(folder_path).parent).lstrip(".")]

        return Folder.load(
            tree=self.tree,
            name=os.path.basename(folder_path),
            parent_folder=parent_folder,
        )


def validate_host_uniqueness(varname: str, host_name: HostName) -> None:
    host = Host.host(host_name)
    if host:
        raise MKUserError(
            varname,
            _(
                "A host with the name <b><tt>%s</tt></b> already "
                'exists in the folder <a href="%s">%s</a>.'
            )
            % (host_name, host.folder().url(), host.folder().alias_path()),
        )


def _get_cgconf_from_attributes(attributes: HostAttributes) -> HostContactGroupSpec:
    return attributes.get(
        "contactgroups",
        HostContactGroupSpec(
            groups=[],
            recurse_perms=False,
            use=False,
            use_for_services=False,
            recurse_use=False,
        ),
    )


class SearchFolder(FolderProtocol):
    """A virtual folder representing the result of a search."""

    def __init__(self, tree: FolderTree, base_folder: Folder, criteria: SearchCriteria) -> None:
        super().__init__()
        self.attributes: dict[str, Any] = {"meta_data": {}}
        self.effective_attributes = EffectiveAttributes(lambda: {})
        self.permissions = PermissionChecker(lambda _unused: None)
        self.tree = tree
        self._criteria = criteria
        self._base_folder = base_folder
        self._found_hosts: dict[HostName, Host] | None = None
        self._name = None

    def __repr__(self) -> str:
        return f"SearchFolder({self.tree!r}, {self._base_folder.path()!r}, {self._name})"

    def parent(self) -> Folder:
        return self._base_folder

    def is_disk_folder(self) -> bool:
        return False

    def is_search_folder(self) -> bool:
        return True

    def title(self) -> str:
        return _("Search results for folder %s") % self._base_folder.title()

    def breadcrumb(self) -> Breadcrumb:
        return _folder_breadcrumb(self)

    def hosts(self) -> Mapping[HostName, Host]:
        if self._found_hosts is None:
            self._found_hosts = self._search_hosts_recursively(self._base_folder)
        return self._found_hosts

    def host_validation_errors(self) -> dict[HostName, list[str]]:
        return validate_all_hosts(self.tree, list(self.hosts().keys()))

    def load_host(self, host_name: HostName) -> Host:
        try:
            return self.hosts()[host_name]
        except KeyError:
            raise MKUserError(None, f"The host {host_name} could not be found.")

    def has_host(self, host_name: HostName) -> bool:
        return host_name in self.hosts()

    def has_hosts(self) -> bool:
        return bool(self.hosts())

    def locked_hosts(self) -> bool:
        return False

    def locked_subfolders(self) -> bool:
        return False

    def show_locking_information(self) -> None:
        pass

    def has_subfolder(self, name: str) -> bool:
        return False

    def has_subfolders(self) -> bool:
        return False

    def choices_for_moving_host(self) -> Sequence[tuple[str, str]]:
        return self.tree.folder_choices()

    def path(self) -> str:
        if self._name:
            return self._base_folder.path() + "//search:" + self._name
        return self._base_folder.path() + "//search"

    def url(self, add_vars: HTTPVariables | None = None) -> str:
        if add_vars is None:
            add_vars = []

        url_vars: HTTPVariables = [("host_search", "1"), *add_vars]

        for varname, value in request.itervars():
            if varname.startswith("host_search_") or varname.startswith("_change"):
                url_vars.append((varname, value))
        return self.parent().url(url_vars)

    def delete_hosts(
        self,
        host_names: Sequence[HostName],
        *,
        automation: Callable[
            [LocalAutomationConfig | RemoteAutomationConfig, Sequence[HostName], bool],
            ABCAutomationResult,
        ],
        pprint_value: bool,
        debug: bool,
        use_git: bool,
    ) -> None:
        auth_errors = []
        for folder, these_host_names in self._group_hostnames_by_folder(host_names):
            try:
                folder.delete_hosts(
                    these_host_names,
                    automation=automation,
                    pprint_value=pprint_value,
                    debug=debug,
                    use_git=use_git,
                )
            except MKAuthException as e:
                auth_errors.append(
                    _("<li>Cannot delete hosts in folder %s: %s</li>") % (folder.alias_path(), e)
                )
        self._invalidate_search()
        if auth_errors:
            raise MKAuthException(
                _("Some hosts could not be deleted:<ul>%s</ul>") % "".join(auth_errors)
            )

    def move_hosts(
        self,
        host_names: Sequence[HostName],
        target_folder: Folder,
        *,
        pprint_value: bool,
        use_git: bool,
    ) -> None:
        auth_errors = []
        for folder, host_names1 in self._group_hostnames_by_folder(host_names):
            try:
                # FIXME: this is not transaction safe, might get partially finished...
                folder.move_hosts(
                    host_names1, target_folder, pprint_value=pprint_value, use_git=use_git
                )
            except MKAuthException as e:
                auth_errors.append(
                    _("<li>Cannot move hosts from folder %s: %s</li>") % (folder.alias_path(), e)
                )
        self._invalidate_search()
        if auth_errors:
            raise MKAuthException(
                _("Some hosts could not be moved:<ul>%s</ul>") % "".join(auth_errors)
            )

    def _group_hostnames_by_folder(
        self, host_names: Sequence[HostName]
    ) -> list[tuple[Folder, list[HostName]]]:
        by_folder: dict[str, list[Host]] = {}
        for host_name in host_names:
            host = self.load_host(host_name)
            by_folder.setdefault(host.folder().path(), []).append(host)

        return [
            (hosts[0].folder(), [_host.name() for _host in hosts]) for hosts in by_folder.values()
        ]

    def _search_hosts_recursively(self, in_folder: Folder) -> dict[HostName, Host]:
        hosts = self._search_hosts(in_folder)
        for subfolder in in_folder.subfolders():
            hosts.update(self._search_hosts_recursively(subfolder))
        return hosts

    def _search_hosts(self, in_folder: Folder) -> dict[HostName, Host]:
        if not in_folder.permissions.may("read"):
            return {}

        found = {}
        host_attributes = self.tree.all_host_attributes()
        for host_name, host in in_folder.hosts().items():
            if self._criteria[".name"] and not host_attribute_matches(
                self._criteria[".name"], host_name
            ):
                continue

            # Compute inheritance
            effective = host.effective_attributes()

            # Check attributes
            dont_match = False
            for attrname, attr in host_attributes.items():
                if attrname in self._criteria and not attr.filter_matches(
                    self._criteria[attrname], effective.get(attrname), host_name
                ):
                    dont_match = True
                    break

            if not dont_match:
                found[host_name] = host

        return found

    def _invalidate_search(self) -> None:
        self._found_hosts = None


def parent_folder_chain(origin: SearchFolder | Folder) -> list[Folder]:
    folders = []
    folder = origin.parent()
    while folder:
        folders.append(folder)
        folder = folder.parent()
    return folders[::-1]


class Host:
    """Class representing one host that is managed via Setup. Hosts are contained in Folders."""

    # .--------------------------------------------------------------------.
    # | STATIC METHODS                                                     |
    # '--------------------------------------------------------------------'

    @staticmethod
    def load_host(host_name: HostName) -> Host:
        host = Host.host(host_name)
        if host is None:
            raise MKUserError(None, "Host could not be found.", status=404)
        return host

    @staticmethod
    def host(host_name: HostName) -> Host | None:
        return folder_lookup_cache().get(host_name)

    @staticmethod
    def all() -> dict[HostName, Host]:
        return folder_tree().root_folder().all_hosts_recursively()

    @staticmethod
    def host_exists(host_name: HostName) -> bool:
        return Host.host(host_name) is not None

    # .--------------------------------------------------------------------.
    # | CONSTRUCTION, LOADING & SAVING                                     |
    # '--------------------------------------------------------------------'

    def __init__(
        self,
        folder: Folder,
        host_name: HostName,
        attributes: HostAttributes,
        cluster_nodes: Sequence[HostName] | None,
    ) -> None:
        super().__init__()
        self.effective_attributes = EffectiveAttributes(self._compute_effective_attributes)
        self.permissions = PermissionChecker(self._user_needs_permission)
        self._folder = folder
        self._name = host_name
        self.attributes = attributes
        self._cluster_nodes = cluster_nodes
        self._cached_host_tags: None | dict[TagGroupID, TagID] = None

    def __repr__(self) -> str:
        return "Host(%r)" % (self._name)

    def drop_caches(self) -> None:
        self.effective_attributes.drop_caches()
        self._cached_host_tags = None

    # .--------------------------------------------------------------------.
    # | ELEMENT ACCESS                                                     |
    # '--------------------------------------------------------------------'

    def id(self) -> HostName:
        return self.name()

    def ident(self) -> str:
        return self.name()

    def name(self) -> HostName:
        return self._name

    def alias(self) -> str | None:
        # Alias cannot be inherited, so no need to use effective_attributes()
        return self.attributes.get("alias")

    def folder(self) -> Folder:
        return self._folder

    def object_ref(self) -> ObjectRef:
        return ObjectRef(ObjectRefType.Host, self.name())

    def locked(self) -> bool | str:
        return self.folder().locked_hosts()

    def need_unlocked(self) -> None:
        self.folder().need_unlocked_hosts()

    def is_cluster(self) -> bool:
        return self._cluster_nodes is not None

    def cluster_nodes(self) -> Sequence[HostName] | None:
        return self._cluster_nodes

    def is_offline(self) -> bool:
        return self.tag(TagGroupID("criticality")) == "offline"

    def site_id(self) -> SiteId:
        return self.attributes.get("site") or self.folder().site_id()

    def parents(self) -> Sequence[HostName]:
        return self.effective_attributes().get("parents", [])

    def locked_by(self) -> GlobalIdent | None:
        # locked_by cannot be inherited, so no need to use effective_attributes()
        locked = self.attributes.get("locked_by")
        if locked and len(locked) == 3:
            # convert list/tuple to dict structure
            return GlobalIdent(
                site_id=locked[0],
                program_id=locked[1],
                instance_id=locked[2],
            )
        return None

    def tag_groups(self) -> Mapping[TagGroupID, TagID]:
        """Compute tags from host attributes
        Each tag attribute may set multiple tags.  can set tags (e.g. the SiteAttribute)
        """

        if self._cached_host_tags is not None:
            return self._cached_host_tags  # Cached :-)

        tag_groups: dict[TagGroupID, TagID] = {}
        effective = self.effective_attributes()
        for attr in self._folder.tree.all_host_attributes().values():
            value = effective.get(attr.name())
            tag_groups.update(attr.get_tag_groups(value))

        # When a host as been configured not to use the agent and not to use
        # SNMP, it needs to get the ping tag assigned.
        # Because we need information from multiple attributes to get this
        # information, we need to add this decision here.
        # Skip this in case no-ip is configured: A ping check is useless in this case
        if (
            tag_groups[TagGroupID("snmp_ds")] == TagID("no-snmp")
            and tag_groups[TagGroupID("agent")] == TagID("no-agent")
            and tag_groups[TagGroupID("address_family")] != TagID("no-ip")
        ):
            tag_groups[TagGroupID("ping")] = TagID("ping")

        self._cached_host_tags = tag_groups
        return tag_groups

    # TODO: Can we remove this?
    def tags(self) -> set[TagID]:
        # The pre 1.6 tags contained only the tag group values (-> chosen tag id),
        # but there was a single tag group added with it's leading tag group id. This
        # was the internal "site" tag that is created by HostAttributeSite.
        tags = {v for k, v in self.tag_groups().items() if k != TagGroupID("site")}
        tags.add(TagID("site:%s" % self.tag_groups()[TagGroupID("site")]))
        return tags

    def is_ping_host(self) -> bool:
        return self.tag_groups().get(TagGroupID("ping")) == TagID("ping")

    def tag(self, taggroup_name: TagGroupID) -> TagID | None:
        effective = self.effective_attributes()
        attribute_name = "tag_" + taggroup_name
        value = effective.get(attribute_name)
        if isinstance(value, str):
            return TagID(value)
        return None

    def discovery_failed(self) -> bool:
        return self.attributes.get("inventory_failed", False)

    def is_waiting_for_discovery(self) -> bool:
        return self.attributes.get("waiting_for_discovery", False)

    def validation_errors(self) -> list[str]:
        if hooks.registered("validate-host"):
            errors = []
            for hook in hooks.get("validate-host"):
                try:
                    hook.handler(self)
                except MKUserError as e:
                    errors.append("%s" % e)
            return errors
        return []

    def _compute_effective_attributes(self) -> HostAttributes:
        effective = self.folder().effective_attributes()
        effective.update(self.attributes)
        effective["labels"] = self.labels()
        return effective

    def labels(self) -> Labels:
        """Returns the aggregated labels for the current host

        The labels of all parent folders and the host are added together. When multiple
        objects define the same tag group, the nearest to the host wins."""
        labels: dict[str, str] = {}

        all_attributes = self._folder.tree.all_host_attributes()

        def set_attribute_labels(
            labels: dict[str, str],
            object_attributes: HostAttributes,
            all_attributes: Mapping[str, ABCHostAttribute],
        ) -> None:
            for name, value in object_attributes.items():
                attr = all_attributes.get(name)
                if attr and (attr_labels := attr.labels(value)):
                    labels.update(attr_labels)

        for obj in parent_folder_chain(self.folder()) + [self.folder()]:
            labels.update(obj.attributes.get("labels", {}).items())
            set_attribute_labels(labels, obj.attributes, all_attributes)

        labels.update(self.attributes.get("labels", {}).items())
        set_attribute_labels(labels, self.attributes, all_attributes)

        return labels

    def groups(self) -> tuple[set[_ContactgroupName], set[_ContactgroupName], bool]:
        return self.folder().groups(self)

    def _user_needs_permission(self, how: Literal["read", "write"]) -> None:
        if how == "write" and user.may("wato.all_folders"):
            return

        if how == "read" and user.may("wato.see_all_folders"):
            return

        if how == "write":
            user.need_permission("wato.edit_hosts")

        if self.is_contact(user):
            return

        if len(self.groups()[0]) > 0:
            group_sentence = _(
                "To get access, ensure your user is in a contact "
                "group specified in the host's permissions: <b>%s</b>."
            ) % ", ".join(self.groups()[0])
        else:
            group_sentence = _(
                "Access is restricted, but no contact groups are assigned in the host's permissions."
            )

        raise MKAuthException(
            _("You cannot edit the configuration for host '<b>%s</b>'. %s")
            % (self.name(), group_sentence)
        )

    def is_contact(self, user_: LoggedInUser) -> bool:
        permitted_groups, _host_contact_groups, _use_for_services = self.groups()
        return any(group in permitted_groups for group in user_.contact_groups)

    def edit_url(self) -> str:
        return urls.makeuri_contextless(
            request,
            [
                ("mode", "edit_host"),
                ("folder", self.folder().path()),
                ("host", self.name()),
            ],
            filename="wato.py",
        )

    def params_url(self) -> str:
        return urls.makeuri_contextless(
            request,
            [
                ("mode", "object_parameters"),
                ("folder", self.folder().path()),
                ("host", self.name()),
            ],
            filename="wato.py",
        )

    def services_url(self) -> str:
        return urls.makeuri_contextless(
            request,
            [
                ("mode", "inventory"),
                ("folder", self.folder().path()),
                ("host", self.name()),
            ],
            filename="wato.py",
        )

    def clone_url(self) -> str:
        return urls.makeuri_contextless(
            request,
            [
                ("mode", "newcluster" if self.is_cluster() else "newhost"),
                ("folder", self.folder().path()),
                ("clone", self.name()),
            ],
            filename="wato.py",
        )

    # .--------------------------------------------------------------------.
    # | MODIFICATIONS                                                      |
    # |                                                                    |
    # | These methods are for being called by actual Setup modules when they|
    # | want to modify hosts. See details at the comment header in Folder. |
    # '--------------------------------------------------------------------'

    def apply_edit(
        self, attributes: HostAttributes, cluster_nodes: Sequence[HostName] | None
    ) -> tuple[str, list[SiteId]]:
        """Apply the changes to the host. This method does not save the changes to file!"""
        # 1. Check preconditions
        if attributes.get("contactgroups") != self.attributes.get("contactgroups"):
            self._need_folder_write_permissions()
        self.permissions.need_permission("write")
        self.need_unlocked()

        folder = self.folder()
        folder.validators.validate_edit_host(folder.site_id(), self.name(), attributes)
        _validate_contact_group_modification(
            _get_cgconf_from_attributes(self.attributes)["groups"],
            _get_cgconf_from_attributes(attributes)["groups"],
        )

        diff = diff_attributes(self.attributes, self._cluster_nodes, attributes, cluster_nodes)

        # 2. Actual modification
        affected_sites = [self.site_id()]
        self.attributes = attributes
        self._cluster_nodes = cluster_nodes
        affected_sites = list(set(affected_sites + [self.site_id()]))

        return diff, affected_sites

    def add_edit_host_change(
        self, diff: str, affected_sites: list[SiteId], *, use_git: bool
    ) -> None:
        add_change(
            action_name="edit-host",
            text=_l("Modified host %s.") % self.name(),
            user_id=user.id,
            object_ref=self.object_ref(),
            sites=affected_sites,
            diff_text=diff,
            domains=[config_domain_registry[CORE_DOMAIN]],
            domain_settings=_core_settings_hosts_to_update([self.name()]),
            use_git=use_git,
        )

    def edit(
        self,
        attributes: HostAttributes,
        cluster_nodes: Sequence[HostName] | None,
        *,
        pprint_value: bool,
        use_git: bool,
    ) -> None:
        diff, affected_sites = self.apply_edit(attributes, cluster_nodes)
        self.folder().save_hosts(pprint_value=pprint_value)
        self.add_edit_host_change(diff, affected_sites, use_git=use_git)

    def update_attributes(
        self, changed_attributes: HostAttributes, *, pprint_value: bool, use_git: bool
    ) -> None:
        new_attributes = self.attributes.copy()
        new_attributes.update(changed_attributes)
        self.edit(new_attributes, self._cluster_nodes, pprint_value=pprint_value, use_git=use_git)

    def clean_attributes(
        self,
        attrnames_to_clean: Sequence[str],
        *,
        pprint_value: bool,
        use_git: bool,
    ) -> None:
        # 1. Check preconditions
        if "contactgroups" in attrnames_to_clean:
            self._need_folder_write_permissions()
        self.need_unlocked()

        old_attrs = self.attributes.copy()
        old_nodes = self._cluster_nodes

        # 2. Actual modification
        affected_sites = [self.site_id()]
        for attrname in attrnames_to_clean:
            if attrname in self.attributes:
                # Mypy can not help here with the dynamic key access
                del self.attributes[attrname]  # type: ignore[misc]
        affected_sites = list(set(affected_sites + [self.site_id()]))
        self.folder().save_hosts(pprint_value=pprint_value)

        add_change(
            action_name="edit-host",
            text=_l("Removed explicit attributes of host %s.") % self.name(),
            user_id=user.id,
            object_ref=self.object_ref(),
            sites=affected_sites,
            diff_text=diff_attributes(old_attrs, old_nodes, self.attributes, self._cluster_nodes),
            domains=[config_domain_registry[CORE_DOMAIN]],
            domain_settings=_core_settings_hosts_to_update([self.name()]),
            use_git=use_git,
        )

    def _need_folder_write_permissions(self) -> None:
        if not self.folder().permissions.may("write"):
            raise MKAuthException(
                _(
                    "Sorry. In order to change the permissions of a host you need write "
                    "access to the folder it is contained in."
                )
            )

    def clear_discovery_failed(self, *, pprint_value: bool) -> None:
        # 1. Check preconditions
        # We do not check permissions. They are checked during the discovery.
        self.need_unlocked()

        # 2. Actual modification
        self.set_discovery_failed(False, pprint_value=pprint_value)

    def set_discovery_failed(self, how: bool = True, *, pprint_value: bool) -> None:
        # 1. Check preconditions
        # We do not check permissions. They are checked during the discovery.
        self.need_unlocked()

        # 2. Actual modification
        if how:
            if not self.attributes.get("inventory_failed"):
                self.attributes["inventory_failed"] = True
                self.folder().save_hosts(pprint_value=pprint_value)
        elif self.attributes.get("inventory_failed"):
            del self.attributes["inventory_failed"]
            self.folder().save_hosts(pprint_value=pprint_value)

    def rename_cluster_node(
        self, oldname: HostName, newname: HostName, *, pprint_value: bool, use_git: bool
    ) -> bool:
        # We must not check permissions here. Permissions
        # on the renamed host must be sufficient. If we would
        # fail here we would leave an inconsistent state
        if self._cluster_nodes is None:
            return False

        new_cluster_nodes = [str(e) for e in self._cluster_nodes]
        changed = rename_host_in_list(new_cluster_nodes, oldname, newname)
        if not changed:
            return False

        self._cluster_nodes = [HostName(h) for h in new_cluster_nodes]
        add_change(
            action_name="rename-node",
            text=_l("Renamed cluster node from %s into %s.") % (oldname, newname),
            user_id=user.id,
            object_ref=self.object_ref(),
            sites=[self.site_id()],
            use_git=use_git,
        )
        self.folder().save_hosts(pprint_value=pprint_value)
        return True

    def rename_parent(
        self, oldname: HostName, newname: HostName, *, pprint_value: bool, use_git: bool
    ) -> bool:
        # Same is with rename_cluster_node()
        new_parents = [str(e) for e in self.attributes["parents"]]
        changed = rename_host_in_list(new_parents, oldname, newname)
        if not changed:
            return False

        self.attributes["parents"] = [HostName(h) for h in new_parents]
        add_change(
            action_name="rename-parent",
            text=_l("Renamed parent from %s into %s.") % (oldname, newname),
            user_id=user.id,
            object_ref=self.object_ref(),
            sites=[self.site_id()],
            use_git=use_git,
        )
        self.folder().save_hosts(pprint_value=pprint_value)
        return True

    def rename(self, new_name: HostName, *, use_git: bool) -> None:
        add_change(
            action_name="rename-host",
            text=_l("Renamed host from %s into %s.") % (self.name(), new_name),
            user_id=user.id,
            object_ref=self.object_ref(),
            sites=[self.site_id(), omd_site()],
            prevent_discard_changes=True,
            use_git=use_git,
        )
        self._name = new_name


def diff_attributes(
    left_attributes: Mapping[str, object],
    left_cluster_nodes: Sequence[HostName] | None,
    right_attributes: Mapping[str, object],
    right_cluster_nodes: Sequence[HostName] | None,
) -> str:
    """Diff two sets of host attributes, masking secrets"""
    # The diff has no type infomation, so in order to detect secrets, we have to mask them before
    # diffing. However, all masked secrets look the same in the diff, so then we couldn't detect
    # the changes anymore.
    # To add them manually, see if masking changes the diff. If so, secrets must have changed.
    (left_attributes := dict(left_attributes)).pop("meta_data", None)
    if left_cluster_nodes:
        left_attributes["nodes"] = left_cluster_nodes
    (right_attributes := dict(right_attributes)).pop("meta_data", None)
    if right_cluster_nodes:
        right_attributes["nodes"] = right_cluster_nodes

    unmasked_diff = make_diff(left_attributes, right_attributes)
    masked_diff = make_diff(
        left_masked := mask_attributes(left_attributes),
        right_masked := mask_attributes(right_attributes),
    )

    if unmasked_diff == masked_diff:
        # no special treatment needed
        return make_diff_text(left_masked, right_masked)

    return (masked_diff + "\n" if masked_diff else "") + _("Redacted secrets changed.")


def _validate_contact_group_modification(
    old_groups: Sequence[_ContactgroupName], new_groups: Sequence[_ContactgroupName]
) -> None:
    """Verifies if a user is allowed to modify the contact groups.

    A user must not be member of all groups assigned to a host/folder, but a user can only add or
    remove the contact groups if he is a member of.

    This is necessary to provide the user a consistent experience: In case he is able to add a
    group, he should also be able to remove it. And vice versa.
    """
    if diff_groups := set(old_groups) ^ set(new_groups):
        _must_be_in_contactgroups(diff_groups)


def _must_be_in_contactgroups(cgs: Collection[_ContactgroupName]) -> None:
    """Make sure that the user is in all of cgs contact groups

    This is needed when the user assigns contact groups to
    objects. He may only assign such groups he is member himself.
    """
    if user.may("wato.all_folders"):
        return

    if not cgs:
        return  # No contact groups specified

    users = userdb.load_users()
    if user.id not in users:
        user_cgs = []
    else:
        user_cgs = users[user.id]["contactgroups"]
    for c in cgs:
        if c not in user_cgs:
            raise MKAuthException(
                _(
                    "Sorry, you cannot assign the contact group '<b>%s</b>' "
                    "because you are not member in that group. Your groups are: <b>%s</b>"
                )
                % (c, ", ".join(user_cgs))
            )


def call_hook_hosts_changed(folder: Folder) -> None:
    if hooks.registered("hosts-changed"):
        hosts = _collect_hosts(folder)
        hooks.call("hosts-changed", hosts)

    # The same with all hosts!
    if hooks.registered("all-hosts-changed"):
        hosts = _collect_hosts(folder.tree.root_folder())
        hooks.call("all-hosts-changed", hosts)


# This hook is called in order to determine the errors of the given
# hostnames. These informations are used for displaying warning
# symbols in the host list and the host detail view
# Returns dictionary { hostname: [errors] }
def validate_all_hosts(
    tree: FolderTree, hostnames: Sequence[HostName], force_all: bool = False
) -> dict[HostName, list[str]]:
    if hooks.registered("validate-all-hosts") and (len(hostnames) > 0 or force_all):
        hosts_errors: dict[HostName, list[str]] = {}
        all_hosts = _collect_hosts(tree.root_folder())

        if force_all:
            hostnames = list(all_hosts.keys())

        for name in hostnames:
            eff = all_hosts[name]
            errors = []
            for hook in hooks.get("validate-all-hosts"):
                try:
                    hook.handler(eff, all_hosts)
                except MKUserError as e:
                    errors.append("%s" % e)
            hosts_errors[name] = errors
        return hosts_errors
    return {}


def collect_all_hosts() -> Mapping[HostName, CollectedHostAttributes]:
    return _collect_hosts(folder_tree().root_folder())


def _collect_hosts(folder: Folder) -> Mapping[HostName, CollectedHostAttributes]:
    hosts_attributes = {}
    for host_name, host in folder.all_hosts_recursively().items():
        # Mypy can currently not help here (we have dynamic attributes, so we can not map
        # explicitly). Would need something more powerful than typed dicts to clean this up.
        hosts_attributes[host_name] = CollectedHostAttributes(host.effective_attributes())  # type: ignore[misc]
        hosts_attributes[host_name]["path"] = host.folder().path()
        hosts_attributes[host_name]["edit_url"] = host.edit_url()
    return hosts_attributes


def folder_preserving_link(add_vars: HTTPVariables) -> str:
    return folder_from_request(request.var("folder"), request.get_ascii_input("host")).url(add_vars)


def make_action_link(vars_: HTTPVariables) -> str:
    session_vars: HTTPVariables = [("_transid", transactions.get())]
    if session and hasattr(session, "session_info"):
        session_vars.append(("_csrf_token", session.session_info.csrf_token))

    return folder_preserving_link(vars_ + session_vars)


@request_memoize()
def get_folder_title_path(path: PathWithoutSlash) -> list[str]:
    """Return a list with all the titles of the paths'
    components, e.g. "muc/north" -> [ "Main", "Munich", "North" ]"""
    return folder_tree().folder(path).title_path()


@request_memoize()
def get_folder_title_path_with_links(path: PathWithoutSlash) -> list[HTML]:
    return folder_tree().folder(path).title_path_with_links()


def get_folder_title(path: str) -> str:
    """Return the title of a folder - which is given as a string path"""
    return folder_tree().folder(path).title()


# TODO: Move to Folder()?
def check_wato_foldername(htmlvarname: str | None, name: str, just_name: bool = False) -> None:
    if not just_name and folder_from_request(
        request.var("folder"), request.get_ascii_input("host")
    ).has_subfolder(name):
        raise MKUserError(htmlvarname, _("A folder with that name already exists."))

    if not name:
        raise MKUserError(htmlvarname, _("Please specify a name."))

    if not regex(WATO_FOLDER_PATH_NAME_REGEX).match(name):
        raise MKUserError(
            htmlvarname,
            _("Invalid folder name. Only the characters a-z, A-Z, 0-9, _ and - are allowed."),
        )


def _ensure_trailing_slash(path: str) -> PathWithSlash:
    """Ensure one single trailing slash on a pathname.

    Examples:
        >>> _ensure_trailing_slash('/foo/bar')
        '/foo/bar/'

        >>> _ensure_trailing_slash('/foo/bar/')
        '/foo/bar/'

        >>> _ensure_trailing_slash('/foo/bar//')
        '/foo/bar/'

    Args:
        path: A pathname

    Returns:
        A pathname with a single trailing slash

    """
    return path.rstrip("/") + "/"


def rebuild_folder_lookup_cache(config: Config) -> None:
    """Rebuild folder lookup cache around ~5AM
    This needs to be done, since the cachefile might include outdated/vanished hosts"""

    localtime = time.localtime()
    if not (localtime.tm_hour == 5 and localtime.tm_min < 5):
        return

    folder_lookup_cache().rebuild_outdated(max_age=300)


def ajax_popup_host_action_menu(ctx: PageContext) -> None:
    hostname = request.get_validated_type_input_mandatory(HostName, "hostname")
    host = Host.host(hostname)
    if host is None:
        html.show_error(_('"%s" is not a valid host name') % hostname)
        return

    # Clone host
    if request.get_str_input("show_clone_link"):
        html.open_a(href=host.clone_url())
        html.static_icon(StaticIcon(IconNames.insert))
        html.write_text_permissive(_("Clone host"))
        html.close_a()

    form_name: str = "hosts"

    # Detect network parents
    if request.get_str_input("show_parentscan_link"):
        html.open_a(
            href=None,
            onclick="cmk.selection.execute_bulk_action_for_single_host(this, cmk.page_menu.form_submit, %s);"
            % json.dumps([form_name, "_parentscan"]),
        )
        html.static_icon(StaticIcon(IconNames.parentscan))
        html.write_text_permissive(_("Detect network parents"))
        html.close_a()

    # Remove TLS registration
    if request.get_str_input("show_remove_tls_link"):
        remove_tls_options: dict[str, str | dict[str, str]] = confirmed_form_submit_options(
            title=_('Remove TLS registration of host "%s"') % hostname,
            message=remove_tls_registration_help(),
            confirm_text=_("Remove"),
            warning=True,
        )
        html.open_a(
            href=None,
            onclick="cmk.selection.execute_bulk_action_for_single_host(this, cmk.page_menu.confirmed_form_submit, %s); cmk.popup_menu.close_popup()"
            % json.dumps(
                [
                    form_name,
                    "_remove_tls_registration_from_selection",
                    remove_tls_options,
                ]
            ),
        )
        html.static_icon(StaticIcon(IconNames.tls, emblem="remove"))
        html.write_text_permissive(_("Remove TLS registration"))
        html.close_a()


def find_usages_of_contact_group_in_hosts_and_folders(
    name: GroupName, _settings: GlobalSettings, folder: Folder | None = None
) -> list[tuple[str, str]]:
    if folder is None:
        folder = folder_tree().root_folder()
    used_in = []
    for subfolder in folder.subfolders():
        used_in += find_usages_of_contact_group_in_hosts_and_folders(name, _settings, subfolder)

    if name in folder.attributes.get("contactgroups", {}).get("groups", []):
        used_in.append((_("Folder: %s") % folder.alias_path(), folder.edit_url()))

    for host in folder.hosts().values():
        if name in host.attributes.get("contactgroups", {}).get("groups", []):
            used_in.append((_("Host: %s") % host.name(), host.edit_url()))

    return used_in


@dataclass(frozen=True)
class FolderSiteStats:
    hosts: dict[SiteId, set[Host]]
    folders: dict[SiteId, set[Folder]]

    @classmethod
    def build(cls, root: Folder) -> Self:
        hosts: dict[SiteId, set[Host]] = defaultdict(set)
        folders: dict[SiteId, set[Folder]] = defaultdict(set)
        cls._walk_folder_tree(root, hosts, folders)
        return cls(hosts, folders)

    @staticmethod
    def _walk_folder_tree(
        folder: Folder, hosts: dict[SiteId, set[Host]], folders: dict[SiteId, set[Folder]]
    ) -> None:
        folders[folder.site_id()].add(folder)
        for host in folder.hosts().values():
            hosts[host.site_id()].add(host)
        for subfolder in folder.subfolders():
            FolderSiteStats._walk_folder_tree(subfolder, hosts, folders)


@dataclass(frozen=True)
class FolderValidators:
    ident: str
    validate_edit_host: Callable[[SiteId, HostName, HostAttributes], None]
    validate_create_hosts: Callable[
        [Iterable[tuple[HostName, HostAttributes, Sequence[HostName] | None]], SiteId],
        None,
    ]
    validate_create_subfolder: Callable[[Folder, HostAttributes], None]
    validate_edit_folder: Callable[[Folder, HostAttributes], None]
    validate_move_hosts: Callable[[Folder, Iterable[HostName], Folder], None]
    validate_move_subfolder_to: Callable[[Folder, Folder], None]


class FolderValidatorsRegistry(Registry[FolderValidators]):
    def plugin_name(self, instance: FolderValidators) -> str:
        return instance.ident


folder_validators_registry = FolderValidatorsRegistry()


def strip_hostname_whitespace_chars(host: str) -> str:
    return host.strip(" \n\t\r")
