#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""SARIF (Static Analysis Results Interchange Format) output for astrein."""

import json
from collections.abc import Mapping, Sequence

from cmk.astrein.framework import CheckerError


def format_sarif(errors: Sequence[CheckerError], summaries: Mapping[str, str]) -> str:
    """Format errors as SARIF JSON for CI integration.

    SARIF is a standardized format for static analysis results that provides
    better integration with CI/CD systems and IDEs.

    Spec: https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html
    """
    rule_ids = sorted({error.checker_id for error in errors})

    rules = [
        {
            "id": rule_id,
            "shortDescription": {"text": summaries.get(rule_id, f"Checker rule: {rule_id}")},
        }
        for rule_id in rule_ids
    ]

    results = [
        {
            "ruleId": error.checker_id,
            "level": "error",
            "message": {"text": error.message},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": str(error.file_path),
                            "uriBaseId": "%SRCROOT%",
                        },
                        "region": {
                            "startLine": error.line,
                            "startColumn": error.column + 1,  # SARIF uses 1-based columns
                        },
                    }
                }
            ],
        }
        for error in errors
    ]

    sarif_output = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "astrein",
                        "informationUri": "https://checkmk.com",
                        "version": "1.0.0",
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }

    return json.dumps(sarif_output, indent=2)
