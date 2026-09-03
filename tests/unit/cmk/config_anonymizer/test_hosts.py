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
    _anonymize_single_host_and_folder_attributes,
)


def _anon_interface() -> AnonInterface:
    return AnonInterface(Path("test"), {}, logging.getLogger("test"))


@pytest.mark.usefixtures("patch_omd_site")
def test_a_relation_hides_the_host_it_names() -> None:
    anon_interface = _anon_interface()

    anonymized = _anonymize_single_host_and_folder_attributes(
        anon_interface,
        [],
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
        _anon_interface(), [], {"relations": "os1"}
    )

    assert anonymized["relations"] == []
