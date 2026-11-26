#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Groups that are assigned to a customer can be anonymized."""

import logging
from pathlib import Path

import pytest

from cmk.config_anonymizer.interface import AnonInterface
from cmk.config_anonymizer.plugins.groups import _anonymize_groups
from cmk.gui.groups import AllGroupSpecs


@pytest.fixture(name="anon_interface")
def fixture_anon_interface(monkeypatch: pytest.MonkeyPatch) -> AnonInterface:
    # The mapping is shared between all instances, keep the tests independent of each other
    monkeypatch.setattr(AnonInterface, "_anon_mapping", {})
    return AnonInterface(Path("anon1"), {}, logging.getLogger("test"))


def test_host_and_service_groups_keep_their_customer_assignment(
    anon_interface: AnonInterface,
) -> None:
    all_groups_spec: AllGroupSpecs = {
        "host": {
            "hg_acme": {"alias": "ACME hosts", "customer": "acme"},
            "hg_initech": {"alias": "Initech hosts", "customer": "initech"},
        },
        "service": {
            "sg_acme": {"alias": "ACME services", "customer": "acme"},
            "sg_initech": {"alias": "Initech services", "customer": "initech"},
        },
        "contact": {
            "cg_acme": {"alias": "ACME contacts", "customer": "acme"},
        },
    }

    assert _anonymize_groups(all_groups_spec, anon_interface) == {
        "host": {
            "host_group1": {"alias": "host_group_alias1", "customer": "customer1"},
            "host_group2": {"alias": "host_group_alias2", "customer": "customer2"},
        },
        "service": {
            "service_group1": {"alias": "service_group_alias1", "customer": "customer1"},
            "service_group2": {"alias": "service_group_alias2", "customer": "customer2"},
        },
        "contact": {
            "contact_group1": {"alias": "contact_group_alias1", "customer": "customer1"},
        },
    }


def test_global_host_and_service_groups_stay_global(anon_interface: AnonInterface) -> None:
    all_groups_spec: AllGroupSpecs = {
        "host": {"hg_global": {"alias": "Global hosts", "customer": None}},
        "service": {"sg_global": {"alias": "Global services", "customer": None}},
    }

    assert _anonymize_groups(all_groups_spec, anon_interface) == {
        "host": {"host_group1": {"alias": "host_group_alias1", "customer": None}},
        "service": {"service_group1": {"alias": "service_group_alias1", "customer": None}},
    }


def test_unknown_host_group_attribute_is_rejected(anon_interface: AnonInterface) -> None:
    all_groups_spec: AllGroupSpecs = {
        "host": {"hg": {"alias": "Hosts", "unexpected": "value"}},
    }

    with pytest.raises(ValueError, match="Unknown host group spec unexpected"):
        _anonymize_groups(all_groups_spec, anon_interface)
