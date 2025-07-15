#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import marshal
import os
import time
from collections.abc import Mapping
from pathlib import Path

from livestatus import LivestatusResponse, Query, QuerySpecification

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId

from cmk.bi.filesystem import BIFileSystem
from cmk.bi.lib import (
    ABCBIStatusFetcher,
    BIHostData,
    BIHostSpec,
    BIHostStatusInfoRow,
    BIServiceData,
    BIServiceWithFullState,
    BIStatusInfo,
    RequiredBIElement,
    SitesCallback,
)
from cmk.bi.trees import BICompiledAggregation, BICompiledRule

SiteProgramStart = tuple[SiteId, int]


# Livestatus delivers strings with incorrectly encoded special characters
# (e.g. emoticons) if JSON output format is used
# This function fixes the encoding for such strings
def fix_encoding(value: str) -> str:
    return value.encode("utf-16", "surrogatepass").decode("utf-16")


#   .--Defines-------------------------------------------------------------.
#   |                  ____        __ _                                    |
#   |                 |  _ \  ___ / _(_)_ __   ___  ___                    |
#   |                 | | | |/ _ \ |_| | '_ \ / _ \/ __|                   |
#   |                 | |_| |  __/  _| | | | |  __/\__ \                   |
#   |                 |____/ \___|_| |_|_| |_|\___||___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# Structure data used by bi_compiler

#   .--BIStructure Fetcher-------------------------------------------------.
#   |        ____ ___ ____  _                   _                          |
#   |       | __ )_ _/ ___|| |_ _ __ _   _  ___| |_ _   _ _ __ ___         |
#   |       |  _ \| |\___ \| __| '__| | | |/ __| __| | | | '__/ _ \        |
#   |       | |_) | | ___) | |_| |  | |_| | (__| |_| |_| | | |  __/        |
#   |       |____/___|____/ \__|_|   \__,_|\___|\__|\__,_|_|  \___|        |
#   |                                                                      |
#   |                  _____    _       _                                  |
#   |                 |  ___|__| |_ ___| |__   ___ _ __                    |
#   |                 | |_ / _ \ __/ __| '_ \ / _ \ '__|                   |
#   |                 |  _|  __/ || (__| | | |  __/ |                      |
#   |                 |_|  \___|\__\___|_| |_|\___|_|                      |
#   |                                                                      |
#   +----------------------------------------------------------------------+


