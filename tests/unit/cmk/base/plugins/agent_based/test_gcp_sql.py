#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import Callable, Sequence, Tuple, Union

import pytest

from cmk.base.api.agent_based.checking_classes import Service, ServiceLabel
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.gcp_sql import (
    check_gcp_sql_cpu,
    check_gcp_sql_memory,
    check_gcp_sql_status,
    discover,
    parse,
)
from cmk.base.plugins.agent_based.utils import gcp
from cmk.base.plugins.agent_based.utils.gcp import AssetSection, Section, SectionItem

SECTION_TABLE = [
    [
        '{"metric": {"type": "cloudsql.googleapis.com/database/up", "labels": {}}, "resource": {"type": "cloudsql_database", "labels": {"project_id": "tribe29-check-development", "database_id": "tribe29-check-development:checktest"}}, "metric_kind": 1, "value_type": 2, "points": [{"interval": {"start_time": "2022-03-15T12:10:45.186892Z", "end_time": "2022-03-15T12:10:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T12:09:45.186892Z", "end_time": "2022-03-15T12:09:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T12:08:45.186892Z", "end_time": "2022-03-15T12:08:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T12:07:45.186892Z", "end_time": "2022-03-15T12:07:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T12:06:45.186892Z", "end_time": "2022-03-15T12:06:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T12:05:45.186892Z", "end_time": "2022-03-15T12:05:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T12:04:45.186892Z", "end_time": "2022-03-15T12:04:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T12:03:45.186892Z", "end_time": "2022-03-15T12:03:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T12:02:45.186892Z", "end_time": "2022-03-15T12:02:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T12:01:45.186892Z", "end_time": "2022-03-15T12:01:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T12:00:45.186892Z", "end_time": "2022-03-15T12:00:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T11:59:45.186892Z", "end_time": "2022-03-15T11:59:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T11:58:45.186892Z", "end_time": "2022-03-15T11:58:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T11:57:45.186892Z", "end_time": "2022-03-15T11:57:45.186892Z"},"value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T11:56:45.186892Z", "end_time": "2022-03-15T11:56:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T11:55:45.186892Z", "end_time": "2022-03-15T11:55:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T11:54:45.186892Z", "end_time": "2022-03-15T11:54:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T11:53:45.186892Z", "end_time": "2022-03-15T11:53:45.186892Z"}, "value": {"int64_value": "1"}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "cloudsql.googleapis.com/database/network/received_bytes_count", "labels": {}}, "resource": {"type": "cloudsql_database", "labels": {"database_id": "tribe29-check-development:checktest", "project_id": "tribe29-check-development"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-03-15T12:11:45.186892Z", "end_time": "2022-03-15T12:11:45.186892Z"}, "value": {"double_value": 5176.966666666666}}, {"interval": {"start_time": "2022-03-15T12:10:45.186892Z", "end_time": "2022-03-15T12:10:45.186892Z"}, "value": {"double_value": 5238.016666666666}}, {"interval": {"start_time": "2022-03-15T12:09:45.186892Z", "end_time": "2022-03-15T12:09:45.186892Z"}, "value": {"double_value": 5199.233333333334}}, {"interval": {"start_time": "2022-03-15T12:08:45.186892Z", "end_time": "2022-03-15T12:08:45.186892Z"}, "value": {"double_value": 5457.9}}, {"interval": {"start_time": "2022-03-15T12:07:45.186892Z", "end_time": "2022-03-15T12:07:45.186892Z"}, "value": {"double_value": 8960.933333333332}}, {"interval": {"start_time":"2022-03-15T12:06:45.186892Z", "end_time": "2022-03-15T12:06:45.186892Z"}, "value": {"double_value": 5237.05}}, {"interval": {"start_time": "2022-03-15T12:05:45.186892Z", "end_time": "2022-03-15T12:05:45.186892Z"}, "value": {"double_value": 5242.65}}, {"interval": {"start_time": "2022-03-15T12:04:45.186892Z", "end_time": "2022-03-15T12:04:45.186892Z"}, "value": {"double_value": 5483.3}}, {"interval": {"start_time": "2022-03-15T12:03:45.186892Z", "end_time": "2022-03-15T12:03:45.186892Z"}, "value": {"double_value": 5191.05}}, {"interval": {"start_time": "2022-03-15T12:02:45.186892Z", "end_time": "2022-03-15T12:02:45.186892Z"}, "value": {"double_value": 5195.483333333334}}, {"interval": {"start_time": "2022-03-15T12:01:45.186892Z", "end_time": "2022-03-15T12:01:45.186892Z"}, "value": {"double_value": 5349.633333333333}}, {"interval": {"start_time": "2022-03-15T12:00:45.186892Z", "end_time": "2022-03-15T12:00:45.186892Z"}, "value": {"double_value": 5405.733333333334}}, {"interval": {"start_time": "2022-03-15T11:59:45.186892Z", "end_time": "2022-03-15T11:59:45.186892Z"}, "value": {"double_value": 5239.333333333333}}, {"interval": {"start_time": "2022-03-15T11:58:45.186892Z", "end_time": "2022-03-15T11:58:45.186892Z"}, "value": {"double_value": 5211.6}}, {"interval": {"start_time": "2022-03-15T11:57:45.186892Z", "end_time": "2022-03-15T11:57:45.186892Z"}, "value": {"double_value": 5263.566666666667}}, {"interval": {"start_time": "2022-03-15T11:56:45.186892Z", "end_time":"2022-03-15T11:56:45.186892Z"}, "value": {"double_value": 5477.433333333333}}, {"interval": {"start_time": "2022-03-15T11:55:45.186892Z", "end_time": "2022-03-15T11:55:45.186892Z"}, "value": {"double_value": 5290.6}}, {"interval": {"start_time": "2022-03-15T11:54:45.186892Z", "end_time": "2022-03-15T11:54:45.186892Z"}, "value": {"double_value": 5397.183333333333}}, {"interval": {"start_time": "2022-03-15T11:53:45.186892Z", "end_time": "2022-03-15T11:53:45.186892Z"}, "value": {"double_value": 5359.733333333334}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "cloudsql.googleapis.com/database/network/sent_bytes_count", "labels": {}}, "resource": {"type": "cloudsql_database", "labels": {"project_id": "tribe29-check-development", "database_id": "tribe29-check-development:checktest"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-03-15T12:11:45.186892Z", "end_time": "2022-03-15T12:11:45.186892Z"}, "value": {"double_value": 17443.083333333332}}, {"interval": {"start_time": "2022-03-15T12:10:45.186892Z", "end_time": "2022-03-15T12:10:45.186892Z"}, "value": {"double_value": 16112.366666666667}}, {"interval": {"start_time": "2022-03-15T12:09:45.186892Z", "end_time": "2022-03-15T12:09:45.186892Z"}, "value": {"double_value": 17166.633333333335}}, {"interval": {"start_time": "2022-03-15T12:08:45.186892Z", "end_time": "2022-03-15T12:08:45.186892Z"}, "value": {"double_value": 16234.283333333333}}, {"interval": {"start_time": "2022-03-15T12:07:45.186892Z", "end_time": "2022-03-15T12:07:45.186892Z"}, "value": {"double_value": 20479.316666666666}}, {"interval": {"start_time": "2022-03-15T12:06:45.186892Z", "end_time": "2022-03-15T12:06:45.186892Z"}, "value": {"double_value": 17990.483333333334}}, {"interval": {"start_time": "2022-03-15T12:05:45.186892Z", "end_time": "2022-03-15T12:05:45.186892Z"}, "value": {"double_value": 16119.55}}, {"interval": {"start_time": "2022-03-15T12:04:45.186892Z", "end_time": "2022-03-15T12:04:45.186892Z"}, "value": {"double_value": 17360.483333333334}}, {"interval": {"start_time": "2022-03-15T12:03:45.186892Z", "end_time": "2022-03-15T12:03:45.186892Z"}, "value": {"double_value": 16119.2}}, {"interval": {"start_time": "2022-03-15T12:02:45.186892Z", "end_time": "2022-03-15T12:02:45.186892Z"}, "value": {"double_value": 16953.266666666666}}, {"interval": {"start_time": "2022-03-15T12:01:45.186892Z", "end_time": "2022-03-15T12:01:45.186892Z"}, "value": {"double_value": 17651.633333333335}}, {"interval": {"start_time": "2022-03-15T12:00:45.186892Z", "end_time": "2022-03-15T12:00:45.186892Z"}, "value": {"double_value": 16584.75}}, {"interval": {"start_time": "2022-03-15T11:59:45.186892Z", "end_time": "2022-03-15T11:59:45.186892Z"}, "value": {"double_value": 16632.0}}, {"interval": {"start_time": "2022-03-15T11:58:45.186892Z", "end_time": "2022-03-15T11:58:45.186892Z"}, "value": {"double_value": 16681.166666666668}}, {"interval": {"start_time": "2022-03-15T11:57:45.186892Z", "end_time": "2022-03-15T11:57:45.186892Z"}, "value": {"double_value": 17043.283333333333}}, {"interval": {"start_time": "2022-03-15T11:56:45.186892Z", "end_time": "2022-03-15T11:56:45.186892Z"}, "value": {"double_value": 17707.433333333334}}, {"interval": {"start_time": "2022-03-15T11:55:45.186892Z", "end_time": "2022-03-15T11:55:45.186892Z"}, "value": {"double_value": 16710.4}}, {"interval": {"start_time": "2022-03-15T11:54:45.186892Z", "end_time": "2022-03-15T11:54:45.186892Z"}, "value": {"double_value": 16489.916666666668}}, {"interval": {"start_time": "2022-03-15T11:53:45.186892Z", "end_time": "2022-03-15T11:53:45.186892Z"}, "value": {"double_value": 16583.05}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "cloudsql.googleapis.com/database/memory/utilization", "labels": {}}, "resource": {"type": "cloudsql_database", "labels": {"project_id": "tribe29-check-development", "database_id": "tribe29-check-development:checktest"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-03-15T12:10:45.186892Z", "end_time": "2022-03-15T12:10:45.186892Z"}, "value": {"double_value": 0.09334965707848912}}, {"interval": {"start_time": "2022-03-15T12:09:45.186892Z", "end_time": "2022-03-15T12:09:45.186892Z"}, "value": {"double_value": 0.09338921284327736}}, {"interval": {"start_time": "2022-03-15T12:08:45.186892Z", "end_time": "2022-03-15T12:08:45.186892Z"}, "value": {"double_value": 0.09339385764899114}}, {"interval": {"start_time": "2022-03-15T12:07:45.186892Z", "end_time": "2022-03-15T12:07:45.186892Z"}, "value": {"double_value": 0.09334905774871961}}, {"interval": {"start_time": "2022-03-15T12:06:45.186892Z", "end_time": "2022-03-15T12:06:45.186892Z"}, "value": {"double_value": 0.09335804769526239}}, {"interval": {"start_time": "2022-03-15T12:05:45.186892Z", "end_time": "2022-03-15T12:05:45.186892Z"}, "value": {"double_value": 0.09337977339940744}}, {"interval": {"start_time": "2022-03-15T12:04:45.186892Z", "end_time": "2022-03-15T12:04:45.186892Z"}, "value": {"double_value": 0.0934118375420767}}, {"interval": {"start_time": "2022-03-15T12:03:45.186892Z", "end_time": "2022-03-15T12:03:45.186892Z"}, "value": {"double_value": 0.09336449049028471}}, {"interval": {"start_time": "2022-03-15T12:02:45.186892Z", "end_time": "2022-03-15T12:02:45.186892Z"}, "value": {"double_value": 0.09334216545637014}}, {"interval": {"start_time": "2022-03-15T12:01:45.186892Z", "end_time": "2022-03-15T12:01:45.186892Z"}, "value": {"double_value": 0.09335325305710623}}, {"interval": {"start_time": "2022-03-15T12:00:45.186892Z", "end_time": "2022-03-15T12:00:45.186892Z"}, "value": {"double_value": 0.0933659888147085}}, {"interval": {"start_time": "2022-03-15T11:59:45.186892Z", "end_time": "2022-03-15T11:59:45.186892Z"}, "value": {"double_value": 0.0933853171997755}}, {"interval": {"start_time": "2022-03-15T11:58:45.186892Z", "end_time": "2022-03-15T11:58:45.186892Z"}, "value": {"double_value": 0.09335969585212857}}, {"interval": {"start_time": "2022-03-15T11:57:45.186892Z", "end_time": "2022-03-15T11:57:45.186892Z"}, "value": {"double_value": 0.09334231528881252}}, {"interval": {"start_time": "2022-03-15T11:56:45.186892Z", "end_time": "2022-03-15T11:56:45.186892Z"}, "value": {"double_value": 0.09336254266853378}}, {"interval": {"start_time": "2022-03-15T11:55:45.186892Z", "end_time": "2022-03-15T11:55:45.186892Z"}, "value": {"double_value": 0.09336523965249661}}, {"interval": {"start_time": "2022-03-15T11:54:45.186892Z", "end_time": "2022-03-15T11:54:45.186892Z"}, "value": {"double_value": 0.09336404099295757}}, {"interval": {"start_time": "2022-03-15T11:53:45.186892Z", "end_time": "2022-03-15T11:53:45.186892Z"}, "value": {"double_value": 0.09337602758834795}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "cloudsql.googleapis.com/database/cpu/utilization", "labels": {}}, "resource": {"type": "cloudsql_database", "labels": {"project_id": "tribe29-check-development", "database_id": "tribe29-check-development:checktest"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-03-15T12:10:45.186892Z", "end_time": "2022-03-15T12:10:45.186892Z"}, "value": {"double_value": 0.013087989967803774}}, {"interval": {"start_time": "2022-03-15T12:09:45.186892Z", "end_time": "2022-03-15T12:09:45.186892Z"}, "value": {"double_value": 0.012672818401661345}}, {"interval": {"start_time": "2022-03-15T12:08:45.186892Z", "end_time": "2022-03-15T12:08:45.186892Z"}, "value": {"double_value": 0.013488882986159467}}, {"interval": {"start_time": "2022-03-15T12:07:45.186892Z", "end_time": "2022-03-15T12:07:45.186892Z"}, "value": {"double_value": 0.014496929856982869}}, {"interval": {"start_time": "2022-03-15T12:06:45.186892Z", "end_time": "2022-03-15T12:06:45.186892Z"}, "value": {"double_value": 0.013904319665215088}}, {"interval": {"start_time": "2022-03-15T12:05:45.186892Z", "end_time": "2022-03-15T12:05:45.186892Z"}, "value": {"double_value": 0.01338267950601401}}, {"interval": {"start_time": "2022-03-15T12:04:45.186892Z", "end_time": "2022-03-15T12:04:45.186892Z"}, "value": {"double_value": 0.012998424167034747}}, {"interval": {"start_time": "2022-03-15T12:03:45.186892Z", "end_time": "2022-03-15T12:03:45.186892Z"}, "value": {"double_value": 0.013400508641464151}}, {"interval": {"start_time": "2022-03-15T12:02:45.186892Z", "end_time": "2022-03-15T12:02:45.186892Z"}, "value": {"double_value": 0.014177463508075286}}, {"interval": {"start_time": "2022-03-15T12:01:45.186892Z", "end_time": "2022-03-15T12:01:45.186892Z"}, "value": {"double_value": 0.013153952654619161}}, {"interval": {"start_time": "2022-03-15T12:00:45.186892Z", "end_time": "2022-03-15T12:00:45.186892Z"},"value": {"double_value": 0.012025448297467278}}, {"interval": {"start_time": "2022-03-15T11:59:45.186892Z", "end_time": "2022-03-15T11:59:45.186892Z"}, "value": {"double_value": 0.011814011703310949}}, {"interval": {"start_time": "2022-03-15T11:58:45.186892Z", "end_time": "2022-03-15T11:58:45.186892Z"}, "value": {"double_value": 0.012254220290575308}}, {"interval": {"start_time": "2022-03-15T11:57:45.186892Z", "end_time": "2022-03-15T11:57:45.186892Z"}, "value": {"double_value": 0.012846020411788336}}, {"interval": {"start_time": "2022-03-15T11:56:45.186892Z", "end_time": "2022-03-15T11:56:45.186892Z"}, "value": {"double_value": 0.012598779307621537}}, {"interval": {"start_time": "2022-03-15T11:55:45.186892Z", "end_time": "2022-03-15T11:55:45.186892Z"}, "value": {"double_value": 0.01285304995199136}}, {"interval": {"start_time": "2022-03-15T11:54:45.186892Z", "end_time": "2022-03-15T11:54:45.186892Z"}, "value": {"double_value": 0.012780085063349845}}, {"interval": {"start_time": "2022-03-15T11:53:45.186892Z", "end_time": "2022-03-15T11:53:45.186892Z"}, "value": {"double_value": 0.013482351061049986}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "cloudsql.googleapis.com/database/state", "labels": {}}, "resource": {"type": "cloudsql_database", "labels": {"region": "us-central", "project_id": "tribe29-check-development", "database_id": "tribe29-check-development:checktest"}}, "metric_kind": 1, "value_type": 4, "points": [{"interval": {"start_time": "2022-03-15T12:10:45.186892Z", "end_time": "2022-03-15T12:10:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T12:09:45.186892Z", "end_time": "2022-03-15T12:09:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T12:08:45.186892Z", "end_time": "2022-03-15T12:08:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T12:07:45.186892Z", "end_time": "2022-03-15T12:07:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T12:06:45.186892Z", "end_time": "2022-03-15T12:06:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T12:05:45.186892Z", "end_time": "2022-03-15T12:05:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T12:04:45.186892Z", "end_time": "2022-03-15T12:04:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T12:03:45.186892Z", "end_time": "2022-03-15T12:03:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T12:02:45.186892Z", "end_time": "2022-03-15T12:02:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T12:01:45.186892Z", "end_time": "2022-03-15T12:01:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T12:00:45.186892Z", "end_time": "2022-03-15T12:00:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T11:59:45.186892Z", "end_time": "2022-03-15T11:59:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T11:58:45.186892Z", "end_time": "2022-03-15T11:58:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T11:57:45.186892Z", "end_time": "2022-03-15T11:57:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T11:56:45.186892Z", "end_time": "2022-03-15T11:56:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T11:55:45.186892Z", "end_time": "2022-03-15T11:55:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T11:54:45.186892Z", "end_time": "2022-03-15T11:54:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T11:53:45.186892Z", "end_time": "2022-03-15T11:53:45.186892Z"}, "value": {"string_value": "RUNNING"}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "cloudsql.googleapis.com/database/disk/write_ops_count", "labels": {}}, "resource": {"type": "cloudsql_database", "labels": {"project_id": "tribe29-check-development", "database_id": "tribe29-check-development:checktest"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-03-15T12:10:45.186892Z", "end_time": "2022-03-15T12:10:45.186892Z"}, "value": {"double_value": 541.0}}, {"interval": {"start_time": "2022-03-15T12:09:45.186892Z", "end_time": "2022-03-15T12:09:45.186892Z"}, "value": {"double_value": 569.0}}, {"interval": {"start_time": "2022-03-15T12:08:45.186892Z", "end_time": "2022-03-15T12:08:45.186892Z"}, "value": {"double_value": 531.0}}, {"interval": {"start_time": "2022-03-15T12:07:45.186892Z", "end_time": "2022-03-15T12:07:45.186892Z"}, "value": {"double_value": 571.0}}, {"interval": {"start_time": "2022-03-15T12:06:45.186892Z", "end_time": "2022-03-15T12:06:45.186892Z"}, "value": {"double_value": 563.0}}, {"interval": {"start_time": "2022-03-15T12:05:45.186892Z", "end_time": "2022-03-15T12:05:45.186892Z"}, "value": {"double_value": 529.0}}, {"interval": {"start_time": "2022-03-15T12:04:45.186892Z", "end_time": "2022-03-15T12:04:45.186892Z"}, "value": {"double_value": 495.0}}, {"interval": {"start_time": "2022-03-15T12:03:45.186892Z", "end_time": "2022-03-15T12:03:45.186892Z"}, "value": {"double_value": 518.0}}, {"interval": {"start_time": "2022-03-15T12:02:45.186892Z", "end_time": "2022-03-15T12:02:45.186892Z"}, "value": {"double_value": 508.0}}, {"interval": {"start_time": "2022-03-15T12:01:45.186892Z", "end_time": "2022-03-15T12:01:45.186892Z"}, "value": {"double_value": 559.0}}, {"interval": {"start_time": "2022-03-15T12:00:45.186892Z", "end_time": "2022-03-15T12:00:45.186892Z"}, "value": {"double_value": 542.0}}, {"interval": {"start_time": "2022-03-15T11:59:45.186892Z", "end_time": "2022-03-15T11:59:45.186892Z"}, "value": {"double_value": 542.0}}, {"interval": {"start_time": "2022-03-15T11:58:45.186892Z", "end_time": "2022-03-15T11:58:45.186892Z"}, "value": {"double_value": 565.0}}, {"interval": {"start_time": "2022-03-15T11:57:45.186892Z", "end_time": "2022-03-15T11:57:45.186892Z"}, "value": {"double_value": 532.0}}, {"interval": {"start_time": "2022-03-15T11:56:45.186892Z", "end_time": "2022-03-15T11:56:45.186892Z"}, "value": {"double_value": 536.0}}, {"interval": {"start_time": "2022-03-15T11:55:45.186892Z", "end_time": "2022-03-15T11:55:45.186892Z"}, "value": {"double_value": 560.0}}, {"interval": {"start_time": "2022-03-15T11:54:45.186892Z", "end_time": "2022-03-15T11:54:45.186892Z"}, "value": {"double_value": 515.0}}, {"interval": {"start_time": "2022-03-15T11:53:45.186892Z", "end_time": "2022-03-15T11:53:45.186892Z"}, "value": {"double_value": 496.0}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "cloudsql.googleapis.com/database/disk/read_ops_count", "labels": {}}, "resource": {"type": "cloudsql_database", "labels": {"project_id": "tribe29-check-development", "database_id": "tribe29-check-development:checktest"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-03-15T12:11:45.186892Z", "end_time": "2022-03-15T12:11:45.186892Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-15T12:10:45.186892Z", "end_time": "2022-03-15T12:10:45.186892Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-15T12:09:45.186892Z", "end_time": "2022-03-15T12:09:45.186892Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-15T12:08:45.186892Z", "end_time": "2022-03-15T12:08:45.186892Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-15T12:07:45.186892Z", "end_time": "2022-03-15T12:07:45.186892Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-15T12:06:45.186892Z", "end_time": "2022-03-15T12:06:45.186892Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-15T12:05:45.186892Z", "end_time": "2022-03-15T12:05:45.186892Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-15T12:04:45.186892Z", "end_time": "2022-03-15T12:04:45.186892Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-15T12:03:45.186892Z", "end_time": "2022-03-15T12:03:45.186892Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-15T12:02:45.186892Z", "end_time": "2022-03-15T12:02:45.186892Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-15T12:01:45.186892Z", "end_time": "2022-03-15T12:01:45.186892Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-15T12:00:45.186892Z", "end_time": "2022-03-15T12:00:45.186892Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-15T11:59:45.186892Z", "end_time": "2022-03-15T11:59:45.186892Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-15T11:58:45.186892Z", "end_time": "2022-03-15T11:58:45.186892Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-15T11:57:45.186892Z", "end_time": "2022-03-15T11:57:45.186892Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-15T11:56:45.186892Z", "end_time": "2022-03-15T11:56:45.186892Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-15T11:55:45.186892Z", "end_time": "2022-03-15T11:55:45.186892Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-15T11:54:45.186892Z", "end_time": "2022-03-15T11:54:45.186892Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-15T11:53:45.186892Z", "end_time": "2022-03-15T11:53:45.186892Z"}, "value": {"double_value": 0.0}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "cloudsql.googleapis.com/database/disk/utilization", "labels": {}}, "resource": {"type": "cloudsql_database", "labels": {"project_id": "tribe29-check-development", "database_id": "tribe29-check-development:checktest"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-03-15T12:11:45.186892Z", "end_time": "2022-03-15T12:11:45.186892Z"}, "value": {"double_value": 0.05669390630118181}}, {"interval": {"start_time": "2022-03-15T12:10:45.186892Z", "end_time": "2022-03-15T12:10:45.186892Z"}, "value": {"double_value": 0.05669390630118181}}, {"interval": {"start_time": "2022-03-15T12:09:45.186892Z", "end_time": "2022-03-15T12:09:45.186892Z"}, "value": {"double_value": 0.05669390630118181}}, {"interval": {"start_time": "2022-03-15T12:08:45.186892Z", "end_time": "2022-03-15T12:08:45.186892Z"}, "value": {"double_value": 0.05669390630118181}}, {"interval": {"start_time": "2022-03-15T12:07:45.186892Z", "end_time": "2022-03-15T12:07:45.186892Z"}, "value": {"double_value": 0.05669390630118181}}, {"interval": {"start_time": "2022-03-15T12:06:45.186892Z", "end_time": "2022-03-15T12:06:45.186892Z"}, "value": {"double_value": 0.05669390630118181}}, {"interval": {"start_time": "2022-03-15T12:05:45.186892Z", "end_time": "2022-03-15T12:05:45.186892Z"}, "value": {"double_value": 0.05669390630118181}}, {"interval": {"start_time": "2022-03-15T12:04:45.186892Z", "end_time": "2022-03-15T12:04:45.186892Z"}, "value": {"double_value": 0.05669390630118181}}, {"interval": {"start_time": "2022-03-15T12:03:45.186892Z", "end_time": "2022-03-15T12:03:45.186892Z"}, "value": {"double_value": 0.05669390630118181}}, {"interval": {"start_time": "2022-03-15T12:02:45.186892Z", "end_time": "2022-03-15T12:02:45.186892Z"}, "value": {"double_value": 0.05669390630118181}}, {"interval": {"start_time": "2022-03-15T12:01:45.186892Z", "end_time": "2022-03-15T12:01:45.186892Z"}, "value": {"double_value": 0.05669390630118181}}, {"interval": {"start_time": "2022-03-15T12:00:45.186892Z", "end_time": "2022-03-15T12:00:45.186892Z"}, "value": {"double_value": 0.05669390630118181}}, {"interval": {"start_time": "2022-03-15T11:59:45.186892Z", "end_time": "2022-03-15T11:59:45.186892Z"}, "value": {"double_value": 0.05669390630118181}}, {"interval": {"start_time": "2022-03-15T11:58:45.186892Z", "end_time": "2022-03-15T11:58:45.186892Z"}, "value": {"double_value": 0.05669390630118181}}, {"interval": {"start_time": "2022-03-15T11:57:45.186892Z", "end_time": "2022-03-15T11:57:45.186892Z"}, "value": {"double_value": 0.05669390630118181}}, {"interval": {"start_time": "2022-03-15T11:56:45.186892Z", "end_time": "2022-03-15T11:56:45.186892Z"}, "value": {"double_value": 0.05669390630118181}}, {"interval": {"start_time": "2022-03-15T11:55:45.186892Z", "end_time": "2022-03-15T11:55:45.186892Z"}, "value": {"double_value": 0.05669390630118181}}, {"interval": {"start_time": "2022-03-15T11:54:45.186892Z", "end_time": "2022-03-15T11:54:45.186892Z"}, "value":{"double_value": 0.05669390630118181}}, {"interval": {"start_time": "2022-03-15T11:53:45.186892Z", "end_time": "2022-03-15T11:53:45.186892Z"}, "value": {"double_value": 0.05669390630118181}}], "unit": ""}'
    ],
]

