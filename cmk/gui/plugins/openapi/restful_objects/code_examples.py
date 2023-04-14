#!/usr/bin/env python3
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Generate code-examples for the documentation.

To add a new example (new language, library, etc.), a new Jinja2-Template has to be written and
be referenced in the result of _build_code_templates.

"""
import functools
import json
import re
from typing import Any, cast, NamedTuple, TypeAlias

import black
import jinja2
from apispec.ext.marshmallow import resolve_schema_instance
from marshmallow import Schema

from cmk.utils.site import omd_site

from cmk.gui import fields
from cmk.gui.plugins.openapi.restful_objects.params import fill_out_path_template, to_openapi
from cmk.gui.plugins.openapi.restful_objects.specification import SPEC
from cmk.gui.plugins.openapi.restful_objects.type_defs import CodeSample, OpenAPIParameter

CODE_TEMPLATE_MACROS = """
{%- macro comments(comment_format="# ", request_schema_multiple=False) %}
{%- set cf = comment_format %}
{%- if request_schema_multiple %}
{{ (cf ~ "This schema has multiple variations. Please refer to the 'Payload' section for details.") |
   wordwrap(60) | replace('\\n', ('\\n' ~ cf)) }}
{%- endif %}
{%- endmacro %}

{%- macro list_params(params, indent=8) -%}
{%- for param in params %}{% if not (param.example is defined and (param.example is true or
param.example is false or param.example)) %}{% continue %}{% endif %}
{{ " " * indent }}"{{ param.name }}": {{
            param.example | repr }},{% if param.description is defined and param.description %}  #
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
import pprint
{%- set downloadable = endpoint.content_type == 'application/octet-stream' %}
{%- if downloadable %}
import shutil{% endif %}
{%- if query_params %}
import urllib.parse{% endif %}
import urllib.request

HOST_NAME = "{{ hostname }}"
SITE_NAME = "{{ site }}"
API_URL = f"http://{HOST_NAME}/{SITE_NAME}/check_mk/api/1.0"

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
        "Accept": "{{ endpoint.content_type }}",
        {{- list_params(header_params) }}
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
{%- if downloadable %}
if resp.status_code == 200:
    file_name = resp.headers["content-disposition"].split("filename=")[1].strip('\"')
    with open(file_name, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)
    print("Done")
{%- else %}
if resp.status_code == 200:
    pprint.pprint(resp.json())
elif resp.status_code == 204:
    print("Done")
{%- endif %}
{%- if endpoint.does_redirects %}
elif resp.status_code == 302:
    print("Redirected to", resp.headers["location"])
{%- endif %}
else:
    raise RuntimeError(pprint.pformat(resp.json()))
"""

CODE_TEMPLATE_CURL = """
#!/bin/bash

# NOTE: We recommend all shell users to use the "httpie" examples instead.

HOST_NAME="{{ hostname }}"
SITE_NAME="{{ site }}"
API_URL="http://$HOST_NAME/$SITE_NAME/check_mk/api/1.0"

USERNAME="{{ username }}"
PASSWORD="{{ password }}"

{%- from '_macros' import comments %}
{{ comments(comment_format="# ", request_schema_multiple=request_schema_multiple) }}
out=$(
  curl \\
{%- if query_params %}
    -G \\
{%- endif %}
    --request {{ request_method | upper }} \\
    --write-out "\\nxxx-status_code=%{http_code}\\n" \\
    --header "Authorization: Bearer $USERNAME $PASSWORD" \\
    --header "Accept: {{ endpoint.content_type }}" \\
{%- for header in header_params %}
    --header "{{ header.name }}: {{ header.example }}" \\
{%- endfor %}
{%- if query_params %}
 {%- for param in query_params %}

  {%- if param.example is defined and param.example %}
    {%- if param.example is iterable and param.example is not string %}
    {%- for example in param.example %}
    --data-urlencode {{ (param.name + "=" + example) | repr }} \\
    {%- endfor %}
    {%- else %}
    --data-urlencode {{ (param.name + "=" + param.example) | repr }} \\
    {%- endif %}
  {%- endif %}
 {%- endfor %}
{%- endif %}
{%- if request_schema %}
    --data '{{ request_schema |
            to_dict |
            to_json(indent=2, sort_keys=True) |
            _escape_single_quotes |
            indent(skip_lines=1, spaces=8) }}' \\
{%- endif %}
    "$API_URL{{ request_endpoint | fill_out_parameters }}")

resp=$( echo "${out}" | grep -v "xxx-status_code" )
code=$( echo "${out}" | awk -F"=" '/^xxx-status_code/ {print $2}')

# For indentation, please install 'jq' (JSON query tool)
echo "$resp" | jq
# echo "$resp"

