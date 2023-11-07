#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module provides hooks for converting ValueSpec trees into FormElement instances.

These hooks are used in the function `valuespec_to_ir` to convert each node of a tree of
ValueSpec instances into a FormElement. Each hook is responsible for calling `valuespec_to_ir`
on the sub-nodes of it's matched ValueSpec instance.

To define a hook for a specific ValueSpec subclass, decorate a function with
`@match_on(valuespec.ValueSpecClassName)`. This function will then be used to convert instances of
`ValueSpecClassName` into FormElements.

Example:

    @match_on(valuespec.Integer)
    def valuespec_integer(valuespec_instance: valuespec.Integer) -> compiler.Integer:
        # ... code to convert the ValueSpec instance to a FormElement ...

Note:
    Ensure the hooks are appropriately registered for each ValueSpec subclass for correct
    conversion.

Module Attributes:
    default_of: A function which gives the default value of a given ValueSpec instance.
    list_choices: A function which extracts the choices from dropdown, etc. ValueSpecs.
    match_on: Decorator used to register conversion functions for specific ValueSpec subclasses.
    maybe_lazy: A function which evaluates a callable, but doesn't if the value is concrete.
"""
import typing

from cmk.gui import valuespec
from cmk.gui.validation.ir import elements
from cmk.gui.validation.ir.elements import DictionaryKeySpec, LegacyValueSpecDetails

Stack = list[str]
T = typing.TypeVar("T")


def stack_to_name(stack: Stack, append: str | None = None) -> str:
    res = ".".join(stack)
    if append:
        res += f".{append}"

    return res


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
# Solution:
#    In order to address this issue, we maintain a stack during the traversal of the ValueSpec-tree,
#    adding a new name-component to it whenever a part is discovered (like a dictionary key, and
#    so on). When generating a node, the name is formed by connecting the current stack elements
#    with dots (for instance, elem.key1.key2).
#    Special cases, such as lists, can also be accommodated by using placeholders (like
#    elem.{index}.key2). These placeholders can then be utilized by different visitors to input the
#    pertinent naming, which means they can either keep it as a template or substitute it with a
#    specific value. See _render_tag.


T_F_co = typing.TypeVar("T_F_co", bound=elements.FormElement, covariant=True)
V_c = typing.TypeVar("V_c", bound=valuespec.ValueSpec)

TransformFunction = typing.Callable[[V_c, Stack, str | None], elements.FormElement]


class MatchEntry(typing.NamedTuple, typing.Generic[V_c]):
    match_func: TransformFunction[V_c]
    has_name: bool


class MatchDict(typing.Protocol[V_c]):
    def __getitem__(self, item: type[V_c] | type[None]) -> MatchEntry[V_c]:
        ...

    def __setitem__(self, item: type[V_c] | type[None], value: MatchEntry[V_c]) -> None:
        ...


matchers: MatchDict[valuespec.ValueSpec] = {}


def match_on(
    vs_type: type[V_c] | type[None],
    has_name: bool = True,
) -> typing.Callable[[TransformFunction], TransformFunction]:
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

    def register_func(func: TransformFunction) -> TransformFunction:
        matchers[vs_type] = MatchEntry(match_func=func, has_name=has_name)
        return func

    return register_func


def get_validator(vs_instance: valuespec.ValueSpec | None) -> list[elements.Validator] | None:
    if vs_instance is None:
        return None

    def validator(value: typing.Any, _all_values: typing.Any) -> None:
        vs_instance.validate_datatype(value, varprefix="")
        vs_instance.validate_value(value, varprefix="")

    return [validator]


# @match_on(valuespec.ListOf)
def valuespec_listof(
    vs_instance: valuespec.ListOf,
    stack: Stack,
    name: str | None,
) -> elements.ListElement:
    return elements.ListElement(
        ident=stack_to_name(stack),
        details=elements.ListDetails(
            # NOTE: valuespec.ListOf doesn't support min or max length.
            min_length=None,
            max_length=None,
            label_text=vs_instance.title(),
            help=get_help(vs_instance),
            entry=valuespec_to_ir(vs_instance._valuespec, stack=stack, name="{index}"),
            default_value=default_of(vs_instance),
        ),
        validators=get_validator(vs_instance),
    )


# @match_on(valuespec.ListOfStrings)
def valuespec_listofstrings(
    vs_instance: valuespec.ListOfStrings,
    stack: Stack,
    name: str | None,
) -> elements.ListElement:
    return elements.ListElement(
        ident=stack_to_name(stack),
        validators=get_validator(vs_instance),
        details=elements.ListDetails(
            label_text=vs_instance.title(),
            max_length=vs_instance._max_entries,
            min_length=None,
            entry=elements.StringElement(
                ident=stack_to_name(stack, append="{index}"),
                validators=None,  # FIXME string validator
                details=elements.StringDetails(
                    placeholder=None,
                    personality="string",
                    label_text=None,
                    help=None,
                    default_value=None,
                    min_length=None,
                    max_length=None,
                    pattern=None,
                ),
            ),
            help=get_help(vs_instance),
            default_value=default_of(vs_instance),
        ),
    )


# @match_on(valuespec.Timeofday)
def valuespec_timeofday(
    vs_instance: valuespec.Timeofday,
    stack: Stack,
    name: str | None,
) -> elements.TimeElement:
    return elements.TimeElement(
        ident=stack_to_name(stack),
        details=elements.TimeDetails(
            help=get_help(vs_instance),
            label_text=vs_instance.title(),
            default_value=default_of(vs_instance),
            allow_24_00=vs_instance._allow_24_00,
        ),
        validators=get_validator(vs_instance),
    )


# @match_on(valuespec.Age)
def valuespec_age(
    vs_instance: valuespec.Age,
    stack: Stack,
    name: str | None,
) -> elements.AgeElement:
    return elements.AgeElement(
        ident=stack_to_name(stack),
        details=elements.AgeDetails(
            display=vs_instance._display,
            help=get_help(vs_instance),
            label_text=vs_instance.title(),
            default_value=default_of(vs_instance),
        ),
        validators=get_validator(vs_instance),
    )


@match_on(valuespec.Integer)
@match_on(valuespec.Filesize)
def valuespec_integer(
    vs_instance: valuespec.Integer,
    stack: Stack,
    name: str | None,
) -> elements.NumberElement:
    return elements.NumberElement(
        ident=stack_to_name(stack),
        details=elements.NumberDetails(
            help=get_help(vs_instance),
            label_text=vs_instance.title(),
            default_value=default_of(vs_instance),
            unit=vs_instance._renderer._unit,
            le=vs_instance._bounds._upper,
            ge=vs_instance._bounds._lower,
            lt=None,
            gt=None,
            multiple_of=None,
            type=int,
        ),
        validators=get_validator(vs_instance),
    )


# @match_on(valuespec.HostAddress)
# @match_on(valuespec.TextInput)
def valuespec_textinput(
    vs_instance: valuespec.TextInput,
    stack: Stack,
    name: str | None,
) -> elements.StringElement:
    personality: elements.StringPersonalities
    if isinstance(vs_instance, valuespec.HostAddress):
        personality = "hostname"
    else:
        personality = "string"

    min_len = vs_instance._minlen
    if not vs_instance.allow_empty() and not min_len:
        min_len = 1

    max_len: int | None
    if vs_instance._size == "max":
        max_len = None
    else:
        max_len = vs_instance._size

    return elements.StringElement(
        ident=stack_to_name(stack),
        details=elements.StringDetails(
            placeholder=vs_instance._empty_text or None,
            personality=personality,
            help=get_help(vs_instance),
            label_text=vs_instance.title(),
            default_value=default_of(vs_instance),
            min_length=min_len,
            max_length=max_len,
            pattern=None,
        ),
        validators=get_validator(vs_instance),
    )


# @match_on(valuespec.Timerange)
def valuespec_timerange(
    vs_instance: valuespec.Timerange,
    stack: Stack,
    name: str | None,
) -> elements.TimerangeElement:
    return elements.TimerangeElement(
        ident=stack_to_name(stack),
        details=elements.TimerangeDetails(
            help=get_help(vs_instance),
            label_text=vs_instance.title(),
            default_value=default_of(vs_instance),
        ),
        validators=get_validator(vs_instance),
    )


# @match_on(valuespec.Password)
def valuespec_password(
    vs_instance: valuespec.Password,
    stack: Stack,
    name: str | None,
) -> elements.PasswordElement:
    return elements.PasswordElement(
        ident=stack_to_name(stack),
        details=elements.StringDetails(
            placeholder=vs_instance._empty_text or None,
            personality="password",
            help=get_help(vs_instance),
            label_text=vs_instance.title(),
            default_value=default_of(vs_instance),
            min_length=None,
            max_length=None,
            pattern=None,
        ),
        validators=get_validator(vs_instance),
    )


@match_on(valuespec.Dictionary)
def valuespec_dictionary(
    vs_instance: valuespec.Dictionary,
    stack: Stack,
    name: str | None,
) -> elements.TypedDictionaryElement:
    optional_keys = vs_instance._optional_keys
    required_keys = vs_instance._required_keys

    dictionary_elements = []
    for ident, element in maybe_lazy(vs_instance._elements):
        dictionary_elements.append(
            (
                DictionaryKeySpec(
                    name=ident,
                    optional=False if optional_keys in (False, []) else ident not in required_keys,
                ),
                valuespec_to_ir(element, stack=stack, name=name),
            )
        )

    return elements.TypedDictionaryElement(
        ident=stack_to_name(stack),
        details=elements.TypedDictionaryDetails(
            elements=dictionary_elements,
            label_text=vs_instance.title(),
            help=get_help(vs_instance),
            default_value=default_of(vs_instance),
        ),
        validators=get_validator(vs_instance),
    )


# @match_on(valuespec.Alternative, has_name=False)
def valuespec_alternative(
    vs_instance: valuespec.Alternative,
    stack: Stack,
    name: str | None,
) -> elements.UnionElement:
    return elements.UnionElement(
        ident=stack_to_name(stack),
        details=elements.UnionDetails(
            elements=[
                valuespec_to_ir(sub_vs, stack=stack, name=name)
                for sub_vs in maybe_lazy(vs_instance._elements)
            ],
            help=get_help(vs_instance),
            label_text=vs_instance.title(),
            default_value=default_of(vs_instance),
        ),
        validators=get_validator(vs_instance),
    )


# @match_on(valuespec.FixedValue)
def valuespec_fixedvalue(
    vs_instance: valuespec.FixedValue,
    stack: Stack,
    name: str | None,
) -> elements.ConstantElement:
    origin = typing.get_origin(vs_instance)
    if origin is not None:
        hints = typing.get_type_hints(origin)
        raise Exception(origin, hints)
    # FixedValue generic
    return elements.ConstantElement(
        ident=stack_to_name(stack),
        details=elements.ConstantDetails(
            label_text=vs_instance.title(),
            help=get_help(vs_instance),
            value=vs_instance._value,
            default_value=default_of(vs_instance),
        ),
        validators=get_validator(vs_instance),
    )


@match_on(valuespec.Checkbox)
def valuespec_checkbox(
    vs_instance: valuespec.Checkbox,
    stack: Stack,
    name: str | None,
) -> elements.CheckboxElement:
    return elements.CheckboxElement(
        ident=stack_to_name(stack),
        details=elements.Details[bool](
            label_text=vs_instance.title(),
            help=get_help(vs_instance),
            default_value=default_of(vs_instance),
        ),
        validators=get_validator(vs_instance),
    )


# @match_on(valuespec.CascadingDropdown)
def valuespec_cascading_dropdown(
    vs_instance: valuespec.CascadingDropdown,
    stack: Stack,
    name: str | None,
) -> elements.TaggedUnionElement:
    choices_ = [
        elements.TaggedUnionEntry(
            title=title,
            ident=str(ident),  # FIXME None, False, True, etc?
            element=valuespec_to_ir(
                element if element is not None else valuespec.FixedValue(ident, title=title),
                stack=stack,
                name=ident,
            ),
        )
        for ident, title, element in vs_instance.choices()
    ]
    all_keys = [entry.ident for entry in choices_]
    if len(choices_) != len(set(all_keys)):
        raise ValueError(f"Duplicate key in tagged union field: {all_keys}")

    return elements.TaggedUnionElement(
        ident=stack_to_name(stack),
        details=elements.TaggedUnionDetails(
            elements=choices_,
            help=get_help(vs_instance),
            label_text=vs_instance.title(),
            default_value=default_of(vs_instance),
        ),
        validators=get_validator(vs_instance),
    )


# @match_on(valuespec.DropdownChoice)
def valuespec_dropdown_choice(
    vs_instance: valuespec.DropdownChoice,
    stack: Stack,
    name: str | None,
) -> elements.SelectElement:
    return elements.SelectElement(
        ident=stack_to_name(stack),
        details=elements.SelectDetails(
            options=[
                elements.SelectOption(
                    value=ident,
                    label=label,
                )
                for ident, label in list_choices(vs_instance._choices)
            ],
            help=get_help(vs_instance),
            label_text=vs_instance.title(),
            default_value=default_of(vs_instance),
        ),
        validators=get_validator(vs_instance),
    )


# @match_on(valuespec.Foldable, has_name=False)
def valuespec_foldable(
    vs_instance: valuespec.Foldable,
    stack: Stack,
    name: str | None,
) -> elements.CollapsableElement:
    return elements.CollapsableElement(
        ident=stack_to_name(stack),
        details=elements.CollapsableDetails(
            help=get_help(vs_instance),
            label_text=vs_instance.title(),
            collapsed=False,
            element=valuespec_to_ir(vs_instance._valuespec, stack=stack, name=name),
            default_value=None,
        ),
        validators=get_validator(vs_instance),
    )


# @match_on(type(None))
def valuespec_none(
    vs_instance: None,
    stack: Stack,
    name: str | None,
) -> elements.NullElement:
    return elements.NullElement(
        ident=stack_to_name(stack),
        details=elements.Details[None](
            label_text=None,
            help=None,
            default_value=None,
        ),
        validators=get_validator(vs_instance),
    )


# @match_on(valuespec.Optional)
def valuespec_transparent(
    vs_instance: valuespec.Optional,
    stack: Stack,
    name: str | None,
) -> elements.TransparentElement:
    # FIXME: default_value?
    return elements.TransparentElement(
        ident=stack_to_name(stack),
        details=elements.TransparentDetails(
            element=valuespec_to_ir(vs_instance._valuespec, stack=stack, name=name),
            label_text=vs_instance.title(),
            help=get_help(vs_instance),
            default_value=default_of(vs_instance),
        ),
        validators=get_validator(vs_instance),
    )


# @match_on(valuespec.Transform)
def valuespec_transform(
    vs_instance: valuespec.Transform,
    stack: Stack,
    name: str | None,
) -> elements.TransformElement:
    args = typing.get_args(vs_instance)
    cls: type[elements.TransformDetails]
    if args:
        cls = elements.TransformDetails[args[0]]  # type: ignore[valid-type]
    else:
        cls = elements.TransformDetails
    return elements.TransformElement(
        ident=stack_to_name(stack),
        details=cls(
            element=valuespec_to_ir(vs_instance._valuespec, stack=stack, name=name),
            label_text=vs_instance.title(),
            help=get_help(vs_instance),
            default_value=default_of(vs_instance),
            convert_to=vs_instance.to_valuespec,
            convert_from=vs_instance.from_valuespec,
        ),
        validators=get_validator(vs_instance),
    )


# @match_on(valuespec.Url)
def valuespec_url(
    vs_instance: valuespec.Url,
    stack: Stack,
    name: str | None,
) -> elements.UrlElement:
    return elements.UrlElement(
        ident=stack_to_name(stack),
        details=elements.UrlDetails(
            placeholder=vs_instance._placeholder,
            personality="url",
            label_text=vs_instance.title(),
            help=get_help(vs_instance),
            default_value=default_of(vs_instance),
            allowed_schemes=list(vs_instance._allowed_schemes),
            min_length=None,
            max_length=vs_instance._size if vs_instance._size != "max" else None,
            pattern=None,
            scheme_required=vs_instance._default_scheme is not None,
            default_scheme=vs_instance._default_scheme,
        ),
        validators=get_validator(vs_instance),
    )


# @match_on(valuespec.Float)
def valuespec_float(
    vs_instance: valuespec.Float,
    stack: Stack,
    name: str | None,
) -> elements.NumberElement:
    return elements.NumberElement(
        ident=stack_to_name(stack),
        details=elements.NumberDetails(
            label_text=vs_instance.title(),
            help=get_help(vs_instance),
            unit=vs_instance._renderer._unit,
            ge=vs_instance._bounds._lower,
            gt=None,
            lt=vs_instance._bounds._upper,
            le=None,
            multiple_of=None,
            default_value=default_of(vs_instance),
            type=float,
        ),
        validators=get_validator(vs_instance),
    )


# @match_on(valuespec.EmailAddress)
def valuespec_email(
    vs_instance: valuespec.EmailAddress,
    stack: Stack,
    name: str | None,
) -> elements.EmailElement:
    return elements.EmailElement(
        ident=stack_to_name(stack),
        details=elements.StringDetails(
            personality="email",
            label_text=vs_instance.title(),
            placeholder=vs_instance._empty_text or None,
            help=get_help(vs_instance),
            default_value=default_of(vs_instance),
            max_length=vs_instance._size if vs_instance._size != "max" else None,
            min_length=None,
            pattern=None,
        ),
        validators=get_validator(vs_instance),
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
        return [(str(key), value) for key, value in choices.items()]

    return [(str(key), value) for key, value in choices]


def default_of(vs_instance: valuespec.ValueSpec) -> typing.Callable[[], typing.Any] | None:
    # We can't call default_value() as this will give us the "canonical value" as a default,
    # even if no default is set.

    # if vs_instance._default_value is valuespec.DEF_VALUE:
    #     return None
    #
    # return vs_instance.default_value

    # ab: i see no problem in using this default value. 'None', as it is used above, is obviously wrong.
    return vs_instance.default_value()


# @match_on(valuespec.ListChoice)
def valuespec_listchoice(
    vs_instance: valuespec.ListChoice,
    stack: Stack,
    _name: str | None,
) -> elements.TypedDictionaryElement:
    list_elements: list[tuple[DictionaryKeySpec, elements.FormElement]] = []
    for ident, label in list_choices(vs_instance._choices):
        list_elements.append(
            (
                DictionaryKeySpec(
                    name=ident,
                ),
                elements.CheckboxElement(
                    ident=stack_to_name(stack, append=str(ident)),
                    details=elements.Details[bool](
                        label_text=label,
                        help=None,
                        default_value=None,
                    ),
                    validators=None,
                ),
            ),
        )

    return elements.TypedDictionaryElement(
        ident=stack_to_name(stack),
        details=elements.TypedDictionaryDetails(
            label_text=vs_instance.title(),
            elements=list_elements,
            help=get_help(vs_instance),
            default_value=default_of(vs_instance),
        ),
        validators=get_validator(vs_instance),
    )


def get_help(vs_instance: valuespec.ValueSpec) -> str | None:
    if help_text := vs_instance.help():
        return str(help_text)

    return None


@match_on(valuespec.Tuple)
def valuespec_tuple(
    vs_instance: valuespec.Tuple,
    stack: Stack,
    name: str | None,
) -> elements.TupleElement:
    return elements.TupleElement(
        ident=stack_to_name(stack),
        details=elements.TupleDetails(
            elements=[
                valuespec_to_ir(sub_element, stack=stack, name=str(index))
                for index, sub_element in enumerate(vs_instance._elements)
            ],
            help=get_help(vs_instance),
            label_text=vs_instance.title(),
            default_value=default_of(vs_instance),
        ),
        validators=get_validator(vs_instance),
    )


def legacy_valuespec(vs_instance: valuespec.ValueSpec) -> elements.LegacyValueSpecElement:
    return elements.LegacyValueSpecElement(
        ident="legacy_valuespec",
        details=LegacyValueSpecDetails(
            label_text=vs_instance.title(),
            help=get_help(vs_instance),
            valuespec=vs_instance,
            default_value=vs_instance.default_value(),
        ),
        validators=get_validator(vs_instance),
    )


def valuespec_to_ir(
    vs_instance: valuespec.ValueSpec,
    *,
    stack: Stack,
    name: str | bool | int | None,
) -> elements.FormElement:
    res: elements.FormElement

    try:
        match_entry = matchers[type(vs_instance)]
    except KeyError:
        return legacy_valuespec(vs_instance)

    if name is not None:
        name = str(name)

    if match_entry.has_name and name is not None:
        stack.append(name)
        res = match_entry.match_func(vs_instance, stack, name)
        stack.pop()
    else:
        res = match_entry.match_func(vs_instance, stack, name)

    return res


@typing.overload
def maybe_lazy(entry: typing.Callable[[], typing.Iterable[T]]) -> typing.Iterable[T]:
    ...


@typing.overload
def maybe_lazy(entry: typing.Iterable[T]) -> typing.Iterable[T]:
    ...


def maybe_lazy(
    entry: typing.Iterable[T] | typing.Callable[[], typing.Iterable[T]]
) -> typing.Iterable[T]:
    """Return the iterable unchanged, but invoking the parameter it if it's a callable.

    Takes an iterable or a callable that returns an iterable as input. If the input is a
    callable, calls the function to obtain the iterable.

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
