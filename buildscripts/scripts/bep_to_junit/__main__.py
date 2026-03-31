#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
bep_to_junit - Bazel Build Event Protocol → JUnit XML for CI reporters.

Generates JUnit XML files for two failure modes that produce no useful test.xml:
  1. Test targets that FAILED TO BUILD (the target never ran, no test.xml written)
  2. Test targets that ran and FAILED (testResult status=FAILED), using test.log
     as the report body (covers runners that crash before writing XML_OUTPUT_FILE)

One XML file is written per failing target into the output directory, named
after its label.  These are meant to be collected by the CI JUnit reporter
alongside bazel-testlogs/*/test.xml.

Usage:
    bazel test //... --config=ci --build_event_json_file=bep.json
    RC=$?
    python3 -m bep_to_junit bep.json output_dir/
    exit $RC
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from bep_to_junit._helpers import label_to_dirname, read_uri, write_xml
from bep_to_junit._parser import parse_bep
from bep_to_junit._xml_builders import build_failure_xml, test_failure_xml, test_log_uri


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("bep_json", metavar="bep.json", type=Path, help="BEP JSON file")
    parser.add_argument("output_dir", metavar="output-dir", type=Path, help="Output directory")
    args = parser.parse_args(argv)

    if not args.bep_json.exists():
        parser.error(f"{args.bep_json}: not found")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    with args.bep_json.open() as bep:
        failed_builds, failed_tests, action_stderr_uris, action_timing = parse_bep(bep)

    action_stderr = {key: read_uri(uri) for key, uri in action_stderr_uris.items()}

    for label, event in sorted(failed_builds.items()):
        write_xml(
            build_failure_xml(label, event, action_stderr, action_timing),
            args.output_dir / label_to_dirname(label) / "test.xml",
        )

    for label, event in sorted(failed_tests.items()):
        write_xml(
            test_failure_xml(label, event, read_uri(test_log_uri(event))),
            args.output_dir / label_to_dirname(label) / "test.xml",
        )

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