ASSET_TABLE = [
    ['{"project":"backup-255820"}'],
    [
        '{"name": "//cloudsql.googleapis.com/projects/tribe29-check-development/instances/checktest", "asset_type": "sqladmin.googleapis.com/Instance", "resource": {"version": "v1beta4", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/sqladmin/v1beta4/rest", "discovery_name": "DatabaseInstance", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {"serviceAccountEmailAddress": "p1074106860578-yhxe0q@gcp-sa-cloud-sql.iam.gserviceaccount.com", "instanceType": "CLOUDSQL_INSTANCE", "settings": {"dataDiskSizeGb": "20", "kind": "sql#settings", "storageAutoResize": true, "availabilityType": "ZONAL", "settingsVersion": "1", "backupConfiguration": {"kind": "sql#backupConfiguration", "backupRetentionSettings": {"retainedBackups": 7.0, "retentionUnit": "COUNT"}, "startTime": "01:00", "enabled": true, "transactionLogRetentionDays": 7.0, "binaryLogEnabled": false, "location": "us"}, "userLabels": {"reason": "check-development", "team": "dev"}, "activationPolicy": "ALWAYS", "replicationType": "SYNCHRONOUS", "pricingPlan": "PER_USE", "locationPreference": {"kind": "sql#locationPreference", "zone": "us-central1-f"}, "storageAutoResizeLimit": "0", "dataDiskType": "PD_HDD", "ipConfiguration": {"ipv4Enabled": true}, "tier": "db-custom-4-26624", "maintenanceWindow": {"hour": 0.0, "day": 0.0, "kind": "sql#maintenanceWindow"}}, "ipAddresses": [{"ipAddress": "34.121.172.190", "type": "PRIMARY"}], "selfLink": "https://sqladmin.googleapis.com/sql/v1beta4/projects/tribe29-check-development/instances/checktest", "region": "us-central1", "backendType": "SECOND_GEN", "databaseInstalledVersion": "MYSQL_5_7_36", "createTime": "2022-03-15T08:48:13.998Z", "connectionName": "tribe29-check-development:us-central1:checktest", "kind": "sql#instance", "serverCaCert": {"expirationTime": "2032-03-12T08:51:12.19Z", "kind": "sql#sslCert", "certSerialNumber": "0", "instance": "checktest", "sha1Fingerprint": "05e6c602375a78bd86ca46d9b80709d9bb43a0f2", "createTime": "2022-03-15T08:50:12.19Z", "commonName": "C=US,O=Google\\\\, Inc,CN=Google Cloud SQL Server CA,dnQualifier=8c6bc987-8655-4ff1-aebc-01d408409866"}, "databaseVersion": "MYSQL_5_7", "gceZone": "us-central1-f", "project": "tribe29-check-development", "state": "RUNNABLE", "name": "checktest"}, "location": "us-central1", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-03-15T08:53:30.997492Z", "org_policy": []}'
    ],
]


