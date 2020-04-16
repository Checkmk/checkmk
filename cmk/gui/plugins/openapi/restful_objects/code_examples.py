#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import collections
import json
import threading

import jinja2
from apispec.ext.marshmallow import resolve_schema_instance  # type: ignore[import]

from cmk.gui.plugins.openapi.restful_objects.specification import PARAM_RE, SPEC

CODE_TEMPLATES_LOCK = threading.Lock()

CODE_TEMPLATE_CURL = """
curl \\
    -X {{ request_method | upper }} \\
    --header "Authorization: Bearer username password" \\
    --header "Accept: application/json" \\
    -d '{{ request_schema | to_dict | to_json(indent=2) | indent(skip_lines=1, spaces=8) }}' \\
    {{ request_endpoint | fill_out_parameters }}
"""

CODE_TEMPLATE_HTTPIE = """
http {{ request_method | upper }} {{ request_endpoint | fill_out_parameters }} \\
    'Authorization: Bearer username password' \\
    {% for key, value in (request_schema | to_dict).items() -%}
        {{ key }}='{{ value | to_env }}'{% if not loop.last %} \\{% endif %}
    {% endfor -%}
"""

CODE_TEMPLATE_REQUESTS = """
import requests
{% set method = request_method | lower %}
resp = requests.{{ method }}("{{ request_endpoint | fill_out_parameters }}",
    headers={'Authorization': 'Bearer username password'},
    {% if method == "get" %}params{% else %}data{% endif %}={{
            request_schema |
            to_dict |
            to_json(indent=4, sort_keys=True) |
            indent(skip_lines=1, spaces=4) }},
)
resp.raise_for_status()
"""


def to_env(value):
    if isinstance(value, dict):
        return json.dumps(value)

    return value


def to_dict(schema):
    ret = {}
    for name, field in schema.fields.items():
        try:
            ret[name] = field.metadata['example']
        except KeyError:
            raise KeyError("%s.%s has no example (%r)" % (
                schema.__class__.__name__,
                name,
                field,
            ))
    return ret


# noinspection PyDefaultArgument
def code_samples(path, method, request_schema, code_templates=[]):  # pylint: disable=dangerous-default-value
    """Create a list of rendered code sample Objects

    These are not specified by OpenAPI but are specific to ReDoc."""
    if not code_templates:
        with CODE_TEMPLATES_LOCK:
            if not code_templates:
                code_templates.append(_build_code_templates())

    return [{
        'lang': language,
        'source': template.render(
            request_endpoint=path,
            request_method=method,
            request_schema=resolve_schema_instance(request_schema),
        ).strip(),
    } for language, template in code_templates[0].items()]


def _build_code_templates():
    """Create a map with code templates, ready to render.

    We don't want to build all this stuff at the module-level as it is only needed when
    re-generating the SPEC file.

    >>> tmpls = _build_code_templates()
    >>> result = tmpls['curl'].render(
    ...     request_endpoint='foo',
    ...     request_method='get',
    ...     request_schema=resolve_schema_instance('CreateHost')
    ... )
    >>> assert '&' not in result

    """
    # NOTE:
    # This is not a security problem, as this is an Environment which accepts no data from the web
    # but is only used to fill in our code examples.
    tmpl_env = jinja2.Environment(  # nosec
        autoescape=False,  # because copy-paste we don't want HTML entities in our code examples.
        loader=jinja2.BaseLoader(),
        undefined=jinja2.StrictUndefined,
        keep_trailing_newline=True,
    )
    # These functions will be available in the templates
    tmpl_env.filters.update(
        fill_out_parameters=fill_out_parameters,
        indent=indent,
        to_dict=to_dict,
        to_env=to_env,
        to_json=json.dumps,
    )
    # These objects will be available in the templates
    tmpl_env.globals.update(
        spec=SPEC,
        parameters=SPEC.components._parameters,
    )

    # NOTE: To add a new code-example, just add them to this OrderedDict. The examples will
    # appear in the order they are put in here.
    return collections.OrderedDict([
        ('curl', tmpl_env.from_string(CODE_TEMPLATE_CURL)),
        ('httpie', tmpl_env.from_string(CODE_TEMPLATE_HTTPIE)),
        ('requests', tmpl_env.from_string(CODE_TEMPLATE_REQUESTS)),
    ])


@jinja2.contextfilter
def fill_out_parameters(ctx, val):
    return _fill_out_parameters(val, ctx['parameters'])


def _fill_out_parameters(orig_path, parameters):
    """Fill out a simple template.

    Examples:

        >>> param_spec = {'var': {'example': 'foo'}}
        >>> _fill_out_parameters('/path/{var}', param_spec)
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


def indent(s, skip_lines=0, spaces=2):
    """Indent a text by a number of spaces.

    Lines can be skipped from the start by using the `skip_lines` parameter.
    The indentation depth can be controlled with the `spaces` parameter.

    Examples:

        >>> text = u"blah1\\nblah2\\nblah3"
        >>> indent(text, spaces=1)
        u' blah1\\n blah2\\n blah3'

        >>> indent(text, skip_lines=2, spaces=1)
        u'blah1\\nblah2\\n blah3'

    Args:
        s:
            The string which shall be indented.

        skip_lines:
            How many lines shall be ignored for indenting.

        spaces:
            By how many spaces the text should be indented.

    Returns:
        The indented string.

    """
    resp = []
    for count, line in enumerate(s.splitlines()):
        if count < skip_lines:
            resp.append(line)
        else:
            resp.append((' ' * spaces) + line)
    return u'\n'.join(resp)