if [[ $code -lt 400 ]]; then
    echo "OK"
    exit 0
else
    echo "Request error"
    exit 1
fi
"""

CODE_TEMPLATE_HTTPIE = """
#!/bin/bash
HOST_NAME="{{ hostname }}"
SITE_NAME="{{ site }}"
API_URL="http://$HOST_NAME/$SITE_NAME/check_mk/api/1.0"

USERNAME="{{ username }}"
PASSWORD="{{ password }}"

# Requires httpie version >= 3
{%- from '_macros' import comments %}
{{ comments(comment_format="# ", request_schema_multiple=request_schema_multiple) }}
http {{ request_method | upper }} "$API_URL{{ request_endpoint | fill_out_parameters }}" \\
    {%- if endpoint.does_redirects %}
    --follow \\
    --all \\
    {%- endif %}
    "Authorization: Bearer $USERNAME $PASSWORD" \\
    "Accept: {{ endpoint.content_type }}" \\
{%- for header in header_params %}
    '{{ header.name }}:{{ header.example }}' \\
{%- endfor %}
{%- if query_params %}
 {%- for param in query_params %}
  {%- if param.example is defined and param.example %}
    {{ param.name }}=='{{ param.example }}' \\
  {%- endif %}
 {%- endfor %}
{%- endif %}
{%- if request_schema %}
{{ request_schema | to_dict | httpie_request_body | indent(spaces=4) }}
{%- endif %}
{%- if endpoint.content_type == 'application/octet-stream' %}
    --download \\
{%- endif %}

"""

# Beware, correct whitespace handling in this template is a bit tricky.
CODE_TEMPLATE_REQUESTS = """
#!/usr/bin/env python3
import pprint
import requests
{%- set downloadable = endpoint.content_type == 'application/octet-stream' %}
{%- if downloadable %}
import shutil {%- endif %}

HOST_NAME = "{{ hostname }}"
SITE_NAME = "{{ site }}"
API_URL = f"http://{HOST_NAME}/{SITE_NAME}/check_mk/api/1.0"

USERNAME = "{{ username }}"
PASSWORD = "{{ password }}"

session = requests.session()
session.headers['Authorization'] = f"Bearer {USERNAME} {PASSWORD}"
session.headers['Accept'] = '{{ endpoint.content_type }}'
{%- if endpoint.does_redirects %}
session.max_redirects = 100  # increase if necessary
{%- endif %}
{%- set method = request_method | lower %}

{%- from '_macros' import show_params, comments %}

resp = session.{{ method }}(
    f"{API_URL}{{ request_endpoint | fill_out_parameters }}",
    {{- show_params("params", query_params, comment="goes into query string") }}
    {{- show_params("headers", header_params) }}
    {{- comments(comment_format="    # ", request_schema_multiple=request_schema_multiple) }}
    {%- if request_schema %}
    json={{
            request_schema |
            to_dict |
            to_python |
            indent(skip_lines=1, spaces=4) }},
    {%- endif %}
    {%- if endpoint.does_redirects %}
    allow_redirects=True,
    {%- endif %}
    {%- if downloadable %}
    stream=True,
    {%- endif %}
)
{%- if downloadable %}
if resp.status_code == 200:
    file_name = resp.headers["content-disposition"].split("filename=")[1].strip('\"')
    with open(file_name, 'wb') as out_file:
        resp.raw.decode_content = True
        shutil.copyfileobj(resp.raw, out_file)
    print("Done")
{%- else %}
if resp.status_code == 200:
    pprint.pprint(resp.json())
elif resp.status_code == 204:
    print("Done")
{%- endif %}
{%- if endpoint.does_redirects %}
elif resp.status_code == 302:
    print("Redirected to", resp.headers["location"])
{%- endif %}
else:
    raise RuntimeError(pprint.pformat(resp.json()))
