#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access
"""This module provides hooks for converting ValueSpec trees into FormElement instances.

These hooks are used in the function `valuespec_to_formspec` to convert each node of a tree of
ValueSpec instances into a tree of FormElement instances. Each hook is responsible for calling
`valuespec_to_formspec` on the sub-nodes of it's matched ValueSpec instance.

To define a hook for a specific ValueSpec subclass, decorate a function with
`@match_on(valuespec.ValueSpecClassName)`. This function will then be used to convert instances of
`ValueSpecClassName` into FormElements.

Example:

    @match_on(valuespec.Integer)
    def valuespec_integer(valuespec_instance: valuespec.Integer) -> form_spec.Integer:
        # ... code to convert the ValueSpec instance to a FormElement ...

Note:
    Ensure the hooks are appropriately registered for each ValueSpec subclass for correct
    conversion. Subclasses will not automatically use the converter of the parent-class, each
    distinct class has to have its own converter.

Module Attributes:
    list_choices: A function which extracts the choices from dropdown, etc. ValueSpecs.
    match_on: Decorator used to register conversion functions for specific ValueSpec subclasses.
    maybe_lazy: A function which evaluates a callable, but doesn't if the value is concrete.
    optional_text: A function which converts text types from ValueSpec land to FormSpec land.
    default_value, default_or_input_hint, default_or_placeholder:
        Functions for type conversion between ValueSpec land and FormSpec land

    valuespec_to_formspec:
        The entry point of the conversion system. Pass any ValueSpec instance there.
"""
import re
import typing
from dataclasses import dataclass

from cmk.gui.exceptions import MKUserError
from cmk.gui.utils.html import HTML

from cmk.rulesets.v1 import form_specs, Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import DefaultValue, InputHint, validators
from cmk.rulesets.v1.form_specs.validators import LengthInRange, NumberInRange

from . import definitions

#
# NOTE
#  * Instances of ValueSpec are "special" as they are not aware of their own name. The reason
#    for this lies in the manner they are constructed, which inherently prevents them from having
#    this knowledge.
# Problems:
#  * Our intermediate-representation tree needs all nodes to have names.
#    The reason for this is that these nodes are then used to render HTML forms, and inputs have to
#    have names.
#  * Also, these names should properly correspond to the structure that is expected by
#    `datastructures.NestedDictConverter`.
#


ModelT = typing.TypeVar("ModelT")

T = typing.TypeVar("T")

T_L = typing.TypeVar("T_L", Help, Label, Message, Title)

V_c = typing.TypeVar("V_c", bound=definitions.ValueSpec)

MigrateFunc = typing.Callable[[typing.Any], typing.Any]
TransformFunction = typing.Callable[[V_c, MigrateFunc | None], form_specs.FormSpec]


@typing.runtime_checkable
class FormSpecProtocol(typing.Protocol[ModelT]):
    title: Title | None = None
    help_text: Title | None = None
    migrate: typing.Callable[[object], ModelT] | None = None
    custom_validate: typing.Callable[[ModelT], object] | None = None

    def __call__(
        self,
        title: Title | None = None,
        help_text: Title | None = None,
        migrate: typing.Callable[[object], ModelT] | None = None,
        custom_validate: typing.Callable[[ModelT], object] | None = None,
    ) -> typing.Self: ...


@typing.runtime_checkable
class FormSpecProtocolPrefill(typing.Protocol[ModelT]):
    title: Title | None = None
    help_text: Title | None = None
    migrate: typing.Callable[[object], ModelT] | None = None
    prefill: DefaultValue[ModelT] | InputHint[ModelT]  # only change

    def __call__(
        self,
        prefill: DefaultValue[ModelT] | InputHint[ModelT],
        title: Title | None = None,
        help_text: Title | None = None,
        migrate: typing.Callable[[object], ModelT] | None = None,
        custom_validate: typing.Callable[[ModelT], object] | None = None,
    ) -> typing.Self: ...


