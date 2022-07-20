#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""

This file contains helper functions for transform and transform_json. Each
function is required to handle data from the client or from JSON.
"""

import datetime
import re
from typing import Mapping, TypeGuard, Union

from .schemata import api
from .schemata.api import Label, LabelName, LabelValue


def convert_to_timestamp(kube_date_time: Union[str, datetime.datetime]) -> api.Timestamp:
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
