#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import atexit
import json
import os
import sys
from pathlib import Path

import vcr

# nosemgrep: disallow-print
print(f"vcr_sitecustomize.py loaded in process {os.getpid()}", file=sys.stderr, flush=True)

cassette = os.environ.get("VCR_CASSETTE")
if cassette:
    # nosemgrep: disallow-print
    print(f"VCR_CASSETTE environment variable found: {cassette}", file=sys.stderr, flush=True)
    try:
        # Get VCR configuration from environment variable
        vcr_config_str = os.environ.get("VCR_CONFIG", "{}")
        # nosemgrep: disallow-print
        print(f"Raw VCR_CONFIG: {vcr_config_str}", file=sys.stderr, flush=True)

        vcr_config = json.loads(vcr_config_str)
        # nosemgrep: disallow-print
        print(f"Parsed VCR config: {vcr_config}", file=sys.stderr, flush=True)

        # Convert lists back to tuples for VCR filter parameters
        # JSON serialization converts tuples to lists, but VCR expects tuples
        for filter_key in [
            "filter_headers",
            "filter_query_parameters",
            "filter_post_data_parameters",
        ]:
            if filter_key in vcr_config:
                vcr_config[filter_key] = [tuple(item) for item in vcr_config[filter_key]]

        # nosemgrep: disallow-print
        print(f"VCR config after tuple conversion: {vcr_config}", file=sys.stderr, flush=True)

        # Ensure cassette directory exists
        cassette_path = Path(cassette)
        cassette_path.parent.mkdir(parents=True, exist_ok=True)
        # nosemgrep: disallow-print
        print(f"Cassette directory created: {cassette_path.parent}", file=sys.stderr, flush=True)

        # Configure VCR with settings from pytest fixtures
        # nosemgrep: disallow-print
        print(f"Creating VCR with config: {vcr_config}", file=sys.stderr, flush=True)
        myvcr = vcr.VCR(**vcr_config)  # type: ignore[attr-defined]

        ctx = myvcr.use_cassette(str(cassette_path))

        # Enter the cassette for the lifetime of the process
        ctx.__enter__()

        def exit_handler(*args):
            print(  # nosemgrep: disallow-print
                f"VCR cassette context exiting, saving to: {cassette_path}",
                file=sys.stderr,
                flush=True,
            )
            ctx.__exit__(*args)
            if cassette_path.exists():
                print(  # nosemgrep: disallow-print
                    f"Cassette file created successfully: {cassette_path} (size: {cassette_path.stat().st_size} bytes)",
                    file=sys.stderr,
                    flush=True,
                )
            else:
                print(  # nosemgrep: disallow-print
                    f"WARNING: Cassette file not found after exit: {cassette_path}",
                    file=sys.stderr,
                    flush=True,
                )

        atexit.register(exit_handler, None, None, None)

        # Debug print to verify it's working
        # nosemgrep: disallow-print
        print(f"VCR enabled for cassette: {cassette_path}", file=sys.stderr, flush=True)

    except Exception as e:
        # nosemgrep: disallow-print
        print(f"Failed to initialize VCR: {e}", file=sys.stderr, flush=True)
else:
    # nosemgrep: disallow-print
    print("No VCR_CASSETTE environment variable found", file=sys.stderr, flush=True)
