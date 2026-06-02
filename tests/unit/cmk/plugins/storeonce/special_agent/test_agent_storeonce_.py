#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from collections.abc import Sequence
from unittest import mock

import pytest
import requests

from cmk.password_store.v1_unstable import Secret
from cmk.plugins.storeonce.special_agent import agent_storeonce


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


def _fake_get(url: str, **_kwargs: object) -> _FakeResponse:
    # Return the matching demo XML payload depending on the queried endpoint.
    if url.endswith("/servicesets/"):
        return _FakeResponse(agent_storeonce.servicesets_xml)
    if url.endswith("/stores/"):
        return _FakeResponse(agent_storeonce.stores_xml)
    return _FakeResponse(agent_storeonce.cluster_xml)


@pytest.mark.parametrize(
    ["extra_args", "expected_verify"],
    [
        pytest.param(["--no-cert-check"], False, id="--no-cert-check disables TLS verification"),
        pytest.param([], True, id="TLS verification enabled by default"),
    ],
)
def test_main_no_cert_check_controls_tls_verification(
    extra_args: Sequence[str],
    expected_verify: bool,
) -> None:
    """--no-cert-check must map to requests.get(verify=False) and vice versa (regression guard)."""
    argv = [
        "agent_storeonce",
        "--username",
        "user",
        "--password",
        "secret",
        "hostname",
        *extra_args,
    ]
    with (
        mock.patch.object(sys, "argv", argv),
        mock.patch.object(requests, "get", side_effect=_fake_get) as mock_get,
    ):
        assert agent_storeonce.main() == 0

    assert mock_get.call_count > 0
    assert {call.kwargs["verify"] for call in mock_get.call_args_list} == {expected_verify}


@pytest.mark.parametrize("opt_cert", [True, False])
def test_query_passes_opt_cert_to_requests_verify(opt_cert: bool) -> None:
    """query() must forward opt_cert verbatim as the requests verify flag."""
    with mock.patch.object(requests, "get", side_effect=_fake_get) as mock_get:
        agent_storeonce.query(
            "https://host/storeonceservices/cluster/",
            "user",
            Secret("secret"),
            opt_cert=opt_cert,
        )

    assert mock_get.call_args.kwargs["verify"] is opt_cert
