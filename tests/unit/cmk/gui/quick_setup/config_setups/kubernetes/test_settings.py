#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.site import SiteId
from cmk.gui.quick_setup.config_setups.kubernetes.settings import (
    ADVANCED,
    CLUSTER,
    CONNECTION,
    HOST,
    PULL_URL,
    PullSettings,
    PushSettings,
    read_common_settings,
    read_settings,
)
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData


def test_deployment_settings_require_an_explicit_connection_mode(data: ParsedFormData) -> None:
    with pytest.raises(ValueError, match="Choose a connection mode"):
        read_settings(data, default_site=SiteId("site"))


def test_monitoring_settings_preserve_filters_and_derive_host_name(data: ParsedFormData) -> None:
    settings = read_common_settings(data, default_site=SiteId("site"))

    assert settings.monitoring.host_name == "production"
    assert settings.monitoring.namespaces == ("exclude", ("^test",))
    assert settings.monitoring.annotations == ("pattern", "^example")
    assert settings.monitoring.excluded_node_roles == ()
    assert settings.release_name == "kubernetes-config-1"


def test_unchecked_filters_monitor_all_namespaces_without_annotations(
    data: ParsedFormData,
) -> None:
    settings = read_common_settings(
        {
            **data,
            CLUSTER: {**data[CLUSTER], "namespaces": None},
            ADVANCED: {**data[ADVANCED], "annotations": None},
        },
        default_site=SiteId("site"),
    )

    assert settings.monitoring.namespaces == ("include", ())
    assert settings.monitoring.annotations == "none"


def test_explicit_host_name_overrides_cluster_name(data: ParsedFormData) -> None:
    settings = read_common_settings(
        {**data, HOST: {"host_name_source": ("explicit", "legacy"), "host_path": ""}},
        default_site=SiteId("site"),
    )

    assert settings.monitoring.host_name == "legacy"


def test_push_ignores_leftover_pull_url_and_secret(data: ParsedFormData) -> None:
    settings = read_settings(
        {
            **data,
            CONNECTION: ("push", {"receiver_host": "monitor", "shared_secret": "unused"}),
            PULL_URL: {"base_url": "https://old"},
        },
        default_site=SiteId("site"),
    )

    assert settings == PushSettings(
        common=read_common_settings(data, default_site=SiteId("site")),
        receiver_host="monitor",
    )


def test_pull_keeps_deployment_secret_and_final_url(data: ParsedFormData) -> None:
    settings = read_settings(
        {
            **data,
            CONNECTION: (
                "pull",
                {"shared_secret": "existing", "service_exposure": ("node_port", 31050)},
            ),
            PULL_URL: {"base_url": "https://agent"},
        },
        default_site=SiteId("site"),
    )

    assert isinstance(settings, PullSettings)
    assert settings.shared_secret == "existing"
    assert settings.base_url == "https://agent"
    assert settings.node_port == 31050
    assert "existing" not in repr(settings)


def test_pull_deployment_settings_do_not_require_the_final_url(data: ParsedFormData) -> None:
    settings = read_settings(
        {**data, CONNECTION: ("pull", {"shared_secret": "deployed-secret"})},
        default_site=SiteId("site"),
    )

    assert isinstance(settings, PullSettings)
    assert settings.base_url == ""


def test_unknown_connection_mode_is_rejected(data: ParsedFormData) -> None:
    with pytest.raises(ValueError, match="Invalid connection mode"):
        read_settings({**data, CONNECTION: ("unknown", {})}, default_site=SiteId("site"))
