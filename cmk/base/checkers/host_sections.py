#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import logging
import sys
import time
from pathlib import Path
from typing import (
    Any,
    Callable,
    cast,
    Dict,
    Final,
    Generic,
    ItemsView,
    Iterator,
    KeysView,
    List,
    MutableMapping,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
    ValuesView,
)

import cmk.utils.debug
import cmk.utils.store as _store
from cmk.utils.check_utils import section_name_of
from cmk.utils.type_defs import (
    CheckPluginNameStr,
    HostKey,
    HostName,
    ParsedSectionName,
    SectionName,
    SourceType,
)

from cmk.snmplib.type_defs import SNMPSectionContent

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.caching as caching
import cmk.base.item_state as item_state
from cmk.base.api.agent_based.type_defs import SectionPlugin
from cmk.base.check_api_utils import HOST_PRECEDENCE as LEGACY_HOST_PRECEDENCE
from cmk.base.check_api_utils import MGMT_ONLY as LEGACY_MGMT_ONLY
from cmk.base.exceptions import MKParseFunctionError

from .type_defs import (
    AgentSectionContent,
    NO_SELECTION,
    PiggybackRawData,
    SectionCacheInfo,
    SectionNameCollection,
)

# AbstractSectionContent is wrong from a typing point of view.
# AgentSectionContent and SNMPSectionContent are not correct either,
# at best, they should be List[<element>] because this is what they
# have in common and, more importantly, what is used here.
AbstractSectionContent = Union[AgentSectionContent, SNMPSectionContent]

ParsedSectionContent = Any
TSectionContent = TypeVar("TSectionContent", bound=AbstractSectionContent)
THostSections = TypeVar("THostSections", bound="HostSections")


class PersistedSections(
        Generic[TSectionContent],
        MutableMapping[SectionName, Tuple[int, int, TSectionContent]],
):
    __slots__ = ("_store",)

    def __init__(self, store: MutableMapping[SectionName, Tuple[int, int, TSectionContent]]):
        self._store = store

    def __repr__(self) -> str:
        return "%s(%r)" % (type(self).__name__, self._store)

    def __getitem__(self, key: SectionName) -> Tuple[int, int, TSectionContent]:
        return self._store.__getitem__(key)

    def __setitem__(self, key: SectionName, value: Tuple[int, int, TSectionContent]) -> None:
        return self._store.__setitem__(key, value)

    def __delitem__(self, key: SectionName) -> None:
        return self._store.__delitem__(key)

    def __iter__(self) -> Iterator[SectionName]:
        return self._store.__iter__()

    def __len__(self) -> int:
        return self._store.__len__()


class SectionStore(Generic[TSectionContent]):
    def __init__(
        self,
        path: Union[str, Path],
        *,
        keep_outdated: bool,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self.path: Final = Path(path)
        self.keep_outdated: Final = keep_outdated
        self._logger: Final = logger

    def update(
        self,
        persisted_sections: PersistedSections[TSectionContent],
    ) -> None:
        """Fuse stored sections with the provided ones

        Fill up the persisted sections with the stored ones,
        if they are not already present. Save the result to disk.
        """
        stored = self.load()
        if persisted_sections == stored:
            return

        stored.update(persisted_sections)
        persisted_sections.update(stored)
        self.store(stored)

    def store(self, sections: PersistedSections[TSectionContent]) -> None:
        if not sections:
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)
        _store.save_object_to_file(self.path, {str(k): v for k, v in sections.items()},
                                   pretty=False)
        self._logger.debug("Stored persisted sections: %s", ", ".join(str(s) for s in sections))

    # TODO: This is not race condition free when modifying the data. Either remove
    # the possible write here and simply ignore the outdated sections or lock when
    # reading and unlock after writing
    def load(self) -> PersistedSections[TSectionContent]:
        raw_sections_data = _store.load_object_from_file(self.path, default={})
        sections: PersistedSections[TSectionContent] = {  # type: ignore[assignment]
            SectionName(k): v for k, v in raw_sections_data.items()
        }
        if not self.keep_outdated:
            sections = self._filter(sections)

        if not sections:
            self._logger.debug("No persisted sections loaded")
            self.path.unlink(missing_ok=True)

        return sections

    def _filter(
        self,
        sections: PersistedSections[TSectionContent],
    ) -> PersistedSections[TSectionContent]:
        now = time.time()
        for section_name, entry in list(sections.items()):
            if len(entry) == 2:
                persisted_until = entry[0]
            else:
                persisted_until = entry[1]

            if now > persisted_until:
                self._logger.debug("Persisted section %s is outdated by %d seconds. Skipping it.",
                                   section_name, now - persisted_until)
                del sections[section_name]
        return sections


