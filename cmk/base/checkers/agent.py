#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time
from pathlib import Path
from typing import cast, Dict, Final, Iterable, List, NamedTuple, Optional, Tuple

from six import ensure_binary, ensure_str

import cmk.utils.agent_simulator as agent_simulator
import cmk.utils.misc
from cmk.utils.encoding import ensure_str_with_fallback
from cmk.utils.regex import regex, REGEX_HOST_NAME_CHARS
from cmk.utils.type_defs import (
    AgentRawData,
    HostAddress,
    HostName,
    MetricTuple,
    SectionName,
    ServiceCheckResult,
    ServiceDetails,
    ServiceState,
    SourceType,
)
from cmk.utils.werks import parse_check_mk_version

from cmk.fetchers.agent import DefaultAgentFileCache, NoCache
from cmk.fetchers.cache import PersistedSections, SectionStore
from cmk.fetchers.controller import FetcherType
from cmk.fetchers.type_defs import AgentSectionContent

import cmk.base.config as config
from cmk.base.check_api_utils import state_markers
from cmk.base.exceptions import MKGeneralException
from cmk.base.ip_lookup import normalize_ip_addresses

from ._abstract import FileCacheFactory, Mode, Parser, SectionNameCollection, Source, Summarizer
from .host_sections import HostSections

__all__ = ["AgentSource", "AgentHostSections"]

AgentHostSections = HostSections[AgentSectionContent]


class DefaultAgentFileCacheFactory(FileCacheFactory[AgentRawData]):
    def make(self) -> DefaultAgentFileCache:
        return DefaultAgentFileCache(
            base_path=self.base_path,
            max_age=self.max_age,
            disabled=self.disabled | self.agent_disabled,
            use_outdated=self.use_outdated,
            simulation=self.simulation,
        )


class NoCacheFactory(FileCacheFactory[AgentRawData]):
    def make(self) -> NoCache:
        return NoCache(
            base_path=self.base_path,
            max_age=self.max_age,
            disabled=self.disabled | self.agent_disabled,
            use_outdated=self.use_outdated,
            simulation=self.simulation,
        )


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

    def _make_parser(self) -> "AgentParser":
        return AgentParser(
            self.hostname,
            SectionStore[AgentSectionContent](
                self.persisted_sections_file_path,
                keep_outdated=self.use_outdated_persisted_sections,
                logger=self._logger,
            ),
            self._logger,
        )


class AgentSummarizer(Summarizer[AgentHostSections]):
    pass


