#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import contextlib
import os
from collections.abc import Generator
from unittest import mock

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection


@contextlib.contextmanager
def mocked_livestatus() -> Generator[MockLiveStatusConnection, None, None]:
    # NOTE: We only use this, so that the long connection timeout returns instantly. This allows
    # us to try out the GUI without having to wait for long. We don't expect any sensible data from
    # the mocker.
    live = MockLiveStatusConnection()
    live.set_sites(["dev", "local"])
    with mock.patch(
        "cmk.gui.sites._get_enabled_and_disabled_sites", new=live.enabled_and_disabled_sites
    ), mock.patch(
        "livestatus.MultiSiteConnection.expect_query", new=live.expect_query, create=True
    ), mock.patch(
        "livestatus.SingleSiteConnection._create_socket", new=live.create_socket
    ):
        yield live


def git_absolute(file_name: str) -> str:
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", file_name))
    return path


# Taken from https://stackoverflow.com/a/34333710
@contextlib.contextmanager
def modified_environ(*remove: str, **update: str) -> Generator[None, None, None]:
    """
    Temporarily updates the ``os.environ`` dictionary in-place.

    The ``os.environ`` dictionary is updated in-place so that the modification
    is sure to work in all situations.

    :param remove: Environment variables to remove.
    :param update: Dictionary of environment variables and values to add/update.
    """
    env = os.environ
    update = update or {}
    remove = remove or tuple()

    # List of environment variables being updated or removed.
    stomped = (set(update.keys()) | set(remove)) & set(env.keys())
    # Environment variables and values to restore on exit.
    update_after = {k: env[k] for k in stomped}
    # Environment variables and values to remove on exit.
    remove_after = frozenset(k for k in update if k not in env)

    try:
        env.update(update)
        for k in remove:
            env.pop(k, None)
        yield
    finally:
        env.update(update_after)
        for k in remove_after:
            env.pop(k)