def test_parse_gcp():
    section = parse(SECTION_TABLE)
    n_rows = sum(len(i.rows) for i in section.values())
    assert n_rows == len(SECTION_TABLE)


@pytest.fixture(name="asset_section")
def fixture_asset_section() -> AssetSection:
    return gcp.parse_assets(ASSET_TABLE)


@pytest.fixture(name="sql_services")
def fixture_sql_services(asset_section: AssetSection) -> Sequence[Service]:
    return sorted(discover(section_gcp_service_cloud_sql=None, section_gcp_assets=asset_section))


def test_no_asset_section_yields_no_service():
    assert len(list(discover(section_gcp_service_cloud_sql=None, section_gcp_assets=None))) == 0


def test_discover_two_sql_services(sql_services: Sequence[Service]):
    assert {b.item for b in sql_services} == {"checktest"}


def test_discover_project_labels(sql_services: Sequence[Service]):
    for service in sql_services:
        assert ServiceLabel("gcp/projectId", "backup-255820") in service.labels


def test_discover_labels(sql_services: Sequence[Service]):
    labels = sql_services[0].labels
    assert set(labels) == {
        ServiceLabel("gcp/labels/reason", "check-development"),
        ServiceLabel("gcp/cloud_sql/name", "checktest"),
        ServiceLabel("gcp/cloud_sql/databaseVersion", "MYSQL_5_7"),
        ServiceLabel("gcp/labels/team", "dev"),
        ServiceLabel("gcp/cloud_sql/availability", "ZONAL"),
        ServiceLabel("gcp/location", "us-central1"),
        ServiceLabel("gcp/projectId", "backup-255820"),
    }


