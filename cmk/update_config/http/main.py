#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from pprint import pprint

from cmk.utils.redis import disable_redis

from cmk.gui.main_modules import load_plugins
from cmk.gui.session import SuperUserContext
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.rulesets import AllRulesets
from cmk.gui.wsgi.blueprints.global_vars import set_global_vars

from cmk.update_config.http.conflicts import detect_conflicts, MigratableValue
from cmk.update_config.http.migrate import migrate


def main() -> None:
    load_plugins()
    with disable_redis(), gui_context(), SuperUserContext():
        set_global_vars()
        all_rulesets = AllRulesets.load_all_rulesets()
    for folder, rule_index, rule in all_rulesets.get_rulesets()["active_checks:http"].get_rules():
        value = detect_conflicts(rule.value)
        if isinstance(value, MigratableValue):
            sys.stdout.write(f"MIGRATABLE: {folder}, {rule_index}\n")
            pprint(migrate(rule.value))  # nosemgrep: disallow-print
        else:
            sys.stdout.write(f"IMPOSSIBLE: {folder}, {rule_index}\n")
        pprint(rule.value)  # nosemgrep: disallow-print
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
