#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import logging
from collections.abc import Iterable, Iterator, Sequence
from pprint import pformat
from typing import Generic, NamedTuple, Protocol, TypeVar

from cmk.utils.check_utils import ParametersTypeAlias
from cmk.utils.rulesets.definition import RuleGroup

from cmk.checkengine.plugins import AgentBasedPlugins, CheckPlugin, InventoryPlugin

from cmk.gui.inventory import RulespecGroupInventory
from cmk.gui.plugins.wato.utils import RulespecGroupCheckParametersDiscovery
from cmk.gui.utils.rule_specs.legacy_converter import GENERATED_GROUP_PREFIX
from cmk.gui.wato import RulespecGroupDiscoveryCheckParameters
from cmk.gui.watolib.rulespecs import (
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    Rulespec,
    rulespec_registry,
    RulespecSubGroup,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")
TF = TypeVar("TF", bound=Rulespec)
TC = TypeVar("TC", bound=CheckPlugin | InventoryPlugin)


class MergeKey(NamedTuple):
    type_name: str
    name: str


class DefaultLoadingFailed(Exception):
    pass


class Base(Generic[T], abc.ABC):
    type: str

    def __init__(self, element: T) -> None:
        self._element: T = element

    @abc.abstractmethod
    def get_merge_name(self) -> str:
        """
        return name by which Wato and Plugin lists are merged
        """

    def get_name(self) -> str:
        """
        return name that identifies this element
        """
        return self.get_merge_name()

    def get_merge_key(self) -> MergeKey:
        return MergeKey(self.type, self.get_merge_name())

    @abc.abstractmethod
    def get_description(self) -> str:
        """
        return human readable unique identifier for this element
        """

    def __gt__(self, other: object) -> bool:
        if other is None or not isinstance(other, Base):
            raise ValueError()
        return self.get_merge_key() > other.get_merge_key()

    def __eq__(self, other: object) -> bool:
        if other is None or not isinstance(other, Base):
            return False
        return self.get_merge_key() == other.get_merge_key()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self._element}>"


class BaseProtocol(Protocol):
    type: str

    def get_name(self) -> str: ...

    def get_merge_name(self) -> str: ...

    def get_description(self) -> str: ...

    def __eq__(self, other: object) -> bool: ...

    def __gt__(self, other: object) -> bool: ...


class WatoProtocol(BaseProtocol, Protocol):
    def validate_parameter(self, parameters: ParametersTypeAlias | None) -> Exception | None: ...


class PluginProtocol(BaseProtocol, Protocol):
    def get_default_parameters(self) -> ParametersTypeAlias | None: ...


class Plugin(Base[TC], abc.ABC):
    def get_description(self) -> str:
        return f"{self.type}-plugin '{self.get_name()}'"

    def get_name(self) -> str:
        return str(self._element.name)

    @abc.abstractmethod
    def get_default_parameters(self) -> ParametersTypeAlias | None: ...


class PluginDiscovery(Plugin[CheckPlugin]):
    type = "discovery"

    def get_merge_name(self) -> str:
        assert self._element.discovery_ruleset_name
        return str(self._element.discovery_ruleset_name)

    def get_default_parameters(self) -> ParametersTypeAlias | None:
        return self._element.discovery_default_parameters


class PluginInventory(Plugin[InventoryPlugin]):
    type = "inventory"

    def get_merge_name(self) -> str:
        assert self._element.ruleset_name
        return str(self._element.ruleset_name)

    def get_default_parameters(self) -> ParametersTypeAlias | None:
        return self._element.defaults


class PluginCheck(Plugin[CheckPlugin]):
    type = "check"

    def get_merge_name(self) -> str:
        assert self._element.check_ruleset_name
        return str(self._element.check_ruleset_name)

    def get_default_parameters(self) -> ParametersTypeAlias | None:
        return self._element.check_default_parameters

    def has_item(self) -> bool:
        return "%" in self._element.service_name


class Wato(Base[TF]):
    def get_description(self) -> str:
        return f"wato {self.type}-rule '{self.get_name()}'"

    def validate_parameter(self, parameters: ParametersTypeAlias | None) -> Exception | None:
        try:
            self._element.valuespec.validate_datatype(parameters, "")
            self._element.valuespec.validate_value(parameters, "")
        except Exception as exception:
            return exception
        return None


