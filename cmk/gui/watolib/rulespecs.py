#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The rulespecs are the ruleset specifications registered to Setup."""

import abc
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast, Literal, NamedTuple

import cmk.ccc.plugin_registry
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.version import Edition, edition, mark_edition_only

from cmk.utils import paths
from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.config import active_config
from cmk.gui.form_specs.converter import Tuple as FSTuple
from cmk.gui.form_specs.private import SingleChoiceElementExtended, SingleChoiceExtended
from cmk.gui.form_specs.private.time_specific import TimeSpecific
from cmk.gui.global_config import get_global_config
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.type_defs import HTTPVariables
from cmk.gui.utils.html import HTML
from cmk.gui.utils.urls import (
    DocReference,
    makeuri,
    makeuri_contextless_rulespec_group,
)
from cmk.gui.valuespec import (
    DEF_VALUE,
    Dictionary,
    DropdownChoice,
    DropdownChoiceEntries,
    ElementSelection,
    FixedValue,
    JSONValue,
    ListOf,
    OptionalDropdownChoice,
    Transparent,
    Tuple,
    ValueSpec,
    ValueSpecDefault,
    ValueSpecHelp,
    ValueSpecText,
    ValueSpecValidateFunc,
)

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import DefaultValue, FormSpec, SingleChoice, SingleChoiceElement
from cmk.rulesets.v1.form_specs import FixedValue as FSFixedValue

from .check_mk_automations import get_check_information_cached
from .main_menu import ABCMainModule, MainModuleRegistry
from .timeperiods import TimeperiodSelection

MatchType = Literal["first", "all", "list", "dict", "varies"]


_LOCAL_ROOT = str(paths.local_root)  # `Path`s are slow.


class AllowAll:
    def is_visible(self, _rulespec_name: str) -> bool:
        return True


@dataclass(frozen=True)
class RulespecAllowList:
    visible_rulespecs: set[str] = field(default_factory=set)

    @classmethod
    def from_config(cls) -> "RulespecAllowList":
        global_config = get_global_config()
        model = global_config.rulespec_allow_list
        visible_rulespecs = set()
        for group in model.rule_groups:
            _prefix = "" if group.type_ is None else f"{group.type_.value}:"
            names = {f"{_prefix}{name}" for name in group.rule_names}
            visible_rulespecs.update(names)
        return cls(visible_rulespecs=visible_rulespecs)

    def is_visible(self, rulespec_name: str) -> bool:
        return rulespec_name in self.visible_rulespecs


def get_rulespec_allow_list() -> RulespecAllowList | AllowAll:
    if edition(paths.omd_root) is not Edition.CSE:
        return AllowAll()
    return RulespecAllowList.from_config()


class RulespecBaseGroup(abc.ABC):
    """Base class for all rulespec group types"""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique internal key of this group"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def title(self) -> str:
        """Human readable title of this group"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def help(self) -> str | None:
        """Helpful description of this group"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def choice_title(self) -> str:
        raise NotImplementedError()


class RulespecGroup(RulespecBaseGroup):
    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique internal key of this group"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def title(self) -> str:
        """Human readable title of this group"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def help(self) -> str:
        """Helpful description of this group"""
        raise NotImplementedError()

    @property
    def doc_references(self) -> dict[DocReference, str]:
        """Doc references of this group and their titles"""
        return {}

    @property
    def choice_title(self) -> str:
        return self.title


class RulespecSubGroup(RulespecBaseGroup, abc.ABC):
    @property
    @abc.abstractmethod
    def main_group(self) -> type[RulespecGroup]:
        """A reference to the main group class"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def sub_group_name(self) -> str:
        """The internal name of the sub group"""
        raise NotImplementedError()

    @property
    def name(self) -> str:
        return "/".join([self.main_group().name, self.sub_group_name])

    @property
    def choice_title(self) -> str:
        return "&nbsp;&nbsp;⌙ %s" % self.title

    @property
    def help(self) -> None:
        return None  # Sub groups currently have no help text


class RulespecGroupRegistry(cmk.ccc.plugin_registry.Registry[type[RulespecBaseGroup]]):
    def __init__(self) -> None:
        super().__init__()
        self._main_groups: list[type[RulespecGroup]] = []
        self._sub_groups_by_main_group: dict[type[RulespecGroup], list[type[RulespecSubGroup]]] = {}

    def plugin_name(self, instance: type[RulespecBaseGroup]) -> str:
        return instance().name

    def registration_hook(self, instance: type[RulespecBaseGroup]) -> None:
        if issubclass(instance, RulespecSubGroup):
            self._sub_groups_by_main_group.setdefault(instance().main_group, []).append(instance)
        elif issubclass(instance, RulespecGroup):
            self._main_groups.append(instance)
        else:
            raise TypeError('Got invalid type "%s"' % instance.__name__)

    def get_group_choices(self) -> list[tuple[str, str]]:
        """Returns all available ruleset groups to be used in dropdown choices"""
        choices: list[tuple[str, str]] = []

        main_groups = [g_class() for g_class in self.get_main_groups()]
        for main_group in sorted(main_groups, key=lambda g: g.title):
            choices.append((main_group.name, main_group.choice_title))

            sub_groups = [g_class() for g_class in self._get_sub_groups_of(main_group.__class__)]
            for sub_group in sorted(sub_groups, key=lambda g: g.title):
                choices.append((sub_group.name, sub_group.choice_title))

        return choices

    def get_main_groups(self) -> list[type[RulespecGroup]]:
        return self._main_groups

    def _get_sub_groups_of(self, main_group: type[RulespecGroup]) -> list[type[RulespecSubGroup]]:
        return self._sub_groups_by_main_group.get(main_group, [])

    def get_matching_group_names(self, group_name: str) -> list[str]:
        """Get either the main group and all sub groups of a matching main group or the matching sub group"""
        for group_class in self._main_groups:
            if group_class().name == group_name:
                return [group_name] + [
                    g_class().name for g_class in self._get_sub_groups_of(group_class)
                ]

        return [name for name in self._entries if name == group_name]

    def get_host_rulespec_group_names(self, for_host: bool) -> list[str]:
        """Collect all rulesets that apply to hosts, except those specifying new active or static
        checks and except all server monitoring rulesets. Usually, the needed context for service
        monitoring rulesets is not given when the host rulesets are requested."""
        names: list[str] = []
        hidden_groups: tuple[str, ...] = ("static", "activechecks")
        if for_host:
            hidden_groups = hidden_groups + ("monconf",)
        hidden_main_groups = ("host_monconf", "monconf", "agents", "agent")
        for g_class in self.values():
            group = g_class()
            if isinstance(group, RulespecSubGroup) and group.main_group().name in hidden_groups:
                continue

            if (
                not isinstance(group, RulespecSubGroup)
                and group.name in hidden_groups
                or group.name in hidden_main_groups
            ):
                continue

            names.append(group.name)
        return names


