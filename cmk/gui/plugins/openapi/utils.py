#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from typing import Literal, Optional, Dict, Any

from marshmallow import Schema

import docstring_parser  # type: ignore[import]

from cmk.gui.http import Response


def problem(
    status: int = 400,
    title: str = "A problem occured.",
    detail: Optional[str] = None,
    type_: Optional[str] = None,
    ext: Optional[Dict[str, Any]] = None,
):
    problem_dict = {
        'title': title,
        'status': status,
    }
    if detail is not None:
        problem_dict['detail'] = detail
    if type_ is not None:
        problem_dict['type'] = type_

    if isinstance(ext, dict):
        problem_dict.update(ext)
    else:
        problem_dict['ext'] = ext

    response = Response()
    response.status_code = status
    response.set_content_type("application/problem+json")
    response.set_data(json.dumps(problem_dict))
    return response


class BaseSchema(Schema):
    """The Base Schema for all request and response schemas."""
    class Meta:
        """Holds configuration for marshmallow"""
        ordered = True  # we want to have documentation in definition-order


def param_description(
    string: Optional[str],
    param_name: str,
    errors: Literal['raise', 'ignore'] = 'ignore',
) -> Optional[str]:
    """Get a param description of a docstring.

    Args:
        string:
            The docstring from which to extract the parameter description.

        param_name:
            The name of the parameter.

        errors:
            Either 'raise' or 'ignore'.

    Examples:

        If a docstring is given, there are a few possibilities.

            >>> param_description(param_description.__doc__, 'string')
            'The docstring from which to extract the parameter description.'

            >>> param_description(param_description.__doc__, 'foo')

            >>> param_description(param_description.__doc__, 'foo', errors='raise')
            Traceback (most recent call last):
            ...
            ValueError: Parameter 'foo' not found in docstring.

        There are cases, when no docstring is assigned to a function.

            >>> param_description(None, 'foo')

            >>> param_description(None, 'foo', errors='raise')
            Traceback (most recent call last):
            ...
            ValueError: No docstring was given.

    Returns:
        The description of the parameter, if possible.

    """
    if string is None:
        if errors == 'raise':
            raise ValueError("No docstring was given.")
        return None

    docstring = docstring_parser.parse(string)
    for param in docstring.params:
        if param.arg_name == param_name:
            return param.description
    if errors == 'raise':
        raise ValueError(f"Parameter {param_name!r} not found in docstring.")
    return None
