#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import errno
import operator
import os
import pickle
import shutil
import subprocess
import time
import uuid
from collections.abc import Mapping as ABCMapping
from contextlib import contextmanager, suppress
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Final,
    Iterable,
    Iterator,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypedDict,
    Union,
)

import psutil  # type: ignore[import]

from livestatus import SiteId

import cmk.utils.paths
import cmk.utils.version as cmk_version
from cmk.utils import store
from cmk.utils.iterables import first
from cmk.utils.memoize import MemoizeCache
from cmk.utils.redis import get_redis_client, Pipeline
from cmk.utils.regex import regex, WATO_FOLDER_PATH_NAME_CHARS, WATO_FOLDER_PATH_NAME_REGEX
from cmk.utils.site import omd_site
from cmk.utils.store import PickleSerializer
from cmk.utils.store.host_storage import (
    ABCHostsStorage,
    apply_hosts_file_to_object,
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
from cmk.utils.type_defs import ContactgroupName, HostName, TaggroupID, TaggroupIDToTagID, TagID

import cmk.gui.hooks as hooks
import cmk.gui.userdb as userdb
import cmk.gui.utils.escaping as escaping
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.exceptions import MKAuthException, MKGeneralException, MKUserError, RequestTimeout
from cmk.gui.globals import config, g, html, request, transactions, user
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.sites import allsites, is_wato_slave_site
from cmk.gui.type_defs import HTTPVariables, SetOnceDict
from cmk.gui.utils import urls
from cmk.gui.valuespec import Choices
from cmk.gui.watolib.changes import add_change, make_diff_text, ObjectRef, ObjectRefType
from cmk.gui.watolib.check_mk_automations import delete_hosts
from cmk.gui.watolib.config_domains import ConfigDomainCore
from cmk.gui.watolib.host_attributes import collect_attributes, host_attribute_registry
from cmk.gui.watolib.search import (
    ABCMatchItemGenerator,
    match_item_generator_registry,
    MatchItem,
    MatchItems,
)
from cmk.gui.watolib.sidebar_reload import need_sidebar_reload
from cmk.gui.watolib.utils import (
    convert_cgroups_from_tuple,
    get_value_formatter,
    host_attribute_matches,
    HostContactGroupSpec,
    rename_host_in_list,
    try_bake_agents_for_hosts,
    wato_root_dir,
)

if cmk_version.is_managed_edition():
    import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module

HostAttributes = Mapping[str, Any]
HostsWithAttributes = Mapping[HostName, HostAttributes]
AttributeType = Tuple[str, str, Dict[str, Any], str]  # host attr, cmk.base var name, value, title


class FolderMetaData:
    """Stores meta information for one CREFolder.
    Usually this class is instantiated with data from Redis"""

    def __init__(
        self,
        path: PathWithSlash,
        title: str,
        title_path_without_root: str,
        permitted_contact_groups: List[ContactgroupName],
    ):
        self._path: Final = path
        self._title: Final = title
        self._title_path_without_root: Final[str] = title_path_without_root
        self._permitted_groups: Final[List[ContactgroupName]] = permitted_contact_groups
        self._num_hosts_recursively: Optional[int] = None

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
    def path_titles(self) -> List[str]:
        return self._path.split("/")

    @property
    def permitted_groups(self) -> List[ContactgroupName]:
        return self._permitted_groups

    @property
    def num_hosts_recursively(self) -> int:
        if self._num_hosts_recursively is None:
            if may_use_redis():
                self._num_hosts_recursively = get_wato_redis_client().num_hosts_recursively_lua(
                    self._path
                )
            else:
                self._num_hosts_recursively = Folder.folder(
                    self._path.rstrip("/")
                ).num_hosts_recursively()
        return self._num_hosts_recursively


# Names:
# folder_path: Path of the folders directory relative to etc/check_mk/conf.d/wato
#              The root folder is "". No trailing / is allowed here.
# wato_info:   The dictionary that is saved in the folder's .wato file

# Terms:
# create, delete   mean actual filesystem operations
# add, remove      mean just modifications in the data structures


class WithPermissions:
    def may(self, how: str) -> bool:  # how is "read" or "write"
        try:
            self._user_needs_permission(how)
            return True
        except MKAuthException:
            return False

    def reason_why_may_not(self, how: str) -> Optional[str]:
        try:
            self._user_needs_permission(how)
            return None
        except MKAuthException as e:
            return str(e)

    def need_permission(self, how: str) -> None:
        self._user_needs_permission(how)

    def _user_needs_permission(self, how: str) -> None:
        raise NotImplementedError()


class _ContactGroupsInfo(NamedTuple):
    actual_groups: Set[ContactgroupName]
    configured_groups: Optional[List[ContactgroupName]]
    apply_to_subfolders: bool


PathWithSlash = str
PathWithoutSlash = str
PermittedGroupsOfFolder = Mapping[PathWithoutSlash, _ContactGroupsInfo]


def _get_permitted_groups_of_all_folders(
    all_folders: Mapping[PathWithoutSlash, CREFolder]
) -> PermittedGroupsOfFolder:
    def _compute_tokens(folder_path: PathWithoutSlash) -> Tuple[PathWithoutSlash, ...]:
        """Create tokens for each folder. The main folder requires some special treatment
        since it is not '/' but just an empty string"""
        if folder_path == "":
            # Main folder
            return (folder_path,)
        # Some subfolder, prefix root dir
        return tuple([""] + folder_path.split("/"))

    tokenized_folders = sorted(_compute_tokens(x) for x in all_folders.keys())
    effective_groups_per_folder: Dict[Tuple[str, ...], _ContactGroupsInfo] = {}

    for tokens in tokenized_folders:
        # Compute the groups we get from the parent folders
        # Either directly inherited (nearest parent wins) or enforce inherited through recurse_perms
        parents_all_subfolder_groups: Set[ContactgroupName] = set()
        parents_nearest_configured: Optional[List[ContactgroupName]] = None
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

        if contactgroups := all_folders["/".join(tokens[1:])].attributes().get("contactgroups"):
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
    - computes the metadata out of CREFolder instances and stores it in redis
    - provides functions to compute the number of hosts and fetch the metadata for folders"""

    def __init__(self):
        self._client = get_redis_client()
        self._folder_metadata = {}

        self._loaded_wato_folders: Optional[Mapping[PathWithoutSlash, CREFolder]] = None
        self._folder_paths: Optional[Tuple[PathWithSlash, ...]] = None

        if self._cache_integrity_ok():
            return

        # Store the fully loaded WATO folders. Maybe some process needs them later on
        latest_timestamp, wato_folders = self._get_latest_timestamp_and_folders()
        self._loaded_wato_folders = wato_folders
        self._folder_paths = tuple(f"{path}/" for path in self._loaded_wato_folders)
        self._create_cache_from_scratch(latest_timestamp, self._loaded_wato_folders)

    def _get_latest_timestamp_and_folders(self) -> Tuple[str, Mapping[str, CREFolder]]:
        # Timestamp has to be determined first, otherwise unobserved changes can slip through
        latest_timestamp = self._get_latest_timestamps_from_disk()[-1]
        wato_folders = _get_fully_loaded_wato_folders()
        return latest_timestamp, wato_folders

    @classmethod
    def redis_server_active(cls) -> bool:
        redis_pid_path = cmk.utils.paths.omd_root / "tmp" / "run" / "redis-server.pid"
        if not redis_pid_path.exists():
            return False

        with suppress(ValueError):
            return psutil.pid_exists(int(store.load_bytes_from_file(redis_pid_path)))
        return False

    @property
    def folder_paths(self) -> Sequence[PathWithSlash]:
        if self._folder_paths is None:
            self._folder_paths = tuple(self._client.smembers("wato:folder_list"))
        return self._folder_paths

    def recursive_subfolders_for_path(self, path: PathWithSlash) -> List[PathWithSlash]:
        return [x for x in self.folder_paths if x.startswith(path)]

    @property
    def loaded_wato_folders(self) -> Optional[Mapping[str, CREFolder]]:
        return self._loaded_wato_folders

    def clear_cached_folders(self) -> None:
        self._loaded_wato_folders = None
        self._folder_paths = None

    def choices_for_moving(self, path: PathWithoutSlash, move_type: _MoveType) -> Choices:
        self._fetch_all_metadata()
        path_to_title = {x.path: x.title_path_without_root for x in self._folder_metadata.values()}

        # Remove self
        del path_to_title[f"{path}/"]

        # Folder sanity checks. A folder cannot be moved into its subfolders
        if move_type == _MoveType.Folder:
            if path != "":
                # Remove move into parent (folder is already there)
                del path_to_title[f"{os.path.dirname(path)}/"]

            # Remove all subfolders (recursively)
            for possible_child_path in list(path_to_title.keys()):
                if possible_child_path.startswith(path):
                    del path_to_title[possible_child_path]

        # Check permissions
        if not user.may("wato.all_folders"):
            assert user.id is not None
            user_cgs = set(userdb.contactgroups_of_user(user.id))
            # Remove folders without permission
            for check_path in list(path_to_title.keys()):
                if permitted_groups := self._folder_metadata[check_path].permitted_groups:
                    if not user_cgs.intersection(set(permitted_groups.split(","))):
                        del path_to_title[check_path]

        return [(key.rstrip("/"), value) for key, value in path_to_title.items()]

    def folder_metadata(self, path: PathWithoutSlash) -> Optional[FolderMetaData]:
        path_with_slash = f"{path}/"
        if path_with_slash not in self._folder_metadata:
            results = self._client.hmget(
                f"wato:folders:{path_with_slash}",
                "title",
                "title_path_without_root",
                "permitted_contact_groups",
            )
            if not results:
                return None

            # Redis hmget typing states that the field can be None
            # It won't happen if the key is found, adding fallbacks anyway.
            permitted_groups = results[2].split(",") if results[2] is not None else []
            self._folder_metadata[path_with_slash] = FolderMetaData(
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

        def pairwise(iterable: Iterable[str]) -> Iterator[Tuple[str, str, str, str]]:
            """s -> (s0,s1,s2,s3), (s4,s5,s6,s7), ..."""
            a = iter(iterable)
            return zip(a, a, a, a)

        results = pipeline.execute()
        for folder_path, title, title_path_without_root, permitted_contact_groups in pairwise(
            results[0]
        ):
            self._folder_metadata[folder_path] = FolderMetaData(
                folder_path, title, title_path_without_root, permitted_contact_groups.split(",")
            )

    def _create_cache_from_scratch(
        self,
        update_timestamp: str,
        all_folders: Mapping[PathWithSlash, CREFolder],
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
        self, pipeline: Pipeline, all_folders: Mapping[PathWithoutSlash, CREFolder]
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
        permitted_contact_groups: Set[ContactgroupName],
    ) -> None:
        folder_key = f"wato:folders:{path}/"
        mapping: Mapping[Union[str, bytes], Union[str, int]] = {
            "num_hosts": num_hosts,
            "title": title,
            "title_path_without_root": title_path_without_root,
            "permitted_contact_groups": ",".join(permitted_contact_groups),
        }
        pipeline.hset(folder_key, mapping=mapping)

    def _add_last_folder_update_to_pipeline(self, pipeline: Pipeline, timestamp: str) -> None:
        pipeline.set("wato:folder_list:last_update", timestamp)

    def num_hosts_recursively_lua(self, path_with_slash: PathWithSlash) -> int:
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
        keys = [f"{path_with_slash}*"]
        args = ["permitted_contact_groups", "num_hosts"]
        recursive_hosts(keys=keys, args=args, client=pipeline)
        results = pipeline.execute()

        total_hosts = 0
        if not results:
            return total_hosts

        if (
            user.may("wato.see_all_folders")
            or not config.wato_hide_folders_without_read_permissions
        ):
            return sum(map(int, results[0][1::2]))

        def pairwise(iterable: Iterable[str]) -> Iterator[Tuple[str, str]]:
            """s -> (s0,s1), (s2,s3), (s4, s5), ..."""
            a = iter(iterable)
            return zip(a, a)

        assert user.id is not None
        user_cgs = set(userdb.contactgroups_of_user(user.id))
        for (folder_cgs, num_hosts) in pairwise(results[0]):
            cgs = set(folder_cgs.split(","))
            if user_cgs.intersection(cgs):
                total_hosts += int(num_hosts)

        return total_hosts

    def _cache_integrity_ok(self) -> bool:
        return self._get_latest_timestamps_from_disk()[-1] == self._get_last_update_from_redis()

    def _partial_data_update_possible(self, allowed_timestamps: List[str]) -> bool:
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

    def _get_allowed_folder_timestamps(self, folder: CREFolder) -> List[str]:
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
        folder: CREFolder,
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
        result = subprocess.run(
            "find ~/etc/check_mk/conf.d/wato -type d -printf '%T@\n' -o -name .wato -printf '%T@\n' | sort -n | tail -6 | uniq",
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
                return value
        except ValueError:
            pass
        return self._timestamp_to_fixed_precision_str(0.0)


def _get_fully_loaded_wato_folders() -> Mapping[PathWithoutSlash, CREFolder]:
    wato_folders: Dict[PathWithoutSlash, CREFolder] = {}
    Folder("", "").add_to_dictionary(wato_folders)
    return wato_folders


class _ABCWATOInfoStorage:
    def read(self, file_path: Path) -> Optional[Dict[str, Any]]:
        raise NotImplementedError()

    def write(self, file_path: Path, data: Dict[str, Any]) -> None:
        raise NotImplementedError()


class _StandardWATOInfoStorage(_ABCWATOInfoStorage):
    def read(self, file_path: Path) -> Dict[str, Any]:
        return store.load_object_from_file(file_path, default={})

    def write(self, file_path: Path, data: Dict[str, Any]) -> None:
        store.save_object_to_file(file_path, data)


class _PickleWATOInfoStorage(_ABCWATOInfoStorage):
    def read(self, file_path: Path) -> Optional[Dict[str, Any]]:
        pickle_path = self._add_suffix(file_path)
        if not pickle_path.exists() or not self._file_valid(pickle_path, file_path):
            return None
        return store.ObjectStore(pickle_path, serializer=PickleSerializer()).read_obj(default={})

    def _file_valid(self, pickle_path: Path, file_path: Path) -> bool:
        # The experimental file must not be older than the corresponding .wato
        # The file is also invalid if no matching .wato file exists
        if not file_path.exists():
            return False

        return file_path.stat().st_mtime <= pickle_path.stat().st_mtime

    def write(self, file_path: Path, data: Dict[str, Any]) -> None:
        pickle_store = store.ObjectStore(self._add_suffix(file_path), serializer=PickleSerializer())
        with pickle_store.locked():
            pickle_store.write_obj(data)

    def _add_suffix(self, path: Path) -> Path:
        return path.with_suffix(StorageFormat.PICKLE.extension())


class _WATOInfoStorageManager:
    """Handles read/write operations for the .wato file"""

    def __init__(self):
        self._write_storages = self._get_write_storages()
        self._read_storages = list(reversed(self._write_storages))

    def _get_write_storages(self) -> List[_ABCWATOInfoStorage]:
        storages: List[_ABCWATOInfoStorage] = [_StandardWATOInfoStorage()]
        if get_storage_format(config.config_storage_format) == StorageFormat.PICKLE:
            storages.append(_PickleWATOInfoStorage())
        return storages

    def read(self, store_file: Path) -> Dict[str, Any]:
        for storage in self._read_storages:
            if (storage_data := storage.read(store_file)) is not None:
                return storage_data
        return {}

    def write(self, store_file: Path, data: Dict[str, Any]) -> None:
        for storage in self._write_storages:
            storage.write(store_file, data)


class WithUniqueIdentifier(abc.ABC):
    """Provides methods for giving Hosts and Folders unique identifiers."""

    def __init__(self, *args, **kw):
        self._id = None
        # NOTE: Mixins with attributes are a bit questionable in general.
        # Furthermore, mypy is currently too dumb to understand mixins the way
        # we implement them, see e.g.
        # https://github.com/python/mypy/issues/5887 and related issues.
        super().__init__(*args, **kw)  # type: ignore[call-arg]

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
    def by_id(cls, identifier: str) -> Any:
        """Return the Folder instance of this particular identifier.

        Args:
            identifier (str): The unique key.

        Returns:
            The Folder-instance
        """
        folders = cls._mapped_by_id()
        if identifier not in folders:
            raise MKUserError(None, _("Folder %s not found.") % (identifier,))
        return folders[identifier]

    @classmethod
    def wato_info_storage_manager(cls):
        if "wato_info_storage_manager" not in g:
            g.wato_info_storage_manager = _WATOInfoStorageManager()
        return g.wato_info_storage_manager

    def persist_instance(self) -> None:
        """Save the current state of the instance to a file."""
        if self._id is None:
            self._id = self._get_identifier()

        data = self._get_instance_data()
        data = self._upgrade_keys(data)
        data["attributes"] = update_metadata(data["attributes"])
        data["__id"] = self._id
        store.makedirs(os.path.dirname(self._store_file_name()))
        self.wato_info_storage_manager().write(Path(self._store_file_name()), data)
        self._instance_saved_postprocess()

    def load_instance(self) -> None:
        """Load the data of this instance and return it.

        The internal state of the object will not be changed.

        Returns:
            The loaded data.
        """
        data = self.wato_info_storage_manager().read(Path(self._store_file_name()))

        data = self._upgrade_keys(data)
        unique_id = data.get("__id")
        if self._id is None:
            self._id = unique_id
        self._set_instance_data(data)

    @abc.abstractmethod
    def _set_instance_data(self, wato_info):
        """Hook method which is called by 'load_instance'.

        This method should assign to the instance the information just loaded from the file."""
        raise NotImplementedError()

    @abc.abstractmethod
    def _get_identifier(self) -> str:
        """The unique identifier of this object."""
        raise NotImplementedError()

    @abc.abstractmethod
    def _upgrade_keys(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Upgrade the structure of the store-file."""
        raise NotImplementedError()

    @abc.abstractmethod
    def _get_instance_data(self) -> Dict[str, Any]:
        """The data to persist to the file."""
        raise NotImplementedError()

    def _instance_saved_postprocess(self) -> None:
        """Additional actions after saving the data."""
        return

    @abc.abstractmethod
    def _store_file_name(self) -> str:
        """The filename to which to persist this object."""
        raise NotImplementedError()

    @abc.abstractmethod
    def _clear_id_cache(self) -> None:
        """Clear the cache if applicable."""
        raise NotImplementedError()

    @classmethod
    def _mapped_by_id(cls) -> Dict[str, Any]:
        """Give out a mapping from unique identifiers to class instances."""
        raise NotImplementedError()


class WithAttributes:
    """Mixin containing attribute management methods.

    Used in the Host and Folder classes."""

    def __init__(self, *args, **kw):
        # NOTE: Mixins with attributes are a bit questionable in general.
        # Furthermore, mypy is currently too dumb to understand mixins the way
        # we implement them, see e.g.
        # https://github.com/python/mypy/issues/5887 and related issues.
        super().__init__(*args, **kw)  # type: ignore[call-arg]
        self._attributes: Dict[str, Any] = {"meta_data": {}}
        self._effective_attributes = None

    # .--------------------------------------------------------------------.
    # | ATTRIBUTES                                                         |
    # '--------------------------------------------------------------------'
    # TODO: Returning a mutable private field is an absolute no-no... :-P
    def attributes(self):
        return self._attributes

    def attribute(self, attrname, default_value=None):
        return self.attributes().get(attrname, default_value)

    def set_attribute(self, attrname, value):
        self._attributes[attrname] = value

    def has_explicit_attribute(self, attrname):
        return attrname in self.attributes()

    def effective_attributes(self):
        raise NotImplementedError()

    def effective_attribute(self, attrname, default_value=None):
        return self.effective_attributes().get(attrname, default_value)

    def remove_attribute(self, attrname):
        del self.attributes()[attrname]

    def drop_caches(self):
        self._effective_attributes = None

    def updated_at(self):
        md = self._attributes.get("meta_data", {})
        return md.get("updated_at")

    def _cache_effective_attributes(self, effective):
        self._effective_attributes = effective.copy()

    def _get_cached_effective_attributes(self):
        if self._effective_attributes is None:
            raise KeyError("Not cached")
        return self._effective_attributes.copy()


class BaseFolder:
    """Base class of SearchFolder and Folder. Implements common methods"""

    def hosts(self):
        raise NotImplementedError()

    def breadcrumb(self) -> Breadcrumb:
        breadcrumb = Breadcrumb()

        for folder in self.parent_folder_chain() + [self]:
            breadcrumb.append(
                BreadcrumbItem(
                    title=folder.title(),
                    url=folder.url(),
                )
            )

        return breadcrumb

    def host_names(self):
        return self.hosts().keys()

    def load_host(self, host_name: str) -> CREHost:
        try:
            return self.hosts()[host_name]
        except KeyError:
            raise MKUserError(None, f"The host {host_name} could not be found.")

    def host(self, host_name: str) -> Optional[CREHost]:
        return self.hosts().get(host_name)

    def has_host(self, host_name):
        return host_name in self.hosts()

    def has_hosts(self):
        return len(self.hosts()) != 0

    def host_validation_errors(self):
        return validate_all_hosts(self.host_names())

    def is_disk_folder(self):
        return False

    def is_search_folder(self):
        return False

    def has_parent(self):
        return self.parent() is not None

    def parent(self):
        raise NotImplementedError()

    def is_same_as(self, folder):
        return self == folder or self.path() == folder.path()

    def path(self):
        raise NotImplementedError()

    def __eq__(self, other):
        return id(self) == id(other) or self.path() == other.path()

    def __hash__(self):
        return id(self)

    def is_current_folder(self):
        return self.is_same_as(Folder.current())

    def is_parent_of(self, maybe_child):
        return maybe_child.parent() == self

    def is_transitive_parent_of(self, maybe_child):
        return self.is_same_as(maybe_child) or (
            maybe_child.has_parent() and self.is_transitive_parent_of(maybe_child.parent())
        )

    def is_root(self):
        return not self.has_parent()

    def parent_folder_chain(self) -> List:
        folders = []
        folder = self.parent()
        while folder:
            folders.append(folder)
            folder = folder.parent()
        return folders[::-1]

    def name(self):
        raise NotImplementedError()

    def title(self) -> str:
        raise NotImplementedError()

    def subfolders(self, only_visible=False):
        raise NotImplementedError()

    def subfolder_by_title(self, title):
        raise NotImplementedError()

    def subfolder(self, name):
        raise NotImplementedError()

    def has_subfolders(self):
        raise NotImplementedError()

    def subfolder_choices(self):
        raise NotImplementedError()

    def move_subfolder_to(self, subfolder, target_folder):
        raise NotImplementedError()

    def create_subfolder(self, name, title, attributes):
        raise NotImplementedError()

    def edit_url(self, backfolder=None):
        raise NotImplementedError()

    def edit(self, new_title, new_attributes):
        raise NotImplementedError()

    def locked(self):
        raise NotImplementedError()

    def create_hosts(self, entries, bake_hosts=True):
        raise NotImplementedError()

    def site_id(self):
        raise NotImplementedError()


def deep_update(original, update, overwrite=True):
    """Update a dictionary with another's keys.

    Args:
        original: The original dictionary. This is being updated.
        update: The keys to be set on the original dictionary. May contain new keys.
        overwrite (bool): Also set already set values, even if they aren't None.

    Examples:

        If we don't want to overwrite the original's keys we can set the overwrite
        parameter to false.

        >>> res = deep_update({'meta_data': {'ca': 123, 'cb': 'foo'}},
        ...                   {'meta_data': {'ca': 234, 'ua': 123}}, overwrite=False)
        >>> assert res == {'meta_data': {'ca': 123, 'ua': 123, 'cb': 'foo'}}, res

        When 'overwrite' is set to true, every key is always set.

        >>> res = deep_update({'meta_data': {'ca': 123, 'cb': 'foo'}},
        ...                   {'meta_data': {'ca': 234, 'ua': 123}}, overwrite=True)
        >>> assert res == {'meta_data': {'ca': 234, 'ua': 123, 'cb': 'foo'}}, res

    Returns:
        The updated original dictionary, changed in place.

    """
    # Adapted from https://stackoverflow.com/a/3233356
    for k, v in update.items():
        if isinstance(v, ABCMapping):
            original[k] = deep_update(original.get(k, {}), v, overwrite=overwrite)
        else:
            if overwrite or k not in original or original[k] is None:
                original[k] = v
    return original


def update_metadata(
    attributes: Dict[str, Any],
    created_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Update meta_data timestamps and set created_by if provided.

    Args:
        attributes (dict): The attributes dictionary
        created_by (str): The user or script which created this object.

    Returns:
        The modified 'attributes' dictionary. It is actually modified in-place.

    Examples:

        >>> res = update_metadata({'meta_data': {'updated_at': 123}}, created_by='Dog')
        >>> assert res['meta_data']['created_by'] == 'Dog'
        >>> assert res['meta_data']['created_at'] == 123
        >>> assert 123 < res['meta_data']['updated_at'] <= time.time()

    Notes:

        New in 1.6:
            'meta_data' struct added.
        New in 1.7:
            Key 'updated_at' in 'meta_data' added for use in the REST API.

    """
    attributes.setdefault("meta_data", {})

    now_ = time.time()
    last_update = attributes["meta_data"].get("updated_at", None)
    # These attributes are only set if they don't exist or were set to None before.
    deep_update(
        attributes,
        {
            "meta_data": {
                "created_at": last_update if last_update is not None else now_,  # fix empty field
                "updated_at": now_,
                "created_by": created_by,
            }
        },
        overwrite=False,
    )

    # Intentionally overwrite updated_at every time
    deep_update(attributes, {"meta_data": {"updated_at": now_}}, overwrite=True)

    return attributes


def get_wato_redis_client() -> _RedisHelper:
    if "wato_redis_client" not in g:
        g.wato_redis_client = _RedisHelper()
    return g.wato_redis_client


class WATOHosts(TypedDict):
    locked: bool
    host_attributes: HostAttributes
    all_hosts: List[HostName]
    clusters: Dict[HostName, List[HostName]]


_enforce_disabled_redis = False


def may_use_redis() -> bool:
    # Redis can't be used for certain scenarios. For example
    # - Redis server is not running during cmk_update_config.py
    # - Bulk operations which would update redis several thousand times, instead of just once
    #     There is a special context manager which allows to disable redis handling in this case
    if not _redis_available() or _enforce_disabled_redis:
        return False

    return True


@request_memoize()
def _redis_available() -> bool:
    if not _RedisHelper.redis_server_active():
        return False

    if os.path.exists(os.path.expanduser("~/use_classic")):
        return False
    return True


@contextmanager
def disable_redis() -> Iterator[None]:
    global _enforce_disabled_redis
    last_value = _enforce_disabled_redis
    _enforce_disabled_redis = True
    yield
    _enforce_disabled_redis = last_value


def _wato_folders_factory() -> Mapping[PathWithoutSlash, Optional[CREFolder]]:
    if not may_use_redis():
        return _get_fully_loaded_wato_folders()

    wato_redis_client = get_wato_redis_client()
    if wato_redis_client.loaded_wato_folders is not None:
        # Folders were already completely loaded during cache generation -> use these
        return wato_redis_client.loaded_wato_folders

    # Provide a dict where the values are generated on demand
    return WATOFoldersOnDemand({x.rstrip("/"): None for x in wato_redis_client.folder_paths})


class CREFolder(WithPermissions, WithAttributes, WithUniqueIdentifier, BaseFolder):
    """This class represents a WATO folder that contains other folders and hosts."""

    # .--------------------------------------------------------------------.
    # | STATIC METHODS                                                     |
    # '--------------------------------------------------------------------'

    @staticmethod
    def all_folders():
        if "wato_folders" not in g:
            g.wato_folders = _wato_folders_factory()
        return g.wato_folders

    @staticmethod
    def folder_choices():
        if "folder_choices" not in g:
            g.folder_choices = Folder.root_folder().recursive_subfolder_choices()
        return g.folder_choices

    @staticmethod
    def folder_choices_fulltitle():
        if "folder_choices_full_title" not in g:
            g.folder_choices_full_title = Folder.root_folder().recursive_subfolder_choices(
                pretty=False
            )
        return g.folder_choices_full_title

    @staticmethod
    def folder(folder_path):
        if folder_path in Folder.all_folders():
            return Folder.all_folders()[folder_path]
        raise MKGeneralException("No WATO folder %s." % folder_path)

    @staticmethod
    def create_missing_folders(folder_path):
        folder = Folder.folder("")
        for subfolder_name in Folder._split_folder_path(folder_path):
            if folder.has_subfolder(subfolder_name):
                folder = folder.subfolder(subfolder_name)
            else:
                folder = folder.create_subfolder(subfolder_name, subfolder_name, {})

    @staticmethod
    def _split_folder_path(folder_path):
        if not folder_path:
            return []
        return folder_path.split("/")

    @staticmethod
    def folder_exists(folder_path: str) -> bool:
        # We need the slash '/' here
        if regex(r"^[%s/]*$" % WATO_FOLDER_PATH_NAME_CHARS).match(folder_path) is None:
            raise MKUserError("folder", "Folder name is not valid.")
        return os.path.exists(wato_root_dir() + folder_path)

    @staticmethod
    def root_folder() -> "CREFolder":
        return Folder.folder("")

    # Need this for specifying the correct type
    def parent_folder_chain(self) -> "List[CREFolder]":  # pylint: disable=useless-super-delegation
        return super().parent_folder_chain()

    @staticmethod
    def invalidate_caches():
        Folder.root_folder().drop_caches()
        if may_use_redis():
            get_wato_redis_client().clear_cached_folders()
        g.pop("wato_folders", {})
        for cache_id in ["folder_choices", "folder_choices_full_title"]:
            g.pop(cache_id, None)

    # Find folder that is specified by the current URL. This is either by a folder
    # path in the variable "folder" or by a host name in the variable "host". In the
    # latter case we need to load all hosts in all folders and actively search the host.
    # Another case is the host search which has the "host_search" variable set. To handle
    # the later case we call .current() of SearchFolder() to let it decide whether
    # this is a host search. This method has to return a folder in all cases.
    @staticmethod
    def current() -> "CREFolder":
        if "wato_current_folder" in g:
            return g.wato_current_folder

        folder = SearchFolder.current_search_folder()
        if folder:
            return folder

        if request.has_var("folder"):
            try:
                folder = Folder.folder(request.var("folder"))
            except MKGeneralException as e:
                raise MKUserError("folder", "%s" % e)
        else:
            host_name = request.var("host")
            folder = Folder.root_folder()
            if host_name:  # find host with full scan. Expensive operation
                host = Host.host(host_name)
                if host:
                    folder = host.folder()

        Folder.set_current(folder)
        return folder

    @staticmethod
    def current_disk_folder():
        folder = Folder.current()
        while not folder.is_disk_folder():
            folder = folder.parent()
        return folder

    @staticmethod
    def set_current(folder):
        g.wato_current_folder = folder

    def __init__(
        self, name, folder_path=None, parent_folder=None, title=None, attributes=None, root_dir=None
    ):
        super().__init__()
        self._name = name
        self._parent = parent_folder

        self._path_existing_folder = folder_path
        self._loaded_subfolders: Optional[Dict[PathWithoutSlash, CREFolder]] = None

        if attributes is None:
            attributes = {}

        attributes.setdefault("meta_data", {})

        self._choices_for_moving_host = None

        self._root_dir = root_dir
        if self._root_dir:
            self._root_dir = _ensure_trailing_slash(root_dir)
        else:
            self._root_dir = wato_root_dir()

        if self._path_existing_folder is not None:
            # Existing folder
            self._hosts = None
            self.load_instance()
        else:
            # New folder
            self._hosts = {}
            self._num_hosts = 0
            self._title = title or self._fallback_title()
            self._attributes = update_metadata(attributes)
            self._locked = False
            self._locked_hosts = False
            self._locked_subfolders = False

    @property
    def _subfolders(self):
        if self._loaded_subfolders is None:
            self._loaded_subfolders = self._load_subfolders()
        return self._loaded_subfolders

    def __repr__(self):
        return "Folder(%r, %r)" % (self.path(), self._title)

    def get_root_dir(self):
        return self._root_dir

    # Dangerous operation! Only use this if you have a good knowledge of the internas
    def set_root_dir(self, root_dir):
        self._root_dir = _ensure_trailing_slash(root_dir)

    def parent(self) -> "CREFolder":
        """Give the parent instance.

        Returns:
             CREFolder: The parent folder instance.

        """
        return self._parent

    def is_disk_folder(self):
        return True

    def _load_hosts_on_demand(self):
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
            host = self._create_host_from_variables(host_name, wato_hosts)
            self._hosts[host_name] = host

    def _create_host_from_variables(self, host_name: HostName, wato_hosts: WATOHosts) -> CREHost:
        cluster_nodes = wato_hosts["clusters"].get(host_name)
        attributes = self._transform_old_attributes(wato_hosts["host_attributes"][host_name])
        return Host(self, host_name, attributes, cluster_nodes)

    def _upgrade_keys(self, data):
        data["attributes"] = self._transform_old_attributes(data.get("attributes", {}))
        return data

    def _transform_old_attributes(self, attributes):
        """Mangle all attribute structures read from the disk to prepare it for the current logic"""
        attributes = self._transform_pre_15_agent_type_in_attributes(attributes)
        attributes = self._transform_none_value_site_attribute(attributes)
        attributes = self._add_missing_meta_data(attributes)
        attributes = self._transform_tag_snmp_ds(attributes)
        attributes = self._transform_cgconf_attributes(attributes)
        attributes = self._cleanup_pre_210_hostname_attribute(attributes)
        return attributes

    def _transform_cgconf_attributes(self, attributes):
        cgconf = attributes.get("contactgroups")
        if cgconf:
            attributes["contactgroups"] = convert_cgroups_from_tuple(cgconf)
        return attributes

    # In versions previous to 1.6 Checkmk had a tag group named "snmp" and an
    # auxiliary tag named "snmp" in the builtin tags. This name conflict had to
    # be resolved. The tag group has been changed to "snmp_ds" to fix it.
    def _transform_tag_snmp_ds(self, attributes):
        if "tag_snmp" in attributes:
            attributes["tag_snmp_ds"] = attributes.pop("tag_snmp")
        return attributes

    def _cleanup_pre_210_hostname_attribute(self, attributes):
        """Cleanup accidentally added hostname host attribute

        The host diagnostic page was adding the field "hostname" to the "attributes"
        dictionary before 2.0.0p24 and 2.1.0b6 when clicking on "Save and go to host
        properties".

        Args:
            attributes: The attributes dictionary

        Returns:
            The modified 'attributes' dictionary. It actually is modified in-place though.

        """
        attributes.pop("hostname", None)
        return attributes

    def _add_missing_meta_data(self, attributes):
        """Bring meta_data structure up to date.

        New in 1.6:
            'meta_data' struct added.

        New in 1.7:
            Key 'updated_at' in 'meta_data' added for use in the REST API.

        Args:
            attributes: The attributes dictionary

        Returns:
            The modified 'attributes' dictionary. In actually is modified in-place though.

        """
        meta_data = attributes.setdefault("meta_data", {})
        meta_data.setdefault("created_at", None)
        meta_data.setdefault("updated_at", None)
        meta_data.setdefault("created_by", None)
        return attributes

    # Old tag group trans:
    # ('agent', u'Agent type',
    #    [
    #        ('cmk-agent', u'Check_MK Agent (Server)', ['tcp']),
    #        ('snmp-only', u'SNMP (Networking device, Appliance)', ['snmp']),
    #        ('snmp-v1',   u'Legacy SNMP device (using V1)', ['snmp']),
    #        ('snmp-tcp',  u'Dual: Check_MK Agent + SNMP', ['snmp', 'tcp']),
    #        ('ping',      u'No Agent', []),
    #    ],
    # )
    #
    def _transform_pre_15_agent_type_in_attributes(self, attributes):
        if "tag_agent" not in attributes:
            return attributes  # Nothing set here, no transformation necessary

        if "tag_snmp" in attributes:
            return attributes  # Already in new format, no transformation necessary

        if "meta_data" in attributes:
            return attributes  # These attributes were already saved with version 1.6+

        value = attributes["tag_agent"]

        if value == "cmk-agent":
            attributes["tag_snmp"] = "no-snmp"

        elif value == "snmp-only":
            attributes["tag_agent"] = "no-agent"
            attributes["tag_snmp"] = "snmp-v2"

        elif value == "snmp-v1":
            attributes["tag_agent"] = "no-agent"
            attributes["tag_snmp"] = "snmp-v1"

        elif value == "snmp-tcp":
            attributes["tag_agent"] = "cmk-agent"
            attributes["tag_snmp"] = "snmp-v2"

        elif value == "ping":
            attributes["tag_agent"] = "no-agent"
            attributes["tag_snmp"] = "no-snmp"

        return attributes

    def _transform_none_value_site_attribute(self, attributes):
        # Old WATO was saving "site" attribute with value of None. Skip this key.
        if "site" in attributes and attributes["site"] is None:
            del attributes["site"]
        return attributes

    def _load_hosts_file(self) -> Optional[HostsData]:
        variables = get_hosts_file_variables()
        apply_hosts_file_to_object(
            Path(self.hosts_file_path_without_extension()),
            get_host_storage_loaders(config.config_storage_format),
            variables,
        )
        return variables

    def _load_wato_hosts(self) -> Optional[WATOHosts]:
        if (variables := self._load_hosts_file()) is None:
            return None
        return WATOHosts(
            locked=variables["_lock"],
            host_attributes=variables["host_attributes"],
            all_hosts=variables["all_hosts"],
            clusters=variables["clusters"],
        )

    def save_hosts(self):
        self.need_unlocked_hosts()
        self.need_permission("write")
        if self._hosts is not None:
            # Clean up caches of all hosts in this folder, just to be sure. We could also
            # check out all call sites of save_hosts() and partially drop the caches of
            # individual hosts to optimize this.
            for host in self._hosts.values():
                host.drop_caches()

            self._save_hosts_file()
            if may_use_redis():
                # Inform redis that the modified-timestamp of the folder has been updated.
                get_wato_redis_client().folder_updated(self.filesystem_path())

        call_hook_hosts_changed(self)

    def _save_hosts_file(self):
        store.makedirs(self.filesystem_path())
        if not self.has_hosts():
            for storage in get_all_storage_readers():
                storage.remove(Path(self.hosts_file_path_without_extension()))
            return

        all_hosts: List[str] = []
        clusters: Dict[str, List[str]] = {}
        hostnames = sorted(self.hosts().keys())
        # collect value for attributes that are to be present in Nagios
        custom_macros: Dict[str, Dict[str, str]] = {}
        # collect value for attributes that are explicitly set for one host
        explicit_host_conf: Dict[str, Dict[str, str]] = {}
        cleaned_hosts = {}
        host_tags = {}
        host_labels = {}
        group_rules_list: List[Tuple[List[GroupRuleType], bool]] = []

        attribute_mappings: Sequence[tuple[str, str, dict[str, Any]]] = [
            # host attr, cmk.base variable name, value
            ("ipaddress", "ipaddresses", {}),
            ("ipv6address", "ipv6addresses", {}),
            ("snmp_community", "explicit_snmp_communities", {}),
            ("management_snmp_community", "management_snmp_credentials", {}),
            ("management_ipmi_credentials", "management_ipmi_credentials", {}),
            ("management_protocol", "management_protocol", {}),
        ]

        for hostname in hostnames:
            host = self.hosts()[hostname]
            effective = host.effective_attributes()
            cleaned_hosts[hostname] = host.attributes()
            cleaned_hosts[hostname] = update_metadata(cleaned_hosts[hostname], created_by=user.id)

            tag_groups = host.tag_groups()
            if tag_groups:
                host_tags[hostname] = tag_groups

            labels = host.labels()
            if labels:
                host_labels[hostname] = labels

            if host.is_cluster():
                clusters[hostname] = host.cluster_nodes()
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
            if host.has_explicit_attribute("contactgroups"):
                cgconfig = convert_cgroups_from_tuple(host.attribute("contactgroups"))
                cgs = cgconfig["groups"]
                if cgs and cgconfig["use"]:
                    group_rules: List[GroupRuleType] = []
                    for cg in cgs:
                        group_rules.append(
                            {
                                "value": cg,
                                "condition": {"host_name": [hostname]},
                            }
                        )
                    group_rules_list.append((group_rules, cgconfig["use_for_services"]))

            for attr in host_attribute_registry.attributes():
                attrname = attr.name()
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
        )

        storage_list: List[ABCHostsStorage] = [StandardHostsStorage()]
        if experimental_storage := make_experimental_hosts_storage(
            get_storage_format(config.config_storage_format)
        ):
            storage_list.append(experimental_storage)

        for storage_module in storage_list:
            storage_module.write(
                Path(self.hosts_file_path_without_extension()),
                data,
                get_value_formatter(),
            )

    def _get_alias_from_extra_conf(self, host_name, variables):
        aliases = self._host_extra_conf(host_name, variables["extra_host_conf"]["alias"])
        if len(aliases) > 0:
            return aliases[0]
        return

    # This is a dummy implementation which works without tags
    # and implements only a special case of Checkmk's real logic.
    def _host_extra_conf(self, host_name, conflist):
        for value, hostlist in conflist:
            if host_name in hostlist:
                return [value]
        return []

    def _set_instance_data(self, wato_info):
        self._title = wato_info.get("title", self._fallback_title())
        self._attributes = wato_info.get("attributes", {})
        # Can either be set to True or a string (which will be used as host lock message)
        self._locked = wato_info.get("lock", False)
        # Can either be set to True or a string (which will be used as host lock message)
        self._locked_subfolders = wato_info.get("lock_subfolders", False)

        if "num_hosts" in wato_info:
            self._num_hosts = wato_info.get("num_hosts", None)
        else:
            # We don't want to trigger any state modifying methods on loading, as this leads to
            # very unpredictable behaviour. We dictate that `hosts()` will only ever be called
            # intentionally.
            self._num_hosts = len(self._hosts or {})

    def save(self) -> None:
        self.persist_instance()
        Folder.invalidate_caches()
        self.load_instance()

    def _get_identifier(self):
        return uuid.uuid4().hex

    def _get_instance_data(self):
        return self.get_wato_info()

    def _instance_saved_postprocess(self) -> None:
        if may_use_redis():
            get_wato_redis_client().save_folder_info(self)

    def get_wato_info(self):
        return {
            "title": self._title,
            "attributes": self._attributes,
            "num_hosts": self._num_hosts,
            "lock": self._locked,
            "lock_subfolders": self._locked_subfolders,
        }

    def _fallback_title(self):
        if self.is_root():
            return _("Main")
        return self.name()

    def _load_subfolders(self) -> Dict[PathWithoutSlash, CREFolder]:
        loaded_subfolders: Dict[str, CREFolder] = {}

        dir_path = self._root_dir + self.path()
        if not os.path.exists(dir_path):
            return loaded_subfolders

        for entry in os.listdir(dir_path):
            subfolder_dir = os.path.join(dir_path, entry)
            if os.path.isdir(subfolder_dir):
                if self.path():
                    subfolder_path = os.path.join(self.path(), entry)
                else:
                    # Main directory
                    subfolder_path = entry

                loaded_subfolders[entry] = Folder(
                    entry,
                    subfolder_path,
                    parent_folder=self,
                    root_dir=self._root_dir,
                )

        return loaded_subfolders

    def wato_info_path(self) -> str:
        return self.filesystem_path() + "/.wato"

    def hosts_file_path(self) -> str:
        return self.hosts_file_path_without_extension() + ".mk"

    def hosts_file_path_without_extension(self) -> str:
        return self.filesystem_path() + "/hosts"

    def rules_file_path(self) -> str:
        return self.filesystem_path() + "/rules.mk"

    def add_to_dictionary(self, dictionary):
        dictionary[self.path()] = self
        for subfolder in self._subfolders.values():
            subfolder.add_to_dictionary(dictionary)

    def drop_caches(self) -> None:
        super().drop_caches()
        self._choices_for_moving_host = None

        for subfolder in self._subfolders.values():
            subfolder.drop_caches()

        if self._hosts is not None:
            for host in self._hosts.values():
                host.drop_caches()

    # .-----------------------------------------------------------------------.
    # | ELEMENT ACCESS                                                        |
    # '-----------------------------------------------------------------------'

    def name(self):
        return self._name

    def title(self):
        return self._title

    def filesystem_path(self):
        return (self._root_dir + self.path()).rstrip("/")

    def ident(self):
        return self.path()

    def path(self):
        if may_use_redis() and self._path_existing_folder is not None:
            return self._path_existing_folder

        if self.parent() and not self.parent().is_root() and not self.is_root():
            return _ensure_trailing_slash(self.parent().path()) + self.name()

        return self.name()

    def path_for_gui_rule_matching(self):
        if self.is_root():
            return "/"
        return "/wato/%s/" % self.path()

    def path_for_rule_matching(self):
        path = self.path()
        return "/wato/%s/" % path if path else "/wato/"

    def object_ref(self) -> ObjectRef:
        return ObjectRef(ObjectRefType.Folder, self.path())

    def hosts(self) -> Dict[str, CREHost]:
        self._load_hosts_on_demand()
        return self._hosts

    def num_hosts(self):
        # Do *not* load hosts here! This method must kept cheap
        return self._num_hosts

    def num_hosts_recursively(self) -> int:
        if may_use_redis():
            if folder_metadata := get_wato_redis_client().folder_metadata(self.path()):
                return folder_metadata.num_hosts_recursively
            return 0

        num = self.num_hosts()
        for subfolder in self.subfolders(only_visible=True):
            num += subfolder.num_hosts_recursively()
        return num

    def all_hosts_recursively(self) -> Dict[str, CREHost]:
        hosts = {}
        hosts.update(self.hosts())
        for subfolder in self.subfolders():
            hosts.update(subfolder.all_hosts_recursively())
        return hosts

    def all_folders_recursively(self, only_visible: bool = False) -> List["CREFolder"]:
        def _add_folders(folder: CREFolder, collection: List[CREFolder]) -> None:
            collection.append(folder)
            for sub_folder in folder.subfolders(only_visible=only_visible):
                _add_folders(sub_folder, collection)

        folders: List[CREFolder] = []
        _add_folders(self.root_folder(), folders)
        return folders

    def subfolders(self, only_visible: bool = False) -> "List[CREFolder]":
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

    def subfolder(self, name: str) -> "CREFolder":
        """Find a Folder by its name-part.

        Args:
            name (str): The basename of this Folder, not its path.

        Returns:
            The found Folder-instance or raises a KeyError.
        """
        return self._subfolders[name]

    def subfolder_by_title(self, title: str) -> "Optional[CREFolder]":
        """Find a Folder by its title.

        Args:
            title (str): The `title()` of the folder to retrieve.

        Returns:
            The found Folder-instance or None.

        """
        return first([f for f in self.subfolders() if f.title() == title])

    def has_subfolder(self, name: str) -> bool:
        return name in self._subfolders

    def has_subfolders(self) -> bool:
        return len(self._subfolders) > 0

    def subfolder_choices(self):
        choices = []
        for subfolder in sorted(
            self.subfolders(only_visible=True), key=operator.methodcaller("title")
        ):
            choices.append((subfolder.path(), subfolder.title()))
        return choices

    def _prefixed_title(self, current_depth, pretty):
        if not pretty:
            return HTML(
                escaping.escape_attribute("/".join(str(p) for p in self.title_path_without_root()))
            )

        title_prefix = ("\u00a0" * 6 * current_depth) + "\u2514\u2500 " if current_depth else ""
        return HTML(title_prefix + escaping.escape_attribute(self.title()))

    def _walk_tree(self, results: List[Tuple[str, HTML]], current_depth, pretty):
        visible_subfolders = False
        for subfolder in sorted(
            self._subfolders.values(), key=operator.methodcaller("title"), reverse=True
        ):
            visible_subfolders = (
                subfolder._walk_tree(results, current_depth + 1, pretty) or visible_subfolders
            )

        if (
            visible_subfolders
            or self.may("read")
            or self.is_root()
            or not config.wato_hide_folders_without_read_permissions
        ):
            results.append((self.path(), self._prefixed_title(current_depth, pretty)))
            return True

        return False

    def recursive_subfolder_choices(self, pretty=True):
        result: List[Tuple[str, HTML]] = []
        self._walk_tree(result, 0, pretty)
        result.reverse()
        return result

    def choices_for_moving_folder(self) -> Choices:
        return self._choices_for_moving("folder")

    def choices_for_moving_host(self) -> Choices:
        if self._choices_for_moving_host is not None:
            return self._choices_for_moving_host  # Cached

        self._choices_for_moving_host = self._choices_for_moving("host")
        return self._choices_for_moving_host

    def folder_should_be_shown(self, how: str) -> bool:
        if not config.wato_hide_folders_without_read_permissions:
            return True

        has_permission = self.may(how)
        for subfolder in self.subfolders():
            if has_permission:
                break
            has_permission = subfolder.folder_should_be_shown(how)

        return has_permission

    def _choices_for_moving(self, what: str) -> Choices:
        choices: Choices = []

        if may_use_redis():
            return self._get_sorted_choices(
                get_wato_redis_client().choices_for_moving(self.path(), _MoveType(what))
            )

        for folder_path, folder in Folder.all_folders().items():
            if not folder.may("write"):
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

            msg = "/".join(str(p) for p in folder.title_path_without_root())
            choices.append((folder_path, msg))

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
        if "site" in self._attributes:
            return self._attributes["site"]
        if self.has_parent():
            return self.parent().site_id()
        if not is_wato_slave_site():
            return omd_site()

        # Placeholder for "central site". This is only relevant when using WATO on a remote site
        # and a host / folder has no site set.
        return SiteId("")

    def all_site_ids(self) -> List[SiteId]:
        site_ids: Set[SiteId] = set()
        self._add_all_sites_to_set(site_ids)
        return list(site_ids)

    # TODO: Horrible typing depending on optional parameter, which poisons all
    # call sites. Split this method!
    def title_path(self, withlinks: bool = False) -> List[Union[HTML, str]]:
        if withlinks:
            # In this case, we return a List[HTML]
            return [
                html.render_a(
                    folder.title(),
                    href=urls.makeuri_contextless(
                        request,
                        [("mode", "folder"), ("folder", folder.path())],
                        filename="wato.py",
                    ),
                )
                for folder in self.parent_folder_chain() + [self]
            ]
        # In this case, we return a List[str]
        return [folder.title() for folder in self.parent_folder_chain() + [self]]

    # TODO: Actually, we return a List[str], but title_path()'s typing is broken.
    def title_path_without_root(self) -> List[Union[HTML, str]]:
        if self.is_root():
            return [self.title()]
        return self.title_path()[1:]

    def alias_path(self, show_main=True):
        tp = self.title_path() if show_main else self.title_path_without_root()
        return " / ".join(str(p) for p in tp)

    def effective_attributes(self):
        try:
            return self._get_cached_effective_attributes()  # cached :-)
        except KeyError:
            pass

        effective = {}
        for folder in self.parent_folder_chain():
            effective.update(folder.attributes())
        effective.update(self.attributes())

        # now add default values of attributes for all missing values
        for host_attribute in host_attribute_registry.attributes():
            attrname = host_attribute.name()
            if attrname not in effective:
                effective.setdefault(attrname, host_attribute.default_value())

        self._cache_effective_attributes(effective)
        return effective

    def groups(self, host=None):
        # CLEANUP: this method is also used for determining host permission
        # in behalv of Host::groups(). Not nice but was done for avoiding
        # code duplication
        permitted_groups = set([])
        host_contact_groups = set([])
        if host:
            effective_folder_attributes = host.effective_attributes()
        else:
            effective_folder_attributes = self.effective_attributes()
        cgconf = _get_cgconf_from_attributes(effective_folder_attributes)

        # First set explicit groups
        permitted_groups.update(cgconf["groups"])
        if cgconf["use"]:
            host_contact_groups.update(cgconf["groups"])

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

        return permitted_groups, host_contact_groups, cgconf.get("use_for_services", False)

    def find_host_recursively(self, host_name: str) -> "Optional[CREHost]":
        host: Optional[CREHost] = self.host(host_name)
        if host:
            return host

        for subfolder in self.subfolders():
            host = subfolder.find_host_recursively(host_name)
            if host:
                return host
        return None

    @staticmethod
    def host_lookup_cache_path():
        return os.path.join(cmk.utils.paths.tmp_dir, "wato", "wato_host_folder_lookup.cache")

    @staticmethod
    def find_host_by_lookup_cache(host_name) -> Optional["CREHost"]:
        """This function tries to create a host object using its name from a lookup cache.
        If this does not work (cache miss), the regular search for the host is started.
        If the host was found by the regular search, the lookup cache is updated accordingly."""

        try:
            folder_lookup_cache = Folder.get_folder_lookup_cache()
            folder_hint = folder_lookup_cache.get(host_name)
            if folder_hint is not None and Folder.folder_exists(folder_hint):
                folder_instance = Folder.folder(folder_hint)
                host_instance = folder_instance.host(host_name)
                if host_instance is not None:
                    return host_instance

            # The hostname was not found in the lookup cache
            # Use find_host_recursively to search this host in the configuration
            host_instance = Folder.root_folder().find_host_recursively(host_name)
            if not host_instance:
                return None

            # Save newly found host instance to cache
            folder_lookup_cache[host_name] = host_instance.folder().path()
            Folder.save_host_lookup_cache(Folder.host_lookup_cache_path(), folder_lookup_cache)
            return host_instance
        except RequestTimeout:
            raise
        except Exception:
            logger.warning(
                "Unexpected exception in find_host_by_lookup_cache. Falling back to recursive host lookup",
                exc_info=True,
            )
            return Folder.root_folder().find_host_recursively(host_name)

    @staticmethod
    def get_folder_lookup_cache() -> Dict[HostName, str]:
        if "folder_lookup_cache" not in g:
            cache_path = Folder.host_lookup_cache_path()
            if not os.path.exists(cache_path) or os.stat(cache_path).st_size == 0:
                Folder.build_host_lookup_cache(cache_path)
            try:
                g.folder_lookup_cache = pickle.loads(store.load_bytes_from_file(cache_path))
            except (TypeError, pickle.UnpicklingError) as e:
                logger.warning("Unable to read folder_lookup_cache from disk: %s", str(e))
                g.folder_lookup_cache = {}
        return g.folder_lookup_cache

    @staticmethod
    def build_host_lookup_cache(cache_path):
        store.aquire_lock(cache_path)
        folder_lookup = {}
        for host_name, host in Folder.root_folder().all_hosts_recursively().items():
            folder_lookup[host_name] = host.folder().path()
        Folder.save_host_lookup_cache(cache_path, folder_lookup)

    @staticmethod
    def save_host_lookup_cache(cache_path, folder_lookup):
        store.save_bytes_to_file(cache_path, pickle.dumps(folder_lookup))

    @staticmethod
    def delete_host_lookup_cache():
        try:
            os.unlink(Folder.host_lookup_cache_path())
        except OSError as e:
            if e.errno == errno.ENOENT:
                return  # Not existant -> OK
            raise

    @staticmethod
    def add_hosts_to_lookup_cache(host2path_list):
        cache_path = Folder.host_lookup_cache_path()
        folder_lookup_cache = Folder.get_folder_lookup_cache()
        for (hostname, folder_path) in host2path_list:
            folder_lookup_cache[hostname] = folder_path
        Folder.save_host_lookup_cache(cache_path, folder_lookup_cache)

    @staticmethod
    def delete_hosts_from_lookup_cache(hostnames):
        cache_path = Folder.host_lookup_cache_path()
        folder_lookup_cache = Folder.get_folder_lookup_cache()
        for hostname in hostnames:
            try:
                del folder_lookup_cache[hostname]
            except KeyError:
                pass
        Folder.save_host_lookup_cache(cache_path, folder_lookup_cache)

    def _user_needs_permission(self, how: str) -> None:
        if how == "write" and user.may("wato.all_folders"):
            return

        if how == "read" and user.may("wato.see_all_folders"):
            return

        permitted_groups, _folder_contactgroups, _use_for_services = self.groups()
        assert user.id is not None
        # TODO: this groups are loaded anew for EVERY folder..
        user_contactgroups = userdb.contactgroups_of_user(user.id)

        for c in user_contactgroups:
            if c in permitted_groups:
                return

        reason = _("Sorry, you have no permissions to the folder <b>%s</b>.") % self.alias_path()
        if not permitted_groups:
            reason += " " + _("The folder is not permitted for any contact group.")
        else:
            reason += " " + _("The folder's permitted contact groups are <b>%s</b>.") % ", ".join(
                permitted_groups
            )
            if user_contactgroups:
                reason += " " + _("Your contact groups are <b>%s</b>.") % ", ".join(
                    user_contactgroups
                )
            else:
                reason += " " + _("But you are not a member of any contact group.")
        reason += " " + _(
            "You may enter the folder as you might have permission on a subfolders, though."
        )
        raise MKAuthException(reason)

    def need_recursive_permission(self, how: str) -> None:
        self.need_permission(how)
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

    def url(self, add_vars: Optional[HTTPVariables] = None) -> str:
        if add_vars is None:
            add_vars = []

        url_vars = [("folder", self.path())]
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

    def edit_url(self, backfolder: "Optional[CREFolder]" = None) -> str:
        if backfolder is None:
            if self.has_parent():
                backfolder = self.parent()
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

    def locked(self) -> Union[bool, str]:
        return self._locked

    def locked_subfolders(self) -> Union[bool, str]:
        return self._locked_subfolders

    def locked_hosts(self) -> Union[bool, str]:
        self._load_hosts_on_demand()
        return self._locked_hosts

    # Returns:
    #  None:      No network scan is enabled.
    #  timestamp: Next planned run according to config.
    def next_network_scan_at(self) -> Optional[float]:
        if "network_scan" not in self._attributes:
            return None

        interval = self._attributes["network_scan"]["scan_interval"]
        last_end = self._attributes.get("network_scan_result", {}).get("end", None)
        if last_end is None:
            next_time = time.time()
        else:
            next_time = last_end + interval

        time_allowed = self._attributes["network_scan"].get("time_allowed")
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
    # | These methods are for being called by actual WATO modules when they   |
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
    # | Sidebar: some sidebar snapins show the WATO folder tree. Everytime    |
    # | the tree changes the sidebar needs to be reloaded. This is done here. |
    # |                                                                       |
    # | Validation: these methods do *not* validate the parameters for syntax.|
    # | This is the task of the actual WATO modes or the API.                 |
    # '-----------------------------------------------------------------------'

    def create_subfolder(self, name, title, attributes):
        """Create a subfolder of the current folder

        Args:
            name: The filename of the folder to be created.
            title: The title.
            attributes: The attributes.

        Returns:
            Created Folder instance.
        """
        # 1. Check preconditions
        user.need_permission("wato.manage_folders")
        self.need_permission("write")
        self.need_unlocked_subfolders()
        _must_be_in_contactgroups(_get_cgconf_from_attributes(attributes)["groups"])

        attributes = update_metadata(attributes, created_by=user.id)

        # 2. Actual modification
        new_subfolder = Folder(name, parent_folder=self, title=title, attributes=attributes)
        self._subfolders[name] = new_subfolder
        new_subfolder.save()
        add_change(
            "new-folder",
            _("Created new folder %s") % new_subfolder.alias_path(),
            object_ref=new_subfolder.object_ref(),
            sites=[new_subfolder.site_id()],
            diff_text=make_diff_text(
                make_folder_audit_log_object({}),
                make_folder_audit_log_object(new_subfolder.attributes()),
            ),
        )
        hooks.call("folder-created", new_subfolder)
        self._clear_id_cache()
        need_sidebar_reload()
        return new_subfolder

    def delete_subfolder(self, name):
        # 1. Check preconditions
        user.need_permission("wato.manage_folders")
        self.need_permission("write")
        self.need_unlocked_subfolders()

        # 2. check if hosts have parents
        subfolder = self.subfolder(name)
        hosts_with_children = self._get_parents_of_hosts(subfolder.all_hosts_recursively().keys())
        if hosts_with_children:
            raise MKUserError(
                "delete_host",
                _("You cannot delete these hosts: %s")
                % ", ".join(
                    [
                        _("%s is parent of %s.") % (parent, ", ".join(children))
                        for parent, children in sorted(hosts_with_children.items())
                    ]
                ),
            )

        # 3. Actual modification
        hooks.call("folder-deleted", subfolder)
        add_change(
            "delete-folder",
            _("Deleted folder %s") % subfolder.alias_path(),
            object_ref=self.object_ref(),
            sites=subfolder.all_site_ids(),
        )
        del self._subfolders[name]
        shutil.rmtree(subfolder.filesystem_path())
        self._clear_id_cache()
        Folder.invalidate_caches()
        need_sidebar_reload()
        Folder.delete_host_lookup_cache()

    def move_subfolder_to(self, subfolder, target_folder):
        # 1. Check preconditions
        user.need_permission("wato.manage_folders")
        self.need_permission("write")
        self.need_unlocked_subfolders()
        target_folder.need_permission("write")
        target_folder.need_unlocked_subfolders()
        subfolder.need_recursive_permission("write")  # Inheritance is changed
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
                _("Cannot move folder: A folder can not be moved into itself."),
            )

        if self.path() == target_folder.path():
            raise MKUserError(
                None,
                _("Cannot move folder: A folder can not be moved to it's own parent folder."),
            )

        if subfolder in target_folder.parent_folder_chain():
            raise MKUserError(
                None,
                _("Cannot move folder: A folder can not be moved to a folder within itself."),
            )

        original_alias_path = subfolder.alias_path()

        # 2. Actual modification
        affected_sites = subfolder.all_site_ids()
        old_filesystem_path = subfolder.filesystem_path()
        shutil.move(old_filesystem_path, target_folder.filesystem_path())

        self._clear_id_cache()
        Folder.invalidate_caches()

        # Reload folder at new location and rewrite host files
        # Again, some special handling because of the missing slash in the main folder
        if not target_folder.is_root():
            moved_subfolder = Folder.folder(f"{target_folder.path()}/{subfolder.name()}")
        else:
            moved_subfolder = Folder.folder(subfolder.name())

        with disable_redis():
            # Do not update redis while rewriting a plethora of host files
            # Redis automatically updates on the next request
            moved_subfolder.rewrite_hosts_files()  # fixes changed inheritance

        affected_sites = list(set(affected_sites + moved_subfolder.all_site_ids()))
        add_change(
            "move-folder",
            _("Moved folder %s to %s") % (original_alias_path, target_folder.alias_path()),
            object_ref=moved_subfolder.object_ref(),
            sites=affected_sites,
        )
        need_sidebar_reload()
        Folder.delete_host_lookup_cache()

    def edit(self, new_title, new_attributes):
        # 1. Check preconditions
        self.need_permission("write")
        self.need_unlocked()

        # For changing contact groups user needs write permission on parent folder
        new_cgconf = _get_cgconf_from_attributes(new_attributes)
        old_cgconf = _get_cgconf_from_attributes(self.attributes())
        if new_cgconf != old_cgconf:
            _validate_contact_group_modification(old_cgconf["groups"], new_cgconf["groups"])

            if self.has_parent():
                if not self.parent().may("write"):
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

        old_object = make_folder_audit_log_object(self._attributes)

        self._title = new_title
        self._attributes = new_attributes

        # Due to changes in folder/file attributes, host files
        # might need to be rewritten in order to reflect Changes
        # in Nagios-relevant attributes.
        self.save()
        self.rewrite_hosts_files()

        affected_sites = list(set(affected_sites + self.all_site_ids()))
        add_change(
            "edit-folder",
            _("Edited properties of folder %s") % self.title(),
            object_ref=self.object_ref(),
            sites=affected_sites,
            diff_text=make_diff_text(old_object, make_folder_audit_log_object(self._attributes)),
        )
        self._clear_id_cache()

    def prepare_create_hosts(self):
        user.need_permission("wato.manage_hosts")
        self.need_unlocked_hosts()
        self.need_permission("write")

    def create_hosts(self, entries, bake_hosts=True):
        # 1. Check preconditions
        self.prepare_create_hosts()

        for host_name, attributes, _cluster_nodes in entries:
            self.verify_host_details(host_name, attributes)

        self.create_validated_hosts(entries, bake_hosts)

    def create_validated_hosts(self, entries, bake_hosts):
        # 2. Actual modification
        self._load_hosts_on_demand()
        for host_name, attributes, cluster_nodes in entries:
            self.propagate_hosts_changes(host_name, attributes, cluster_nodes)

        self.persist_instance()  # num_hosts has changed
        self.save_hosts()

        # 3. Prepare agents for the new hosts
        if bake_hosts:
            try_bake_agents_for_hosts([e[0] for e in entries])

        folder_path = self.path()
        Folder.add_hosts_to_lookup_cache([(x[0], folder_path) for x in entries])

    @staticmethod
    def verify_host_details(name, attributes):
        # MKAuthException, MKUserError
        _must_be_in_contactgroups(_get_cgconf_from_attributes(attributes)["groups"])
        validate_host_uniqueness("host", name)
        update_metadata(attributes, created_by=user.id)

    def propagate_hosts_changes(self, host_name, attributes, cluster_nodes):
        host = Host(self, host_name, attributes, cluster_nodes)
        self._hosts[host_name] = host
        self._num_hosts = len(self._hosts)
        add_change(
            "create-host",
            _("Created new host %s.") % host_name,
            object_ref=host.object_ref(),
            sites=[host.site_id()],
            diff_text=make_diff_text(
                {}, make_host_audit_log_object(host.attributes(), host.cluster_nodes())
            ),
            domain_settings=ConfigDomainCore.generate_domain_settings([host_name]),
        )

    def delete_hosts(self, host_names):
        # 1. Check preconditions
        user.need_permission("wato.manage_hosts")
        self.need_unlocked_hosts()
        self.need_permission("write")

        # 2. check if hosts have parents
        hosts_with_children = self._get_parents_of_hosts(host_names)
        if hosts_with_children:
            raise MKUserError(
                "delete_host",
                _("You cannot delete these hosts: %s")
                % ", ".join(
                    [
                        _("%s is parent of %s.") % (parent, ", ".join(children))
                        for parent, children in sorted(hosts_with_children.items())
                    ]
                ),
            )

        # 3. Delete host specific files (caches, tempfiles, ...)
        self._delete_host_files(host_names)

        # 4. Actual modification
        for host_name in host_names:
            host = self.hosts()[host_name]
            del self._hosts[host_name]
            self._num_hosts = len(self._hosts)
            add_change(
                "delete-host",
                _("Deleted host %s") % host_name,
                object_ref=host.object_ref(),
                sites=[host.site_id()],
            )

        self.persist_instance()  # num_hosts has changed
        self.save_hosts()
        Folder.delete_hosts_from_lookup_cache(host_names)

    def _get_parents_of_hosts(self, host_names):
        # Note: Deletion of chosen hosts which are parents
        # is possible if and only if all children are chosen, too.
        hosts_with_children: Dict[str, List[str]] = {}
        for child_key, child in Folder.root_folder().all_hosts_recursively().items():
            for host_name in host_names:
                if host_name in child.parents():
                    hosts_with_children.setdefault(host_name, [])
                    hosts_with_children[host_name].append(child_key)

        result: Dict[str, List[str]] = {}
        for parent, children in hosts_with_children.items():
            if not set(children) < set(host_names):
                result.setdefault(parent, children)
        return result

    # Group the given host names by their site and delete their files
    def _delete_host_files(self, host_names: Sequence[HostName]) -> None:
        for site_id, site_host_names in self.get_hosts_by_site(host_names).items():
            delete_hosts(
                site_id,
                site_host_names,
            )

    def get_hosts_by_site(
        self, host_names: Sequence[HostName]
    ) -> Mapping[SiteId, Sequence[HostName]]:
        hosts_by_site: Dict[SiteId, List[HostName]] = {}
        hosts = self.hosts()
        for host_name in host_names:
            host = hosts[host_name]
            hosts_by_site.setdefault(host.site_id(), []).append(host_name)
        return hosts_by_site

    def move_hosts(self, host_names, target_folder):
        # 1. Check preconditions
        user.need_permission("wato.manage_hosts")
        user.need_permission("wato.edit_hosts")
        user.need_permission("wato.move_hosts")
        self.need_permission("write")
        self.need_unlocked_hosts()
        target_folder.need_permission("write")
        target_folder.need_unlocked_hosts()

        # 2. Actual modification
        for host_name in host_names:
            host = self.load_host(host_name)

            affected_sites = [host.site_id()]

            self._remove_host(host)
            target_folder._add_host(host)

            affected_sites = list(set(affected_sites + [host.site_id()]))
            old_folder_text = self.path() or self.root_folder().title()
            new_folder_text = target_folder.path() or self.root_folder().title()
            add_change(
                "move-host",
                _('Moved host from "%s" to "%s"') % (old_folder_text, new_folder_text),
                object_ref=host.object_ref(),
                sites=affected_sites,
            )

        self.persist_instance()  # num_hosts has changed
        self.save_hosts()

        target_folder.persist_instance()
        target_folder.save_hosts()

        folder_path = target_folder.path()
        Folder.add_hosts_to_lookup_cache([(x, folder_path) for x in host_names])

    def rename_host(self, oldname, newname):
        # 1. Check preconditions
        user.need_permission("wato.manage_hosts")
        user.need_permission("wato.edit_hosts")
        self.need_unlocked_hosts()
        host = self.hosts()[oldname]
        host.need_permission("write")

        # 2. Actual modification
        host.rename(newname)
        del self._hosts[oldname]
        self._hosts[newname] = host
        add_change(
            "rename-host",
            _("Renamed host from %s to %s") % (oldname, newname),
            object_ref=host.object_ref(),
            sites=[host.site_id()],
        )

        Folder.delete_hosts_from_lookup_cache([oldname])
        Folder.add_hosts_to_lookup_cache([(newname, self.path())])

        self.save_hosts()

    def rename_parent(self, oldname, newname):
        # Must not fail because of auth problems. Auth is check at the
        # actually renamed host.
        changed = rename_host_in_list(self._attributes["parents"], oldname, newname)
        if not changed:
            return False

        add_change(
            "rename-parent",
            _('Renamed parent from %s to %s in folder "%s"')
            % (oldname, newname, self.alias_path()),
            object_ref=self.object_ref(),
            sites=self.all_site_ids(),
        )
        self.save_hosts()
        self.save()
        return True

    def rewrite_hosts_files(self):
        self._rewrite_hosts_file()
        for subfolder in self.subfolders():
            subfolder.rewrite_hosts_files()

    def rewrite_folders(self):
        self.persist_instance()
        for subfolder in self.subfolders():
            subfolder.rewrite_folders()

    def _add_host(self, host):
        self._load_hosts_on_demand()
        self._hosts[host.name()] = host
        host._folder = self
        self._num_hosts = len(self._hosts)

    def _remove_host(self, host):
        self._load_hosts_on_demand()
        del self._hosts[host.name()]
        host._folder = None
        self._num_hosts = len(self._hosts)

    def _add_all_sites_to_set(self, site_ids):
        site_ids.add(self.site_id())
        for host in self.hosts().values():
            site_ids.add(host.site_id())
        for subfolder in self.subfolders():
            subfolder._add_all_sites_to_set(site_ids)

    def _rewrite_hosts_file(self):
        self._load_hosts_on_demand()
        self.save_hosts()

    # .-----------------------------------------------------------------------.
    # | HTML Generation                                                       |
    # '-----------------------------------------------------------------------'

    def show_locking_information(self):
        self._load_hosts_on_demand()
        lock_messages: List[str] = []

        # Locked hosts
        if self._locked_hosts is True:
            lock_messages.append(
                _(
                    "Host attributes are locked "
                    "(You cannot create, edit or delete hosts in this folder)"
                )
            )
        elif isinstance(self._locked_hosts, str) and self._locked_hosts:
            lock_messages.append(self._locked_hosts)

        # Locked folder attributes
        if self._locked is True:
            lock_messages.append(
                _("Folder attributes are locked " "(You cannot edit the attributes of this folder)")
            )
        elif isinstance(self._locked, str) and self._locked:
            lock_messages.append(self._locked)

        # Also subfolders are locked
        if self._locked_subfolders:
            lock_messages.append(
                _("Subfolders are locked " "(You cannot create or remove folders in this folder)")
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

    def _store_file_name(self):
        return self.wato_info_path()

    def _clear_id_cache(self):
        folders_by_id.clear_cache()

    @classmethod
    def _mapped_by_id(cls) -> "Dict[str, Type[CREFolder]]":
        return folders_by_id()


class WATOFoldersOnDemand(Mapping[PathWithoutSlash, Optional[CREFolder]]):
    def __init__(self, values: Dict[PathWithoutSlash, Optional[CREFolder]]):
        self._raw_dict: Dict[PathWithoutSlash, Optional[CREFolder]] = values

    def __getitem__(self, path_without_slash: PathWithoutSlash) -> CREFolder:
        item: Optional[CREFolder] = self._raw_dict.get(path_without_slash)
        if item is None:
            item = self._create_folder(path_without_slash)
            self._raw_dict.__setitem__(path_without_slash, item)
        return item

    def __iter__(self) -> Iterator[PathWithoutSlash]:
        return iter(self._raw_dict)

    def __len__(self) -> int:
        return len(self._raw_dict)

    def _create_folder(self, folder_path: PathWithoutSlash) -> CREFolder:
        parent_folder = None
        if folder_path != "":
            parent_folder = self.__getitem__(str(Path(folder_path).parent).lstrip("."))

        return Folder(os.path.basename(folder_path), folder_path, parent_folder)


def validate_host_uniqueness(varname, host_name):
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
    v = attributes.get("contactgroups", (False, []))
    return convert_cgroups_from_tuple(v)


class SearchFolder(WithPermissions, WithAttributes, BaseFolder):
    """A virtual folder representing the result of a search."""

    @staticmethod
    def criteria_from_html_vars():
        crit = {".name": request.var("host_search_host")}
        crit.update(
            collect_attributes(
                "host_search", new=False, do_validate=False, varprefix="host_search_"
            )
        )
        return crit

    # This method is allowed to return None when no search is currently performed.
    @staticmethod
    def current_search_folder():
        if request.has_var("host_search"):
            base_folder = Folder.folder(request.var("folder", ""))
            search_criteria = SearchFolder.criteria_from_html_vars()
            folder = SearchFolder(base_folder, search_criteria)
            Folder.set_current(folder)
            return folder

    # .--------------------------------------------------------------------.
    # | CONSTRUCTION                                                       |
    # '--------------------------------------------------------------------'

    def __init__(self, base_folder, criteria):
        super().__init__()
        self._criteria = criteria
        self._base_folder = base_folder
        self._found_hosts = None
        self._name = None

    def __repr__(self):
        return "SearchFolder(%r, %s)" % (self._base_folder.path(), self._name)

    # .--------------------------------------------------------------------.
    # | ACCESS                                                             |
    # '--------------------------------------------------------------------'

    def attributes(self):
        return {}

    def parent(self):
        return self._base_folder

    def is_search_folder(self):
        return True

    def _user_needs_permission(self, how: str) -> None:
        pass

    def title(self):
        return _("Search results for folder %s") % self._base_folder.title()

    def hosts(self):
        if self._found_hosts is None:
            self._found_hosts = self._search_hosts_recursively(self._base_folder)
        return self._found_hosts

    def locked_hosts(self):
        return False

    def locked_subfolders(self):
        return False

    def show_locking_information(self):
        pass

    def has_subfolder(self, name):
        return False

    def has_subfolders(self):
        return False

    def choices_for_moving_host(self):
        return Folder.folder_choices()

    def path(self):
        if self._name:
            return self._base_folder.path() + "//search:" + self._name
        return self._base_folder.path() + "//search"

    def url(self, add_vars=None):
        if add_vars is None:
            add_vars = []

        url_vars = [("host_search", "1")] + add_vars

        for varname, value in request.itervars():
            if varname.startswith("host_search_") or varname.startswith("_change"):
                url_vars.append((varname, value))
        return self.parent().url(url_vars)

    # .--------------------------------------------------------------------.
    # | ACTIONS                                                            |
    # '--------------------------------------------------------------------'

    def delete_hosts(self, host_names):
        auth_errors = []
        for folder, these_host_names in self._group_hostnames_by_folder(host_names):
            try:
                folder.delete_hosts(these_host_names)
            except MKAuthException as e:
                auth_errors.append(
                    _("<li>Cannot delete hosts in folder %s: %s</li>") % (folder.alias_path(), e)
                )
        self._invalidate_search()
        if auth_errors:
            raise MKAuthException(
                _("Some hosts could not be deleted:<ul>%s</ul>") % "".join(auth_errors)
            )

    def move_hosts(self, host_names, target_folder):
        auth_errors = []
        for folder, host_names1 in self._group_hostnames_by_folder(host_names):
            try:
                # FIXME: this is not transaction safe, might get partially finished...
                folder.move_hosts(host_names1, target_folder)
            except MKAuthException as e:
                auth_errors.append(
                    _("<li>Cannot move hosts from folder %s: %s</li>") % (folder.alias_path(), e)
                )
        self._invalidate_search()
        if auth_errors:
            raise MKAuthException(
                _("Some hosts could not be moved:<ul>%s</ul>") % "".join(auth_errors)
            )

    # .--------------------------------------------------------------------.
    # | PRIVATE METHODS                                                    |
    # '--------------------------------------------------------------------'

    def _group_hostnames_by_folder(self, host_names):
        by_folder: Dict[str, List[CREHost]] = {}
        for host_name in host_names:
            host = self.load_host(host_name)
            by_folder.setdefault(host.folder().path(), []).append(host)

        return [
            (hosts[0].folder(), [_host.name() for _host in hosts]) for hosts in by_folder.values()
        ]

    def _search_hosts_recursively(self, in_folder):
        hosts = self._search_hosts(in_folder)
        for subfolder in in_folder.subfolders():
            hosts.update(self._search_hosts_recursively(subfolder))
        return hosts

    def _search_hosts(self, in_folder):
        if not in_folder.may("read"):
            return {}

        found = {}
        for host_name, host in in_folder.hosts().items():
            if self._criteria[".name"] and not host_attribute_matches(
                self._criteria[".name"], host_name
            ):
                continue

            # Compute inheritance
            effective = host.effective_attributes()

            # Check attributes
            dont_match = False
            for attr in host_attribute_registry.attributes():
                attrname = attr.name()
                if attrname in self._criteria and not attr.filter_matches(
                    self._criteria[attrname], effective.get(attrname), host_name
                ):
                    dont_match = True
                    break

            if not dont_match:
                found[host_name] = host

        return found

    def _invalidate_search(self):
        self._found_hosts = None


class CREHost(WithPermissions, WithAttributes):
    """Class representing one host that is managed via WATO. Hosts are contained in Folders."""

    # .--------------------------------------------------------------------.
    # | STATIC METHODS                                                     |
    # '--------------------------------------------------------------------'

    @staticmethod
    def load_host(host_name: str) -> "CREHost":
        host = Host.host(host_name)
        if host is None:
            raise MKUserError(None, "Host could not be found.", status=404)
        return host

    @staticmethod
    def host(host_name) -> Optional["CREHost"]:
        return Folder.find_host_by_lookup_cache(host_name)

    @staticmethod
    def all() -> Dict[str, "CREHost"]:
        return Folder.root_folder().all_hosts_recursively()

    @staticmethod
    def host_exists(host_name) -> bool:
        return Host.host(host_name) is not None

    # .--------------------------------------------------------------------.
    # | CONSTRUCTION, LOADING & SAVING                                     |
    # '--------------------------------------------------------------------'

    def __init__(self, folder, host_name, attributes, cluster_nodes):
        super().__init__()
        self._folder = folder
        self._name = host_name
        self._attributes = attributes
        self._cluster_nodes = cluster_nodes
        self._cached_host_tags = None

    def __repr__(self):
        return "Host(%r)" % (self._name)

    def drop_caches(self):
        super().drop_caches()
        self._cached_host_tags = None

    # .--------------------------------------------------------------------.
    # | ELEMENT ACCESS                                                     |
    # '--------------------------------------------------------------------'

    def id(self):
        return self.name()

    def ident(self) -> str:
        return self.name()

    def name(self):
        return self._name

    def alias(self):
        # Alias cannot be inherited, so no need to use effective_attributes()
        return self.attributes().get("alias")

    def folder(self) -> CREFolder:
        return self._folder

    def object_ref(self) -> ObjectRef:
        return ObjectRef(ObjectRefType.Host, self.name())

    def locked(self):
        return self.folder().locked_hosts()

    def need_unlocked(self):
        return self.folder().need_unlocked_hosts()

    def is_cluster(self):
        return self._cluster_nodes is not None

    def cluster_nodes(self):
        return self._cluster_nodes

    def is_offline(self):
        return self.tag("criticality") == "offline"

    def site_id(self):
        return self._attributes.get("site") or self.folder().site_id()

    def parents(self):
        return self.effective_attribute("parents", [])

    def tag_groups(self) -> TaggroupIDToTagID:
        """Compute tags from host attributes
        Each tag attribute may set multiple tags.  can set tags (e.g. the SiteAttribute)"""

        if self._cached_host_tags is not None:
            return self._cached_host_tags  # Cached :-)

        tag_groups: Dict[TaggroupID, TagID] = {}
        effective = self.effective_attributes()
        for attr in host_attribute_registry.attributes():
            value = effective.get(attr.name())
            tag_groups.update(attr.get_tag_groups(value))

        # When a host as been configured not to use the agent and not to use
        # SNMP, it needs to get the ping tag assigned.
        # Because we need information from multiple attributes to get this
        # information, we need to add this decision here.
        # Skip this in case no-ip is configured: A ping check is useless in this case
        if (
            tag_groups["snmp_ds"] == "no-snmp"
            and tag_groups["agent"] == "no-agent"
            and tag_groups["address_family"] != "no-ip"
        ):
            tag_groups["ping"] = "ping"

        # The following code is needed to migrate host/rule matching from <1.5
        # to 1.5 when a user did not modify the "agent type" tag group.  (See
        # migrate_old_sample_config_tag_groups() for more information)
        aux_tag_ids = [t.id for t in config.tags.aux_tag_list.get_tags()]

        # Be compatible to: Agent type -> SNMP v2 or v3
        if (
            tag_groups["agent"] == "no-agent"
            and tag_groups["snmp_ds"] == "snmp-v2"
            and "snmp-only" in aux_tag_ids
        ):
            tag_groups["snmp-only"] = "snmp-only"

        # Be compatible to: Agent type -> Dual: SNMP + TCP
        if (
            tag_groups["agent"] == "cmk-agent"
            and tag_groups["snmp_ds"] == "snmp-v2"
            and "snmp-tcp" in aux_tag_ids
        ):
            tag_groups["snmp-tcp"] = "snmp-tcp"

        self._cached_host_tags = tag_groups
        return tag_groups

    # TODO: Can we remove this?
    def tags(self):
        # The pre 1.6 tags contained only the tag group values (-> chosen tag id),
        # but there was a single tag group added with it's leading tag group id. This
        # was the internal "site" tag that is created by HostAttributeSite.
        tags = set(v for k, v in self.tag_groups().items() if k != "site")
        tags.add("site:%s" % self.tag_groups()["site"])
        return tags

    def is_ping_host(self):
        return self.tag_groups().get("ping") == "ping"

    def tag(self, taggroup_name):
        effective = self.effective_attributes()
        attribute_name = "tag_" + taggroup_name
        return effective.get(attribute_name)

    def discovery_failed(self):
        return self.attributes().get("inventory_failed", False)

    def validation_errors(self):
        if hooks.registered("validate-host"):
            errors = []
            for hook in hooks.get("validate-host"):
                try:
                    hook.handler(self)
                except MKUserError as e:
                    errors.append("%s" % e)
            return errors
        return []

    def effective_attributes(self):
        try:
            return self._get_cached_effective_attributes()  # cached :-)
        except KeyError:
            pass

        effective = self.folder().effective_attributes()
        effective.update(self.attributes())
        self._cache_effective_attributes(effective)
        return effective

    def labels(self):
        """Returns the aggregated labels for the current host

        The labels of all parent folders and the host are added together. When multiple
        objects define the same tag group, the nearest to the host wins."""
        labels = {}
        for obj in self.folder().parent_folder_chain() + [self.folder()]:
            labels.update(obj.attributes().get("labels", {}).items())
        labels.update(self.attributes().get("labels", {}).items())
        return labels

    def groups(self):
        return self.folder().groups(self)

    def _user_needs_permission(self, how: str) -> None:
        if how == "write" and user.may("wato.all_folders"):
            return

        if how == "read" and user.may("wato.see_all_folders"):
            return

        if how == "write":
            user.need_permission("wato.edit_hosts")

        permitted_groups, _host_contact_groups, _use_for_services = self.groups()
        assert user.id is not None
        user_contactgroups = userdb.contactgroups_of_user(user.id)

        for c in user_contactgroups:
            if c in permitted_groups:
                return

        reason = _(
            "Sorry, you have no permission on the host '<b>%s</b>'. The host's contact "
            "groups are <b>%s</b>, your contact groups are <b>%s</b>."
        ) % (self.name(), ", ".join(permitted_groups), ", ".join(user_contactgroups))
        raise MKAuthException(reason)

    def edit_url(self):
        return urls.makeuri_contextless(
            request,
            [
                ("mode", "edit_host"),
                ("folder", self.folder().path()),
                ("host", self.name()),
            ],
            filename="wato.py",
        )

    def params_url(self):
        return urls.makeuri_contextless(
            request,
            [
                ("mode", "object_parameters"),
                ("folder", self.folder().path()),
                ("host", self.name()),
            ],
            filename="wato.py",
        )

    def services_url(self):
        return urls.makeuri_contextless(
            request,
            [
                ("mode", "inventory"),
                ("folder", self.folder().path()),
                ("host", self.name()),
            ],
            filename="wato.py",
        )

    def clone_url(self):
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
    # | These methods are for being called by actual WATO modules when they|
    # | want to modify hosts. See details at the comment header in Folder. |
    # '--------------------------------------------------------------------'

    def edit(self, attributes, cluster_nodes):
        # 1. Check preconditions
        if attributes.get("contactgroups") != self._attributes.get("contactgroups"):
            self._need_folder_write_permissions()
        self.need_permission("write")
        self.need_unlocked()

        _validate_contact_group_modification(
            _get_cgconf_from_attributes(self._attributes)["groups"],
            _get_cgconf_from_attributes(attributes)["groups"],
        )

        old_object = make_host_audit_log_object(self._attributes, self._cluster_nodes)
        new_object = make_host_audit_log_object(attributes, cluster_nodes)

        # 2. Actual modification
        affected_sites = [self.site_id()]
        self._attributes = attributes
        self._cluster_nodes = cluster_nodes
        affected_sites = list(set(affected_sites + [self.site_id()]))
        self.folder().save_hosts()
        add_change(
            "edit-host",
            _("Modified host %s.") % self.name(),
            object_ref=self.object_ref(),
            sites=affected_sites,
            diff_text=make_diff_text(old_object, new_object),
            domain_settings=ConfigDomainCore.generate_domain_settings([self.name()]),
        )

    def update_attributes(self, changed_attributes):
        new_attributes = self.attributes().copy()
        new_attributes.update(changed_attributes)
        self.edit(new_attributes, self._cluster_nodes)

    def clean_attributes(self, attrnames_to_clean):
        # 1. Check preconditions
        if "contactgroups" in attrnames_to_clean:
            self._need_folder_write_permissions()
        self.need_unlocked()

        old = make_host_audit_log_object(self._attributes.copy(), self._cluster_nodes)

        # 2. Actual modification
        affected_sites = [self.site_id()]
        for attrname in attrnames_to_clean:
            if attrname in self._attributes:
                del self._attributes[attrname]
        affected_sites = list(set(affected_sites + [self.site_id()]))
        self.folder().save_hosts()
        add_change(
            "edit-host",
            _("Removed explicit attributes of host %s.") % self.name(),
            object_ref=self.object_ref(),
            sites=affected_sites,
            diff_text=make_diff_text(
                old, make_host_audit_log_object(self._attributes, self._cluster_nodes)
            ),
        )

    def _need_folder_write_permissions(self):
        if not self.folder().may("write"):
            raise MKAuthException(
                _(
                    "Sorry. In order to change the permissions of a host you need write "
                    "access to the folder it is contained in."
                )
            )

    def clear_discovery_failed(self):
        # 1. Check preconditions
        # We do not check permissions. They are checked during the discovery.
        self.need_unlocked()

        # 2. Actual modification
        self.set_discovery_failed(False)

    def set_discovery_failed(self, how=True):
        # 1. Check preconditions
        # We do not check permissions. They are checked during the discovery.
        self.need_unlocked()

        # 2. Actual modification
        if how:
            if not self._attributes.get("inventory_failed"):
                self._attributes["inventory_failed"] = True
                self.folder().save_hosts()
        else:
            if self._attributes.get("inventory_failed"):
                del self._attributes["inventory_failed"]
                self.folder().save_hosts()

    def rename_cluster_node(self, oldname, newname):
        # We must not check permissions here. Permissions
        # on the renamed host must be sufficient. If we would
        # fail here we would leave an inconsistent state
        changed = rename_host_in_list(self._cluster_nodes, oldname, newname)
        if not changed:
            return False

        add_change(
            "rename-node",
            _("Renamed cluster node from %s into %s.") % (oldname, newname),
            object_ref=self.object_ref(),
            sites=[self.site_id()],
        )
        self.folder().save_hosts()
        return True

    def rename_parent(self, oldname, newname):
        # Same is with rename_cluster_node()
        changed = rename_host_in_list(self._attributes["parents"], oldname, newname)
        if not changed:
            return False

        add_change(
            "rename-parent",
            _("Renamed parent from %s into %s.") % (oldname, newname),
            object_ref=self.object_ref(),
            sites=[self.site_id()],
        )
        self.folder().save_hosts()
        return True

    def rename(self, new_name):
        add_change(
            "rename-host",
            _("Renamed host from %s into %s.") % (self.name(), new_name),
            object_ref=self.object_ref(),
            sites=[self.site_id()],
        )
        self._name = new_name


def make_host_audit_log_object(attributes, cluster_nodes):
    """The resulting object is used for building object diffs"""
    obj = attributes.copy()
    if cluster_nodes:
        obj["nodes"] = cluster_nodes
    obj.pop("meta_data", None)
    return obj


def make_folder_audit_log_object(attributes):
    """The resulting object is used for building object diffs"""
    obj = attributes.copy()
    obj.pop("meta_data", None)
    return obj


def _validate_contact_group_modification(
    old_groups: Sequence[ContactgroupName], new_groups: Sequence[ContactgroupName]
) -> None:
    """Verifies if a user is allowed to modify the contact groups.

    A user must not be member of all groups assigned to a host/folder, but a user can only add or
    remove the contact groups if he is a member of.

    This is necessary to provide the user a consistent experience: In case he is able to add a
    group, he should also be able to remove it. And vice versa.
    """
    if diff_groups := set(old_groups) ^ set(new_groups):
        _must_be_in_contactgroups(diff_groups)


def _must_be_in_contactgroups(cgs: Iterable[ContactgroupName]) -> None:
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


# .
#   .--CME-----------------------------------------------------------------.
#   |                          ____ __  __ _____                           |
#   |                         / ___|  \/  | ____|                          |
#   |                        | |   | |\/| |  _|                            |
#   |                        | |___| |  | | |___                           |
#   |                         \____|_|  |_|_____|                          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Managed Services Edition specific things                             |
#   '----------------------------------------------------------------------'
# TODO: This has been moved directly into watolib because it was not easily possible
# to extract Folder/Host dependencies to a separate module. As soon as we have untied
# this we should re-establish a watolib plugin hierarchy and move this to a CME
# specific watolib plugin


class CMEFolder(CREFolder):
    def edit(self, new_title, new_attributes):
        if "site" in new_attributes:
            site_id = new_attributes["site"]
            parent = self.parent()
            if isinstance(parent, CMEFolder):
                parent._check_parent_customer_conflicts(site_id)
            self._check_childs_customer_conflicts(site_id)

        super().edit(new_title, new_attributes)
        self._clear_id_cache()

    def _check_parent_customer_conflicts(self, site_id):
        new_customer_id = managed.get_customer_of_site(site_id)
        customer_id = self._get_customer_id()

        if (
            new_customer_id == managed.default_customer_id()
            and customer_id != managed.default_customer_id()
        ):
            raise MKUserError(
                None,
                _(
                    "The configured target site refers to the default customer <i>%s</i>. The parent folder however, "
                    "already have the specific customer <i>%s</i> set. This violates the CME folder hierarchy."
                )
                % (
                    managed.get_customer_name_by_id(managed.default_customer_id()),
                    managed.get_customer_name_by_id(customer_id),
                ),
            )

        # The parents customer id may be the default customer or the same customer
        customer_id = self._get_customer_id()
        if customer_id not in [managed.default_customer_id(), new_customer_id]:
            folder_sites = ", ".join(list(managed.get_sites_of_customer(customer_id).keys()))
            raise MKUserError(
                None,
                _(
                    "The configured target site <i>%s</i> for this folder is invalid. The folder <i>%s</i> already belongs "
                    "to the customer <i>%s</i>. This violates the CME folder hierarchy. You may choose the "
                    "following sites <i>%s</i>."
                )
                % (
                    allsites()[site_id]["alias"],
                    self.title(),
                    managed.get_customer_name_by_id(customer_id),
                    folder_sites,
                ),
            )

    def _check_childs_customer_conflicts(self, site_id):
        customer_id = managed.get_customer_of_site(site_id)
        # Check hosts
        self._check_hosts_customer_conflicts(site_id)

        # Check subfolders
        for subfolder in (f for f in self.subfolders() if isinstance(f, CMEFolder)):
            subfolder_explicit_site = subfolder.attributes().get("site")
            if subfolder_explicit_site:
                subfolder_customer = subfolder._get_customer_id()
                if subfolder_customer != customer_id:
                    raise MKUserError(
                        None,
                        _(
                            "The subfolder <i>%s</i> has the explicit site <i>%s</i> set, which belongs to "
                            "customer <i>%s</i>. This violates the CME folder hierarchy."
                        )
                        % (
                            subfolder.title(),
                            allsites()[subfolder_explicit_site]["alias"],
                            managed.get_customer_name_by_id(subfolder_customer),
                        ),
                    )

            subfolder._check_childs_customer_conflicts(site_id)

    def _check_hosts_customer_conflicts(self, site_id):
        customer_id = managed.get_customer_of_site(site_id)
        for host in self.hosts().values():
            host_explicit_site = host.attributes().get("site")
            if host_explicit_site:
                host_customer = managed.get_customer_of_site(host_explicit_site)
                if host_customer != customer_id:
                    raise MKUserError(
                        None,
                        _(
                            "The host <i>%s</i> has the explicit site <i>%s</i> set, which belongs to "
                            "customer <i>%s</i>. This violates the CME folder hierarchy."
                        )
                        % (
                            host.name(),
                            allsites()[host_explicit_site]["alias"],
                            managed.get_customer_name_by_id(host_customer),
                        ),
                    )

    def create_subfolder(self, name, title, attributes):
        if "site" in attributes:
            self._check_parent_customer_conflicts(attributes["site"])
        return super().create_subfolder(name, title, attributes)

    def move_subfolder_to(self, subfolder, target_folder):
        target_folder_customer = target_folder._get_customer_id()
        if target_folder_customer != managed.default_customer_id():
            result_dict: Dict[str, Any] = {
                "explicit_host_sites": {},  # May be used later on to
                "explicit_folder_sites": {},  # improve error message
                "involved_customers": set(),
            }
            subfolder._determine_involved_customers(result_dict)
            other_customers = result_dict["involved_customers"] - {target_folder_customer}
            if other_customers:
                other_customers_text = ", ".join(
                    map(managed.get_customer_name_by_id, other_customers)
                )
                raise MKUserError(
                    None,
                    _(
                        "Cannot move folder. Some of its elements have specifically other customers set (<i>%s</i>). "
                        "This violates the CME folder hierarchy."
                    )
                    % other_customers_text,
                )

        # The site attribute is not explicitely set. The new inheritance might brake something..
        super().move_subfolder_to(subfolder, target_folder)

    def create_hosts(self, entries, bake_hosts=True):
        customer_id = self._get_customer_id()
        if customer_id != managed.default_customer_id():
            for hostname, attributes, _cluster_nodes in entries:
                self.check_modify_host(hostname, attributes)

        super().create_hosts(entries, bake_hosts=bake_hosts)

    def check_modify_host(self, hostname, attributes):
        if "site" not in attributes:
            return

        customer_id = self._get_customer_id()
        if customer_id != managed.default_customer_id():
            host_customer_id = managed.get_customer_of_site(attributes["site"])
            if host_customer_id != customer_id:
                folder_sites = ", ".join(managed.get_sites_of_customer(customer_id))
                raise MKUserError(
                    None,
                    _(
                        "Unable to modify host <i>%s</i>. Its site id <i>%s</i> conflicts with the customer <i>%s</i>, "
                        "which owns this folder. This violates the CME folder hierarchy. You may "
                        "choose the sites: %s"
                    )
                    % (
                        hostname,
                        allsites()[attributes["site"]]["alias"],
                        customer_id,
                        folder_sites,
                    ),
                )

    def move_hosts(self, host_names, target_folder):
        # Check if the target folder may have this host
        # A host from customerA is not allowed in a customerB folder
        target_site_id = target_folder.site_id()

        # Check if the hosts are moved to a provider folder
        target_customer_id = managed.get_customer_of_site(target_site_id)
        if target_customer_id != managed.default_customer_id():
            allowed_sites = managed.get_sites_of_customer(target_customer_id)
            for hostname in host_names:
                host = self.load_host(hostname)
                host_site = host.attributes().get("site")
                if not host_site:
                    continue
                if host_site not in allowed_sites:
                    raise MKUserError(
                        None,
                        _(
                            "Unable to move host <i>%s</i>. Its explicit set site attribute <i>%s</i> "
                            "belongs to customer <i>%s</i>. The target folder however, belongs to customer <i>%s</i>. "
                            "This violates the folder CME folder hierarchy."
                        )
                        % (
                            hostname,
                            allsites()[host_site]["alias"],
                            managed.get_customer_of_site(host_site),
                            managed.get_customer_of_site(target_site_id),
                        ),
                    )

        super().move_hosts(host_names, target_folder)

    def _get_customer_id(self):
        customer_id = managed.get_customer_of_site(self.site_id())
        return customer_id

    def _determine_involved_customers(self, result_dict):
        self._determine_explicit_set_site_ids(result_dict)
        result_dict["involved_customers"].update(
            set(map(managed.get_customer_of_site, result_dict["explicit_host_sites"].keys()))
        )
        result_dict["involved_customers"].update(
            set(map(managed.get_customer_of_site, result_dict["explicit_folder_sites"].keys()))
        )

    def _determine_explicit_set_site_ids(self, result_dict):
        for host in self.hosts().values():
            host_explicit_site = host.attributes().get("site")
            if host_explicit_site:
                result_dict["explicit_host_sites"].setdefault(host_explicit_site, []).append(
                    host.name()
                )

        for subfolder in (f for f in self.subfolders() if isinstance(f, CMEFolder)):
            subfolder_explicit_site = subfolder.attributes().get("site")
            if subfolder_explicit_site:
                result_dict["explicit_folder_sites"].setdefault(subfolder_explicit_site, []).append(
                    subfolder.title()
                )
            subfolder._determine_explicit_set_site_ids(result_dict)

        return result_dict


class CMEHost(CREHost):
    def edit(self, attributes, cluster_nodes):
        f = self.folder()
        if isinstance(f, CMEFolder):
            f.check_modify_host(self.name(), attributes)
        super().edit(attributes, cluster_nodes)


def _get_host_and_folder_class() -> Tuple[Type[CREFolder], Type[CREHost]]:
    if not cmk_version.is_managed_edition():
        return CREFolder, CREHost
    return CMEFolder, CMEHost


host_and_folder_classes = _get_host_and_folder_class()
Folder: Type[CREFolder] = host_and_folder_classes[0]
Host: Type[CREHost] = host_and_folder_classes[1]


@MemoizeCache
def folders_by_id() -> Dict[str, Type[CREFolder]]:
    """Map all reachable folders via their uuid.uuid4() id.

    This will essentially flatten all Folders into one dictionary, yet uniquely identifiable via
    their respective ids.

    Returns:
        A dictionary of uuid4 keys (hex encoded, byte-string) to Folder instances. It's
        hex-encoded because the repr() output of a string is smaller than the repr() output of the
        same byte-sequence (due to escaping characters).
    """

    # Rationale:
    #   This is pretty wasteful but should not have any loop-holes. The problem with these sorts
    #   of caches is the "identity" of the objects instantiated. Is the representation on disk or
    #   the instantiated object the source of truth? Of course, it is the file on disk,
    #   which means that we have to make sure that the state of all instances always reflect
    #   the state on disk faithfully. In order to do that, we drop the entire cache on every
    #   modification of any folder. (via folders_by_id.clear_cache(), part of lru_cache)
    #   Downside is of course a lot of wasted CPU cycles/IO on big installations, but in order to
    #   be more efficient the Folder classes need more invasive changes.
    def _update_mapping(_folder, _mapping):
        if not _folder.is_root():
            _mapping[_folder.id()] = _folder
        for _sub_folder in _folder.subfolders():
            _update_mapping(_sub_folder, _mapping)

    mapping: Dict[str, Type[CREFolder]] = SetOnceDict()
    _update_mapping(Folder.root_folder(), mapping)
    return mapping


def call_hook_hosts_changed(folder: CREFolder) -> None:
    if hooks.registered("hosts-changed"):
        hosts = _collect_hosts(folder)
        hooks.call("hosts-changed", hosts)

    # The same with all hosts!
    if hooks.registered("all-hosts-changed"):
        hosts = _collect_hosts(Folder.root_folder())
        hooks.call("all-hosts-changed", hosts)


# This hook is called in order to determine the errors of the given
# hostnames. These informations are used for displaying warning
# symbols in the host list and the host detail view
# Returns dictionary { hostname: [errors] }
def validate_all_hosts(hostnames, force_all=False):
    if hooks.registered("validate-all-hosts") and (len(hostnames) > 0 or force_all):
        hosts_errors = {}
        all_hosts = _collect_hosts(Folder.root_folder())

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


def collect_all_hosts() -> HostsWithAttributes:
    return _collect_hosts(Folder.root_folder())


def _collect_hosts(folder: CREFolder) -> HostsWithAttributes:
    hosts_attributes = {}
    for host_name, host in folder.all_hosts_recursively().items():
        hosts_attributes[host_name] = host.effective_attributes()
        hosts_attributes[host_name]["path"] = host.folder().path()
        hosts_attributes[host_name]["edit_url"] = host.edit_url()
    return hosts_attributes


def folder_preserving_link(add_vars: HTTPVariables) -> str:
    return Folder.current().url(add_vars)


def make_action_link(vars_: HTTPVariables) -> str:
    return folder_preserving_link(vars_ + [("_transid", transactions.get())])


def get_folder_title_path(path, with_links=False):
    """Return a list with all the titles of the paths'
    components, e.g. "muc/north" -> [ "Main", "Munich", "North" ]"""
    # In order to speed this up, we work with a per HTML-request cache
    cache_name = "wato_folder_titles" + (with_links and "_linked" or "")
    cache = g.setdefault(cache_name, {})
    if path not in cache:
        cache[path] = Folder.folder(path).title_path(with_links)
    return cache[path]


def get_folder_title(path: str) -> str:
    """Return the title of a folder - which is given as a string path"""
    folder = Folder.folder(path)
    if folder:
        return folder.title()
    return path


# TODO: Move to Folder()?
def check_wato_foldername(htmlvarname: Optional[str], name: str, just_name: bool = False) -> None:
    if not just_name and Folder.current().has_subfolder(name):
        raise MKUserError(htmlvarname, _("A folder with that name already exists."))

    if not name:
        raise MKUserError(htmlvarname, _("Please specify a name."))

    if not regex(WATO_FOLDER_PATH_NAME_REGEX).match(name):
        raise MKUserError(
            htmlvarname,
            _("Invalid folder name. Only the characters a-z, A-Z, 0-9, _ and - are allowed."),
        )


def _ensure_trailing_slash(path: str) -> str:
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


class MatchItemGeneratorHosts(ABCMatchItemGenerator):
    def __init__(
        self,
        name: str,
        host_collector: Callable[[], HostsWithAttributes],
    ) -> None:
        super().__init__(name)
        self._host_collector = host_collector

    @staticmethod
    def _get_additional_match_texts(host_attributes: HostAttributes) -> Iterable[str]:
        yield from (
            val
            for key in ["alias", "ipaddress", "ipv6address"]
            for val in [host_attributes[key]]
            if val
        )
        yield from (
            ip_address
            for key in ["additional_ipv4addresses", "additional_ipv6addresses"]
            for ip_address in host_attributes[key]
        )

    def generate_match_items(self) -> MatchItems:
        yield from (
            MatchItem(
                title=host_name,
                topic=_("Hosts"),
                url=host_attributes["edit_url"],
                match_texts=[
                    host_name,
                    *self._get_additional_match_texts(host_attributes),
                ],
            )
            for host_name, host_attributes in self._host_collector().items()
        )

    @staticmethod
    def is_affected_by_change(change_action_name: str) -> bool:
        return "host" in change_action_name

    @property
    def is_localization_dependent(self) -> bool:
        return False


match_item_generator_registry.register(
    MatchItemGeneratorHosts(
        "hosts",
        collect_all_hosts,
    )
)
