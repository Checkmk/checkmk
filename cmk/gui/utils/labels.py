#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from ast import literal_eval
from typing import Dict, Iterable, List, Mapping, NamedTuple, Set, Tuple, TYPE_CHECKING, Union

from redis.client import Pipeline

from livestatus import LivestatusResponse, lqencode, quote_dict, SiteId

from cmk.utils.redis import get_redis_client, IntegrityCheckResponse, query_redis
from cmk.utils.type_defs import Labels as _Labels

import cmk.gui.sites as sites
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import user
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _

if TYPE_CHECKING:
    from cmk.utils.redis import RedisDecoded


class Label(NamedTuple):
    id: str
    value: str
    negate: bool


Labels = Iterable[Label]


class _LivestatusLabelResponse(NamedTuple):
    host_rows: LivestatusResponse
    service_rows: LivestatusResponse


class _MergedLabels(NamedTuple):
    hosts: Dict[SiteId, Dict[str, str]]
    services: Dict[SiteId, Dict[str, str]]


def parse_labels_value(value: str) -> Labels:

    try:
        decoded_labels = json.loads(value or "[]")
    except ValueError as e:
        raise MKUserError(None, _("Failed to parse labels: %s") % e)

    seen: Set[str] = set()
    for entry in decoded_labels:
        label_id, label_value = [p.strip() for p in entry["value"].split(":", 1)]
        if label_id in seen:
            raise MKUserError(
                None,
                _(
                    "A label key can be used only once per object. "
                    'The Label key "%s" is used twice.'
                )
                % label_id,
            )
        yield Label(label_id, label_value, False)
        seen.add(label_id)


def encode_label_for_livestatus(column: str, label: Label) -> str:
    """
    >>> encode_label_for_livestatus("labels", Label("key", "value", False))
    "Filter: labels = 'key' 'value'"
    """
    return "Filter: %s %s %s %s" % (
        lqencode(column),
        "!=" if label.negate else "=",
        lqencode(quote_dict(label.id)),
        lqencode(quote_dict(label.value)),
    )


def encode_labels_for_livestatus(
    column: str,
    labels: Labels,
) -> str:
    """
    >>> encode_labels_for_livestatus("labels", [Label("key", "value", False), Label("x", "y", False)])
    "Filter: labels = 'key' 'value'\\nFilter: labels = 'x' 'y'\\n"
    >>> encode_labels_for_livestatus("labels", [])
    ''
    """
    if headers := "\n".join(encode_label_for_livestatus(column, label) for label in labels):
        return headers + "\n"
    return ""


def encode_labels_for_tagify(
    labels: Union[Labels, Iterable[Tuple[str, str]]]
) -> Iterable[Mapping[str, str]]:
    """
    >>> encode_labels_for_tagify({"key": "value", "x": "y"}.items()) ==  encode_labels_for_tagify([Label("key", "value", False), Label("x", "y", False)])
    True
    """
    return [{"value": "%s:%s" % e[:2]} for e in labels]


def encode_labels_for_http(labels: Union[Labels, Iterable[Tuple[str, str]]]) -> str:
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

    def get_labels_list(self) -> list[tuple[str, str]]:
        """Main function to query, check and update caches"""
        integrity_function = self._verify_cache_integrity
        update_function = self._redis_update_labels
        query_function = self._redis_query_labels

        all_labels = query_redis(
            self._redis_client, self._namespace, integrity_function, update_function, query_function
        )

        return all_labels

    def _redis_query_labels(self) -> list[tuple[str, str]]:
        """Query all labels from redis"""
        cache_names: List = []
        for site_id in self._get_site_ids():
            for label_type in [self._hst_label, self._svc_label]:
                cache_names.append("%s:%s:%s" % (self._namespace, site_id, label_type))

        with self._redis_client.pipeline() as pipeline:
            for cache in cache_names:
                pipeline.hgetall(cache)
            result = pipeline.execute()
            return self._get_deserialized_labels(result)

    def _get_deserialized_labels(self, result: list[dict[str, str]]) -> list[tuple[str, str]]:
        all_labels: list[tuple[str, str]] = []
        for labels in result:
            deserialized_labels = self._deserialize_labels(labels)
            for label in deserialized_labels:
                all_labels.append(label)

        return all_labels

    def _livestatus_get_labels(self, only_sites: List[SiteId]) -> _MergedLabels:
        """Get labels for all sites that need an update and the user is authorized for"""
        try:
            sites.live().set_auth_domain("labels")
            return self._collect_labels_from_livestatus_labels(self._query_livestatus(only_sites))
        finally:
            sites.live().set_auth_domain("read")

    def _query_livestatus(
        self,
        only_sites: List[SiteId],
    ) -> _LivestatusLabelResponse:

        with sites.prepend_site(), sites.only_sites(only_sites):
            service_rows = sites.live().query(
                "GET services\n" "Cache: reload\n" "Columns: labels\n"
            )
            host_rows = sites.live().query("GET hosts\n" "Cache: reload\n" "Columns: labels\n")

        return _LivestatusLabelResponse(host_rows, service_rows)

    def _collect_labels_from_livestatus_labels(
        self, livestatus_labels: _LivestatusLabelResponse
    ) -> _MergedLabels:
        all_sites_host_labels: Dict[SiteId, Dict[str, Set]] = {}
        all_sites_service_labels: Dict[SiteId, Dict[str, Set]] = {}

        # Collect data from rows
        for source_rows, target_dict in (
            (livestatus_labels.host_rows, all_sites_host_labels),
            (livestatus_labels.service_rows, all_sites_service_labels),
        ):
            for (site_id, labels) in source_rows:
                site_labels = target_dict.setdefault(site_id, {})
                for key, value in labels.items():
                    site_labels.setdefault(key, set()).add(value)

        # Convert label_values to a single str
        merged_host_labels: Dict[SiteId, Dict[str, str]] = {}
        merged_service_labels: Dict[SiteId, Dict[str, str]] = {}
        for source_dict, target_merged_labels in (
            (all_sites_host_labels, merged_host_labels),
            (all_sites_service_labels, merged_service_labels),
        ):
            for site_id, values in source_dict.items():
                site_dict = target_merged_labels.setdefault(site_id, {})
                for key, value in values.items():
                    site_dict[key] = repr(sorted(value))

        return _MergedLabels(merged_host_labels, merged_service_labels)

    def _redis_update_labels(self, pipeline: Pipeline) -> None:
        """Set cache for all sites that need an update"""
        merged_labels = self._livestatus_get_labels(list(self._sites_to_update))

        for labels, label_type in [
            (merged_labels.hosts, self._hst_label),
            (merged_labels.services, self._svc_label),
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

            if not label:
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

    def _deserialize_labels(self, labels: _Labels) -> list[tuple[str, str]]:
        all_labels = []
        for key, value in labels.items():
            value_list = literal_eval(value)
            for entry in value_list:
                all_labels.append((key, entry))

        return all_labels


@request_memoize()
def get_labels_cache() -> LabelsCache:
    return LabelsCache()