rulespec_group_registry = RulespecGroupRegistry()


def get_rulegroup(group_name: str) -> RulespecBaseGroup:
    try:
        group_class = rulespec_group_registry[group_name]
    except KeyError:
        group_class = _get_legacy_rulespec_group_class(group_name, group_title=None, help_text=None)
        rulespec_group_registry.register(group_class)
    # Pylint does not detect the subclassing in LegacyRulespecSubGroup correctly. Disable the check here :(
    return group_class()


def _get_legacy_rulespec_group_class(
    group_name: str, group_title: str | None, help_text: str | None
) -> type[RulespecBaseGroup]:
    if "/" in group_name:
        main_group_name, sub_group_name = group_name.split("/", 1)
        sub_group_title = group_title or sub_group_name

        # group_name could contain non alphanumeric characters
        internal_sub_group_name = re.sub("[^a-zA-Z]", "", sub_group_name)

        main_group_class = get_rulegroup(main_group_name).__class__
        return cast(
            type[RulespecSubGroup],
            type(
                "LegacyRulespecSubGroup%s" % internal_sub_group_name.title(),
                (RulespecSubGroup,),
                {
                    "main_group": main_group_class,
                    "sub_group_name": internal_sub_group_name.lower(),
                    "title": sub_group_title,
                },
            ),
        )

    group_title = group_title or group_name

    return cast(
        type[RulespecGroup],
        type(
            "LegacyRulespecGroup%s" % group_name.title(),
            (RulespecGroup,),
            {
                "name": group_name,
                "title": group_title,
                "help": help_text,
            },
        ),
    )


def _validate_function_args(arg_infos: list[tuple[Any, bool, bool]], hint: str) -> None:
    for idx, (arg, is_callable, none_allowed) in enumerate(arg_infos):
        if not none_allowed and arg is None:
            raise MKGeneralException(_("Invalid None argument at for %s idx %d") % (hint, idx))
        if arg is not None and callable(arg) != is_callable:
            raise MKGeneralException(
                _("Invalid expected callable for %s at idx %d: %r") % (hint, idx, arg)
            )


class FormSpecDefinition(NamedTuple):
    value: Callable[[], FormSpec]
    item: Callable[[], FormSpec] | None


class FormSpecNotImplementedError(Exception):
    pass