@typing.runtime_checkable
class FormSpecProtocolDefault(typing.Protocol[ModelT]):
    prefill: DefaultValue[ModelT]  # only change
    title: Title | None = None
    help_text: Title | None = None
    migrate: typing.Callable[[object], ModelT] | None = None
    custom_validate: typing.Callable[[ModelT], object] | None = None

    def __call__(
        self,
        prefill: DefaultValue[ModelT],
        title: Title | None = None,
        help_text: Title | None = None,
        migrate: typing.Callable[[object], ModelT] | None = None,
        custom_validate: typing.Callable[[ModelT], object] | None = None,
    ) -> typing.Self: ...


# @match_on(definitions.Color)
# def valuespec_color(
#    vs_instance: definitions.Color,
#    migrate_func: MigrateFunc | None = None,
# ) -> Color:
#    return _simple_case(
#        vs_instance,
#        migrate_func=migrate_func,
#        form_spec_class=formspec_definitions.Color,
#    )
#
#
# @match_on(definitions.DatePicker)
# def valuespec_date_picker(
#    vs_instance: definitions.DatePicker,
#    migrate_func: MigrateFunc | None = None,
# ) -> formspec_definitions.DatePicker:
#    return _simple_case(
#        vs_instance,
#        migrate_func=migrate_func,
#        form_spec_class=formspec_definitions.DatePicker,
#    )
#
#
# def _simple_case(
#     vs_instance: definitions.ValueSpec,
#     *,
#     migrate_func: MigrateFunc | None,
#     form_spec_class: type[T],
# ) -> T:
#     if isinstance(form_spec_class, FormSpecProtocolPrefill) and isinstance(
#         vs_instance, definitions.TextInput
#     ):
#         return form_spec_class(
#             title=optional_text(vs_instance.title(), Title),
#             help_text=optional_text(vs_instance.help(), Help),
#             custom_validate=(ValueSpecValidator(vs_instance),),
#             prefill=default_or_placeholder(vs_instance),
#             migrate=migrate_func,
#         )
#
#     if isinstance(form_spec_class, FormSpecProtocolDefault):
#         return form_spec_class(
#             title=optional_text(vs_instance.title(), Title),
#             help_text=optional_text(vs_instance.help(), Help),
#             custom_validate=(ValueSpecValidator(vs_instance),),
#             prefill=default_value(vs_instance, default=form_spec_class.prefill),
#             migrate=migrate_func,
#         )
#
#     if isinstance(form_spec_class, FormSpecProtocol):
#         return form_spec_class(
#             title=optional_text(vs_instance.title(), Title),
#             help_text=optional_text(vs_instance.help(), Help),
#             custom_validate=(ValueSpecValidator(vs_instance),),
#             migrate=migrate_func,
#         )
#
#     raise RuntimeError(f"{type(form_spec_class)} is not supported.")


def optional_text(text: str | HTML | None, output_type: type[T_L]) -> T_L | None:
    if text is None:
        return None

    return output_type(str(text))


def default_or_input_hint(
    vs_instance: definitions.ValueSpec,
    *,
    default: form_specs.Prefill,
) -> form_specs.Prefill:
    if callable(vs_instance._default_value):
        _default_value = vs_instance._default_value()
    else:
        _default_value = vs_instance._default_value

    if isinstance(_default_value, definitions.Sentinel):
        return default

    return DefaultValue(_default_value)


def default_or_placeholder(
    vs_instance: definitions.TextInput,
) -> form_specs.Prefill[str]:
    prefill: form_specs.Prefill
    if vs_instance._placeholder and not vs_instance._default_value:
        prefill = form_specs.InputHint(vs_instance._placeholder)
    elif vs_instance._default_value and not vs_instance._placeholder:
        prefill = form_specs.DefaultValue(vs_instance._default_value)
    elif vs_instance._default_value is not None and vs_instance._placeholder is not None:
        raise RuntimeError(f"Can't decide here. -> {vs_instance}")
    else:
        prefill = form_specs.InputHint("")

    return prefill