class HostSections(Generic[TSectionContent], metaclass=abc.ABCMeta):
    """A wrapper class for the host information read by the data sources

    It contains the following information:

        1. sections:                A dictionary from section_name to a list of rows,
                                    the section content
        2. piggybacked_raw_data:    piggy-backed data for other hosts
        3. cache_info:              Agent cache information
                                    (dict section name -> (cached_at, cache_interval))
    """
    def __init__(
        self,
        sections: Optional[MutableMapping[SectionName, TSectionContent]] = None,
        *,
        cache_info: Optional[SectionCacheInfo] = None,
        piggybacked_raw_data: Optional[PiggybackRawData] = None,
        # Unparsed info for other hosts. A dictionary, indexed by the piggybacked host name.
        # The value is a list of lines which were received for this host.
    ) -> None:
        super().__init__()
        self.sections = sections if sections else {}
        self.cache_info = cache_info if cache_info else {}
        self.piggybacked_raw_data = piggybacked_raw_data if piggybacked_raw_data else {}

    def __repr__(self):
        return "%s(sections=%r, cache_info=%r, piggybacked_raw_data=%r)" % (
            type(self).__name__,
            self.sections,
            self.cache_info,
            self.piggybacked_raw_data,
        )

    def filter(self, selection: SectionNameCollection) -> "HostSections[TSectionContent]":
        """Filter for preselected sections"""
        # This could be optimized by telling the parser object about the
        # preselected sections and dismissing raw data at an earlier stage.
        # For now we don't need that, so we keep it simple.
        if selection is NO_SELECTION:
            return self
        return HostSections(
            {k: v for k, v in self.sections.items() if k in selection},
            cache_info={k: v for k, v in self.cache_info.items() if k in selection},
            piggybacked_raw_data={
                k: v for k, v in self.piggybacked_raw_data.items() if SectionName(k) in selection
            },
        )

    # TODO: It should be supported that different sources produce equal sections.
    # this is handled for the self.sections data by simply concatenating the lines
    # of the sections, but for the self.cache_info this is not done. Why?
    # TODO: checking.execute_check() is using the oldest cached_at and the largest interval.
    #       Would this be correct here?
    def add(self, host_sections: "HostSections") -> None:
        """Add the content of `host_sections` to this HostSection."""
        for section_name, section_content in host_sections.sections.items():
            self.sections.setdefault(
                section_name,
                cast(TSectionContent, []),
            ).extend(section_content)

        for hostname, raw_lines in host_sections.piggybacked_raw_data.items():
            self.piggybacked_raw_data.setdefault(hostname, []).extend(raw_lines)

        if host_sections.cache_info:
            self.cache_info.update(host_sections.cache_info)

    def add_persisted_sections(
        self,
        persisted_sections: PersistedSections[TSectionContent],
        *,
        logger: logging.Logger,
    ) -> None:
        """Add information from previous persisted infos."""
        for section_name, entry in persisted_sections.items():
            if len(entry) == 2:
                continue  # Skip entries of "old" format

            # Don't overwrite sections that have been received from the source with this call
            if section_name in self.sections:
                logger.debug("Skipping persisted section %r, live data available", section_name)
                continue

            logger.debug("Using persisted section %r", section_name)
            persisted_from, persisted_until, section = entry
            self.cache_info[section_name] = (persisted_from, persisted_until - persisted_from)
            self.sections[section_name] = section


