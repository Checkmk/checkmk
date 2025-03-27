#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

MIGRATE_POSTFIX = " (migrated)"


def print_summary_dryrun(conflicts: int, rules: int, skipped: int) -> None:
    sys.stdout.write(
        f"Dry run results: {conflicts} conflict(s), {rules - skipped - conflicts} rule(s) can be migrated, {skipped} skipped.\n"
    )
    sys.stdout.write(
        "Resolve conflicts by adding the corresponding  options. Use ‘cmk-migrate-http migrate -h’ for all options. "
        "Once you are satisfied with the results, use ‘cmk-migrate-http migrate --write’ to create the new rules.\n"
    )


def print_summary_write(conflicts: int, rules: int, skipped: int) -> None:
    sys.stdout.write(
        f"Summary: {conflicts} conflict(s), {rules - skipped - conflicts} rule(s) have been written to disk, {skipped} skipped.\n"
    )
    sys.stdout.write("Rules created by the script are deactivated by default.\n")
    sys.stdout.write(
        f"The new v2 rules have the id of their v1 counterpart in the description, and use ‘{MIGRATE_POSTFIX}’ suffix in the service name.\n"
    )
    sys.stdout.write(
        "To see the new services in monitoring and compare the output with the old services activate the rules using ‘cmk-migrate-http activate’.\n"
    )
    sys.stdout.write(
        "Once satisfied with the monitoring, use ‘cmk-migrate-http finalize’ to delete the v1 rules and clean up the v2 rules.\n"
    )


def print_summary_finalize(rulecount_v1: int, rulecount_v2: int) -> None:
    sys.stdout.write(
        f"Summary: {rulecount_v1} v1 rule(s) deleted, {rulecount_v2} v2 rule(s) finalized\n"
    )
    if rulecount_v1 or rulecount_v2:
        if rulecount_v1 < rulecount_v2:
            sys.stdout.write(
                "Script was not able to find and delete all v1 rules that were migrated. "
                "This could be because they were already manually deleted or the reference in the v2 rule had been removed. "
                "The v2 rules have now been edited so that the ‘migrated’ prefix is removed from the service name and the reference to the v1 rule has been deleted from the description. "
            )
        else:
            sys.stdout.write(
                "Migrated v1 rule(s) have been deleted. "
                f"The v2 rule(s) have now been edited so that the ‘{MIGRATE_POSTFIX}’ suffix is removed from the service name and the reference to the v1 rule has been deleted from the description. "
            )
        sys.stdout.write(
            "For the changes to take effect, complete the process by activating the changes on the site.\n"
        )
