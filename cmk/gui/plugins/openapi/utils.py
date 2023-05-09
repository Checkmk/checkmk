#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from typing import Literal, Optional, Dict, Any, cast
from urllib.parse import quote_plus

import docstring_parser  # type: ignore[import]
from werkzeug.exceptions import HTTPException

from cmk.gui.http import Response
from cmk.utils.livestatus_helpers.queries import Query
from livestatus import SiteId


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
        if ext:
            problem_dict['ext'] = ext

    response = Response()
    response.status_code = status
    response.set_content_type("application/problem+json")
    response.set_data(json.dumps(problem_dict))
    return response


class ProblemException(HTTPException):
    def __init__(
        self,
        status: int = 400,
        title: str = "A problem occured.",
        detail: Optional[str] = None,
        type_: Optional[str] = None,
        ext: Optional[Dict[str, Any]] = None,
    ):
        """
        This exception is holds arguments that are going to be passed to the
        `problem` function to generate a proper response.
        """
        super().__init__(description=title)
        # These two are named as such for HTTPException compatibility.
        self.code: int = status
        self.description: str = title

        self.detail = detail
        self.type = type_
        self.ext = ext

    def __call__(self, environ, start_response):
        return self.to_problem()(environ, start_response)

    def to_problem(self):
        return problem(
            status=self.code,
            title=self.description,  # same as title
            detail=self.detail,
            type_=self.type,
            ext=self.ext,
        )


def param_description(
    string: Optional[str],
    param_name: str,
    errors: Literal['raise', 'ignore'] = 'raise',
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

            >>> from cmk.gui import watolib
            >>> param_description(watolib.activate_changes_start.__doc__, 'force_foreign_changes')
            'Will activate changes even if the user who made those changes is not the currently logged in user.'

            >>> param_description(param_description.__doc__, 'string')
            'The docstring from which to extract the parameter description.'

            >>> param_description(param_description.__doc__, 'foo', errors='ignore')

            >>> param_description(param_description.__doc__, 'foo', errors='raise')
            Traceback (most recent call last):
            ...
            ValueError: Parameter 'foo' not found in docstring.

        There are cases, when no docstring is assigned to a function.

            >>> param_description(None, 'foo', errors='ignore')

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
            return param.description.replace("\n", " ")
    if errors == 'raise':
        raise ValueError(f"Parameter {param_name!r} not found in docstring.")
    return None


def create_url(site: SiteId, query: Query) -> str:
    """Create a REST-API query URL.

    Examples:

        >>> create_url('heute',
        ...            Query.from_string("GET hosts\\nColumns: name\\nFilter: name = heute"))
        '/heute/check_mk/api/1.0/domain-types/host/collections/all?query=%7B%22op%22%3A+%22%3D%22%2C+%22left%22%3A+%22hosts.name%22%2C+%22right%22%3A+%22heute%22%7D'

    Args:
        site:
            A valid site-name.

        query:
            The Query() instance which the endpoint shall create again.

    Returns:
        The URL.

    Raises:
        A ValueError when no URL could be created.

    """
    table = cast(str, query.table.__tablename__)
    try:
        domain_type = {
            'hosts': 'host',
            'services': 'service',
        }[table]
    except KeyError:
        raise ValueError(f"Could not find a domain-type for table {table}.")
    url = f"/{site}/check_mk/api/1.0/domain-types/{domain_type}/collections/all"
    query_dict = query.dict_repr()
    if query_dict:
        query_string_value = quote_plus(json.dumps(query_dict))
        url += f"?query={query_string_value}"

    return url
