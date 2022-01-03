#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Dict, Iterable, List, Mapping, Set, Tuple, TYPE_CHECKING

from redis.client import Pipeline

from livestatus import lqencode, quote_dict, SiteId

from cmk.utils.redis import get_redis_client, IntegrityCheckResponse, query_redis
from cmk.utils.type_defs import Labels as _Labels

import cmk.gui.sites as sites
from cmk.gui.globals import user
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _

if TYPE_CHECKING:
    from cmk.utils.redis import RedisDecoded

Labels = Iterable[Tuple[str, str]]


def encode_label_for_livestatus(
    column: str,
    label_id: str,
    label_value: str,
    negate: bool = False,
) -> str:
    """
    >>> encode_label_for_livestatus("labels", "key", "value")
    "Filter: labels = 'key' 'value'"
    """
    return "Filter: %s %s %s %s" % (
        lqencode(column),
        "!=" if negate else "=",
        lqencode(quote_dict(label_id)),
        lqencode(quote_dict(label_value)),
    )


def encode_labels_for_livestatus(
    column: str,
    labels: Labels,
) -> str:
    """
    >>> encode_labels_for_livestatus("labels", {"key": "value", "x": "y"}.items())
    "Filter: labels = 'key' 'value'\\nFilter: labels = 'x' 'y'"
    >>> encode_labels_for_livestatus("labels", [])
    ''
    """
    return "\n".join(
        encode_label_for_livestatus(column, label_id, label_value)
        for label_id, label_value in labels
    )


def encode_labels_for_tagify(labels: Labels) -> Iterable[Mapping[str, str]]:
    """
    >>> encode_labels_for_tagify({"key": "value", "x": "y"}.items())
    [{'value': 'key:value'}, {'value': 'x:y'}]
    """
    return [{"value": "%s:%s" % e} for e in labels]


def encode_labels_for_http(labels: Labels) -> str:
    """The result can be used in building URLs
    >>> encode_labels_for_http([])
    '[]'
    >>> encode_labels_for_http({"key": "value", "x": "y"}.items())
    '[{"value": "key:value"}, {"value": "x:y"}]'
    """
    return json.dumps(encode_labels_for_tagify(labels))


def label_help_text() -> str:
    return _(
        "Labels need to be in the format <tt>[KEY]:[VALUE]</tt>. For example <tt>cmk/os_family:linux</tt>."
    )


class LabelsCache:
    def __init__(self):
        self._namespace: str = "labels"
        self._hst_label: str = "host_labels"
        self._svc_label: str = "service_labels"
        self._program_starts: str = self._namespace + ":last_program_starts"
        self._redis_client: "RedisDecoded" = get_redis_client()
        self._sites_to_update: Set[SiteId] = set()

    def _get_site_ids(self) -> List[SiteId]:
        """Create list of all site IDs the user is authorized for"""
        site_ids: List[SiteId] = []
        for site_id, _site in user.authorized_sites().items():
            site_ids.append(site_id)
        return site_ids

    def get_labels(self) -> _Labels:
        """Main function to query, check and update caches"""
        integrity_function = self._verify_cache_integrity
        update_function = self._redis_update_labels
        query_function = self._redis_query_labels

        all_labels = query_redis(
            self._redis_client, self._namespace, integrity_function, update_function, query_function
        )

        return all_labels

    def _redis_query_labels(self) -> _Labels:
        """Query all labels from redis"""
        cache_names: List = []
        for site_id in self._get_site_ids():
            for label_type in [self._hst_label, self._svc_label]:
                cache_names.append("%s:%s:%s" % (self._namespace, site_id, label_type))

        all_labels = {}
        with self._redis_client.pipeline() as pipeline:
            for cache in cache_names:
                pipeline.hgetall(cache)
            result = pipeline.execute()
            for labels in result:
                all_labels.update(labels)
        return all_labels

    def _livestatus_get_labels(
        self, only_sites: List[str]
    ) -> Tuple[Mapping[SiteId, _Labels], Mapping[SiteId, _Labels]]:
        """Get labels for all sites that need an update and the user is authorized for"""
        query: str = "GET services\n" "Cache: reload\n" "Columns: host_labels labels\n"

        with sites.prepend_site(), sites.only_sites(only_sites):
            rows = [(x[0], x[1], x[2]) for x in sites.live(user).query(query)]

        host_labels: Dict[SiteId, Dict[str, str]] = {}
        service_labels: Dict[SiteId, Dict[str, str]] = {}
        for row in rows:
            site_id = row[0]
            host_label = row[1]
            service_label = row[2]

            for key, value in host_label.items():
                host_labels.setdefault(site_id, {}).update({key: value})

            for key, value in service_label.items():
                service_labels.setdefault(site_id, {}).update({key: value})

        return (host_labels, service_labels)

    def _redis_update_labels(self, pipeline: Pipeline) -> None:
        """Set cache for all sites that need an update"""
        host_labels, service_labels = self._livestatus_get_labels(list(self._sites_to_update))

        for labels, label_type in [
            (host_labels, self._hst_label),
            (service_labels, self._svc_label),
        ]:
            self._redis_delete_old_and_set_new(labels, label_type, pipeline)

    def _redis_delete_old_and_set_new(
        self,
        labels: Mapping[SiteId, _Labels],
        label_type: str,
        pipeline: Pipeline,
    ) -> None:

        sites_list: List[SiteId] = []
        for site_id, label in labels.items():
            if site_id not in self._sites_to_update:
                continue

            label_key = "%s:%s:%s" % (self._namespace, site_id, label_type)
            pipeline.delete(label_key)
            # NOTE: Mapping is invariant in its key because of __getitem__, so for mypy's sake we
            # make a copy below. This doesn't matter from a performance view, hset is iterating over
            # the dict anyway, and after that there is some serious I/O going on.
            # NOTE: pylint is too dumb to see the need for the comprehension.
            # pylint: disable=unnecessary-comprehension
            pipeline.hset(label_key, mapping={k: v for k, v in label.items()})

            if site_id not in sites_list:
                sites_list.append(site_id)

        for site_id in sites_list:
            self._redis_set_last_program_start(site_id, pipeline)

    def _redis_get_last_program_starts(self) -> Dict[str, str]:
        program_starts = self._redis_client.hgetall(self._program_starts)
        return program_starts

    def _redis_set_last_program_start(self, site_id: SiteId, pipeline: Pipeline) -> None:
        program_start = self._livestatus_get_last_program_start(site_id)
        pipeline.hset(self._program_starts, key=site_id, value=program_start)

    def _livestatus_get_last_program_start(self, site_id: SiteId) -> int:
        return sites.states().get(site_id, sites.SiteStatus({})).get("program_start", 0)

    def _verify_cache_integrity(self) -> IntegrityCheckResponse:
        """Verify last program start value in redis with current value"""
        last_program_starts = self._redis_get_last_program_starts()

        if not last_program_starts:
            all_sites = self._get_site_ids()
            self._sites_to_update.update(all_sites)
            return IntegrityCheckResponse.UPDATE

        for site_id, last_program_start in last_program_starts.items():

            if last_program_start is None or (
                int(last_program_start) != self._livestatus_get_last_program_start(site_id)
            ):

                self._sites_to_update.update([site_id])

        if self._sites_to_update:
            return IntegrityCheckResponse.UPDATE

        return IntegrityCheckResponse.USE


@request_memoize()
def get_labels_cache() -> LabelsCache:
    return LabelsCache()