def default_value(
    vs_instance: definitions.ValueSpec, *, default: form_specs.DefaultValue[T]
) -> form_specs.DefaultValue[T]:
    if callable(vs_instance._default_value):
        _default_value = vs_instance._default_value()
    else:
        _default_value = vs_instance._default_value

    if isinstance(_default_value, definitions.Sentinel):
        return default

    return form_specs.DefaultValue(_default_value)


class MatchEntry(typing.NamedTuple, typing.Generic[V_c]):
    match_func: TransformFunction[V_c]


class MatchDict(typing.Protocol[V_c]):
    def __getitem__(self, item: type[V_c] | type[None]) -> MatchEntry[V_c]: ...

    def __setitem__(self, item: type[V_c] | type[None], value: MatchEntry[V_c]) -> None: ...


matchers: MatchDict[definitions.ValueSpec] = {}


def valuespec_to_formspec(
    vs_instance: definitions.ValueSpec,
) -> form_specs.FormSpec:
    migrate_func: MigrateFunc | None
    if isinstance(vs_instance, definitions.Migrate):
        to_convert = vs_instance._valuespec
        migrate_func = vs_instance.to_valuespec
    else:
        to_convert = vs_instance
        migrate_func = None

    try:
        match_entry = matchers[type(to_convert)]
    except KeyError:
        match_entry = MatchEntry(match_func=generic_valuespec_to_formspec)
    return match_entry.match_func(to_convert, migrate_func)


@dataclass(frozen=True, kw_only=True)
class ValueSpecFormSpec(form_specs.FormSpec[definitions.ValueSpec]):
    valuespec: definitions.ValueSpec
    prefill: DefaultValue[typing.Any] | InputHint[Title] = InputHint(Title(""))


def generic_valuespec_to_formspec(
    vs_instance: definitions.ValueSpec,
    migrate_func: MigrateFunc | None = None,
) -> ValueSpecFormSpec:
    return ValueSpecFormSpec(
        title=optional_text(vs_instance.title(), Title),
        help_text=optional_text(vs_instance.help(), Help),
        valuespec=vs_instance,
        custom_validate=(ValueSpecValidator(vs_instance),),
        migrate=migrate_func,
    )


def match_on(
    vs_type: type[V_c] | type[None],
) -> typing.Callable[[TransformFunction], TransformFunction]:
    """Register a transform function based on value type.

    Acts as a decorator to register a transform function (`TransformFunction`) in
    a global matcher dictionary (`matchers`). The function associates the given
    `vs_type` with the provided transform function.

    Args:
        vs_type: Type of value to match on. Can be either a custom type `V_c` or `None`.

    Returns:
        Callable[[TransformFunction], TransformFunction]: A decorator that takes a
        transform function and returns it, after registering it in the global
        `matchers` dictionary.

    Example:
        @match_on(int)
        def transform_int(value):
            ...  # do stuff here

    """

    def register_func(func: TransformFunction) -> TransformFunction:
        matchers[vs_type] = MatchEntry(match_func=func)
        return func

    return register_func


@match_on(definitions.ListOf)
def valuespec_listof(
    vs_instance: definitions.ListOf,
    migrate_func: MigrateFunc | None = None,
) -> form_specs.List:
    return form_specs.List(
        # NOTE: valuespec.ListOf doesn't support min or max length.
        title=optional_text(vs_instance.title(), Title),
        help_text=optional_text(vs_instance.help(), Help),
        element_template=valuespec_to_formspec(vs_instance._valuespec),
        custom_validate=(ValueSpecValidator(vs_instance),),
        add_element_label=Label("%s") % vs_instance._add_label,
        remove_element_label=Label("%s") % vs_instance._del_label,
        no_element_label=Label("%s") % vs_instance._text_if_empty,
        editable_order=vs_instance._movable,
        migrate=migrate_func,
    )


