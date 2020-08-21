#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Generate code-examples for the documentation.

To add a new example (new language, library, etc.), a new Jinja2-Template has to be written and
be referenced in the result of _build_code_templates.

"""
import json
import re
import threading
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Type, Union

import jinja2
import yapf.yapflib.yapf_api  # type: ignore[import]
from apispec.ext.marshmallow import resolve_schema_instance  # type: ignore[import]
from marshmallow import Schema  # type: ignore[import]

from cmk.gui.plugins.openapi.restful_objects.specification import SPEC
from cmk.gui.plugins.openapi.restful_objects.type_defs import (
    AnyParameter,
    AnyParameterAndReference,
    fill_out_path_template,
    HTTPMethod,
    LocationType,
    OperationSpecType,
    ParamDict,
    RequestSchema,
)

CODE_TEMPLATES_LOCK = threading.Lock()

# This is
CODE_TEMPLATE_MACROS = """
{%- macro comments(comment_format="# ", request_schema_multiple=False) %}
{%- set cf = comment_format %}
{%- if request_schema_multiple %}
{{ (cf ~ "This schema has multiple variations. Please refer to the 'Payload' section for details.") |
   wordwrap(60) | replace('\\n', ('\\n' ~ cf)) }}
{%- endif %}
{%- endmacro %}

{%- macro list_params(params, indent=8) -%}
{%- for param in params %}{% if not (param.example is defined and param.example) %}{% continue %}{% endif %}
{{ " " * indent }}"{{ param.name }}": "{{
            param.example }}",{% if param.description is defined and param.description %}  #
        {%- if param.required %} (required){% endif %} {{
            param.description | first_sentence }}{% endif %}
{%- endfor %}
{%- endmacro %}

{%- macro show_params(name, params, comment=None) %}
{%- if params %}
    {{ name }}={ {%- if comment %}  # {{ comment }}{% endif %}
        {{- list_params(params) }}
    },
{%- endif %}
{%- endmacro %}

{%- macro show_query_params(params) %}
{%- if params %}
{%- for param in params %}
{%- if not (param.example is defined and param.example) %}
    {%- continue %}
{%- endif %}
{%- if not loop.first %}&{% endif %}
{{- param.name }}={{ param.example }}
{%- endfor %}
{%- endif %}
{%- endmacro %}
"""

CODE_TEMPLATE_URLLIB = """
#!/usr/bin/env python3
import json
{%- if query_params %}
import urllib.parse{% endif %}
import urllib.request

HOST_NAME = "{{ hostname }}"
SITE_NAME = "{{ site }}"
API_URL = f"http://{HOST_NAME}/{SITE_NAME}/check_mk/api/v0"

USERNAME = "{{ username }}"
PASSWORD = "{{ password }}"

{%- from '_macros' import list_params, comments %}
{%- if query_params %}

query_string = urllib.parse.urlencode({
    {{- list_params(query_params, indent=4) }}
})
{%- endif %}

request = urllib.request.Request(
    f"{API_URL}{{ request_endpoint | fill_out_parameters }}
        {%- if query_params %}?{query_string}{% endif %}",
    method="{{ request_method | upper }}",
    headers={
        "Authorization": f"Bearer {USERNAME} {PASSWORD}",
        "Accept": "application/json",
        {{- list_params(headers) }}
    },
    {{- comments(comment_format="    # ", request_schema_multiple=request_schema_multiple) }}
    {%- if request_schema %}
    data=json.dumps({{
            request_schema |
            to_dict |
            to_python |
            indent(skip_lines=1, spaces=4) }}).encode('utf-8'),
    {%- endif %}
)
response = urllib.request.urlopen(request)
data = json.loads(response.read())
"""

CODE_TEMPLATE_CURL = """
#!/bin/bash
HOST_NAME="{{ hostname }}"
SITE_NAME="{{ site }}"
API_URL="http://$HOST_NAME/$SITE_NAME/check_mk/api/v0"

USERNAME="{{ username }}"
PASSWORD="{{ password }}"

{%- from '_macros' import comments %}
{{ comments(comment_format="# ", request_schema_multiple=request_schema_multiple) }}
curl \\
    -X {{ request_method | upper }} \\
    --header "Authorization: Bearer $USERNAME $PASSWORD" \\
    --header "Accept: application/json" \\
{%- for header in headers %}
    --header "{{ header.name }}: {{ header.example }}" \\
{%- endfor %}
{%- if query_params %}
    -G  \\
 {%- for param in query_params %}
  {%- if param.example is defined and param.example %}
    --data-urlencode "{{ param.name }}={{ param.example }}"{% if not loop.last %} \\{% endif %}
  {%- endif %}
 {%- endfor %}
{%- endif %}
{%- if request_schema %} \\
    --data '{{ request_schema |
            to_dict |
            to_json(indent=2, sort_keys=True) |
            indent(skip_lines=1, spaces=8) }}' \\
{%- endif %}
    "$API_URL{{ request_endpoint | fill_out_parameters }}"
