# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""CLI argument parsing for cmk-dev-deploy."""

from __future__ import annotations

import argparse


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for cmk-dev-deploy."""
    parser = argparse.ArgumentParser(
        prog="cmk-dev-deploy",
        description="Deploy local changes to a running OMD site.",
        epilog=(
            "examples:\n"
            "  cmk-dev-deploy              Auto-detect site and deploy\n"
            "  cmk-dev-deploy --site v260  Deploy to a specific site\n"
            "  cmk-dev-deploy --info       Show site info without deploying\n"
            "  cmk-dev-deploy --full       Force full deploy (ignore state)\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--site",
        "-s",
        default=None,
        help="Target OMD site name (default: auto-detect)",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show site info and exit without deployment",
    )
    parser.add_argument(
        "--no-restart",
        action="store_true",
        help="Deploy files only, skip service restarts",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Force full deployment, ignoring incremental state",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase verbosity (-v for detailed output)",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be deployed without actually deploying",
    )
    parser.add_argument(
        "--watch",
        "-w",
        action="store_true",
        help="Watch for changes and auto-deploy",
    )
    parser.add_argument(
        "--jobs",
        "-j",
        type=int,
        default=4,
        help="Max parallel deployment workers (default: 4)",
    )
    parser.add_argument(
        "--commit",
        default=None,
        metavar="REF",
        help="Use the given commit/branch/tag for change detection instead of the "
        "working tree (implies --full). Note: the manifest and Bazel builds still use "
        "the current working tree. To deploy the exact state of another branch, check "
        "it out first.",
    )
    parser.add_argument(
        "--rebuild-manifest",
        action="store_true",
        help="Force manifest regeneration before deploying",
    )
    parser.add_argument(
        "--frontend",
        action="store_true",
        help="Start iBazel frontend supervisor after deploying (foreground, Ctrl-C to stop)",
    )
    parser.add_argument(
        "--purge",
        action="store_true",
        help="Remove overlay and revert site to original state, then exit (no deploy)",
    )
    parser.add_argument(
        "--json-errors",
        action="store_true",
        help="On error, output a JSON diagnostic bundle to stdout (for automation)",
    )

    args = parser.parse_args(argv)

    # Validate --jobs
    args.jobs = max(args.jobs, 1)

    # Mutual exclusion checks
    _incompatible = [
        ("watch", "dry_run"),
        ("watch", "info"),
        ("full", "info"),
        ("frontend", "dry_run"),
        ("frontend", "info"),
        ("commit", "watch"),
        ("commit", "info"),
    ]
    for a, b in _incompatible:
        if getattr(args, a) and getattr(args, b):
            parser.error(
                f"--{a.replace('_', '-')} and --{b.replace('_', '-')} cannot be used together"
            )

    if args.commit:
        args.full = True

    if args.purge:
        for flag in ("full", "dry_run", "watch", "info", "frontend"):
            if getattr(args, flag, False):
                parser.error(f"--purge and --{flag.replace('_', '-')} cannot be used together")

    return args