@match_on(definitions.HostState)
def valuespec_host_state(
    vs_instance: definitions.HostState,
    migrate_func: MigrateFunc | None = None,
) -> form_specs.HostState:
    return form_specs.HostState(
        title=optional_text(vs_instance.title(), Title),
        help_text=optional_text(vs_instance.help(), Help),
        # FIXME: This requires Literal[0, 1, 2, 3] as type, but I don't want to cast this.
        prefill=default_or_input_hint(vs_instance, default=form_specs.HostState.prefill),  # type: ignore[arg-type]
        custom_validate=(ValueSpecValidator(vs_instance),),
        migrate=migrate_func,
    )


@match_on(definitions.ListOfStrings)
def valuespec_listofstrings(
    vs_instance: definitions.ListOfStrings,
    migrate_func: MigrateFunc | None = None,
) -> form_specs.List:
    list_validators: list[typing.Callable[[typing.Sequence], None]] = [
        ValueSpecValidator(vs_instance)
    ]
    if vs_instance._max_entries is not None:
        list_validators.append(
            LengthInRange(
                min_value=None,
                max_value=vs_instance._max_entries,
            )
        )

    return form_specs.List(
        title=optional_text(vs_instance.title(), Title),
        help_text=optional_text(vs_instance.help(), Help),
        element_template=valuespec_to_formspec(
            vs_instance._valuespec
        ),  # may not necessarily be a String, e.g. NetworkPort
        custom_validate=tuple(list_validators),
        migrate=migrate_func,
    )


@match_on(definitions.Age)
@match_on(definitions.TimeSpan)
def valuespec_timespan(
    vs_instance: definitions.TimeSpan,
    migrate_func: MigrateFunc | None = None,
) -> form_specs.TimeSpan:
    mapping = {
        "days": form_specs.TimeMagnitude.DAY,
        "hours": form_specs.TimeMagnitude.HOUR,
        "minutes": form_specs.TimeMagnitude.MINUTE,
        "seconds": form_specs.TimeMagnitude.SECOND,
        "milliseconds": form_specs.TimeMagnitude.MILLISECOND,
    }
    displayed_magnitudes: list[form_specs.TimeMagnitude] = [
        mapping[name]
        for name in typing.cast(list[str], vs_instance._display)  # Container has no __iter__
    ]

    return form_specs.TimeSpan(
        title=optional_text(vs_instance.title(), Title),
        help_text=optional_text(vs_instance.help(), Help),
        label=optional_text(vs_instance._label, Label),
        displayed_magnitudes=displayed_magnitudes,
        prefill=default_or_input_hint(vs_instance, default=form_specs.TimeSpan.prefill),
        migrate=migrate_func,
    )


# @match_on(definitions.LDAPDistinguishedName)
# def valuespec_ldap_distinguished_name(
#    vs_instance: definitions.LDAPDistinguishedName,
#    migrate_func: MigrateFunc | None = None,
# ) -> form_specs.String:
#    return form_specs.String(
#        title=optional_text(vs_instance.title(), Title),
#        help_text=optional_text(vs_instance.help(), Help),
#        label=optional_text(vs_instance._label, Label),
#        custom_validate=(
#            EnforceSuffix(vs_instance.enforce_suffix, case="ignore"),
#        )
#        if vs_instance.enforce_suffix
#        else None,
#        prefill=default_or_placeholder(vs_instance),
#        migrate=migrate_func,
#    )


LBU: typing.TypeAlias = definitions.LegacyBinaryUnit
IM: typing.TypeAlias = form_specs.IECMagnitude
SIM: typing.TypeAlias = form_specs.SIMagnitude


