#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import collections
import json
import re
import threading

import jinja2
from apispec.ext.marshmallow import resolve_schema_instance  # type: ignore[import]

from cmk.gui.plugins.openapi.restful_objects.specification import SPEC
from cmk.gui.plugins.openapi.restful_objects.utils import fill_out_path_template, ParamDict

CODE_TEMPLATES_LOCK = threading.Lock()

CODE_TEMPLATE_CURL = """
API_URL = "http://$HOST_NAME/$SITE_NAME/check_mk/api/v0"
USERNAME = "..."
PASSWORD = "..."

curl \\
    -X {{ request_method | upper }} \\
    --header "Authorization: Bearer $USERNAME $PASSWORD" \\
    --header "Accept: application/json" \\
{%- for header in headers %}
    --header "{{ header['name'] }}: {{ header['example'] }}" \\
{%- endfor %}{% if request_schema %}
    -d '{{ request_schema | to_dict | to_json(indent=2) | indent(skip_lines=1, spaces=8) }}' \\
{%- endif %}
    "$API_URL{{ request_endpoint | fill_out_parameters }}"
"""

CODE_TEMPLATE_HTTPIE = """
API_URL = "http://$HOST_NAME/$SITE_NAME/check_mk/api/v0"
USERNAME = "..."
PASSWORD = "..."

http {{ request_method | upper }} "$API_URL{{ request_endpoint | fill_out_parameters }}" \\
    "Authorization: Bearer $USERNAME $PASSWORD"
{%- for header in headers %} \\
    '{{ header['name'] }}: {{ header['example'] }}'{% if not loop.last %} \\{% endif %}
{%- endfor %}{% if request_schema %} \\
    {% for key, value in (request_schema | to_dict).items() -%}
        {{ key }}='{{ value | to_env }}'{% if not loop.last %} \\{% endif %}
    {% endfor -%}
{% endif %}
"""

# Beware, correct whitespace handling in this template is a bit tricky.
CODE_TEMPLATE_REQUESTS = """
import requests

session = requests.session()
session.headers['Authorization'] = 'Bearer username password'
session.headers['Accept'] = 'application/json'
{%- set method = request_method | lower %}

# Replace HOST_NAME and SITE_NAME with the names from your host and site.
API_URL = 'http://HOST_NAME/SITE_NAME/check_mk/api/v0'

resp = session.{{ method }}(
    API_URL + "{{ request_endpoint | fill_out_parameters }}",
{%- for header in headers %}
{%- if loop.first %}
    headers={ {% endif %}
        "{{ header['name'] }}": "{{ header['example'] }}",{% if header['description'] %}  #
        {%- if header['required'] %} (required){% endif %} {{
        header['description'] | first_sentence }}{% endif %}
{%- if loop.last %}
    },{% endif %}{% endfor %}{% if request_schema %}
    {% if method == "get" %}params{% else %}json{% endif %}={{
            request_schema |
            to_dict |
            to_json(indent=4, sort_keys=True) |
            indent(skip_lines=1, spaces=4) }},{% endif %}
)
resp.raise_for_status()
"""


def to_env(value):
    if isinstance(value, (list, dict)):
        return json.dumps(value)

    return value


def first_sentence(text):
    """Return the first sentence in a string.

    Args:
        text: Some text. Sentences are separated by dots directly following a word.

    Examples:
        >>> first_sentence("This is the first part. This is the second part. Or the third.")
        'This is the first part.'

        >>> first_sentence("This is ... the first part. This is the second part.")
        'This is ... the first part.'

        >>> first_sentence('This is also a sentence')
        'This is also a sentence'

    Returns:
        A string containing only the first sentence of a string.

    """
    return ''.join(re.split(r'(\w\.)', text)[:2])


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


def _is_parameter(param):
    is_primitive_param = isinstance(param, dict) and 'name' in param and 'in' in param
    return isinstance(param, ParamDict) or is_primitive_param


def _transform_params(param_list):
    """Transform a list of parameters to a dict addressable by name.

    Args:
        param_list:
            A list of parameters.

    Examples:

        >>> _transform_params([
        ...     {'name': 'foo', 'in': 'query'},
        ...     'bar',
        ...     {'name': 'ETag', 'in': 'header'},
        ... ])
        {'foo': {'name': 'foo', 'in': 'query'}}

        >>> transformed = _transform_params([
        ...      ParamDict.create('foo', 'query'),
        ...      ParamDict.create('bar', 'header'),
        ... ])
        >>> expected = {
        ...     'foo': {
        ...         'name': 'foo',
        ...         'in': 'query',
        ...         'required': True,
        ...         'allowEmptyValue': False,
        ...         'schema': {'type': 'string'},
        ...     }
        ... }
        >>> assert expected == transformed, transformed

    Returns:
        A dict with the key being the parameters name and the value being the parameter.
    """
    return {
        param['name']: param
        for param in param_list
        if _is_parameter(param) and param['in'] != 'header'
    }