class WatoDiscovery(Wato[Rulespec]):
    type = "discovery"

    def get_merge_name(self) -> str:
        return self._element.name


class WatoInventory(Wato[Rulespec]):
    type = "inventory"

    def get_merge_name(self) -> str:
        return self._element.name


class WatoCheck(Wato[CheckParameterRulespecWithoutItem | CheckParameterRulespecWithItem]):
    type = "check"

    def get_merge_name(self) -> str:
        return self._element.check_group_name

    def get_name(self) -> str:
        return self._element.name

    def has_item(self) -> bool:
        return isinstance(self._element, CheckParameterRulespecWithItem)


def load_plugin(agent_based_plugins: AgentBasedPlugins) -> Iterator[PluginProtocol]:
    for check_element in agent_based_plugins.check_plugins.values():
        if check_element.check_ruleset_name is not None:
            yield PluginCheck(check_element)
    for discovery_element in agent_based_plugins.check_plugins.values():
        if discovery_element.discovery_ruleset_name is not None:
            yield PluginDiscovery(discovery_element)
    for inventory_element in agent_based_plugins.inventory_plugins.values():
        if inventory_element.ruleset_name is not None:
            yield PluginInventory(inventory_element)


def load_wato() -> Iterator[WatoProtocol]:
    for element in rulespec_registry.values():
        if isinstance(group := element.group(), RulespecGroupCheckParametersDiscovery) or (
            isinstance(group, RulespecSubGroup)
            and GENERATED_GROUP_PREFIX in group.__class__.__name__
            and issubclass(group.main_group, RulespecGroupDiscoveryCheckParameters)
        ):
            yield WatoDiscovery(element)
        elif element.group == RulespecGroupInventory:
            yield WatoInventory(element)
        elif isinstance(
            element,
            CheckParameterRulespecWithItem | CheckParameterRulespecWithoutItem,
        ):
            yield WatoCheck(element)


def test_plugin_vs_wato(agent_based_plugins: AgentBasedPlugins) -> None:
    error_reporter = ErrorReporter()
    for plugin, wato in merge(sorted(load_plugin(agent_based_plugins)), sorted(load_wato())):
        if plugin is None and wato is not None:
            error_reporter.report_wato_unused(wato)
        elif wato is None and plugin is not None:
            error_reporter.report_wato_missing(plugin)
        else:
            assert plugin is not None and wato is not None, "something is wrong with merge()"
            error_reporter.run_tests(plugin, wato)

    error_reporter.raise_last_default_loading_exception()
    assert not error_reporter.failures()
    error_reporter.test_for_vanished_known_problems()