"""

CODE_TEMPLATE_HTTPIE = """
#!/bin/bash
HOST_NAME="{{ hostname }}"
SITE_NAME="{{ site }}"
API_URL="http://$HOST_NAME/$SITE_NAME/check_mk/api/v0"

USERNAME="{{ username }}"
PASSWORD="{{ password }}"

{%- from '_macros' import comments %}
{{ comments(comment_format="# ", request_schema_multiple=request_schema_multiple) }}
http {{ request_method | upper }} "$API_URL{{ request_endpoint | fill_out_parameters }}" \\
    "Authorization: Bearer $USERNAME $PASSWORD" \\
    "Accept: application/json" \\
{%- for header in headers %}
    '{{ header.name }}:{{ header.example }}' \\
{% endfor -%}
{%- if query_params %}
 {%- for param in query_params %}
  {%- if param.example is defined and param.example %}
    {{ param.name }}=="{{ param.example }}" \\
  {%- endif %}
 {%- endfor %}
{%- endif %}
{%- if request_schema %}
 {%- for key, value in (request_schema | to_dict).items() | sort %}
    {{ key }}='{{ value | to_env }}' \\
 {%- endfor %}
{%- endif %}
    --json

"""

# Beware, correct whitespace handling in this template is a bit tricky.
CODE_TEMPLATE_REQUESTS = """
#!/usr/bin/env python3
import requests

HOST_NAME = "{{ hostname }}"
SITE_NAME = "{{ site }}"
API_URL = f"http://{HOST_NAME}/{SITE_NAME}/check_mk/api/v0"

USERNAME = "{{ username }}"
PASSWORD = "{{ password }}"

session = requests.session()
session.headers['Authorization'] = f"Bearer {USERNAME} {PASSWORD}"
session.headers['Accept'] = 'application/json'
{%- set method = request_method | lower %}

{%- from '_macros' import show_params, comments %}

