#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""The rulespecs are the ruleset specifications registered to WATO."""

import abc
import re
from typing import Text, Dict, List, Type, Optional, Any, Callable  # pylint: disable=unused-import
from typing import Tuple as TypingTuple  # pylint: disable=unused-import
import six

import cmk.utils.plugin_registry

from cmk.gui.globals import html
from cmk.gui.valuespec import ValueSpec  # pylint: disable=unused-import
from cmk.gui.valuespec import (
    Dictionary,
    Transform,
    ListOf,
    ElementSelection,
    FixedValue,
    Tuple,
    DropdownChoice,
    OptionalDropdownChoice,
)
from cmk.gui.watolib.timeperiods import TimeperiodSelection
from cmk.gui.watolib.automations import check_mk_local_automation
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException


class RulespecBaseGroup(object):
    """Base class for all rulespec group types"""
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def name(self):
        # type: () -> Text
        """Unique internal key of this group"""
        raise NotImplementedError()

    @abc.abstractproperty
    def title(self):
        # type: () -> Text
        """Human readable title of this group"""
        raise NotImplementedError()

    @abc.abstractproperty
    def help(self):
        # type: () -> Text
        """Helpful description of this group"""
        raise NotImplementedError()

    @abc.abstractproperty
    def is_sub_group(self):
        # type: () -> bool
        raise NotImplementedError()

    @abc.abstractproperty
    def choice_title(self):
        # type: () -> Text
        raise NotImplementedError()


class RulespecGroup(RulespecBaseGroup):
    @abc.abstractproperty
    def name(self):
        # type: () -> Text
        """Unique internal key of this group"""
        raise NotImplementedError()

    @abc.abstractproperty
    def title(self):
        # type: () -> Text
        """Human readable title of this group"""
        raise NotImplementedError()

    @abc.abstractproperty
    def help(self):
        # type: () -> Text
        """Helpful description of this group"""
        raise NotImplementedError()

    @property
    def is_sub_group(self):
        return False

    @property
    def choice_title(self):
        return self.title


class RulespecSubGroup(RulespecBaseGroup):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def main_group(self):
        """A reference to the main group class"""
        raise NotImplementedError()

    @abc.abstractproperty
    def sub_group_name(self):
        """The internal name of the sub group"""
        raise NotImplementedError()

    @property
    def name(self):
        return "/".join([self.main_group().name, self.sub_group_name])

    @property
    def choice_title(self):
        return u"&nbsp;&nbsp;⌙ %s" % self.title

    @property
    def help(self):
        return None  # Sub groups currently have no help text

    @property
    def is_sub_group(self):
        return True


class RulespecGroupRegistry(cmk.utils.plugin_registry.ClassRegistry):
    def __init__(self):
        super(RulespecGroupRegistry, self).__init__()
        self._main_groups = []  # type: List[Type[RulespecGroup]]
        self._sub_groups_by_main_group = {
        }  # type: Dict[Type[RulespecGroup], List[Type[RulespecSubGroup]]]

    def plugin_base_class(self):
        return RulespecBaseGroup

    def plugin_name(self, plugin_class):
        return plugin_class().name

    def registration_hook(self, plugin_class):
        group = plugin_class()
        if not group.is_sub_group:
            self._main_groups.append(plugin_class)
        else:
            self._sub_groups_by_main_group.setdefault(group.main_group, []).append(plugin_class)

    def get_group_choices(self, mode):
        """Returns all available ruleset groups to be used in dropdown choices"""
        choices = []

        main_groups = [g_class() for g_class in self.get_main_groups()]
        for main_group in sorted(main_groups, key=lambda g: g.title):
            if mode == "static_checks" and main_group.name != "static":
                continue
            elif mode != "static_checks" and main_group.name == "static":
                continue

            choices.append((main_group.name, main_group.choice_title))

            sub_groups = [g_class() for g_class in self._get_sub_groups_of(main_group.__class__)]
            for sub_group in sorted(sub_groups, key=lambda g: g.title):
                choices.append((sub_group.name, sub_group.choice_title))

        return choices

    def get_main_groups(self):
        # type: () -> List[Type[RulespecGroup]]
        return self._main_groups

    def _get_sub_groups_of(self, main_group):
        # type: (Type[RulespecGroup]) -> List[Type[RulespecSubGroup]]
        return self._sub_groups_by_main_group.get(main_group, [])

    def get_matching_group_names(self, group_name):
        # type: (str) -> List[str]
        """Get either the main group and all sub groups of a matching main group or the matching sub group"""
        for group_class in self._main_groups:
            if group_class().name == group_name:
                return [group_name
                       ] + [g_class().name for g_class in self._get_sub_groups_of(group_class)]

        return [name for name in self._entries if name == group_name]

    def get_host_rulespec_group_names(self):
        """Collect all rulesets that apply to hosts, except those specifying new active or static checks"""
        names = []
        hidden_groups = ("static", "checkparams", "activechecks")
        hidden_main_groups = ("monconf", "agents", "agent")
        for g_class in self.values():
            group = g_class()
            if group.is_sub_group and group.main_group().name in hidden_groups:
                continue

            if not group.is_sub_group and group.name in hidden_groups or group.name in hidden_main_groups:
                continue

            names.append(group.name)
        return names