"""


class CodeExample(NamedTuple):
    lang: str
    label: str
    template: str


# NOTE: To add a new code-example, you need to add them to this list.
CODE_EXAMPLES: list[CodeExample] = [
    CodeExample(lang="python", label="requests", template=CODE_TEMPLATE_REQUESTS),
    CodeExample(lang="python", label="urllib", template=CODE_TEMPLATE_URLLIB),
    CodeExample(lang="bash", label="httpie", template=CODE_TEMPLATE_HTTPIE),
    CodeExample(lang="bash", label="curl", template=CODE_TEMPLATE_CURL),
]

# The examples will appear in the order they are put in above, as starting from Python 3.7, dicts
# keep insertion order.
TEMPLATES = {
    "_macros": CODE_TEMPLATE_MACROS,
    **{example.label: example.template for example in CODE_EXAMPLES},
}


def _to_env(value) -> str:  # type: ignore[no-untyped-def]
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
    return "".join(re.split(r"(\w\.)", text)[:2])


def field_value(field: fields.Field) -> str:
    return field.metadata["example"]


def to_dict(schema: Schema) -> dict[str, str]:
    """Convert a Schema-class to a dict-representation.

    Examples:

        >>> from cmk.gui.fields.utils import BaseSchema
        >>> from cmk import fields
        >>> class SayHello(BaseSchema):
        ...      message = fields.String(example="Hello world!")
        ...      message2 = fields.String(example="Hello Bob!")
        >>> to_dict(SayHello())
        {'message': 'Hello world!', 'message2': 'Hello Bob!'}

        >>> class Nobody(BaseSchema):
        ...      expects = fields.String()
        >>> to_dict(Nobody())
        Traceback (most recent call last):
        ...
        KeyError: "Field 'Nobody.expects' has no 'example'"

    Args:
        schema:
            A Schema instance with all it's fields having an `example` key.

    Returns:
        A dict with the field-names as a key and their example as value.

    """
    if not getattr(schema.Meta, "ordered", False):
        # NOTE: We need this to make sure our checkmk.yaml spec file is always predictably sorted.
        raise Exception(f"Schema '{schema.__module__}.{schema.__class__.__name__}' is not ordered.")
    ret = {}
    for name, field in schema.declared_fields.items():
        try:
            ret[name] = field.metadata["example"]
        except KeyError as exc:
            raise KeyError(f"Field '{schema.__class__.__name__}.{name}' has no {exc}")
    return ret


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


    Returns:
        A dict with the key being the parameters name and the value being the parameter.
    """
    return {
        param["name"]: param for param in param_list if "in" in param and param["in"] != "header"
    }


JsonObject: TypeAlias = dict[
    str, int | float | str | bool | dict[str, "JsonObject"] | list["JsonObject"]
]


def _httpie_request_body_lines(prefix: str, field: JsonObject, lines: list[str]) -> list[str]:
    for key, example in field.items():
        match example:
            case bool():
                lines.append(prefix + key + ":=" + str(example).lower())
            case int() | float():
                lines.append(prefix + key + ":=" + str(example))
            case str():
                lines.append(prefix + key + "=" + "'" + str(example) + "'")
            case list():
                lines.append(prefix + key + ":=" + "'" + json.dumps(example) + "'")
            case dict():
                nested = cast(dict, example)
                _httpie_request_body_lines(
                    f"{prefix}{key}", {f"[{key}]": val for key, val in nested.items()}, lines
                )
            case _:
                raise ValueError(f"Value of unexpected type: {example} of type {type(example)}")
    return lines


def httpie_request_body(examples: JsonObject) -> str:
    """

    Args:
        examples: a field to example dict, as created by `to_dict`

    Returns:
        a str that httpie can use as a request body specification


    >>> httpie_request_body({"foo": "bar bar bar"})
    "foo='bar bar bar'"
    >>> httpie_request_body({"foo": 5})
    'foo:=5'
    >>> httpie_request_body({"foo": False})
    'foo:=false'
    >>> httpie_request_body({"foo": [1,2,3]})
    "foo:='[1, 2, 3]'"
    >>> httpie_request_body({"foo": {"bar": {"baz" : "buz"}}})
    "foo[bar][baz]='buz'"
    """

    return "\\\n".join(_httpie_request_body_lines("", examples, []))


def code_samples(  # type:ignore[no-untyped-def]
    endpoint,
    header_params,
    path_params,
    query_params,
) -> list[CodeSample]:
    """Create a list of rendered code sample Objects

    These are not specified by OpenAPI but are specific to ReDoc.

    Examples:

        >>> class Endpoint:  # doctest: +SKIP
        ...     path = 'foo'
        ...     method = 'get'
        ...     content_type = 'application/json'
        ...     request_schema = _get_schema('CreateHost')
        ...     does_redirects = False

        >>> endpoint = Endpoint()  # doctest: +SKIP
        >>> samples = code_samples(endpoint, [], [], [])  # doctest: +SKIP


    """
    env = _jinja_environment()

    return [
        {
            "label": example.label,
            "lang": example.lang,
            "source": env.get_template(example.label)
            .render(
                hostname="localhost",
                site=omd_site(),
                username="automation",
                password="test123",
                endpoint=endpoint,
                path_params=to_openapi(path_params, "path"),
                query_params=to_openapi(query_params, "query"),
                header_params=to_openapi(header_params, "header"),
                request_endpoint=endpoint.path,
                request_method=endpoint.method,
                request_schema=_get_schema(endpoint.request_schema),
                request_schema_multiple=_schema_is_multiple(endpoint.request_schema),
            )
            .strip(),
        }
        for example in CODE_EXAMPLES
    ]


