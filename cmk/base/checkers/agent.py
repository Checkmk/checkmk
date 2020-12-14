#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import (
    cast,
    Dict,
    Final,
    List,
    Optional,
    Union,
)

import cmk.utils.misc
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.misc import normalize_ip_addresses
from cmk.utils.type_defs import (
    AgentRawData,
    AgentRawDataSection,
    AgentTargetVersion,
    ExitSpec,
    HostAddress,
    HostName,
    MetricTuple,
    SectionName,
    ServiceCheckResult,
    ServiceDetails,
    ServiceState,
    SourceType,
    state_markers,
)
from cmk.utils.werks import parse_check_mk_version

from cmk.fetchers.agent import AgentParser, AgentHostSections
from cmk.fetchers.cache import SectionStore
from cmk.fetchers.controller import FetcherType
from cmk.fetchers.type_defs import Mode

import cmk.base.config as config

from ._abstract import Mode, Source, Summarizer

__all__ = ["AgentSource"]


class AgentSource(Source[AgentRawData, AgentHostSections]):
    """Configure agent checkers and fetchers.

    Args:
        main_data_source: The data source that is the "main" agent
            based data source uses the cache and persisted directories
            that existed before the data source concept has been added
            where each data source has it's own set of directories.

    """
    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        mode: Mode,
        source_type: SourceType,
        fetcher_type: FetcherType,
        description: str,
        id_: str,
        main_data_source: bool,
    ):
        super().__init__(
            hostname,
            ipaddress,
            mode=mode,
            source_type=source_type,
            fetcher_type=fetcher_type,
            description=description,
            default_raw_data=AgentRawData(b""),
            default_host_sections=AgentHostSections(),
            id_=id_,
            cache_dir=Path(cmk.utils.paths.tcp_cache_dir) if main_data_source else None,
            persisted_section_dir=(Path(cmk.utils.paths.var_dir) /
                                   "persisted") if main_data_source else None,
        )
        # TODO: We should cleanup these old directories one day.
        #       Then we can remove this special case
        self.main_data_source: Final[bool] = main_data_source

    def _make_parser(self) -> AgentParser:
        check_interval = config.HostConfig.make_host_config(self.hostname).check_mk_check_interval
        return AgentParser(
            self.hostname,
            SectionStore[AgentRawDataSection](
                self.persisted_sections_file_path,
                logger=self._logger,
            ),
            check_interval=check_interval,
            keep_outdated=self.use_outdated_persisted_sections,
            translation=config.get_piggyback_translations(self.hostname),
            encoding_fallback=config.fallback_agent_output_encoding,
            simulation=config.agent_simulator,
            logger=self._logger,
        )


class AgentSummarizer(Summarizer[AgentHostSections]):
    pass