class Rulespec(abc.ABC):
    NO_FACTORY_DEFAULT: list = []
    # This option has the same effect as `NO_FACTORY_DEFAULT`. It's often used in MKPs.
    FACTORY_DEFAULT_UNUSED: list = []

    def __init__(
        self,
        *,
        name: str,
        group: type[RulespecBaseGroup],
        title: Callable[[], str] | None,
        valuespec: Callable[[], ValueSpec],
        match_type: MatchType,
        item_type: Literal["service", "item"] | None,
        # WATCH OUT: passing a Callable[[], Transform] will not work (see the
        # isinstance check in the item_spec property)!
        item_spec: Callable[[], ValueSpec] | None,
        item_name: Callable[[], str] | None,
        item_help: Callable[[], str] | None,
        is_optional: bool,
        is_deprecated: bool,
        deprecation_planned: bool,
        is_cloud_and_managed_edition_only: bool,
        is_for_services: bool,
        is_binary_ruleset: bool,  # unused
        factory_default: Any,
        help_func: Callable[[], str] | None,
        doc_references: dict[DocReference, str] | None,
        form_spec_definition: FormSpecDefinition | None = None,
    ) -> None:
        super().__init__()

        arg_infos: list[tuple[Any, bool, bool]] = [
            # (arg, is_callable, none_allowed)
            (name, False, False),
            (group, True, False),  # A class -> callable
            (title, True, True),
            (valuespec, True, False),
            (match_type, False, False),
            (item_type, False, True),
            (item_spec, True, True),
            (item_name, True, True),
            (item_help, True, True),
            (is_optional, False, False),
            (is_deprecated, False, False),
            (deprecation_planned, False, False),
            (is_for_services, False, False),
            (is_binary_ruleset, False, False),
            (factory_default, False, True),
            (help_func, True, True),
            (form_spec_definition, False, True),
        ]
        _validate_function_args(arg_infos, name)

        self._name = name
        self._group = group
        self._title = title
        self._valuespec = valuespec
        self._match_type = match_type
        self._item_type = item_type
        self._item_spec = item_spec
        self._item_name = item_name
        self._item_help = item_help
        self._is_optional = is_optional
        self._is_deprecated = is_deprecated
        self._deprecation_planned = deprecation_planned
        self._is_cloud_and_managed_edition_only = is_cloud_and_managed_edition_only
        self._is_binary_ruleset = is_binary_ruleset
        self._is_for_services = is_for_services
        self._factory_default = factory_default
        self._help = help_func
        self._doc_references = doc_references
        self._form_spec_definition = form_spec_definition

    @property
    def name(self) -> str:
        return self._name

    @property
    def group(self) -> type[RulespecBaseGroup]:
        return self._group

    @property
    def valuespec(self) -> ValueSpec:
        return self._valuespec()

    @property
    def form_spec(self) -> FormSpec:
        if self._form_spec_definition is None:
            raise FormSpecNotImplementedError()
        return self._form_spec_definition.value()

    @property
    def item_form_spec(self) -> FormSpec | None:
        if self._form_spec_definition is None:
            raise FormSpecNotImplementedError()
        if self._form_spec_definition.item is None:
            return None
        return self._form_spec_definition.item()

    @property
    def title(self) -> str | None:
        plain_title = self._title() if self._title else self.valuespec.title()
        if plain_title is None:
            return None
        if self._is_deprecated:
            return "{}: {}".format(_("Deprecated"), plain_title)
        if self._is_cloud_and_managed_edition_only:
            return mark_edition_only(plain_title, [Edition.CME, Edition.CCE])
        return plain_title

    @property
    def help(self) -> None | str | HTML:
        if self._help:
            return self._help()

        return self.valuespec.help()

    @property
    def is_for_services(self) -> bool:
        return self._is_for_services

    @property
    def is_binary_ruleset(self) -> bool:
        return self._is_binary_ruleset

    @property
    def item_type(self) -> Literal["service", "item"] | None:
        return self._item_type

    @property
    def item_spec(self) -> ValueSpec | None:
        if self._item_spec:
            return self._item_spec()

        return None

    @property
    def item_name(self) -> str | None:
        if self._item_name:
            return self._item_name()

        if self._item_spec:
            return self._item_spec().title() or _("Item")

        if self.item_type == "service":
            return _("Service")

        return None

    @property
    def item_help(self) -> None | str | HTML:
        if self._item_help:
            return self._item_help()

        if self._item_spec:
            return self._item_spec().help()

        return None

    @property
    def item_enum(self) -> DropdownChoiceEntries | None:
        item_spec = self.item_spec
        if item_spec is None:
            return None

        if isinstance(item_spec, DropdownChoice | OptionalDropdownChoice):
            return item_spec.choices()

        return None

    @property
    def group_name(self) -> str:
        return self._group().name

    @property
    def main_group_name(self) -> str:
        return self.group_name.split("/")[0]

    @property
    def sub_group_name(self) -> str:
        return self.group_name.split("/")[1] if "/" in self.group_name else ""

    @property
    def match_type(self) -> MatchType:
        return self._match_type

    @property
    def factory_default(self) -> Any:
        return self._factory_default

    @property
    def is_optional(self) -> bool:
        return self._is_optional

    @property
    def is_deprecated(self) -> bool:
        return self._is_deprecated

    @property
    def deprecation_planned(self) -> bool:
        return self._deprecation_planned

    @property
    def is_cloud_and_managed_edition_only(self) -> bool:
        return self._is_cloud_and_managed_edition_only

    @property
    def doc_references(self) -> dict[DocReference, str]:
        """Doc references of this rulespec and their titles"""
        return self._doc_references or {}


class HostRulespec(Rulespec):
    """Base class for all rulespecs managing host rule sets with values"""

    # Required because of Rulespec.NO_FACTORY_DEFAULT
    def __init__(
        self,
        name: str,
        group: type[Any],
        valuespec: Callable[[], ValueSpec],
        title: Callable[[], str] | None = None,
        match_type: MatchType = "first",
        is_optional: bool = False,
        is_deprecated: bool = False,
        deprecation_planned: bool = False,
        is_binary_ruleset: bool = False,
        is_cloud_and_managed_edition_only: bool = False,
        factory_default: Any = Rulespec.NO_FACTORY_DEFAULT,
        help_func: Callable[[], str] | None = None,
        doc_references: dict[DocReference, str] | None = None,
        form_spec_definition: FormSpecDefinition | None = None,
    ) -> None:
        super().__init__(
            name=name,
            group=group,
            title=title,
            valuespec=valuespec,
            match_type=match_type,
            is_optional=is_optional,
            is_deprecated=is_deprecated,
            deprecation_planned=deprecation_planned,
            is_cloud_and_managed_edition_only=is_cloud_and_managed_edition_only,
            is_binary_ruleset=is_binary_ruleset,
            factory_default=factory_default,
            help_func=help_func,
            doc_references=doc_references,
            form_spec_definition=None if form_spec_definition is None else form_spec_definition,
            # Excplicit set
            is_for_services=False,
            item_type=None,
            item_name=None,
            item_spec=None,
            item_help=None,
        )