ITEM = "checktest"


@pytest.fixture(name="section")
def fixture_section() -> Section:
    return parse(SECTION_TABLE)


@pytest.mark.parametrize("state", (State.OK, State.WARN, State.CRIT))
def test_gcp_sql_status_params(section, state):
    params = {"RUNNING": state}
    results = list(
        check_gcp_sql_status(
            item=ITEM, params=params, section_gcp_service_cloud_sql=section, section_gcp_assets=None
        )
    )
    assert len(results) == 3
    result = results[-1]
    assert isinstance(result, Result)
    assert result == Result(state=state, summary="State: RUNNING")


def test_gcp_sql_status_metric(section):
    params = {"RUNNING": State.UNKNOWN}
    results = list(
        check_gcp_sql_status(
            item=ITEM,
            params=params,
            section_gcp_service_cloud_sql=section,
            section_gcp_assets=None,
        )
    )
    assert len(results) == 3
    result = results[1]
    assert isinstance(result, Metric)
    assert result.value == 1.0


def test_gcp_sql_status_no_state_metric_in_available_metrics():
    params = {"RUNNING": State.UNKNOWN}
    results = list(
        check_gcp_sql_status(
            item=ITEM,
            params=params,
            section_gcp_service_cloud_sql={"checktest": SectionItem(rows=[])},
            section_gcp_assets=None,
        )
    )
    assert len(results) == 3
    result = results[-1]
    assert isinstance(result, Result)
    assert result == Result(state=State.UNKNOWN, summary="No data available")


