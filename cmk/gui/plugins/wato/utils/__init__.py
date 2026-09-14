#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for Setup internals and the Setup plugins"""

from cmk.gui.valuespec import CascadingDropdown as CascadingDropdown
from cmk.gui.valuespec import FixedValue as FixedValue
from cmk.gui.valuespec import ListOf as ListOf
from cmk.gui.valuespec import RegExp as RegExp
from cmk.gui.valuespec import TextInput as TextInput
from cmk.gui.wato import Levels as Levels
from cmk.gui.wato import PredictiveLevels as PredictiveLevels
from cmk.gui.watolib.config_variable_groups import (
    ConfigVariableGroupUserInterface as ConfigVariableGroupUserInterface,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupCheckParametersApplications as RulespecGroupCheckParametersApplications,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupCheckParametersDiscovery as RulespecGroupCheckParametersDiscovery,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupCheckParametersEnvironment as RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupCheckParametersHardware as RulespecGroupCheckParametersHardware,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupCheckParametersNetworking as RulespecGroupCheckParametersNetworking,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupCheckParametersOperatingSystem as RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupCheckParametersPrinters as RulespecGroupCheckParametersPrinters,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupCheckParametersStorage as RulespecGroupCheckParametersStorage,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupCheckParametersVirtualization as RulespecGroupCheckParametersVirtualization,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupEnforcedServicesApplications as RulespecGroupEnforcedServicesApplications,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupEnforcedServicesEnvironment as RulespecGroupEnforcedServicesEnvironment,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupEnforcedServicesHardware as RulespecGroupEnforcedServicesHardware,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupEnforcedServicesNetworking as RulespecGroupEnforcedServicesNetworking,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupEnforcedServicesStorage as RulespecGroupEnforcedServicesStorage,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupHostsMonitoringRulesVarious as RulespecGroupHostsMonitoringRulesVarious,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupMonitoringAgents as RulespecGroupMonitoringAgents,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupMonitoringAgentsGenericOptions as RulespecGroupMonitoringAgentsGenericOptions,
)
from cmk.gui.watolib.rulespecs import BinaryHostRulespec as BinaryHostRulespec
from cmk.gui.watolib.rulespecs import (
    CheckParameterRulespecWithItem as CheckParameterRulespecWithItem,
)
from cmk.gui.watolib.rulespecs import (
    CheckParameterRulespecWithoutItem as CheckParameterRulespecWithoutItem,
)
from cmk.gui.watolib.rulespecs import HostRulespec as HostRulespec
from cmk.gui.watolib.rulespecs import ManualCheckParameterRulespec as ManualCheckParameterRulespec
from cmk.gui.watolib.rulespecs import rulespec_group_registry as rulespec_group_registry
from cmk.gui.watolib.rulespecs import rulespec_registry as rulespec_registry
from cmk.gui.watolib.rulespecs import RulespecGroup as RulespecGroup
from cmk.gui.watolib.rulespecs import RulespecSubGroup as RulespecSubGroup
from cmk.gui.watolib.rulespecs import TimeperiodValuespec as TimeperiodValuespec