def format_nicely(obj: object) -> str:
    """Format the object nicely.

    Examples:

        While this should format in a stable manner, I'm not quite sure about it.

        >>> format_nicely({'password': 'foo', 'username': 'bar'})
        '{"password": "foo", "username": "bar"}\\n'

    Args:
        obj:
            A python object, which gets represented as valid Python-code when a str() is applied.

    Returns:
        A string of the object, formatted nicely.

    """
    return black.format_str(str(obj), mode=black.Mode(line_length=50))


def _get_schema(schema: str | type[Schema] | None) -> Schema | None:
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
    if _schema_is_multiple(schema):
        type_schemas = _schema.type_schemas  # type: ignore[attr-defined]
        first_key = list(type_schemas.keys())[0]
        _schema = resolve_schema_instance(type_schemas[first_key])

    return _schema


def _schema_is_multiple(schema: str | type[Schema] | None) -> bool:
    if schema is None:
        return False
    _schema = resolve_schema_instance(schema)
    return bool(getattr(_schema, "type_schemas", None))


@functools.lru_cache
def _jinja_environment() -> jinja2.Environment:
    """Create a map with code templates, ready to render.

    We don't want to build all this stuff at the module-level as it is only needed when
    re-generating the SPEC file.

    >>> class Endpoint:  # doctest: +SKIP
    ...     path = 'foo'
    ...     method = 'get'
    ...     content_type = 'application/json'
    ...     request_schema = _get_schema('CreateHost')

    >>> endpoint = Endpoint()  # doctest: +SKIP

    >>> env = _jinja_environment()
    >>> result = env.get_template('curl').render(  # doctest: +SKIP
    ...     hostname='localhost',
    ...     site='heute',
    ...     username='automation',
    ...     password='test123',
    ...     path_params=[],
    ...     query_params=[],
    ...     header_params=[],
    ...     endpoint=endpoint,
    ...     request_endpoint=endpoint.path,
    ...     request_method=endpoint.method,
    ...     request_schema=_get_schema(endpoint.request_schema),
    ...     request_schema_multiple=_schema_is_multiple('CreateHost'),
    ... )

    """
    # NOTE:
    # This is not a security problem, as this is an Environment which accepts no data from the web
    # but is only used to fill in our code examples.
    tmpl_env = jinja2.Environment(  # nosec
        extensions=["jinja2.ext.loopcontrols"],
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
        field_value=field_value,
        to_dict=to_dict,
        to_env=_to_env,
        to_json=json.dumps,
        to_python=format_nicely,
        repr=repr,
        httpie_request_body=httpie_request_body,
        _escape_single_quotes=_escape_single_quotes,
    )
    # These objects will be available in the templates
    tmpl_env.globals.update(
        spec=SPEC,
    )
    return tmpl_env


def _escape_single_quotes(text: str) -> str:
    return text.replace("'", "'\\''")


def to_param_dict(params: list[OpenAPIParameter]) -> dict[str, OpenAPIParameter]:
    """

    >>> to_param_dict([{'name': 'Foo'}, {'name': 'Bar'}])
    {'Foo': {'name': 'Foo'}, 'Bar': {'name': 'Bar'}}

    Args:
        params:

    Returns:

    """
    res = {}
    for entry in params:
        if "name" not in entry:
            raise ValueError(f"Illegal parameter (name missing) ({entry!r}) in {params!r}")
        res[entry["name"]] = entry
    return res


@jinja2.pass_context
def fill_out_parameters(ctx: dict[str, Any], val) -> str:  # type:ignore[no-untyped-def]
    """Fill out path parameters, either using the global parameter or the endpoint defined ones.

    This assumes the parameters to be defined as such:

        ctx['parameters']: Dict[str, Dict[str, str]]

    Args:
        ctx: A Jinja2 context
        val: The path template.

    Examples:

        This does a lot of Jinja2 setup. We may want to move this to a "proper" test-file.

        >>> parameters = {}
        >>> env = jinja2.Environment()
        >>> env.filters['fill_out_parameters'] = fill_out_parameters

        >>> host = {'name': 'host', 'in': 'path', 'example': 'example.com'}
        >>> service = {'name': 'service', 'in': 'path', 'example': 'CPU'}

        >>> tmpl_source = '{{ "/{host}/{service}" | fill_out_parameters }}'
        >>> tmpl = env.from_string(tmpl_source)

        >>> tmpl.render(path_params=[])
        Traceback (most recent call last):
        ...
        ValueError: Parameter 'host' needed, but not supplied in {}

        >>> tmpl.render(path_params=[host, service])
        '/example.com/CPU'

    Returns:
        A filled out string.
    """
    return fill_out_path_template(val, to_param_dict(ctx["path_params"]))


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
            resp.append((" " * spaces) + line)
    return "\n".join(resp)