def test_gcp_sql_status_no_agent_data_is_no_result():
    assert [] == list(
        check_gcp_sql_status(
            item=ITEM,
            params={},
            section_gcp_service_cloud_sql=None,
            section_gcp_assets=None,
        )
    )


def test_gcp_sql_status_no_results_if_item_not_found(section: gcp.Section):
    params = {k: None for k in ["requests"]}
    results = (
        el
        for el in check_gcp_sql_status(
            item="I do not exist",
            params=params,
            section_gcp_service_cloud_sql=section,
            section_gcp_assets=None,
        )
        if isinstance(el, Metric)
    )
    assert list(results) == []


@dataclass(frozen=True)
class Plugin:
    metrics: Sequence[str]
    function: Callable


PLUGINS = [
    Plugin(
        function=check_gcp_sql_cpu,
        metrics=[
            "util",
        ],
    ),
    Plugin(
        function=check_gcp_sql_memory,
        metrics=[
            "memory_util",
        ],
    ),
]


@pytest.fixture(params=PLUGINS, name="checkplugin")
def fixture_checkplugin(request) -> Plugin:
    return request.param


Results = Tuple[Sequence[Union[Metric, Result]], Plugin]


@pytest.fixture(name="results_and_plugin")
def fixture_results(checkplugin: Plugin, section: Section) -> Results:
    params = {k: None for k in checkplugin.metrics}
    results = list(
        checkplugin.function(
            item=ITEM, params=params, section_gcp_service_cloud_sql=section, section_gcp_assets=None
        )
    )
    return results, checkplugin


