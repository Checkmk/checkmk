#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


"""This module provides hooks for converting ValueSpec trees into marshmallow fields.

These hooks are used in the function `valuespec_to_marshmallow` to convert each node of a tree of
ValueSpec instances into a marshmallow field. Each hook is responsible for calling
`valuespec_to_marshmallow` on the sub-nodes of it's matched ValueSpec instance.

To define a hook for a specific ValueSpec subclass, decorate a function with
`@match_on(valuespec.ValueSpecClassName)`. This function will then be used to convert instances of
`ValueSpecClassName` into marshmallow fields.

Example:

    @match_on(valuespec.Integer)
    def valuespec_integer(valuespec_instance: valuespec.Integer) -> fields.Integer:
        # ... code to convert the ValueSpec instance to a FormElement ...

Note:
    Ensure the hooks are appropriately registered for each ValueSpec subclass for correct
    conversion.

Module Attributes:
    match_on: Decorator used to register conversion functions for specific ValueSpec subclasses.
"""

import typing
from typing import cast

from marshmallow import ValidationError
from marshmallow.validate import Validator

from cmk.utils.tags import AuxTag, TagGroup

from cmk.gui import fields as gui_fields
from cmk.gui import valuespec
from cmk.gui.fields.base import BaseSchema
from cmk.gui.openapi.endpoints.global_settings.schemas import (
    CAInputSchema,
    FileUploadSchema,
    GlobalSettingsOneOfSchema,
    IconSchema,
    TagOneOfBaseSchema,
)
from cmk.gui.openapi.marshmallow_converter.internal_to_marshmallow import (
    cleanup_default_value,
    get_default_value,
    get_oneof_default_values,
)
from cmk.gui.openapi.marshmallow_converter.type_defs import (
    BaseOrOneOfSchemaType,
    maybe_lazy,
    V_c,
    ValuespecToSchemaMatchDict,
    ValuespecToSchemaMatchEntry,
    ValuespecToSchemaTransformFunction,
)
from cmk.gui.userdb._user_selection import _UserSelection
from cmk.gui.valuespec.definitions import _CAInput
from cmk.gui.wato import DictHostTagCondition, FullPathFolderChoice
from cmk.gui.wato._group_selection import _GroupSelection
from cmk.gui.watolib.sites import LivestatusViaTCP
from cmk.gui.watolib.tags import load_all_tag_config_read_only

from cmk import fields

MATCHERS: ValuespecToSchemaMatchDict[valuespec.ValueSpec] = {}
PRECALCULATED_SCHEMAS: dict[str, BaseOrOneOfSchemaType] = {}


def match_on(
    vs_type: type[V_c] | type[None],
    has_name: bool = True,
) -> typing.Callable[[ValuespecToSchemaTransformFunction], ValuespecToSchemaTransformFunction]:
    """Register a transform function based on value type.

    Acts as a decorator to register a transform function (`TransformFunction`) in
    a global matcher dictionary (`matchers`). The function associates the given
    `vs_type` with the provided transform function.

    Args:
        vs_type: Type of value to match on. Can be either a custom type `V_c` or `None`.
        has_name (bool, optional): Whether the value should have a name attribute.
            Defaults to True.

    Returns:
        Callable[[TransformFunction], TransformFunction]: A decorator that takes a
        transform function and returns it, after registering it in the global
        `matchers` dictionary.

    Example:
        @match_on(int)
        def transform_int(value):
            ...  # do stuff here

    """

    def register_func(
        func: ValuespecToSchemaTransformFunction,
    ) -> ValuespecToSchemaTransformFunction:
        if MATCHERS.get(vs_type):
            raise ValueError(f"Match function for {vs_type} already registered.")
        MATCHERS[vs_type] = ValuespecToSchemaMatchEntry(match_func=func, has_name=has_name)
        return func

    return register_func


def get_validator(vs_instance: valuespec.ValueSpec | None) -> fields.ValidateAnyOfValidators:
    if vs_instance is None:
        return fields.ValidateAnyOfValidators([])

    class VSValidator(Validator):
        def __call__(self, value: typing.Any) -> bool:
            try:
                if vs_instance is None:
                    return True
                vs_instance.validate_datatype(value, varprefix="")
                vs_instance.validate_value(value, varprefix="")
                return True
            except ValueError as exc:
                raise ValidationError(str(exc))

    return fields.ValidateAnyOfValidators([VSValidator()])


