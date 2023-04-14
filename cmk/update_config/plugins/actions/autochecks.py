#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
from logging import Logger
from pathlib import Path

from cmk.utils import debug
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.paths import autochecks_dir
from cmk.utils.type_defs import HostName, LegacyCheckParameters

from cmk.checkers.checking import CheckPluginName
from cmk.checkers.discovery import AutocheckEntry, AutochecksStore

from cmk.base.api.agent_based import register

from cmk.gui.watolib.rulesets import AllRulesets, RulesetCollection

from cmk.update_config.plugins.actions.replaced_check_plugins import REPLACED_CHECK_PLUGINS
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class UpdateAutochecks(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        failed_hosts = []

        all_rulesets = AllRulesets.load_all_rulesets()

        for autocheck_file in Path(autochecks_dir).glob("*.mk"):
            hostname = HostName(autocheck_file.stem)
            store = AutochecksStore(hostname)

            try:
                autochecks = store.read()
            except MKGeneralException as exc:
                if debug.enabled():
                    raise
                logger.error(str(exc))
                failed_hosts.append(hostname)
                continue

            store.write([_fix_entry(logger, s, all_rulesets, hostname) for s in autochecks])

        if failed_hosts:
            msg = f"Failed to rewrite autochecks file for hosts: {', '.join(failed_hosts)}"
            logger.error(msg)
            raise MKGeneralException(msg)


update_action_registry.register(
    UpdateAutochecks(
        name="autochecks",
        title="Autochecks",
        sort_index=40,
    )
)


def _fix_entry(
    logger: Logger,
    entry: AutocheckEntry,
    all_rulesets: RulesetCollection,
    hostname: str,
) -> AutocheckEntry:
    """Change names of removed plugins to the new ones and transform parameters"""
    new_plugin_name = REPLACED_CHECK_PLUGINS.get(entry.check_plugin_name)
    new_params = _transformed_params(
        logger,
        new_plugin_name or entry.check_plugin_name,
        entry.parameters,
        all_rulesets,
        hostname,
    )

    if new_plugin_name is None and new_params is None:
        # don't create a new entry if nothing has changed
        return entry

    return AutocheckEntry(
        check_plugin_name=new_plugin_name or entry.check_plugin_name,
        item=entry.item,
        parameters=new_params or entry.parameters,
        service_labels=entry.service_labels,
    )


def _transformed_params(
    logger: Logger,
    plugin_name: CheckPluginName,
    params: LegacyCheckParameters,
    all_rulesets: RulesetCollection,
    hostname: str,
) -> LegacyCheckParameters:
    check_plugin = register.get_check_plugin(plugin_name)
    if check_plugin is None:
        return None

    ruleset_name = "checkgroup_parameters:%s" % check_plugin.check_ruleset_name
    if ruleset_name not in all_rulesets.get_rulesets():
        return None

    debug_info = "host={!r}, plugin={!r}, ruleset={!r}, params={!r}".format(
        hostname,
        str(plugin_name),
        str(check_plugin.check_ruleset_name),
        params,
    )

    try:
        ruleset = all_rulesets.get_rulesets()[ruleset_name]

        # TODO: in order to keep the original input parameters and to identify misbehaving
        #       transform_values() implementations we check the passed values for modifications
        #       In that case we have to fix that transform_values() before using it
        #       This hack chould vanish as soon as we know transform_values() works as expected
        param_copy = copy.deepcopy(params)
        new_params = ruleset.valuespec().transform_value(param_copy) if params else {}
        if not param_copy == params:
            logger.warning(
                "transform_value() for ruleset '%s' altered input" % check_plugin.check_ruleset_name
            )

        assert new_params or not params, "non-empty params vanished"
        assert not isinstance(params, dict) or isinstance(new_params, dict), (
            "transformed params down-graded from dict: %r" % new_params
        )

        # TODO: in case of known exceptions we don't want the transformed values be combined
        #       with old keys. As soon as we can remove the workaround below we should not
        #       handle any ruleset differently
        if str(check_plugin.check_ruleset_name) in {"if", "filesystem"}:
            # Valuespecs are currently Any...
            return new_params  # type: ignore[no-any-return]

        # TODO: some transform_value() implementations (e.g. 'ps') return parameter with
        #       missing keys - so for safety-reasons we keep keys that don't exist in the
        #       transformed values
        #       On the flipside this can lead to problems with the check itself and should
        #       be vanished as soon as we can be sure no keys are deleted accidentally
        return {**params, **new_params} if isinstance(params, dict) else new_params

    except Exception as exc:
        msg = f"Transform failed: {debug_info}, error={exc!r}"
        if debug.enabled():
            raise RuntimeError(msg) from exc
        logger.error(msg)

    return None
