#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


#########################################################################################
#                                                                                       #
#                                 !!   W A T C H   O U T   !!                           #
#                                                                                       #
#   The logwatch plug-in is notorious for being an exception to just about every rule   #
#   or best practice that applies to check plug-in development.                         #
#   It is highly discouraged to use this a an example!                                  #
#                                                                                       #
#########################################################################################

from collections.abc import Mapping, Sequence
from pathlib import Path

from cmk.agent_based.v2 import CheckPlugin
from cmk.base.configlib.loaded_config import BaseConfig
from cmk.base.configlib.servicename import make_final_service_name_config, PassiveServiceNameConfig
from cmk.ccc.hostaddress import HostName
from cmk.checkengine.plugins import (
    CheckPluginName,
    ServiceID,
)
from cmk.logwatch.config import (
    NEVER_DISCOVER_SERVICE_LABELS,
    ParameterLogwatchEc,
    ParameterLogwatchRules,
    set_global_state,
)
from cmk.utils.labels import LabelManager
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher


def set_global_logwatch_config(
    loaded_config: BaseConfig,
    matcher: RulesetMatcher,
    label_manager: LabelManager,
    *,
    omd_root: Path,
    var_dir: Path,
    debug: bool,
) -> None:
    set_global_state(
        _LogwatchConfig(
            loaded_config,
            matcher,
            label_manager,
            omd_root=omd_root,
            var_dir=var_dir,
            debug=debug,
        )
    )


class _LogwatchConfig:
    """Implementing logwatch rulesets / configuration

    Logwatch uses more configuration parameters that just its rulesets.
    It also uses the current host name, and the "effective service level".

    We consider 8 cases here: EC/¬EC, grouped/single, cluster/node.

    There are three logwatch rulesets:

    logwatch_rules:
        These contain the reclassification-patterns and -states.
        They are used:
            * In all 8 check functions
              ** match type "ALL"
              ** in logwatch_ec (gouped) they don't match on the item (the group),
                 but on the individual logfiles _in_ the group (bug or feature?).

    logwatch_ec:
        These contain forwarding parameters (which files + how) and a few flags.
        They are used:
            * As the 'official' check parameters in logwatch_ec (_not_ logwatch_ec_single)
              This implies match type "MERGED".
            * In all discovery functions, where in a "merged" style only the "restrict_logfiles"
              parameters is used to filter the logfiles (forwardig VS no forwarding).
            * In the EC case, they are "forwarded" to the check functions as discovered parameters.

    logwatch_groups:
        These contain grouping patterns for the ¬EC case.
        They are used:
            * As regular 'ALL' style discovery parameters for the ¬EC plugins.

    PROPOSAL:
    Way out: Change to one common discovery and two dedicated check paramater rulesets:

        Discovery ruleset (ONE for all plugins).
         * Match type: ALL.
         * Grouping patterns: List of tripples:
            ** <Group matches to one item 'group name'> | <matched logfiles are single items>
            ** <patterns (include/exclude?)>
            ** <forward these to EC or not>

        ¬EC check ruleset
         * Match type: MERGE
         * Reclassify-patterns and -states
         * matching regularly, i.e. on items or groups

        EC check ruleset
         * Match type: MERGE
         * Reclassify-patterns and -states
         * Forwarding parameters
         * matching regularly, i.e. on items or groups

    * Current configurations could be embedded in an update config step.
    * In the future, reclassification parameters would *always* be matched against the *item*.
    * Proposal: Grouping should work the same regardless of EC/¬EC
      (currently the options in EC are only 'group everything' or 'group nothing').
    """

    def __init__(
        self,
        loaded_config: BaseConfig,
        matcher: RulesetMatcher,
        label_manager: LabelManager,
        *,
        omd_root: Path,
        var_dir: Path,
        debug: bool,
    ) -> None:
        self._label_manager = label_manager
        self._matcher = matcher
        self._service_name_config = PassiveServiceNameConfig(
            make_final_service_name_config(loaded_config, matcher),
            user_defined_service_names=loaded_config.service_descriptions,
            use_new_names_for=loaded_config.use_new_descriptions_for,
            labels_of_host=label_manager.labels_of_host,
        )

        self._logwatch_rules = loaded_config.logwatch_rules
        self._logwatch_ec_rules = loaded_config.checkgroup_parameters.get("logwatch_ec", [])
        self.omd_root = omd_root
        self.msg_dir = var_dir / "logwatch"
        self.base_spool_path = var_dir / "logwatch_spool"
        self.debug = debug

    # This is only wishful typing -- but lets assume this is what we get.
    def logwatch_rules_all(
        self, *, host_name: str, plugin: CheckPlugin, logfile: str
    ) -> Sequence[ParameterLogwatchRules]:
        host_name = HostName(host_name)
        # We're using the logfile to match the ruleset, not necessarily the "item"
        # (which might be the group). However: the ruleset matcher expects this to be the item.
        # As a result, the following will all fail (hidden in `service_extra_conf`):
        #
        # Fail #1: Look up the discovered labels
        # Mitigate this by never discovering any labels.
        discovered_labels: Mapping[str, str] = dict(NEVER_DISCOVER_SERVICE_LABELS)

        # Fail #2: Compute the correct service description
        # This will be wrong if the logfile is grouped.
        service_description = self._service_name_config(
            host_name, ServiceID(CheckPluginName(plugin.name), logfile), plugin.service_name
        )

        # Fail #3: Retrieve the configured labels for this service.
        # This might be wrong as a result of #2.
        service_labels = self._label_manager.labels_of_service(
            host_name, service_description, discovered_labels
        )
        # => Matching this rule agains service labels will most likely fail.
        return self._matcher.get_checkgroup_ruleset_values(
            host_name,
            logfile,
            service_labels,
            self._logwatch_rules,  # type: ignore[arg-type]
            self._label_manager.labels_of_host,
        )

    # This is only wishful typing -- but lets assume this is what we get.
    def logwatch_ec_all(self, host_name: str) -> Sequence[ParameterLogwatchEc]:
        """Isolate the remaining API violation w.r.t. parameters"""
        return self._matcher.get_host_values_all(
            HostName(host_name),
            self._logwatch_ec_rules,  # type: ignore[arg-type]
            self._label_manager.labels_of_host,
        )