class ErrorReporter:
    KNOWN_WATO_UNUSED = {
        # type # name
        ("check", RuleGroup.CheckgroupParameters("checkmk_agent_plugins")),
        ("check", RuleGroup.CheckgroupParameters("ceph_status")),
        ("check", RuleGroup.CheckgroupParameters("mailqueue_length")),
        ("check", RuleGroup.CheckgroupParameters("mssql_blocked_sessions")),
        ("check", RuleGroup.CheckgroupParameters("postgres_sessions")),
        ("check", RuleGroup.CheckgroupParameters("ruckus_mac")),
        ("check", RuleGroup.CheckgroupParameters("systemd_services")),
        ("check", RuleGroup.CheckgroupParameters("temperature_trends")),
        ("check", RuleGroup.CheckgroupParameters("prism_container")),
        ("check", RuleGroup.CheckgroupParameters("azure_databases")),  # deprecated
        ("check", RuleGroup.CheckgroupParameters("azure_storageaccounts")),  # deprecated
        ("discovery", "discovery_systemd_units_services_rules"),
        ("inventory", RuleGroup.ActiveChecks("cmk_inv")),
        ("inventory", RuleGroup.InvParameters("inv_if")),
        ("inventory", RuleGroup.InvParameters("lnx_sysctl")),
        ("inventory", "inv_retention_intervals"),
        (
            "inventory",
            RuleGroup.InvExports("software_csv"),
        ),  # deprecated since 2.2
    }

    ENFORCING_ONLY_RULESETS = {
        # These plugins only have rules to be enforced (and configured),
        # but no rules to configure discovered services.
        # This may or may not be intentional and/or reasonable.
        # If the plugins are discovered by default, it is likely to be unintentional.
        # type # instance # wato
        ("check", "3ware_units", "raid"),  # has no params, but can be enforced.
        ("check", "lsi_array", "raid"),  # has no params, but can be enforced.
        ("check", "md", "raid"),  # has no params, but can be enforced.
        ("check", "netstat", "tcp_connections"),  # can only be enforced, never discovered.
        ("check", "nvidia_errors", "hw_errors"),
        ("check", "vbox_guest", "vm_state"),
        ("check", "win_netstat", "tcp_connections"),
        ("check", "wmic_process", "wmic_process"),
        ("check", "zertificon_mail_queues", "zertificon_mail_queues"),
        ("check", "zpool_status", "zpool_status"),
    }

    KNOWN_WATO_MISSING = {
        # type # instance # wato
        ("discovery", "fileinfo", "fileinfo_groups"),
        ("discovery", "fileinfo_groups", "fileinfo_groups"),
        ("discovery", "sap_hana_fileinfo", "fileinfo_groups"),
        ("discovery", "sap_hana_fileinfo_groups", "fileinfo_groups"),
        ("discovery", "logwatch_groups", "logwatch_groups"),
        ("discovery", "logwatch", "logwatch_groups"),
        ("inventory", "inv_if", "inv_if"),
        ("inventory", "lnx_sysctl", "lnx_sysctl"),
    }

    def __init__(self) -> None:
        self._last_exception: DefaultLoadingFailed | None = None
        self._failures: list[str] = []
        self._known_wato_unused = self.KNOWN_WATO_UNUSED.copy()
        self._known_wato_missing = self.KNOWN_WATO_MISSING | self.ENFORCING_ONLY_RULESETS

    def failures(self) -> Sequence[str]:
        return self._failures

    def report_wato_unused(self, wato: WatoProtocol) -> None:
        element = (wato.type, wato.get_name())
        if element in self._known_wato_unused:
            self._known_wato_unused.remove(element)
            return
        msg = f"{wato.get_description()} is not used by any plugin"
        logger.info(msg)
        self._failures.append(msg)

    def report_wato_missing(self, plugin: PluginProtocol) -> None:
        element = (plugin.type, plugin.get_name(), plugin.get_merge_name())
        if element in self._known_wato_missing:
            self._known_wato_missing.remove(element)
            return
        msg = (
            f"{plugin.get_description()} wants to use "
            f"wato ruleset '{plugin.get_merge_name()}' but this can not be found"
        )
        logger.info(msg)
        self._failures.append(msg)

    def run_tests(self, plugin: PluginProtocol, wato: WatoProtocol) -> None:
        # try to load the plug-in defaults into wato ruleset
        exception = wato.validate_parameter(plugin.get_default_parameters())
        if exception:
            self._report_error_loading_defaults(plugin, wato, exception)

        # see if both plug-in and wato have the same idea about items
        if isinstance(plugin, PluginCheck) and isinstance(wato, WatoCheck):
            if wato.has_item() != plugin.has_item():
                self._report_check_item_requirements(plugin, wato)

    def _report_check_item_requirements(
        self,
        plugin: PluginCheck,
        wato: WatoCheck,
    ) -> None:
        msg = f"{plugin.get_description()} and {wato.get_description()} have different item requirements"
        logger.info("%s:", msg)
        logger.info("    wato   handles item: %r", wato.has_item())
        logger.info("    plug-in handles items: %r", plugin.has_item())
        self._failures.append(msg)

    def _report_error_loading_defaults(
        self,
        plugin: PluginProtocol,
        wato: WatoProtocol,
        exception: Exception,
    ) -> None:
        msg = (
            f"Loading the default value of {plugin.get_description()} "
            f"into {wato.get_description()} failed:\n    {exception.__class__.__name__}: {exception}"
        )
        logger.info(msg)
        self._last_exception = DefaultLoadingFailed(
            f"Loading the default value of {plugin.type} {plugin.get_name()} "
            f"into wato rulespec {wato.get_name()} failed! "
            "The original exception is reported above."
        )
        self._last_exception.__cause__ = exception
        self._failures.append(msg)

    def test_for_vanished_known_problems(self) -> None:
        """
        Generally test_plugin_vs_wato makes sure that the plug-in default values
        matches the structure of the wato ruleset.

        This particular test makes sure that the known defects defined in the
        `_known_*` class variables are up to date and don't have obsolete
        values.

        So If this test failes, chances are high you recently fixed such an
        mismatch! Then simply remove the element from the corresponding
        `_known_*` set.
        """
        # ci does not report the variables, so we print them...
        logger.info(pformat(self._known_wato_missing))
        logger.info(pformat(self._known_wato_unused))
        assert len(self._known_wato_missing) == 0
        assert len(self._known_wato_unused) == 0

    def raise_last_default_loading_exception(self) -> None:
        if self._last_exception is not None:
            raise self._last_exception