class ServiceRulespec(Rulespec):
    """Base class for all rulespecs managing service rule sets with values"""

    # Required because of Rulespec.NO_FACTORY_DEFAULT
    def __init__(
        self,
        *,
        name: str,
        group: type[RulespecBaseGroup],
        valuespec: Callable[[], ValueSpec],
        item_type: Literal["item", "service"],
        title: Callable[[], str] | None = None,
        match_type: MatchType = "first",
        item_name: Callable[[], str] | None = None,
        item_spec: Callable[[], ValueSpec] | None = None,
        item_help: Callable[[], str] | None = None,
        is_optional: bool = False,
        is_deprecated: bool = False,
        deprecation_planned: bool = False,
        is_cloud_and_managed_edition_only: bool = False,
        is_binary_ruleset: bool = False,
        factory_default: Any = Rulespec.NO_FACTORY_DEFAULT,
        help_func: Callable[[], str] | None = None,
        doc_references: dict[DocReference, str] | None = None,
        form_spec_definition: FormSpecDefinition | None = None,
    ) -> None:
        super().__init__(
            name=name,
            group=group,
            title=title,
            valuespec=valuespec,
            match_type=match_type,
            is_binary_ruleset=is_binary_ruleset,
            item_type=item_type,
            item_name=item_name,
            item_spec=item_spec,
            item_help=item_help,
            is_optional=is_optional,
            is_deprecated=is_deprecated,
            deprecation_planned=deprecation_planned,
            is_cloud_and_managed_edition_only=is_cloud_and_managed_edition_only,
            factory_default=factory_default,
            help_func=help_func,
            doc_references=doc_references,
            form_spec_definition=form_spec_definition,
            # Excplicit set
            is_for_services=True,
        )


class BinaryHostRulespec(HostRulespec):
    # Required because of Rulespec.NO_FACTORY_DEFAULT
    def __init__(
        self,
        name: str,
        group: type[RulespecBaseGroup],
        title: Callable[[], str] | None = None,
        match_type: MatchType = "first",
        is_optional: bool = False,
        is_deprecated: bool = False,
        factory_default: Any = Rulespec.NO_FACTORY_DEFAULT,
        help_func: Callable[[], str] | None = None,
        doc_references: dict[DocReference, str] | None = None,
    ) -> None:
        super().__init__(
            name=name,
            group=group,
            title=title,
            match_type=match_type,
            is_optional=is_optional,
            is_deprecated=is_deprecated,
            factory_default=factory_default,
            help_func=help_func,
            doc_references=doc_references,
            # Explicit set
            is_binary_ruleset=True,
            valuespec=self._binary_host_valuespec,
            form_spec_definition=FormSpecDefinition(self._binary_host_form_spec, None),
        )

    def _binary_host_valuespec(self) -> ValueSpec:
        return DropdownChoice(
            choices=[
                (True, _("Positive match (Add matching hosts to the set)")),
                (False, _("Negative match (Exclude matching hosts from the set)")),
            ],
            default_value=True,
        )

    def _binary_host_form_spec(self) -> SingleChoiceExtended:
        return SingleChoiceExtended[bool](
            elements=[
                SingleChoiceElementExtended[bool](
                    name=True, title=Title("Positive match (Add matching hosts to the set)")
                ),
                SingleChoiceElementExtended[bool](
                    name=False, title=Title("Negative match (Exclude matching hosts from the set)")
                ),
            ],
            prefill=DefaultValue(True),
        )


class BinaryServiceRulespec(ServiceRulespec):
    # Required because of Rulespec.NO_FACTORY_DEFAULT
    def __init__(
        self,
        name: str,
        group: type[RulespecBaseGroup],
        title: Callable[[], str] | None = None,
        match_type: MatchType = "first",
        item_type: Literal["item", "service"] = "service",
        item_name: Callable[[], str] | None = None,
        item_spec: Callable[[], ValueSpec] | None = None,
        item_help: Callable[[], str] | None = None,
        is_optional: bool = False,
        is_deprecated: bool = False,
        factory_default: Any = Rulespec.NO_FACTORY_DEFAULT,
        help_func: Callable[[], str] | None = None,
        doc_references: dict[DocReference, str] | None = None,
    ) -> None:
        super().__init__(
            name=name,
            group=group,
            title=title,
            match_type=match_type,
            is_optional=is_optional,
            is_deprecated=is_deprecated,
            item_type=item_type,
            item_spec=item_spec,
            item_name=item_name,
            item_help=item_help,
            factory_default=factory_default,
            help_func=help_func,
            doc_references=doc_references,
            # Explicit set
            is_binary_ruleset=True,
            valuespec=self._binary_service_valuespec,
            form_spec_definition=FormSpecDefinition(self._binary_service_form_spec, None),
        )

    def _binary_service_valuespec(self) -> ValueSpec:
        return DropdownChoice(
            choices=[
                (True, _("Positive match (Add matching services to the set)")),
                (False, _("Negative match (Exclude matching services from the set)")),
            ],
            default_value=True,
        )

    def _binary_service_form_spec(self) -> SingleChoiceExtended:
        return SingleChoiceExtended[bool](
            elements=[
                SingleChoiceElementExtended[bool](
                    name=True, title=Title("Positive match (Add services hosts to the set)")
                ),
                SingleChoiceElementExtended[bool](
                    name=False,
                    title=Title("Negative match (Exclude matching services from the set)"),
                ),
            ],
            prefill=DefaultValue(True),
        )


