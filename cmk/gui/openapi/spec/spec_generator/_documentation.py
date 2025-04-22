#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

from apispec.utils import dedent
from marshmallow import Schema
from marshmallow.fields import Field
from marshmallow.schema import SchemaMeta

from cmk.gui.openapi.restful_objects.type_defs import LocationType, RawParameter, SchemaParameter
from cmk.gui.permissions import permission_registry
from cmk.gui.utils import permission_verification as permissions


def _build_description(description_text: str | None, werk_id: int | None = None) -> str:
    r"""Build a OperationSpecType description.

    Examples:

        >>> _build_description(None)
        ''

        >>> _build_description("Foo")
        'Foo'

        >>> _build_description(None, 12345)
        '`WARNING`: This URL is deprecated, see [Werk 12345](https://checkmk.com/werk/12345) for more details.\n\n'

        >>> _build_description('Foo', 12345)
        '`WARNING`: This URL is deprecated, see [Werk 12345](https://checkmk.com/werk/12345) for more details.\n\nFoo'

    Args:
        description_text:
            The text of the description. This may be None.

        werk_id:
            A Werk ID for a deprecation warning. This may be None.

    Returns:
        Either a complete description or None

    """
    if werk_id:
        werk_link = f"https://checkmk.com/werk/{werk_id}"
        description = (
            f"`WARNING`: This URL is deprecated, see [Werk {werk_id}]({werk_link}) for more "
            "details.\n\n"
        )
    else:
        description = ""

    if description_text is not None:
        description += description_text

    return description


def _permission_descriptions(
    perms: permissions.BasePerm,
    descriptions: Mapping[str, str] | None = None,
) -> str:
    r"""Describe permissions human-readable

    Args:
        perms:
        descriptions:

    Examples:

        >>> _permission_descriptions(
        ...     permissions.Perm("wato.edit_folders"),
        ...     {'wato.edit_folders': 'Allowed to cook the books.'},
        ... )
        'This endpoint requires the following permissions: \n * `wato.edit_folders`: Allowed to cook the books.\n'

        >>> _permission_descriptions(
        ...     permissions.AllPerm([permissions.Perm("wato.edit_folders")]),
        ...     {'wato.edit_folders': 'Allowed to cook the books.'},
        ... )
        'This endpoint requires the following permissions: \n * `wato.edit_folders`: Allowed to cook the books.\n'

        >>> _permission_descriptions(
        ...     permissions.AllPerm([permissions.Perm("wato.edit_folders"),
        ...                          permissions.Undocumented(permissions.Perm("wato.edit"))]),
        ...     {'wato.edit_folders': 'Allowed to cook the books.'},
        ... )
        'This endpoint requires the following permissions: \n * `wato.edit_folders`: Allowed to cook the books.\n'

        >>> _permission_descriptions(
        ...     permissions.AnyPerm([permissions.Perm("wato.edit_folders"), permissions.Perm("wato.edit_folders")]),
        ...     {'wato.edit_folders': 'Allowed to cook the books.'},
        ... )
        'This endpoint requires the following permissions: \n * Any of:\n   * `wato.edit_folders`: Allowed to cook the books.\n   * `wato.edit_folders`: Allowed to cook the books.\n'

        The description will have a structure like this:

            * Any of:
               * c
               * All of:
                  * a
                  * b

        >>> _permission_descriptions(
        ...     permissions.AnyPerm([
        ...         permissions.Perm("c"),
        ...         permissions.AllPerm([
        ...              permissions.Perm("a"),
        ...              permissions.Perm("b"),
        ...         ]),
        ...     ]),
        ...     {'a': 'Hold a', 'b': 'Hold b', 'c': 'Hold c'}
        ... )
        'This endpoint requires the following permissions: \n * Any of:\n   * `c`: Hold c\n   * All of:\n     * `a`: Hold a\n     * `b`: Hold b\n'

    Returns:
        The description as a string.

    """
    description_map: Mapping[str, str] = descriptions if descriptions is not None else {}
    _description: list[str] = ["This endpoint requires the following permissions: "]

    def _count_perms(_perms):
        return len([p for p in _perms if not isinstance(p, permissions.Undocumented)])

    def _add_desc(permission: permissions.BasePerm, indent: int, desc_list: list[str]) -> None:
        if isinstance(permission, permissions.Undocumented):
            # Don't render
            return

        # We indent by two spaces, as is required by markdown.
        prefix = "  " * indent
        if isinstance(permission, permissions.Perm | permissions.OkayToIgnorePerm):
            perm_name = permission.name
            try:
                desc = description_map.get(perm_name) or permission_registry[perm_name].description
            except KeyError:
                if isinstance(permission, permissions.OkayToIgnorePerm):
                    return
                raise
            _description.append(f"{prefix} * `{perm_name}`: {desc}")
        elif isinstance(permission, permissions.AllPerm):
            # If AllOf only contains one permission, we don't need to show the AllOf
            if _count_perms(permission.perms) == 1:
                _add_desc(permission.perms[0], indent, desc_list)
            else:
                desc_list.append(f"{prefix} * All of:")
                for perm in permission.perms:
                    _add_desc(perm, indent + 1, desc_list)
        elif isinstance(permission, permissions.AnyPerm):
            # If AnyOf only contains one permission, we don't need to show the AnyOf
            if _count_perms(permission.perms) == 1:
                _add_desc(permission.perms[0], indent, desc_list)
            else:
                desc_list.append(f"{prefix} * Any of:")
                for perm in permission.perms:
                    _add_desc(perm, indent + 1, desc_list)
        elif isinstance(permission, permissions.Optional):
            desc_list.append(f"{prefix} * Optionally:")
            _add_desc(permission.perm, indent + 1, desc_list)
        else:
            raise NotImplementedError(f"Printing of {permission!r} not yet implemented.")

    _add_desc(perms, 0, _description)
    return "\n".join(_description) + "\n"


