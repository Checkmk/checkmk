# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""CLI: generate the Slack-ready crash-owner rollup with caching + diff."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

from .cache import cache_dir, load_previous_snapshot, write_snapshot
from .diff import make_snapshot, render_diff
from .emit import render
from .fetch import fetch_enriched_groups
from .routing import is_external_plugin, load_components, route_group


def parse_min_version(s: str) -> tuple[int, int]:
    parts = s.split(".")
    if len(parts) < 2:
        raise argparse.ArgumentTypeError(f"Invalid min version: {s!r}")
    return (int(parts[0]), int(parts[1]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--min-version",
        default="2.4",
        help="Minimum Checkmk version cutoff (default: 2.4)",
    )
    parser.add_argument(
        "--plugins-coordinator",
        default="moritz.kiemer@checkmk.com",
        help="Email address routed to as the Plugins-bucket coordinator",
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Path to the Checkmk repo (for filename lookups during routing)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass the enrichment cache (forces full re-fetch)",
    )
    parser.add_argument(
        "--no-diff",
        action="store_true",
        help="Don't emit the 'Changes since last run' section",
    )
    parser.add_argument(
        "--refresh-components",
        action="store_true",
        help="Bypass the daily cmk-components info cache",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write Slack text to this file (in addition to stdout)",
    )
    args = parser.parse_args(argv)

    min_version = parse_min_version(args.min_version)
    repo = Path(args.repo).resolve()

    print("# fetching crash groups…", file=sys.stderr)
    t0 = time.time()
    enriched_all = fetch_enriched_groups(min_version=min_version, use_cache=not args.no_cache)
    enriched = [g for g in enriched_all if not is_external_plugin(g.plugin_path or "")]
    n_external = len(enriched_all) - len(enriched)
    print(
        f"# enriched {len(enriched_all)} groups in {time.time() - t0:.1f}s "
        f"(excluded {n_external} third-party / site-local plugin groups)",
        file=sys.stderr,
    )

    print("# loading component owners…", file=sys.stderr)
    components, path_index = load_components(force_refresh=args.refresh_components)
    components_by_id = {c.id: c for c in components}

    routed: list[dict[str, Any]] = []
    for g in enriched:
        r = route_group(g.plugin_path, g.check_type, components_by_id, path_index, repo)
        routed.append(
            {
                "group_id": g.group_id,
                "num_crashes": g.num_crashes,
                "check_type": g.check_type,
                "section_name": g.section_name,
                "plugin_path": g.plugin_path,
                "owner_email": r.lead if r else "",
                "component_id": r.component_id if r else "",
                "component_name": r.component_name if r else "",
                "matched_path": r.matched_path if r else "",
            }
        )

    generated_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    snapshot = make_snapshot(routed, generated_at)

    diff_text = ""
    if not args.no_diff:
        prior = load_previous_snapshot()
        diff_text = render_diff(prior, snapshot)

    snap_path = write_snapshot(snapshot)
    print(f"# wrote snapshot: {snap_path}", file=sys.stderr)

    text = render(
        routed_groups=routed,
        plugins_coordinator_email=args.plugins_coordinator,
        diff_section=diff_text or None,
        min_version_label=args.min_version,
    )
    print(text)
    if args.output:
        args.output.write_text(text + "\n")
        print(f"# wrote Slack post: {args.output}", file=sys.stderr)
    print(f"# cache dir: {cache_dir()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