def _get_manual_check_parameter_rulespec_instance(
    group: type[Any],
    check_group_name: str,
    title: Callable[[], str] | None = None,
    parameter_valuespec: Callable[[], ValueSpec] | None = None,
    item_spec: Callable[[], ValueSpec] | None = None,
    is_optional: bool = False,
    is_deprecated: bool = False,
    is_cloud_and_managed_edition_only: bool = False,
    form_spec_definition: FormSpecDefinition | None = None,
) -> "ManualCheckParameterRulespec":
    # There may be no RulespecGroup declaration for the static checks.
    # Create some based on the regular check groups (which should have a definition)
    try:
        subgroup_key = "static/" + group().sub_group_name
        checkparams_static_sub_group_class = rulespec_group_registry[subgroup_key]
    except KeyError:
        group_instance = group()
        checkparams_static_sub_group_class = type(
            "%sStatic" % group_instance.__class__.__name__,
            (group_instance.__class__,),
            {
                "main_group": RulespecGroupEnforcedServices,
            },
        )

    return ManualCheckParameterRulespec(
        group=checkparams_static_sub_group_class,
        check_group_name=check_group_name,
        title=title,
        parameter_valuespec=parameter_valuespec,
        item_spec=item_spec,
        is_optional=is_optional,
        is_deprecated=is_deprecated,
        is_cloud_and_managed_edition_only=is_cloud_and_managed_edition_only,
        form_spec_definition=form_spec_definition,
    )


class RulespecGroupEnforcedServices(RulespecGroup):
    @property
    def name(self) -> str:
        return "static"

    @property
    def title(self) -> str:
        return _("Enforced services")

    @property
    def help(self):
        return _(
            "Rules to set up [wato_services#enforced_services|enforced services]. Services set "
            "up in this way do not depend on the service discovery. This is useful if you want "
            "to enforce compliance with a specific guideline. You can for example ensure that "
            "a certain Windows service is always present on a host."
        )


class CheckParameterRulespecWithItem(ServiceRulespec):
    """Base class for all rulespecs managing parameters for check groups with item

    These have to be named checkgroup_parameters:<name-of-checkgroup>. These
    parameters affect the discovered services only, not the manually configured
    checks."""

    # Required because of Rulespec.NO_FACTORY_DEFAULT
    def __init__(
        self,
        *,
        check_group_name: str,
        group: type[RulespecBaseGroup],
        parameter_valuespec: Callable[[], ValueSpec],
        item_spec: Callable[[], ValueSpec] | None = None,  # CMK-12228
        title: Callable[[], str] | None = None,
        match_type: MatchType | None = None,
        item_type: Literal["item", "service"] = "item",
        is_optional: bool = False,
        is_deprecated: bool = False,
        is_cloud_and_managed_edition_only: bool = False,
        factory_default: Any = Rulespec.NO_FACTORY_DEFAULT,
        create_manual_check: bool = True,
        form_spec_definition: FormSpecDefinition | None = None,
    ) -> None:
        # Mandatory keys
        self._check_group_name = check_group_name
        name = RuleGroup.CheckgroupParameters(self._check_group_name)
        self._parameter_valuespec = parameter_valuespec

        arg_infos = [
            # (arg, is_callable, none_allowed)
            (check_group_name, False, False),
            (parameter_valuespec, True, False),
            (form_spec_definition, False, True),
        ]
        _validate_function_args(arg_infos, name)

        super().__init__(
            name=name,
            group=group,
            title=title,
            item_type=item_type,
            item_spec=item_spec,
            is_optional=is_optional,
            is_deprecated=is_deprecated,
            is_cloud_and_managed_edition_only=is_cloud_and_managed_edition_only,
            # Excplicit set
            is_binary_ruleset=False,
            match_type=match_type or "first",
            valuespec=self._rulespec_valuespec,
            form_spec_definition=None
            if form_spec_definition is None
            else FormSpecDefinition(
                lambda: _wrap_form_spec_in_timeperiod_form_spec(form_spec_definition.value()),
                form_spec_definition.item,
            ),
        )

        self.manual_check_parameter_rulespec_instance = None
        if create_manual_check:
            self.manual_check_parameter_rulespec_instance = (
                _get_manual_check_parameter_rulespec_instance(
                    group=self.group,
                    check_group_name=check_group_name,
                    title=title,
                    parameter_valuespec=parameter_valuespec,
                    item_spec=item_spec,
                    is_optional=is_optional,
                    is_deprecated=is_deprecated,
                    form_spec_definition=form_spec_definition,
                )
            )

    @property
    def check_group_name(self) -> str:
        return self._check_group_name

    def _rulespec_valuespec(self) -> ValueSpec:
        return _wrap_valuespec_in_timeperiod_valuespec(self._parameter_valuespec())


