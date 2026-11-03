#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from flask import has_request_context

from cmk.gui.ctx_stack import global_var, set_global_var

type OnPermissionChecked = Callable[[str], None]


@contextmanager
def track_permissions(on_permission_checked: OnPermissionChecked) -> Iterator[None]:
    """Report the permissions checked by the current request to on_permission_checked"""
    old = _get_permission_tracker()
    try:
        _set_permission_tracker(on_permission_checked)
        yield
    finally:
        _set_permission_tracker(old)


@contextmanager
def disable_permission_tracking() -> Iterator[None]:
    old = _get_permission_tracker()
    try:
        _set_permission_tracker(None)
        yield
    finally:
        _set_permission_tracker(old)


def permission_checked(permission: str) -> None:
    """Is called by the hook "permission-checked" and reports to the current request"""
    if not has_request_context():
        return  # Permissions are also checked outside of requests, e.g. by background jobs
    if (on_permission_checked := _get_permission_tracker()) is not None:
        on_permission_checked(permission)


def _get_permission_tracker() -> OnPermissionChecked | None:
    return global_var("permission_tracker", default=None)


def _set_permission_tracker(on_permission_checked: OnPermissionChecked | None) -> None:
    set_global_var("permission_tracker", on_permission_checked)
