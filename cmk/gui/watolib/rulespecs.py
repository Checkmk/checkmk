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
from typing import Text, List, Type, Optional, Any  # pylint: disable=unused-import
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
        }  # type: Dict[Type[RulespecGroup], Type[RulespecSubGroup]]

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


class Rulespec(object):
    __metaclass__ = abc.ABCMeta

    # needed for unique ID
    NO_FACTORY_DEFAULT = []  # type: list
    # means this ruleset is not used if no rule is entered
    FACTORY_DEFAULT_UNUSED = []  # type: list

    @abc.abstractproperty
    def name(self):
        # type: () -> str
        raise NotImplementedError()

    @abc.abstractproperty
    def group(self):
        # type: () -> Type[RulespecGroup]
        raise NotImplementedError()

    @abc.abstractproperty
    def valuespec(self):
        # type: () -> Optional[ValueSpec]
        raise NotImplementedError()

    @abc.abstractproperty
    def title(self):
        # type: () -> Text
        raise NotImplementedError()

    @abc.abstractproperty
    def help(self):
        # type: () -> Text
        raise NotImplementedError()

    @abc.abstractproperty
    def is_for_services(self):
        # type: () -> bool
        raise NotImplementedError()

    @abc.abstractproperty
    def item_type(self):
        # type: () -> Optional[str]
        raise NotImplementedError()

    @abc.abstractproperty
    def item_name(self):
        # type: () -> Optional[Text]
        raise NotImplementedError()

    @abc.abstractproperty
    def item_spec(self):
        # type: () -> Optional[ValueSpec]
        raise NotImplementedError()

    @abc.abstractproperty
    def item_help(self):
        # type: () -> Optional[Text]
        raise NotImplementedError()

    @abc.abstractproperty
    def item_enum(self):
        # type: () -> Optional[List]
        raise NotImplementedError()

    @property
    def group_name(self):
        # type: () -> Text
        return self.group().name

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
        return "first"

    @property
    def factory_default(self):
        # type: () -> Any
        return self.NO_FACTORY_DEFAULT

    @property
    def is_optional(self):
        # type: () -> bool
        return False

    @property
    def is_deprecated(self):
        # type: () -> bool
        return False


class ABCHostRulespec(object):
    """Base class for all rulespecs managing host rule sets"""
    @property
    def is_for_services(self):
        return False

    @property
    def item_type(self):
        # type: () -> None
        return None

    @property
    def item_name(self):
        # type: () -> None
        return None

    @property
    def item_spec(self):
        # type: () -> None
        return None

    @property
    def item_help(self):
        # type: () -> None
        return None

    @property
    def item_enum(self):
        # type: () -> None
        return None


class ABCServiceRulespec(object):
    """Base class for all rulespecs managing service rule sets"""
    @property
    def is_for_services(self):
        return True

    # TODO: Is this always service?
    @property
    def item_type(self):
        # type: () -> Optional[str]
        return "service"

    @property
    def item_name(self):
        # type: () -> Optional[Text]
        if self.item_type == "service":
            return _("Service")
        return None

    @property
    def item_spec(self):
        # type: () -> Optional[ValueSpec]
        return None

    @property
    def item_help(self):
        # type: () -> Optional[Text]
        return None

    @property
    def item_enum(self):
        # type: () -> Optional[List]
        """List of choices to select using a ListChoice() when editing a rule
        In case this is set this replaces the regular service condition input (see EditRuleMode._get_rule_conditions())
        """
        return None


class ABCBinaryRulespec(Rulespec):
    """Base class for all rulespecs that create a binary host/service rule list"""
    @property
    def valuespec(self):
        return None

    @abc.abstractproperty
    def title(self):
        # type: () -> Text
        raise NotImplementedError()

    @abc.abstractproperty
    def help(self):
        # type: () -> Text
        raise NotImplementedError()


class BinaryHostRulespec(ABCHostRulespec, ABCBinaryRulespec):
    pass


class BinaryServiceRulespec(ABCServiceRulespec, ABCBinaryRulespec):
    pass


class ABCValueRulespec(Rulespec):
    """Base class for all rulespecs that create a host/service list with values"""
    @abc.abstractproperty
    def valuespec(self):
        # type: () -> ValueSpec
        raise NotImplementedError()

    @property
    def title(self):
        # type: () -> Text
        return self.valuespec.title()

    @property
    def help(self):
        # type: () -> Text
        return self.valuespec.help()