################################################################################
# implementation details
################################################################################


T_contra = TypeVar("T_contra", contravariant=True)


class SupportsGreaterThan(Protocol, Generic[T_contra]):
    def __gt__(self, other: T_contra) -> bool: ...


A = TypeVar("A", bound=SupportsGreaterThan)
B = TypeVar("B")


def merge(a: Iterable[A], b: Iterable[B]) -> Iterator[tuple[A | None, B | None]]:
    """
    merge a and b in a way that elements that are equal in a and b are in the
    same tuple.
    a and b have to be sorted before calling this function!
    """
    iter_a = iter(a)
    iter_b = iter(b)

    def next_a() -> A | None:
        try:
            return next(iter_a)
        except StopIteration:
            return None

    def next_b() -> B | None:
        try:
            return next(iter_b)
        except StopIteration:
            return None

    value_a = next_a()
    value_b = next_b()

    while True:
        if value_a is None and value_b is None:
            break
        if value_a is None:
            yield (None, value_b)
            value_b = next_b()
        elif value_b is None:
            yield (value_a, None)
            value_a = next_a()
        elif value_a == value_b:
            yield (value_a, value_b)
            prev_a = value_a
            prev_b = value_b
            value_a = next_a()
            value_b = next_b()
            if (prev_a == value_a) and (prev_b == value_b):
                continue
            while prev_a == value_a:
                yield (value_a, prev_b)
                value_a = next_a()
            while prev_b == value_b:
                yield (prev_a, value_b)
                value_b = next_b()
        elif value_a > value_b:
            yield (None, value_b)
            value_b = next_b()
        else:
            yield (value_a, None)
            value_a = next_a()


def test_merge() -> None:
    result = merge([1, 3, 5], [2, 3, 4])
    assert list(result) == [(1, None), (None, 2), (3, 3), (None, 4), (5, None)]
    result = merge([1, 1, 5], [2, 3, 4])
    assert list(result) == [(1, None), (1, None), (None, 2), (None, 3), (None, 4), (5, None)]
    result = merge([1], [2, 3, 4])
    assert list(result) == [(1, None), (None, 2), (None, 3), (None, 4)]
    result = merge([1, 1, 1, 4], [1, 2, 3, 4])
    assert list(result) == [(1, 1), (1, 1), (1, 1), (None, 2), (None, 3), (4, 4)]
    result = merge([1, 1, 1], [1, 1, 1])
    assert list(result) == [(1, 1), (1, 1), (1, 1)]


def test_compare() -> None:
    class CompareBase(Base[MergeKey]):
        def __init__(self, element: MergeKey) -> None:
            self._element: MergeKey
            super().__init__(element)

        def get_merge_key(self) -> MergeKey:
            return self._element

        def get_description(self) -> str:
            return ""

        def get_merge_name(self) -> str:
            return ""

    assert CompareBase(MergeKey("a", "")) < CompareBase(MergeKey("b", ""))
    assert CompareBase(MergeKey("a", "")) == CompareBase(MergeKey("a", ""))
    result = sorted([CompareBase(MergeKey("b", "zwei")), CompareBase(MergeKey("a", "eins"))])
    assert result[0]._element.name == "eins"
