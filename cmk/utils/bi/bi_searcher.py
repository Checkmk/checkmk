#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Iterable, List, Tuple

from cmk.utils.bi.bi_lib import ABCBISearcher, BIHostData, BIHostSearchMatch, BIServiceSearchMatch
from cmk.utils.regex import regex
from cmk.utils.rulesets.ruleset_matcher import matches_labels, matches_tag_condition
from cmk.utils.type_defs import HostName, TaggroupIDToTagCondition

#   .--Defines-------------------------------------------------------------.
#   |                  ____        __ _                                    |
#   |                 |  _ \  ___ / _(_)_ __   ___  ___                    |
#   |                 | | | |/ _ \ |_| | '_ \ / _ \/ __|                   |
#   |                 | |_| |  __/  _| | | | |  __/\__ \                   |
#   |                 |____/ \___|_| |_|_| |_|\___||___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# Search data used by bi_searcher

#   .--BISearcher----------------------------------------------------------.
#   |         ____ ___ ____                      _                         |
#   |        | __ )_ _/ ___|  ___  __ _ _ __ ___| |__   ___ _ __           |
#   |        |  _ \| |\___ \ / _ \/ _` | '__/ __| '_ \ / _ \ '__|          |
#   |        | |_) | | ___) |  __/ (_| | | | (__| | | |  __/ |             |
#   |        |____/___|____/ \___|\__,_|_|  \___|_| |_|\___|_|             |
#   |                                                                      |
#   +----------------------------------------------------------------------+


class BISearcher(ABCBISearcher):
    def set_hosts(self, hosts: Dict[HostName, BIHostData]) -> None:
        self.cleanup()
        self.hosts = hosts

    def cleanup(self) -> None:
        # Note: Do not call clear() on hosts
        #       This would clear the reference we've got on set_hosts
        self.hosts = {}
        self._host_regex_match_cache.clear()
        self._host_regex_miss_cache.clear()

    def search_hosts(self, conditions: Dict) -> List[BIHostSearchMatch]:
        hosts, matched_re_groups = self.filter_host_choice(
            list(self.hosts.values()), conditions["host_choice"]
        )
        matched_hosts = self.filter_host_folder(hosts, conditions["host_folder"])
        matched_hosts = self.filter_host_tags(matched_hosts, conditions["host_tags"])
        matched_hosts = self.filter_host_labels(matched_hosts, conditions["host_labels"])
        return [BIHostSearchMatch(x, matched_re_groups[x.name]) for x in matched_hosts]

    def filter_host_choice(
        self,
        hosts: List[BIHostData],
        condition: Dict,
    ) -> Tuple[List[BIHostData], Dict]:
        if condition["type"] == "all_hosts":
            return hosts, self._host_match_groups(hosts)

        if condition["type"] == "host_name_regex":
            return self.get_host_name_matches(hosts, condition["pattern"])

        if condition["type"] == "host_alias_regex":
            return self.get_host_alias_matches(hosts, condition["pattern"])

        raise NotImplementedError("Invalid condition type %r" % condition["type"])

    def _host_match_groups(self, hosts: List[BIHostData], match="name"):
        return {host.name: (getattr(host, match),) for host in hosts}

    def get_host_name_matches(
        self,
        hosts: List[BIHostData],
        pattern: str,
    ) -> Tuple[List[BIHostData], Dict]:

        if pattern == "(.*)":
            return hosts, self._host_match_groups(hosts)

        is_regex_match = any(map(lambda x: x in pattern, ["(", ")", "*", "$", "|", "[", "]"]))
        if not is_regex_match:
            host = self.hosts.get(pattern)
            if host:
                return [host], {pattern: (pattern,)}
            return [], {}

        # Hidden "feature": The regex pattern condition for hosts implicitly uses a $ at the end
        pattern_with_anchor = pattern
        if not pattern_with_anchor.endswith("$"):
            pattern_with_anchor += "$"

        matched_hosts = []
        matched_re_groups = {}
        regex_pattern = regex(pattern_with_anchor)
        pattern_match_cache = self._host_regex_match_cache.setdefault(pattern_with_anchor, {})
        pattern_miss_cache = self._host_regex_miss_cache.setdefault(pattern_with_anchor, {})
        for host in hosts:
            if host.name in pattern_miss_cache:
                continue

            cached_match = pattern_match_cache.get(host.name)
            if cached_match:
                matched_hosts.append(host)
                matched_re_groups[host.name] = cached_match
                continue

            match = regex_pattern.match(host.name)
            if match is None:
                pattern_miss_cache[host.name] = True
                continue
            pattern_match_cache[host.name] = match.groups()
            matched_hosts.append(host)
            matched_re_groups[host.name] = pattern_match_cache[host.name]

        return matched_hosts, matched_re_groups

    def get_host_alias_matches(
        self,
        hosts: List[BIHostData],
        pattern: str,
    ) -> Tuple[List[BIHostData], Dict]:
        if pattern == "(.*)":
            return hosts, self._host_match_groups(hosts, "alias")

        # TODO: alias matches currently costs way more performance than the host matches
        #       requires alias lookup cache to fix
        matched_hosts = []
        matched_re_groups = {}
        regex_pattern = regex(pattern)
        for host in hosts:
            match = regex_pattern.match(host.alias)
            if match is None:
                continue
            matched_hosts.append(host)
            matched_re_groups[host.name] = tuple(match.groups())
        return matched_hosts, matched_re_groups

    def get_service_description_matches(
        self,
        host_matches: List[BIHostSearchMatch],
        pattern: str,
    ) -> List[BIServiceSearchMatch]:
        matched_services = []
        regex_pattern = regex(pattern)
        for host_match in host_matches:
            for service_description in host_match.host.services.keys():
                if match := regex_pattern.match(service_description):
                    matched_services.append(
                        BIServiceSearchMatch(host_match, service_description, tuple(match.groups()))
                    )
        return matched_services

    def search_services(self, conditions: Dict) -> List[BIServiceSearchMatch]:
        host_matches: List[BIHostSearchMatch] = self.search_hosts(conditions)
        service_matches = self.get_service_description_matches(
            host_matches, conditions["service_regex"]
        )
        service_matches = self.filter_service_labels(service_matches, conditions["service_labels"])
        return service_matches

    def filter_host_folder(
        self,
        hosts: Iterable[BIHostData],
        folder_path: str,
    ) -> Iterable[BIHostData]:
        if not folder_path:
            return hosts

        folder_path = f"{folder_path}/"
        return (x for x in hosts if x.folder.startswith(folder_path))

    def filter_host_tags(
        self,
        hosts: Iterable[BIHostData],
        tag_conditions: TaggroupIDToTagCondition,
    ) -> Iterable[BIHostData]:
        return (
            host
            for host in hosts  #
            if all(
                matches_tag_condition(
                    taggroup_id,
                    tag_condition,
                    host.tags,
                )
                for taggroup_id, tag_condition in tag_conditions.items()
            )
        )

    def filter_host_labels(
        self, hosts: Iterable[BIHostData], required_labels
    ) -> Iterable[BIHostData]:
        if not required_labels:
            return hosts
        return (x for x in hosts if matches_labels(x.labels, required_labels))

    def filter_service_labels(self, services: List[BIServiceSearchMatch], required_labels):
        if not required_labels:
            return services

        matched_services = []
        for service in services:
            service_data = service.host_match.host.services[service.service_description]
            if matches_labels(service_data.labels, required_labels):
                matched_services.append(service)
        return matched_services
