#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<splunk_jobs>>>
# splunk-system-user, , 0.91, False, 61440, False
# admin, search, 0.101, False, 69632, False


# mypy: disable-error-code="var-annotated"

import collections

from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info

JobCount = collections.namedtuple(  # pylint: disable=collections-namedtuple-call
    "JobCount", ["jobs", "failed", "zombies", "output"]
)


def parse_splunk_jobs(string_table):
    parsed = {}
    long_output = ""
    job_count, failed_count, zombie_count = 0, 0, 0

    for job_detail in string_table:
        try:
            published, author, app, dispatchstate, iszombie = job_detail
            job_count += 1

            if dispatchstate == "FAILED":
                failed_count += 1
            if iszombie == "True":
                zombie_count += 1

            long_output += "{} - Author: {}, Application: {}, State: {}, Zombie: {}\n".format(
                published,
                author,
                app,
                dispatchstate,
                iszombie,
            )

        except (IndexError, ValueError):
            pass

    parsed.setdefault("job", []).append(
        JobCount(job_count, failed_count, zombie_count, long_output)
    )

    return parsed


def inventory_splunk_jobs(parsed):
    yield None, {}


def check_splunk_jobs(_no_item, params, parsed):
    data = parsed["job"][0]

    for key, value, infotext in [
        ("job_total", data.jobs, "Job Count"),
        ("failed_jobs", data.failed, "Failed jobs"),
        ("zombie_jobs", data.zombies, "Zombie jobs"),
    ]:
        yield check_levels(value, key, params.get(key), human_readable_func=int, infoname=infotext)

    if data.output:
        yield 0, "\n%s" % data.output


check_info["splunk_jobs"] = LegacyCheckDefinition(
    parse_function=parse_splunk_jobs,
    service_name="Splunk Jobs",
    discovery_function=inventory_splunk_jobs,
    check_function=check_splunk_jobs,
    check_ruleset_name="splunk_jobs",
)
