# File copied from:
# https://github.com/bazelbuild/rules_python/blob/504caab8dece64bb7ee8f1eea975f56be5b6f926/python/pip_install/requirements_parser.bzl
# Copyright 2023 The Bazel Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"Pip requirements parser for Starlark"

_STATE = struct(
    # Consume extraneous whitespace
    ConsumeSpace = 0,
    # Consume a comment
    ConsumeComment = 1,
    # Parse the name of a pip package
    ParseDependency = 2,
    # Parse a full requirement line
    ParseRequirement = 3,
    # Parse a pip option
    ParseOption = 4,
)

EOF = {}

def parse(content):
    """A simplistic (and incomplete) pip requirements lockfile parser.

    Parses package names and their full requirement lines, as well pip
    options.

    Args:
      content: lockfile content as a string

    Returns:
      Struct with fields `requirements` and `options`.

      requirements: List of requirements, where each requirement is a 2-element
        tuple containing the package name and the requirement line.
        E.g., [(certifi', 'certifi==2021.10.8 --hash=sha256:7888...'), ...]

      options: List of pip option lines
    """
    content = content.replace("\r", "")
    result = struct(
        requirements = [],
        options = [],
    )
    state = _STATE.ConsumeSpace
    buffer = ""

    inputs = content.elems()[:]
    inputs.append(EOF)

    for input in inputs:
        if state == _STATE.ConsumeSpace:
            (state, buffer) = _handleConsumeSpace(input)
        elif state == _STATE.ConsumeComment:
            (state, buffer) = _handleConsumeComment(input, buffer, result)
        elif state == _STATE.ParseDependency:
            (state, buffer) = _handleParseDependency(input, buffer, result)
        elif state == _STATE.ParseOption:
            (state, buffer) = _handleParseOption(input, buffer, result)
        elif state == _STATE.ParseRequirement:
            (state, buffer) = _handleParseRequirement(input, buffer, result)
        else:
            fail("Unknown state %d" % state)

    new_result = struct(
        requirements = [(name, sort_hashes(rest)) for name, rest in result.requirements],
        options = result.options,
    )

    return new_result

# buildifier: disable=function-docstring
def sort_hashes(req):
    delim = req.find("--hash")
    if delim < 0:
        return req
    name_version = req[:delim - 1].strip()
    sorted_hashes = [h for h in sorted(req[delim:].split(" ")) if h != ""]
    return " ".join([name_version] + sorted_hashes)

def _handleConsumeSpace(input):
    if input == EOF:
        return (_STATE.ConsumeSpace, "")
    if input.isspace():
        return (_STATE.ConsumeSpace, "")
    elif input == "#":
        return (_STATE.ConsumeComment, "")
    elif input == "-":
        return (_STATE.ParseOption, input)

    return (_STATE.ParseDependency, input)

def _handleConsumeComment(input, buffer, result):
    if input == "\n":
        if len(result.requirements) > 0 and len(result.requirements[-1]) == 1:
            result.requirements[-1] = (result.requirements[-1][0], buffer.rstrip(" \n"))
            return (_STATE.ConsumeSpace, "")
        elif len(buffer) > 0:
            result.options.append(buffer.rstrip(" \n"))
            return (_STATE.ConsumeSpace, "")
        return (_STATE.ConsumeSpace, "")
    return (_STATE.ConsumeComment, buffer)

def _handleParseDependency(input, buffer, result):
    if input == EOF:
        fail("Enountered unexpected end of file while parsing requirement")
    elif input.isspace() or input in [">", "<", "~", "=", ";", "["]:
        result.requirements.append((buffer,))
        return (_STATE.ParseRequirement, buffer + input)

    return (_STATE.ParseDependency, buffer + input)

def _handleParseOption(input, buffer, result):
    if input == "\n" and buffer.endswith("\\"):
        return (_STATE.ParseOption, buffer[0:-1])
    elif input == " ":
        result.options.append(buffer.rstrip("\n"))
        return (_STATE.ParseOption, "")
    elif input == "\n" or input == EOF:
        result.options.append(buffer.rstrip("\n"))
        return (_STATE.ConsumeSpace, "")
    elif input == "#" and (len(buffer) == 0 or buffer[-1].isspace()):
        return (_STATE.ConsumeComment, buffer)

    return (_STATE.ParseOption, buffer + input)

def _handleParseRequirement(input, buffer, result):
    if input == "\n" and buffer.endswith("\\"):
        return (_STATE.ParseRequirement, buffer[0:-1])
    elif input == "\n" or input == EOF:
        result.requirements[-1] = (result.requirements[-1][0], buffer.rstrip(" \n"))
        return (_STATE.ConsumeSpace, "")
    elif input == "#" and (len(buffer) == 0 or buffer[-1].isspace()):
        return (_STATE.ConsumeComment, buffer)

    return (_STATE.ParseRequirement, buffer + input)