@match_on(definitions.LegacyDataSize)
def valuespec_legacy_data_size(
    vs_instance: definitions.LegacyDataSize,
    migrate_func: MigrateFunc | None = None,
) -> form_specs.DataSize:
    sim_mapping: dict[LBU, SIM] = {
        LBU.Byte: SIM.BYTE,
        LBU.KB: SIM.KILO,
        LBU.MB: SIM.MEGA,
        LBU.GB: SIM.GIGA,
        LBU.TB: SIM.TERA,
        LBU.PB: SIM.PETA,
        LBU.EB: SIM.EXA,
        LBU.ZB: SIM.ZETTA,
        LBU.YB: SIM.YOTTA,
    }
    sim_magnitudes: list[SIM] = [sim_mapping[name] for name in vs_instance._units]

    im_mapping: dict[LBU, IM] = {
        LBU.KiB: IM.KIBI,
        LBU.MiB: IM.MEBI,
        LBU.GiB: IM.GIBI,
        LBU.TiB: IM.TEBI,
        LBU.PiB: IM.PEBI,
        LBU.EiB: IM.EXBI,
        LBU.ZiB: IM.ZEBI,
        LBU.YiB: IM.YOBI,
    }
    im_magnitudes: list[IM] = [im_mapping[name] for name in vs_instance._units]

    displayed_magnitudes: list[IM] | list[SIM]
    if sim_magnitudes and not im_magnitudes:
        displayed_magnitudes = sim_magnitudes
    elif im_magnitudes and not sim_magnitudes:
        displayed_magnitudes = im_magnitudes
    else:
        raise RuntimeError("SI binary units and IEC binary units may not be mixed.")

    return form_specs.DataSize(
        title=optional_text(vs_instance.title(), Title),
        help_text=optional_text(vs_instance.help(), Help),
        label=optional_text(vs_instance._renderer._label, Label),
        displayed_magnitudes=displayed_magnitudes,
        custom_validate=(ValueSpecValidator(vs_instance),),
        migrate=migrate_func,
    )


@match_on(definitions.Filesize)
def valuespec_filesize(
    vs_instance: definitions.Filesize,
    migrate_func: MigrateFunc | None = None,
) -> form_specs.DataSize:
    mapping: dict[str, IM] = {
        "Byte": IM.BYTE,
        "KiB": IM.KIBI,
        "MiB": IM.MEBI,
        "GiB": IM.GIBI,
        "TiB": IM.TEBI,
    }
    displayed_magnitudes: list[IM] = [mapping[name] for name in vs_instance._names]

    return form_specs.DataSize(
        title=optional_text(vs_instance.title(), Title),
        help_text=optional_text(vs_instance.help(), Help),
        label=optional_text(vs_instance._renderer._label, Label),
        displayed_magnitudes=displayed_magnitudes,
        custom_validate=(ValueSpecValidator(vs_instance),),
        migrate=migrate_func,
    )


@match_on(definitions.Integer)
def valuespec_integer(
    vs_instance: definitions.Integer,
    migrate_func: MigrateFunc | None = None,
) -> form_specs.Integer:
    validator_list: list[typing.Callable[[int], None]] = []
    if vs_instance._bounds._upper is not None or vs_instance._bounds._lower is not None:
        validator_list.append(
            NumberInRange(
                min_value=vs_instance._bounds._lower,
                max_value=vs_instance._bounds._upper,
            )
        )
    validator_list.append(ValueSpecValidator(vs_instance))

    return form_specs.Integer(
        title=optional_text(vs_instance.title(), Title),
        help_text=optional_text(vs_instance.help(), Help),
        custom_validate=tuple(validator_list),
        label=optional_text(vs_instance._renderer._label, Label),
        prefill=default_or_input_hint(vs_instance, default=form_specs.Integer.prefill),
        migrate=migrate_func,
    )


