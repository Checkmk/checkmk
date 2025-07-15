#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import os
import time
from multiprocessing.pool import Pool
from pathlib import Path
from typing import TypedDict

import psutil
from redis import Redis

from livestatus import Query, QuerySpecification

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.i18n import _

from cmk.utils.log import logger
from cmk.utils.redis import get_redis_client

from cmk.bi import storage
from cmk.bi.aggregation import BIAggregation
from cmk.bi.data_fetcher import BIStructureFetcher, SiteProgramStart
from cmk.bi.filesystem import BIFileSystem, get_default_site_filesystem
from cmk.bi.lib import SitesCallback
from cmk.bi.packs import BIAggregationPacks
from cmk.bi.searcher import BISearcher
from cmk.bi.trees import BICompiledAggregation, BICompiledRule, FrozenBIInfo

_LOGGER = logger.getChild("web.bi.compilation")
_MAX_MULTIPROCESSING_POOL_SIZE = 8
_AVAILABLE_MEMORY_RATIO = 0.75


class ConfigStatus(TypedDict):
    configfile_timestamp: float
    known_sites: set[SiteProgramStart]
    online_sites: set[SiteProgramStart]


class BICompiler:
    def __init__(
        self,
        bi_configuration_file: Path,
        sites_callback: SitesCallback,
        fs: BIFileSystem | None = None,
        redis_client: Redis[str] | None = None,
    ) -> None:
        self._sites_callback = sites_callback
        self._fs = fs or get_default_site_filesystem()

        self._compiled_aggregations: dict[str, BICompiledAggregation] = {}

        self._aggregation_store = storage.AggregationStore(self._fs.cache)
        self._metadata_store = storage.MetadataStore(self._fs)
        self._frozen_store = storage.FrozenAggregationStore(self._fs.var)
        self._lookup_store = storage.LookupStore(redis_client or get_redis_client())

        self._bi_packs = BIAggregationPacks(bi_configuration_file)
        self._bi_structure_fetcher = BIStructureFetcher(self._sites_callback, self._fs)
        self.bi_searcher = BISearcher()

    @property
    def compiled_aggregations(self) -> dict[str, BICompiledAggregation]:
        return self._compiled_aggregations

    def get_aggregation_by_name(
        self, aggr_name: str
    ) -> tuple[BICompiledAggregation, BICompiledRule] | None:
        for _name, compiled_aggregation in self._compiled_aggregations.items():
            for branch in compiled_aggregation.branches:
                if branch.properties.title == aggr_name:
                    return compiled_aggregation, branch
        return None

    def load_compiled_aggregations(self) -> None:
        try:
            self._check_compilation_status()
        finally:
            self._load_compiled_aggregations()

    def get_frozen_aggr_id(self, frozen_info: FrozenBIInfo) -> str:
        return f"frozen_{frozen_info.based_on_aggregation_id}_{frozen_info.based_on_branch_title}"

    def _freeze_new_branches(self, compiled_aggregation: BICompiledAggregation) -> bool:
        new_branch_found = False
        for branch in list(compiled_aggregation.branches):
            if self._frozen_store.exists(compiled_aggregation.id, branch.properties.title):
                continue
            new_branch_found = True
            self.freeze_branch(branch.properties.title)
        return new_branch_found

    def freeze_branch(self, branch_name: str) -> None:
        # Creates a frozen aggregation in the frozen_aggregations_dir
        # And an additional hint-file in an aggregation sub-folder, so that we know
        # where the frozen aggregation branch initially came from

        result = self.get_aggregation_by_name(aggr_name=branch_name)
        if not result:
            raise MKGeneralException(f"Unknown aggregation {branch_name}")
        aggregation, branch = result

        # Prepare a single frozen configuration specifically for this branch
        # This includes the aggregation configuration and the frozen branch
        if frozen_info := aggregation.frozen_info:
            aggr_id = frozen_info.based_on_aggregation_id
        else:
            aggr_id = aggregation.id

        original_branches = aggregation.branches
        original_id = aggregation.id
        try:
            aggregation.branches = [branch]
            aggregation.id = self.get_frozen_aggr_id(FrozenBIInfo(aggr_id, branch_name))
            self._frozen_store.save(aggregation, aggr_id, branch_name)
        finally:
            aggregation.branches = original_branches
            aggregation.id = original_id

    def _manage_frozen_branches(
        self, compiled_aggregations: dict[str, BICompiledAggregation]
    ) -> dict[str, BICompiledAggregation]:
        updated_aggregations = {}

        computed_new_frozen_branch = False
        for aggr_id, compiled_aggregation in compiled_aggregations.items():
            updated_aggregations[aggr_id] = compiled_aggregation
            if compiled_aggregation.frozen_info is not None:
                # Already frozen
                continue

            if not compiled_aggregation.computation_options.freeze_aggregations:
                self._frozen_store.delete(aggr_id)
                continue

            computed_new_frozen_branch = (
                self._freeze_new_branches(compiled_aggregation) or computed_new_frozen_branch
            )

            # Read frozen branches. Each branch gets a separate aggregation ID since
            # the computation time may differ, which also means possibly changed computation options
            for branch in list(compiled_aggregation.branches):
                branch_title = branch.properties.title
                if frozen_agg := self._frozen_store.get(compiled_aggregation.id, branch_title):
                    frozen_agg.frozen_info = FrozenBIInfo(compiled_aggregation.id, branch_title)
                    updated_aggregations[frozen_agg.id] = frozen_agg

            # Remove all branches from the original aggregation, since all of them are now frozen
            compiled_aggregation.branches = []

        if computed_new_frozen_branch:
            self._lookup_store.generate_aggregation_lookups(updated_aggregations)

        return updated_aggregations

    def _get_currently_loaded_aggregation_identifiers(self) -> set[storage.Identifier]:
        return {storage.generate_identifier(id_) for id_ in self._compiled_aggregations.keys()}

    def _get_vanished_aggregation_identifiers(self) -> set[storage.Identifier]:
        stored_identifiers = set(self._aggregation_store.yield_stored_identifiers())
        loaded_identifiers = self._get_currently_loaded_aggregation_identifiers()
        return stored_identifiers - loaded_identifiers

    def _load_compiled_aggregations(self) -> None:
        for identifier in self._get_vanished_aggregation_identifiers():
            aggregation = self._aggregation_store.get_by_identifier(identifier)
            _LOGGER.debug("Loaded cached aggregation result: %s", aggregation.id)
            self._compiled_aggregations[aggregation.id] = aggregation

        self._compiled_aggregations = self._manage_frozen_branches(self._compiled_aggregations)

    def _check_compilation_status(self) -> None:
        current_configstatus = self.compute_current_configstatus()
        if not self._compilation_required(current_configstatus):
            _LOGGER.debug("No compilation required.")
            return

        with store.locked(self._fs.cache.compilation_lock):
            # Re-check compilation required after lock has been required
            # Another apache might have done the job
            current_configstatus = self.compute_current_configstatus()
            if not self._compilation_required(current_configstatus):
                _LOGGER.debug("No compilation required. Another process already compiled it.")
                return

            self.prepare_for_compilation(current_configstatus["online_sites"])

            if aggregations := self._bi_packs.get_all_aggregations():
                with self._get_multiprocessing_pool(len(aggregations)) as pool:
                    compiled_aggregations = pool.imap_unordered(_process_compilation, aggregations)
                    for compiled_aggregation in compiled_aggregations:
                        self._compiled_aggregations[compiled_aggregation.id] = compiled_aggregation

            self._verify_aggregation_title_uniqueness(self._compiled_aggregations)

            for compiled_aggregation in self._compiled_aggregations.values():
                self._store_compiled_aggregation(compiled_aggregation)

            self._compiled_aggregations = self._manage_frozen_branches(self._compiled_aggregations)
            self._lookup_store.generate_aggregation_lookups(self._compiled_aggregations)

        known_sites = {kv[0]: kv[1] for kv in current_configstatus.get("known_sites", set())}
        self._cleanup_vanished_aggregations()
        self._bi_structure_fetcher.cleanup_orphaned_files(known_sites)
        self._metadata_store.update_last_compilation(current_configstatus["configfile_timestamp"])

    def _get_multiprocessing_pool(self, aggregation_count: int) -> Pool:
        # HACK: due to known constraints with multiprocessing in Python, this is a simple way to
        # "inject" the BI searcher dependency to our separate processes. An alternative approach
        # would be to move this object to a global variable. However, we prefer the attribute based
        # approach on the process function as it better encapsulates the logic. The underlying issue
        # has to do with the implicit pickling of all objects in process function which is slow and
        # sometimes fails when the object isn't "pickleable".
        def initializer(function) -> None:  # type: ignore[no-untyped-def]
            function.searcher = self.bi_searcher

        return Pool(
            processes=_get_multiprocessing_pool_size(aggregation_count),
            initializer=initializer,
            initargs=(_process_compilation,),
        )

    def _store_compiled_aggregation(self, compiled_aggregation: BICompiledAggregation) -> None:
        start = time.perf_counter()
        self._aggregation_store.save(compiled_aggregation)
        end = time.perf_counter()
        _LOGGER.debug(
            "Schema dump of %s (%d branches) took: %fs"
            % (compiled_aggregation.id, len(compiled_aggregation.branches), end - start)
        )

    def _cleanup_vanished_aggregations(self) -> None:
        for identifier in self._get_vanished_aggregation_identifiers():
            self._aggregation_store.delete_by_identifier(identifier)
            self._frozen_store.delete_by_identifier(identifier)

    def _verify_aggregation_title_uniqueness(
        self, compiled_aggregations: dict[str, BICompiledAggregation]
    ) -> None:
        used_titles: dict[str, str] = {}
        for aggr_id, bi_aggregation in compiled_aggregations.items():
            for bi_branch in bi_aggregation.branches:
                branch_title = bi_branch.properties.title
                if branch_title in used_titles:
                    raise MKGeneralException(
                        _(
                            'The aggregation titles are not unique. "%s" is created '
                            "by aggregation <b>%s</b> and <b>%s</b>"
                        )
                        % (branch_title, aggr_id, used_titles[branch_title])
                    )
                used_titles[branch_title] = aggr_id

    def prepare_for_compilation(self, online_sites: set[SiteProgramStart]) -> None:
        self._bi_packs.load_config()
        self._bi_structure_fetcher.update_data(online_sites)
        self.bi_searcher.set_hosts(self._bi_structure_fetcher.hosts)

    def compile_aggregation_result(self, aggr_id: str, title: str) -> BICompiledAggregation | None:
        """Allows to compile a single aggregation with a given title. Does not save any results to disk"""
        current_configstatus = self.compute_current_configstatus()
        self.prepare_for_compilation(current_configstatus["online_sites"])
        aggregation = self._bi_packs.get_aggregation(aggr_id)
        if not aggregation:
            return None

        try:
            aggregation.node.restrict_rule_title = title
            return aggregation.compile(self.bi_searcher)
        finally:
            aggregation.node.restrict_rule_title = None

    def _compilation_required(self, current_configstatus: ConfigStatus) -> bool:
        # Check monitoring core changes
        if self._site_status_changed(current_configstatus["online_sites"]):
            return True

        # Check BI configuration changes
        last_compilation = self._metadata_store.get_last_compilation()
        return current_configstatus["configfile_timestamp"] > last_compilation

    def _site_status_changed(self, required_program_starts: set[SiteProgramStart]) -> bool:
        # The cached data may include more data than the currently required_program_starts
        # Empty branches are simply not shown during computation
        cached_program_starts = self._bi_structure_fetcher.get_cached_program_starts()
        return len(required_program_starts - cached_program_starts) > 0

    def compute_current_configstatus(self) -> ConfigStatus:
        current_configstatus: ConfigStatus = {
            "configfile_timestamp": self._metadata_store.get_last_config_change(),
            "online_sites": set(),
            "known_sites": set(),
        }

        # The get status message also checks if the remote site is still alive
        result = self._sites_callback.query(
            Query(QuerySpecification("status", ["program_start"], "Cache: reload"))
        )
        program_start_times = {row[0]: int(row[1]) for row in result}

        for site_id, site_is_online in self._sites_callback.all_sites_with_id_and_online():
            start_time = program_start_times.get(site_id, 0)
            current_configstatus["known_sites"].add((site_id, start_time))
            if site_is_online:
                current_configstatus["online_sites"].add((site_id, start_time))

        return current_configstatus

    def is_part_of_aggregation(self, host_name: str, service_description: str) -> bool:
        if not self._lookup_store.base_lookup_key_exists():
            # The following scenario only happens if the redis daemon loses its data
            # In the normal workflow the lookup cache is updated after the compilation phase
            # What happens if multiple apache process want to read the cache at the same time:
            # - One apache gets the lock, updates the cache
            # - The other apache wait till the cache has been updated
            with self._lookup_store.get_aggregation_lookup_lock():
                self.load_compiled_aggregations()
                self._lookup_store.generate_aggregation_lookups(self._compiled_aggregations)

        return self._lookup_store.aggregation_lookup_exists(host_name, service_description)


def _get_multiprocessing_pool_size(aggregation_count: int) -> int:
    current_process = psutil.Process(os.getpid())

    available_memory = _AVAILABLE_MEMORY_RATIO * psutil.virtual_memory().available
    current_process_memory = current_process.memory_info().rss
    potential_pool_size = int(available_memory // current_process_memory)

    return min(potential_pool_size, _MAX_MULTIPROCESSING_POOL_SIZE, aggregation_count)


def _process_compilation(aggregation: BIAggregation) -> BICompiledAggregation:
    start = time.perf_counter()
    compiled_aggregation = aggregation.compile(_process_compilation.searcher)  # type: ignore[attr-defined]
    end = time.perf_counter()
    _LOGGER.debug("Compilation of %s took: %fs", aggregation.id, end - start)
    return compiled_aggregation
