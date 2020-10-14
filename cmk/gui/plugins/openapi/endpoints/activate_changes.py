#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Activate changes"""
from cmk.gui import watolib
from cmk.gui.globals import request
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    endpoint_schema,
    response_schemas,
    ParamDict,
)

ACTIVATION_ID = ParamDict.create(
    'activation_id',
    'path',
    description='The activation-id.',
    required=True,
    schema_type='string',
    example='d3b07384d113e0ec49eaa6238ad5ff00',
)


@endpoint_schema(constructors.domain_type_action_href('activation_run', 'activate-changes'),
                 'cmk/activate',
                 method='post',
                 response_schema=response_schemas.DomainObject)
def activate_changes(params):
    """Activate pending changes"""
    body = params.get('body', {})
    sites = body.get('sites', [])
    activation_id = watolib.activate_changes_start(sites)
    return _serve_activation_run(activation_id, is_running=True)


def _serve_activation_run(activation_id, is_running=False):
    """Serialize the activation response."""
    links = []
    action = "has completed"
    if is_running:
        action = "was started"
        links.append(
            constructors.link_endpoint('cmk.gui.plugins.openapi.endpoints.activate_changes',
                                       'cmk/wait-for-completion',
                                       parameters={'activation_id': activation_id}))
    return constructors.domain_object(
        domain_type='activation_run',
        identifier=activation_id,
        title=f'Activation {activation_id} {action}.',
        deletable=False,
        editable=False,
        links=links,
    )


@endpoint_schema(constructors.object_action_href('activation_run', '{activation_id}',
                                                 'wait-for-completion'),
                 'cmk/wait-for-completion',
                 method='get',
                 parameters=[ACTIVATION_ID],
                 will_do_redirects=True,
                 output_empty=True)
def activate_changes_state(params):
    """Wait for an activation-run to complete

    This endpoint will periodically redirect on itself to prevent timeouts.
    """
    activation_id = params['activation_id']
    manager = watolib.ActivateChangesManager()
    manager.load()
    manager.load_activation(activation_id)
    done = manager.wait_for_completion(timeout=request.request_timeout - 10)
    if not done:
        response = Response(status=301)
        response.location = request.url
        return response

    return Response(status=204)


@endpoint_schema(constructors.object_href('activation_run', '{activation_id}'),
                 'cmk/show',
                 method='get',
                 parameters=[ACTIVATION_ID],
                 response_schema=response_schemas.DomainObject)
def show_activation(params):
    """Show the status of a particular activation-run
    """
    activation_id = params['activation_id']
    manager = watolib.ActivateChangesManager()
    manager.load()
    manager.load_activation(activation_id)
    return _serve_activation_run(activation_id, is_running=manager.is_running())


@endpoint_schema(constructors.collection_href('activation_run', 'running'),
                 'cmk/run',
                 method='get',
                 response_schema=response_schemas.DomainObjectCollection)
def list_activations(params):
    """List currently running activations"""
    manager = watolib.ActivateChangesManager()
    activations = []
    for activation_id, change in manager.activations():
        activations.append(
            constructors.collection_item(
                domain_type='activation_run',
                obj={
                    'id': activation_id,
                    'title': change['_comment'],
                },
            ))

    return constructors.collection_object(domain_type='activation_run', value=activations)
