#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""

This file contains helper functions for transform and transform_json. Each
function is required to handle data from the client or from JSON.
"""

import json
import re
from collections.abc import Iterator, Mapping

from .schemata import api


def parse_match_labels(labels: Mapping[str, str]) -> Mapping[api.LabelName, api.LabelValue]:
    return {api.LabelName(k): api.LabelValue(v) for k, v in labels.items()}


def parse_open_metric_samples(
    raw_response_dump: str,
) -> Iterator[api.KubeletVolumeMetricSample]:
    for raw_open_metric in raw_response_dump.split("\n"):
        if "{" not in raw_open_metric:
            continue

        open_metric_sample = _parse_metric_sample_with_labels(raw_open_metric)
        if not isinstance(open_metric_sample.root, api.UnusedKubeletMetricSample):
            yield open_metric_sample.root


def _parse_metric_sample_with_labels(
    raw_open_metric_sample: str,
) -> api.KubeletMetricSample:
    metric_name, rest = raw_open_metric_sample.split("{", 1)
    labels_string, timestamped_value = rest.rsplit("}", 1)
    value_string, *_optional_timestamp = timestamped_value.strip().split()
    labels = _parse_labels(labels_string)
    return api.KubeletMetricSample.model_validate(
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
        label_name, label_value = label.split("=", maxsplit=1)
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