def _coalesce_schemas(
    parameters: Sequence[tuple[LocationType, Sequence[RawParameter]]],
) -> Sequence[SchemaParameter]:
    rv: list[SchemaParameter] = []
    for location, params in parameters:
        if not params:
            continue

        to_convert: dict[str, Field] = {}
        for param in params:
            if isinstance(param, SchemaMeta):
                rv.append({"in": location, "schema": param})
            else:
                to_convert.update(param)

        if to_convert:
            rv.append({"in": location, "schema": _to_named_schema(to_convert)})

    return rv


def _patch_regex(fields: dict[str, Field]) -> dict[str, Field]:
    for _, value in fields.items():
        if "pattern" in value.metadata and value.metadata["pattern"].endswith(r"\Z"):
            value.metadata["pattern"] = value.metadata["pattern"][:-2] + "$"
    return fields


def _to_named_schema(fields_: dict[str, Field]) -> type[Schema]:
    attrs: dict[str, Any] = _patch_regex(fields_.copy())
    attrs["Meta"] = type(
        "GeneratedMeta",
        (Schema.Meta,),
        {"register": True},
    )
    _hash = hashlib.sha256()

    def _update(d_):
        for key, value in sorted(d_.items()):
            _hash.update(str(key).encode("utf-8"))
            if hasattr(value, "metadata"):
                _update(value.metadata)
            else:
                _hash.update(str(value).encode("utf-8"))

    _update(fields_)

    name = f"GeneratedSchema{_hash.hexdigest()}"
    schema_cls: type[Schema] = type(name, (Schema,), attrs)
    return schema_cls


def _docstring_description(docstring: str | None) -> str | None:
    """Split the docstring by title and rest.

    This is part of the rest.

    >>> _docstring_description(_docstring_description.__doc__).split("\\n")[0]
    'This is part of the rest.'

    Args:
        docstring:

    Returns:
        A string or nothing.

    """
    if not docstring:
        return None
    parts = dedent(docstring).split("\n\n", 1)
    if len(parts) > 1:
        return parts[1].strip()
    return None


def _docstring_name(docstring: str | None) -> str:
    """Split the docstring by title and rest.

    This is part of the rest.

    >>> _docstring_name(_docstring_name.__doc__)
    'Split the docstring by title and rest.'

    >>> _docstring_name("")
    Traceback (most recent call last):
    ...
    ValueError: No name for the module defined. Please add a docstring!

    Args:
        docstring:

    Returns:
        A string or nothing.

    """
    if not docstring:
        raise ValueError("No name for the module defined. Please add a docstring!")

    return [part.strip() for part in dedent(docstring).split("\n\n", 1)][0]


def _add_once(coll: list[dict[str, Any]], to_add: dict[str, Any]) -> None:
    """Add an entry to a collection, only once.

    Examples:

        >>> l = []
        >>> _add_once(l, {'foo': []})
        >>> l
        [{'foo': []}]

        >>> _add_once(l, {'foo': []})
        >>> l
        [{'foo': []}]

    Args:
        coll:
        to_add:

    Returns:

    """
    if to_add in coll:
        return None

    coll.append(to_add)
    return None
