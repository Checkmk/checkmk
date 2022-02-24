#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The rulespecs are the ruleset specifications registered to WATO."""

import abc
import re
from typing import Any, Callable, Dict, List, Optional
from typing import Tuple as _Tuple
from typing import Type, Union

import cmk.utils.plugin_registry

from cmk.gui.exceptions import MKGeneralException
from cmk.gui.globals import html, request
from cmk.gui.i18n import _
from cmk.gui.type_defs import HTTPVariables
from cmk.gui.utils.html import HTML
from cmk.gui.utils.urls import makeuri, makeuri_contextless, makeuri_contextless_rulespec_group
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    ElementSelection,
    FixedValue,
    ListOf,
    OptionalDropdownChoice,
    Transform,
    Tuple,
    ValueSpec,
    ValueSpecText,
)
from cmk.gui.watolib.check_mk_automations import get_check_information
from cmk.gui.watolib.main_menu import ABCMainModule, ModuleRegistry
from cmk.gui.watolib.search import (
    ABCMatchItemGenerator,
    match_item_generator_registry,
    MatchItem,
    MatchItems,
)
from cmk.gui.watolib.timeperiods import TimeperiodSelection


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
    def help(self) -> Optional[str]:
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
    def choice_title(self) -> str:
        return self.title


class RulespecSubGroup(RulespecBaseGroup, abc.ABC):
    @property
    @abc.abstractmethod
    def main_group(self) -> Type[RulespecGroup]:
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


class RulespecGroupRegistry(cmk.utils.plugin_registry.Registry[Type[RulespecBaseGroup]]):
    def __init__(self):
        super().__init__()
        self._main_groups: List[Type[RulespecGroup]] = []
        self._sub_groups_by_main_group: Dict[Type[RulespecGroup], List[Type[RulespecSubGroup]]] = {}

    def plugin_name(self, instance: Type[RulespecBaseGroup]) -> str:
        return instance().name

    def registration_hook(self, instance: Type[RulespecBaseGroup]) -> None:
        if issubclass(instance, RulespecSubGroup):
            self._sub_groups_by_main_group.setdefault(instance().main_group, []).append(instance)
        elif issubclass(instance, RulespecGroup):
            self._main_groups.append(instance)
        else:
            raise TypeError('Got invalid type "%s"' % instance.__name__)

    def get_group_choices(self) -> List[_Tuple[str, str]]:
        """Returns all available ruleset groups to be used in dropdown choices"""
        choices: List[_Tuple[str, str]] = []

        main_groups = [g_class() for g_class in self.get_main_groups()]
        for main_group in sorted(main_groups, key=lambda g: g.title):
            choices.append((main_group.name, main_group.choice_title))

            sub_groups = [g_class() for g_class in self._get_sub_groups_of(main_group.__class__)]
            for sub_group in sorted(sub_groups, key=lambda g: g.title):
                choices.append((sub_group.name, sub_group.choice_title))

        return choices

    def get_main_groups(self) -> List[Type[RulespecGroup]]:
        return self._main_groups

    def _get_sub_groups_of(self, main_group: Type[RulespecGroup]) -> List[Type[RulespecSubGroup]]:
        return self._sub_groups_by_main_group.get(main_group, [])

    def get_matching_group_names(self, group_name: str) -> List[str]:
        """Get either the main group and all sub groups of a matching main group or the matching sub group"""
        for group_class in self._main_groups:
            if group_class().name == group_name:
                return [group_name] + [
                    g_class().name for g_class in self._get_sub_groups_of(group_class)
                ]

        return [name for name in self._entries if name == group_name]

    def get_host_rulespec_group_names(self, for_host: bool) -> List[str]:
        """Collect all rulesets that apply to hosts, except those specifying new active or static
        checks and except all server monitoring rulesets. Usually, the needed context for service
        monitoring rulesets is not given when the host rulesets are requested."""
        names: List[str] = []
        hidden_groups: _Tuple[str, ...] = ("static", "activechecks")
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


@rulespec_group_registry.register
class RulespecGroupEnforcedServices(RulespecGroup):
    @property
    def name(self):
        return "static"

    @property
    def title(self):
        return _("Enforced services")

    @property
    def help(self):
        return _(
            "Rules to set up [wato_services#manual_checks|manual services]. Services set "
            "up in this way do not depend on the service discovery. This is useful if you want "
            "to enforce compliance with a specific guideline. You can for example ensure that "
            "a certain Windows service is always present on a host."
        )


