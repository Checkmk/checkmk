#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Host tags have to be anonymized consistently with the anonymized tag configuration."""

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
