#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

"""Helper function for dataclass field metadata.

The `api_field` function is a wrapper around the `dataclasses.field` function, with the goal to
improve the dev experience when creating API related schemas."""

from collections.abc import Callable, Mapping, MutableMapping
from dataclasses import field, MISSING
from typing import Any, overload

from cmk.gui.openapi.framework.model.omitted import ApiOmitted

_NOT_SET = object()


# `default` and `default_factory` are optional and mutually exclusive (just like dataclasses.field)
@overload
def api_field[T](
    *,
    description: str,
    default: T,
    serialization_alias: str | None = None,
    title: str | None = None,
    example: object | None = None,
    pattern: str | None = None,
    discriminator: str | None = None,
    deprecated: bool = False,
    init: bool = True,
    repr: bool = True,
    hash: bool | None = None,
    compare: bool = True,
    kw_only: bool | None = None,
    additional_metadata: Mapping[str, object] | None = None,
) -> T: ...


@overload
def api_field[T](
    *,
    description: str,
    default_factory: Callable[[], T],
    serialization_alias: str | None = None,
    title: str | None = None,
    example: object | None = None,
    pattern: str | None = None,
    discriminator: str | None = None,
    deprecated: bool = False,
    init: bool = True,
    repr: bool = True,
    hash: bool | None = None,
    compare: bool = True,
    kw_only: bool | None = None,
    additional_metadata: Mapping[str, object] | None = None,
) -> T: ...


@overload
def api_field(
    *,
    description: str,
    default_factory: type[ApiOmitted] | None = None,
    serialization_alias: str | None = None,
    title: str | None = None,
    example: object | None = None,
    pattern: str | None = None,
    discriminator: str | None = None,
    deprecated: bool = False,
    init: bool = True,
    repr: bool = True,
    hash: bool | None = None,
    compare: bool = True,
    kw_only: bool | None = None,
    additional_metadata: Mapping[str, object] | None = None,
) -> Any: ...  # unfortunately, this is the best we can do here, see comment below


def api_field(
    *,
    description: str,
    default: object = _NOT_SET,
    default_factory: Callable[[], object] | type[ApiOmitted] | None = None,
    serialization_alias: str | None = None,
    title: str | None = None,
    example: object | None = None,
    pattern: str | None = None,
    discriminator: str | None = None,
    deprecated: bool = False,
    init: bool = True,
    repr: bool = True,
    hash: bool | None = None,
    compare: bool = True,
    kw_only: bool | None = None,
    additional_metadata: Mapping[str, object] | None = None,
    # the actual return type is dataclasses.Field[T], but just like dataclasses.field we're lying
    # (by claiming it's T/Any) to make type checkers happier
) -> Any:
    """
    Wrapper around `dataclasses.field` to add OpenAPI specific metadata.

    Args:
        description: Description of the field, used for OpenAPI schema generation.
        default: Set a default value for the field. Mutually exclusive with `default_factory`.
        default_factory: Set a default value for the field using a callable.
                         Mutually exclusive with `default`.
        serialization_alias: Alias for the field, will be used instead of the field name for
                             (de-)serialization.
        title: Title of the field, used for OpenAPI schema generation.
        example: Serialized example value of the field, used for OpenAPI schema generation.
        pattern: Regular expression pattern for the field, used for OpenAPI schema generation
                 and validation.
        discriminator: Discriminator for tagged unions, improves error responses.
        deprecated: If True, the field is marked as deprecated in the OpenAPI schema.
        init: Include the field in the generated __init__ method.
        repr: Include the field in the generated __repr__ method.
        hash: Include the field in the generated __hash__ method. If None, use the compare behavior.
        compare: Include the field in the generated comparison methods.
        kw_only: Include the field as a keyword-only argument in the generated __init__ method.
        additional_metadata: Additional metadata to include in the field.
    """
    metadata: MutableMapping[str, object] = {
        "description": description,
    }
    if serialization_alias:
        metadata["alias"] = serialization_alias
    if title:
        metadata["title"] = title
    if example:
        metadata["examples"] = [example]
    if pattern:
        metadata["pattern"] = pattern
    if discriminator:
        metadata["discriminator"] = discriminator
    if deprecated:
        metadata["deprecated"] = True
    if additional_metadata:
        metadata.update(additional_metadata)

    # Defaulting to true or false would be wrong here, as the default should be to use the
    # configuration from the class, which is why we must use MISSING.
    kw_only_value = MISSING if kw_only is None else kw_only

    # NOTE 1: From https://docs.python.org/3/library/dataclasses.html#dataclasses.Field:
    # "Users should never instantiate a Field object directly." => Only use `fields()`

    # NOTE 2: `default` and `default_factory` are optional and mutually exclusive, and the typing of
    # `fields()` models this via overloads. As a consequence, we'll have to follow that pattern
    # below to avoid ugly & fragile typing suppressions. That's the price one has to pay when trying
    # to wrap an overloaded function within another overloaded function...
    if default is _NOT_SET and default_factory is None:
        return field(
            default=MISSING,
            default_factory=MISSING,
            init=init,
            repr=repr,
            hash=hash,
            compare=compare,
            kw_only=kw_only_value,
            metadata=metadata,
        )
    if default is _NOT_SET and default_factory is not None:
        return field(
            default=MISSING,
            default_factory=default_factory,
            init=init,
            repr=repr,
            hash=hash,
            compare=compare,
            kw_only=kw_only_value,
            metadata=metadata,
        )
    if default is not _NOT_SET and default_factory is None:
        return field(
            default=default,
            default_factory=MISSING,
            init=init,
            repr=repr,
            hash=hash,
            compare=compare,
            kw_only=kw_only_value,
            metadata=metadata,
        )
    raise ValueError("cannot specify both default and default_factory")
