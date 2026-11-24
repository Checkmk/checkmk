#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""An anonymized dump defines the customers the rest of it refers to."""

import logging
from pathlib import Path

import pytest

from cmk.config_anonymizer.interface import AnonInterface
from cmk.config_anonymizer.plugins.customers import anonymize_customers


def _anon_interface() -> AnonInterface:
    return AnonInterface(Path("test"), {}, logging.getLogger("test"))


@pytest.mark.usefixtures("patch_omd_site")
def test_customers_are_defined_under_the_ids_the_rest_of_the_dump_refers_to() -> None:
    anon_interface = _anon_interface()

    anonymized = anonymize_customers({"acme": {"name": "ACME Inc."}}, anon_interface)

    assert anon_interface.get_customer("acme") in anonymized


@pytest.mark.usefixtures("patch_omd_site")
def test_the_provider_stays_the_provider() -> None:
    anonymized = anonymize_customers(
        {"provider": {"name": "Hosting Corp."}, "acme": {"name": "ACME Inc."}},
        _anon_interface(),
    )

    assert anonymized["provider"] == {"name": "provider"}


@pytest.mark.usefixtures("patch_omd_site")
def test_explicit_references_to_the_provider_stay_the_provider() -> None:
    assert _anon_interface().get_customer("provider") == "provider"


@pytest.mark.usefixtures("patch_omd_site")
def test_nothing_but_an_anonymized_name_is_kept_of_a_customer() -> None:
    anon_interface = _anon_interface()

    anonymized = anonymize_customers(
        {
            "acme": {
                "name": "ACME Inc.",
                "macros": [("CUSTOMER_CONTACT", "jane@acme.example")],
                "customer_report_layout": "acme_layout",
            }
        },
        anon_interface,
    )

    anon_id = anon_interface.get_customer("acme")
    assert anonymized[anon_id] == {"name": anon_id}
    assert "acme" not in str(anonymized).lower()
