#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, MutableMapping
from contextlib import contextmanager
from dataclasses import dataclass, field

from cmk.agent_based.v1.value_store import set_value_store_manager


@dataclass
class _ValueStoreManager:
    """Stand-in for the check engine, which owns the value store in production."""

    active_service_interface: MutableMapping[str, object] = field(default_factory=dict)

    def save(self) -> None:
        pass


@contextmanager
def value_store(initial: MutableMapping[str, object] | None = None) -> Iterator[None]:
    """Enter a service's value store, so a check function can be called as it is in production.

    Pass `initial` to pretend the check has run before, which the rate and trend
    computations need in order to produce anything.
    """
    with set_value_store_manager(_ValueStoreManager(dict(initial or {})), store_changes=False):
        yield
