#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from contextlib import contextmanager

from cmk.gui.ctx_stack import global_var, set_global_var


@contextmanager
def disable_permission_tracking() -> Iterator[None]:
    old = _get_permission_tracking()
    try:
        _set_permission_tracking(False)
        yield
    finally:
        _set_permission_tracking(old)


@contextmanager
def enable_permission_tracking() -> Iterator[None]:
    old = _get_permission_tracking()
    try:
        _set_permission_tracking(True)
        yield
    finally:
        _set_permission_tracking(old)


def is_permission_tracking_enabled() -> bool:
    return _get_permission_tracking()


def _get_permission_tracking() -> bool:
    return global_var("permission_tracking", default=False)


def _set_permission_tracking(enable: bool) -> None:
    set_global_var("permission_tracking", enable)
