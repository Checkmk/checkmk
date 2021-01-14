#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import logging
import time
from typing import (
    cast,
    Dict,
    Final,
    Iterable,
    List,
    MutableMapping,
    NamedTuple,
    Optional,
    Tuple,
    Union,
)

from six import ensure_binary, ensure_str

import cmk.utils.agent_simulator as agent_simulator
import cmk.utils.debug
import cmk.utils.misc
from cmk.utils.encoding import ensure_str_with_fallback
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.misc import normalize_ip_addresses
from cmk.utils.regex import regex, REGEX_HOST_NAME_CHARS
from cmk.utils.translations import translate_piggyback_host, TranslationOptions
from cmk.utils.type_defs import (
    AgentRawData,
    AgentRawDataSection,
    AgentTargetVersion,
    ExitSpec,
    HostName,
    MetricTuple,
    SectionName,
    ServiceDetails,
    ServiceCheckResult,
    ServiceState,
    state_markers,
)
from cmk.utils.werks import parse_check_mk_version

from ._base import Fetcher, Parser, Summarizer
from .cache import FileCache, FileCacheFactory, SectionStore
from .host_sections import HostSections
from .type_defs import Mode, SectionNameCollection

AgentHostSections = HostSections[AgentRawDataSection]


class AgentFileCache(FileCache[AgentRawData]):
    pass


class DefaultAgentFileCache(AgentFileCache):
    @staticmethod
    def _from_cache_file(raw_data: bytes) -> AgentRawData:
        return AgentRawData(raw_data)

    @staticmethod
    def _to_cache_file(raw_data: AgentRawData) -> bytes:
        # TODO: This does not seem to be needed
        return ensure_binary(raw_data)


class NoCache(AgentFileCache):
    """Noop cache for fetchers that do not cache."""
    def read(self) -> None:
        return None

    def write(self, raw_data: AgentRawData) -> None:
        pass

    @staticmethod
    def _from_cache_file(raw_data: bytes) -> AgentRawData:
        return AgentRawData(raw_data)

    @staticmethod
    def _to_cache_file(raw_data: AgentRawData) -> bytes:
        return ensure_binary(raw_data)


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


class AgentFetcher(Fetcher[AgentRawData]):
    pass


class SectionMarker(NamedTuple):
    name: SectionName
    cached: Optional[Tuple[int, int]]
    encoding: str
    nostrip: bool
    persist: Optional[int]
    separator: Optional[str]

    @staticmethod
    def is_header(line: bytes) -> bool:
        line = line.strip()
        return (line.startswith(b'<<<') and line.endswith(b'>>>') and
                not SectionMarker.is_footer(line) and not PiggybackParser.is_header(line) and
                not PiggybackParser.is_footer(line))

    @staticmethod
    def is_footer(line: bytes) -> bool:
        return line.strip() == b'<<<>>>'

    @classmethod
    def from_headerline(cls, headerline: bytes) -> "SectionMarker":
        def parse_options(elems: Iterable[str]) -> Iterable[Tuple[str, str]]:
            for option in elems:
                if "(" not in option:
                    continue
                name, value = option.split("(", 1)
                assert value[-1] == ")", value
                yield name, value[:-1]

        if not SectionMarker.is_header(headerline):
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

        return SectionMarker(
            name=SectionName(headerparts[0]),
            cached=cached,
            encoding=encoding,
            nostrip=nostrip,
            persist=persist,
            separator=separator,
        )

    def cache_info(self, cached_at: int) -> Optional[Tuple[int, int]]:
        # If both `persist` and `cached` are present, `cached` has priority
        # over `persist`.  I do not know whether this is correct.
        if self.cached:
            return self.cached
        if self.persist is not None:
            return cached_at, self.persist - cached_at
        return None