@match_on(definitions.CheckmkVersionInput)
@match_on(definitions.TextInput)
def valuespec_textinput(
    vs_instance: definitions.TextInput,
    migrate_func: MigrateFunc | None = None,
) -> form_specs.String:
    min_len = vs_instance._minlen
    if not vs_instance.allow_empty() and not min_len:
        min_len = 1

    max_len = vs_instance._maxlen

    custom_validators: list[typing.Callable[[str], None]] = [ValueSpecValidator(vs_instance)]
    if min_len or max_len:
        custom_validators.append(
            LengthInRange(
                min_value=min_len,
                max_value=max_len,
            ),
        )

    if vs_instance._forbidden_chars:
        custom_validators.append(
            validators.MatchRegex(
                f"[^{re.escape(vs_instance._forbidden_chars)}]",
                error_msg=Message("The following characters are forbidden: %s")
                % vs_instance._forbidden_chars,
            ),
        )

    if vs_instance._regex is not None:
        custom_validators.append(
            validators.MatchRegex(
                vs_instance._regex,
                error_msg=Message("%s") % vs_instance._regex_error,
            )
        )

    return form_specs.String(
        title=optional_text(vs_instance.title(), Title),
        help_text=optional_text(vs_instance.help(), Help),
        label=optional_text(vs_instance._label, Label),
        custom_validate=tuple(custom_validators),
        prefill=default_or_placeholder(vs_instance),
        migrate=migrate_func,
    )


@match_on(definitions.Dictionary)
def valuespec_dictionary(
    vs_instance: definitions.Dictionary,
    migrate_func: MigrateFunc | None = None,
) -> form_specs.Dictionary:
    optional_keys = vs_instance._optional_keys
    required_keys = vs_instance._required_keys

    dictionary_elements = {}
    for ident, element in maybe_lazy(vs_instance._elements):
        optional = False if optional_keys in (False, []) else ident not in required_keys
        dictionary_elements[ident] = form_specs.DictElement(
            parameter_form=valuespec_to_formspec(element),
            required=not optional,
        )

    return form_specs.Dictionary(
        title=optional_text(vs_instance.title(), Title),
        help_text=optional_text(vs_instance.help(), Help),
        elements=dictionary_elements,
        custom_validate=(ValueSpecValidator(vs_instance),),
        migrate=migrate_func,
    )


@match_on(definitions.FixedValue)
def valuespec_fixed_value(
    vs_instance: definitions.FixedValue,
    migrate_func: MigrateFunc | None = None,
) -> form_specs.FixedValue:
    return form_specs.FixedValue(
        title=optional_text(vs_instance.title(), Title),
        help_text=optional_text(vs_instance.help(), Help),
        value=vs_instance._value,
        migrate=migrate_func,
    )


@match_on(definitions.Checkbox)
def valuespec_checkbox(
    vs_instance: definitions.Checkbox,
    migrate_func: MigrateFunc | None = None,
) -> form_specs.BooleanChoice:
    return form_specs.BooleanChoice(
        title=optional_text(vs_instance.title(), Title),
        help_text=optional_text(vs_instance.help(), Help),
        label=optional_text(vs_instance._label, Label),
        prefill=default_value(vs_instance, default=form_specs.BooleanChoice.prefill),
        migrate=migrate_func,
    )


@match_on(definitions.DropdownChoice)
def valuespec_dropdown_choice(
    vs_instance: definitions.DropdownChoice,
    migrate_func: MigrateFunc | None = None,
) -> form_specs.SingleChoice:
    return form_specs.SingleChoice(
        title=optional_text(vs_instance.title(), Title),
        help_text=optional_text(vs_instance.help(), Help),
        label=optional_text(vs_instance._label, Label),
        no_elements_text=Message("%s") % vs_instance._empty_text,
        elements=[
            form_specs.SingleChoiceElement(
                name=name,
                title=Title("%s") % title,
            )
            for name, title in vs_instance.choices()
        ],
        prefill=default_or_input_hint(vs_instance, default=form_specs.SingleChoice.prefill),
        custom_validate=(ValueSpecValidator(vs_instance),),
        migrate=migrate_func,
    )