def get_schema_from_tuple_elements(
    elements: typing.Sequence[valuespec.ValueSpec],
    name: str | None,
) -> BaseOrOneOfSchemaType:
    return get_schema_from_precalculated_schemas(
        BaseSchema,
        {
            f"tuple_entry_{str(id_)}": valuespec_to_marshmallow(
                vs_instance,
                name=f"{name}_tuple_entry_{id_}",
                required=True,
            )
            for id_, vs_instance in enumerate(elements)
        },
        f"ValuespecSchema_{name}_tuple",
    )


def get_schema_from_dict_elements(
    elements: typing.Iterable[tuple[str, valuespec.ValueSpec]],
    name: str | None,
    optional_keys: bool,
    required_keys: typing.Sequence[str],
) -> BaseOrOneOfSchemaType:
    return get_schema_from_precalculated_schemas(
        BaseSchema,
        {
            str(id_): valuespec_to_marshmallow(
                vs_instance=vs_instance,
                name=f"{name}_dict_{id_}",
                required=False if optional_keys else id_ in required_keys,
            )
            for id_, vs_instance in elements
        },
        f"ValuespecSchema_{name}_dict",
    )


def get_oneof_schema_from_elements(
    elements: typing.Iterable[tuple[str, valuespec.ValueSpec]],
    name: str | None,
) -> BaseOrOneOfSchemaType:
    class GeneratedIDsSchema(BaseSchema):
        type = fields.String(
            enum=[id_ for id_, _vs_instance in elements],
            required=True,
        )

    class GeneratedOneOfSchema(GlobalSettingsOneOfSchema):
        type_schemas = {
            str(id_): get_schema_from_precalculated_schemas(
                GeneratedIDsSchema,
                {
                    "value": valuespec_to_marshmallow(
                        vs_instance, name=f"{name}_oneofoption_{id_}", required=False
                    )
                },
                f"ValuespecSchema_{name}_oneofoption_{id_}",
            )
            for id_, vs_instance in elements
        }

    return get_schema_from_precalculated_schemas(
        GeneratedOneOfSchema, {}, f"ValuespecSchema_{name}_oneof"
    )


def get_schema_from_choices(
    list_choices_: list[tuple[str, str]],
    name: str | None,
) -> BaseOrOneOfSchemaType:
    return get_schema_from_precalculated_schemas(
        BaseSchema,
        {
            str(id_): fields.Boolean(
                description=description or "",
                required=False,
            )
            for id_, description in list_choices_
        },
        f"ValuespecSchema_{name}_choices",
    )


@match_on(valuespec.Integer)
@match_on(valuespec.Filesize)
def valuespec_integer(
    vs_instance: valuespec.Integer,
    name: str | None,
    required: bool = False,
) -> fields.Integer:
    params = get_default_params(required, vs_instance.allow_empty(), get_default_value(vs_instance))
    if (maximum := vs_instance._bounds._upper) is not None:
        params["maximum"] = maximum
    if (minimum := vs_instance._bounds._lower) is not None:
        params["minimum"] = minimum
    return fields.Integer(
        description=get_help(vs_instance),
        validate=get_validator(vs_instance),
        **params,
    )


@match_on(valuespec.Percentage)
@match_on(valuespec.Float)
def valuespec_float(
    vs_instance: valuespec.Float,
    name: str | None,
    required: bool = False,
) -> fields.Float:
    params = get_default_params(required, vs_instance.allow_empty(), get_default_value(vs_instance))
    if (maximum := vs_instance._bounds._upper) is not None:
        params["maximum"] = maximum
    if (minimum := vs_instance._bounds._lower) is not None:
        params["minimum"] = minimum
    return fields.Float(
        description=get_help(vs_instance),
        validate=get_validator(vs_instance),
        **params,
    )


@match_on(valuespec.IconSelector)
def valuespec_icon_selector(
    vs_instance: valuespec.IconSelector,
    name: str | None,
    required: bool = False,
) -> fields.Nested:
    params = get_default_params(required, vs_instance.allow_empty(), get_default_value(vs_instance))
    return fields.Nested(
        IconSchema,
        description=get_help(vs_instance),
        validate=get_validator(vs_instance),
        **params,
    )


