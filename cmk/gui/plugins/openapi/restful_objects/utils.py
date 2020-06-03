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

        >>> p = ParamDict(schema={'pattern': '123'})
        >>> type(p['schema'])
        <class 'dict'>

        >>> p = ParamDict(name='foo', location='query', required=True)
        >>> p
        {'name': 'foo', 'required': True, 'in': 'query'}

        >>> p(required=False)
        {'name': 'foo', 'required': False, 'in': 'query'}

        >>> p.spec_tuple()
        ('foo', 'query', {'required': True})

    """
    def __init__(self, *seq, **kwargs):
        if 'location' in kwargs:
            kwargs['in'] = kwargs.pop('location')
        super(ParamDict, self).__init__(*seq, **kwargs)

    def __call__(self,
                 name: str = None,
                 location: Literal["query", "header", "path", "cookie"] = None,
                 description: str = None,
                 example: str = None,
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

    def to_dict(self):
        return dict(self)

    def spec_tuple(self):
        """Return a tuple suitable for passing into components.parameters()"""
        new = self()
        return new.pop('name'), new.pop('in'), dict(new)
