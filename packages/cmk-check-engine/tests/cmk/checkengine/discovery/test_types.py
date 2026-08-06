#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.checkengine.discovery.types import DiscoverySettings


def test_from_vs_none() -> None:
    assert DiscoverySettings.from_vs(None) == DiscoverySettings(
        update_host_labels=False,
        add_new_services=False,
        remove_vanished_services=False,
        update_changed_service_labels=False,
        update_changed_service_parameters=False,
    )


def test_from_vs_full_custom() -> None:
    assert DiscoverySettings.from_vs(
        (
            "custom",
            {
                "add_new_services": True,
                "remove_vanished_services": True,
                "update_changed_service_labels": True,
                "update_changed_service_parameters": True,
                "update_host_labels": True,
            },
        )
    ) == DiscoverySettings(
        update_host_labels=True,
        add_new_services=True,
        remove_vanished_services=True,
        update_changed_service_labels=True,
        update_changed_service_parameters=True,
    )


def test_from_vs_legacy_custom_without_update_changed_service_parameters() -> None:
    # Crash report 3d61c6aa-0b06-11f1-b999-005056ad1ba9 (group 4580): a periodic service
    # discovery rule stored before the 'update_changed_service_parameters' flag existed
    # reaches the check engine as a 'custom' mode dict missing that key. from_vs must
    # tolerate it (defaulting the missing flag to False) instead of raising KeyError.
    legacy_mode = (
        "custom",
        {
            "add_new_services": True,
            "remove_vanished_services": False,
            "update_changed_service_labels": False,
            "update_host_labels": True,
        },
    )
    assert DiscoverySettings.from_vs(legacy_mode) == DiscoverySettings(  # type: ignore[arg-type]
        update_host_labels=True,
        add_new_services=True,
        remove_vanished_services=False,
        update_changed_service_labels=False,
        update_changed_service_parameters=False,
    )