# noinspection PyDefaultArgument
def code_samples(
    path,
    method,
    request_schema,
    operation_spec,
    code_templates=[],
):  # pylint: disable=dangerous-default-value
    """Create a list of rendered code sample Objects

    These are not specified by OpenAPI but are specific to ReDoc."""
    if not code_templates:
        with CODE_TEMPLATES_LOCK:
            if not code_templates:
                code_templates.append(_build_code_templates())

    headers = []
    parameters = operation_spec.get('parameters', [])
    for param in parameters:
        if isinstance(param, dict) and param['in'] == 'header':
            headers.append(param)

    return [{
        'lang': language,
        'source': template.render(
            request_endpoint=path,
            request_method=method,
            request_schema=(resolve_schema_instance(request_schema)
                            if request_schema is not None else None),
            endpoint_parameters=_transform_params(parameters),
            headers=headers,
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
    ...     request_schema=resolve_schema_instance('CreateHost'),
    ...     headers=[],
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
        first_sentence=first_sentence,
        indent=indent,
        to_dict=to_dict,
        to_env=to_env,
        to_json=json.dumps,
    )
    # These objects will be available in the templates
    tmpl_env.globals.update(
        spec=SPEC,
        parameters=SPEC.components.to_dict().get('parameters', {}),
    )

    # NOTE: To add a new code-example, just add them to this OrderedDict. The examples will
    # appear in the order they are put in here.
    return collections.OrderedDict([
        ('requests', tmpl_env.from_string(CODE_TEMPLATE_REQUESTS)),
        ('curl', tmpl_env.from_string(CODE_TEMPLATE_CURL)),
        ('httpie', tmpl_env.from_string(CODE_TEMPLATE_HTTPIE)),
    ])


@jinja2.contextfilter
def fill_out_parameters(ctx, val):
    """Fill out path parameters, either using the global parameter or the endpoint defined ones.

    This assumes the parameters to be defined as such:

        ctx['parameters']: Dict[str, ParamDict]
        ctx['endpoint_parameters']: Dict[str, ParamDict]

    Args:
        ctx: A Jinja2 context
        val: The path template.

    Examples:

        This does a lot of Jinja2 setup. We may want to move this to a "proper" test-file.

        >>> parameters = {}
        >>> env = jinja2.Environment()
        >>> env.filters['fill_out_parameters'] = fill_out_parameters
        >>> env.globals['parameters'] = parameters

        >>> global_host_param = ParamDict.create('host', 'path', example='global_host')
        >>> host = ParamDict.create('host', 'path', example='host')
        >>> service = ParamDict.create('service', 'path', example='service')

        >>> tmpl_source = '{{ "/{host}/{service}" | fill_out_parameters }}'
        >>> tmpl = env.from_string(tmpl_source)

        >>> tmpl.render(endpoint_parameters={})
        Traceback (most recent call last):
        ...
        KeyError: 'host'

        >>> tmpl.render(endpoint_parameters={'host': host, 'service': service})
        '/host/service'

        >>> parameters['host'] = global_host_param
        >>> tmpl.render(endpoint_parameters={'host': host, 'service': service})
        '/host/service'

        >>> parameters['host'] = global_host_param
        >>> tmpl.render(endpoint_parameters={'service': service})
        '/global_host/service'


    Returns:
        A filled out string.
    """
    parameters = {}
    parameters.update(ctx['parameters'])
    parameters.update(ctx['endpoint_parameters'])
    return fill_out_path_template(val, parameters)


def indent(s, skip_lines=0, spaces=2):
    """Indent a text by a number of spaces.

    Lines can be skipped from the start by using the `skip_lines` parameter.
    The indentation depth can be controlled with the `spaces` parameter.

    Examples:

        >>> text = u"blah1\\nblah2\\nblah3"
        >>> indent(text, spaces=1)
        ' blah1\\n blah2\\n blah3'

        >>> indent(text, skip_lines=2, spaces=1)
        'blah1\\nblah2\\n blah3'

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
    return '\n'.join(resp)
