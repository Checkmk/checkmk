#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import sys
import tempfile
from collections.abc import Sequence
from contextlib import redirect_stdout
from pathlib import Path

from sarif import __version__ as SARIF_TOOLS_PACKAGE_VERSION  # type: ignore[import-untyped]
from sarif.operations import copy_op  # type: ignore[import-untyped]
from sarif.sarif_file import SarifFile, SarifFileSet  # type: ignore[import-untyped]


def parse_header(header: str) -> Path:
    target = header.rsplit(" ", 1)[-1]
    directory, name = target.split(":", 1)
    return Path(directory) / name[: name.index(":")]


def parse(raw_data: Sequence[str]) -> SarifFileSet:
    results = SarifFileSet()
    header: str = ""
    payload = ""
    for line in raw_data:
        if not line.strip():
            continue
        if line and not header:
            assert line.startswith("Lint results for"), line
            header = line
            continue
        if line and header:
            payload += line

        try:
            data = json.loads(payload)
        except json.decoder.JSONDecodeError:
            pass
        else:
            # Successful runs miss "results".
            if any(_.get("results") for _ in data.get("runs", [])):
                with tempfile.NamedTemporaryFile(
                    mode="w+", prefix=parse_header(header).name, encoding="utf-8"
                ) as f:
                    json.dump(data, f)
                    sarif = SarifFile(f.name, data)
                results.add_file(sarif)
            header = ""
            payload = ""
    return results


def main() -> None:
    results = parse(sys.stdin.readlines())
    with redirect_stdout(None):
        result = copy_op.generate_sarif(
            input_files=results,
            output="out.sarif",
            append_timestamp=False,
            sarif_tools_version=SARIF_TOOLS_PACKAGE_VERSION,
            cmdline="bazel lint",
        )
    sys.stdout.write(json.dumps(result.data, indent=4, sort_keys=True))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
