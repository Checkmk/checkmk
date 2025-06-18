#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Generate code-examples for the documentation.

To add a new example (new language, library, etc.), a new Jinja2-Template has to be written and
be referenced in the result of _build_code_templates.

"""

import functools
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any, cast, NamedTuple, TypeAlias

import jinja2
from apispec import APISpec

from cmk.utils.jsontype import JsonSerializable

from cmk.gui.openapi.restful_objects.params import fill_out_path_template
from cmk.gui.openapi.restful_objects.type_defs import CodeSample, OpenAPIParameter
from cmk.gui.openapi.spec.spec_generator._type_defs import SpecEndpoint

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
{%- set downloadable = content_type == 'application/octet-stream' %}
{%- if downloadable %}
import shutil{% endif %}
{%- if query_params %}
import urllib.parse{% endif %}
import urllib.request

HOST_NAME = "{{ hostname }}"
SITE_NAME = "{{ site }}"
PROTO = "http" #[http|https]
API_URL = f"{PROTO}://{HOST_NAME}/{SITE_NAME}/check_mk/api/1.0"

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
        {%- if content_type %}
        "Accept": "{{ content_type }}",
        {% endif %}
        {{- list_params(header_params) }}
    },
    {{- comments(comment_format="    # ", request_schema_multiple=request_schema_multiple) }}
    {%- if request_schema %}
    data=json.dumps({{
            request_schema |
            to_python |
            indent(skip_lines=1, spaces=4) }}).encode('utf-8'),
    {%- endif %}
)
# Will raise an HTTPError if status code is >= 400
resp = urllib.request.urlopen(request)
{{ formatted_if_statement }}
"""

CODE_TEMPLATE_CURL = """
{%- set downloadable = content_type == 'application/octet-stream' %}
#!/bin/bash

# NOTE: We recommend all shell users to use the "httpie" examples instead.
#       `curl` should not be used for writing large scripts.
#       This code is provided for debugging purposes only.

HOST_NAME="{{ hostname }}"
SITE_NAME="{{ site }}"
PROTO="http" #[http|https]
API_URL="$PROTO://$HOST_NAME/$SITE_NAME/check_mk/api/1.0"

USERNAME="{{ username }}"
PASSWORD="{{ password }}"

{%- from '_macros' import comments %}
{{ comments(comment_format="# ", request_schema_multiple=request_schema_multiple) }}
curl {%- if includes_redirect %} -L {%- endif %} \\
  {%- if query_params and request_method|upper == 'GET' %}
  --get \\
  {%- endif %}
  {%- if downloadable %}
  -JO \\
  {%- endif %}
  {%- if not includes_redirect and request_method | upper != 'GET' %}
  --request {{ request_method | upper }} \\
  {%- endif %}
  --write-out "\\nxxx-status_code=%{http_code}\\n" \\
  --header "Authorization: Bearer $USERNAME $PASSWORD" \\
  {%- if content_type %}
  --header "Accept: {{ content_type }}" \\
  {% endif %}
{%- for header in header_params %}
  --header "{{ header.name }}: {{ header.example }}" \\
{%- endfor %}
{%- if query_params %}
 {%- for param in query_params %}

  {%- if param.example is defined and param.example %}
    {%- if param.example is iterable and param.example is not string %}
    {%- for example in param.example %}
  --data-urlencode {{ (param.name ~ "=" ~ example) | repr }} \\
    {%- endfor %}
    {%- else %}
  --data-urlencode {{ (param.name ~ "=" ~ param.example) | repr }} \\
    {%- endif %}
  {%- endif %}
 {%- endfor %}
{%- endif %}
{%- if request_schema %}
  --data '{{ request_schema |
          to_json(indent=2, sort_keys=True) |
          _escape_single_quotes |
          indent(skip_lines=1, spaces=8) }}' \\
{%- endif %}
  "$API_URL{{ request_endpoint | fill_out_parameters }}"

"""

CODE_TEMPLATE_HTTPIE = """
#!/bin/bash
HOST_NAME="{{ hostname }}"
SITE_NAME="{{ site }}"
PROTO="http" #[http|https]
API_URL="$PROTO://$HOST_NAME/$SITE_NAME/check_mk/api/1.0"

USERNAME="{{ username }}"
PASSWORD="{{ password }}"

# Requires httpie version >= 3
{%- from '_macros' import comments %}
{{ comments(comment_format="# ", request_schema_multiple=request_schema_multiple) }}
http {{ request_method | upper }} "$API_URL{{ request_endpoint | fill_out_parameters }}" \\
    {%- if does_redirects %}
    --follow \\
    --all \\
    {%- endif %}
    "Authorization: Bearer $USERNAME $PASSWORD" \\
    {%- if content_type %}
    "Accept: {{ content_type }}" \\
    {% endif %}
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
{{ request_schema | httpie_request_body | indent(spaces=4) }}
{%- endif %}
{%- if content_type == 'application/octet-stream' %}
    --download \\
{%- endif %}

"""

