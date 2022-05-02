#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
import json
from contextlib import contextmanager
from typing import Iterator


# TODO: Cleanup this dirty hack. Creating a custom subclass of the JSONEncoder and implement the
# needed features there would be more straight forward. But that would need all call sites to use
# that encoder instead of the default methods.
@contextmanager
def patch_json(json_module) -> Iterator[None]:
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

    # And here we go for another dirty JSON hack. We often use he JSON we produce for adding it to HTML
    # tags and the JSON produced by json.dumps() can not directly be added to <script> tags in a save way.
    # TODO: This is something which should be realized by using a custom JSONEncoder. The slash encoding
    # is not necessary when the resulting string is not added to HTML content, but there is no problem
    # to apply it to all encoded strings.
    # We make this a function which is called on import-time because mypy fell into an endless-loop
    # due to changes outside this scope.
    orig_func = json_module.encoder.encode_basestring_ascii

    @functools.wraps(orig_func)
    def _escaping_wrapper(s):
        return orig_func(s).replace("/", "\\/")

    json_module.encoder.encode_basestring_ascii = _escaping_wrapper

    try:
        yield
    finally:
        json_module.encoder.encode_basestring_ascii = orig_func
        json_module.JSONEncoder.default = _default.default  # type: ignore[attr-defined]