def test_no_sql_section_yields_no_metric_data(checkplugin):
    params = {k: None for k in checkplugin.metrics}
    results = list(
        checkplugin.function(
            item=ITEM,
            params=params,
            section_gcp_service_cloud_sql=None,
            section_gcp_assets=None,
        )
    )
    assert len(results) == 0


def test_yield_metrics_as_specified(results_and_plugin: Results):
    results, checkplugin = results_and_plugin
    res = {r.name: r for r in results if isinstance(r, Metric)}
    assert len(res) == len(checkplugin.metrics)
    assert set(res.keys()) == set(checkplugin.metrics)


def test_yield_results_as_specified(results_and_plugin: Results):
    results, checkplugin = results_and_plugin
    res = [r for r in results if isinstance(r, Result)]
    assert len(res) == len(checkplugin.metrics)
    for r in res:
        assert r.state == State.OK


class TestConfiguredNotificationLevels:
    # In the example sections we do not have data for all metrics. To be able to test all check plugins
    # use 0, the default value, to check notification levels.
    def test_warn_levels(self, checkplugin: Plugin, section: Section):
        params = {k: (0, None) for k in checkplugin.metrics}
        results = list(
            checkplugin.function(
                item=ITEM,
                params=params,
                section_gcp_service_cloud_sql=section,
                section_gcp_assets=None,
            )
        )
        results = [r for r in results if isinstance(r, Result)]
        for r in results:
            assert r.state == State.WARN

    def test_crit_levels(self, checkplugin: Plugin, section: Section):
        params = {k: (None, 0) for k in checkplugin.metrics}
        results = list(
            checkplugin.function(
                item=ITEM,
                params=params,
                section_gcp_service_cloud_sql=section,
                section_gcp_assets=None,
            )
        )
        results = [r for r in results if isinstance(r, Result)]
        for r in results:
            assert r.state == State.CRIT


def test_no_results_if_item_not_found(section: gcp.Section, checkplugin: Plugin):
    params = {k: None for k in ["requests"]}
    results = (
        el
        for el in checkplugin.function(
            item="I do not exist",
            params=params,
            section_gcp_service_cloud_sql=section,
            section_gcp_assets=None,
        )
        if isinstance(el, Metric)
    )
    assert list(results) == []