class HostRulespec(ABCHostRulespec, ABCValueRulespec):
    """Base class for all rulespecs managing host rule sets with values"""
    pass


class ServiceRulespec(ABCServiceRulespec, ABCValueRulespec):
    """Base class for all rulespecs managing service rule sets with values"""
    pass


class CheckParameterRulespecWithItem(ServiceRulespec):
    """Base class for all rulespecs managing parameters for check groups with item

    These have to be named checkgroup_parameters:<name-of-checkgroup>. These
    parameters affect the discovered services only, not the manually configured
    checks."""
    @abc.abstractproperty
    def check_group_name(self):
        raise NotImplementedError()

    @property
    def name(self):
        return "checkgroup_parameters:%s" % self.check_group_name

    @property
    def item_type(self):
        return "item"

    # TODO: Cleanup call sites to use item_spec directly
    @property
    def item_name(self):
        return self.item_spec.title()

    # TODO: Cleanup call sites to use item_spec directly
    @property
    def item_help(self):
        return self.item_spec.help()

    @property
    def item_enum(self):
        if isinstance(self.item_spec, (DropdownChoice, OptionalDropdownChoice)):
            return self.item_spec._choices
        return None

    @property
    def valuespec(self):
        # type: () -> ValueSpec
        """Enclose the parameter valuespec with a TimeperiodValuespec.
        The given valuespec will be transformed to a list of valuespecs,
        whereas each element can be set to a specific timeperiod.
        """
        parameter_vs = self.parameter_valuespec
        if isinstance(parameter_vs, TimeperiodValuespec):
            # Legacy check parameters registered through register_check_parameters() already
            # have their valuespec wrapped in TimeperiodValuespec.
            return parameter_vs
        return TimeperiodValuespec(self.parameter_valuespec)

    @abc.abstractproperty
    def parameter_valuespec(self):
        # type: () -> ValueSpec
        raise NotImplementedError()


class CheckParameterRulespecWithoutItem(HostRulespec):
    """Base class for all rulespecs managing parameters for check groups without item

    These have to be named checkgroup_parameters:<name-of-checkgroup>. These
    parameters affect the discovered services only, not the manually configured
    checks."""
    @abc.abstractproperty
    def check_group_name(self):
        raise NotImplementedError()

    @property
    def name(self):
        return "checkgroup_parameters:%s" % self.check_group_name

    @property
    def valuespec(self):
        # type: () -> ValueSpec
        """Enclose the parameter valuespec with a TimeperiodValuespec.
        The given valuespec will be transformed to a list of valuespecs,
        whereas each element can be set to a specific timeperiod.
        """
        parameter_vs = self.parameter_valuespec
        if isinstance(parameter_vs, TimeperiodValuespec):
            # Legacy check parameters registered through register_check_parameters() already
            # have their valuespec wrapped in TimeperiodValuespec.
            return parameter_vs
        return TimeperiodValuespec(self.parameter_valuespec)

    @abc.abstractproperty
    def parameter_valuespec(self):
        # type: () -> ValueSpec
        raise NotImplementedError()


class ManualCheckParameterRulespec(HostRulespec):
    """Base class for all rulespecs managing manually configured checks

    These have to be named static_checks:<name-of-checkgroup>"""
    @abc.abstractproperty
    def check_group_name(self):
        raise NotImplementedError()

    @property
    def name(self):
        return "static_checks:%s" % self.check_group_name

    @property
    def valuespec(self):
        """Wraps the parameter together with the other needed valuespecs

        This should not be overridden by specific manual checks. Normally the parameter_valuespec
        is the one that should be overridden.
        """
        parameter_vs = self.parameter_valuespec
        return Tuple(
            title=parameter_vs.title(),
            elements=[
                CheckTypeGroupSelection(
                    self.check_group_name,
                    title=_("Checktype"),
                    help=_("Please choose the check plugin"),
                ),
                self.item_spec,
                parameter_vs,
            ],
        )

    @property
    def parameter_valuespec(self):
        return FixedValue(
            None,
            help=_("This check has no parameters."),
            totext="",
        )

    @property
    def item_spec(self):
        """Not used as condition, only for the rule value valuespec"""
        return FixedValue(
            None,
            totext='',
        )

    @property
    def match_type(self):
        """Manual check rulespecs always use this match type"""
        return "all"


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

    class_attrs = {
        "name": varname,
        "group": group,
        "match_type": match,
        "factory_default": factory_default,
        "is_optional": optional,
        "is_deprecated": deprecated,
    }

    if valuespec is not None:
        class_attrs["valuespec"] = valuespec

    if varname.startswith("static_checks:"):
        base_class = ManualCheckParameterRulespec
    elif varname.startswith("checkgroup_parameters:"):
        base_class = CheckParameterRulespecWithItem if itemtype is not None else CheckParameterRulespecWithoutItem
    elif valuespec is None:
        base_class = BinaryServiceRulespec if itemtype is not None else BinaryHostRulespec
    else:
        base_class = ServiceRulespec if itemtype is not None else HostRulespec

    if varname.startswith("static_checks:") or varname.startswith("checkgroup_parameters:"):
        class_attrs["check_group_name"] = varname.split(":", 1)[1]

    if title is not None:
        class_attrs["title"] = title

    if help is not None:
        class_attrs["help"] = help

    class_attrs.update({
        "item_spec": itemspec,
        "item_help": itemhelp,
        "item_enum": itemenum,
        "item_type": itemtype,
    })

    if not itemname and itemtype == "service":
        class_attrs["item_name"] = _("Service")
    else:
        class_attrs["item_name"] = itemname

    rulespec_class = type("LegacyRulespec%s" % varname, (base_class,), class_attrs)
    rulespec_registry.register(rulespec_class)