class AgentSummarizerDefault(AgentSummarizer):
    # TODO: refactor
    def __init__(
        self,
        exit_spec: ExitSpec,
        *,
        is_cluster: bool,
        agent_min_version: int,
        agent_target_version: AgentTargetVersion,
        only_from: Union[None, List[str], str],
    ) -> None:
        super().__init__(exit_spec)
        self.is_cluster: Final = is_cluster
        self.agent_min_version: Final = agent_min_version
        self.agent_target_version: Final = agent_target_version
        self.only_from: Final = only_from

    def summarize_success(
        self,
        host_sections: AgentHostSections,
        *,
        mode: Mode,
    ) -> ServiceCheckResult:
        return self._summarize_impl(
            host_sections.sections.get(SectionName("check_mk")),
            mode=mode,
        )

    def _summarize_impl(
        self,
        cmk_section: Optional[AgentRawDataSection],
        *,
        mode: Mode,
    ) -> ServiceCheckResult:
        agent_info = self._get_agent_info(cmk_section)
        agent_version = agent_info["version"]

        status: ServiceState = 0
        output: List[ServiceDetails] = []
        perfdata: List[MetricTuple] = []
        if not self.is_cluster and agent_version is not None:
            output.append("Version: %s" % agent_version)

        if not self.is_cluster and agent_info["agentos"] is not None:
            output.append("OS: %s" % agent_info["agentos"])

        if mode is Mode.CHECKING and cmk_section:
            for sub_result in [
                    self._sub_result_version(agent_info),
                    self._sub_result_only_from(agent_info),
            ]:
                if not sub_result:
                    continue
                sub_status, sub_output, sub_perfdata = sub_result
                status = max(status, sub_status)
                output.append(sub_output)
                perfdata += sub_perfdata
        return status, ", ".join(output), perfdata

    @staticmethod
    def _get_agent_info(cmk_section: Optional[AgentRawDataSection],) -> Dict[str, Optional[str]]:
        agent_info: Dict[str, Optional[str]] = {
            "version": u"unknown",
            "agentos": u"unknown",
        }
        if not cmk_section:
            return agent_info

        for line in cmk_section:
            value = " ".join(line[1:]) if len(line) > 1 else None
            agent_info[str(line[0][:-1].lower())] = value
        return agent_info

    def _sub_result_version(
        self,
        agent_info: Dict[str, Optional[str]],
    ) -> Optional[ServiceCheckResult]:
        agent_version = str(agent_info["version"])
        expected_version = self.agent_target_version

        if expected_version and agent_version \
             and not AgentSummarizerDefault._is_expected_agent_version(agent_version, expected_version):
            expected = u""
            # expected version can either be:
            # a) a single version string
            # b) a tuple of ("at_least", {'daily_build': '2014.06.01', 'release': '1.2.5i4'}
            #    (the dict keys are optional)
            if isinstance(expected_version, tuple) and expected_version[0] == 'at_least':
                spec = cast(Dict[str, str], expected_version[1])
                expected = 'at least'
                if 'daily_build' in spec:
                    expected += ' build %s' % spec['daily_build']
                if 'release' in spec:
                    if 'daily_build' in spec:
                        expected += ' or'
                    expected += ' release %s' % spec['release']
            else:
                expected = "%s" % (expected_version,)
            status = cast(int, self.exit_spec.get("wrong_version", 1))
            return (status, "unexpected agent version %s (should be %s)%s" %
                    (agent_version, expected, state_markers[status]), [])

        if self.agent_min_version and cast(int, agent_version) < self.agent_min_version:
            # TODO: This branch seems to be wrong. Or: In which case is agent_version numeric?
            status = self.exit_spec.get("wrong_version", 1)
            return (status, "old plugin version %s (should be at least %s)%s" %
                    (agent_version, self.agent_min_version, state_markers[status]), [])

        return None

    def _sub_result_only_from(
        self,
        agent_info: Dict[str, Optional[str]],
    ) -> Optional[ServiceCheckResult]:
        agent_only_from = agent_info.get("onlyfrom")
        if agent_only_from is None:
            return None

        config_only_from = self.only_from
        if config_only_from is None:
            return None

        allowed_nets = set(normalize_ip_addresses(agent_only_from))
        expected_nets = set(normalize_ip_addresses(config_only_from))
        if allowed_nets == expected_nets:
            return 0, "Allowed IP ranges: %s%s" % (" ".join(allowed_nets), state_markers[0]), []

        infotexts = []
        exceeding = allowed_nets - expected_nets
        if exceeding:
            infotexts.append("exceeding: %s" % " ".join(sorted(exceeding)))

        missing = expected_nets - allowed_nets
        if missing:
            infotexts.append("missing: %s" % " ".join(sorted(missing)))

        mismatch_state = self.exit_spec.get("restricted_address_mismatch", 1)
        assert isinstance(mismatch_state, int)
        return (mismatch_state, "Unexpected allowed IP ranges (%s)%s" %
                (", ".join(infotexts), state_markers[mismatch_state]), [])

    @staticmethod
    def _is_expected_agent_version(
        agent_version: Optional[str],
        expected_version: AgentTargetVersion,
    ) -> bool:
        try:
            if agent_version is None:
                return False

            if agent_version in ['(unknown)', 'None']:
                return False

            if isinstance(expected_version, str) and expected_version != agent_version:
                return False

            if isinstance(expected_version, tuple) and expected_version[0] == 'at_least':
                spec = cast(Dict[str, str], expected_version[1])
                if cmk.utils.misc.is_daily_build_version(agent_version) and 'daily_build' in spec:
                    expected = int(spec['daily_build'].replace('.', ''))

                    branch = cmk.utils.misc.branch_of_daily_build(agent_version)
                    if branch == "master":
                        agent = int(agent_version.replace('.', ''))

                    else:  # branch build (e.g. 1.2.4-2014.06.01)
                        agent = int(agent_version.split('-')[1].replace('.', ''))

                    if agent < expected:
                        return False

                elif 'release' in spec:
                    if cmk.utils.misc.is_daily_build_version(agent_version):
                        return False

                    if parse_check_mk_version(agent_version) < parse_check_mk_version(
                            spec['release']):
                        return False

            return True
        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            raise MKGeneralException(
                "Unable to check agent version (Agent: %s Expected: %s, Error: %s)" %
                (agent_version, expected_version, e))
