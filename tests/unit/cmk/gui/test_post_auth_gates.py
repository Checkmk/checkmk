#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.config import Config
from cmk.gui.post_auth_gates import (
    post_auth_gate_redirect_url,
    post_auth_gate_registry,
    PostAuthGate,
    PostAuthGateRegistry,
)


@pytest.fixture(name="registry")
def fixture_registry(monkeypatch: pytest.MonkeyPatch) -> PostAuthGateRegistry:
    registry = PostAuthGateRegistry()
    monkeypatch.setattr(
        "cmk.gui.post_auth_gates.post_auth_gate_registry",
        registry,
    )
    return registry


def _gate(
    ident: str = "my_gate",
    allowed_page_names: frozenset[str] = frozenset({"my_gate_page", "logout"}),
    url: str | None = "my_gate_page.py",
) -> PostAuthGate:
    return PostAuthGate(
        ident=ident,
        allowed_page_names=allowed_page_names,
        redirect_url=lambda config: url,
    )


def test_no_registered_gate_yields_no_redirect(registry: PostAuthGateRegistry) -> None:
    assert post_auth_gate_redirect_url(Config(), "index") is None


def test_inactive_gate_yields_no_redirect(registry: PostAuthGateRegistry) -> None:
    registry.register(_gate(url=None))
    assert post_auth_gate_redirect_url(Config(), "index") is None


def test_active_gate_redirects(registry: PostAuthGateRegistry) -> None:
    registry.register(_gate())
    assert post_auth_gate_redirect_url(Config(), "index") == "my_gate_page.py"


def test_allowed_page_is_not_redirected(registry: PostAuthGateRegistry) -> None:
    registry.register(_gate())
    assert post_auth_gate_redirect_url(Config(), "my_gate_page") is None
    assert post_auth_gate_redirect_url(Config(), "logout") is None


def test_first_active_gate_wins(registry: PostAuthGateRegistry) -> None:
    registry.register(_gate(ident="inactive", url=None))
    registry.register(_gate(ident="first", url="first.py"))
    registry.register(_gate(ident="second", url="second.py"))
    assert post_auth_gate_redirect_url(Config(), "index") == "first.py"


def test_default_registry_is_empty() -> None:
    assert not post_auth_gate_registry.keys()