# @match_on(definitions.Alternative)
# def valuespec_alternative(
#     vs_instance: definitions.Alternative,
# ) -> elements.UnionElement:
#     return elements.UnionElement(
#         details=elements.UnionDetails(
#             elements=[
#                 valuespec_to_formspec(sub_vs)
#                 for sub_vs in maybe_lazy(vs_instance._elements)
#             ],
#             label_text=vs_instance.title(),
#         ),
#     )


@match_on(definitions.CascadingDropdown)
def valuespec_cascading_dropdown(
    vs_instance: definitions.CascadingDropdown,
    migrate_func: MigrateFunc | None = None,
) -> form_specs.CascadingSingleChoice:
    def enforce_str(value: str | bool | int | None) -> str:
        if value is None:
            raise RuntimeError("Can't be None")
        return str(value)

    def enforce_valuespec(vs_inst: definitions.ValueSpec | None) -> definitions.ValueSpec:
        if vs_inst is None:
            raise RuntimeError("Can't be None")
        return vs_inst

    # NOTE
    # This conversion is a bit hairy, because the ValueSpec and FormSpec logic differ a bit.
    # The case of _no_preselect_title = None has semantic meaning in the ValueSpec, but can't be
    # represented in the FormSpec.
    # WARNING
    # The FormSpec one is the more sensible one though, so for now the conversion of undefinable
    # FormSpec combinations is intentionally broken.
    prefill: form_specs.Prefill
    if vs_instance._no_preselect_title is not None:
        prefill = InputHint(Title("%s") % vs_instance._no_preselect_title)
    elif not isinstance(vs_instance._default_value, definitions.Sentinel):
        prefill = DefaultValue(vs_instance._default_value)
    else:
        raise RuntimeError(
            "Either select 'no_preselect_text' or 'default_value', but not both or neither of them."
        )

    return form_specs.CascadingSingleChoice(
        title=optional_text(vs_instance.title(), Title),
        help_text=optional_text(vs_instance.help(), Help),
        label=optional_text(vs_instance._label, Label),
        elements=[
            form_specs.CascadingSingleChoiceElement(
                name=enforce_str(name),
                title=Title("%s") % title,
                parameter_form=valuespec_to_formspec(enforce_valuespec(sub_vs_instance)),
            )
            for name, title, sub_vs_instance in maybe_lazy(vs_instance._choices)
        ],
        prefill=prefill,
        migrate=migrate_func,
    )


@match_on(definitions.RegExp)
def valuespec_regexp(
    vs_instance: definitions.RegExp,
    migrate_func: MigrateFunc | None = None,
) -> form_specs.RegularExpression:
    matching_scope = {
        definitions.RegExp.infix: form_specs.MatchingScope.INFIX,
        definitions.RegExp.complete: form_specs.MatchingScope.FULL,
        definitions.RegExp.prefix: form_specs.MatchingScope.PREFIX,
    }[vs_instance._mode]

    return form_specs.RegularExpression(
        title=optional_text(vs_instance.title(), Title),
        help_text=optional_text(vs_instance.help(), Help),
        label=optional_text(vs_instance._label, Label),
        predefined_help_text=matching_scope,
        prefill=default_or_placeholder(vs_instance),
        migrate=migrate_func,
    )


@match_on(definitions.Url)
def valuespec_url(
    vs_instance: definitions.Url,
    migrate_func: MigrateFunc | None = None,
) -> form_specs.String:
    return form_specs.String(
        title=optional_text(vs_instance.title(), Title),
        help_text=optional_text(vs_instance.help(), Help),
        prefill=default_or_placeholder(vs_instance),
        migrate=migrate_func,
        custom_validate=(
            validators.Url(
                protocols=[
                    validators.UrlProtocol(scheme) for scheme in vs_instance._allowed_schemes
                ]
            ),
            LengthInRange(
                min_value=None,
                max_value=(
                    int(vs_instance._size) if vs_instance._size not in ("max", None) else None
                ),
            ),
            ValueSpecValidator(vs_instance),
        ),
    )


