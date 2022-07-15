#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping

import pytest

from tests.unit.conftest import FixRegister

from cmk.base.api.agent_based.type_defs import AgentParseFunction, AgentSectionPlugin, SectionName
from cmk.base.plugins.agent_based.utils import kube as check

from cmk.special_agents.utils_kubernetes.schemata import section as agent


@pytest.fixture(scope="module", name="kube_agent_section_models")
def get_kube_agent_section_models() -> frozenset[type[agent.Section]]:
    """Section models used by the Kubernetes special agent.

    This fixture returns the pydantic models, which are used by agent_kube to
    serialize the section data. It is assumed, that these models are
    - a subclass of agent.Section and
    - contained in the agent module.
    """
    return frozenset(
        m
        for m in agent.__dict__.values()
        if isinstance(m, type) and issubclass(m, agent.Section) and not m == agent.Section
    )


@pytest.fixture(scope="module", name="kube_agent_sections")
def get_kube_agent_sections(fix_register: FixRegister) -> Mapping[SectionName, AgentSectionPlugin]:
    return {
        name: section
        for name, section in fix_register.agent_sections.items()
        if str(name).startswith("kube_")
    }


@pytest.fixture(scope="module", name="kube_parse_functions")
def get_kube_parse_functions(
    kube_agent_sections: Mapping[SectionName, AgentSectionPlugin],
) -> Mapping[SectionName, AgentParseFunction]:

    return {name: section.parse_function for name, section in kube_agent_sections.items()}


@pytest.fixture(scope="module", name="kube_parsed_section_types")
def get_kube_parsed_section_types(
    kube_parse_functions: Mapping[SectionName, AgentParseFunction],
) -> Mapping[SectionName, object]:
    return {name: f.__annotations__["return"] for name, f in kube_parse_functions.items()}


_KNOWN_EXCEPTIONS = {
    SectionName("kube_pod_containers_v1"): check.PodContainers,
    SectionName("kube_pod_init_containers_v1"): check.PodContainers,
    SectionName("kube_start_time_v1"): check.StartTime,
}


@pytest.fixture(scope="module", name="kube_check_section_models")
def get_kube_check_section_models(
    kube_parsed_section_types: Mapping[SectionName, type],
) -> Mapping[SectionName, type[check.Section]]:
    """Section models used by parse_functions.

    This fixture returns the pydantic models, which are used by the
    parse_functions to deserialize the section data. In most cases, this model
    is also returned by the parse_function. The exception to this rule are
    maintained in _KNOWN_EXCEPTIONS.
    """
    result = kube_parsed_section_types | _KNOWN_EXCEPTIONS
    # make sure signature is not lying, also mypy is happier this way
    assert all(issubclass(model, check.Section) for model in result.values())
    return result


def test_keep_known_exceptions_up_to_date(
    kube_parsed_section_types: Mapping[SectionName, type]
) -> None:
    assert all(
        kube_parsed_section_types[name] != section for name, section in _KNOWN_EXCEPTIONS.items()
    )


def test_schema_did_not_diverge(
    kube_agent_section_models: frozenset[type[agent.Section]],
    kube_check_section_models: Mapping[SectionName, type[check.Section]],
) -> None:
    """Sync serialization and deserialization.

    Special agents are (relatively) self-contained programs and thus no code is
    shared between agent_kube and the agent_based.plugins. To ensure
    consistency, we ensure that agent_kube and agent_based.plugins uses the
    same jsonschema.
    """
    name_to_check_model = {
        m.__name__: m.schema() for m in frozenset(kube_check_section_models.values())
    }
    name_to_agent_model = {m.__name__: m.schema() for m in kube_agent_section_models}
    assert name_to_agent_model == name_to_check_model
