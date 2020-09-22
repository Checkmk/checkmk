#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import time
import cmk
import pprint
from pathlib import Path
from typing import (
    Dict,
    Set,
    Optional,
    TypedDict,
    Tuple,
    List,
)

from cmk.utils.log import logger
from cmk.utils.bi.bi_packs import BIAggregationPacks
from cmk.utils.bi.bi_searcher import BISearcher
from cmk.utils.bi.bi_data_fetcher import (
    BIStructureFetcher,
    get_cache_dir,
    SiteProgramStart,
)

import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException

from cmk.utils.i18n import _
from cmk.utils.bi.bi_trees import BICompiledAggregation, BICompiledAggregationSchema
from cmk.utils.bi.bi_aggregation import BIAggregation
from cmk.utils.type_defs import HostName, ServiceName
from cmk.utils.bi.bi_lib import SitesCallback


class ConfigStatus(TypedDict):
    configfile_timestamp: float
    known_sites: Set[SiteProgramStart]
    online_sites: Set[SiteProgramStart]


class BICompiler:
    def __init__(self, bi_configuration_file, sites_callback: SitesCallback):
        self._sites_callback = sites_callback
        self._bi_configuration_file = bi_configuration_file

        self._logger = logger.getChild("bi.compiler")
        self._compiled_aggregations: Dict[str, BICompiledAggregation] = {}
        self._path_compilation_lock = Path(get_cache_dir(), "compilation.LOCK")
        self._path_compilation_timestamp = Path(get_cache_dir(), "last_compilation")
        self._path_compiled_aggregations = Path(get_cache_dir(), "compiled_aggregations")
        self._path_compiled_aggregations.mkdir(parents=True, exist_ok=True)
        self._part_of_aggregation_map: Dict[Tuple[HostName, Optional[ServiceName]],
                                            List[Tuple[str, str]]] = {}

        self._setup()

    def _setup(self):
        self._bi_packs = BIAggregationPacks(self._bi_configuration_file)
        self._bi_structure_fetcher = BIStructureFetcher(self._sites_callback)
        self.bi_searcher = BISearcher()

    @property
    def compiled_aggregations(self) -> Dict[str, BICompiledAggregation]:
        return self._compiled_aggregations

    def cleanup(self) -> None:
        self._compiled_aggregations.clear()

    def load_compiled_aggregations(self) -> None:
        try:
            self._check_compilation_status()
        finally:
            self._load_compiled_aggregations()

    def _load_compiled_aggregations(self) -> None:
        for path_object in self._path_compiled_aggregations.iterdir():
            aggr_id = path_object.name
            if aggr_id in self._compiled_aggregations:
                continue
            self._logger.debug("Loading cached aggregation results %s" % aggr_id)
            aggr_data = ast.literal_eval(path_object.read_text())
            self._compiled_aggregations[aggr_id] = BIAggregation.create_trees_from_schema(aggr_data)

        self._update_part_of_aggregation_map()

    def used_in_aggregation(self, host_name: HostName, service_description: ServiceName) -> bool:
        return (host_name, service_description) in self._part_of_aggregation_map

    def _update_part_of_aggregation_map(self) -> None:
        self._part_of_aggregation_map = {}
        for aggr_id, compiled_aggregation in self._compiled_aggregations.items():
            for branch in compiled_aggregation.branches:
                for _site, host_name, service_description in branch.required_elements():
                    key = (host_name, service_description)
                    self._part_of_aggregation_map.setdefault(key, [])
                    self._part_of_aggregation_map[key].append((aggr_id, branch.properties.title))

    def _check_compilation_status(self) -> None:
        current_configstatus = self.compute_current_configstatus()
        if not self._compilation_required(current_configstatus):
            self._logger.debug("No compilation required")
            return

        with store.locked(self._path_compilation_lock):
            # Re-check compilation required after lock has been required
            # Another apache might have done the job
            current_configstatus = self.compute_current_configstatus()
            if not self._compilation_required(current_configstatus):
                self._logger.debug("No compilation required. An other process already compiled it")
                return

            self.prepare_for_compilation(current_configstatus["online_sites"])

            # Compile the raw tree
            for aggregation in self._bi_packs.get_all_aggregations():
                start = time.time()
                self._compiled_aggregations[aggregation.id] = aggregation.compile(self.bi_searcher)
                self._logger.debug("Compilation of %s took %f" %
                                   (aggregation.id, time.time() - start))

            self._verify_aggregation_title_uniqueness(self._compiled_aggregations)

            for aggr_id, aggr in self._compiled_aggregations.items():
                start = time.time()
                result = BICompiledAggregationSchema().dump(aggr)
                # TODO: remove pprint before going live, change to marshal
                self._path_compiled_aggregations.joinpath(aggr_id).write_text(
                    pprint.pformat(result))
                self._logger.debug("Dump config took %f" % (time.time() - start))

        known_sites = {kv[0]: kv[1] for kv in current_configstatus.get("known_sites", set())}
        self._bi_structure_fetcher._cleanup_orphaned_files(known_sites)

        self._path_compilation_timestamp.write_text(
            str(current_configstatus["configfile_timestamp"]))

    def _verify_aggregation_title_uniqueness(
            self, compiled_aggregations: Dict[str, BICompiledAggregation]) -> None:
        used_titles: Dict[str, str] = {}
        for aggr_id, bi_aggregation in compiled_aggregations.items():
            for bi_branch in bi_aggregation.branches:
                branch_title = bi_branch.properties.title
                if branch_title in used_titles:
                    raise MKGeneralException(
                        _("The aggregation titles are not unique. \"%s\" is created "
                          "by aggregation <b>%s</b> and <b>%s</b>") %
                        (branch_title, aggr_id, used_titles[branch_title]))
                used_titles[branch_title] = aggr_id

    def prepare_for_compilation(self, online_sites: Set[SiteProgramStart]):
        self._bi_packs.load_config()
        self._bi_structure_fetcher.update_data(online_sites)
        self.bi_searcher.set_hosts(self._bi_structure_fetcher.hosts)

    def compile_aggregation_result(self, aggr_id: str,
                                   title: str) -> Optional[BICompiledAggregation]:
        """ Allows to compile a single aggregation with a given title. Does not save any results to disk """
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
        if current_configstatus["configfile_timestamp"] > self._get_compilation_timestamp():
            return True

        return False

    def _get_compilation_timestamp(self) -> float:
        compilation_timestamp = 0.0
        try:
            # I prefer Path.read_text
            # The corresponding cmk.utils.store has some "this function needs to die!" comment
            if self._path_compilation_timestamp.exists():
                compilation_timestamp = float(self._path_compilation_timestamp.read_text())
        except (FileNotFoundError, ValueError) as e:
            self._logger.warning("Can not determine compilation timestamp %s" % str(e))
        return compilation_timestamp

    def _site_status_changed(self, required_program_starts: Set[SiteProgramStart]) -> bool:
        # The cached data may include more data than the currently required_program_starts
        # Empty branches are simply not shown during computation
        cached_program_starts = self._bi_structure_fetcher.get_cached_program_starts()
        return len(required_program_starts - cached_program_starts) > 0

    def compute_current_configstatus(self) -> ConfigStatus:
        current_configstatus: ConfigStatus = {
            "configfile_timestamp": self._get_last_configuration_change(),
            "online_sites": set(),
            "known_sites": set(),
        }

        # The get status message also checks if the remote site is still alive
        result = self._sites_callback.query("GET status\nColumns: program_start\nCache: reload")
        program_start_times = {row[0]: int(row[1]) for row in result}

        for site_id, values in self._sites_callback.states().items():
            start_time = program_start_times.get(site_id, 0)
            current_configstatus["known_sites"].add((site_id, start_time))
            if values.get("state") == "online":
                current_configstatus["online_sites"].add((site_id, start_time))

        return current_configstatus

    def _get_last_configuration_change(self) -> float:
        conf_dir = cmk.utils.paths.default_config_dir + "/multisite.d"
        latest_timestamp = 0.0
        wato_config = Path(conf_dir, "wato", self._bi_configuration_file)
        if wato_config.exists():
            latest_timestamp = max(latest_timestamp, wato_config.stat().st_mtime)

        for path_object in Path(conf_dir).iterdir():
            if path_object.is_dir():
                continue
            latest_timestamp = max(latest_timestamp, path_object.stat().st_mtime)

        return latest_timestamp