class RulespecRegistry(cmk.utils.plugin_registry.ClassRegistry):
    def __init__(self, group_registry):
        super(RulespecRegistry, self).__init__()
        self._group_registry = group_registry

    def plugin_base_class(self):
        return Rulespec

    def plugin_name(self, plugin_class):
        return plugin_class().name

    def get_by_group(self, group_name):
        # type: (str) -> List[Rulespec]
        rulespecs = []

        if group_name not in self._group_registry:
            raise KeyError()

        for rulespec_class in self.values():
            rulespec = rulespec_class()
            if rulespec.group_name == group_name:
                rulespecs.append(rulespec)
        return rulespecs

    def get_all_groups(self):
        """Returns a list of all rulespec groups that have rules registered for

        Can not use direct rulespec_group_registry access for this, because the
        group registry does not know whether a group is registered for it"""
        return list(set(gc().group_name for gc in self.values()))

    def register(self, plugin_class):
        """Check group parameter rulespecs (checkgroup_parameters:*) added to the registry
        are registering a second rulespec for manual check registration. This may be
        prevented by setting the argument with_manual_check_rulespec=False"""
        super(RulespecRegistry, self).register(plugin_class)

        if issubclass(plugin_class,
                      (CheckParameterRulespecWithItem, CheckParameterRulespecWithoutItem)):
            self._register_manual_check_rulespec(plugin_class)

    def register_without_manual_check_rulespec(self, plugin_class):
        """Use this register method to prevent adding a manual check rulespec"""
        super(RulespecRegistry, self).register(plugin_class)

    def _register_manual_check_rulespec(self, plugin_class):
        """Register a manual check configuration rulespec based on the given checkgroup parameter
        rulespec

        The user will be able to configure manual checks of the check types that are registered
        for this check group instead of relying on the service discovery.

        Static checks are always host rulespecs.
        """

        param_rulespec = plugin_class()

        class_attrs = {
            "check_group_name": param_rulespec.check_group_name,
            "title": param_rulespec.title,
            "is_deprecated": param_rulespec.is_deprecated,
        }

        valuespec = param_rulespec.valuespec
        if valuespec:
            if not valuespec.title():
                # TODO: Clean up this hack
                valuespec._title = _("Parameters")

            class_attrs["parameter_valuespec"] = valuespec

        item_spec = param_rulespec.item_spec
        if item_spec:
            class_attrs["item_spec"] = item_spec

        # There may be no RulespecSubGroup declaration for the static checks.
        # Create some based on the regular check groups (which should have a definition)
        group = param_rulespec.group()
        try:
            subgroup_key = "static/" + group.sub_group_name
            checkparams_static_sub_group_class = rulespec_group_registry[subgroup_key]
        except KeyError:
            main_group_static_class = rulespec_group_registry["static"]
            checkparams_static_sub_group_class = type("%sStatic" % group.__class__.__name__,
                                                      (group.__class__,), {
                                                          "main_group": main_group_static_class,
                                                      })
            rulespec_group_registry.register(checkparams_static_sub_group_class)

        class_attrs["group"] = checkparams_static_sub_group_class

        manual_check_class = type("ManualCheck%s", (ManualCheckParameterRulespec,), class_attrs)
        rulespec_registry.register(manual_check_class)


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