class CheckParameterRulespecWithoutItem(HostRulespec):
    """Base class for all rulespecs managing parameters for check groups without item

    These have to be named checkgroup_parameters:<name-of-checkgroup>. These
    parameters affect the discovered services only, not the manually configured
    checks."""

    # Required because of Rulespec.NO_FACTORY_DEFAULT
    def __init__(
        self,
        *,
        check_group_name: str,
        group: type[RulespecBaseGroup],
        parameter_valuespec: Callable[[], ValueSpec],
        title: Callable[[], str] | None = None,
        match_type: MatchType | None = None,
        is_optional: bool = False,
        is_deprecated: bool = False,
        is_cloud_and_managed_edition_only: bool = False,
        factory_default: Any = Rulespec.NO_FACTORY_DEFAULT,
        create_manual_check: bool = True,
        form_spec_definition: FormSpecDefinition | None = None,
    ):
        self._check_group_name = check_group_name
        name = "checkgroup_parameters:%s" % self._check_group_name
        self._parameter_valuespec = parameter_valuespec

        arg_infos = [
            # (arg, is_callable, none_allowed)
            (check_group_name, False, False),
            (parameter_valuespec, True, False),
        ]
        _validate_function_args(arg_infos, name)

        super().__init__(
            group=group,
            title=title,
            is_optional=is_optional,
            is_deprecated=is_deprecated,
            is_cloud_and_managed_edition_only=is_cloud_and_managed_edition_only,
            # Excplicit set
            name=name,
            is_binary_ruleset=False,
            match_type=match_type or "first",
            valuespec=self._rulespec_valuespec,
            form_spec_definition=None
            if form_spec_definition is None
            else FormSpecDefinition(
                lambda: _wrap_form_spec_in_timeperiod_form_spec(form_spec_definition.value()), None
            ),
        )

        self.manual_check_parameter_rulespec_instance = None
        if create_manual_check:
            self.manual_check_parameter_rulespec_instance = (
                _get_manual_check_parameter_rulespec_instance(
                    group=self.group,
                    check_group_name=check_group_name,
                    title=title,
                    parameter_valuespec=parameter_valuespec,
                    is_optional=is_optional,
                    is_deprecated=is_deprecated,
                    form_spec_definition=form_spec_definition,
                )
            )

    @property
    def check_group_name(self) -> str:
        return self._check_group_name

    def _rulespec_valuespec(self) -> ValueSpec:
        return _wrap_valuespec_in_timeperiod_valuespec(self._parameter_valuespec())


def _wrap_valuespec_in_timeperiod_valuespec(valuespec: ValueSpec) -> ValueSpec:
    """Enclose the parameter valuespec with a TimeperiodValuespec.
    The given valuespec will be transformed to a list of valuespecs,
    whereas each element can be set to a specific timeperiod.
    """
    if isinstance(valuespec, TimeperiodValuespec):
        # Legacy check parameters registered through register_check_parameters() already
        # have their valuespec wrapped in TimeperiodValuespec.
        return valuespec
    return TimeperiodValuespec(valuespec)


def _wrap_form_spec_in_timeperiod_form_spec(form_spec: FormSpec) -> TimeSpecific:
    """Enclose the parameter form_spec with a TimeSpecific form spec.
    The given form_spec will be transformed to a list of form specs,
    whereas each element can be set to a specific timeperiod.
    """
    if isinstance(form_spec, TimeSpecific):
        # Legacy check parameters registered through register_check_parameters() already
        # have their form_spec wrapped in TimeSpecific.
        return form_spec
    return TimeSpecific(parameter_form=form_spec)


class ManualCheckParameterRulespec(HostRulespec):
    """Base class for all rulespecs managing manually configured checks

    These have to be named static_checks:<name-of-checkgroup>"""

    # Required because of Rulespec.NO_FACTORY_DEFAULT
    def __init__(
        self,
        group: type[RulespecBaseGroup],
        check_group_name: str,
        parameter_valuespec: Callable[[], ValueSpec] | None = None,
        title: Callable[[], str] | None = None,
        item_spec: Callable[[], ValueSpec] | None = None,
        is_optional: bool = False,
        is_deprecated: bool = False,
        is_cloud_and_managed_edition_only: bool = False,
        name: str | None = None,
        match_type: MatchType = "all",
        factory_default: Any = Rulespec.NO_FACTORY_DEFAULT,
        form_spec_definition: FormSpecDefinition | None = None,
    ):
        # Mandatory keys
        self._check_group_name = check_group_name
        if name is None:
            name = RuleGroup.StaticChecks(self._check_group_name)

        arg_infos = [
            # (arg, is_callable, none_allowed)
            (check_group_name, False, False),
            (parameter_valuespec, True, True),
            (item_spec, True, True),
            (form_spec_definition, False, True),
        ]
        _validate_function_args(arg_infos, name)
        super().__init__(
            group=group,
            name=name,
            title=title,
            match_type=match_type,
            is_optional=is_optional,
            is_deprecated=is_deprecated,
            factory_default=factory_default,
            is_cloud_and_managed_edition_only=is_cloud_and_managed_edition_only,
            # Explicit set
            valuespec=self._rulespec_valuespec,
            form_spec_definition=None
            if form_spec_definition is None
            else FormSpecDefinition(lambda: self._rulespec_form_spec(form_spec_definition), None),
        )

        # Optional keys
        self._parameter_valuespec = parameter_valuespec
        self._rule_value_item_valuespec = item_spec

    @property
    def check_group_name(self) -> str:
        return self._check_group_name

    def _rulespec_valuespec(self) -> ValueSpec:
        """Wraps the parameter together with the other needed valuespecs

        This should not be overridden by specific manual checks. Normally the parameter_valuespec
        is the one that should be overridden.
        """

        if self._parameter_valuespec:
            parameter_vs = _wrap_valuespec_in_timeperiod_valuespec(self._parameter_valuespec())
        else:
            parameter_vs = FixedValue(
                value=None,
                help=_("This check has no parameters."),
                totext="",
            )

        if parameter_vs.title() is None:
            parameter_vs._title = _("Parameters")

        return Tuple(
            title=parameter_vs.title(),
            elements=[
                CheckTypeGroupSelection(
                    self.check_group_name,
                    title=_("Check type"),
                    help=_("Please choose the check plug-in"),
                ),
                self._get_item_valuespec(),
                parameter_vs,
            ],
        )

    def _get_item_valuespec(self) -> ValueSpec:
        """Not used as condition, only for the rule value valuespec"""
        if self._rule_value_item_valuespec:
            return self._rule_value_item_valuespec()

        return FixedValue(
            value=None,
            totext="",
        )

    def _rulespec_form_spec(self, form_spec_definition: FormSpecDefinition) -> FormSpec:
        """Wraps the parameter together with the other needed form specs

        This should not be overridden by specific manual checks. Normally the parameter_form_spec
        is the one that should be overridden.
        """

        value_form_spec, item_form_spec = form_spec_definition

        parameter_fs: FormSpec[Any]
        if value_form_spec is None:
            parameter_fs = FSFixedValue(
                title=Title("Parameters"),
                value=None,
                help_text=Help("This check has no parameters."),
                label=Label(""),
            )
        else:
            parameter_fs = _wrap_form_spec_in_timeperiod_form_spec(value_form_spec())

        return FSTuple(
            title=parameter_fs.title,
            elements=[
                _get_check_type_group_choice(
                    title=Title("Check type"),
                    help_text=Help("Please choose the check plug-in"),
                    check_group_name=self.check_group_name,
                    debug=active_config.debug,
                ),
                self._compute_item_form_spec(item_form_spec),
                parameter_fs,
            ],
        )

    def _compute_item_form_spec(self, form_spec: Callable[[], FormSpec] | None) -> FormSpec:
        """Not used as condition, only for the rule value valuespec"""
        if form_spec is None:
            return FSFixedValue(
                value=None,
                label=Label(""),
            )
        return form_spec()


