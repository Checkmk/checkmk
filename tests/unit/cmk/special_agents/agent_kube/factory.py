#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import itertools
from typing import Iterator

from pydantic_factories import ModelFactory

from cmk.special_agents.utils_kubernetes.schemata import api

# Pod related Factories


class PodMetaDataFactory(ModelFactory):
    __model__ = api.PodMetaData


class PodSpecFactory(ModelFactory):
    __model__ = api.PodSpec


class PodStatusFactory(ModelFactory):
    __model__ = api.PodStatus


class APIPodFactory(ModelFactory):
    __model__ = api.Pod


def pod_phase_generator() -> Iterator[api.Phase]:
    yield from itertools.cycle(api.Phase)
