#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ruff: noqa: A005

import json
from collections.abc import Iterator
from contextlib import contextmanager
from types import ModuleType


# TODO: Cleanup this dirty hack. Creating a custom subclass of the JSONEncoder and implement the
# needed features there would be more straight forward. But that would need all call sites to use
# that encoder instead of the default methods.
@contextmanager
def patch_json(json_module: ModuleType) -> Iterator[None]:
    # Monkey patch in order to make the HTML class below json-serializable without changing the
    # default json calls.
    def _default(self: json.JSONEncoder, obj: object) -> str:
        # ignore attr-defined: See hack below
        func = getattr(obj.__class__, "to_json", _default.default)  # type: ignore[attr-defined]
        assert func is not None  # Hmmm...
        return func(obj)

    # TODO: suppress mypy warnings for this monkey patch right now. See also:
    # https://github.com/python/mypy/issues/2087
    # Save unmodified default:
    _default.default = json_module.JSONEncoder().default  # type: ignore[attr-defined]
    # replacement:
    json_module.JSONEncoder.default = _default

    try:
        yield
    finally:
        json_module.JSONEncoder.default = _default.default  # type: ignore[attr-defined]
