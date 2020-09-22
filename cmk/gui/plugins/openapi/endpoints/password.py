#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Passwords"""

import json

from connexion import problem  # type: ignore[import]

from cmk.gui.http import Response
from cmk.gui.watolib.passwords import (
    save_password,
    load_password_to_modify,
    load_passwords_to_modify,
    load_passwords,
)

from cmk.gui.plugins.openapi.restful_objects import (
    endpoint_schema,
    request_schemas,
    response_schemas,
    constructors,
)


@endpoint_schema(constructors.collection_href('password'),
                 'cmk/create',
                 method='post',
                 request_schema=request_schemas.InputPassword,
                 output_empty=True)
def create_password(params):
    """Create a password"""
    body = params['body']
    ident = body['ident']
    body["owned_by"] = None if body['owned_by'] == "admin" else body['owned_by']
    save_password(ident, body)
    return Response(status=204)


@endpoint_schema(constructors.object_href('password', '{name}'),
                 '.../update',
                 method='put',
                 parameters=['name'],
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


@endpoint_schema(constructors.object_href('password', '{name}'),
                 '.../delete',
                 method='delete',
                 parameters=['name'],
                 request_body_required=False,
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


@endpoint_schema(constructors.object_href('password', '{name}'),
                 'cmk/show',
                 method='get',
                 parameters=['name'],
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
    return _serve_password(password_details)


def _serve_password(password_details):
    response = Response()
    response.set_data(json.dumps(serialize_password(password_details)))
    response.set_content_type('application/json')
    return response


def serialize_password(details):
    return constructors.domain_object(domain_type="password",
                                      identifier=details["ident"],
                                      title=details["title"],
                                      members={
                                          "title": constructors.object_property(
                                              name='title',
                                              value=details["title"],
                                              prop_format='string',
                                              base=constructors.object_href(
                                                  'password', details["ident"]),
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