class MultiHostSections(MutableMapping[HostKey, HostSections]):
    """Container object for wrapping the host sections of a host being processed
    or multiple hosts when a cluster is processed. Also holds the functionality for
    merging these information together for a check"""
    def __init__(self, data: Optional[Dict[HostKey, HostSections]] = None) -> None:
        super().__init__()
        self._data: Dict[HostKey, HostSections] = {} if data is None else data
        self._section_content_cache = caching.DictCache()
        # The following are not quite the same as section_content_cache.
        # They are introduced for the changed data handling with the migration
        # to 'agent_based' plugins.
        # This hodls the result of the parsing of individual raw sections
        self._parsing_results = caching.DictCache()
        # This hodls the result of the superseding section along with the
        # cache info of the raw section that was used.
        self._parsed_sections = caching.DictCache()

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[HostKey]:
        return self._data.__iter__()

    def __getitem__(self, key: HostKey) -> HostSections:
        return self._data.__getitem__(key)

    def __setitem__(self, key: HostKey, value: HostSections) -> None:
        self._data.__setitem__(key, value)

    def __delitem__(self, key: HostKey) -> None:
        self._data.__delitem__(key)

    def __repr__(self) -> str:
        return "%s(data=%r)" % (type(self).__name__, self._data)

    def keys(self) -> KeysView[HostKey]:
        return self._data.keys()  # pylint: disable=dict-keys-not-iterating

    def values(self) -> ValuesView[HostSections]:
        return self._data.values()  # pylint: disable=dict-values-not-iterating

    def items(self) -> ItemsView[HostKey, HostSections]:
        return self._data.items()  # pylint: disable=dict-items-not-iterating

    def get_section_kwargs(
        self,
        host_key: HostKey,
        parsed_section_names: List[ParsedSectionName],
    ) -> Dict[str, Any]:
        """Prepares section keyword arguments for a non-cluster host

        It returns a dictionary containing one entry (may be None) for each
        of the required sections, or an empty dictionary if no data was found at all.
        """
        keys = (["section"] if len(parsed_section_names) == 1 else
                ["section_%s" % s for s in parsed_section_names])

        kwargs = {
            key: self.get_parsed_section(host_key, parsed_section_name)
            for key, parsed_section_name in zip(keys, parsed_section_names)
        }
        # empty it, if nothing was found:
        if all(v is None for v in kwargs.values()):
            kwargs.clear()

        return kwargs

    def get_section_cluster_kwargs(
        self,
        node_keys: List[HostKey],
        parsed_section_names: List[ParsedSectionName],
    ) -> Dict[str, Dict[str, Any]]:
        """Prepares section keyword arguments for a cluster host

        It returns a dictionary containing one optional dictionary[Host, ParsedSection]
        for each of the required sections, or an empty dictionary if no data was found at all.
        """
        kwargs: Dict[str, Dict[str, Any]] = {}
        for node_key in node_keys:
            node_kwargs = self.get_section_kwargs(node_key, parsed_section_names)
            for key, sections_node_data in node_kwargs.items():
                kwargs.setdefault(key, {})[node_key.hostname] = sections_node_data
        # empty it, if nothing was found:
        if all(v is None for s in kwargs.values() for v in s.values()):
            kwargs.clear()

        return kwargs

    def get_cache_info(
        self,
        parsed_section_names: List[ParsedSectionName],
    ) -> Optional[Tuple[int, int]]:
        """Aggregate information about the age of the data in the agent sections
        """
        cached_ats: List[int] = []
        intervals: List[int] = []
        for host_key in self:
            for parsed_section_name in parsed_section_names:
                # Fear not, the parsing itself is cached. But in case we have not already
                # parsed, we must do so in order to see which raw sections cache info we
                # must use.
                _parsed, cache_info = self._get_parsed_section_with_cache_info(
                    host_key, parsed_section_name)
                if cache_info:
                    cached_ats.append(cache_info[0])
                    intervals.append(cache_info[1])

        return (min(cached_ats), max(intervals)) if cached_ats else None

    def get_parsed_section(
        self,
        host_key: HostKey,
        parsed_section_name: ParsedSectionName,
    ) -> Optional[ParsedSectionContent]:
        return self._get_parsed_section_with_cache_info(host_key, parsed_section_name)[0]

    def _get_parsed_section_with_cache_info(
        self,
        host_key: HostKey,
        parsed_section_name: ParsedSectionName,
    ) -> Tuple[Optional[ParsedSectionContent], Optional[Tuple[int, int]]]:
        cache_key = host_key + (parsed_section_name,)
        if cache_key in self._parsed_sections:
            return self._parsed_sections[cache_key]

        try:
            host_sections = self[host_key]
        except KeyError:
            return self._parsed_sections.setdefault(cache_key, (None, None))

        for section in agent_based_register.get_ranked_sections(
                host_sections.sections,
            {parsed_section_name},
        ):
            parsed = self._get_parsing_result(host_key, section)
            if parsed is None:
                continue

            cache_info = host_sections.cache_info.get(section.name)
            return self._parsed_sections.setdefault(cache_key, (parsed, cache_info))

        return self._parsed_sections.setdefault(cache_key, (None, None))

    def determine_applicable_sections(
        self,
        parse_sections: Set[ParsedSectionName],
        source_type: SourceType,
    ) -> List[SectionPlugin]:
        """Try to parse all given sections and return a set of names for which the
        parsed sections value is not None.

        This takes into account the supersedings and permanently "dismisses" all
        superseded raw sections (by setting their parsing result to None).
        """
        applicable_sections: List[SectionPlugin] = []
        for host_key, host_sections in self.items():
            if host_key.source_type != source_type:
                continue

            for section in agent_based_register.get_ranked_sections(
                    host_sections.sections,
                    parse_sections,
            ):
                parsed = self._get_parsing_result(host_key, section)
                if parsed is None:
                    continue

                applicable_sections.append(section)
                self._parsed_sections[host_key + (section.parsed_section_name,)] = (
                    parsed,
                    host_sections.cache_info.get(section.name),
                )
                # set result of superseded ones to None:
                for superseded in section.supersedes:
                    self._parsing_results[host_key + (superseded,)] = None

        return applicable_sections

    def _get_parsing_result(
        self,
        host_key: HostKey,
        section: SectionPlugin,
    ) -> Any:
        # lookup the parsing result in the cache, it might have been computed
        # during resolving of the supersedings (or set to None b/c the section
        # *is* superseeded)
        cache_key = host_key + (section.name,)
        if cache_key in self._parsing_results:
            return self._parsing_results[cache_key]

        try:
            data = self[host_key].sections[section.name]
        except KeyError:
            return self._parsing_results.setdefault(cache_key, None)

        return self._parsing_results.setdefault(cache_key, section.parse_function(data))

    # DEPRECATED
    # This function is only kept for the legacy cluster mode from hell
    def get_section_content(
        self,
        host_key: HostKey,
        management_board_info: str,
        check_plugin_name: CheckPluginNameStr,
        for_discovery: bool,
        *,
        cluster_node_keys: Optional[List[HostKey]] = None,
        check_legacy_info: Dict[str, Dict[str, Any]],
    ) -> Union[None, ParsedSectionContent, List[ParsedSectionContent]]:
        """Prepares the section_content construct for a Check_MK check on ANY host

        The section_content construct is then handed over to the check, inventory or
        discovery functions for doing their work.

        If the host is a cluster, the sections from all its nodes is merged together
        here. Optionally the node info is added to the nodes section content.

        It handles the whole data and cares about these aspects:

        a) Extract the section_content for the given check_plugin_name
        b) Adds node_info to the section_content (if check asks for this)
        c) Applies the parse function (if check has some)
        d) Adds extra_sections (if check asks for this)
           and also applies node_info and extra_section handling to this

        It can return an section_content construct or None when there is no section content
        for this check available.
        """

        section_name = section_name_of(check_plugin_name)
        cache_key = (host_key, management_board_info, section_name, for_discovery,
                     bool(cluster_node_keys))

        try:
            return self._section_content_cache[cache_key]
        except KeyError:
            pass

        section_content = self._get_section_content(
            host_key._replace(source_type=SourceType.MANAGEMENT if management_board_info ==
                              LEGACY_MGMT_ONLY else SourceType.HOST),
            check_plugin_name,
            SectionName(section_name),
            for_discovery,
            cluster_node_keys=cluster_node_keys,
            check_legacy_info=check_legacy_info,
        )

        # If we found nothing, see if we must check the management board:
        if (section_content is None and host_key.source_type is SourceType.HOST and
                management_board_info == LEGACY_HOST_PRECEDENCE):
            section_content = self._get_section_content(
                host_key._replace(source_type=SourceType.MANAGEMENT),
                check_plugin_name,
                SectionName(section_name),
                for_discovery,
                cluster_node_keys=cluster_node_keys,
                check_legacy_info=check_legacy_info,
            )

        self._section_content_cache[cache_key] = section_content
        return section_content

    # DEPRECATED
    # This function is only kept for the legacy cluster mode from hell
    def _get_section_content(
        self,
        host_key: HostKey,
        check_plugin_name: CheckPluginNameStr,
        section_name: SectionName,
        for_discovery: bool,
        *,
        cluster_node_keys: Optional[List[HostKey]] = None,
        check_legacy_info: Dict[str, Dict[str, Any]]
    ) -> Union[None, ParsedSectionContent, List[ParsedSectionContent]]:
        # Now get the section_content from the required hosts and merge them together to
        # a single section_content. For each host optionally add the node info.
        section_content: Optional[AbstractSectionContent] = None
        for node_key in cluster_node_keys or [host_key]:

            try:
                host_section_content = self[node_key].sections[section_name]
            except KeyError:
                continue

            if section_content is None:
                section_content = host_section_content[:]
            else:
                section_content += host_section_content

        if section_content is None:
            return None

        assert isinstance(section_content, list)

        return self._update_with_parse_function(
            section_content,
            section_name,
            check_legacy_info,
        )

    # DEPRECATED
    # This function is only kept for the legacy cluster mode from hell
    # TODO: Add correct type hint for node wrapped SectionContent. We would have to create some kind
    # of AbstractSectionContentWithNodeInfo.
    @staticmethod
    def _add_node_column(
        section_content: AbstractSectionContent,
        nodename: Optional[HostName],
    ) -> AbstractSectionContent:
        new_section_content = []
        node_text = str(nodename) if isinstance(nodename, str) else nodename
        for line in section_content:
            if len(line) > 0 and isinstance(line[0], list):
                new_entry = []
                for entry in line:
                    new_entry.append([node_text] + entry)  # type: ignore[operator]
                new_section_content.append(new_entry)
            else:
                new_section_content.append([node_text] + line)  # type: ignore[arg-type,operator]
        return new_section_content  # type: ignore[return-value]

    # DEPRECATED
    # This function is only kept for the legacy cluster mode from hell
    @staticmethod
    def _update_with_parse_function(
        section_content: AbstractSectionContent,
        section_name: SectionName,
        check_legacy_info: Dict[str, Dict[str, Any]],
    ) -> ParsedSectionContent:
        """Transform the section_content using the defined parse functions.

        Some checks define a parse function that is used to transform the section_content
        somehow. It is applied by this function.

        Please note that this is not a check/subcheck individual setting. This option is related
        to the agent section.

        All exceptions raised by the parse function will be catched and re-raised as
        MKParseFunctionError() exceptions."""
        # We can use the migrated section: we refuse to migrate sections with
        # "'node_info'=True", so the auto-migrated ones will keep working.
        # This function will never be called on checks programmed against the new
        # API (or migrated manually)
        if not agent_based_register.is_registered_section_plugin(section_name):
            # use legacy parse function for unmigrated sections
            parse_function = check_legacy_info.get(str(section_name), {}).get("parse_function")
        else:
            section_plugin = agent_based_register.get_section_plugin(section_name)
            parse_function = cast(Callable[[AbstractSectionContent], ParsedSectionContent],
                                  section_plugin.parse_function)

        if parse_function is None:
            return section_content

        # (mo): ValueStores (formally Item state) need to be *only* available
        # from within the check function, nowhere else.
        orig_item_state_prefix = item_state.get_item_state_prefix()
        try:
            item_state.set_item_state_prefix(section_name, None)
            return parse_function(section_content)

        except item_state.MKCounterWrapped:
            raise

        except Exception:
            if cmk.utils.debug.enabled():
                raise
            raise MKParseFunctionError(*sys.exc_info())

        finally:
            item_state.set_item_state_prefix(*orig_item_state_prefix)
