#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Passwords

Passwords intended for authentification of certain checks can be stored in the Checkmk
password store. You can use in a rule a password stored in the password store without knowing or
entering the password.
"""

import json

from cmk.gui.http import Response
from cmk.gui.plugins.openapi.utils import problem
from cmk.gui.plugins.openapi.restful_objects.parameters import NAME_FIELD
from cmk.gui.watolib.passwords import (
    save_password,
    load_password_to_modify,
    load_passwords_to_modify,
    load_passwords,
)

from cmk.gui.plugins.openapi.restful_objects import (
    Endpoint,
    request_schemas,
    response_schemas,
    constructors,
)


@Endpoint(constructors.collection_href('password'),
          'cmk/create',
          method='post',
          request_schema=request_schemas.InputPassword,
          output_empty=True)
def create_password(params):
    """Create a password"""
    body = params['body']
    ident = body['ident']
    password_details = {k: v for k, v in body.items() if k not in ("ident", "owned_by")}
    password_details["owned_by"] = None if body['owned_by'] == "admin" else body['owned_by']
    save_password(ident, password_details)
    return Response(status=204)


@Endpoint(constructors.object_href('password', '{name}'),
          '.../update',
          method='put',
          path_params=[NAME_FIELD],
          request_schema=request_schemas.UpdatePassword,
          output_empty=True)
def update_password(params):
    """Update a password"""
    body = params['body']
    ident = params['name']
    password_details = load_password_to_modify(ident)
    password_details.update(body)
    save_password(ident, password_details)
    return Response(status=204)


@Endpoint(constructors.object_href('password', '{name}'),
          '.../delete',
          method='delete',
          path_params=[NAME_FIELD],
          output_empty=True)
def delete_password(params):
    """Delete a password"""
    ident = params['name']
    entries = load_passwords_to_modify()
    if ident not in entries:
        return problem(
            404, f'Password "{ident}" is not known.',
            'The password you asked for is not known. Please check for eventual misspellings.')
    _ = entries.pop(ident)
    return Response(status=204)


@Endpoint(constructors.object_href('password', '{name}'),
          'cmk/show',
          method='get',
          path_params=[NAME_FIELD],
          response_schema=response_schemas.ConcretePassword)
def show_password(params):
    """Show a password"""
    ident = params['name']
    passwords = load_passwords()
    if ident not in passwords:
        return problem(
            404, f'Password "{ident}" is not known.',
            'The password you asked for is not known. Please check for eventual misspellings.')
    password_details = passwords[ident]
    return _serve_password(ident, password_details)


def _serve_password(ident, password_details):
    response = Response()
    response.set_data(json.dumps(serialize_password(ident, password_details)))
    response.set_content_type('application/json')
    return response


def serialize_password(ident, details):
    return constructors.domain_object(domain_type="password",
                                      identifier=ident,
                                      title=details["title"],
                                      members={
                                          "title": constructors.object_property(
                                              name='title',
                                              value=details["title"],
                                              prop_format='string',
                                              base=constructors.object_href('password', ident),
                                          )
                                      },
                                      extensions={
                                          key: details[key] for key in details if key in (
                                              "comment",
                                              "docu_url",
                                              "password",
                                              "owned_by",
                                              "shared_with",
                                          )
                                      })
