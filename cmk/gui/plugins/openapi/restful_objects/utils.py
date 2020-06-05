#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from typing import Optional

from cmk.gui.plugins.openapi.restful_objects.type_defs import LocationType
from cmk.gui.type_defs import SetOnceDict

# This is the central store for all our endpoints. We use this to determine the correct URLs at
# runtime so that we can't have typos when interlinking responses.
ENDPOINT_REGISTRY = SetOnceDict()

PARAM_RE = re.compile(r"\{([a-z][a-z0-9]*)\}")


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
        for d in seq:
            if 'location' in kwargs:
                d['in'] = d.pop('location')
        super(ParamDict, self).__init__(*seq, **kwargs)

    def __call__(self,
                 name: str = None,
                 description: str = None,
                 location: LocationType = None,
                 required: bool = None,
                 allow_empty: bool = None,
                 example: str = None,
                 schema_type: str = None,
                 schema_pattern: str = None,
                 **kw):
        # NOTE: The defaults are all None here, so that only the updated keys will overwrite the
        # previous values.
        new_dict = self.__class__(**self)
        new_dict.update(
            _denilled({
                'name': name,
                'in': location,
                'description': description,
                'example': example,
                'schema': _denilled({
                    'schema_type': schema_type,
                    'schema_pattern': schema_pattern,
                }) or None,
                'required': required,
            }))
        new_dict.update(kw)
        return new_dict

    def __str__(self):
        """Return just the name of the parameter.

        This is useful for parameter re-use."""
        return self['name']

    @classmethod
    def create(
        cls,
        param_name,  # type: str
        location,  # type: LocationType
        description=None,  # type: Optional[str]
        required=True,  # type: bool
        allow_emtpy=False,  # type: bool
        schema_type='string',  # type: str
        schema_pattern=None,  # type: str
        **kw,
    ):
        # type: (...) -> ParamDict
        """Specify an OpenAPI parameter to be used on a particular endpoint.

        Args:
            param_name:
                The name of the parameter.

            description:
                Optionally the description of the parameter. Markdown may be used.

            location:
                One of 'query', 'path', 'cookie', 'header'.

            required:
                If `location` is `path` this needs to be set and True. Otherwise it can even be absent.

            allow_emtpy:
                If None as a value is allowed.

            schema_type:
                May be 'string', 'bool', etc.

            schema_pattern:
                A regex which is used to filter invalid values.

        Examples:

            >>> p = ParamDict.create('foo', 'query', required=False)
            >>> expected = {
            ...     'name': 'foo',
            ...     'in': 'query',
            ...     'required': False,
            ...     'allowEmptyValue': False,
            ...     'schema': {'type': 'string'},
            ... }
            >>> assert p == expected, p


        Returns:
            The parameter dict.

        """
        if location == 'path' and not required:
            raise ValueError("path parameters' `required` field always needs to be True!")

        raw_values = {
            'name': param_name,
            'in': location,
            'required': required,
            'description': description,
            'allowEmptyValue': allow_emtpy,
            'schema': _denilled({
                'type': schema_type,
                'pattern': schema_pattern,
            }) or None,
        }
        # We throw away None valued keys so they won't show up in the specification.
        _param = cls(_denilled(raw_values))
        for key, value in kw.items():
            if key in raw_values:
                # This bypasses our translation from pythonic names to OpenAPI names. Don't want.
                raise ValueError("Please specify %s through the normal parameters." % key)
            _param[key] = value
        return _param

    def to_dict(self):
        return dict(self)

    def spec_tuple(self):
        """Return a tuple suitable for passing into components.parameters()"""
        new = self()
        return new.pop('name'), new.pop('in'), new.to_dict()

    def header_dict(self):
        new = self()
        location = new.pop('in')
        if location != 'header':
            raise ValueError("Only header parameters can be added to the header-struct.")
        return {new.pop('name'): new.to_dict()}


param = ParamDict.create


def fill_out_path_template(orig_path, parameters):
    """Fill out a simple template.

    Examples:

        >>> param_spec = {'var': {'example': 'foo'}}
        >>> fill_out_path_template('/path/{var}', param_spec)
        '/path/foo'

    Args:
        orig_path:
        parameters:

    Returns:

    """
    path = orig_path
    for path_param in PARAM_RE.findall(path):
        param_spec = parameters[path_param]
        try:
            path = path.replace("{" + path_param + "}", param_spec['example'])
        except KeyError:
            raise KeyError("Param %s of path %r has no example" % (path_param, orig_path))
    return path