rulespec_group_registry = RulespecGroupRegistry()


@rulespec_group_registry.register
class RulespecGroupManualChecks(RulespecGroup):
    @property
    def name(self):
        return "static"

    @property
    def title(self):
        return _("Manual Checks")

    @property
    def help(self):
        return _("Statically configured Check_MK checks that do not rely on the inventory")


@rulespec_group_registry.register
class RulespecGroupManualChecksNetworking(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupManualChecks

    @property
    def sub_group_name(self):
        return "networking"

    @property
    def title(self):
        return _("Networking")


@rulespec_group_registry.register
class RulespecGroupManualChecksApplications(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupManualChecks

    @property
    def sub_group_name(self):
        return "applications"

    @property
    def title(self):
        return _("Applications, Processes & Services")


@rulespec_group_registry.register
class RulespecGroupManualChecksEnvironment(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupManualChecks

    @property
    def sub_group_name(self):
        return "environment"

    @property
    def title(self):
        return _("Temperature, Humidity, Electrical Parameters, etc.")


@rulespec_group_registry.register
class RulespecGroupManualChecksOperatingSystem(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupManualChecks

    @property
    def sub_group_name(self):
        return "os"

    @property
    def title(self):
        return _("Operating System Resources")


@rulespec_group_registry.register
class RulespecGroupManualChecksHardware(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupManualChecks

    @property
    def sub_group_name(self):
        return "hardware"

    @property
    def title(self):
        return _("Hardware, BIOS")


@rulespec_group_registry.register
class RulespecGroupManualChecksStorage(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupManualChecks

    @property
    def sub_group_name(self):
        return "storage"

    @property
    def title(self):
        return _("Storage, Filesystems and Files")


@rulespec_group_registry.register
class RulespecGroupManualChecksVirtualization(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupManualChecks

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
        internal_sub_group_name = str(re.sub('[^a-zA-Z]', '', sub_group_name))

        main_group_class = get_rulegroup(main_group_name).__class__
        return type(
            "LegacyRulespecSubGroup%s" % internal_sub_group_name.title(), (RulespecSubGroup,), {
                "main_group": main_group_class,
                "sub_group_name": internal_sub_group_name.lower(),
                "title": sub_group_title,
            })

    group_title = group_title or group_name

    return type("LegacyRulespecGroup%s" % group_name.title(), (RulespecGroup,), {
        "name": group_name,
        "title": group_title,
        "help": help_text,
    })


def _validate_function_args(arg_infos, hint):
    # type: (List[TypingTuple[Any, bool, bool]], str) -> None
    for idx, (arg, is_callable, none_allowed) in enumerate(arg_infos):
        if not none_allowed and arg is None:
            raise MKGeneralException(_("Invalid None argument at for %s idx %d") % (hint, idx))
        if arg is not None and callable(arg) != is_callable:
            raise MKGeneralException(
                _("Invalid expected callable for %s at idx %d: %r") % (hint, idx, arg))


class Rulespec(object):
    __metaclass__ = abc.ABCMeta

    # needed for unique ID
    NO_FACTORY_DEFAULT = []  # type: list
    # means this ruleset is not used if no rule is entered
    FACTORY_DEFAULT_UNUSED = []  # type: list

    def __init__(
            self,
            name,
            group,
            title,
            valuespec,
            match_type,
            item_type,
            item_spec,
            item_name,
            item_help,
            is_optional,
            is_deprecated,
            is_for_services,
            is_binary_ruleset,
            factory_default,
            help_func,
    ):
        # type: (str, Type[RulespecGroup], Optional[Callable[[], Text]], Callable[[], ValueSpec], str, Optional[str], Optional[Callable[[], ValueSpec]], Optional[Callable[[], Text]], Optional[Callable[[], Text]], bool, bool, bool, bool, Any, Optional[Callable[[], Text]]) -> None
        super(Rulespec, self).__init__()

        arg_infos = [
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
        ]  # type: List[TypingTuple[Any, bool, bool]]
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
    def name(self):
        # type: () -> str
        return self._name

    @property
    def group(self):
        # type: () -> Type[RulespecGroup]
        return self._group

    @property
    def valuespec(self):
        # type: () -> ValueSpec
        return self._valuespec()

    @property
    def title(self):
        # type: () -> Text
        if self._title:
            return self._title()

        return self.valuespec.title()

    @property
    def help(self):
        # type: () -> Text
        if self._help:
            return self._help()

        return self.valuespec.help()

    @property
    def is_for_services(self):
        # type: () -> bool
        return self._is_for_services

    @property
    def is_binary_ruleset(self):
        # type: () -> bool
        return self._is_binary_ruleset

    @property
    def item_type(self):
        # type: () -> Optional[str]
        return self._item_type

    @property
    def item_spec(self):
        # type: () -> Optional[ValueSpec]
        if self._item_spec:
            return self._item_spec()

        return None

    @property
    def item_name(self):
        # type: () -> Optional[Text]
        if self._item_name:
            return self._item_name()

        if self._item_spec:
            return self._item_spec().title()

        if self.item_type == "service":
            return _("Service")

        return None

    @property
    def item_help(self):
        # type: () -> Optional[Text]
        if self._item_help:
            return self._item_help()

        if self._item_spec:
            return self._item_spec().help()

        return None

    @property
    def item_enum(self):
        # type: () -> Optional[List[TypingTuple[str, Text]]]
        item_spec = self.item_spec
        if item_spec is None:
            return None

        if isinstance(item_spec, (DropdownChoice, OptionalDropdownChoice)):
            return item_spec._choices

        return None

    @property
    def group_name(self):
        # type: () -> Text
        return self._group().name

    @property
    def main_group_name(self):
        # type: () -> Text
        return self.group_name.split("/")[0]

    @property
    def sub_group_name(self):
        # type: () -> Text
        return self.group_name.split("/")[1] if "/" in self.group_name else ""

    @property
    def match_type(self):
        # type: () -> str
        return self._match_type

    @property
    def factory_default(self):
        # type: () -> Any
        return self._factory_default

    @property
    def is_optional(self):
        # type: () -> bool
        return self._is_optional

    @property
    def is_deprecated(self):
        # type: () -> bool
        return self._is_deprecated


class HostRulespec(Rulespec):
    """Base class for all rulespecs managing host rule sets with values"""

    # Required because of Rulespec.NO_FACTORY_DEFAULT
    def __init__(  # pylint: disable=dangerous-default-value
            self,
            name,
            group,
            valuespec,
            title=None,
            match_type="first",
            is_optional=False,
            is_deprecated=False,
            is_binary_ruleset=False,
            factory_default=Rulespec.NO_FACTORY_DEFAULT,
            help_func=None,
    ):
        # type: (str, Type[Any], Callable[[], ValueSpec], Optional[Callable[[], Text]], str, bool, bool, bool, Any, Optional[Callable[[], Text]]) -> None
        super(HostRulespec, self).__init__(
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
            name,
            group,
            valuespec,
            title=None,
            match_type="first",
            item_type=None,
            item_name=None,
            item_spec=None,
            item_help=None,
            is_optional=False,
            is_deprecated=False,
            is_binary_ruleset=False,
            factory_default=Rulespec.NO_FACTORY_DEFAULT,
            help_func=None,
    ):
        # type: (str, Type[RulespecGroup], Callable[[], ValueSpec], Optional[Callable[[], Text]], str, Optional[str], Optional[Callable[[], Text]], Optional[Callable[[], ValueSpec]], Optional[Callable[[], Text]], bool, bool, bool, Any, Optional[Callable[[], Text]]) -> None
        super(ServiceRulespec, self).__init__(
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
            is_for_services=True)


class BinaryHostRulespec(HostRulespec):
    # Required because of Rulespec.NO_FACTORY_DEFAULT
    def __init__(  # pylint: disable=dangerous-default-value
            self,
            name,
            group,
            title=None,
            match_type="first",
            is_optional=False,
            is_deprecated=False,
            factory_default=Rulespec.NO_FACTORY_DEFAULT,
            help_func=None,
    ):
        # type: (str, Type[RulespecGroup], Optional[Callable[[], Text]], str, bool, bool, Any, Optional[Callable[[], Text]]) -> None
        super(BinaryHostRulespec, self).__init__(
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

    def _binary_host_valuespec(self):
        # type: () -> ValueSpec
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
            name,
            group,
            title=None,
            match_type="first",
            item_type=None,
            item_name=None,
            item_spec=None,
            item_help=None,
            is_optional=False,
            is_deprecated=False,
            factory_default=Rulespec.NO_FACTORY_DEFAULT,
            help_func=None,
    ):
        # type: (str, Type[RulespecGroup], Optional[Callable[[], Text]], str, Optional[str], Optional[Callable[[], Text]], Optional[Callable[[], ValueSpec]], Optional[Callable[[], Text]], bool, bool, Any, Optional[Callable[[], Text]]) -> None
        super(BinaryServiceRulespec, self).__init__(
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

    def _binary_service_valuespec(self):
        # type: () -> ValueSpec
        return DropdownChoice(
            choices=[
                (True, _("Positive match (Add matching services to the set)")),
                (False, _("Negative match (Exclude matching services from the set)")),
            ],
            default_value=True,
        )


def _get_manual_check_parameter_rulespec_instance(
        group,
        check_group_name,
        title=None,
        parameter_valuespec=None,
        item_spec=None,
        is_optional=None,
        is_deprecated=None,
):
    # type: (Type[Any], str, Optional[Callable[[], Text]], Optional[Callable[[], ValueSpec]], Optional[Callable[[], ValueSpec]], bool, bool) -> ManualCheckParameterRulespec
    # There may be no RulespecGroup declaration for the static checks.
    # Create some based on the regular check groups (which should have a definition)
    try:
        subgroup_key = "static/" + group().sub_group_name
        checkparams_static_sub_group_class = rulespec_group_registry[subgroup_key]
    except KeyError:
        group_instance = group()
        main_group_static_class = rulespec_group_registry["static"]
        checkparams_static_sub_group_class = type("%sStatic" % group_instance.__class__.__name__,
                                                  (group_instance.__class__,), {
                                                      "main_group": main_group_static_class,
                                                  })

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
            check_group_name,
            group,
            parameter_valuespec,
            title=None,
            match_type=None,
            item_type=None,
            item_name=None,
            item_spec=None,
            item_help=None,
            is_optional=False,
            is_deprecated=False,
            factory_default=Rulespec.NO_FACTORY_DEFAULT,
            create_manual_check=True,
    ):
        # type: (str, Type[RulespecGroup], Callable[[], ValueSpec], Optional[Callable[[], Text]], str, Optional[str], Optional[Callable[[], Text]], Optional[Callable[[], ValueSpec]], Optional[Callable[[], Text]], bool, bool, Any, bool) -> None
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

        super(CheckParameterRulespecWithItem, self).__init__(
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
            valuespec=self._rulespec_valuespec)

        self.manual_check_parameter_rulespec_instance = None
        if create_manual_check:
            self.manual_check_parameter_rulespec_instance = _get_manual_check_parameter_rulespec_instance(
                group=self.group,
                check_group_name=check_group_name,
                title=title,
                parameter_valuespec=parameter_valuespec,
                item_spec=item_spec,
                is_optional=is_optional,
                is_deprecated=is_deprecated,
            )

    @property
    def check_group_name(self):
        # type: () -> str
        return self._check_group_name

    def _rulespec_valuespec(self):
        # type: () -> ValueSpec
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

        super(CheckParameterRulespecWithoutItem, self).__init__(
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
            self.manual_check_parameter_rulespec_instance = _get_manual_check_parameter_rulespec_instance(
                group=self.group,
                check_group_name=check_group_name,
                title=title,
                parameter_valuespec=parameter_valuespec,
                is_optional=is_optional,
                is_deprecated=is_deprecated,
            )

    @property
    def check_group_name(self):
        # type: () -> str
        return self._check_group_name

    def _rulespec_valuespec(self):
        # type: () -> ValueSpec
        return _wrap_valuespec_in_timeperiod_valuespec(self._parameter_valuespec())


def _wrap_valuespec_in_timeperiod_valuespec(valuespec):
    # type: (ValueSpec) -> ValueSpec
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
    def __init__(self,
                 group,
                 check_group_name,
                 parameter_valuespec=None,
                 title=None,
                 item_spec=None,
                 is_optional=False,
                 is_deprecated=False):

        # Mandatory keys
        self._check_group_name = check_group_name
        name = "static_checks:%s" % self._check_group_name

        arg_infos = [
            # (arg, is_callable, none_allowed)
            (check_group_name, False, False),
            (parameter_valuespec, True, True),
            (item_spec, True, True),
        ]
        _validate_function_args(arg_infos, name)
        super(ManualCheckParameterRulespec, self).__init__(
            group=group,
            name=name,
            title=title,
            is_optional=is_optional,
            is_deprecated=is_deprecated,

            # Explicit set
            valuespec=self._rulespec_valuespec,
            match_type="all",
        )

        # Optional keys
        self._parameter_valuespec = parameter_valuespec
        self._rule_value_item_spec = item_spec

    @property
    def check_group_name(self):
        # type: () -> str
        return self._check_group_name

    def _rulespec_valuespec(self):
        # type: () -> ValueSpec
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

    def _get_item_spec(self):
        # type: () -> ValueSpec
        """Not used as condition, only for the rule value valuespec"""
        if self._rule_value_item_spec:
            return self._rule_value_item_spec()

        return FixedValue(
            None,
            totext='',
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
        **kwargs):

    factory_default = kwargs.get("factory_default", Rulespec.NO_FACTORY_DEFAULT)

    if isinstance(group, six.string_types):
        group = get_rulegroup(group).__class__

    class_kwargs = {
        "name": varname,
        "group": group,
        "match_type": match,
        "factory_default": factory_default,
        "is_optional": optional,
        "is_deprecated": deprecated,
    }

    if valuespec is not None:
        class_kwargs["valuespec"] = lambda: valuespec

    if varname.startswith("static_checks:"):
        base_class = ManualCheckParameterRulespec
    elif varname.startswith("checkgroup_parameters:"):
        base_class = CheckParameterRulespecWithItem if itemtype is not None else CheckParameterRulespecWithoutItem
    elif valuespec is None:
        base_class = BinaryServiceRulespec if itemtype is not None else BinaryHostRulespec
    else:
        base_class = ServiceRulespec if itemtype is not None else HostRulespec

    if varname.startswith("static_checks:") or varname.startswith("checkgroup_parameters:"):
        class_kwargs["check_group_name"] = varname.split(":", 1)[1]

    if title is not None:
        class_kwargs["title"] = lambda: title

    for name, value, lambda_enclosed in [
        ("help_func", help, True),
        ("item_type", itemtype, False),
        ("item_spec", itemspec, True),
        ("item_name", itemname, True),
        ("item_help", itemhelp, True),
    ]:
        if value is not None:
            if lambda_enclosed:
                class_kwargs[name] = lambda v=value: v
            else:
                class_kwargs[name] = value

    if not itemname and itemtype == "service":
        class_kwargs["item_name"] = lambda: _("Service")

    rulespec_registry.register(base_class(**class_kwargs))


class RulespecRegistry(cmk.utils.plugin_registry.InstanceRegistry):
    def __init__(self, group_registry):
        super(RulespecRegistry, self).__init__()
        self._group_registry = group_registry

    def plugin_base_class(self):
        return Rulespec

    def plugin_name(self, instance):
        # type: (Rulespec) -> str
        return instance.name

    def get_by_group(self, group_name):
        # type: (str) -> List[Rulespec]
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

    def register(self, instance):
        # type: (Rulespec) -> None
        if not isinstance(instance, Rulespec):
            MKGeneralException(
                _("!!! Error: Received class in RulespecRegistry:register %r") % instance)

        if isinstance(instance,
                      (CheckParameterRulespecWithItem, CheckParameterRulespecWithoutItem)):

            manual_instance = instance.manual_check_parameter_rulespec_instance  # type: Any
            if manual_instance:
                subgroup_key = "static/" + manual_instance.group().sub_group_name
                if subgroup_key not in rulespec_group_registry:
                    rulespec_group_registry.register(manual_instance.group)

                super(RulespecRegistry, self).register(manual_instance)

        super(RulespecRegistry, self).register(instance)

    def register_without_manual_check_rulespec(self, instance):
        # type: (Rulespec) -> None
        """Use this register method to prevent adding a manual check rulespec"""
        if not isinstance(instance, Rulespec):
            MKGeneralException(
                _("!!! Error: Received class in RulespecRegistry:register_manual_check_rulespec %r")
                % instance)
            return
        super(RulespecRegistry, self).register(instance)


class CheckTypeGroupSelection(ElementSelection):
    def __init__(self, checkgroup, **kwargs):
        super(CheckTypeGroupSelection, self).__init__(**kwargs)
        self._checkgroup = checkgroup

    def get_elements(self):
        checks = check_mk_local_automation("get-check-information")
        elements = dict([(cn, "%s - %s" % (cn, c["title"]))
                         for (cn, c) in checks.items()
                         if c.get("group") == self._checkgroup])
        return elements

    def value_to_text(self, value):
        return "<tt>%s</tt>" % value


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
        super(TimeperiodValuespec, self).__init__(
            title=valuespec.title(),
            help=valuespec.help(),
        )
        self._enclosed_valuespec = valuespec

    def default_value(self):
        # If nothing is configured, simply return the default value of the enclosed valuespec
        return self._enclosed_valuespec.default_value()

    def render_input(self, varprefix, value):
        # The display mode differs when the valuespec is activated
        vars_copy = dict(html.request.itervars())

        # The timeperiod mode can be set by either the GUI switch or by the value itself
        # GUI switch overrules the information stored in the value
        if html.request.has_var(self.tp_toggle_var):
            is_active = self._is_switched_on()
        else:
            is_active = self.is_active(value)

        # Set the actual used mode
        html.hidden_field(self.tp_current_mode, "%d" % is_active)

        mode = _("Disable") if is_active else _("Enable")
        vars_copy[self.tp_toggle_var] = "%d" % (not is_active)
        toggle_url = html.makeuri(vars_copy.items())

        if is_active:
            value = self._get_timeperiod_value(value)
            self._get_timeperiod_valuespec().render_input(varprefix, value)
            html.buttonlink(toggle_url,
                            _("%s timespecific parameters") % mode,
                            class_=["toggle_timespecific_parameter"])
        else:
            value = self._get_timeless_value(value)
            r = self._enclosed_valuespec.render_input(varprefix, value)
            html.buttonlink(toggle_url,
                            _("%s timespecific parameters") % mode,
                            class_=["toggle_timespecific_parameter"])
            return r

    def value_to_text(self, value):
        text = ""
        if self.is_active(value):
            # TODO/Phantasm: highlight currently active timewindow
            text += self._get_timeperiod_valuespec().value_to_text(value)
        else:
            text += self._enclosed_valuespec.value_to_text(value)
        return text

    def from_html_vars(self, varprefix):
        if html.request.var(self.tp_current_mode) == "1":
            # Fetch the timespecific settings
            parameters = self._get_timeperiod_valuespec().from_html_vars(varprefix)
            if parameters[self.tp_values_key]:
                return parameters

            # Fall back to enclosed valuespec data when no timeperiod is set
            return parameters[self.tp_default_value_key]

        # Fetch the data from the enclosed valuespec
        return self._enclosed_valuespec.from_html_vars(varprefix)

    def canonical_value(self):
        return self._enclosed_valuespec.canonical_value()

    def validate_datatype(self, value, varprefix):
        if self.is_active(value):
            self._get_timeperiod_valuespec().validate_datatype(value, varprefix)
        else:
            self._enclosed_valuespec.validate_datatype(value, varprefix)

    def validate_value(self, value, varprefix):
        if self.is_active(value):
            self._get_timeperiod_valuespec().validate_value(value, varprefix)
        else:
            self._enclosed_valuespec.validate_value(value, varprefix)

    def _get_timeperiod_valuespec(self):
        return Dictionary(
            elements=[
                (self.tp_default_value_key,
                 Transform(self._enclosed_valuespec,
                           title=_("Default parameters when no timeperiod matches"))),
                (self.tp_values_key,
                 ListOf(
                     Tuple(elements=[
                         TimeperiodSelection(
                             title=_("Match only during timeperiod"),
                             help=_("Match this rule only during times where the "
                                    "selected timeperiod from the monitoring "
                                    "system is active."),
                         ), self._enclosed_valuespec
                     ]),
                     title=_("Configured timeperiod parameters"),
                 )),
            ],
            optional_keys=False,
        )

    # Checks whether the tp-mode is switched on through the gui
    def _is_switched_on(self):
        return html.request.var(self.tp_toggle_var) == "1"

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


rulespec_registry = RulespecRegistry(rulespec_group_registry)
