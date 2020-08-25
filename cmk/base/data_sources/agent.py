#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import time
from pathlib import Path
from typing import cast, Dict, Final, List, Optional, Tuple

from six import ensure_binary, ensure_str

import cmk.utils.agent_simulator as agent_simulator
import cmk.utils.misc
from cmk.utils.regex import regex, REGEX_HOST_NAME_CHARS
from cmk.utils.encoding import ensure_str_with_fallback
from cmk.utils.type_defs import (
    AgentRawData,
    HostAddress,
    HostName,
    Metric,
    SectionName,
    ServiceCheckResult,
    ServiceDetails,
    ServiceState,
    SourceType,
)
from cmk.utils.werks import parse_check_mk_version

from cmk.fetchers.controller import FetcherType

import cmk.base.config as config
from cmk.base.check_api_utils import state_markers
from cmk.base.check_utils import (
    AgentPersistedSections,
    AgentSectionContent,
    AgentSections,
    PiggybackRawData,
    SectionCacheInfo,
)
from cmk.base.exceptions import MKGeneralException
from cmk.base.ip_lookup import normalize_ip_addresses

from ._abstract import (
    ABCConfigurator,
    ABCDataSource,
    ABCHostSections,
    ABCParser,
    ABCSummarizer,
    Mode,
)

__all__ = ["AgentConfigurator", "AgentHostSections", "AgentDataSource"]


class AgentHostSections(ABCHostSections[AgentRawData, AgentSections, AgentPersistedSections,
                                        AgentSectionContent]):
    pass


class AgentConfigurator(ABCConfigurator[AgentRawData]):
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
        cpu_tracking_id: str,
    ):
        super().__init__(
            hostname,
            ipaddress,
            mode=mode,
            source_type=source_type,
            fetcher_type=fetcher_type,
            description=description,
            default_raw_data=AgentRawData(),
            id_=id_,
            cpu_tracking_id=cpu_tracking_id,
            cache_dir=Path(cmk.utils.paths.tcp_cache_dir) if main_data_source else None,
            persisted_section_dir=(Path(cmk.utils.paths.var_dir) /
                                   "persisted") if main_data_source else None,
        )
        # TODO: We should cleanup these old directories one day.
        #       Then we can remove this special case
        self.main_data_source: Final[bool] = main_data_source


class AgentSummarizer(ABCSummarizer[AgentHostSections]):
    pass


