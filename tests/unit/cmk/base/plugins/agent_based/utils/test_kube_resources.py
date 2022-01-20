#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pydantic_factories import ModelFactory

from cmk.base.plugins.agent_based.utils import kube_resources


class ResourcesFactory(ModelFactory):
    __model__ = kube_resources.Resources


class AllocatableResourceFactory(ModelFactory):
    __model__ = kube_resources.AllocatableResource


def test_requirements_for_object_has_request_limit_ordered_as_per_kubernetes_convention() -> None:
    resources = ResourcesFactory.build()
    expected = ["request", "limit"]
    actual = [t for t, _, _ in kube_resources.requirements_for_object(resources, None)]
    assert actual == expected


def test_requirements_for_object_has_allocatable_after_limit() -> None:
    resources = ResourcesFactory.build()
    allocatable = AllocatableResourceFactory.build()
    expected = ["request", "limit", "allocatable"]
    actual = [t for t, _, _ in kube_resources.requirements_for_object(resources, allocatable)]
    assert actual == expected