# Beware, correct whitespace handling in this template is a bit tricky.
CODE_TEMPLATE_REQUESTS = """
#!/usr/bin/env python3
import pprint
import requests
{%- set downloadable = content_type == 'application/octet-stream' %}
{%- if downloadable %}
import shutil {%- endif %}

HOST_NAME = "{{ hostname }}"
SITE_NAME = "{{ site }}"
PROTO = "http" #[http|https]
API_URL = f"{PROTO}://{HOST_NAME}/{SITE_NAME}/check_mk/api/1.0"

USERNAME = "{{ username }}"
PASSWORD = "{{ password }}"

session = requests.session()
session.headers['Authorization'] = f"Bearer {USERNAME} {PASSWORD}"
{%- if content_type %}
session.headers['Accept'] = '{{ content_type }}'
{%- endif %}
{%- if does_redirects %}
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
            to_python |
            indent(skip_lines=1, spaces=4) }},
    {%- endif %}
    {%- if does_redirects %}
    allow_redirects=True,
    {%- endif %}
    {%- if downloadable %}
    stream=True,
    {%- endif %}
)
{{ formatted_if_statement }}
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


def _to_env(value: list | dict | str) -> str:
    if isinstance(value, list | dict):
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


JsonObject: TypeAlias = dict[str, JsonSerializable]


def _httpie_request_body_lines(prefix: str, field: JsonObject, lines: list[str]) -> list[str]:
    for key, example in field.items():
        match example:
            case None:
                lines.append(prefix + key + ":=null")
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
        examples: a field to example dict

    Returns:
        a str that httpie can use as a request body specification


    >>> httpie_request_body({"foo": "bar bar bar"})
    "foo='bar bar bar'"
    >>> httpie_request_body({"foo": 5})
    'foo:=5'
    >>> httpie_request_body({"foo": None})
    'foo:=null'
    >>> httpie_request_body({"foo": False})
    'foo:=false'
    >>> httpie_request_body({"foo": [1,2,3]})
    "foo:='[1, 2, 3]'"
    >>> httpie_request_body({"foo": {"bar": {"baz" : "buz"}}})
    "foo[bar][baz]='buz'"
    """

    return "\\\n".join(_httpie_request_body_lines("", examples, []))


def code_samples(
    spec: APISpec,
    spec_endpoint: SpecEndpoint,
    request_schema_example: Mapping[str, object] | None,
    multiple_request_schemas: bool,
    includes_redirect: bool,
    header_params: Sequence[OpenAPIParameter],
    path_params: Sequence[OpenAPIParameter],
    query_params: Sequence[OpenAPIParameter],
    site_name: str,
) -> list[CodeSample]:
    """Create a list of rendered code sample Objects

    These are not specified by OpenAPI but are specific to ReDoc.
    """
    env = _jinja_environment(spec)
    result: list[CodeSample] = []
    for example in CODE_EXAMPLES:
        result.append(
            {
                "label": example.label,
                "lang": example.lang,
                "source": env.get_template(example.label)
                .render(
                    hostname="localhost",
                    site=site_name,
                    username="automation",
                    password="test123",
                    content_type=spec_endpoint.content_type,
                    does_redirects=spec_endpoint.does_redirects,
                    path_params=_extract_example(path_params),
                    query_params=_extract_example(query_params),
                    header_params=_extract_example(header_params),
                    includes_redirect=includes_redirect,
                    request_endpoint=spec_endpoint.path,
                    request_method=spec_endpoint.method,
                    request_schema=request_schema_example,
                    request_schema_multiple=multiple_request_schemas,
                    formatted_if_statement=formatted_if_statement_for_responses(
                        list(spec_endpoint.expected_status_codes),
                        spec_endpoint.content_type == "application/octet-stream",
                        example.label,
                    ),
                )
                .strip()
                .rstrip("\\"),
            }
        )
    return result


def _extract_example(parameters: Sequence[Mapping[str, object]]) -> Sequence[dict[str, object]]:
    # TODO: to be cleaned up
    out = []
    for param in parameters:
        new = dict(param)
        if "example" in param:
            pass
        elif (examples := param.get("examples")) and isinstance(examples, list):
            new["example"] = examples[0]
        elif (schema := param.get("schema")) and isinstance(schema, dict):
            if "example" in schema:
                new["example"] = schema["example"]
            elif (examples := schema.get("examples")) and isinstance(examples, list):
                new["example"] = examples[0]
            elif "default" in schema:
                new["example"] = schema["default"]
        elif (
            (c := param.get("content"))
            and isinstance(c, dict)
            and (content := c.get("application/json"))
            and isinstance(c, dict)
        ):
            if "example" in content:
                new["example"] = content["example"]
            elif (schema := content.get("schema")) and isinstance(schema, dict):
                if "example" in schema:
                    new["example"] = schema["example"]
                elif (examples := schema.get("examples")) and isinstance(examples, list):
                    new["example"] = examples[0]
                elif "default" in schema:
                    new["example"] = schema["default"]

        if "example" not in new:
            raise ValueError("Missing example for parameter", new)
        out.append(new)

    return out