@match_on(valuespec.RegExp)
@match_on(valuespec.TextAreaUnicode)
@match_on(valuespec.EmailAddress)
@match_on(valuespec.Password)
@match_on(valuespec.HostAddress)
@match_on(valuespec.TextInput)
def valuespec_text_input(
    vs_instance: valuespec.TextInput,
    name: str | None,
    required: bool = False,
) -> fields.String:
    params = get_default_params(required, vs_instance.allow_empty(), get_default_value(vs_instance))
    if (maxLength := vs_instance._maxlen) is not None:
        params["maxLength"] = maxLength
    if (minLength := vs_instance._minlen) is not None:
        params["minLength"] = minLength
    return fields.String(
        description=get_help(vs_instance),
        validate=get_validator(vs_instance),
        **params,
    )


@match_on(valuespec.FixedValue)
def valuespec_fixed_value(
    vs_instance: valuespec.FixedValue,
    name: str | None,
    required: bool = False,
) -> fields.Constant:
    params = get_default_params(required, vs_instance.allow_empty(), get_default_value(vs_instance))
    return fields.Constant(
        vs_instance._value,
        description=get_help(vs_instance),
        validate=get_validator(vs_instance),
        **params,
    )


@match_on(valuespec.AbsoluteDate)
@match_on(valuespec.Age)
def valuespec_age(
    vs_instance: valuespec.Age,
    name: str | None,
    required: bool = False,
) -> gui_fields.Timestamp:
    params = get_default_params(required, vs_instance.allow_empty(), get_default_value(vs_instance))
    return gui_fields.Timestamp(
        format="iso8601",
        description=get_help(vs_instance),
        validate=get_validator(vs_instance),
        **params,
    )


@match_on(valuespec.Tuple)
def valuespec_tuple(
    vs_instance: valuespec.Tuple,
    name: str | None,
    required: bool = False,
) -> fields.Nested:
    params = get_default_params(required, vs_instance.allow_empty(), get_default_value(vs_instance))
    return fields.Nested(
        get_schema_from_tuple_elements(vs_instance._elements, name),
        description=get_help(vs_instance),
        validate=get_validator(vs_instance),
        **params,
    )


@match_on(valuespec.Checkbox)
def valuespec_checkbox(
    vs_instance: valuespec.Checkbox,
    name: str | None,
    required: bool = False,
) -> fields.Boolean:
    params = get_default_params(required, vs_instance.allow_empty(), get_default_value(vs_instance))
    return fields.Boolean(
        description=get_help(vs_instance),
        validate=get_validator(vs_instance),
        **params,
    )


@match_on(valuespec.Url)
def valuespec_url(
    vs_instance: valuespec.TextInput,
    name: str | None,
    required: bool = False,
) -> fields.URL:
    params = get_default_params(required, vs_instance.allow_empty(), get_default_value(vs_instance))
    if (maxLength := vs_instance._maxlen) is not None:
        params["maxLength"] = maxLength
    if (minLength := vs_instance._minlen) is not None:
        params["minLength"] = minLength
    return fields.URL(
        description=get_help(vs_instance),
        validate=get_validator(vs_instance),
        **params,
    )


@match_on(valuespec.Optional)
def valuespec_optional(
    vs_instance: valuespec.Optional,
    name: str | None,
    required: bool = False,
) -> fields.Field:
    return valuespec_to_marshmallow(vs_instance._valuespec, name=f"{name}_optional", required=False)


@match_on(LivestatusViaTCP)
@match_on(valuespec.Dictionary)
def valuespec_dictionary(
    vs_instance: valuespec.Dictionary,
    name: str | None,
    required: bool = False,
) -> fields.Nested:
    params = get_default_params(required, vs_instance.allow_empty(), get_default_value(vs_instance))
    optional_keys = vs_instance._optional_keys
    required_keys = vs_instance._required_keys
    return fields.Nested(
        get_schema_from_dict_elements(
            maybe_lazy(vs_instance._elements),
            name=name,
            optional_keys=optional_keys in (False, []),
            required_keys=required_keys,
        ),
        description=get_help(vs_instance),
        validate=get_validator(vs_instance),
        **params,
    )


