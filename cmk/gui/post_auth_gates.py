#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Pluggable gates that lock the interactive GUI onto a dedicated page.

A :class:`PostAuthGate` lets a feature take over the GUI the same way the
forced password change does: while the gate's condition holds, every request
is redirected to the gate's page, except for the small set of pages the gate
itself needs (:attr:`PostAuthGate.allowed_page_names`).

The registry is consulted by ``ensure_authentication()`` only for interactive,
fully logged-in (``"logged_in"`` session state), non-automation GUI sessions.
The REST API, ``noauth:`` pages, site-internal logins and automation users
never pass through it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import override

from cmk.ccc.plugin_registry import Registry
from cmk.gui.config import Config


@dataclass(frozen=True)
class PostAuthGate:
    """A condition that, while it holds, locks the GUI onto one page.

    Attributes:
        ident: Unique name of the gate.
        allowed_page_names: Pages that stay reachable while the gate is
            active. Must contain the gate's own page and its ajax endpoints;
            include ``"logout"`` so users can always sign out.
        redirect_url: Returns the URL to redirect to while the gate is
            active, or ``None`` while it is not.
    """

    ident: str
    allowed_page_names: frozenset[str]
    redirect_url: Callable[[Config], str | None]


class PostAuthGateRegistry(Registry[PostAuthGate]):
    @override
    def plugin_name(self, instance: PostAuthGate) -> str:
        return instance.ident


post_auth_gate_registry = PostAuthGateRegistry()


def post_auth_gate_redirect_url(config: Config, requested_file: str) -> str | None:
    """URL of the first active gate that does not allow the requested page."""
    for gate in post_auth_gate_registry.values():
        if requested_file in gate.allowed_page_names:
            continue
        if (url := gate.redirect_url(config)) is not None:
            return url
    return None
