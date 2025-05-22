#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum
from collections.abc import Callable, Mapping, Sequence

from apispec import APISpec
from apispec.utils import dedent
from werkzeug.utils import import_string

from cmk.ccc.version import Edition

from cmk.gui.openapi import endpoint_family_registry
from cmk.gui.openapi.restful_objects.type_defs import (
    EditionLabel,
    OpenAPITag,
    TagGroup,
)
from cmk.gui.permissions import permission_registry
from cmk.gui.utils import permission_verification as permissions


class DefaultStatusCodeDescription(enum.Enum):
    Code406 = "The requests accept headers can not be satisfied."
    Code401 = "The user is not authorized to do this request."
    Code403 = "Configuration via Setup is disabled."
    Code404 = "The requested object has not be found."
    Code422 = "The request could not be processed."
    Code423 = "The resource is currently locked."
    Code405 = "Method not allowed: This request is only allowed with other HTTP methods."
    Code409 = "The request is in conflict with the stored resource."
    Code415 = "The submitted content-type is not supported."
    Code302 = (
        "Either the resource has moved or has not yet completed. "
        "Please see this resource for further information."
    )
    Code400 = "Parameter or validation failure."
    Code412 = "The value of the If-Match header doesn't match the object's ETag."
    Code428 = "The required If-Match header is missing."
    Code200 = "The operation was done successfully."
    Code204 = "Operation done successfully. No further output."


def format_endpoint_supported_editions(editions: set[Edition]) -> Sequence[EditionLabel]:
    colors: Mapping[Edition, str] = {
        Edition.CEE: "#74ebdd",
        Edition.CRE: "#afb9c2",
        Edition.CCE: "#586aa2",
        Edition.CSE: "#7e96f3",
        Edition.CME: "#70a8db",
    }
    ordered_editions = (Edition.CRE, Edition.CEE, Edition.CCE, Edition.CME, Edition.CSE)
    edition_labels: list[EditionLabel] = []
    for edition in ordered_editions:
        if edition in editions:
            edition_labels.append(
                {
                    "name": edition.short.upper(),
                    "position": "after",
                    "color": colors[edition],
                }
            )
    return edition_labels


def endpoint_title_and_description_from_docstring(
    endpoint_func: Callable, operation_id: str
) -> tuple[str, str | None]:
    module_obj = import_string(endpoint_func.__module__)

    try:
        docstring_name = _docstring_name(endpoint_func.__doc__)
    except ValueError as exc:
        raise ValueError(
            f"Function {module_obj.__name__}:{endpoint_func.__name__} has no docstring."
        ) from exc

    if not docstring_name:
        raise RuntimeError(f"Please put a docstring onto {operation_id}")

    docstring_description = _docstring_description(endpoint_func.__doc__)
    return docstring_name, docstring_description


def build_spec_description(
    endpoint_description: str | None,
    werk_id: int | None,
    permissions_required: permissions.BasePerm | None,
    permissions_description: Mapping[str, str] | None,
) -> str:
    # The validator will complain on empty descriptions being set, even though it's valid.
    spec_description = _build_description(endpoint_description, werk_id)

    if permissions_required is not None:
        # Check that all the names are known to the system.
        for perm in permissions_required.iter_perms():
            if isinstance(perm, permissions.OkayToIgnorePerm):
                continue

            if perm.name not in permission_registry:
                # NOTE:
                #   See rest_api.py. dynamic_permission() have to be loaded before request
                #   for this to work reliably.
                raise RuntimeError(
                    f'Permission "{perm}" is not registered in the permission_registry.'
                )

        # Write permission documentation in openapi spec.
        if permissions_spec_description := _permission_descriptions(
            permissions_required, permissions_description
        ):
            if not spec_description:
                spec_description += "\n\n"
            spec_description += permissions_spec_description

    return spec_description


def build_tag_obj_from_family(family_name: str) -> OpenAPITag:
    """Build a tag object from the endpoint family definition"""
    family = endpoint_family_registry.get(family_name)
    if family is None:
        raise ValueError(f"Family {family_name} not found in registry")

    return family.to_openapi_tag()


def add_tag(spec: APISpec, tag: OpenAPITag, tag_group: TagGroup | None = None) -> None:
    name = tag["name"]
    if name in [t["name"] for t in spec._tags]:
        return

    spec.tag(dict(tag))
    if tag_group is not None:
        _assign_to_tag_group(spec, tag_group, name)


def _assign_to_tag_group(spec: APISpec, tag_group: TagGroup, name: str) -> None:
    for group in spec.options.setdefault("x-tagGroups", []):
        if group["name"] == tag_group:
            group["tags"].append(name)
            break
    else:
        raise ValueError(f"x-tagGroup {tag_group} not found. Please add it to specification.py")


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
        'This endpoint requires the following permissions: \n * Modify existing folders (`wato.edit_folders`): Allowed to cook the books.\n'

        >>> _permission_descriptions(
        ...     permissions.AllPerm([permissions.Perm("wato.edit_folders")]),
        ...     {'wato.edit_folders': 'Allowed to cook the books.'},
        ... )
        'This endpoint requires the following permissions: \n * Modify existing folders (`wato.edit_folders`): Allowed to cook the books.\n'

        >>> _permission_descriptions(
        ...     permissions.AllPerm([permissions.Perm("wato.edit_folders"),
        ...                          permissions.Undocumented(permissions.Perm("wato.edit"))]),
        ...     {'wato.edit_folders': 'Allowed to cook the books.'},
        ... )
        'This endpoint requires the following permissions: \n * Modify existing folders (`wato.edit_folders`): Allowed to cook the books.\n'

        >>> _permission_descriptions(
        ...     permissions.AnyPerm([permissions.Perm("wato.edit_folders"), permissions.Perm("wato.edit_folders")]),
        ...     {'wato.edit_folders': 'Allowed to cook the books.'},
        ... )
        'This endpoint requires the following permissions: \n * Any of:\n   * Modify existing folders (`wato.edit_folders`): Allowed to cook the books.\n   * Modify existing folders (`wato.edit_folders`): Allowed to cook the books.\n'

        The description will have a structure like this:

            * Any of:
               * a
               * All of:
                  * b
                  * c

        >>> _permission_descriptions(
        ...     permissions.AnyPerm([
        ...         permissions.Perm("wato.edit"),
        ...         permissions.AllPerm([
        ...              permissions.Perm("wato.manage_hosts"),
        ...              permissions.Perm("wato.edit_folders"),
        ...         ]),
        ...     ]),
        ...     {'wato.edit': 'a', 'wato.manage_hosts': 'b', 'wato.edit_folders':  'c'}
        ... )
        'This endpoint requires the following permissions: \n * Any of:\n   * Make changes, perform actions (`wato.edit`): a\n   * All of:\n     * Add & remove hosts (`wato.manage_hosts`): b\n     * Modify existing folders (`wato.edit_folders`): c\n'

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
                display_name = permission_registry[perm_name].title
                desc = description_map.get(perm_name) or permission_registry[perm_name].description
            except KeyError:
                if isinstance(permission, permissions.OkayToIgnorePerm):
                    return
                raise
            _description.append(f"{prefix} * {display_name} (`{perm_name}`): {desc}")
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