@match_on(valuespec.DualListChoice)
@match_on(valuespec.ListChoice)
def valuespec_listchoice(
    vs_instance: valuespec.ListChoice,
    name: str | None,
    required: bool = False,
) -> fields.Nested:
    params = get_default_params(required, vs_instance.allow_empty(), get_default_value(vs_instance))
    choices = list_choices(vs_instance._choices)
    return fields.Nested(
        get_schema_from_choices(choices, name),
        description=get_help(vs_instance),
        validate=get_validator(vs_instance),
        **params,
    )


@match_on(valuespec.ListOfStrings)
def valuespec_list_of_strings(
    vs_instance: valuespec.ListOfStrings,
    name: str | None,
    required: bool = False,
) -> fields.List:
    params = get_default_params(required, vs_instance.allow_empty(), get_default_value(vs_instance))
    return fields.List(
        fields.String(),
        description=get_help(vs_instance),
        validate=get_validator(vs_instance),
        **params,
    )


@match_on(valuespec.ListOf)
def valuespec_list_of(
    vs_instance: valuespec.ListOf,
    name: str | None,
    required: bool = False,
) -> fields.List:
    params = get_default_params(required, vs_instance.allow_empty(), get_default_value(vs_instance))
    return fields.List(
        valuespec_to_marshmallow(
            vs_instance=vs_instance._valuespec, name=f"{name}_listof", required=False
        ),
        description=get_help(vs_instance),
        validate=get_validator(vs_instance),
        **params,
    )


@match_on(valuespec.Timerange)
@match_on(valuespec.CascadingDropdown)
def valuespec_cascading_dropdown(
    vs_instance: valuespec.CascadingDropdown,
    name: str | None,
    required: bool = False,
) -> fields.Nested:
    elements = [
        (str(id_), vs_instance) for id_, _title, vs_instance in vs_instance.choices() if vs_instance
    ]
    params = get_default_params(
        required, vs_instance.allow_empty(), get_oneof_default_values(elements[0])
    )
    return fields.Nested(
        get_oneof_schema_from_elements(elements, name),
        description=get_help(vs_instance),
        validate=get_validator(vs_instance),
        **params,
    )


@match_on(valuespec.Foldable)
@match_on(valuespec.MigrateNotUpdated)
@match_on(valuespec.Migrate)
@match_on(valuespec.Transform)
def valuespec_transform(
    vs_instance: valuespec.Transform,
    name: str | None,
    required: bool = False,
) -> fields.Field:
    return valuespec_to_marshmallow(
        vs_instance._valuespec, name=f"{name}_transform", required=required
    )


@match_on(type(None))
def valuespec_none(
    vs_instance: None,
    name: str | None,
    required: bool = False,
) -> fields.Constant:
    return fields.Constant(None)


@match_on(valuespec._CAorCAChain)
@match_on(valuespec.Alternative)
def valuespec_alternative(
    vs_instance: valuespec.Alternative,
    name: str | None,
    required: bool = False,
) -> fields.Nested:
    elements = [
        (f"alternative_option_{str(id_)}", vs_instance)
        for id_, vs_instance in enumerate(vs_instance._elements)
    ]
    params = get_default_params(
        required, vs_instance.allow_empty(), get_oneof_default_values(elements[0])
    )
    return fields.Nested(
        get_oneof_schema_from_elements(elements, name),
        description=get_help(vs_instance),
        validate=get_validator(vs_instance),
        **params,
    )


@match_on(_CAInput)
def valuespec_ca_input(
    vs_instance: _CAInput,
    name: str | None,
    required: bool = False,
) -> fields.Nested:
    params = get_default_params(required, vs_instance.allow_empty(), get_default_value(vs_instance))
    return fields.Nested(
        CAInputSchema,
        description=get_help(vs_instance),
        validate=get_validator(vs_instance),
        **params,
    )


@match_on(valuespec.FileUpload)
def valuespec_file_upload(
    vs_instance: valuespec.FileUpload,
    name: str | None,
    required: bool = False,
) -> fields.Nested:
    params = get_default_params(required, vs_instance.allow_empty(), get_default_value(vs_instance))
    return fields.Nested(
        FileUploadSchema,
        description=get_help(vs_instance),
        validate=get_validator(vs_instance),
        **params,
    )