@rulespec_group_registry.register
class RulespecGroupEnforcedServicesNetworking(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupEnforcedServices

    @property
    def sub_group_name(self):
        return "networking"

    @property
    def title(self):
        return _("Networking")


@rulespec_group_registry.register
class RulespecGroupEnforcedServicesApplications(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupEnforcedServices

    @property
    def sub_group_name(self):
        return "applications"

    @property
    def title(self):
        return _("Applications, Processes & Services")


@rulespec_group_registry.register
class RulespecGroupEnforcedServicesEnvironment(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupEnforcedServices

    @property
    def sub_group_name(self):
        return "environment"

    @property
    def title(self):
        return _("Temperature, Humidity, Electrical Parameters, etc.")


@rulespec_group_registry.register
class RulespecGroupEnforcedServicesOperatingSystem(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupEnforcedServices

    @property
    def sub_group_name(self):
        return "os"

    @property
    def title(self):
        return _("Operating System Resources")


@rulespec_group_registry.register
class RulespecGroupEnforcedServicesHardware(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupEnforcedServices

    @property
    def sub_group_name(self):
        return "hardware"

    @property
    def title(self):
        return _("Hardware, BIOS")


@rulespec_group_registry.register
class RulespecGroupEnforcedServicesStorage(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupEnforcedServices

    @property
    def sub_group_name(self):
        return "storage"

    @property
    def title(self):
        return _("Storage, Filesystems and Files")


@rulespec_group_registry.register
class RulespecGroupEnforcedServicesVirtualization(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupEnforcedServices

    @property
    def sub_group_name(self):
        return "virtualization"

    @property
    def title(self):
        return _("Virtualization")


# TODO: Kept for compatibility with pre 1.6 plugins
def register_rulegroup(group_name, title, help_text):
    rulespec_group_registry.register(_get_legacy_rulespec_group_class(group_name, title, help_text))


def get_rulegroup(group_name):
    try:
        group_class = rulespec_group_registry[group_name]
    except KeyError:
        group_class = _get_legacy_rulespec_group_class(group_name, group_title=None, help_text=None)
        rulespec_group_registry.register(group_class)
    # Pylint does not detect the subclassing in LegacyRulespecSubGroup correctly. Disable the check here :(
    return group_class()  # pylint: disable=abstract-class-instantiated


def _get_legacy_rulespec_group_class(group_name, group_title, help_text):
    if "/" in group_name:
        main_group_name, sub_group_name = group_name.split("/", 1)
        sub_group_title = group_title or sub_group_name

        # group_name could contain non alphanumeric characters
        internal_sub_group_name = re.sub("[^a-zA-Z]", "", sub_group_name)

        main_group_class = get_rulegroup(main_group_name).__class__
        return type(
            "LegacyRulespecSubGroup%s" % internal_sub_group_name.title(),
            (RulespecSubGroup,),
            {
                "main_group": main_group_class,
                "sub_group_name": internal_sub_group_name.lower(),
                "title": sub_group_title,
            },
        )

    group_title = group_title or group_name

    return type(
        "LegacyRulespecGroup%s" % group_name.title(),
        (RulespecGroup,),
        {
            "name": group_name,
            "title": group_title,
            "help": help_text,
        },
    )


def _validate_function_args(arg_infos: List[_Tuple[Any, bool, bool]], hint: str) -> None:
    for idx, (arg, is_callable, none_allowed) in enumerate(arg_infos):
        if not none_allowed and arg is None:
            raise MKGeneralException(_("Invalid None argument at for %s idx %d") % (hint, idx))
        if arg is not None and callable(arg) != is_callable:
            raise MKGeneralException(
                _("Invalid expected callable for %s at idx %d: %r") % (hint, idx, arg)
            )


class Rulespec(abc.ABC):
    NO_FACTORY_DEFAULT: list = []
    # means this ruleset is not used if no rule is entered
    FACTORY_DEFAULT_UNUSED: list = []

    def __init__(
        self,
        name: str,
        group: Type[RulespecBaseGroup],
        title: Optional[Callable[[], str]],
        valuespec: Callable[[], ValueSpec],
        match_type: str,
        item_type: Optional[str],
        # WATCH OUT: passing a Callable[[], Transform] will not work (see the
        # isinstance check in the item_spec property)!
        item_spec: Optional[Callable[[], ValueSpec]],
        item_name: Optional[Callable[[], str]],
        item_help: Optional[Callable[[], str]],
        is_optional: bool,
        is_deprecated: bool,
        is_for_services: bool,
        is_binary_ruleset: bool,
        factory_default: Any,
        help_func: Optional[Callable[[], str]],
    ) -> None:
        super().__init__()

        arg_infos: List[_Tuple[Any, bool, bool]] = [
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
            (is_for_services, False, False),
            (is_binary_ruleset, False, False),
            (factory_default, False, True),
            (help_func, True, True),
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
        self._is_binary_ruleset = is_binary_ruleset
        self._is_for_services = is_for_services
        self._factory_default = factory_default
        self._help = help_func

    @property
    def name(self) -> str:
        return self._name

    @property
    def group(self) -> Type[RulespecBaseGroup]:
        return self._group

    @property
    def valuespec(self) -> ValueSpec:
        return self._valuespec()

    @property
    def title(self) -> Optional[str]:
        if self._title:
            return self._title()

        return self.valuespec.title()

    @property
    def help(self) -> Union[None, str, HTML]:
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
    def item_type(self) -> Optional[str]:
        return self._item_type

    @property
    def item_spec(self) -> Optional[ValueSpec]:
        if self._item_spec:
            return self._item_spec()

        return None

    @property
    def item_name(self) -> Optional[str]:
        if self._item_name:
            return self._item_name()

        if self._item_spec:
            return self._item_spec().title()

        if self.item_type == "service":
            return _("Service")

        return None

    @property
    def item_help(self) -> Union[None, str, HTML]:
        if self._item_help:
            return self._item_help()

        if self._item_spec:
            return self._item_spec().help()

        return None

    @property
    def item_enum(self) -> Optional[List[_Tuple[str, str]]]:
        item_spec = self.item_spec
        if item_spec is None:
            return None

        if isinstance(item_spec, (DropdownChoice, OptionalDropdownChoice)):
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
    def match_type(self) -> str:
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


class HostRulespec(Rulespec):
    """Base class for all rulespecs managing host rule sets with values"""

    # Required because of Rulespec.NO_FACTORY_DEFAULT
    def __init__(  # pylint: disable=dangerous-default-value
        self,
        name: str,
        group: Type[Any],
        valuespec: Callable[[], ValueSpec],
        title: Optional[Callable[[], str]] = None,
        match_type: str = "first",
        is_optional: bool = False,
        is_deprecated: bool = False,
        is_binary_ruleset: bool = False,
        factory_default: Any = Rulespec.NO_FACTORY_DEFAULT,
        help_func: Optional[Callable[[], str]] = None,
    ) -> None:
        super().__init__(
            name=name,
            group=group,
            title=title,
            valuespec=valuespec,
            match_type=match_type,
            is_optional=is_optional,
            is_deprecated=is_deprecated,
            is_binary_ruleset=is_binary_ruleset,
            factory_default=factory_default,
            help_func=help_func,
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
    def __init__(  # pylint: disable=dangerous-default-value
        self,
        name: str,
        group: Type[RulespecBaseGroup],
        valuespec: Callable[[], ValueSpec],
        title: Optional[Callable[[], str]] = None,
        match_type: str = "first",
        item_type: Optional[str] = None,
        item_name: Optional[Callable[[], str]] = None,
        item_spec: Optional[Callable[[], ValueSpec]] = None,
        item_help: Optional[Callable[[], str]] = None,
        is_optional: bool = False,
        is_deprecated: bool = False,
        is_binary_ruleset: bool = False,
        factory_default: Any = Rulespec.NO_FACTORY_DEFAULT,
        help_func: Optional[Callable[[], str]] = None,
    ) -> None:
        super().__init__(
            name=name,
            group=group,
            title=title,
            valuespec=valuespec,
            match_type=match_type,
            is_binary_ruleset=is_binary_ruleset,
            item_type=item_type or "service",
            item_name=item_name,
            item_spec=item_spec,
            item_help=item_help,
            is_optional=is_optional,
            is_deprecated=is_deprecated,
            factory_default=factory_default,
            help_func=help_func,
            # Excplicit set
            is_for_services=True,
        )


class BinaryHostRulespec(HostRulespec):
    # Required because of Rulespec.NO_FACTORY_DEFAULT
    def __init__(  # pylint: disable=dangerous-default-value
        self,
        name: str,
        group: Type[RulespecBaseGroup],
        title: Optional[Callable[[], str]] = None,
        match_type: str = "first",
        is_optional: bool = False,
        is_deprecated: bool = False,
        factory_default: Any = Rulespec.NO_FACTORY_DEFAULT,
        help_func: Optional[Callable[[], str]] = None,
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
            # Explicit set
            is_binary_ruleset=True,
            valuespec=self._binary_host_valuespec,
        )

    def _binary_host_valuespec(self) -> ValueSpec:
        return DropdownChoice(
            choices=[
                (True, _("Positive match (Add matching hosts to the set)")),
                (False, _("Negative match (Exclude matching hosts from the set)")),
            ],
            default_value=True,
        )


class BinaryServiceRulespec(ServiceRulespec):
    # Required because of Rulespec.NO_FACTORY_DEFAULT
    def __init__(  # pylint: disable=dangerous-default-value
        self,
        name: str,
        group: Type[RulespecBaseGroup],
        title: Optional[Callable[[], str]] = None,
        match_type: str = "first",
        item_type: Optional[str] = None,
        item_name: Optional[Callable[[], str]] = None,
        item_spec: Optional[Callable[[], ValueSpec]] = None,
        item_help: Optional[Callable[[], str]] = None,
        is_optional: bool = False,
        is_deprecated: bool = False,
        factory_default: Any = Rulespec.NO_FACTORY_DEFAULT,
        help_func: Optional[Callable[[], str]] = None,
    ) -> None:
        super().__init__(
            name=name,
            group=group,
            title=title,
            match_type=match_type,
            is_optional=is_optional,
            is_deprecated=is_deprecated,
            item_type=item_type or "service",
            item_spec=item_spec,
            item_name=item_name,
            item_help=item_help,
            factory_default=factory_default,
            help_func=help_func,
            # Explicit set
            is_binary_ruleset=True,
            valuespec=self._binary_service_valuespec,
        )

    def _binary_service_valuespec(self) -> ValueSpec:
        return DropdownChoice(
            choices=[
                (True, _("Positive match (Add matching services to the set)")),
                (False, _("Negative match (Exclude matching services from the set)")),
            ],
            default_value=True,
        )


def _get_manual_check_parameter_rulespec_instance(
    group: Type[Any],
    check_group_name: str,
    title: Optional[Callable[[], str]] = None,
    parameter_valuespec: Optional[Callable[[], ValueSpec]] = None,
    item_spec: Optional[Callable[[], ValueSpec]] = None,
    is_optional: Optional[bool] = None,
    is_deprecated: Optional[bool] = None,
) -> "ManualCheckParameterRulespec":
    # There may be no RulespecGroup declaration for the static checks.
    # Create some based on the regular check groups (which should have a definition)
    try:
        subgroup_key = "static/" + group().sub_group_name
        checkparams_static_sub_group_class = rulespec_group_registry[subgroup_key]
    except KeyError:
        group_instance = group()
        main_group_static_class = rulespec_group_registry["static"]
        checkparams_static_sub_group_class = type(
            "%sStatic" % group_instance.__class__.__name__,
            (group_instance.__class__,),
            {
                "main_group": main_group_static_class,
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
    )


class CheckParameterRulespecWithItem(ServiceRulespec):
    """Base class for all rulespecs managing parameters for check groups with item

    These have to be named checkgroup_parameters:<name-of-checkgroup>. These
    parameters affect the discovered services only, not the manually configured
    checks."""

    # Required because of Rulespec.NO_FACTORY_DEFAULT
    def __init__(  # pylint: disable=dangerous-default-value
        self,
        check_group_name: str,
        group: Type[RulespecBaseGroup],
        parameter_valuespec: Callable[[], ValueSpec],
        title: Optional[Callable[[], str]] = None,
        match_type: Optional[str] = None,
        item_type: Optional[str] = None,
        item_name: Optional[Callable[[], str]] = None,
        item_spec: Optional[Callable[[], ValueSpec]] = None,
        item_help: Optional[Callable[[], str]] = None,
        is_optional: bool = False,
        is_deprecated: bool = False,
        factory_default: Any = Rulespec.NO_FACTORY_DEFAULT,
        create_manual_check: bool = True,
    ) -> None:
        # Mandatory keys
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
            name=name,
            group=group,
            title=title,
            item_type=item_type or "item",
            item_name=item_name,
            item_spec=item_spec,
            item_help=item_help,
            is_optional=is_optional,
            is_deprecated=is_deprecated,
            # Excplicit set
            is_binary_ruleset=False,
            match_type=match_type or "first",
            valuespec=self._rulespec_valuespec,
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
    def __init__(  # pylint: disable=dangerous-default-value
        self,
        check_group_name,
        group,
        parameter_valuespec,
        title=None,
        match_type=None,
        is_optional=False,
        is_deprecated=False,
        factory_default=Rulespec.NO_FACTORY_DEFAULT,
        create_manual_check=True,
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
            # Excplicit set
            name=name,
            is_binary_ruleset=False,
            match_type=match_type or "first",
            valuespec=self._rulespec_valuespec,
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


class ManualCheckParameterRulespec(HostRulespec):
    """Base class for all rulespecs managing manually configured checks

    These have to be named static_checks:<name-of-checkgroup>"""

    # Required because of Rulespec.NO_FACTORY_DEFAULT
    def __init__(  # pylint: disable=dangerous-default-value
        self,
        group,
        check_group_name,
        parameter_valuespec=None,
        title=None,
        item_spec=None,
        is_optional=False,
        is_deprecated=False,
        name=None,
        match_type="all",
        factory_default=Rulespec.NO_FACTORY_DEFAULT,
    ):

        # Mandatory keys
        self._check_group_name = check_group_name
        if name is None:
            name = "static_checks:%s" % self._check_group_name

        arg_infos = [
            # (arg, is_callable, none_allowed)
            (check_group_name, False, False),
            (parameter_valuespec, True, True),
            (item_spec, True, True),
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
            # Explicit set
            valuespec=self._rulespec_valuespec,
        )

        # Optional keys
        self._parameter_valuespec = parameter_valuespec
        self._rule_value_item_spec = item_spec

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
                None,
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
                    title=_("Checktype"),
                    help=_("Please choose the check plugin"),
                ),
                self._get_item_spec(),
                parameter_vs,
            ],
        )

    def _get_item_spec(self) -> ValueSpec:
        """Not used as condition, only for the rule value valuespec"""
        if self._rule_value_item_spec:
            return self._rule_value_item_spec()

        return FixedValue(
            None,
            totext="",
        )


# Pre 1.6 rule registering logic. Need to be kept for some time
def register_rule(
    group,
    varname,
    valuespec=None,
    title=None,
    help=None,  # pylint: disable=redefined-builtin
    itemspec=None,
    itemtype=None,
    itemname=None,
    itemhelp=None,
    itemenum=None,
    match="first",
    optional=False,
    deprecated=False,
    **kwargs,
):

    base_class = _rulespec_class_for(varname, valuespec is not None, itemtype is not None)
    class_kwargs = {
        "name": varname,
        "group": get_rulegroup(group).__class__ if isinstance(group, str) else group,
        "match_type": match,
        "factory_default": kwargs.get("factory_default", Rulespec.NO_FACTORY_DEFAULT),
        "is_optional": optional,
        "is_deprecated": deprecated,
    }
    if valuespec is not None:
        class_kwargs["valuespec"] = lambda: valuespec
    if varname.startswith("static_checks:") or varname.startswith("checkgroup_parameters:"):
        class_kwargs["check_group_name"] = varname.split(":", 1)[1]
    if title is not None:
        class_kwargs["title"] = lambda: title
    if itemtype is not None:
        class_kwargs["item_type"] = itemtype
    if help is not None:
        class_kwargs["help_func"] = lambda v=help: v
    if itemspec is not None:
        class_kwargs["item_spec"] = lambda v=itemspec: v
    if itemname is not None:
        class_kwargs["item_name"] = lambda v=itemname: v
    if itemhelp is not None:
        class_kwargs["item_help"] = lambda v=itemhelp: v
    if not itemname and itemtype == "service":
        class_kwargs["item_name"] = lambda: _("Service")

    rulespec_registry.register(base_class(**class_kwargs))


# NOTE: mypy's typing rules for ternaries seem to be a bit broken, so we have
# to nest ifs in a slightly ugly way.
def _rulespec_class_for(varname: str, has_valuespec: bool, has_itemtype: bool) -> Type[Rulespec]:
    if varname.startswith("static_checks:"):
        return ManualCheckParameterRulespec
    if varname.startswith("checkgroup_parameters:"):
        if has_itemtype:
            return CheckParameterRulespecWithItem
        return CheckParameterRulespecWithoutItem
    if has_valuespec:
        if has_itemtype:
            return ServiceRulespec
        return HostRulespec
    if has_itemtype:
        return BinaryServiceRulespec
    return BinaryHostRulespec


class RulespecRegistry(cmk.utils.plugin_registry.Registry[Rulespec]):
    def __init__(self, group_registry):
        super().__init__()
        self._group_registry = group_registry

    def plugin_name(self, instance: Rulespec) -> str:
        return instance.name

    def get_by_group(self, group_name: str) -> List[Rulespec]:
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
        return list(set(gc.group_name for gc in self.values()))

    def register(self, instance: Any) -> Any:
        # not-yet-a-type: (Rulespec) -> None
        if not isinstance(instance, Rulespec):
            raise MKGeneralException(_("Tried to register incompatible rulespec: %r") % instance)

        if isinstance(
            instance, (CheckParameterRulespecWithItem, CheckParameterRulespecWithoutItem)
        ):

            manual_instance: Any = instance.manual_check_parameter_rulespec_instance
            if manual_instance:
                subgroup_key = "static/" + manual_instance.group().sub_group_name
                if subgroup_key not in rulespec_group_registry:
                    rulespec_group_registry.register(manual_instance.group)

                super().register(manual_instance)

        return super().register(instance)

    def register_without_manual_check_rulespec(self, instance: Rulespec) -> None:
        """Use this register method to prevent adding a manual check rulespec"""
        if not isinstance(instance, Rulespec):
            MKGeneralException(
                _("!!! Error: Received class in RulespecRegistry:register_manual_check_rulespec %r")
                % instance
            )
            return
        super().register(instance)


class CheckTypeGroupSelection(ElementSelection):
    def __init__(self, checkgroup, **kwargs):
        super().__init__(**kwargs)
        self._checkgroup = checkgroup

    def get_elements(self):
        checks = get_check_information().plugin_infos
        elements = {
            cn: "%s - %s" % (cn, c["title"])
            for (cn, c) in checks.items()
            if c.get("group") == self._checkgroup
        }
        return elements

    def value_to_html(self, value) -> ValueSpecText:
        return html.render_tt(value)


class TimeperiodValuespec(ValueSpec):
    # Used by GUI switch
    # The actual set mode
    # "0" - no timespecific settings
    # "1" - timespecific settings active
    tp_toggle_var = "tp_toggle"
    tp_current_mode = "tp_active"

    tp_default_value_key = "tp_default_value"  # Used in valuespec
    tp_values_key = "tp_values"  # Used in valuespec

    def __init__(self, valuespec):
        super().__init__(
            title=valuespec.title(),
            help=valuespec.help(),
        )
        self._enclosed_valuespec = valuespec

    def default_value(self):
        # If nothing is configured, simply return the default value of the enclosed valuespec
        return self._enclosed_valuespec.default_value()

    def render_input(self, varprefix: str, value: Any) -> None:
        # The display mode differs when the valuespec is activated
        vars_copy = dict(request.itervars())

        # The timeperiod mode can be set by either the GUI switch or by the value itself
        # GUI switch overrules the information stored in the value
        if request.has_var(self.tp_toggle_var):
            is_active = self._is_switched_on()
        else:
            is_active = self.is_active(value)

        # Set the actual used mode
        html.hidden_field(self.tp_current_mode, "%d" % is_active)

        vars_copy[self.tp_toggle_var] = "%d" % (not is_active)

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
            r = self._enclosed_valuespec.render_input(varprefix, value)
            html.buttonlink(
                toggle_url,
                _("Enable timespecific parameters"),
                class_=["toggle_timespecific_parameter"],
            )
            return r

    def value_to_html(self, value) -> ValueSpecText:
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

    def _validate_value(self, value: Any, varprefix: str) -> None:
        super()._validate_value(value, varprefix)
        self._get_used_valuespec(value).validate_value(value, varprefix)

    def validate_datatype(self, value: Any, varprefix: str) -> None:
        super().validate_datatype(value, varprefix)
        self._get_used_valuespec(value).validate_datatype(value, varprefix)

    def _get_timeperiod_valuespec(self):
        return Dictionary(
            elements=[
                (
                    self.tp_default_value_key,
                    Transform(
                        self._enclosed_valuespec,
                        title=_("Default parameters when no timeperiod matches"),
                    ),
                ),
                (
                    self.tp_values_key,
                    ListOf(
                        Tuple(
                            elements=[
                                TimeperiodSelection(
                                    title=_("Match only during timeperiod"),
                                    help=_(
                                        "Match this rule only during times where the "
                                        "selected timeperiod from the monitoring "
                                        "system is active."
                                    ),
                                ),
                                self._enclosed_valuespec,
                            ]
                        ),
                        title=_("Configured timeperiod parameters"),
                    ),
                ),
            ],
            optional_keys=False,
        )

    # Checks whether the tp-mode is switched on through the gui
    def _is_switched_on(self):
        return request.var(self.tp_toggle_var) == "1"

    # Checks whether the value itself already uses the tp-mode
    def is_active(self, value):
        return isinstance(value, dict) and self.tp_default_value_key in value

    # Returns simply the value or converts a plain value to a tp-value
    def _get_timeperiod_value(self, value):
        if isinstance(value, dict) and self.tp_default_value_key in value:
            return value
        return {self.tp_values_key: [], self.tp_default_value_key: value}

    # Returns simply the value or converts tp-value back to a plain value
    def _get_timeless_value(self, value):
        if isinstance(value, dict) and self.tp_default_value_key in value:
            return value.get(self.tp_default_value_key)
        return value

    # Returns the currently used ValueSpec based on the current value
    def _get_used_valuespec(self, value: Any) -> ValueSpec:
        return (
            self._get_timeperiod_valuespec() if self.is_active(value) else self._enclosed_valuespec
        )

    def transform_value(self, value: Any) -> Any:
        return self._get_used_valuespec(value).transform_value(value)

    def value_to_json(self, value: Any) -> Any:
        return self._get_used_valuespec(value).value_to_json(value)

    def value_from_json(self, json_value: Any) -> Any:
        return self._get_used_valuespec(json_value).value_from_json(json_value)

    def value_to_json_safe(self, value: Any) -> Any:
        return self._get_used_valuespec(value).value_to_json_safe(value)


def main_module_from_rulespec_group_name(
    group_name: str,
    main_module_reg: ModuleRegistry,
) -> ABCMainModule:
    return main_module_reg[
        makeuri_contextless_rulespec_group(
            request,
            group_name,
        )
    ]()


class MatchItemGeneratorRules(ABCMatchItemGenerator):
    def __init__(
        self,
        name: str,
        rulesepc_group_reg: RulespecGroupRegistry,
        rulespec_reg: RulespecRegistry,
    ) -> None:
        super().__init__(name)
        self._rulespec_group_registry = rulesepc_group_reg
        self._rulespec_registry = rulespec_reg

    def _topic(self, rulespec: Rulespec) -> str:
        if rulespec.is_deprecated:
            return _("Deprecated rulesets")
        return f"{self._rulespec_group_registry[rulespec.main_group_name]().title}"

    def generate_match_items(self) -> MatchItems:
        yield from (
            MatchItem(
                title=rulespec.title,
                topic=self._topic(rulespec),
                url=makeuri_contextless(
                    request,
                    [("mode", "edit_ruleset"), ("varname", rulespec.name)],
                    filename="wato.py",
                ),
                match_texts=[rulespec.title, rulespec.name],
            )
            for group in self._rulespec_registry.get_all_groups()
            for rulespec in self._rulespec_registry.get_by_group(group)
            if rulespec.title
        )

    @staticmethod
    def is_affected_by_change(_change_action_name: str) -> bool:
        return False

    @property
    def is_localization_dependent(self) -> bool:
        return True


rulespec_registry = RulespecRegistry(rulespec_group_registry)

match_item_generator_registry.register(
    MatchItemGeneratorRules(
        "rules",
        rulespec_group_registry,
        rulespec_registry,
    )
)
