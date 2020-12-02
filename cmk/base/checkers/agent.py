#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import logging
import time
from pathlib import Path
from typing import cast, Dict, Final, Iterable, List, MutableSet, NamedTuple, Optional, Tuple

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
from cmk.fetchers.controller import FetcherType

import cmk.base.config as config
from cmk.base.check_api_utils import state_markers
from cmk.base.exceptions import MKGeneralException
from cmk.base.ip_lookup import normalize_ip_addresses

from ._abstract import FileCacheFactory, Mode, Parser, SectionNameCollection, Source, Summarizer
from .host_sections import HostSections, PersistedSections, SectionStore
from .type_defs import AgentSectionContent

__all__ = ["AgentSource", "AgentHostSections"]

AgentHostSections = HostSections[AgentSectionContent]


class DefaultAgentFileCacheFactory(FileCacheFactory[AgentRawData]):
    def make(self) -> DefaultAgentFileCache:
        return DefaultAgentFileCache(
            path=self.path,
            max_age=self.max_age,
            disabled=self.disabled | self.agent_disabled,
            use_outdated=self.use_outdated,
            simulation=self.simulation,
        )


class NoCacheFactory(FileCacheFactory[AgentRawData]):
    def make(self) -> NoCache:
        return NoCache(
            path=self.path,
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
    name: SectionName
    cached: Optional[Tuple[int, int]]
    encoding: str
    nostrip: bool
    persist: Optional[int]
    separator: Optional[str]

    @classmethod
    def from_headerline(cls, headerline: bytes) -> "AgentParserSectionHeader":
        def parse_options(elems: Iterable[str]) -> Iterable[Tuple[str, str]]:
            for option in elems:
                if "(" not in option:
                    continue
                name, value = option.split("(", 1)
                assert value[-1] == ")", value
                yield name, value[:-1]

        if not HostSectionParser.is_header(headerline):
            raise ValueError(headerline)

        headerparts = ensure_str(headerline[3:-3]).split(":")
        options = dict(parse_options(headerparts[1:]))
        cached: Optional[Tuple[int, int]]
        try:
            cached_ = tuple(map(int, options["cached"].split(",")))
            cached = cached_[0], cached_[1]
        except KeyError:
            cached = None

        encoding = options.get("encoding", "utf-8")
        nostrip = options.get("nostrip") is not None

        persist: Optional[int]
        try:
            persist = int(options["persist"])
        except KeyError:
            persist = None

        separator: Optional[str]
        try:
            separator = chr(int(options["sep"]))
        except KeyError:
            separator = None

        return AgentParserSectionHeader(
            name=SectionName(headerparts[0]),
            cached=cached,
            encoding=encoding,
            nostrip=nostrip,
            persist=persist,
            separator=separator,
        )


class ParserState(abc.ABC):
    """Base class for the state machine.

    .. uml::

        state "NOOPState" as noop
        state "PiggybackSectionParser" as piggy
        state "HostSectionParser" as host
        state c <<choice>>

        [*] --> noop
        noop --> c

        c --> host: ""<<~<STR>>>""
        host -up-> host: ""<<~<STR>>>""
        host -> piggy: ""<<<~<STR>>>>""
        host -up-> noop: ""<<~<>>>""\nOR error

        c --> piggy : ""<<<~<STR>>>>""
        piggy --> piggy : ""<<<~<STR>>>>""
        piggy -up-> noop: ""<<<~<>>>>""\nOR error

    See Also:
        Gamma, Helm, Johnson, Vlissides (1995) Design Patterns "State pattern"

    """
    def __init__(
        self,
        hostname: HostName,
        host_sections: AgentHostSections,
        *,
        section_info: MutableSet[AgentParserSectionHeader],
        cached_at: int,
        cache_age: int,
        logger: logging.Logger,
    ) -> None:
        self.hostname: Final = hostname
        self.host_sections = host_sections
        self.section_info = section_info
        self.cached_at: Final = cached_at
        self.cache_age: Final = cache_age
        self._logger: Final = logger

    def to_noop_parser(self) -> "NOOPParser":
        return NOOPParser(
            self.hostname,
            self.host_sections,
            section_info=self.section_info,
            cached_at=self.cached_at,
            cache_age=self.cache_age,
            logger=self._logger,
        )

    def to_host_section_parser(
        self,
        section_header: AgentParserSectionHeader,
    ) -> "HostSectionParser":
        return HostSectionParser(
            self.hostname,
            self.host_sections,
            section_header,
            section_info=self.section_info,
            cached_at=self.cached_at,
            cache_age=self.cache_age,
            logger=self._logger,
        )

    def to_piggyback_section_parser(
        self,
        piggybacked_hostname: HostName,
    ) -> "PiggybackSectionParser":
        return PiggybackSectionParser(
            self.hostname,
            self.host_sections,
            piggybacked_hostname,
            section_info=self.section_info,
            cached_at=self.cached_at,
            cache_age=self.cache_age,
            logger=self._logger,
        )

    def __call__(self, line: bytes) -> "ParserState":
        raise NotImplementedError()


class NOOPParser(ParserState):
    def __call__(self, line: bytes) -> ParserState:
        if not line.strip():
            return self

        try:
            if PiggybackSectionParser.is_header(line):
                piggybacked_hostname = PiggybackSectionParser.parse_header(line, self.hostname)
                if piggybacked_hostname == self.hostname:
                    # Unpiggybacked "normal" host
                    return self
                return self.to_piggyback_section_parser(piggybacked_hostname)
            if HostSectionParser.is_header(line):
                return self.to_host_section_parser(HostSectionParser.parse_header(line))
        except Exception:
            self._logger.warning("Ignoring invalid raw section: %r" % line, exc_info=True)
            return self.to_noop_parser()
        return self


class PiggybackSectionParser(ParserState):
    def __init__(
        self,
        hostname: HostName,
        host_sections: AgentHostSections,
        piggybacked_hostname: HostName,
        *,
        section_info: MutableSet[AgentParserSectionHeader],
        cached_at: int,
        cache_age: int,
        logger: logging.Logger,
    ) -> None:
        super().__init__(
            hostname,
            host_sections,
            section_info=section_info,
            cached_at=cached_at,
            cache_age=cache_age,
            logger=logger,
        )
        self.piggybacked_hostname: Final = piggybacked_hostname

    def __call__(self, line: bytes) -> ParserState:
        if not line.strip():
            return self

        try:
            if PiggybackSectionParser.is_footer(line):
                return self.to_noop_parser()
            if PiggybackSectionParser.is_header(line):
                # Footer is optional.
                piggybacked_hostname = PiggybackSectionParser.parse_header(line, self.hostname)
                if piggybacked_hostname == self.hostname:
                    # Unpiggybacked "normal" host
                    return self.to_noop_parser()
                return self.to_piggyback_section_parser(piggybacked_hostname)
            if HostSectionParser.is_header(line):
                line = PiggybackSectionParser._add_cached_info(
                    line.strip(),
                    self.cached_at,
                    self.cache_age,
                )
            self.host_sections.piggybacked_raw_data.setdefault(
                self.piggybacked_hostname,
                [],
            ).append(line)
        except Exception:
            self._logger.warning("Ignoring invalid raw section: %r" % line, exc_info=True)
            return self.to_noop_parser()

        return self

    @staticmethod
    def is_header(line: bytes) -> bool:
        return (line.strip().startswith(b'<<<<') and line.strip().endswith(b'>>>>') and
                not PiggybackSectionParser.is_footer(line))

    @staticmethod
    def is_footer(line: bytes) -> bool:
        return line.strip() == b'<<<<>>>>'

    @staticmethod
    def parse_header(line: bytes, hostname: HostName) -> HostName:
        piggybacked_hostname = ensure_str(line.strip()[4:-4])
        assert piggybacked_hostname
        piggybacked_hostname = config.translate_piggyback_host(hostname, piggybacked_hostname)
        # Protect Checkmk against unallowed host names. Normally source scripts
        # like agent plugins should care about cleaning their provided host names
        # up, but we need to be sure here to prevent bugs in Checkmk code.
        return regex("[^%s]" % REGEX_HOST_NAME_CHARS).sub("_", piggybacked_hostname)

    @staticmethod
    def _add_cached_info(
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


class HostSectionParser(ParserState):
    def __init__(
        self,
        hostname: HostName,
        host_sections: AgentHostSections,
        section_header: AgentParserSectionHeader,
        *,
        section_info: MutableSet[AgentParserSectionHeader],
        cached_at: int,
        cache_age: int,
        logger: logging.Logger,
    ) -> None:
        host_sections.sections.setdefault(section_header.name, [])
        section_info.add(section_header)
        super().__init__(
            hostname,
            host_sections,
            section_info=section_info,
            cached_at=cached_at,
            cache_age=cache_age,
            logger=logger,
        )
        self.section_header = section_header

    def __call__(self, line: bytes) -> ParserState:
        if not line.strip():
            return self

        try:
            if PiggybackSectionParser.is_header(line):
                piggybacked_hostname = PiggybackSectionParser.parse_header(line, self.hostname)
                if piggybacked_hostname == self.hostname:
                    # Unpiggybacked "normal" host
                    return self
                return self.to_piggyback_section_parser(piggybacked_hostname)
            if HostSectionParser.is_footer(line):
                return self.to_noop_parser()
            if HostSectionParser.is_header(line):
                # Footer is optional.
                return self.to_host_section_parser(HostSectionParser.parse_header(line))

            if not self.section_header.nostrip:
                line = line.strip()

            self.host_sections.sections[self.section_header.name].append(
                ensure_str_with_fallback(
                    line,
                    encoding=self.section_header.encoding,
                    fallback="latin-1",
                ).split(self.section_header.separator))
        except Exception:
            self._logger.warning("Ignoring invalid raw section: %r" % line, exc_info=True)
            return self.to_noop_parser()
        return self

    @staticmethod
    def is_header(line: bytes) -> bool:
        line = line.strip()
        return (line.startswith(b'<<<') and line.endswith(b'>>>') and
                not HostSectionParser.is_footer(line) and
                not PiggybackSectionParser.is_header(line) and
                not PiggybackSectionParser.is_footer(line))

    @staticmethod
    def is_footer(line: bytes) -> bool:
        return line.strip() == b'<<<>>>'

    @staticmethod
    def parse_header(line: bytes) -> AgentParserSectionHeader:
        return AgentParserSectionHeader.from_headerline(line)


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

    def parse(
        self,
        raw_data: AgentRawData,
        *,
        selection: SectionNameCollection,
    ) -> AgentHostSections:
        if config.agent_simulator:
            raw_data = agent_simulator.process(raw_data)

        parser = self._parse_host_section(raw_data, self.host_config.check_mk_check_interval)
        self._update_cache_info(
            parser.host_sections,
            parser.section_info,
            cached_at=parser.cached_at,
        )
        persisted_sections = self._make_persisted_sections(
            parser.host_sections,
            parser.section_info,
            cached_at=parser.cached_at,
        )
        self.section_store.update(persisted_sections)
        parser.host_sections.add_persisted_sections(
            persisted_sections,
            logger=self._logger,
        )
        return parser.host_sections.filter(selection)

    def _parse_host_section(
        self,
        raw_data: AgentRawData,
        check_interval: int,
    ) -> ParserState:
        """Split agent output in chunks, splits lines by whitespaces."""
        parser: ParserState = NOOPParser(
            self.hostname,
            AgentHostSections(),
            section_info=set(),
            cached_at=int(time.time()),
            # Transform to seconds and give the piggybacked host a little bit more time
            cache_age=int(1.5 * 60 * check_interval),
            logger=self._logger,
        )
        for line in raw_data.split(b"\n"):
            parser = parser(line.rstrip(b"\n"))

        return parser

    @staticmethod
    def _make_persisted_sections(
        host_sections: AgentHostSections,
        section_info: Iterable[AgentParserSectionHeader],
        *,
        cached_at: int,
    ) -> PersistedSections[AgentSectionContent]:
        return PersistedSections[AgentSectionContent]({
            section_header.name:
            (cached_at, section_header.persist, host_sections.sections[section_header.name])
            for section_header in section_info
            if section_header.persist is not None
        })

    @staticmethod
    def _update_cache_info(
        host_sections: AgentHostSections,
        section_info: Iterable[AgentParserSectionHeader],
        *,
        cached_at: int,
    ) -> None:
        for section_header in section_info:
            # If both `persist` and `cached` are present, `cached` overwrites the
            # settings from `persist`.  I do not know whether this is correct.
            if section_header.persist is not None:
                host_sections.cache_info[section_header.name] = (
                    cached_at,
                    section_header.persist - cached_at,
                )
            if section_header.cached:
                host_sections.cache_info[section_header.name] = section_header.cached
