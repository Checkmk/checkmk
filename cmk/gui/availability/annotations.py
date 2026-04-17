#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"

import itertools
import time
from collections.abc import Callable
from typing import Any, NamedTuple

import cmk.utils.paths
import cmk.utils.render
from cmk.ccc import store

from .type_defs import (
    AVAnnotationEntry,
    AVAnnotationKey,
    AVAnnotations,
    AVObjectType,
    AVOptions,
    AVRawData,
    AVSpan,
    AVTimeRange,
    AVTimeStamp,
    SiteHostSvc,
)


def save_annotations(annotations: AVAnnotations) -> None:
    store.save_object_to_file(cmk.utils.paths.var_dir / "availability_annotations.mk", annotations)


def load_annotations(lock: bool = False) -> AVAnnotations:
    path = cmk.utils.paths.var_dir / "availability_annotations.mk"
    if not path.exists():
        # Support legacy old wrong name-clashing path
        path = cmk.utils.paths.var_dir / "web/statehist_annotations.mk"

    return store.load_object_from_file(path, default={}, lock=lock)


def update_annotations(
    site_host_svc: AVAnnotationKey,
    annotation: AVAnnotationEntry,
    replace_existing: AVAnnotationEntry | None,
) -> None:
    annotations = load_annotations(lock=True)
    entries = annotations.get(site_host_svc, [])
    new_entries = []
    for entry in entries:
        if entry == replace_existing:
            continue  # Skip existing entries with same identity
        new_entries.append(entry)
    new_entries.append(annotation)
    annotations[site_host_svc] = new_entries
    save_annotations(annotations)


def find_annotation(
    annotations: AVAnnotations,
    site_host_svc: AVAnnotationKey,
    host_state: str | None,
    service_state: str | None,
    fromtime: AVTimeStamp,
    untiltime: AVTimeStamp,
) -> AVAnnotationEntry | None:
    entries = annotations.get(site_host_svc)
    if not entries:
        return None
    for annotation in entries:
        if annotation["from"] == fromtime and annotation["until"] == untiltime:
            return annotation
    return None


def delete_annotation(
    annotations: AVAnnotations,
    site_host_svc: AVAnnotationKey,
    host_state: str | None,
    service_state: str | None,
    fromtime: AVTimeStamp,
    untiltime: AVTimeStamp,
) -> None:
    entries = annotations.get(site_host_svc)
    if not entries:
        return

    found = None
    for nr, annotation in enumerate(entries):
        if annotation["from"] == fromtime and annotation["until"] == untiltime:
            found = nr
            break

    if found is not None:
        del entries[found]


def get_relevant_annotations(
    annotations: AVAnnotations, by_host: AVRawData, what: AVObjectType, avoptions: AVOptions
) -> list[tuple[SiteHostSvc, AVAnnotationEntry]]:
    time_range: AVTimeRange = avoptions["range"][0]
    from_time, until_time = time_range

    annos_to_render: list[tuple[SiteHostSvc, AVAnnotationEntry]] = []
    annos_rendered: set[int] = set()

    for site_host, avail_entries in by_host.items():
        for service in avail_entries.keys():
            for search_what in ["host", "service"]:
                if what == "host" and search_what == "service":
                    continue  # Service annotations are not relevant for host

                if search_what == "host":
                    site_host_svc: SiteHostSvc = site_host[0], site_host[1], None
                else:
                    site_host_svc = site_host[0], site_host[1], service  # service can be None

                for annotation in annotations.get(site_host_svc, []):
                    if _annotation_affects_time_range(
                        annotation["from"], annotation["until"], from_time, until_time
                    ):
                        if id(annotation) not in annos_rendered:
                            annos_to_render.append((site_host_svc, annotation))
                            annos_rendered.add(id(annotation))

    return annos_to_render


def get_annotation_date_render_function(
    annotations: list[tuple[SiteHostSvc, AVAnnotationEntry]], avoptions: AVOptions
) -> Callable[[float | None], str]:
    timestamps = list(
        itertools.chain.from_iterable(
            [(a[1]["from"], a[1]["until"]) for a in annotations] + [avoptions["range"][0]]
        )
    )

    multi_day = len({time.localtime(t)[:3] for t in timestamps}) > 1
    if multi_day:
        return cmk.utils.render.date_and_time
    return cmk.utils.render.time_of_day


def _annotation_affects_time_range(
    annotation_from: AVTimeStamp,
    annotation_until: AVTimeStamp,
    from_time: AVTimeStamp,
    until_time: AVTimeStamp,
) -> bool:
    return not (annotation_until < from_time or annotation_from > until_time)


class ReclassifyConfig(NamedTuple):
    downtime: Any | None
    host_state: Any | None
    service_state: Any | None


def reclassify_history_by_annotations(
    history: list[AVSpan], annotation_entries: list[AVAnnotationEntry]
) -> list[AVSpan]:
    new_history = history
    for annotation in annotation_entries:
        downtime = annotation.get("downtime")
        host_state = annotation.get("host_state")
        service_state = annotation.get("service_state")
        if downtime is None and host_state is None and service_state is None:
            continue

        new_config = ReclassifyConfig(
            downtime=downtime,
            host_state=host_state,
            service_state=service_state,
        )

        new_history = reclassify_history_by_annotation(new_history, annotation, new_config)
    return new_history


def reclassify_history_by_annotation(
    history: list[AVSpan],
    annotation: AVAnnotationEntry,
    new_config: ReclassifyConfig,
) -> list[AVSpan]:
    new_history: list[AVSpan] = []
    for history_entry in history:
        new_history += reclassify_times_by_annotation(history_entry, annotation, new_config)

    return new_history


def reclassify_times_by_annotation(
    history_entry: AVSpan,
    annotation: AVAnnotationEntry,
    new_config: ReclassifyConfig,
) -> list[AVSpan]:
    new_history = []
    if annotation["from"] < history_entry["until"] and annotation["until"] > history_entry["from"]:
        for is_in, p_from, p_until in [
            (False, history_entry["from"], max(history_entry["from"], annotation["from"])),
            (
                True,
                max(history_entry["from"], annotation["from"]),
                min(history_entry["until"], annotation["until"]),
            ),
            (False, min(history_entry["until"], annotation["until"]), history_entry["until"]),
        ]:
            if p_from < p_until:
                new_entry = history_entry.copy()
                new_entry["from"] = p_from
                new_entry["until"] = p_until
                new_entry["duration"] = p_until - p_from
                if is_in:
                    reclassify_config_by_annotation(
                        history_entry, annotation, new_entry, new_config
                    )

                new_history.append(new_entry)
    else:
        new_history.append(history_entry)

    return new_history


def reclassify_config_by_annotation(
    history_entry: AVSpan,
    annotation: AVAnnotationEntry,
    new_entry: AVSpan,
    new_config: ReclassifyConfig,
) -> AVSpan:
    if new_config.downtime is not None:
        new_entry["in_downtime"] = 1 if annotation["downtime"] else 0
        # If the annotation removes a downtime from the services, but
        # the actual reason for the service being in downtime is a host
        # downtime, then we must cancel the host downtime (also), or else
        # that would override the unset service downtime.
        if history_entry.get("in_host_downtime") and annotation["downtime"] is False:
            new_entry["in_host_downtime"] = 0
    if new_config.host_state is not None:
        new_host_state = annotation.get("host_state", history_entry.get("host_state"))
        new_entry["state"] = new_host_state
        new_entry["host_down"] = 1 if new_host_state else 0
    if new_config.service_state is not None:
        new_entry["state"] = annotation.get("service_state", history_entry.get("state"))

    return new_entry