def format_nicely(value: Any, indent_level: int = 0) -> str:
    if isinstance(value, dict):
        out = "{\n"
        indent_prefix = (indent_level + 1) * 4 * " "
        for key, val in value.items():
            out += f"{indent_prefix}{format_nicely(key)}: {format_nicely(val, indent_level + 1)},\n"
        return f"{out}{indent_level * 4 * ' '}}}"

    if isinstance(value, list):
        if (
            len(list_str := ", ".join(format_nicely(v) for v in value)) < 35
            and "\n" not in list_str
        ):
            return f"[{list_str}]"

        out = "[\n"
        indent_prefix = (indent_level + 1) * 4 * " "
        for val in value:
            out += f"{indent_prefix}{format_nicely(val, indent_level + 1)},\n"
        return f"{out}{indent_level * 4 * ' '}]"

    if isinstance(value, str):
        return json.dumps(value)

    return repr(value)


@functools.lru_cache
def _jinja_environment(spec: APISpec) -> jinja2.Environment:
    """Create a map with code templates, ready to render.

    We don't want to build all this stuff at the module-level as it is only needed when
    re-generating the spec file.

    >>> class Endpoint:  # doctest: +SKIP
    ...     path = 'foo'
    ...     method = 'get'
    ...     content_type = 'application/json'

    >>> endpoint = Endpoint()  # doctest: +SKIP

    >>> env = _jinja_environment(SPEC)  # doctest: +SKIP
    >>> result = env.get_template('curl').render(  # doctest: +SKIP
    ...     hostname='localhost',
    ...     site='heute',
    ...     username='automation',
    ...     password='test123',
    ...     path_params=[],
    ...     query_params=[],
    ...     header_params=[],
    ...     content_type=endpoint.content_type,
    ...     does_redirects=endpoint.does_redirects,
    ...     request_endpoint=endpoint.path,
    ...     request_method=endpoint.method,
    ...     request_schema={"field_name": "example_value"},
    ...     request_schema_multiple=False,
    ... )

    """
    # NOTE:
    # This is not a security problem, as this is an Environment which accepts no data from the web
    # but is only used to fill in our code examples.
    tmpl_env = jinja2.Environment(  # nosec B701 # BNS:bbfc92
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
        to_env=_to_env,
        to_json=json.dumps,
        to_python=format_nicely,
        repr=repr,
        httpie_request_body=httpie_request_body,
        _escape_single_quotes=_escape_single_quotes,
    )
    # These objects will be available in the templates
    tmpl_env.globals.update(
        spec=spec,
    )
    return tmpl_env


def formatted_if_statement_for_responses(
    expected_response_status_codes: list[int],
    downloadable: bool,
    code_example: str,
) -> str:
    """Return a formatted if-statement for the requests or urrlib code examples.

    Returns:
        A string with a formatted if-statement.

    """
    formatted_str = ""
    target_requests = "requests" == code_example
    status_code_field = "status_code" if target_requests else "status"
    retrieve_data_code = (
        "    pprint.pprint(resp.json())\n"
        if target_requests
        else "    pprint.pprint(json.loads(resp.read().decode()))\n"
    )
    for status_code in sorted(expected_response_status_codes):
        if status_code < 400:
            if len(formatted_str) == 0:
                formatted_str += f"if resp.{status_code_field} == {status_code}:\n"
            else:
                formatted_str += f"elif resp.{status_code_field} == {status_code}:\n"

            if status_code == 200:
                if downloadable:
                    formatted_str += "    file_name = resp.headers['content-disposition'].split('filename=')[1].strip('\"')\n"
                    formatted_str += "    with open(file_name, 'wb') as out_file:\n"

                    if target_requests:
                        formatted_str += "        resp.raw.decode_content = True\n"
                        formatted_str += "        shutil.copyfileobj(resp.raw, out_file)\n"
                    else:
                        formatted_str += "        shutil.copyfileobj(resp, out_file)\n"

                    formatted_str += "    print('Done')\n"

                else:
                    formatted_str += retrieve_data_code
            elif status_code == 204:
                formatted_str += "    print('Done')\n"
            elif status_code >= 300:
                formatted_str += "    print('Redirected to', resp.headers['location'])\n"

    if target_requests:
        formatted_str += "else:\n"
        formatted_str += "    raise RuntimeError(pprint.pformat(resp.json()))\n"

    return formatted_str


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
def fill_out_parameters(ctx: dict[str, Any], val: str) -> str:
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