@match_on(valuespec.OptionalDropdownChoice)
@match_on(valuespec.DropdownChoice)
@match_on(_GroupSelection)
@match_on(_UserSelection)
@match_on(FullPathFolderChoice)
def valuespec_dropdown_choice(
    vs_instance: valuespec.DropdownChoice,
    name: str | None,
    required: bool = False,
) -> fields.String | fields.Constant:
    params = get_default_params(required, vs_instance.allow_empty(), get_default_value(vs_instance))
    choices = list_choices(vs_instance._choices)
    if len(choices) == 0:
        return fields.Constant("No options available")
    description = (
        "Dropdown choice options:"
        "<ul>"
        f"{''.join([f'<li>{choice[0]}: {choice[1]}</li>' for choice in choices])}"
        "</ul>"
    )
    return fields.String(
        enum=[choice[0] for choice in choices],
        description=get_help(vs_instance) + description,
        validate=get_validator(vs_instance),
        **params,
    )


def get_tag_one_of_schema(
    tag_group_or_aux_tag: TagGroup | AuxTag, name: str | None
) -> BaseOrOneOfSchemaType:
    help_text = ""
    tag_ids = []
    if isinstance(tag_group_or_aux_tag, TagGroup):
        help_text = (
            "Available tags:"
            "<ul>"
            f"{''.join([f'<li>{tag.id}: {tag.title}</li>' for tag in tag_group_or_aux_tag.tags])}"
            "</ul>"
        )
        tag_ids = [tag.id for tag in tag_group_or_aux_tag.tags]

    class TagOneOfSchema(GlobalSettingsOneOfSchema):
        type_schemas = {
            "is": get_schema_from_precalculated_schemas(
                TagOneOfBaseSchema,
                {
                    "value": (
                        fields.String(
                            enum=tag_ids,
                            description=f"Include selected tag.<br>{help_text}",
                            required=True,
                        )
                        if isinstance(tag_group_or_aux_tag, TagGroup)
                        else fields.Constant("set")
                    )
                },
                f"ValuespecSchema_{name}_tag_is_{tag_group_or_aux_tag.id}",
            ),
            "isnot": get_schema_from_precalculated_schemas(
                TagOneOfBaseSchema,
                {
                    "value": (
                        fields.String(
                            enum=tag_ids,
                            description=f"Exclude selected tag. <br>{help_text}",
                            required=True,
                        )
                        if isinstance(tag_group_or_aux_tag, TagGroup)
                        else fields.Constant("set")
                    )
                },
                f"ValuespecSchema_{name}_tag_isnot_{tag_group_or_aux_tag.id}",
            ),
            "ignore": TagOneOfBaseSchema,
        }

    return get_schema_from_precalculated_schemas(
        TagOneOfSchema,
        {},
        f"ValuespecSchema_{name}_tag_oneof_{tag_group_or_aux_tag.id}",
    )


def get_host_tag_schema(name: str | None) -> BaseOrOneOfSchemaType:
    tag_config = load_all_tag_config_read_only()
    tag_groups_by_topic = tag_config.get_tag_groups_by_topic()
    aux_tags_by_topic = tag_config.get_aux_tags_by_topic()
    per_topic: dict[str, list[TagGroup | AuxTag]] = {}
    for topic, tag_groups in tag_groups_by_topic:
        per_topic.setdefault(topic, []).extend(tag_groups)
    for topic, aux_tags in aux_tags_by_topic:
        per_topic.setdefault(topic, []).extend(aux_tags)
    all_tags_by_topic = sorted(per_topic.items(), key=lambda x: x[0])

    return get_schema_from_precalculated_schemas(
        BaseSchema,
        {
            topic: fields.Nested(
                BaseSchema.from_dict(
                    {
                        tag_group_or_aux_tag.id: fields.Nested(
                            get_tag_one_of_schema(tag_group_or_aux_tag, name),
                            description=tag_group_or_aux_tag.title,
                        )
                        for tag_group_or_aux_tag in tag_groups_or_aux_tags
                    },
                    name=f"ValuespecSchema_{name}_host_tag_{topic}",
                )
            )
            for topic, tag_groups_or_aux_tags in all_tags_by_topic
        },
        f"ValuespecSchema_{name}_host_tags_by_topic",
    )


