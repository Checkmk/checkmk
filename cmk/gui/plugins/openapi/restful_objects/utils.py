#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Dict, Literal


def _denilled(dict_):
    """Remove all None values from a dict.

    Examples:

        >>> _denilled({'a': None, 'foo': 'bar', 'b': None})
        {'foo': 'bar'}

    Args:
        dict_:

    Returns:
        A dict without values being None.
    """
    return {key: value for key, value in dict_.items() if value is not None}


class ParamDict(dict):
    """Represents a parameter but can be changed by calling it.

    This is basically a dict, but one can return a new dict with updated parameters easily
    without having to change the original.

    Examples:

        >>> p = ParamDict(field="foo", required=True)
        >>> p
        {'field': 'foo', 'required': True}

        >>> p(required=False)
        {'field': 'foo', 'required': False}

    """
    def __call__(self,
                 name=None,
                 location: Literal["query", "header", "path", "cookie"] = None,
                 description=None,
                 example=None,
                 schema: Dict[str, str] = None,
                 required: bool = None,
                 **kw):
        new_dict = ParamDict(**self)
        new_dict.update(
            _denilled({
                'name': name,
                'in': location,
                'description': description,
                'example': example,
                'schema': schema,
                'required': required,
            }))
        new_dict.update(kw)
        return new_dict

    def __str__(self):
        """Return just the name of the parameter.

        This is useful for parameter re-use."""
        return self['name']

    def spec_tuple(self):
        """Return a tuple suitable for passing into components.parameters()"""
        new = self()
        return new.pop('name'), new.pop('location'), new
