#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pprint
import re
from ast import literal_eval
from collections.abc import Iterator
from logging import Logger
from pathlib import Path
from typing import NamedTuple, override

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.site import omd_site, SiteId

import cmk.utils.paths

from cmk.gui.config import active_config
from cmk.gui.i18n import _
from cmk.gui.session import SuperUserContext
from cmk.gui.site_config import is_wato_slave_site
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree

from cmk.update_config.registry import update_action_registry, UpdateAction


class ParentsMKResult(NamedTuple):
    all_hosts: list[str]
    ipaddresses: dict[str, str]
    parents: dict[str, list[str]]


class MigrateParentsMK(UpdateAction):
    _data_pattern = re.compile(
        r"(?:all_hosts \+= (.*)$)|(?:ipaddresses\.update\((.*?)\))|(?:parents \+= (.*?)$)"
    )

    @override
    def __call__(self, logger: Logger) -> None:
        results: dict[Path, ParentsMKResult] = {}
        for path in cmk.utils.paths.check_mk_config_dir.glob("*.mk"):
            with open(path) as f:
                first_line = f.readline()
                if not first_line.startswith("# Automatically created by --scan-parents at"):
                    continue

                try:
                    results[path] = self._parse_data(f)
                except (
                    ValueError,  # Following: ast.literal_eval
                    TypeError,
                    SyntaxError,
                    MemoryError,
                    RecursionError,
                    AssertionError,  # Validation assertions
                ) as ex:
                    logger.warning(
                        f"Could not parse parents.mk file {path}, skipping.", exc_info=ex
                    )
                    continue

        for path in results:
            self._deactivate_mk(path)

        if not any(result.parents for result in results.values()):
            return

        if is_wato_slave_site():
            unconfigured_children = {
                child_host for result in results.values() for child_host in result.parents
            }
            logger.warning(
                "Cannot migrate parent scan configurations on a remote site. "
                "See Werk #16825 for more information. "
                "The following hosts might not have their parents configured as expected: "
                f"{pprint.pformat(unconfigured_children)}"
            )
            return

        try:
            central_site_id = omd_site()

            with SuperUserContext():
                root = folder_tree().root_folder()
                if root.has_subfolder("parents"):
                    parents_folder = root.subfolder("migrated_parents")
                    assert parents_folder is not None
                else:
                    parents_folder = root.create_subfolder(
                        "migrated_parents",
                        _("Migrated Parents"),
                        {},
                        pprint_value=active_config.wato_pprint_config,
                    )

                for result in results.values():
                    self._configure_parents(result, parents_folder, central_site_id)
        except Exception as ex:
            for path in results:
                self._reactivate_mk(path)
            raise ex

    def _parse_data(self, string_iter: Iterator[str]) -> ParentsMKResult:
        all_hosts: list[str] | None = None
        ipaddresses: dict[str, str] | None = None
        parents: dict[str, list[str]] | None = None
        for line in string_iter:
            if matches := self._data_pattern.findall(line):
                host_str, ip_str, parents_str = matches[0]
                if host_str:
                    all_hosts = literal_eval(host_str)
                    assert isinstance(all_hosts, list)
                    assert all(isinstance(host, str) for host in all_hosts)
                    all_hosts = [host.removesuffix("|parent|ping") for host in all_hosts]
                if ip_str:
                    ipaddresses = literal_eval(ip_str)
                if parents_str:
                    parents_old = literal_eval(parents_str)
                    # Reformat from [(parent_host1, [child_host1, child_host2, ...]), ...]
                    # to [(child_host1, [parent_host1, ...]), ...]
                    parents = {}
                    for parent_host, children in parents_old:
                        for child_host in children:
                            parents.setdefault(child_host, []).append(parent_host)
        assert isinstance(all_hosts, list)
        assert isinstance(ipaddresses, dict)
        assert isinstance(parents, dict)
        assert all(host in ipaddresses for host in all_hosts)
        return ParentsMKResult(all_hosts, ipaddresses, parents)

    def _configure_parents(
        self, result: ParentsMKResult, parents_folder: Folder, central_site_id: SiteId
    ) -> None:
        self._create_all_parents(result, parents_folder, central_site_id)
        self._assign_parents(result)

    def _create_all_parents(
        self, result: ParentsMKResult, parents_folder: Folder, central_site_id: SiteId
    ) -> None:
        tree = folder_tree()
        tree.invalidate_caches()
        root = tree.root_folder()
        existing_hosts = root.all_hosts_recursively()

        for host_name_str in result.all_hosts:
            host_name = HostName(host_name_str)
            if host_name not in existing_hosts:
                attributes = self._determine_attributes(
                    result.ipaddresses[host_name_str], central_site_id
                )
                parents_folder.create_hosts(
                    [(host_name, attributes, None)], pprint_value=active_config.wato_pprint_config
                )

    def _assign_parents(self, result: ParentsMKResult) -> None:
        tree = folder_tree()
        tree.invalidate_caches()
        root = tree.root_folder()
        hosts = root.all_hosts_recursively()

        for child_host_name, parents in result.parents.items():
            if (child_host := hosts.get(HostName(child_host_name))) is not None:
                child_host.update_attributes(
                    {"parents": [HostAddress(parent) for parent in parents]},
                    pprint_value=active_config.wato_pprint_config,
                )

    def _deactivate_mk(self, path: Path) -> None:
        path.rename(path.with_suffix(".mk_inactive"))

    def _reactivate_mk(self, path: Path) -> None:
        path.with_suffix(".mk_inactive").rename(path)

    def _determine_attributes(
        self,
        ipaddress: str,
        site_id: SiteId,
    ) -> HostAttributes:
        return HostAttributes(
            {
                "ipaddress": HostAddress(ipaddress),
                "alias": "Created by parent scan",
                "site": site_id,
                "tag_agent": "no-agent",
                "tag_snmp_ds": "no-snmp",
            }
        )


update_action_registry.register(
    MigrateParentsMK(
        name="migrate_parent_scan_config", title="Migrate CLI parent scan config", sort_index=40
    )
)