class AgentSummarizerDefault(AgentSummarizer):
    # TODO: refactor
    def __init__(self, configurator: AgentConfigurator) -> None:
        super().__init__()
        self.configurator = configurator
        self._host_config = self.configurator.host_config

    def summarize(
        self,
        host_sections: AgentHostSections,
    ) -> ServiceCheckResult:
        return self._summarize(
            host_sections.sections.get(SectionName("check_mk")),
            self.configurator.mode is Mode.CHECKING,
        )

    def _summarize(
        self,
        cmk_section: Optional[AgentSectionContent],
        for_checking: bool,
    ) -> ServiceCheckResult:
        agent_info = self._get_agent_info(cmk_section)
        agent_version = agent_info["version"]

        status: ServiceState = 0
        output: List[ServiceDetails] = []
        perfdata: List[Metric] = []
        if not self._host_config.is_cluster and agent_version is not None:
            output.append("Version: %s" % agent_version)

        if not self._host_config.is_cluster and agent_info["agentos"] is not None:
            output.append("OS: %s" % agent_info["agentos"])

        if for_checking and cmk_section:
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
    def _get_agent_info(cmk_section: Optional[AgentSectionContent],) -> Dict[str, Optional[str]]:
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
        expected_version = self._host_config.agent_target_version

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
            status = cast(int, self._host_config.exit_code_spec().get("wrong_version", 1))
            return (status, "unexpected agent version %s (should be %s)%s" %
                    (agent_version, expected, state_markers[status]), [])

        if config.agent_min_version and cast(int, agent_version) < config.agent_min_version:
            # TODO: This branch seems to be wrong. Or: In which case is agent_version numeric?
            status = cast(int, self._host_config.exit_code_spec().get("wrong_version", 1))
            return (status, "old plugin version %s (should be at least %s)%s" %
                    (agent_version, config.agent_min_version, state_markers[status]), [])

        return None

    def _sub_result_only_from(
        self,
        agent_info: Dict[str, Optional[str]],
    ) -> Optional[ServiceCheckResult]:
        agent_only_from = agent_info.get("onlyfrom")
        if agent_only_from is None:
            return None

        config_only_from = self._host_config.only_from
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

        mismatch_state = self._host_config.exit_code_spec().get("restricted_address_mismatch", 1)
        assert isinstance(mismatch_state, int)
        return (mismatch_state, "Unexpected allowed IP ranges (%s)%s" %
                (", ".join(infotexts), state_markers[mismatch_state]), [])

    @staticmethod
    def _is_expected_agent_version(
        agent_version: Optional[str],
        expected_version: config.AgentTargetVersion,
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


class AgentParser(ABCParser[AgentRawData, AgentHostSections]):
    """A parser for agent data."""

    # TODO(ml): Refactor, we should structure the code so that we have one
    #   function per attribute in AgentHostSections (AgentHostSections.sections,
    #   AgentHostSections.cache_info, AgentHostSections.piggybacked_raw_data,
    #   and AgentHostSections.persisted_sections) and a few simple helper functions.
    #   Moreover, the main loop of the parser (at `for line in raw_data.split(b"\n")`)
    #   is an FSM and shoule be written as such.  (See CMK-5004)
    def parse(
        self,
        raw_data: AgentRawData,
    ) -> AgentHostSections:
        raw_data = cast(AgentRawData, raw_data)
        if config.agent_simulator:
            raw_data = agent_simulator.process(raw_data)

        return self._parse_host_section(raw_data, self.host_config.check_mk_check_interval)

    def _parse_host_section(
        self,
        raw_data: AgentRawData,
        check_interval: int,
    ) -> AgentHostSections:
        """Split agent output in chunks, splits lines by whitespaces.

        Returns a HostSections() object.
        """
        hostname = self.hostname
        sections: AgentSections = {}
        # Unparsed info for other hosts. A dictionary, indexed by the piggybacked host name.
        # The value is a list of lines which were received for this host.
        piggybacked_raw_data: PiggybackRawData = {}
        piggybacked_hostname = None
        piggybacked_cached_at = int(time.time())
        # Transform to seconds and give the piggybacked host a little bit more time
        piggybacked_cache_age = int(1.5 * 60 * check_interval)

        # handle sections with option persist(...)
        persisted_sections: AgentPersistedSections = {}
        section_content: Optional[AgentSectionContent] = None
        section_options: Dict[str, Optional[str]] = {}
        agent_cache_info: SectionCacheInfo = {}
        separator: Optional[str] = None
        encoding = None
        for line in raw_data.split(b"\n"):
            line = line.rstrip(b"\r")
            stripped_line = line.strip()
            if stripped_line[:4] == b'<<<<' and stripped_line[-4:] == b'>>>>':
                piggybacked_hostname =\
                    AgentParser._get_sanitized_and_translated_piggybacked_hostname(stripped_line, hostname)

            elif piggybacked_hostname:  # processing data for an other host
                if stripped_line[:3] == b'<<<' and stripped_line[-3:] == b'>>>':
                    line = AgentParser._add_cached_info_to_piggybacked_section_header(
                        stripped_line, piggybacked_cached_at, piggybacked_cache_age)
                piggybacked_raw_data.setdefault(piggybacked_hostname, []).append(line)

            # Found normal section header
            # section header has format <<<name:opt1(args):opt2:opt3(args)>>>
            elif stripped_line[:3] == b'<<<' and stripped_line[-3:] == b'>>>':
                section_name, section_options = AgentParser._parse_section_header(
                    stripped_line[3:-3])

                if section_name is None:
                    self._logger.warning("Ignoring invalid raw section: %r" % stripped_line)
                    section_content = None
                    continue
                section_content = sections.setdefault(section_name, [])

                raw_separator = section_options.get("sep")
                if raw_separator is None:
                    separator = None
                else:
                    separator = chr(int(raw_separator))

                # Split of persisted section for server-side caching
                raw_persist = section_options.get("persist")
                if raw_persist is not None:
                    until = int(raw_persist)
                    cached_at = int(time.time())  # Estimate age of the data
                    cache_interval = int(until - cached_at)
                    agent_cache_info[section_name] = (cached_at, cache_interval)
                    persisted_sections[section_name] = (cached_at, until, section_content)

                raw_cached = section_options.get("cached")
                if raw_cached is not None:
                    cache_times = list(map(int, raw_cached.split(",")))
                    agent_cache_info[section_name] = cache_times[0], cache_times[1]

                # The section data might have a different encoding
                encoding = section_options.get("encoding")

            elif stripped_line != b'':
                if section_content is None:
                    continue

                raw_nostrip = section_options.get("nostrip")
                if raw_nostrip is None:
                    line = stripped_line

                decoded_line = ensure_str_with_fallback(
                    line, encoding=("utf-8" if encoding is None else encoding), fallback="latin-1")

                section_content.append(decoded_line.split(separator))

        return AgentHostSections(
            sections,
            agent_cache_info,
            piggybacked_raw_data,
            persisted_sections,
        )

    @staticmethod
    def _parse_section_header(
        headerline: bytes,) -> Tuple[Optional[SectionName], Dict[str, Optional[str]]]:
        headerparts = ensure_str(headerline).split(":")
        try:
            section_name = SectionName(headerparts[0])
        except ValueError:
            return None, {}

        section_options: Dict[str, Optional[str]] = {}
        for option in headerparts[1:]:
            if "(" not in option:
                section_options[option] = None
            else:
                opt_name, opt_part = option.split("(", 1)
                section_options[opt_name] = opt_part[:-1]
        return section_name, section_options

    @staticmethod
    def _get_sanitized_and_translated_piggybacked_hostname(
        orig_piggyback_header: bytes,
        hostname: HostName,
    ) -> Optional[HostName]:
        piggybacked_hostname = ensure_str(orig_piggyback_header[4:-4])
        if not piggybacked_hostname:
            return None

        piggybacked_hostname = config.translate_piggyback_host(hostname, piggybacked_hostname)
        if piggybacked_hostname == hostname or not piggybacked_hostname:
            return None  # unpiggybacked "normal" host

        # Protect Check_MK against unallowed host names. Normally source scripts
        # like agent plugins should care about cleaning their provided host names
        # up, but we need to be sure here to prevent bugs in Check_MK code.
        return regex("[^%s]" % REGEX_HOST_NAME_CHARS).sub("_", piggybacked_hostname)

    @staticmethod
    def _add_cached_info_to_piggybacked_section_header(
        orig_section_header: bytes,
        cached_at: int,
        cache_age: int,
    ) -> bytes:
        if b':cached(' in orig_section_header or b':persist(' in orig_section_header:
            return orig_section_header
        return b'<<<%s:cached(%s,%s)>>>' % (
            orig_section_header[3:-3],
            ensure_binary("%d" % cached_at),
            ensure_binary("%d" % cache_age),
        )


class AgentDataSource(ABCDataSource[AgentRawData, AgentSections, AgentPersistedSections,
                                    AgentHostSections],
                      metaclass=abc.ABCMeta):
    """Base for agent-based checkers.

    Args:
        main_data_source: The main agent has other cache directories for
            compatibility with older Check MK.

    """

    # NOTE: This class is obviously still abstract, but pylint fails to see
    # this, even in the presence of the meta class assignment below, see
    # https://github.com/PyCQA/pylint/issues/179.

    # pylint: disable=abstract-method

    def __init__(
        self,
        configurator: ABCConfigurator,
        *,
        summarizer: AgentSummarizer,
    ) -> None:
        super().__init__(
            configurator,
            summarizer=summarizer,
            default_host_sections=AgentHostSections(),
        )

    @property
    def _parser(self) -> ABCParser:
        return AgentParser(self.hostname, self._logger)