def _get_check_type_group_choice(
    title: Title, help_text: Help, check_group_name: str, *, debug: bool
) -> SingleChoice:
    checks = get_check_information_cached(debug=debug)
    elements: list[SingleChoiceElement] = []
    for checkname, check in checks.items():
        if check.get("group") == check_group_name:
            elements.append(
                SingleChoiceElement(
                    name=str(checkname),
                    title=Title(f"{checkname} - {check['title']}"),  # pylint: disable=localization-of-non-literal-string
                )
            )
    return SingleChoice(
        title=title,
        help_text=help_text,
        elements=elements,
    )


def _registration_should_be_skipped(instance: object) -> bool:
    # We used this before, but it was a performance killer. The method below is a lot faster.
    # calling_from = inspect.stack()[2].filename
    caller_file = str(sys._getframe(2).f_globals["__file__"])
    if not caller_file.startswith(_LOCAL_ROOT):
        return False

    # We are in a local file, so we can skip the registration for all
    # objects that can be specified using the new API.
    return isinstance(
        instance,
        CheckParameterRulespecWithItem
        | CheckParameterRulespecWithoutItem
        | ManualCheckParameterRulespec
        | HostRulespec
        | ServiceRulespec,
    )


def _log_ignored_local_registration(name: str) -> None:
    logger.info(f"Ignoring deprecated rulespec from local path: {name!r}")


class RulespecRegistry(cmk.ccc.plugin_registry.Registry[Rulespec]):
    def __init__(self, group_registry: RulespecGroupRegistry) -> None:
        super().__init__()
        self._group_registry = group_registry

    def plugin_name(self, instance: Rulespec) -> str:
        return instance.name

    def get_by_group(self, group_name: str) -> list[Rulespec]:
        rulespecs = []

        if group_name not in self._group_registry:
            raise KeyError()

        for rulespec_instance in self.values():
            if rulespec_instance.group_name == group_name:
                rulespecs.append(rulespec_instance)
        return rulespecs

    def get_all_groups(self):
        """Returns a list of all rulespec groups that have rules registered for

        Can not use direct rulespec_group_registry access for this, because the
        group registry does not know whether a group is registered for it"""
        return list({gc.group_name for gc in self.values()})

    def register(self, instance: Any) -> Any:
        if _registration_should_be_skipped(instance):
            _log_ignored_local_registration(instance.name)
            return instance

        # not-yet-a-type: (Rulespec) -> None
        if not isinstance(instance, Rulespec):
            raise MKGeneralException(_("Tried to register incompatible rulespec: %r") % instance)

        if isinstance(instance, CheckParameterRulespecWithItem | CheckParameterRulespecWithoutItem):
            manual_instance: Any = instance.manual_check_parameter_rulespec_instance
            if manual_instance:
                subgroup_key = "static/" + manual_instance.group().sub_group_name
                if subgroup_key not in rulespec_group_registry:
                    rulespec_group_registry.register(manual_instance.group)

                super().register(manual_instance)

        return super().register(instance)


