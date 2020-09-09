#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.regex import regex
from typing import NamedTuple, Dict, List, Tuple
from cmk.utils.rulesets.ruleset_matcher import matches_labels, matches_tag_spec

from cmk.utils.bi.bi_data_fetcher import BIHostData

#   .--Defines-------------------------------------------------------------.
#   |                  ____        __ _                                    |
#   |                 |  _ \  ___ / _(_)_ __   ___  ___                    |
#   |                 | | | |/ _ \ |_| | '_ \ / _ \/ __|                   |
#   |                 | |_| |  __/  _| | | | |  __/\__ \                   |
#   |                 |____/ \___|_| |_|_| |_|\___||___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# Search data used by bi_searcher
BIHostSearchMatch = NamedTuple("BIHostSearchMatch", [
    ("host", BIHostData),
    ("match_groups", tuple),
])

BIServiceSearchMatch = NamedTuple("BIServiceSearchMatch", [
    ("host", BIHostData),
    ("service_description", str),
    ("match_groups", tuple),
])

#   .--BISearcher----------------------------------------------------------.
#   |         ____ ___ ____                      _                         |
#   |        | __ )_ _/ ___|  ___  __ _ _ __ ___| |__   ___ _ __           |
#   |        |  _ \| |\___ \ / _ \/ _` | '__/ __| '_ \ / _ \ '__|          |
#   |        | |_) | | ___) |  __/ (_| | | | (__| | | |  __/ |             |
#   |        |____/___|____/ \___|\__,_|_|  \___|_| |_|\___|_|             |
#   |                                                                      |
#   +----------------------------------------------------------------------+


class BISearcher:
    def __init__(self):
        self.hosts = {}
        self._host_regex_match_cache = {}
        self._host_regex_miss_cache = {}

    def set_hosts(self, hosts: Dict[str, BIHostData]) -> None:
        self.cleanup()
        self.hosts = hosts

    def cleanup(self) -> None:
        # Note: Do not call clear() on hosts
        #       This would clear the reference we've got on set_hosts
        self.hosts = {}
        self._host_regex_match_cache.clear()
        self._host_regex_miss_cache.clear()

    def search_hosts(self, conditions: Dict) -> List[BIHostSearchMatch]:
        matched_hosts, matched_re_groups = self.filter_host_choice(list(self.hosts.values()),
                                                                   conditions["host_choice"])
        matched_hosts = self.filter_host_tags(matched_hosts, conditions["host_tags"])
        matched_hosts = self.filter_host_labels(matched_hosts, conditions["host_labels"])
        return [BIHostSearchMatch(x, matched_re_groups[x.name]) for x in matched_hosts]

    def filter_host_choice(self, hosts: List[BIHostData],
                           condition: Dict) -> Tuple[List[BIHostData], Dict]:
        if condition["type"] == "all_hosts" or condition["pattern"] == "(.*)":
            match_groups = {}
            for host in hosts:
                match_groups[host.name] = (host.name,)
            return hosts, match_groups

        if condition["type"] == "host_name_regex":
            return self.get_host_name_matches(hosts, condition["pattern"])

        if condition["type"] == "host_alias_regex":
            return self.get_host_alias_matches(hosts, condition["pattern"])

        raise NotImplementedError("Invalid condition type %r" % condition["type"])

    def get_host_name_matches(self, hosts: List[BIHostData],
                              pattern: str) -> Tuple[List[BIHostData], Dict]:

        is_regex_match = '*' in pattern or '$' in pattern or '|' in pattern or '[' in pattern
        if not is_regex_match:
            host = self.hosts.get(pattern)
            if host:
                return [host], {pattern: (pattern,)}
            return [], {}

        matched_hosts = []
        matched_re_groups = {}
        regex_pattern = regex(pattern)
        pattern_match_cache = self._host_regex_match_cache.setdefault(pattern, {})
        pattern_miss_cache = self._host_regex_miss_cache.setdefault(pattern, {})
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

    def get_host_alias_matches(self, hosts: List[BIHostData],
                               pattern: str) -> Tuple[List[BIHostData], Dict]:
        # TODO: alias matches currently costs way more performmance than the host matches
        #       requires alias lookup to fix
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

    def get_service_description_matches(self, hosts: List[BIHostData],
                                        pattern: str) -> List[BIServiceSearchMatch]:
        matched_services = []
        regex_pattern = regex(pattern)
        for host in hosts:
            for service_description in host.services.keys():
                match = regex_pattern.match(service_description)
                if match is None:
                    continue
                matched_services.append(
                    BIServiceSearchMatch(host, service_description, tuple(match.groups())))
        return matched_services

    def search_services(self, conditions: Dict) -> List[BIServiceSearchMatch]:
        host_matches: List[BIHostSearchMatch] = bi_searcher.search_hosts(conditions)
        service_matches = self.get_service_description_matches([x.host for x in host_matches],
                                                               conditions["service_regex"])
        service_matches = self.filter_service_labels(service_matches, conditions["service_labels"])
        return service_matches

    def filter_host_tags(self, hosts: List[BIHostData], condition: Dict) -> List[BIHostData]:
        matched_hosts = []
        for host in hosts:
            for tag_condition in condition.values():
                if not matches_tag_spec(tag_condition, host.tags):
                    break
            else:  # I know..
                matched_hosts.append(host)
        return matched_hosts

    def filter_host_labels(self, hosts: List[BIHostData], required_labels):
        if not required_labels:
            return hosts
        matched_hosts = []
        for host in hosts:
            if matches_labels(host.labels, required_labels):
                matched_hosts.append(host)
        return matched_hosts

    def filter_service_labels(self, services: List[BIServiceSearchMatch], required_labels):
        if not required_labels:
            return services

        matched_services = []
        for service in services:
            service_data = service.host.services[service.service_description]
            if matches_labels(service_data.labels, required_labels):
                matched_services.append(service)
        return matched_services


bi_searcher = BISearcher()
