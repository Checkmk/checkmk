#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""

This file contains helper functions for transform and transform_json. Each
function is required to handle data from the client or from JSON.
"""
import datetime
import json
import re
from collections.abc import Mapping
from typing import Iterator, TypeGuard

from .schemata import api
from .schemata.api import Label, LabelName, LabelValue


def convert_to_timestamp(kube_date_time: str | datetime.datetime) -> api.Timestamp:
    if isinstance(kube_date_time, str):
        date_time = datetime.datetime.strptime(kube_date_time, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=datetime.timezone.utc
        )
    elif isinstance(kube_date_time, datetime.datetime):
        date_time = kube_date_time
        if date_time.tzinfo is None:
            raise ValueError(f"Can not convert to timestamp: '{kube_date_time}' is missing tzinfo")
    else:
        raise TypeError(
            f"Can not convert to timestamp: '{kube_date_time}' of type {type(kube_date_time)}"
        )

    return api.Timestamp(date_time.timestamp())


# See LabelValue for details
__validation_value = re.compile(r"(([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9])?")


def _is_valid_label_value(value: object) -> TypeGuard[LabelValue]:
    # The length of a Kubernetes label value at most 63 chars
    return isinstance(value, str) and bool(__validation_value.fullmatch(value)) and len(value) < 64


def parse_annotations(annotations: Mapping[str, str] | None) -> api.Annotations:
    """Select annotations, if they are valid.

    Kubernetes allows the annotations to be arbitrary byte strings with a
    length of at most 256Kb. The python client will try to decode these with
    utf8, but appears to return raw data if an exception occurs. We have not
    tested whether this will happen. The current commit, when this information
    was obtained, was
    https://github.com/kubernetes/kubernetes/commit/a83cc51a19d1b5f2b2d3fb75574b04f587ec0054

    Since not every annotation can be converted to a HostLabel, we decided to
    only use annotations, which are also valid Kubernetes labels. Kubernetes
    makes sure that the annotation has a valid name, so we only verify, that
    the key is also valid as a label.

    >>> parse_annotations(None)  # no annotation specified for the object
    {}
    >>> parse_annotations({
    ... '1': '',
    ... '2': 'a-',
    ... '3': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    ... '4': 'a&a',
    ... '5': 'valid-key',
    ... })
    {'1': '', '5': 'valid-key'}
    """
    if annotations is None:
        return {}
    return {LabelName(k): v for k, v in annotations.items() if _is_valid_label_value(v)}


def parse_labels(labels: Mapping[str, str] | None) -> Mapping[LabelName, Label]:
    if labels is None:
        return {}
    return {LabelName(k): Label(name=LabelName(k), value=LabelValue(v)) for k, v in labels.items()}


def parse_match_labels(labels: Mapping[str, str]) -> Mapping[LabelName, LabelValue]:
    return {LabelName(k): LabelValue(v) for k, v in labels.items()}


def parse_open_metric_samples(
    raw_response_dump: str,
) -> Iterator[api.KubeletVolumeMetricSample]:
    for raw_open_metric in raw_response_dump.split("\n"):
        if "{" not in raw_open_metric:
            continue

        open_metric_sample = _parse_metric_sample_with_labels(raw_open_metric)
        if not isinstance(open_metric_sample.__root__, api.UnusedKubeletMetricSample):
            yield open_metric_sample.__root__


def _parse_metric_sample_with_labels(
    raw_open_metric_sample: str,
) -> api.KubeletMetricSample:
    metric_name, rest = raw_open_metric_sample.split("{", 1)
    labels_string, timestamped_value = rest.rsplit("}", 1)
    value_string, *_optional_timestamp = timestamped_value.strip().split()
    labels = _parse_labels(labels_string)
    return api.KubeletMetricSample.parse_obj(
        {
            "metric_name": metric_name,
            "labels": labels,
            "value": float(value_string),
        }
    )


def _parse_labels(raw_labels: str) -> Mapping[str, str]:
    """Parse open metric formatted Kubernetes labels associated with a
    container.
    """
    labels = {}

    for label in _split_labels(raw_labels):
        label_name, label_value = label.split("=")
        labels[label_name] = json.loads(label_value)  # unquotes the string

    return labels


def _split_labels(raw_labels: str) -> Iterator[str]:
    """Split comma separated Kubernetes labels text into individual labels"""

    if not raw_labels:
        return

    # csv.reader would have been a really neat solution; however, unfortunately
    # only double quotes, and not the separator characters themselves, inside
    # value strings like this:
    #     my_val="hello",another_val="you,my\"friend\""
    # are escaped, rendering it esentially unusable...
    for label in re.split(r",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", raw_labels):
        if label:
            yield label
