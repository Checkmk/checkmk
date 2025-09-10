#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Migrates
- legacy value spec based rulesets (use "registry" transformer option)
- general legacy value spec to form specs

This tool will modify files in place, to make them use the API `cmk.rulesets.v1`.
It requires you to install the python library `libcst`.
It does not require, but will attempt to call `scripts/run-uvenv ruff` on the modified file(s).
For very simple plugins, it might do the whole job, for most it will not.

It's a quick and dirty, untested hacky thing.
"""

import argparse
import pprint
import subprocess
import sys
import traceback
from collections.abc import Iterable, Mapping, Sequence
from enum import Enum
from pathlib import Path
from typing import Callable

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider
from numpy.matlib import empty

# Just add whatever we might need, autoflake will remove the unused ones later
# If you're missing something, add it!
_ADDED_IMPORTS = (
    "from collections.abc import Iterable, Mapping",
    "from typing import Any",
    "from cmk.gui.form_specs.private import LegacyValueSpec, ListExtended",
    "from cmk.gui.form_specs.generators.cascading_choice_utils import enable_deprecated_cascading_elements, CascadingDataConversion",
    "from cmk.gui.form_specs.generators.alternative_utils import enable_deprecated_alternative",
    "from cmk.gui.form_specs.generators.absolute_date import AbsoluteTimestamp, DateTimeFormat",
    "from cmk.gui.form_specs.generators.age import Age",
    "from cmk.rulesets.v1 import Help, Label, Title, Message",
    (
        "from cmk.rulesets.v1.form_specs import ("
        "BooleanChoice, "
        "DefaultValue, "
        "DictElement, "
        "Dictionary, "
        "CascadingSingleChoice, "
        "CascadingSingleChoiceElement, "
        "FieldSize, "
        "FixedValue, "
        "Float, "
        "InputHint, "
        "Integer, "
        "List, "
        "LevelDirection, "
        "migrate_to_float_simple_levels, "
        "migrate_to_password, "
        "MultilineText, "
        "MultipleChoice, "
        "MultipleChoiceElement, "
        "Password, "
        "Percentage, "
        "SimpleLevels, "
        "SingleChoice, "
        "SingleChoiceElement, "
        "String, "
        "TimeMagnitude, "
        "TimeSpan, "
        "validators, "
        ")"
    ),
    (
        "from cmk.rulesets.v1.rule_specs import ActiveCheck, Topic, HostAndServiceCondition, HostCondition, "
        "HostAndItemCondition, CheckParameters, EnforcedService, DiscoveryParameters"
    ),
    ("from cmk.gui.form_specs.private import OptionalChoice, Tuple"),
)

DEFAULT_TIME_SPAN_ARGS = (
    cst.Arg(
        keyword=cst.Name("displayed_magnitudes"),
        value=cst.Tuple(
            [
                cst.Element(
                    cst.Attribute(
                        cst.Name("TimeMagnitude"),
                        cst.Name(magnitude),
                    )
                )
                for magnitude in ["DAY", "HOUR", "MINUTE", "SECOND"]
            ],
        ),
    ),
)


use_unstable_api = False
warnings = []


class Transformers(Enum):
    """Enum to select the transformers to use."""

    IMPORTS = "imports"
    VALUESPECS = "valuespecs"
    REGISTRATION = "registration"


used_transformers = {
    Transformers.IMPORTS,
    Transformers.VALUESPECS,
    Transformers.REGISTRATION,
}


class ImportsTransformer(cst.CSTTransformer):
    def __init__(self) -> None:
        super().__init__()
        self.added_import = False

    def _drop_import(self, imp_fr: cst.ImportFrom) -> bool:
        code = cst.Module([]).code_for_node(imp_fr)
        return "cmk.gui.valuespec" in code

    def leave_SimpleStatementLine(
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.SimpleStatementLine | cst.FlattenSentinel | cst.RemovalSentinel:
        # strip the old imports
        new_node: cst.SimpleStatementLine | None = updated_node
        if isinstance(imp_fr := original_node.body[0], cst.ImportFrom):
            if self._drop_import(imp_fr):
                new_node = None

        if self.added_import:
            return cst.RemovalSentinel.REMOVE if new_node is None else new_node

        self.added_import = True
        # first time: add new imports.
        return cst.FlattenSentinel(
            [
                *(cst.parse_statement(statement) for statement in _ADDED_IMPORTS),
                *(() if new_node is None else [new_node]),
            ]
        )


def _extract(keyword: str, args: Sequence[cst.Arg]) -> Iterable[cst.Arg]:
    return [arg for arg in args if cst.ensure_type(arg.keyword, cst.Name).value == keyword]


class VSTransformer(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        super().__init__()
        self._in_valuespec = False
        self._in_known_unconvertable = False

    def leave_Arg(self, original_node: cst.Arg, updated_node: cst.Arg) -> cst.Arg:
        if not self._in_valuespec or self._in_known_unconvertable:
            return updated_node
        match updated_node:
            case cst.Arg(cst.Call(func=cst.Name("_"), args=args), cst.Name("title")):
                return cst.Arg(cst.Call(func=cst.Name("Title"), args=args), cst.Name("title"))
            case cst.Arg(
                cst.Lambda(body=cst.Call(func=cst.Name("_"), args=args)), cst.Name("title")
            ):
                return cst.Arg(cst.Call(func=cst.Name("Title"), args=args), cst.Name("title"))
            case cst.Arg(cst.Call(func=cst.Name("_"), args=args), cst.Name("empty_text")):
                return cst.Arg(
                    cst.Call(func=cst.Name("Message"), args=args), cst.Name("empty_text")
                )
            case cst.Arg(cst.Call(func=cst.Name("_"), args=args), cst.Name("help")):
                return cst.Arg(cst.Call(func=cst.Name("Help"), args=args), cst.Name("help_text"))
            case cst.Arg(cst.Call(func=cst.Name("_"), args=args), cst.Name("label")):
                return cst.Arg(cst.Call(func=cst.Name("Label"), args=args), cst.Name("label"))
            case cst.Arg(value, cst.Name("default_value")):
                return cst.Arg(
                    cst.Call(cst.Name("DefaultValue"), args=[cst.Arg(value)]),
                    cst.Name("prefill"),
                )
        return updated_node

    def visit_Call(self, node: cst.Call) -> None:
        if isinstance(func := node.func, cst.Name):
            if cst.ensure_type(func, cst.Name).value in self._convertable_valuespecs:
                self._in_valuespec = True
            if cst.ensure_type(func, cst.Name).value in self._known_unconvertable:
                self._in_known_unconvertable = True

    def _optional_wrap_legacy_valuespec(self, node: cst.Call) -> cst.Call:
        """Wraps the legacy valuespec in an OptionalChoice if it is not already wrapped."""
        if not isinstance(node.func, cst.Name):
            # A callable for example
            # ("schedule", self.vs_backup_schedule()),
            return node

        if cst.ensure_type(node.func, cst.Name).value not in self._supported_form_specs:
            if not use_unstable_api:
                warnings.append(
                    f"Unstable/unoffical API required for: Wrap valuespec in LegacyValueSpec {cst.Module([]).code_for_node(node)}"
                )
            return cst.Call(
                func=cst.Attribute(value=cst.Name("LegacyValueSpec"), attr=cst.Name("wrap")),
                args=[cst.Arg(node)],
            )
        return node

    @property
    def _convertable_valuespecs(self) -> set[str]:
        return {
            "Age",
            "AbsoluteDate",
            "Dictionary",
            "ListOf",
            "TextAreaUnicode",
            "DualListChoice",
            "ListChoice",
            "Alternative",
            "CascadingDropdown",
            "Optional",
            "DropdownChoice",
            "TextInput",
            "Checkbox",
            "FixedValue",
            "IndividualOrStoredPassword",
            "MigrateToIndividualOrStoredPassword",
            "Tuple",
            "TimeSpan",
            "SimpleLevels",
        }

    @property
    def _known_unconvertable(self) -> set[str]:
        return set()

    @property
    def _supported_form_specs(self) -> set[str]:
        """Returns a set of known form specs that can be used in the migration."""
        return {
            "Dictionary",
            "List",
            "ListExtended",
            "MultilineText",
            "MultipleChoice",
            "MultipleChoice",
            "CascadingSingleChoice",
            "OptionalChoice",
            "SingleChoice",
            "String",
            "BooleanChoice",
            "FixedValue",
            "Password",
            "Password",
            "Dictionary",
            "TimeSpan",
            "SimpleLevels",
            "Tuple",
            "enable_deprecated_cascading_elements",
            "enable_deprecated_alternative",
        }

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        if isinstance(func := original_node.func, cst.Name):
            convert_call: None | cst.Call = None
            match func.value:
                case "Dictionary":
                    convert_call = self._make_dictionary(updated_node)
                case "ListOf":
                    convert_call = self._make_list(updated_node)
                case "TextAreaUnicode":
                    convert_call = self._make_multiline_text(updated_node)
                case "DualListChoice":
                    convert_call = self._make_list_choice(updated_node)
                case "ListChoice":
                    convert_call = self._make_list_choice(updated_node)
                case "CascadingDropdown":
                    convert_call = self._make_cascading_single_choice(updated_node)
                case "Alternative":
                    convert_call = self._make_cascading_single_choice_from_alternative(updated_node)
                case "Optional":
                    convert_call = self._make_optional(updated_node)
                case "DropdownChoice":
                    convert_call = self._make_single_choice(updated_node)
                case "TextInput":
                    convert_call = self._make_string(updated_node)
                case "FixedValue":
                    convert_call = self._make_fixed_value(updated_node)
                case "Checkbox":
                    convert_call = self._make_boolean_choice(updated_node)
                case "IndividualOrStoredPassword" | "MigrateToIndividualOrStoredPassword":
                    convert_call = self._make_password(updated_node)
                case "Tuple":
                    if use_unstable_api:
                        convert_call = self._make_tuple(updated_node)
                    else:
                        convert_call = self._make_dictionary_from_tuple(updated_node)
                case "TimeSpan":
                    convert_call = self._make_time_span(updated_node)
                case "Age":
                    convert_call = self._make_age(updated_node)
                case "SimpleLevels":
                    convert_call = self._make_simple_levels(updated_node)
                case "AbsoluteDate":
                    convert_call = self._make_absolute_date(updated_node)
            if convert_call is not None:
                self._in_valuespec = False
                return convert_call

            if func.value in self._known_unconvertable:
                self._in_known_unconvertable = False

        return updated_node

    def _make_multiline_text(self, old: cst.Call) -> cst.Call:
        args = self._replace_allow_empty_args(old.args, "Text area can not be empty")
        # Unable not migrate the size of the TextArea
        new_args = [
            arg for arg in args if arg.keyword and arg.keyword.value not in ("cols", "rows")
        ]

        return cst.Call(func=cst.Name("MultilineText"), args=new_args)

    def _make_tuple(self, old: cst.Call) -> cst.Call:
        args = {k.value: arg.value for arg in old.args if (k := arg.keyword) is not None}
        elements: list[cst.Element] = [
            cst.Element(self._optional_wrap_legacy_valuespec(cst.ensure_type(el.value, cst.Call)))
            for el in cst.ensure_type(args["elements"], cst.List).elements
        ]
        return cst.Call(
            func=cst.Name("Tuple"),
            args=(
                *(
                    arg
                    for arg in old.args
                    if cst.ensure_type(arg.keyword, cst.Name).value != "elements"
                ),
                cst.Arg(cst.List(elements), cst.Name("elements")),
            ),
        )

    def _make_dictionary_from_tuple(self, old: cst.Call) -> cst.Call:
        args = {k.value: arg.value for arg in old.args if (k := arg.keyword) is not None}

        elements = cst.Dict(
            [
                cst.DictElement(
                    cst.SimpleString(f"'key_{i}'"),
                    cst.Call(
                        func=cst.Name("DictElement"),
                        args=(
                            cst.Arg(
                                cst.Name("True"),
                                cst.Name("required"),
                            ),
                            cst.Arg(
                                cst.ensure_type(el, cst.Element).value, cst.Name("parameter_form")
                            ),
                        ),
                    ),
                )
                for i, el in enumerate(cst.ensure_type(args["elements"], cst.List).elements)
            ]
        )
        return cst.Call(
            func=cst.Name("Dictionary"),
            args=(
                *(
                    arg
                    for arg in old.args
                    if cst.ensure_type(arg.keyword, cst.Name).value != "elements"
                ),
                cst.Arg(elements, cst.Name("elements")),
            ),
        )

    def _make_dictionary(self, old: cst.Call) -> cst.Call:
        args = {k.value: arg.value for arg in old.args if (k := arg.keyword) is not None}
        try:
            required_keys = self._extract_required_keys(args)

            def _make_required(element_name: str) -> cst.Name:
                return cst.Name("True") if element_name in required_keys else cst.Name("False")

            elements = cst.Dict(
                [
                    cst.DictElement(
                        t.elements[0].value,
                        cst.Call(
                            func=cst.Name("DictElement"),
                            args=(
                                cst.Arg(
                                    _make_required(
                                        cst.ensure_type(t.elements[0].value, cst.SimpleString).value
                                    ),
                                    cst.Name("required"),
                                ),
                                cst.Arg(
                                    self._optional_wrap_legacy_valuespec(
                                        cst.ensure_type(t.elements[1].value, cst.Call)
                                    ),
                                    cst.Name("parameter_form"),
                                ),
                            ),
                        ),
                    )
                    for t in (
                        cst.ensure_type(el.value, cst.Tuple)
                        for el in cst.ensure_type(args["elements"], cst.List).elements
                        if isinstance(el.value, cst.Tuple)
                    )
                ]
            )
            return cst.Call(
                func=cst.Name("Dictionary"),
                args=(
                    *(
                        arg
                        for arg in old.args
                        if cst.ensure_type(arg.keyword, cst.Name).value
                        not in ("elements", "optional_keys", "required_keys")
                    ),
                    cst.Arg(elements, cst.Name("elements")),
                ),
            )
        except Exception as e:
            warnings.append(
                f"Unconvertable dictionary {old.args[0].value}: {e} {''.join(traceback.format_exc())}"
            )
            return old

    @staticmethod
    def _extract_required_keys(args: dict[str, cst.BaseExpression]) -> set[str]:
        if "required_keys" in args:
            return {
                cst.ensure_type(elem.value, cst.SimpleString).value
                for elem in cst.ensure_type(args["required_keys"], cst.List).elements
            }

        if isinstance(args["elements"], cst.Call):
            warnings.append(
                f"Dictionary element is a callable, check required keys {repr(args['elements'])}"
            )
            return set()

        present_keys = {
            cst.ensure_type(tv.elements[0].value, cst.SimpleString).value
            for t in cst.ensure_type(args["elements"], cst.List).elements
            if isinstance(tv := t.value, cst.Tuple)
        }
        if (opt := args.get("optional_keys")) is not None:
            if isinstance(opt, cst.List):
                optional_keys = {
                    cst.ensure_type(t.value, cst.SimpleString).value for t in opt.elements
                }
                return present_keys - optional_keys
            if isinstance(opt, cst.Name) and opt.value == "False":
                return present_keys

            raise NotImplementedError("required_keys scenario not supported")

        return set()

    def _make_optional(self, old: cst.Call) -> cst.Call:
        new_args: list[cst.Arg] = []
        for arg in old.args:
            if arg.keyword and arg.keyword.value == "valuespec":
                new_args.append(cst.Arg(arg.value, cst.Name("parameter_form")))
            else:
                new_args.append(arg)

        return cst.Call(func=cst.Name("OptionalChoice"), args=new_args)

    def _i18n_to_localization(self, old: cst.Call, class_name: str) -> cst.Call:
        return cst.Call(func=cst.Name(class_name), args=old.args)

    def _make_list(self, old: cst.Call) -> cst.Call:
        old_args = self._replace_allow_empty_args(old.args, "Select at least one element")
        new_args: list[cst.Arg] = []
        for arg in old_args:
            assert arg.keyword, "All args should have a keyword"
            match arg.keyword.value:
                case "valuespec":
                    new_args.append(
                        cst.Arg(
                            self._optional_wrap_legacy_valuespec(
                                cst.ensure_type(arg.value, cst.Call)
                            ),
                            cst.Name("element_template"),
                        )
                    )
                case "add_label":
                    new_args.append(
                        cst.Arg(
                            self._i18n_to_localization(
                                cst.ensure_type(arg.value, cst.Call), "Label"
                            ),
                            cst.Name("add_element_label"),
                        )
                    )
                case "empty_text":
                    new_args.append(cst.Arg(arg.value, cst.Name("no_element_label")))
                case "movable":
                    new_args.append(cst.Arg(arg.value, cst.Name("editable_order")))
                case _:
                    new_args.append(arg)

        if self._contains_keyword_arg(old_args, "prefill"):
            if not use_unstable_api:
                warnings.append(
                    f"Unstable/unofficial API required for: ListExtended required for prefill in {cst.Module([]).code_for_node(old)}"
                )
                return cst.Call(func=cst.Name("List"), args=new_args)
            return cst.Call(func=cst.Name("ListExtended"), args=new_args)
        else:
            return cst.Call(func=cst.Name("List"), args=new_args)

    def _drop_args(self, old_args: Sequence[cst.Arg], args_to_drop: Sequence[str]) -> list[cst.Arg]:
        """Drops the specified args from the old_args."""
        return [
            arg
            for arg in old_args
            if cst.ensure_type(arg.keyword, cst.Name).value not in args_to_drop
        ]

    def _contains_keyword_arg(self, args: Sequence[cst.Arg], key: str) -> bool:
        """Checks if the args contain a keyword argument with the specified key."""
        return any(cst.ensure_type(arg.keyword, cst.Name).value == key for arg in args)

    def _replace_allow_empty_args(
        self, old_args: Sequence[cst.Arg], fallback_text: str = ""
    ) -> list[cst.Arg]:
        new_args: list[cst.Arg] = []
        allow_empty = True
        empty_text_arg: list[cst.Arg] = []
        for arg in old_args:
            assert arg.keyword, "All args should have a keyword"
            if arg.keyword.value == "allow_empty":
                allow_empty = False
                continue
            if arg.keyword.value == "empty_text":
                allow_empty = False
                empty_text_arg = [arg]
                continue
            new_args.append(arg)

        if not allow_empty:
            expression = f"[validators.LengthInRange(min_value=1%s)]" % (
                f", error_msg=Message('{fallback_text}')"
                if not empty_text_arg
                else f", error_msg={cst.Module([]).code_for_node(empty_text_arg[0].value)}"
            )
            new_args.append(
                cst.Arg(
                    cst.parse_expression(expression),
                    cst.Name("custom_validate"),
                )
            )
        return new_args

    def _make_list_choice(self, old: cst.Call) -> cst.Call:
        new_args = self._replace_allow_empty_args(old.args)
        for arg in old.args:
            assert arg.keyword, "All args should have a keyword"
            if arg.keyword.value == "choices":
                warnings.append(
                    f"'choices' field in {old.func} requires manual conversion {cst.Module([]).code_for_node(arg.value)}"
                )
        return cst.Call(func=cst.Name("MultipleChoice"), args=new_args)

    def _make_cascading_single_choice_element(
        self,
        name: cst.SimpleString,
        title_args: Sequence[cst.Arg],
        parameter_form: cst.BaseExpression,
    ) -> cst.Element:
        return cst.Element(
            cst.Call(
                func=cst.Name("CascadingSingleChoiceElement"),
                args=(
                    cst.Arg(name, cst.Name("name")),
                    cst.Arg(
                        cst.Call(func=cst.Name("Title"), args=title_args),
                        cst.Name("title"),
                    ),
                    cst.Arg(parameter_form, cst.Name("parameter_form")),
                ),
            )
        )

    def _extract_title_from_formspec(self, form_spec: cst.Call) -> cst.Call:
        """Extract the title from the formspec, if it exists."""
        for arg in form_spec.args:
            assert arg.keyword, "All args should have a keyword"
            if arg.keyword.value == "title":
                return cst.ensure_type(arg.value, cst.Call)
        raise ValueError("FormSpec has no title")

    def _make_cascading_single_choice_from_alternative(self, old: cst.Call) -> cst.Call:
        if not use_unstable_api:
            warnings.append(
                f"Unstable/unofficial API required for: CascadingSingleChoice from Alternative in {cst.Module([]).code_for_node(old)}"
            )
        new_args: list[cst.Arg] = []
        for arg in old.args:
            assert arg.keyword, "All args should have a keyword"
            if arg.keyword.value == "elements":
                new_elements: list[cst.Element] = []
                if isinstance(arg.value, cst.Call):
                    warnings.append("'elements' field in Alternative is a callable")
                    new_args.append(arg)
                    continue

                for idx, el in enumerate(cst.ensure_type(arg.value, cst.List).elements):
                    parameter_form = cst.ensure_type(el.value, cst.Call)
                    new_elements.append(
                        self._make_cascading_single_choice_element(
                            cst.SimpleString(f"alternative_{idx}"),
                            self._extract_title_from_formspec(parameter_form).args,
                            parameter_form,
                        )
                    )
                new_args.append(cst.Arg(cst.List(new_elements), cst.Name("elements")))
            else:
                new_args.append(arg)

        form_spec = cst.Call(func=cst.Name("CascadingSingleChoice"), args=new_args)

        wrapped_form_spec = cst.Call(
            func=cst.Name("enable_deprecated_alternative"),
            args=[
                cst.Arg(value=form_spec, keyword=cst.Name("wrapped_form_spec")),
            ],
        )
        return wrapped_form_spec

    def _make_cascading_single_choice(self, old: cst.Call) -> cst.Call:
        new_args: list[cst.Arg] = []

        requires_legacy_format_wrapper = False
        args_for_legacy_wrapper = {}
        for arg in old.args:
            assert arg.keyword, "All args should have a keyword"
            if arg.keyword.value == "choices":
                new_elements: list[cst.Element] = []
                if isinstance(arg.value, (cst.Call, cst.Name)):
                    warnings.append(
                        f"'choices' field in DropdownChoice is not a list: {cst.Module([]).code_for_node(arg)}"
                    )
                    new_args.append(cst.Arg(arg.value, keyword=cst.Name("elements")))
                    continue

                for el in cst.ensure_type(arg.value, cst.List).elements:
                    tuple_elements: Sequence[cst.BaseElement] = cst.ensure_type(
                        el.value, cst.Tuple
                    ).elements

                    ele = tuple_elements[0].value
                    if isinstance(ele, cst.SimpleString):
                        simplified_value = cst.SimpleString(ele.value)
                    else:
                        # Im not going to add typing checks for the various subtypes
                        simplified_value = cst.SimpleString(f"'{ele.value}'")  # type: ignore[attr-defined]

                    if len(tuple_elements) == 2 or not isinstance(ele, cst.SimpleString):
                        args_for_legacy_wrapper[simplified_value.value] = (
                            tuple_elements[0].value,
                            len(tuple_elements) == 3,
                        )

                    if len(tuple_elements) == 2:
                        requires_legacy_format_wrapper = True
                        new_elements.append(
                            cst.Element(
                                cst.Call(
                                    func=cst.Name("CascadingSingleChoiceElement"),
                                    args=(
                                        cst.Arg(simplified_value, cst.Name("name")),
                                        cst.Arg(
                                            cst.Call(
                                                func=cst.Name("Title"),
                                                args=cst.ensure_type(
                                                    tuple_elements[1].value, cst.Call
                                                ).args,
                                            ),
                                            cst.Name("title"),
                                        ),
                                        cst.Arg(
                                            cst.Call(
                                                func=cst.Name("FixedValue"),
                                                args=[
                                                    cst.Arg(
                                                        cst.Name("True"),
                                                        cst.Name("value"),
                                                    )
                                                ],
                                            ),
                                            cst.Name("parameter_form"),
                                        ),
                                    ),
                                ),
                            ),
                        )
                        continue
                    if len(cst.ensure_type(el.value, cst.Tuple).elements) != 3:
                        raise Exception("Invalid number of elements in cascading choice")

                    new_elements.append(
                        self._make_cascading_single_choice_element(
                            cst.ensure_type(tuple_elements[0].value, cst.SimpleString),
                            cst.ensure_type(tuple_elements[1].value, cst.Call).args,
                            tuple_elements[2].value,
                        )
                    )
                new_args.append(cst.Arg(cst.List(new_elements), cst.Name("elements")))
            else:
                new_args.append(arg)

        form_spec = cst.Call(func=cst.Name("CascadingSingleChoice"), args=new_args)
        if not requires_legacy_format_wrapper:
            return form_spec

        if not use_unstable_api:
            warnings.append(
                f"Unstable/unofficial API required for: CascadingSingleChoice with legacy format in {cst.Module([]).code_for_node(old)}"
            )
            return form_spec

        def create_data_conversion_data_class(
            name: str, value: cst.CSTNode, has_form_spec: bool
        ) -> cst.BaseExpression:
            code = cst.Module([]).code_for_node(value)
            return cst.parse_expression(
                f"CascadingDataConversion(name_in_form_spec={name}, value_on_disk={code}, has_form_spec={has_form_spec})"
            )

        wrapped_form_spec = cst.Call(
            func=cst.Name("enable_deprecated_cascading_elements"),
            args=[
                cst.Arg(value=form_spec, keyword=cst.Name("wrapped_form_spec")),
                cst.Arg(
                    value=cst.List(
                        [
                            cst.Element(
                                create_data_conversion_data_class(key, value, use_form_spec)
                            )
                            for key, (value, use_form_spec) in args_for_legacy_wrapper.items()
                        ]
                    ),
                    keyword=cst.Name("special_value_mapping"),
                ),
            ],
        )
        return wrapped_form_spec

    def _make_single_choice(self, old: cst.Call) -> cst.Call:
        new_args: list[cst.Arg] = []
        for arg in old.args:
            assert arg.keyword, "All args should have a keyword"
            match arg.keyword.value:
                case "choices":
                    element_args: list[cst.Element] = []

                    if isinstance(arg.value, (cst.Call, cst.Name)):
                        warnings.append(
                            f"'choices' field in DropdownChoice is not a list: {cst.Module([]).code_for_node(arg)}"
                        )
                        new_args.append(cst.Arg(arg.value, keyword=cst.Name("elements")))
                        continue

                    for el in cst.ensure_type(arg.value, cst.List).elements:
                        tuple_elements: Sequence[cst.BaseElement] = cst.ensure_type(
                            el.value, cst.Tuple
                        ).elements
                        if len(tuple_elements) != 2:
                            raise Exception("Invalid number of elements in dropdown choice")
                        element_args.append(
                            cst.Element(
                                cst.Call(
                                    func=cst.Name("SingleChoiceElement"),
                                    args=(
                                        cst.Arg(
                                            tuple_elements[0].value,
                                            cst.Name("name"),
                                        ),
                                        cst.Arg(
                                            cst.Call(
                                                func=cst.Name("Title"),
                                                args=cst.ensure_type(
                                                    tuple_elements[1].value, cst.Call
                                                ).args,
                                            ),
                                            cst.Name("title"),
                                        ),
                                    ),
                                ),
                            )
                        )
                    new_args.append(
                        cst.Arg(
                            cst.List(element_args),
                            cst.Name("elements"),
                        )
                    )
                case "no_preselect_title":
                    if isinstance(arg.value, cst.SimpleString):
                        message_args: Sequence[cst.Arg] = [cst.Arg(arg.value)]
                    else:
                        message_args = cst.ensure_type(arg.value, cst.Call).args

                    new_args.append(
                        cst.Arg(
                            cst.Call(func=cst.Name("Message"), args=message_args),
                            cst.Name("no_elements_text"),
                        )
                    )
                    pass
                case _:
                    new_args.append(arg)
        return cst.Call(func=cst.Name("SingleChoice"), args=new_args)

    def _make_string(self, old: cst.Call) -> cst.Call:
        args = self._replace_allow_empty_args(old.args, "Text field can not be empty")
        args = self._drop_args(args, ["size"])
        return cst.Call(func=cst.Name("String"), args=args)

    def _make_fixed_value(self, old: cst.Call) -> cst.Call:
        new_args: list[cst.Arg] = []
        for arg in old.args:
            assert arg.keyword, "All args should have a keyword"
            match arg.keyword.value:
                case "totext":
                    label_args: Sequence[cst.Arg]
                    if isinstance(arg.value, cst.SimpleString):
                        label_args = [cst.Arg(arg.value)]
                    else:
                        label_args = cst.ensure_type(arg.value, cst.Call).args
                    new_args.append(
                        cst.Arg(
                            cst.Call(func=cst.Name("Label"), args=label_args),
                            cst.Name("label"),
                        )
                    )
                case _:
                    new_args.append(arg)
        return cst.Call(func=cst.Name("FixedValue"), args=new_args)

    def _make_boolean_choice(self, old: cst.Call) -> cst.Call:
        return cst.Call(func=cst.Name("BooleanChoice"), args=old.args)

    def _make_time_span(self, old: cst.Call) -> cst.Call:
        return cst.Call(func=cst.Name("TimeSpan"), args=old.args)

    def _make_age(self, old: cst.Call) -> cst.Call:
        new_args: list[cst.Arg] = []
        magnitude_map = {
            "not_supported": "TimeMagnitude.MILLISECOND",
            "seconds": "TimeMagnitude.SECOND",
            "minutes": "TimeMagnitude.MINUTE",
            "hours": "TimeMagnitude.HOUR",
            "days": "TimeMagnitude.DAY",
        }

        minvalue: None | str = None
        maxvalue: None | str = None
        for arg in old.args:
            assert arg.keyword, "All args should have a keyword"
            match arg.keyword.value:
                case "display":
                    used_magnitudes = []
                    for element in cst.ensure_type(arg.value, cst.List).elements:
                        used_magnitudes.append(
                            magnitude_map[
                                cst.ensure_type(element.value, cst.SimpleString).value.strip('"')
                            ]
                        )
                    new_args.append(
                        cst.Arg(
                            cst.parse_expression(f"[{', '.join(used_magnitudes)}]"),
                            cst.Name("displayed_magnitudes"),
                        )
                    )
                case "maxvalue":
                    maxvalue = cst.ensure_type(arg.value, cst.Integer).value
                case "minvalue":
                    minvalue = cst.ensure_type(arg.value, cst.Integer).value

        if minvalue is not None or maxvalue is not None:
            expression = f"[validators.NumberInRange({minvalue}, {maxvalue})]"
            new_args.append(
                cst.Arg(
                    cst.parse_expression(expression),
                    cst.Name("custom_validate"),
                )
            )

        return cst.Call(func=cst.Name("Age"), args=new_args)

    def _make_password(self, old: cst.Call) -> cst.Call:
        old_args = self._replace_allow_empty_args(old.args, "Password field can not be empty")
        old_args = self._drop_args(old_args, ["size"])
        return cst.Call(
            func=cst.Name("Password"),
            args=(
                *old_args,
                cst.Arg(cst.Name("migrate_to_password"), cst.Name("migrate")),
            ),
        )

    def _make_absolute_date(self, old: cst.Call) -> cst.Call:
        new_args: list[cst.Arg] = []
        format_expression = "DateTimeFormat.DATE"
        for arg in old.args:
            assert arg.keyword, "All args should have a keyword"
            match arg.keyword.value:
                case "include_time":
                    format_expression = "DateTimeFormat.DATETIME"
                case "submit_form_name":
                    # obsolete
                    continue
                case "title":
                    new_args.append(arg)

        new_args.append(
            cst.Arg(
                cst.parse_expression(format_expression),
                cst.Name("use_format"),
            )
        )

        return cst.Call(func=cst.Name("AbsoluteTimestamp"), args=new_args)

    def _make_simple_levels(self, old: cst.Call) -> cst.Call:
        args = {k.value: arg.value for arg in old.args if (k := arg.keyword) is not None}
        handled_args = ["spec", "unit", "default_value", "default_levels"]
        kept_args = [
            arg for arg in old.args if (k := arg.keyword) is None or k.value not in handled_args
        ]

        template_args = []
        if (unit := args.get("unit")) is not None:
            template_args = [
                cst.Arg(
                    keyword=cst.Name("unit_symbol"),
                    value=cst.ensure_type(unit, cst.SimpleString),
                )
            ]

        new_args = [
            cst.Arg(
                keyword=cst.Name("level_direction"),
                value=(
                    cst.Attribute(value=cst.Name("LevelDirection"), attr=cst.Name("UPPER"))
                    if args.get("direction", "upper") == "upper"
                    else cst.Attribute(value=cst.Name("LevelDirection"), attr=cst.Name("LOWER"))
                ),
            ),
        ]

        spec = cst.ensure_type(args["spec"], cst.Name)
        match spec.value:
            case "Age":
                new_args.extend(
                    [
                        cst.Arg(
                            cst.Call(cst.Name("TimeSpan"), args=DEFAULT_TIME_SPAN_ARGS),
                            cst.Name("form_spec_template"),
                        ),
                        cst.Arg(cst.Name("migrate_to_float_simple_levels"), cst.Name("migrate")),
                        cst.Arg(
                            self._get_simple_level_prefill(args), cst.Name("prefill_fixed_levels")
                        ),
                    ]
                )
            case "Integer":
                new_args.extend(
                    [
                        cst.Arg(
                            cst.Call(cst.Name(spec.value), args=template_args),
                            cst.Name("form_spec_template"),
                        ),
                        cst.Arg(cst.Name("migrate_to_integer_simple_levels"), cst.Name("migrate")),
                        cst.Arg(
                            self._get_simple_level_prefill(args, float_type=False),
                            cst.Name("prefill_fixed_levels"),
                        ),
                    ]
                )
            case "Float":
                new_args.extend(
                    [
                        cst.Arg(
                            cst.Call(cst.Name(spec.value), args=template_args),
                            cst.Name("form_spec_template"),
                        ),
                        cst.Arg(cst.Name("migrate_to_float_simple_levels"), cst.Name("migrate")),
                        cst.Arg(
                            self._get_simple_level_prefill(args), cst.Name("prefill_fixed_levels")
                        ),
                    ]
                )
            case "Percentage":
                new_args.extend(
                    [
                        cst.Arg(cst.Call(cst.Name(spec.value)), cst.Name("form_spec_template")),
                        cst.Arg(cst.Name("migrate_to_float_simple_levels"), cst.Name("migrate")),
                        cst.Arg(
                            self._get_simple_level_prefill(args), cst.Name("prefill_fixed_levels")
                        ),
                    ]
                )

        return cst.Call(func=cst.Name("SimpleLevels"), args=(*kept_args, *new_args))

    def _get_simple_level_prefill(
        self, args: Mapping[str, cst.BaseExpression], float_type: bool = True
    ) -> cst.Call:
        if (default_value := args.get("default_value")) is not None:
            return cst.Call(
                cst.Name("DefaultValue"),
                args=[cst.Arg(cst.ensure_type(default_value, cst.Tuple))],
            )
        if (default_levels := args.get("default_levels")) is not None:
            return cst.Call(
                cst.Name("DefaultValue"),
                args=[cst.Arg(cst.ensure_type(default_levels, cst.Tuple))],
            )

        elements = (
            [cst.Element(cst.Float("0.0")), cst.Element(cst.Float("0.0"))]
            if float_type
            else [cst.Element(cst.Integer("0")), cst.Element(cst.Integer("0"))]
        )
        return cst.Call(
            cst.Name("InputHint"),
            args=([cst.Arg(cst.Tuple(elements=elements))]),
        )


class RegistrationTransformer(cst.CSTTransformer):
    def leave_SimpleStatementLine(
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.SimpleStatementLine | cst.FlattenSentinel:
        if not (
            isinstance(expr := original_node.body[0], cst.Expr)
            and isinstance(call := expr.value, cst.Call)
            and isinstance(func := call.func, cst.Attribute)
            and isinstance(func.value, cst.Name)
            and func.value.value == "rulespec_registry"
            and func.attr.value == "register"
        ):
            return updated_node
        assert isinstance(old_ruleset := call.args[0].value, cst.Call)
        return self._make_ruleset_plugin(old_ruleset)

    def _make_ruleset_plugin(self, old_ruleset: cst.Call) -> cst.SimpleStatementLine:
        if (rule_type := cst.ensure_type(old_ruleset.func, cst.Name).value) in {
            "CheckParameterRulespecWithItem",
            "CheckParameterRulespecWithoutItem",
        }:
            return self._construct_check_parameters(old_ruleset.args)

        args = {k.value: arg.value for arg in old_ruleset.args if (k := arg.keyword) is not None}
        group = (
            name.value
            if isinstance(name := args["name"], cst.SimpleString)
            else cst.ensure_type(
                cst.ensure_type(args["name"], cst.Call).func, cst.Attribute
            ).attr.value
        )
        if rule_type == "HostRulespec" and group == "SpecialAgents":
            return self._construct_special_agent(old_ruleset.args)
        if rule_type == "HostRulespec" and group == "ActiveChecks":
            return self._construct_active_check(old_ruleset.args)
        if rule_type == "HostRulespec":
            # a guess, but most of the time it's a discovery rule
            return self._construct_discovery_parameters(group, old_ruleset.args)

        print(f"not yet implemented rulespec type: {rule_type}", file=sys.stderr)
        return cst.SimpleStatementLine(
            (
                cst.Assign(
                    targets=(cst.AssignTarget(cst.Name("None")),),  # make sure this fails...
                    value=old_ruleset,
                ),
            )
        )

    def _construct_check_parameters(self, old: Sequence[cst.Arg]) -> cst.SimpleStatementLine:
        args = {k.value: arg.value for arg in old if (k := arg.keyword) is not None}
        name = self._extract_string(args["check_group_name"])
        form_spec = args["parameter_valuespec"]

        return cst.SimpleStatementLine(
            (
                cst.Assign(
                    targets=(cst.AssignTarget(cst.Name(f"rule_spec_{name}")),),
                    value=cst.Call(
                        func=cst.Name("CheckParameters"),
                        args=(
                            cst.Arg(cst.SimpleString(f'"{name}"'), cst.Name("name")),
                            *_extract("title", old),
                            cst.Arg(cst.Name("Topic"), cst.Name("topic")),
                            cst.Arg(form_spec, cst.Name("parameter_form")),
                            cst.Arg(
                                self._make_condition(args.get("item_spec")),
                                cst.Name("condition"),
                            ),
                        ),
                    ),
                ),
            )
        )

    def _construct_discovery_parameters(
        self, name: str, old: Sequence[cst.Arg]
    ) -> cst.SimpleStatementLine:
        args = {k.value: arg.value for arg in old if (k := arg.keyword) is not None}
        form_spec = args["valuespec"]
        name = name.strip('"')

        return cst.SimpleStatementLine(
            (
                cst.Assign(
                    targets=(cst.AssignTarget(cst.Name(f"rule_spec_{name}")),),
                    value=cst.Call(
                        func=cst.Name("DiscoveryParameters"),
                        args=(
                            cst.Arg(cst.SimpleString(f'"{name}"'), cst.Name("name")),
                            *_extract("title", old),
                            cst.Arg(cst.Name("Topic"), cst.Name("topic")),
                            cst.Arg(form_spec, cst.Name("parameter_form")),
                        ),
                    ),
                ),
            )
        )

    def _construct_active_check(self, old: Sequence[cst.Arg]) -> cst.SimpleStatementLine:
        args = {k.value: arg.value for arg in old if (k := arg.keyword) is not None}
        name = self._extract_string(cst.ensure_type(args["name"], cst.Call).args[0].value)
        form_spec = args["valuespec"]

        return cst.SimpleStatementLine(
            (
                cst.Assign(
                    targets=(cst.AssignTarget(cst.Name(f"rule_spec_active_check_{name}")),),
                    value=cst.Call(
                        func=cst.Name("ActiveCheck"),
                        args=(
                            cst.Arg(cst.SimpleString(f'"{name}"'), cst.Name("name")),
                            *_extract("title", old),
                            cst.Arg(cst.Name("Topic"), cst.Name("topic")),
                            cst.Arg(form_spec, cst.Name("parameter_form")),
                        ),
                    ),
                ),
            )
        )

    def _construct_special_agent(self, old: Sequence[cst.Arg]) -> cst.SimpleStatementLine:
        args = {k.value: arg.value for arg in old if (k := arg.keyword) is not None}
        name = self._extract_string(cst.ensure_type(args["name"], cst.Call).args[0].value)
        form_spec = args["valuespec"]

        return cst.SimpleStatementLine(
            (
                cst.Assign(
                    targets=(cst.AssignTarget(cst.Name(f"rule_spec_special_agent_{name}")),),
                    value=cst.Call(
                        func=cst.Name("SpecialAgent"),
                        args=(
                            cst.Arg(cst.SimpleString(f'"{name}"'), cst.Name("name")),
                            *_extract("title", old),
                            cst.Arg(cst.Name("Topic"), cst.Name("topic")),
                            cst.Arg(form_spec, cst.Name("parameter_form")),
                        ),
                    ),
                ),
            )
        )

    @staticmethod
    def _extract_string(old_arg: cst.BaseExpression) -> str:
        return cst.ensure_type(old_arg, cst.SimpleString).value[1:-1]

    @staticmethod
    def _make_condition(old_arg: cst.BaseExpression | None) -> cst.Call:
        if old_arg is None:
            return cst.Call(func=cst.Name("HostCondition"), args=())

        return cst.Call(
            func=cst.Name("HostAndItemCondition"),
            args=(
                cst.Arg(
                    # not quite right, we need to move the title kwarg to the HostAndItemCondition
                    old_arg.body if isinstance(old_arg, cst.Lambda) else old_arg,
                    cst.Name("item_form"),
                ),
            ),
        )


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Debug mode: let Python exceptions come through"
    )

    parser.add_argument(
        "-e",
        "--use_unstable",
        action="store_true",
        help="FOR INTERNAL USE ONLY. Use unstable python API. This includes the Extended versions of FormSpecs "
        "and helper functions which are not part of the public API. Use with care, will break without warning!",
    )

    parser.add_argument(
        "--files",
        help="Legacy plug-ins to rewrite (inplace)",
        nargs="+",
    )

    parser.add_argument(
        "--transformers",
        help="Transformers to use (import/value/registry). Default uses all",
        nargs="+",
    )

    return parser.parse_args(argv)


cs_tree = None


def _transform_file(content: str) -> str:
    global cs_tree
    # cs_tree = MetadataWrapper(cst.parse_module(content))
    cs_tree = cst.parse_module(content)
    for transformer in used_transformers:
        if transformer == Transformers.IMPORTS:
            cs_tree = cs_tree.visit(ImportsTransformer())
        elif transformer == Transformers.VALUESPECS:
            cs_tree = cs_tree.visit(VSTransformer())
        elif transformer == Transformers.REGISTRATION:
            cs_tree = cs_tree.visit(RegistrationTransformer())
        else:
            raise ValueError(f"Unknown transformer: {transformer}")
    return cs_tree.code


def _try_to_run(*command_items: object) -> None:
    try:
        subprocess.check_call([str(o) for o in command_items])
    except subprocess.CalledProcessError as exc:
        print(f"tried to run {command_items[0]!r}, but: {exc}", file=sys.stderr)


def main(argv: Sequence[str]) -> None:
    args = parse_arguments(argv)
    global use_unstable_api
    use_unstable_api = args.use_unstable

    if args.transformers:
        used_transformers.clear()
        used_transformers.update({Transformers(t) for t in args.transformers})

    for file in (Path(p) for p in args.files):
        try:
            file.write_text(_transform_file(file.read_text()))
            print(f"\nTransformed {file}")
            if warnings:
                print(
                    "  WARNINGS:\n  - ############# WARNING: ",
                    "\n  - ############# WARNING: ".join(warnings),
                )
            warnings.clear()
        except Exception as exc:
            print(f"failed {file}: {exc}")
            if args.debug:
                raise

    _try_to_run("scripts/run-uvenv", "ruff", "check", "--fix", *args.files)
    _try_to_run("scripts/run-uvenv", "ruff", "check", "--select", "I", "--fix", *args.files)
    _try_to_run("scripts/run-uvenv", "ruff", "format", *args.files)


if __name__ == "__main__":
    main(sys.argv[1:])