@match_on(DictHostTagCondition)
def valuespec_host_tag_condition(
    vs_instance: DictHostTagCondition,
    name: str | None,
    required: bool = False,
) -> fields.Nested:
    params = get_default_params(required, vs_instance.allow_empty(), get_default_value(vs_instance))
    return fields.Nested(
        get_host_tag_schema(name),
        description=get_help(vs_instance),
        validate=get_validator(vs_instance),
        **params,
    )


@match_on(valuespec.Labels)
def valuespec_labels(
    vs_instance: valuespec.Labels,
    name: str | None,
    required: bool = False,
) -> fields.List:
    params = get_default_params(required, vs_instance.allow_empty(), get_default_value(vs_instance))
    return fields.List(
        fields.String(),
        description=get_help(vs_instance),
        validate=get_validator(vs_instance),
        **params,
    )


def list_choices(choices: valuespec.ListChoiceChoices) -> list[tuple[str, str]]:
    """Generate a list of tuples representing choices.

    Accepts a mapping, callable, or list of tuples as input. If the input is a
    callable, it calls the function to obtain the list of choices. Converts the keys
    to strings in the resulting list of tuples.

    Args:
        choices (valuespec.ListChoiceChoices): The choices to process. Can be a mapping,
            a callable that returns a list of tuples, or a list of tuples.

    Examples:
        >>> list_choices({'a': 'Apple', 'b': 'Banana'})
        [('a', 'Apple'), ('b', 'Banana')]

        >>> list_choices({'a': 'Apple', 'b': 'Banana'})
        [('a', 'Apple'), ('b', 'Banana')]

        >>> list_choices(lambda: {'a': 'Apple', 'b': 'Banana'})
        [('a', 'Apple'), ('b', 'Banana')]

        >>> list_choices(lambda: [('a', 'Apple'), ('b', 'Banana')])
        [('a', 'Apple'), ('b', 'Banana')]

    Returns:
        list[tuple[str, str]]: A list of tuples where each tuple contains two strings.
        Returns an empty list if `_choices` is None.

    """
    if choices is None:
        return []

    if callable(choices):
        choices = choices()

    if isinstance(choices, typing.Mapping):
        return [(str(cleanup_default_value(key)), value) for key, value in choices.items()]

    return [(str(cleanup_default_value(key)), value) for key, value in choices]


def get_schema_from_precalculated_schemas(
    schema_cls: BaseOrOneOfSchemaType, schema_fields: dict[str, typing.Any], schema_name: str
) -> BaseOrOneOfSchemaType:
    """
    Get a schema from the precalculated schemas or create a new one.
    This is required because the schemas are created dynamically and need to be cached
    to avoid creating the same schema multiple times.

    Since the `from_dict` function returns a new type that inherits from the class from
    which it was called but the return type hint is `type[Schema]` it is necessary to set
    the type accordingly.
    """
    if (schema := PRECALCULATED_SCHEMAS.get(schema_name)) is not None:
        return schema
    PRECALCULATED_SCHEMAS[schema_name] = cast(
        BaseOrOneOfSchemaType,
        schema_cls.from_dict(
            schema_fields,
            name=schema_name,
        ),
    )
    return PRECALCULATED_SCHEMAS[schema_name]


def get_help(vs_instance: valuespec.ValueSpec) -> str:
    help_text = vs_instance.help()
    title = vs_instance.title()
    if help_text and title:
        return f"<h3>{title}</h3><p>{help_text}</p>"
    if help_text:
        return f"<p>{help_text}</p>"
    if title:
        return f"<h3>{title}</h3>"
    return ""


def get_default_params(required: bool, allow_empty: bool, default_value: typing.Any) -> dict:
    params = {"required": required}
    if required:
        params["example"] = default_value
        params["allow_none"] = allow_empty
    if not required:
        # TODO: need to verify in combination with allow_empty
        # - valuespec with None as allowed value
        # - if API provides no value for required=False
        params["load_default"] = default_value
    return params


def valuespec_to_marshmallow(
    vs_instance: valuespec.ValueSpec,
    *,
    name: str | bool | int | None = None,
    required: bool = False,
) -> fields.Field:
    match_entry = MATCHERS[type(vs_instance)]

    if name is not None:
        name = str(name)

    return match_entry.match_func(vs_instance, name, required)