resp = session.{{ method }}(
    f"{API_URL}{{ request_endpoint | fill_out_parameters }}",
    {{- show_params("params", query_params, comment="goes into query string") }}
    {{- show_params("headers", headers) }}
    {{- comments(comment_format="    # ", request_schema_multiple=request_schema_multiple) }}
    {%- if request_schema %}
    json={{
            request_schema |
            to_dict |
            to_python |
            indent(skip_lines=1, spaces=4) }},
    {%- endif %}
)
resp.raise_for_status()
data = resp.json()
"""

CodeExample = NamedTuple("CodeExample", [('lang', str), ('label', str), ('template', str)])

# NOTE: To add a new code-example, you need to add them to this list.
CODE_EXAMPLES: List[CodeExample] = [
    CodeExample(lang='python', label='requests', template=CODE_TEMPLATE_REQUESTS),
    CodeExample(lang='python', label='urllib', template=CODE_TEMPLATE_URLLIB),
    CodeExample(lang='bash', label='curl', template=CODE_TEMPLATE_CURL),
    CodeExample(lang='bash', label='httpie', template=CODE_TEMPLATE_HTTPIE),
]

# The examples will appear in the order they are put in above, as starting from Python 3.7, dicts
# keep insertion order.
TEMPLATES = {
    '_macros': CODE_TEMPLATE_MACROS,
    **{example.label: example.template for example in CODE_EXAMPLES}
}


def _to_env(value) -> str:
    if isinstance(value, (list, dict)):
        return json.dumps(value)

    return value


def first_sentence(text: str) -> str:
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


def to_dict(schema: Schema) -> Dict[str, str]:
    """Convert a Schema-class to a dict-representation.

    Examples:

        >>> from marshmallow import Schema, fields
        >>> class SayHello(Schema):
        ...      message = fields.String(example="Hello world!")
        >>> to_dict(SayHello())
        {'message': 'Hello world!'}

        >>> class Nobody(Schema):
        ...      expects = fields.String()
        >>> to_dict(Nobody())
        Traceback (most recent call last):
        ...
        KeyError: "Schema 'Nobody.expects' has no example."

    Args:
        schema:
            A Schema instance with all it's fields having an `example` key.

    Returns:
        A dict with the field-names as a key and their example as value.

    """
    ret = {}
    for name, field in schema.fields.items():
        if 'example' not in field.metadata:
            raise KeyError(f"Schema '{schema.__class__.__name__}.{name}' has no example.")
        ret[name] = field.metadata['example']
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
    path: str,
    method: HTTPMethod,
    request_schema: RequestSchema,
    operation_spec: OperationSpecType,
) -> List[Dict[str, str]]:
    """Create a list of rendered code sample Objects

    These are not specified by OpenAPI but are specific to ReDoc."""
    env = _jinja_environment()

    parameters = operation_spec.get('parameters', [])

    headers = _filter_params(parameters, 'header')
    query_params = _filter_params(parameters, 'query')

    return [{
        'label': example.label,
        'lang': example.lang,
        'source': env.get_template(example.label).render(
            hostname='localhost',
            site='heute',
            username='automation',
            password='test123',
            request_endpoint=path,
            request_method=method,
            request_schema=_get_schema(request_schema),
            request_schema_multiple=_schema_is_multiple(request_schema),
            endpoint_parameters=_transform_params(parameters),
            headers=headers,
            query_params=query_params,
        ).strip(),
    } for example in CODE_EXAMPLES]


def _filter_params(
    parameters: Sequence[AnyParameterAndReference],
    param_location: LocationType,
) -> Sequence[AnyParameter]:
    query_parameters = []
    for param in parameters:
        if isinstance(param, (dict, ParamDict)) and param['in'] == param_location:
            query_parameters.append(param)
    return query_parameters


def yapf_format(obj):
    style = {
        'COLUMN_LIMIT': 50,
        'ALLOW_SPLIT_BEFORE_DICT_VALUE': False,
        'COALESCE_BRACKETS': True,
        'DEDENT_CLOSING_BRACKETS': True,
    }
    text, _ = yapf.yapflib.yapf_api.FormatCode(str(obj), style_config=style)
    return text


def _get_schema(schema: Optional[Union[str, Type[Schema]]]) -> Optional[Schema]:
    """Get the schema instance of a schema name or class.

    In case of OneOfSchema classes, the first dispatched schema is being returned.

    Args:
        schema:
            Either

    Returns:
        A schema instance.

    """
    if schema is None:
        return None

    # NOTE:
    # In case of a "OneOfSchema" instance, we don't really have any fields on this Schema
    # as it is just there for dispatching. The real fields are on the dispatched classes.
    # We just take the first one and go with that, as we have no way of letting the user chose
    # the dispatching-key by himself (this is a limitation of ReDoc).
    _schema: Schema = resolve_schema_instance(schema)
    if _schema_is_multiple(_schema):
        first_key = list(_schema.type_schemas.keys())[0]
        _schema = resolve_schema_instance(_schema.type_schemas[first_key])

    return _schema


def _schema_is_multiple(schema: Optional[Union[str, Schema]]) -> bool:
    if schema is None:
        return False
    _schema = resolve_schema_instance(schema)
    return hasattr(_schema, 'type_schemas') and _schema.type_schemas


def _jinja_environment() -> jinja2.Environment:
    """Create a map with code templates, ready to render.

    We don't want to build all this stuff at the module-level as it is only needed when
    re-generating the SPEC file.

    >>> env = _jinja_environment()
    >>> result = env.get_template('curl').render(
    ...     hostname='localhost',
    ...     site='heute',
    ...     username='automation',
    ...     password='test123',
    ...     request_endpoint='foo',
    ...     request_method='get',
    ...     request_schema=_get_schema('CreateHost'),
    ...     request_schema_multiple=_schema_is_multiple('CreateHost'),
    ...     endpoint_parameters={},
    ...     query_params=[],
    ...     headers=[],
    ... )
    >>> assert '&' not in result, result

    """
    # NOTE:
    # This is not a security problem, as this is an Environment which accepts no data from the web
    # but is only used to fill in our code examples.
    tmpl_env = jinja2.Environment(  # nosec
        extensions=['jinja2.ext.loopcontrols'],
        autoescape=False,  # because copy-paste we don't want HTML entities in our code examples.
        loader=jinja2.DictLoader(TEMPLATES),
        undefined=jinja2.StrictUndefined,
        keep_trailing_newline=True,
    )
    # These functions will be available in the templates
    tmpl_env.filters.update(
        fill_out_parameters=fill_out_parameters,
        first_sentence=first_sentence,
        indent=indent,
        to_dict=to_dict,
        to_env=_to_env,
        to_json=json.dumps,
        to_python=yapf_format,
    )
    # These objects will be available in the templates
    tmpl_env.globals.update(
        spec=SPEC,
        parameters=SPEC.components.to_dict().get('parameters', {}),
    )
    return tmpl_env


@jinja2.contextfilter
def fill_out_parameters(ctx: Dict[str, Any], val):
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
        ValueError: Parameter 'host' needed, but not supplied.

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
