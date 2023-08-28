#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
import typing
import warnings

from cmk.utils.plugin_loader import load_plugins_with_exceptions

P = typing.ParamSpec("P")
R = typing.TypeVar("R")

DecoratedFunction = typing.Callable[P, R]


def import_plugins(
    dotted_paths: list[str],
) -> typing.Callable[[DecoratedFunction], DecoratedFunction]:
    """Temporary decorator to load specified modules for test environment setup.

    This decorator exists solely to work around an issue where certain plugins are not being
    loaded properly before setting up the test environment.
    """
    warnings.warn(
        "This decorator is used, because the test would otherwise fail. "
        "The test should(!) run fine in isolation though, without this decorator! "
        "Once this has been achieved, remove this decorator.",
        DeprecationWarning,
    )

    def wrap_import(func: DecoratedFunction) -> DecoratedFunction:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for path in dotted_paths:
                list(load_plugins_with_exceptions(path))
            return func(*args, **kwargs)

        return wrapper

    return wrap_import
