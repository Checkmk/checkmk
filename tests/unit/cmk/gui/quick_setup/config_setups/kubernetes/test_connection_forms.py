#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.form_specs import (
    DEFAULT_VALUE,
    get_visitor,
    RawDiskData,
    RawFrontendData,
    VisitorOptions,
)
from cmk.gui.quick_setup.config_setups.kubernetes.connection_forms import (
    connection_configuration,
    host_configuration,
    pull_url_configuration,
)
from cmk.shared_typing.vue_formspec_components import CascadingSingleChoice

pytestmark = pytest.mark.usefixtures("request_context")
OPTIONS = VisitorOptions(migrate_values=True, mask_values=False)


def test_unsupported_push_offers_only_pull() -> None:
    visitor = get_visitor(
        connection_configuration(
            receiver_host="monitor", shared_secret="secret", push_supported=False
        ),
        OPTIONS,
    )

    schema, _values = visitor.to_vue(DEFAULT_VALUE)

    assert isinstance(schema, CascadingSingleChoice)
    assert [element.name for element in schema.elements] == ["pull"]
    assert visitor.to_disk(DEFAULT_VALUE) == (
        "pull",
        {"shared_secret": "secret", "service_exposure": ("node_port", 30050)},
    )
    assert visitor.validate(RawDiskData(("push", {"receiver_host": "monitor"})))


def test_supported_push_offers_both_modes() -> None:
    visitor = get_visitor(
        connection_configuration(
            receiver_host="monitor", shared_secret="secret", push_supported=True
        ),
        OPTIONS,
    )

    schema, _values = visitor.to_vue(DEFAULT_VALUE)

    assert isinstance(schema, CascadingSingleChoice)
    assert [element.name for element in schema.elements] == ["push", "pull"]
    assert visitor.to_disk(DEFAULT_VALUE) == ("push", {"receiver_host": "monitor"})


def test_push_defaults_do_not_include_pull_credentials() -> None:
    visitor = get_visitor(
        connection_configuration(receiver_host="monitor", shared_secret="secret"), OPTIONS
    )

    assert visitor.to_disk(DEFAULT_VALUE) == ("push", {"receiver_host": "monitor"})


def test_pull_secret_survives_form_reconstruction() -> None:
    old = get_visitor(
        connection_configuration(receiver_host="monitor", shared_secret="original"), OPTIONS
    )
    schema, _value = old.to_vue(DEFAULT_VALUE)
    assert isinstance(schema, CascadingSingleChoice)
    pull_default = next(
        element.default_value for element in schema.elements if element.name == "pull"
    )
    rebuilt = get_visitor(
        connection_configuration(receiver_host="monitor", shared_secret="new"), OPTIONS
    )

    value = rebuilt.to_disk(RawFrontendData(["pull", pull_default]))

    assert value == (
        "pull",
        {"shared_secret": "original", "service_exposure": ("node_port", 30050)},
    )


@pytest.mark.parametrize(
    "port", [pytest.param(29999, id="too-low"), pytest.param(32768, id="too-high")]
)
def test_nodeport_outside_default_kubernetes_range_is_rejected(port: int) -> None:
    visitor = get_visitor(
        connection_configuration(receiver_host="monitor", shared_secret="secret"), OPTIONS
    )

    assert visitor.validate(
        RawDiskData(("pull", {"shared_secret": "secret", "service_exposure": ("node_port", port)}))
    )


@pytest.mark.parametrize(
    "url",
    [
        pytest.param("", id="missing"),
        pytest.param("ftp://host", id="wrong-protocol"),
        pytest.param("https://agent:70000", id="invalid-port"),
        pytest.param("https://agent:0", id="zero-port"),
        pytest.param("https://agent:abc", id="non-numeric-port"),
        pytest.param("https://user:password@agent", id="credentials"),
        pytest.param("https://agent?token=secret", id="query"),
        pytest.param("https://agent#sections", id="fragment"),
        pytest.param("https://agent/pull/sections/", id="sections-not-base-url"),
        pytest.param("https://agent/proxy/pull/sections", id="prefixed-sections"),
        pytest.param("https://agent\n", id="whitespace"),
    ],
)
def test_unusable_pull_base_urls_are_rejected(url: str) -> None:
    visitor = get_visitor(pull_url_configuration(), OPTIONS)

    assert visitor.validate(RawDiskData({"base_url": url}))


@pytest.mark.parametrize(
    "url", ["http://agent:30050", "https://agent/proxy/", "https://[2001:db8::1]:30050"]
)
def test_pull_base_url_accepts_nodeport_proxy_path_and_ipv6(url: str) -> None:
    visitor = get_visitor(pull_url_configuration(), OPTIONS)

    assert not visitor.validate(RawDiskData({"base_url": url}))


@pytest.mark.usefixtures("with_admin_login")
@pytest.mark.parametrize("name", ["-legacy", ".legacy", "legacy\n"])
def test_invalid_explicit_host_names_are_rejected(name: str) -> None:
    visitor = get_visitor(host_configuration(), OPTIONS)

    assert visitor.validate(RawDiskData({"host_name_source": ("explicit", name), "host_path": ""}))


@pytest.mark.usefixtures("with_admin_login")
@pytest.mark.parametrize(
    "choice",
    [
        pytest.param(("cluster_name", None), id="derived"),
        pytest.param(("explicit", "legacy-host"), id="override"),
        pytest.param(("explicit", "_legacy.host-1"), id="checkmk-name-not-dns-name"),
    ],
)
def test_host_name_choice_is_preserved(choice: object) -> None:
    visitor = get_visitor(host_configuration(), OPTIONS)
    data = RawDiskData({"host_name_source": choice, "host_path": ""})

    assert not visitor.validate(data)
    assert visitor.to_disk(data) == data.value