class BIStructureFetcher:
    def __init__(self, sites_callback: SitesCallback, fs: BIFileSystem) -> None:
        self.sites_callback = sites_callback
        # The key may be a pattern / regex, so `str` is the correct type for the key.
        self._hosts: dict[str, BIHostData] = {}
        self._have_sites: set[SiteId] = set()
        self._fs = fs

    def cleanup(self) -> None:
        self._have_sites.clear()
        self._hosts.clear()

    @property
    def hosts(self) -> dict[str, BIHostData]:
        return self._hosts

    def get_cached_program_starts(self) -> set[SiteProgramStart]:
        return {
            (site_id, timestamp)
            for _path_object, (site_id, timestamp) in self._get_site_data_files()
        }

    def update_data(self, required_program_starts: set[SiteProgramStart]) -> None:
        if missing_program_starts := required_program_starts - self.get_cached_program_starts():
            self._fetch_missing_data(missing_program_starts)

        self._read_cached_data(required_program_starts)

    def _fetch_missing_data(self, missing_program_starts: set) -> None:
        only_sites = {kv[0]: kv[1] for kv in missing_program_starts}

        # Start two queries: GET hosts / GET services
        # Most of the columns are available via the hosts table
        # Querying the service tables provides additional info like service_tags/service_labels
        # If something happens (reload config) between the host and service query, we simply ignore it
        host_query = Query(
            QuerySpecification("hosts", self._host_structure_columns(), "Cache: reload")
        )
        host_rows = self.sites_callback.query(
            host_query,
            list(only_sites.keys()),
            fetch_full_data=True,
        )

        service_query = Query(
            QuerySpecification("services", self._service_structure_columns(), "Cache: reload")
        )
        host_service_lookup: dict[HostName, list] = {}
        for row in self.sites_callback.query(
            service_query,
            list(only_sites.keys()),
            fetch_full_data=True,
        ):
            description, tags, labels = row[2:]
            host_service_lookup.setdefault(row[1], []).append(
                [
                    fix_encoding(description),
                    tags,
                    {fix_encoding(k): fix_encoding(v) for k, v in labels.items()},
                ]
            )

        site_data: dict[SiteId, dict] = {x: {} for x in only_sites}
        for (
            site,
            host_name,
            host_tags,
            host_labels,
            host_childs,
            host_parents,
            host_alias,
            host_filename,
        ) in host_rows:
            services = {
                description: (set(tags), labels)
                for description, tags, labels in host_service_lookup.get(host_name, [])
            }

            # This data will be serialized to disc
            # Named tuples/dicts will be used later on when the data gets processed

            # Remove hosts.mk suffix
            cleaned_host_filename = (
                host_filename[:-8] if host_filename.endswith("/hosts.mk") else host_filename
            )
            # Remove /wato prefix
            cleaned_host_filename = (
                cleaned_host_filename[6:]
                if cleaned_host_filename.startswith("/wato")
                else cleaned_host_filename
            )

            site_data[site][host_name] = (
                site,
                set(host_tags.items()),
                {fix_encoding(k): fix_encoding(v) for k, v in host_labels.items()},
                cleaned_host_filename,
                services,
                tuple(host_childs),
                tuple(host_parents),
                fix_encoding(host_alias),
                host_name,
            )

        for site_id, hosts in site_data.items():
            self.add_site_data(site_id, hosts)
            path = self._fs.cache.get_site_structure_data_path(site_id, only_sites[site_id])
            self._marshal_save_data(path, hosts)

    def _read_cached_data(self, required_program_starts: set[SiteProgramStart]) -> None:
        required_sites = {x[0] for x in required_program_starts}
        for path_object, (site_id, _timestamp) in self._get_site_data_files():
            if site_id in self._have_sites:
                # This data was already read during the live query
                continue

            if site_id not in required_sites:
                # The data for this site is no longer required
                # The site probably got disabled in the distributed monitoring page
                continue

            site_data = self._marshal_load_data(path_object)
            self.add_site_data(site_id, site_data)

    @classmethod
    def _host_structure_columns(cls) -> list[str]:
        return [
            "host_name",
            "host_tags",
            "host_labels",
            "host_childs",
            "host_parents",
            "host_alias",
            "host_filename",
        ]

    @classmethod
    def _service_structure_columns(cls) -> list[str]:
        return ["host_name", "description", "tags", "labels"]

    def add_site_data(self, site_id: SiteId, hosts: Mapping[HostName, tuple]) -> None:
        # BIHostData
        # ("site_id", str),
        # ("tags", set[tuple[TagGroupID, TagID]]),
        # ("labels", set),
        # ("folder", str),
        # ("services", dict[str, BIServiceData]),
        # ("children", tuple),
        # ("parents", tuple),
        # ("alias", str),
        # ("name", str),

        for host_name, values in hosts.items():
            site_id, tags, labels, folder, services, children, parents, alias, name = values
            self._hosts[host_name] = BIHostData(
                site_id,
                tags,
                labels,
                folder,
                {x: BIServiceData(*y) for x, y in services.items()},
                children,
                parents,
                alias,
                name,
            )

        self._have_sites.add(site_id)

    def cleanup_orphaned_files(self, known_sites: Mapping[SiteId, int]) -> None:
        for path_object, (site_id, timestamp) in self._get_site_data_files():
            try:
                if known_sites.get(site_id) == timestamp:
                    # Data still valid
                    continue

                # Delete obsolete data files older than 5 minutes
                if time.time() - path_object.stat().st_mtime > 300:
                    path_object.unlink(missing_ok=True)
            except (IndexError, OSError, ValueError):
                path_object.unlink(missing_ok=True)

    def _get_site_data_files(self) -> list[tuple[Path, SiteProgramStart]]:
        data_files = []
        for path_object in self._fs.cache.site_structure_data.iterdir():
            if path_object.is_dir():
                continue

            if not self._fs.cache.is_site_cache(path_object):
                continue

            try:
                _prefix, site_id, timestamp = path_object.name.split(".", 2)
            except ValueError:
                path_object.unlink(missing_ok=True)
                continue

            data_files.append((path_object, (SiteId(site_id), int(timestamp))))
        return data_files

    def _marshal_save_data(self, filepath: Path, data: dict) -> None:
        with open(filepath, "wb") as f:
            marshal.dump(data, f)
            os.fsync(f.fileno())

    def _marshal_load_data(self, filepath: Path) -> dict:
        with open(filepath, "rb") as f:
            return marshal.load(f)  # nosec B302 # BNS:ccacbd


#   .--BIState Fetcher-----------------------------------------------------.
#   | ____ ___ ____  _        _         _____    _       _                 |
#   || __ )_ _/ ___|| |_ __ _| |_ ___  |  ___|__| |_ ___| |__   ___ _ __   |
#   ||  _ \| |\___ \| __/ _` | __/ _ \ | |_ / _ \ __/ __| '_ \ / _ \ '__|  |
#   || |_) | | ___) | || (_| | ||  __/ |  _|  __/ || (__| | | |  __/ |     |
#   ||____/___|____/ \__\__,_|\__\___| |_|  \___|\__\___|_| |_|\___|_|     |
#   |                                                                      |
#   +----------------------------------------------------------------------+