class ParserState(abc.ABC):
    """Base class for the state machine.

    .. uml::

        state "NOOPState" as noop
        state "PiggybackParser" as piggy
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
        section_info: MutableMapping[SectionName, SectionMarker],
        translation: TranslationOptions,
        encoding_fallback: str,
        logger: logging.Logger,
    ) -> None:
        self.hostname: Final = hostname
        self.host_sections = host_sections
        self.section_info = section_info
        self.translation: Final = translation
        self.encoding_fallback: Final = encoding_fallback
        self._logger: Final = logger

    def to_noop_parser(self) -> "NOOPParser":
        return NOOPParser(
            self.hostname,
            self.host_sections,
            section_info=self.section_info,
            translation=self.translation,
            encoding_fallback=self.encoding_fallback,
            logger=self._logger,
        )

    def to_host_section_parser(
        self,
        section_header: SectionMarker,
    ) -> "HostSectionParser":
        return HostSectionParser(
            self.hostname,
            self.host_sections,
            section_header,
            section_info=self.section_info,
            translation=self.translation,
            encoding_fallback=self.encoding_fallback,
            logger=self._logger,
        )

    def to_piggyback_parser(
        self,
        piggybacked_hostname: HostName,
    ) -> "PiggybackParser":
        return PiggybackParser(
            self.hostname,
            self.host_sections,
            piggybacked_hostname,
            section_info=self.section_info,
            translation=self.translation,
            encoding_fallback=self.encoding_fallback,
            logger=self._logger,
        )

    def __call__(self, line: bytes) -> "ParserState":
        raise NotImplementedError()


class NOOPParser(ParserState):
    def __call__(self, line: bytes) -> ParserState:
        if not line.strip():
            return self

        try:
            if PiggybackParser.is_header(line):
                piggybacked_hostname = PiggybackParser.parse_header(
                    line,
                    self.translation,
                    encoding_fallback=self.encoding_fallback,
                )
                if piggybacked_hostname == self.hostname:
                    # Unpiggybacked "normal" host
                    return self
                return self.to_piggyback_parser(piggybacked_hostname)
            if SectionMarker.is_header(line):
                return self.to_host_section_parser(SectionMarker.from_headerline(line))
        except Exception:
            self._logger.warning("Ignoring invalid raw section: %r" % line, exc_info=True)
            return self.to_noop_parser()
        return self


class PiggybackParser(ParserState):
    def __init__(
        self,
        hostname: HostName,
        host_sections: AgentHostSections,
        piggybacked_hostname: HostName,
        *,
        section_info: MutableMapping[SectionName, SectionMarker],
        translation: TranslationOptions,
        encoding_fallback: str,
        logger: logging.Logger,
    ) -> None:
        super().__init__(
            hostname,
            host_sections,
            section_info=section_info,
            translation=translation,
            encoding_fallback=encoding_fallback,
            logger=logger,
        )
        self.piggybacked_hostname: Final = piggybacked_hostname

    def __call__(self, line: bytes) -> ParserState:
        if not line.strip():
            return self

        try:
            if PiggybackParser.is_footer(line):
                return self.to_noop_parser()
            if PiggybackParser.is_header(line):
                # Footer is optional.
                piggybacked_hostname = PiggybackParser.parse_header(
                    line,
                    self.translation,
                    encoding_fallback=self.encoding_fallback,
                )
                if piggybacked_hostname == self.hostname:
                    # Unpiggybacked "normal" host
                    return self.to_noop_parser()
                return self.to_piggyback_parser(piggybacked_hostname)
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
                not PiggybackParser.is_footer(line))

    @staticmethod
    def is_footer(line: bytes) -> bool:
        return line.strip() == b'<<<<>>>>'

    @staticmethod
    def parse_header(
        line: bytes,
        translation: TranslationOptions,
        *,
        encoding_fallback: str,
    ) -> HostName:
        piggybacked_hostname = ensure_str(line.strip()[4:-4])
        assert piggybacked_hostname
        piggybacked_hostname = translate_piggyback_host(
            piggybacked_hostname,
            translation,
            encoding_fallback=encoding_fallback,
        )
        # Protect Checkmk against unallowed host names. Normally source scripts
        # like agent plugins should care about cleaning their provided host names
        # up, but we need to be sure here to prevent bugs in Checkmk code.
        return regex("[^%s]" % REGEX_HOST_NAME_CHARS).sub("_", piggybacked_hostname)


class HostSectionParser(ParserState):
    def __init__(
        self,
        hostname: HostName,
        host_sections: AgentHostSections,
        section_header: SectionMarker,
        *,
        section_info: MutableMapping[SectionName, SectionMarker],
        translation: TranslationOptions,
        encoding_fallback: str,
        logger: logging.Logger,
    ) -> None:
        host_sections.sections.setdefault(section_header.name, [])
        section_info[section_header.name] = section_header
        super().__init__(
            hostname,
            host_sections,
            section_info=section_info,
            translation=translation,
            encoding_fallback=encoding_fallback,
            logger=logger,
        )
        self.section_header = section_header

    def __call__(self, line: bytes) -> ParserState:
        if not line.strip():
            return self

        try:
            if PiggybackParser.is_header(line):
                piggybacked_hostname = PiggybackParser.parse_header(
                    line,
                    self.translation,
                    encoding_fallback=self.encoding_fallback,
                )
                if piggybacked_hostname == self.hostname:
                    # Unpiggybacked "normal" host
                    return self
                return self.to_piggyback_parser(piggybacked_hostname)
            if SectionMarker.is_footer(line):
                return self.to_noop_parser()
            if SectionMarker.is_header(line):
                # Footer is optional.
                return self.to_host_section_parser(SectionMarker.from_headerline(line))

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


class AgentParser(Parser[AgentRawData, AgentHostSections]):
    """A parser for agent data.

    Note:
        It is forbidden to add base dependencies to this class.

    """
    def __init__(
        self,
        hostname: HostName,
        section_store: SectionStore[AgentRawDataSection],
        *,
        check_interval: int,
        keep_outdated: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
        simulation: bool,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self.hostname: Final = hostname
        self.check_interval: Final = check_interval
        self.section_store: Final = section_store
        self.keep_outdated: Final = keep_outdated
        self.translation: Final = translation
        self.encoding_fallback: Final = encoding_fallback
        self.simulation: Final = simulation
        self._logger = logger

    def parse(
        self,
        raw_data: AgentRawData,
        *,
        selection: SectionNameCollection,
    ) -> AgentHostSections:
        if self.simulation:
            raw_data = agent_simulator.process(raw_data)

        now = int(time.time())

        parser = self._parse_host_section(raw_data)

        host_sections = parser.host_sections
        # Transform to seconds and give the piggybacked host a little bit more time
        cache_age = int(1.5 * 60 * self.check_interval)
        host_sections.cache_info.update({
            header.name: cast(Tuple[int, int], header.cache_info(now))
            for header in parser.section_info.values()
            if header.cache_info(now) is not None
        })
        host_sections.piggybacked_raw_data = self._make_updated_piggyback_section_header(
            host_sections.piggybacked_raw_data,
            cached_at=now,
            cache_age=cache_age,
        )
        host_sections.add_persisted_sections(
            host_sections.sections,
            section_store=self.section_store,
            fetch_interval=lambda section_name: parser.section_info[section_name].persist,
            now=now,
            keep_outdated=self.keep_outdated,
            logger=self._logger,
        )
        return host_sections.filter(selection)

    def _parse_host_section(self, raw_data: AgentRawData) -> ParserState:
        """Split agent output in chunks, splits lines by whitespaces."""
        parser: ParserState = NOOPParser(
            self.hostname,
            AgentHostSections(),
            section_info={},
            translation=self.translation,
            encoding_fallback=self.encoding_fallback,
            logger=self._logger,
        )
        for line in raw_data.split(b"\n"):
            parser = parser(line.rstrip(b"\n"))

        return parser

    @staticmethod
    def _make_updated_piggyback_section_header(
        piggybacked_raw_data: Dict[HostName, List[bytes]],
        *,
        cached_at: int,
        cache_age: int,
    ) -> Dict[HostName, List[bytes]]:
        def update_section_header(line: bytes) -> bytes:
            """Append cache information to section headers.

            If the `line` is a section header without caching
            information, these are added to the header.
            Return any other line without modification.

            """
            if not SectionMarker.is_header(line):
                return line
            if b':cached(' in line or b':persist(' in line:
                return line
            return b'<<<%s:cached(%s,%s)>>>' % (
                line[3:-3],
                ensure_binary("%d" % cached_at),
                ensure_binary("%d" % cache_age),
            )

        updated_piggybacked_raw_data: Dict[HostName, List[bytes]] = {}
        for hostname, raw_data in piggybacked_raw_data.items():
            updated_piggybacked_raw_data[hostname] = [
                update_section_header(line) for line in raw_data
            ]
        return updated_piggybacked_raw_data


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
