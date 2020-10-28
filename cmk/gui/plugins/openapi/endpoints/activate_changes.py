#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Activate changes

When changes are activated, Checkmk transfers the current configuration status to the ongoing
monitoring.

Checkmk differentiates between the configuration environment in which you manage the hosts,
services and settings, and the actual monitoring environment.

Changes in the configuration - adding a new host, for example - will initially have no effect
on the monitoring. Changes must first be activated, which will bring all changes that you have
accumulated since the last activation as a "bundle" into the operational monitoring.

You can find an introduction to the configuration of Checkmk including activation of changes in the
[Checkmk guide](https://checkmk.com/cms_wato.html).
"""

from cmk.gui import watolib
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import request
from cmk.gui.http import Response
from cmk.gui.plugins.openapi import fields
from cmk.gui.plugins.openapi.endpoints.utils import may_fail
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    Endpoint,
    response_schemas,
    request_schemas,
)
from cmk.gui.plugins.openapi.restful_objects.type_defs import LinkType

ACTIVATION_ID = {
    'activation_id': fields.String(
        description='The activation-id.',
        example='d3b07384d113e0ec49eaa6238ad5ff00',
        required=True,
    ),
}


@Endpoint(constructors.domain_type_action_href('activation_run', 'activate-changes'),
          'cmk/activate',
          method='post',
          status_descriptions={
              200: "The activation has already been completed.",
              302: ("The activation is still running. Redirecting to the "
                    "'Wait for completion' endpoint."),
          },
          will_do_redirects=True,
          request_schema=request_schemas.ActivateChanges,
          response_schema=response_schemas.DomainObject)
def activate_changes(params):
    """Activate pending changes"""
    body = params['body']
    sites = body['sites']
    with may_fail(MKUserError, status=400):
        activation_id = watolib.activate_changes_start(sites)
    if body['redirect']:
        wait_for = _completion_link(activation_id)
        response = Response(status=301)
        response.location = wait_for['href']
        return response

    return _serve_activation_run(activation_id, is_running=True)


def _completion_link(activation_id: str) -> LinkType:
    return constructors.link_endpoint('cmk.gui.plugins.openapi.endpoints.activate_changes',
                                      'cmk/wait-for-completion',
                                      parameters={'activation_id': activation_id})


def _serve_activation_run(activation_id, is_running=False):
    """Serialize the activation response"""
    links = []
    action = "has completed"
    if is_running:
        action = "was started"
        links.append(_completion_link(activation_id))
    return constructors.serve_json(
        constructors.domain_object(
            domain_type='activation_run',
            identifier=activation_id,
            title=f'Activation {activation_id} {action}.',
            deletable=False,
            editable=False,
            links=links,
        ))


@Endpoint(constructors.object_action_href('activation_run', '{activation_id}',
                                          'wait-for-completion'),
          'cmk/wait-for-completion',
          method='get',
          path_params=[ACTIVATION_ID],
          will_do_redirects=True,
          output_empty=True)
def activate_changes_state(params):
    """Wait for an activation-run to complete.

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


@Endpoint(constructors.object_href('activation_run', '{activation_id}'),
          'cmk/show',
          method='get',
          path_params=[ACTIVATION_ID],
          response_schema=response_schemas.DomainObject)
def show_activation(params):
    """Show the status of a particular activation-run.
    """
    activation_id = params['activation_id']
    manager = watolib.ActivateChangesManager()
    manager.load()
    manager.load_activation(activation_id)
    return _serve_activation_run(activation_id, is_running=manager.is_running())


@Endpoint(constructors.collection_href('activation_run', 'running'),
          'cmk/run',
          method='get',
          response_schema=response_schemas.DomainObjectCollection)
def list_activations(params):
    """Show all currently running activations"""
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
