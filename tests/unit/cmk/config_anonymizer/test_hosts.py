#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Host attributes that carry host names have to be anonymized like the host names themselves."""

import logging
from pathlib import Path

import pytest

from cmk.config_anonymizer.interface import AnonInterface
from cmk.config_anonymizer.plugins.hosts import (
    _anonymize_host_tag,
    _anonymize_single_host_and_folder_attributes,
    TagIDs,
)

_BUILTIN_TAG_IDS = frozenset({"agent", "tcp"})
_NO_CUSTOM_AUX_TAGS = TagIDs(builtin=_BUILTIN_TAG_IDS, custom_aux=frozenset())


def _anon_interface() -> AnonInterface:
    return AnonInterface(Path("test"), {}, logging.getLogger("test"))


@pytest.mark.usefixtures("patch_omd_site")
def test_a_relation_hides_the_host_it_names() -> None:
    anon_interface = _anon_interface()

    anonymized = _anonymize_single_host_and_folder_attributes(
        anon_interface,
        _NO_CUSTOM_AUX_TAGS,
        {"relations": [{"kind": "management", "direction": "parent", "host": "os1"}]},
    )

    assert anonymized["relations"] == [
        {"kind": "management", "direction": "parent", "host": anon_interface.get_host("os1")}
    ]
    assert "os1" not in str(anonymized["relations"])


@pytest.mark.usefixtures("patch_omd_site")
def test_a_malformed_relations_value_is_dropped_rather_than_leaked() -> None:
    """A hand written "hosts.mk" is exactly what an anonymized dump is taken of."""
    anonymized = _anonymize_single_host_and_folder_attributes(
        _anon_interface(), _NO_CUSTOM_AUX_TAGS, {"relations": "os1"}
    )

    assert anonymized["relations"] == []


@pytest.mark.usefixtures("patch_omd_site")
def test_a_metrics_association_attribute_filter_hides_its_attributes() -> None:
    anon_interface = _anon_interface()
    attribute_filter = {
        "type": "and",
        "conjuncts": [
            {
                "type": "equals",
                "key": {"kind": "resource", "name": "service.name"},
                "value": "checkout",
            },
            {"type": "not", "condition": {"type": "exists", "key": {"kind": "scope", "name": "x"}}},
        ],
    }

    anonymized = _anonymize_single_host_and_folder_attributes(
        anon_interface,
        _NO_CUSTOM_AUX_TAGS,
        {
            "metrics_association": (
                "enabled",
                {
                    "host_name_lookup_rules": [
                        {
                            "resource_attributes": [],
                            "scope_attributes": [],
                            "data_point_attributes": [],
                            "attribute_filter": attribute_filter,
                        }
                    ]
                },
            )
        },
    )

    key = anon_interface.get_generic_mapping
    assert anonymized["metrics_association"] == {
        "host_name_lookup_rules": [
            {
                "resource_attributes": [],
                "scope_attributes": [],
                "data_point_attributes": [],
                "attribute_filter": {
                    "type": "and",
                    "conjuncts": [
                        {
                            "type": "equals",
                            "key": {
                                "kind": "resource",
                                "name": key("service.name", "metric_association_attr_key"),
                            },
                            "value": key("checkout", "metric_association_attr_value"),
                        },
                        {
                            "type": "not",
                            "condition": {
                                "type": "exists",
                                "key": {
                                    "kind": "scope",
                                    "name": key("x", "metric_association_attr_key"),
                                },
                            },
                        },
                    ],
                },
            }
        ]
    }
    assert "service.name" not in str(anonymized) and "checkout" not in str(anonymized)


def test_a_builtin_aux_tag_of_a_host_is_kept() -> None:
    """ "agent: cmk-agent" implies "tcp: tcp". Rules match on it, so it must survive."""
    anonymized = _anonymize_host_tag(_anon_interface(), _NO_CUSTOM_AUX_TAGS, "tcp", "tcp")

    assert anonymized == ("tcp", "tcp")


def test_a_custom_aux_tag_of_a_host_gets_the_id_of_the_anonymized_aux_tag() -> None:
    anon_interface = _anon_interface()
    tag_ids = TagIDs(builtin=_BUILTIN_TAG_IDS, custom_aux=frozenset({"dmz"}))

    anonymized = _anonymize_host_tag(anon_interface, tag_ids, "dmz", "dmz")

    anon_aux_tag_id = anon_interface.get_id_of_aux_tag("dmz")
    assert anonymized == (anon_aux_tag_id, anon_aux_tag_id)


def test_a_custom_tag_of_a_host_gets_the_ids_of_the_anonymized_tag_group() -> None:
    anon_interface = _anon_interface()

    anonymized = _anonymize_host_tag(anon_interface, _NO_CUSTOM_AUX_TAGS, "location", "munich")

    assert anonymized == (
        anon_interface.get_id_of_tag_group("location"),
        anon_interface.get_id_of_tag("munich"),
    )


@pytest.mark.usefixtures("patch_omd_site")
def test_a_custom_tag_attribute_stays_a_tag_attribute_of_the_anonymized_tag_group() -> None:
    anon_interface = _anon_interface()

    anonymized = _anonymize_single_host_and_folder_attributes(
        anon_interface, _NO_CUSTOM_AUX_TAGS, {"tag_location": "munich"}
    )

    assert anonymized == {
        f"tag_{anon_interface.get_id_of_tag_group('location')}": anon_interface.get_id_of_tag(
            "munich"
        )
    }
