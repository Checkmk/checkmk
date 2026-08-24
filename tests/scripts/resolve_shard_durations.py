#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Name the build the shards balance against, and log what it holds.

Prints "<job>#<number>" for the trigger job to pass on. The shards read that
build themselves, see tests/testlib/pytest_helpers/sharding.py.

    tests/scripts/resolve_shard_durations.py \
        --job checkmk/master/heavy/test-system-singlesite-ultimatemt

The job is the full path, so the same call works from the Testing folder and
from any branch.

No opinion on whether the numbers look right, that differs per suite. It fails
only when the report cannot be read or holds no test cases at all, and failing
here is the point: better this job, which has not built a site yet, than eight
that have.

Credentials come from JENKINS_URL, JENKINS_USERNAME and JENKINS_PASSWORD.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.testlib.pytest_helpers.sharding import (
    fetch_durations,
    jenkins_client,
)

logger = logging.getLogger("resolve_shard_durations")


def last_successful_build(job: str) -> int:
    """Build number behind the lastSuccessfulBuild permalink.

    The permalink rather than a scan over recent builds, so a long red streak
    does not take the gate down with it.
    """
    with jenkins_client() as jenkins:
        # The typed wrappers in jenkins_utils are async, and python-jenkins itself
        # is untyped, hence the ignore rather than an asyncio round trip here.
        info = jenkins.client.get_job_info(job)  # type: ignore[no-untyped-call, unused-ignore]

    if not (last_successful := info.get("lastSuccessfulBuild") or {}).get("number"):
        raise RuntimeError(f"{job} has no successful build to read runtimes from")
    return int(last_successful["number"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", required=True, help="full job path, e.g. checkmk/master/heavy/...")
    parser.add_argument("--build", type=int, help="pin a build instead of the last successful one")
    parser.add_argument("--show", action="store_true", help="log the per module runtimes")
    args = parser.parse_args()

    # One summary line by default, the per module detail only when asked for.
    logging.basicConfig(format="%(levelname)s %(message)s", level=logging.INFO)

    try:
        reference = f"{args.job}#{args.build or last_successful_build(args.job)}"
        durations = fetch_durations(reference)
    except Exception as exc:
        sys.exit(f"Could not resolve shard durations: {exc}")

    modules = durations.per_module
    total_minutes = sum(modules.values()) / 60
    logger.info(
        "%s: %d modules, %d tests, %.1f min",
        reference,
        len(modules),
        durations.test_count,
        total_minutes,
    )
    if args.show:
        for module, seconds in sorted(modules.items(), key=lambda kv: -kv[1]):
            logger.info("%7.2f min  %s", seconds / 60, module)
        return

    # The only thing on stdout, the trigger reads this line as it is.
    print(reference)


if __name__ == "__main__":
    main()