class AgentSummarizerDefault(AgentSummarizer):
    # TODO: refactor
    def __init__(
        self,
        exit_spec: config.ExitSpec,
        source: AgentSource,
    ) -> None:
        super().__init__(exit_spec)
        self.source = source
        self._host_config = self.source.host_config

    def summarize_success(
        self,
        host_sections: AgentHostSections,
    ) -> ServiceCheckResult:
        return self._summarize_impl(
            host_sections.sections.get(SectionName("check_mk")),
            self.source.mode is Mode.CHECKING,
        )

    def _summarize_impl(
        self,
        cmk_section: Optional[AgentSectionContent],
        for_checking: bool,
    ) -> ServiceCheckResult:
        agent_info = self._get_agent_info(cmk_section)
        agent_version = agent_info["version"]

        status: ServiceState = 0
        output: List[ServiceDetails] = []
        perfdata: List[MetricTuple] = []
        if not self._host_config.is_cluster and agent_version is not None:
            output.append("Version: %s" % agent_version)

        if not self._host_config.is_cluster and agent_info["agentos"] is not None:
            output.append("OS: %s" % agent_info["agentos"])

        if for_checking and cmk_section:
            for sub_result in [
                    self._sub_result_version(agent_info),
                    self._sub_result_only_from(agent_info),
                    self._sub_result_python_plugins(agent_info),
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
            key = str(line[0][:-1].lower())
            value = " ".join(line[1:]) if len(line) > 1 else None

            if key == "onlyfrom":
                # parse the same way systemd does:
                #  * multiple lines are concatenated
                #  * an empty line clears the list
                agent_info[key] = (None if value is None else
                                   f"{agent_info.get(key) or ''} {value}".strip())
            else:
                agent_info[key] = value

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
            status = cast(int, self.exit_spec.get("wrong_version", 1))
            return (status, "unexpected agent version %s (should be %s)%s" %
                    (agent_version, expected, state_markers[status]), [])

        if config.agent_min_version and cast(int, agent_version) < config.agent_min_version:
            # TODO: This branch seems to be wrong. Or: In which case is agent_version numeric?
            status = self.exit_spec.get("wrong_version", 1)
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

        mismatch_state = self.exit_spec.get("restricted_address_mismatch", 1)
        assert isinstance(mismatch_state, int)
        return (mismatch_state, "Unexpected allowed IP ranges (%s)%s" %
                (", ".join(infotexts), state_markers[mismatch_state]), [])

    def _sub_result_python_plugins(
        self,
        agent_info: Dict[str, Optional[str]],
    ) -> Optional[ServiceCheckResult]:
        failed_plugins = agent_info.get("failedpythonplugins")
        fail_reason = agent_info.get("failedpythonreason")
        if failed_plugins is None:
            return None

        return (
            1,
            f"Failed to execute python plugins: {failed_plugins}" +
            (f" ({fail_reason})" if fail_reason else ""),
            [],
        )

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


class AgentParserSectionHeader(NamedTuple):
    # Note: The `type: ignore` and `cast` are all because of
    #       false positives on mypy side! -- There are tests
    #       to prove it.
    name: SectionName
    options: Dict[str, str]

    @classmethod
    def from_headerline(cls, headerline: bytes) -> "AgentParserSectionHeader":
        def parse_options(elems: Iterable[str]) -> Iterable[Tuple[str, str]]:
            for option in elems:
                if "(" not in option:
                    continue
                name, value = option.split("(", 1)
                assert value[-1] == ")", value
                yield name, value[:-1]

        headerparts = ensure_str(headerline).split(":")
        return AgentParserSectionHeader(
            SectionName(headerparts[0]),
            dict(parse_options(headerparts[1:])),
        )

    @property
    def cached(self) -> Tuple[int, ...]:
        try:
            return tuple(map(int, self.options["cached"].split(",")))  # type: ignore[union-attr]
        except KeyError:
            return ()

    @property
    def encoding(self) -> str:
        return cast(str, self.options.get("encoding", "utf-8"))

    @property
    def nostrip(self) -> bool:
        return self.options.get("nostrip") is not None

    @property
    def persist(self) -> Optional[int]:
        try:
            return int(self.options["persist"])  # type: ignore[arg-type]
        except KeyError:
            return None

    @property
    def separator(self) -> Optional[str]:
        try:
            return chr(int(self.options["sep"]))  # type: ignore [arg-type]
        except KeyError:
            return None


class AgentParser(Parser[AgentRawData, AgentHostSections]):
    """A parser for agent data."""
    def __init__(
        self,
        hostname: HostName,
        section_store: SectionStore[AgentSectionContent],
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self.hostname: Final = hostname
        self.host_config: Final = config.HostConfig.make_host_config(self.hostname)
        self.section_store: Final = section_store
        self._logger = logger

    # TODO(ml): Refactor, we should structure the code so that we have one
    #   function per attribute in AgentHostSections (AgentHostSections.sections,
    #   AgentHostSections.cache_info, AgentHostSections.piggybacked_raw_data,
    #   and AgentHostSections.persisted_sections) and a few simple helper functions.
    #   Moreover, the main loop of the parser (at `for line in raw_data.split(b"\n")`)
    #   is an FSM and shoule be written as such.  (See CMK-5004)
    def parse(
        self,
        raw_data: AgentRawData,
        *,
        selection: SectionNameCollection,
    ) -> AgentHostSections:
        if config.agent_simulator:
            raw_data = agent_simulator.process(raw_data)

        host_sections, persisted_sections = self._parse_host_section(
            raw_data, self.host_config.check_mk_check_interval)
        self.section_store.update(persisted_sections)
        host_sections.add_persisted_sections(
            persisted_sections,
            logger=self._logger,
        )
        return host_sections.filter(selection)

    def _parse_host_section(
        self,
        raw_data: AgentRawData,
        check_interval: int,
    ) -> Tuple[AgentHostSections, PersistedSections[AgentSectionContent]]:
        """Split agent output in chunks, splits lines by whitespaces.

        Returns a HostSections() object.
        """
        host_sections = AgentHostSections()

        piggybacked_hostname = None
        piggybacked_cached_at = int(time.time())
        # Transform to seconds and give the piggybacked host a little bit more time
        piggybacked_cache_age = int(1.5 * 60 * check_interval)

        # handle sections with option persist(...)
        persisted_sections = PersistedSections[AgentSectionContent]({})
        section_content: Optional[AgentSectionContent] = None
        for line in raw_data.split(b"\n"):
            line = line.rstrip(b"\r")
            stripped_line = line.strip()
            if stripped_line[:4] == b'<<<<' and stripped_line[-4:] == b'>>>>':
                piggybacked_hostname = (
                    AgentParser._get_sanitized_and_translated_piggybacked_hostname(
                        stripped_line, self.hostname))

            elif piggybacked_hostname:  # processing data for an other host
                if stripped_line[:3] == b'<<<' and stripped_line[-3:] == b'>>>':
                    line = AgentParser._add_cached_info_to_piggybacked_section_header(
                        stripped_line,
                        piggybacked_cached_at,
                        piggybacked_cache_age,
                    )
                host_sections.piggybacked_raw_data.setdefault(piggybacked_hostname, []).append(line)

            # Found normal section header
            # section header format: <<<name:opt1(args):opt2:opt3(args)>>>
            # *) empty sections <<<>>> or '<<<:cached(...)>>>' are allowed and will be skipped
            elif stripped_line[:3] == b'<<<' and stripped_line[-3:] == b'>>>':
                if stripped_line.startswith((b'<<<>>>', b'<<<:cached')):
                    # Special case b'<<<>>>' is accepted: no data to process, skip it
                    section_content = None
                    continue

                try:
                    section_header = AgentParserSectionHeader.from_headerline(stripped_line[3:-3])
                except ValueError:
                    self._logger.warning("Ignoring invalid raw section: %r" % stripped_line)
                    section_content = None
                    continue
                section_content = host_sections.sections.setdefault(section_header.name, [])

                # Split of persisted section for server-side caching
                if section_header.persist is not None:
                    cached_at = int(time.time())  # Estimate age of the data
                    cache_interval = section_header.persist - cached_at
                    host_sections.cache_info[section_header.name] = (cached_at, cache_interval)
                    # pylint does not seem to understand `NewType`... leave the checking up to mypy.
                    persisted_sections[section_header.name] = (  # false positive: pylint: disable=E1137
                        (cached_at, section_header.persist, section_content))

                if section_header.cached:
                    cache_times = section_header.cached
                    host_sections.cache_info[section_header.name] = cache_times[0], cache_times[1]

            elif stripped_line != b'':
                if section_content is None:
                    continue

                if not section_header.nostrip:
                    line = stripped_line

                decoded_line = ensure_str_with_fallback(
                    line,
                    encoding=section_header.encoding,
                    fallback="latin-1",
                )

                section_content.append(decoded_line.split(section_header.separator))

        return host_sections, persisted_sections

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

        # Protect Checkmk against unallowed host names. Normally source scripts
        # like agent plugins should care about cleaning their provided host names
        # up, but we need to be sure here to prevent bugs in Checkmk code.
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