class BIStatusFetcher(ABCBIStatusFetcher):
    def set_assumed_states(self, assumed_states: dict) -> None:
        # Streamline format to site, host, service (may be None)
        self.assumed_states = {}
        for key, state in assumed_states.items():
            if len(key) == 2:
                self.assumed_states[key + (None,)] = state
            else:
                self.assumed_states[key] = state

    def update_states(self, required_elements: set[RequiredBIElement]) -> None:
        self.states = self._get_status_info(required_elements)

    def update_states_filtered(
        self,
        filter_header: str,
        only_sites: list[SiteId] | None,
        limit: int | None,
        host_columns: list,
        bygroup: bool,
        required_aggregations: list[tuple[BICompiledAggregation, list[BICompiledRule]]],
    ) -> None:
        self.states = self._get_status_info_filtered(
            filter_header, only_sites, limit, host_columns, bygroup, required_aggregations
        )

    def cleanup(self) -> None:
        self.states.clear()
        self.assumed_states.clear()

    # Get all status information for the required_hosts
    def _get_status_info(self, required_elements: set[RequiredBIElement]) -> BIStatusInfo:
        if not required_elements:
            # There is no reason to start a query if no elements are required
            # Even worse, without any required_elements the query would have no filter restrictions
            # and return all hosts
            return {}

        # Query each site only for hosts that that site provides
        req_hosts: set[HostName] = set()
        req_sites: set[SiteId] = set()

        for site, host, _service in required_elements:
            req_hosts.add(host)
            req_sites.add(site)

        # TODO: the cmc slows down if the host filter gets too big
        #       fetch all hosts if the filter exceeds 1000 hosts
        host_filter = "".join(f"Filter: name = {host}\n" for host in req_hosts)
        if len(req_hosts) > 1:
            host_filter += f"Or: {len(req_hosts)}\n"

        query = Query(QuerySpecification("hosts", self.get_status_columns(), host_filter))
        return self.create_bi_status_data(self.sites_callback.query(query, list(req_sites)))

    # This variant of the function is configured not with a list of
    # hosts but with a livestatus filter header and a list of columns
    # that need to be fetched in any case
    def _get_status_info_filtered(
        self,
        filter_header: str,
        only_sites: list[SiteId] | None,
        limit: int | None,
        host_columns: list,
        bygroup: bool,
        required_aggregations: list[tuple[BICompiledAggregation, list[BICompiledRule]]],
    ) -> BIStatusInfo:
        table = "hostsbygroup" if bygroup else "hosts"

        columns = self.get_status_columns() + host_columns
        query = Query(QuerySpecification(table, columns, filter_header))
        data = self.sites_callback.query(query, only_sites)

        # Now determine aggregation branches which include the site hosts
        site_hosts = {BIHostSpec(row[0], row[1]) for row in data}
        required_hosts = set()
        for _compiled_aggregation, branches in required_aggregations:
            for branch in branches:
                branch_hosts = branch.get_required_hosts()
                if branch_hosts.intersection(site_hosts):
                    required_hosts.update(branch_hosts)

        missing_hosts = required_hosts - site_hosts

        # Restrict hosts with only sites, maybe someone want to see a subtree..
        remaining_hosts: set[BIHostSpec] = set()
        if only_sites:
            for site_id, host_name in missing_hosts:
                if site_id in only_sites:
                    remaining_hosts.add(BIHostSpec(site_id, host_name))
        else:
            remaining_hosts = missing_hosts

        if remaining_hosts:
            remaining_sites = set()
            host_filter = ""
            for site_id, host in remaining_hosts:
                remaining_sites.add(site_id)
                host_filter += "Filter: name = %s\n" % host
            if len(remaining_hosts) > 1:
                host_filter += "Or: %d\n" % len(remaining_hosts)

            query = Query(QuerySpecification(table, columns, host_filter))
            data.extend(self.sites_callback.query(query, list(remaining_sites)))

        return self.create_bi_status_data(data, extra_columns=host_columns)

    @classmethod
    def create_bi_status_data(
        cls, rows: LivestatusResponse, extra_columns: list[str] | None = None
    ) -> BIStatusInfo:
        response = {}
        bi_data_end = len(cls.get_status_columns())
        idx_svc_full_state = cls.get_index_services_with_fullstate()
        for row in rows:
            # Convert services_with_fullstate to dict
            services_with_fullstate = {
                fix_encoding(e[0]): BIServiceWithFullState(e[1], e[2], fix_encoding(e[3]), *e[4:])
                for e in row[idx_svc_full_state]
            }
            remaining_row_keys = {}
            if extra_columns:
                remaining_row_keys = dict(zip(extra_columns, row[-len(extra_columns) :]))

            args = row[2:bi_data_end] + [services_with_fullstate] + [remaining_row_keys]
            response[BIHostSpec(row[0], row[1])] = BIHostStatusInfoRow(*args)
        return response

    @classmethod
    def get_index_services_with_fullstate(cls) -> int:
        return cls.get_status_columns().index("services_with_fullstate") + 1

    @classmethod
    def get_status_columns(cls) -> list[str]:
        return [
            "name",
            "state",
            "has_been_checked",
            "hard_state",
            "plugin_output",
            "scheduled_downtime_depth",
            "in_service_period",
            "acknowledged",
            "services_with_fullstate",
        ]