@match_on(definitions.Float)
def valuespec_float(
    vs_instance: definitions.Float,
    migrate_func: MigrateFunc | None = None,
) -> form_specs.Float:
    # FIXME: missing decimal separator
    validator_list: list[typing.Callable[[float], None]] = []
    if vs_instance._bounds._upper is not None or vs_instance._bounds._lower is not None:
        validator_list.append(
            NumberInRange(
                min_value=vs_instance._bounds._lower,
                max_value=vs_instance._bounds._upper,
            )
        )

    validator_list.append(ValueSpecValidator(vs_instance))
    return form_specs.Float(
        title=optional_text(vs_instance.title(), Title),
        help_text=optional_text(vs_instance.help(), Help),
        custom_validate=tuple(validator_list),
        label=optional_text(vs_instance._renderer._label, Label),
        migrate=migrate_func,
        prefill=default_or_input_hint(vs_instance, default=form_specs.Float.prefill),
    )


@match_on(definitions.EmailAddress)
def valuespec_email(
    vs_instance: definitions.EmailAddress,
    migrate_func: MigrateFunc | None = None,
) -> form_specs.String:
    return form_specs.String(
        title=optional_text(vs_instance.title(), Title),
        help_text=optional_text(vs_instance.help(), Help),
        custom_validate=(validators.EmailAddress(),),
        migrate=migrate_func,
        prefill=default_or_placeholder(vs_instance),
    )


def list_choices(choices: definitions.ListChoiceChoices) -> list[tuple[str, str]]:
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
        return [(str(key), value) for key, value in choices.items()]

    return [(str(key), value) for key, value in choices]


@match_on(definitions.ListChoice)
def valuespec_list_choice(
    vs_instance: definitions.ListChoice,
    migrate_func: MigrateFunc | None = None,
) -> form_specs.MultipleChoice:
    elements: list[form_specs.MultipleChoiceElement] = []
    for ident, label in maybe_lazy(vs_instance._elements):
        elements.append(
            form_specs.MultipleChoiceElement(
                name=str(ident),
                title=Title("%s") % label,
            )
        )

    return form_specs.MultipleChoice(
        title=optional_text(vs_instance.title(), Title),
        help_text=optional_text(vs_instance.help(), Help),
        elements=elements,
        show_toggle_all=vs_instance._toggle_all,
        custom_validate=(ValueSpecValidator(vs_instance),),
        prefill=default_value(vs_instance, default=form_specs.MultipleChoice.prefill),
        migrate=migrate_func,
    )


@typing.overload
def maybe_lazy(entry: typing.Callable[[], typing.Iterable[T]]) -> typing.Iterable[T]: ...


@typing.overload
def maybe_lazy(entry: typing.Iterable[T]) -> typing.Iterable[T]: ...


def maybe_lazy(
    entry: typing.Iterable[T] | typing.Callable[[], typing.Iterable[T]]
) -> typing.Iterable[T]:
    """Return the iterable unchanged, but invoking the parameter if it's a callable.

    Takes either an iterable or a callable that returns an iterable as input. If the input is a
    callable, it is called to obtain the iterable.

    Args:
        entry: The iterable or callable returning an iterable to process.

    Returns:
        The resulting iterable. Returns the input directly if it's already an iterable, or the
        result of calling it if it's a callable.

    Examples:
        >>> maybe_lazy([1, 2, 3])
        [1, 2, 3]

        >>> maybe_lazy(lambda: [1, 2, 3])
        [1, 2, 3]
    """
    if callable(entry):
        return entry()
    return entry


class ValueSpecValidator:
    def __init__(self, vs_instance: definitions.ValueSpec) -> None:
        self.vs_instance = vs_instance

    def __call__(self, value: typing.Any) -> None:
        try:
            # NOTE
            # validators given to the instance via validate=... are also called by validate_value
            self.vs_instance.validate_datatype(value, "")
            self.vs_instance.validate_value(value, "")
        except MKUserError as exc:
            raise validators.ValidationError(Message("%s") % str(exc))