class CheckTypeGroupSelection(ElementSelection):
    def __init__(
        self,
        checkgroup: str,
        # ElementSelection
        label: str | None = None,
        empty_text: str | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[str] = DEF_VALUE,
        validate: ValueSpecValidateFunc[str | None] | None = None,
    ):
        super().__init__(
            label=label,
            empty_text=empty_text,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self._checkgroup = checkgroup

    def get_elements(self):
        checks = get_check_information_cached(debug=active_config.debug)
        elements = {
            str(cn): "{} - {}".format(cn, c["title"])
            for (cn, c) in checks.items()
            if c.get("group") == self._checkgroup
        }
        return elements

    def value_to_html(self, value: str | None) -> ValueSpecText:
        return HTMLWriter.render_tt(value)


class TimeperiodValuespec(ValueSpec[dict[str, Any]]):
    # Used by GUI switch
    # The actual set mode
    # "0" - no timespecific settings
    # "1" - timespecific settings active
    tp_toggle_var = "tp_toggle"
    tp_current_mode = "tp_active"

    tp_default_value_key = "tp_default_value"  # Used in valuespec
    tp_values_key = "tp_values"  # Used in valuespec

    def __init__(self, valuespec: ValueSpec[dict[str, Any]]) -> None:
        super().__init__(
            title=valuespec.title(),
            help=valuespec.help(),
        )
        self._enclosed_valuespec = valuespec

    def default_value(self) -> dict[str, Any]:
        # If nothing is configured, simply return the default value of the enclosed valuespec
        return self._enclosed_valuespec.default_value()

    def render_input(self, varprefix: str, value: dict[str, Any]) -> None:
        # The display mode differs when the valuespec is activated
        vars_copy = dict(request.itervars())

        # The time period mode can be set by either the GUI switch or by the value itself
        # GUI switch overrules the information stored in the value
        if request.has_var(self.tp_toggle_var):
            is_active = self._is_switched_on()
        else:
            is_active = self.is_active(value)

        # Set the actual used mode
        html.hidden_field(self.tp_current_mode, str(int(is_active)))

        vars_copy[self.tp_toggle_var] = str(int(not is_active))

        url_vars: HTTPVariables = []
        url_vars += vars_copy.items()
        toggle_url = makeuri(request, url_vars)

        if is_active:
            value = self._get_timeperiod_value(value)
            self._get_timeperiod_valuespec().render_input(varprefix, value)
            html.buttonlink(
                toggle_url,
                _("Disable timespecific parameters"),
                class_=["toggle_timespecific_parameter"],
            )
        else:
            value = self._get_timeless_value(value)
            self._enclosed_valuespec.render_input(varprefix, value)
            html.buttonlink(
                toggle_url,
                _("Enable timespecific parameters"),
                class_=["toggle_timespecific_parameter"],
            )

    def value_to_html(self, value: dict[str, Any]) -> ValueSpecText:
        return self._get_used_valuespec(value).value_to_html(value)

    def from_html_vars(self, varprefix: str) -> dict[str, Any]:
        if request.var(self.tp_current_mode) == "1":
            # Fetch the timespecific settings
            parameters = self._get_timeperiod_valuespec().from_html_vars(varprefix)
            if parameters[self.tp_values_key]:
                return parameters

            # Fall back to enclosed valuespec data when no timeperiod is set
            return parameters[self.tp_default_value_key]

        # Fetch the data from the enclosed valuespec
        return self._enclosed_valuespec.from_html_vars(varprefix)

    def canonical_value(self) -> dict[str, Any]:
        return self._enclosed_valuespec.canonical_value()

    def _validate_value(self, value: dict[str, Any], varprefix: str) -> None:
        super()._validate_value(value, varprefix)
        self._get_used_valuespec(value).validate_value(value, varprefix)

    def validate_datatype(self, value: dict[str, Any], varprefix: str) -> None:
        super().validate_datatype(value, varprefix)
        self._get_used_valuespec(value).validate_datatype(value, varprefix)

    def _get_timeperiod_valuespec(self) -> ValueSpec[dict[str, Any]]:
        return Dictionary(
            elements=[
                (
                    self.tp_default_value_key,
                    Transparent(
                        valuespec=self._enclosed_valuespec,
                        title=_("Default parameters when no time period matches"),
                    ),
                ),
                (
                    self.tp_values_key,
                    ListOf(
                        valuespec=Tuple(
                            elements=[
                                TimeperiodSelection(
                                    title=_("Match only during time period"),
                                    help=_(
                                        "Match this rule only during times where the "
                                        "selected time period from the monitoring "
                                        "system is active."
                                    ),
                                ),
                                self._enclosed_valuespec,
                            ]
                        ),
                        title=_("Configured time period parameters"),
                    ),
                ),
            ],
            optional_keys=False,
        )

    # Checks whether the tp-mode is switched on through the gui
    def _is_switched_on(self) -> bool:
        return request.var(self.tp_toggle_var) == "1"

    # Checks whether the value itself already uses the tp-mode
    def is_active(self, value: dict[str, Any]) -> bool:
        return isinstance(value, dict) and self.tp_default_value_key in value

    # Returns simply the value or converts a plain value to a tp-value
    def _get_timeperiod_value(self, value: dict[str, Any]) -> dict[str, Any]:
        if isinstance(value, dict) and self.tp_default_value_key in value:
            return value
        return {self.tp_values_key: [], self.tp_default_value_key: value}

    # Returns simply the value or converts tp-value back to a plain value
    def _get_timeless_value(self, value: dict[str, Any]) -> Any:
        if isinstance(value, dict) and self.tp_default_value_key in value:
            return value.get(self.tp_default_value_key)
        return value

    # Returns the currently used ValueSpec based on the current value
    def _get_used_valuespec(self, value: dict[str, Any]) -> ValueSpec[dict[str, Any]]:
        return (
            self._get_timeperiod_valuespec() if self.is_active(value) else self._enclosed_valuespec
        )

    def mask(self, value: dict[str, Any]) -> dict[str, Any]:
        return self._get_used_valuespec(value).mask(value)

    def transform_value(self, value: dict[str, Any]) -> dict[str, Any]:
        return self._get_used_valuespec(value).transform_value(value)

    def value_to_json(self, value: dict[str, Any]) -> JSONValue:
        return self._get_used_valuespec(value).value_to_json(value)

    def value_from_json(self, json_value: JSONValue) -> dict[str, Any]:
        return self._get_used_valuespec(json_value).value_from_json(json_value)


def main_module_from_rulespec_group_name(
    main_group_name: str,
    main_module_reg: MainModuleRegistry,
) -> ABCMainModule:
    return main_module_reg[
        makeuri_contextless_rulespec_group(
            request,
            main_group_name,
        )
    ]()


rulespec_registry = RulespecRegistry(rulespec_group_registry)
