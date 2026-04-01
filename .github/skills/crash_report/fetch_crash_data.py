#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Fetch and anonymize crash report data from crash.checkmk.com.

Usage:
    PYTHONPATH=.github/skills python3 -m crash_report.fetch_crash_data <command> [options]

Commands:
    search   Search crash groups with filters
    popular  Show popular (>10 occurrences) unsolved crash groups
    stats    Show aggregate crash statistics
    show     Show individual crash report detail (anonymized)
    group    Show crash group detail (anonymized)
    local    List crash reports from local OMD sites

Authentication (in priority order):
    1. Cached OAuth bearer token from authenticate.py (~/.cache/cmk-crash-reporting/token.json)
    2. CRASH_REPORTING_TOKEN env var (legacy static token, still supported)

All crash data is automatically anonymized before output.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Any

from .anonymize import Anonymizer
from .authenticate import get_cached_bearer_token

BASE_URL = os.environ.get("CRASH_REPORTING_URL", "https://crash.checkmk.com")
API_BASE = f"{BASE_URL}/gui/api/v1/statsapi"
OMD_SITES_DIR = Path("/omd/sites")


class AuthenticationError(Exception):
    """Raised when no authentication token is available."""


class ApiError(Exception):
    """Raised when a remote API request fails."""


# ---------------------------------------------------------------------------
# Local OMD site crash report helpers
# ---------------------------------------------------------------------------


def _find_omd_sites() -> list[Path]:
    """Return paths to all accessible OMD sites."""
    if not OMD_SITES_DIR.is_dir():
        return []
    sites = []
    for site_dir in sorted(OMD_SITES_DIR.iterdir()):
        crashes_dir = site_dir / "var" / "check_mk" / "crashes"
        if crashes_dir.is_dir():
            sites.append(site_dir)
    return sites


def _find_local_crash(crash_id: str) -> Path | None:
    """Search all local OMD sites for a crash report by ID."""
    for site_dir in _find_omd_sites():
        crashes_dir = site_dir / "var" / "check_mk" / "crashes"
        # Crash reports are stored as: crashes/<crash_type>/<crash_id>/crash.info
        for crash_type_dir in crashes_dir.iterdir():
            if not crash_type_dir.is_dir():
                continue
            crash_dir = crash_type_dir / crash_id
            if crash_dir.is_dir() and (crash_dir / "crash.info").is_file():
                return crash_dir
    return None


def _load_local_crash(crash_dir: Path) -> dict[str, Any]:
    """Load a crash report from local disk and return structured data."""
    crash_info_path = crash_dir / "crash.info"
    crash_info = json.loads(crash_info_path.read_text())

    crash_type = crash_dir.parent.name
    parts = crash_dir.parts
    try:
        site_name = parts[parts.index("sites") + 1]
    except (ValueError, IndexError):
        site_name = "unknown"

    result: dict[str, Any] = {
        "crash_id": crash_info.get("id", crash_dir.name),
        "crash_type": crash_info.get("crash_type", crash_type),
        "cmk_version": crash_info.get("version", "Unknown"),
        "upload_time": datetime.fromtimestamp(crash_info.get("time", 0), tz=UTC).isoformat(),
        "exc_type": crash_info.get("exc_type", ""),
        "exc_value": crash_info.get("exc_value", ""),
        "exc_traceback": crash_info.get("exc_traceback", []),
        "local_vars": crash_info.get("local_vars", ""),
        "os": crash_info.get("os", ""),
        "edition": crash_info.get("edition", ""),
        "core": crash_info.get("core", ""),
        "python_version": crash_info.get("python_version", ""),
        "details": crash_info.get("details", {}),
        "contact_name": "",
        "contact_mail": "",
        "source": f"local (site: {site_name})",
        "local_path": str(crash_dir),
    }

    # Load extra files if present
    for extra_file in ["agent_output", "snmp_info"]:
        extra_path = crash_dir / extra_file
        if extra_path.is_file():
            result[extra_file] = extra_path.read_text(errors="replace")[:10000]

    return result


def _list_local_crashes(
    crash_type: str | None = None,
) -> list[dict[str, Any]]:
    """List all crash reports from local OMD sites."""
    results = []
    for site_dir in _find_omd_sites():
        site_name = site_dir.name
        crashes_dir = site_dir / "var" / "check_mk" / "crashes"

        for type_dir in sorted(crashes_dir.iterdir()):
            if not type_dir.is_dir():
                continue
            if crash_type and type_dir.name != crash_type:
                continue

            for crash_dir in sorted(type_dir.iterdir(), reverse=True):
                crash_info_path = crash_dir / "crash.info"
                if not crash_info_path.is_file():
                    continue
                try:
                    info = json.loads(crash_info_path.read_text())
                    results.append(
                        {
                            "crash_id": info.get("id", crash_dir.name),
                            "crash_type": info.get("crash_type", type_dir.name),
                            "cmk_version": info.get("version", "Unknown"),
                            "time": datetime.fromtimestamp(info.get("time", 0), tz=UTC).isoformat(),
                            "exc_type": info.get("exc_type", ""),
                            "exc_value": (info.get("exc_value", "") or "")[:120],
                            "site": site_name,
                        }
                    )
                except (json.JSONDecodeError, OSError) as exc:
                    print(f"Warning: skipping {crash_dir}: {exc}", file=sys.stderr)
                    continue
    return results


# ---------------------------------------------------------------------------
# Remote API helpers
# ---------------------------------------------------------------------------


def _get_auth_headers() -> dict[str, str]:
    """Return authentication headers, preferring cached OAuth token over env var.

    Priority:
    1. Cached bearer token from authenticate.py (Google OAuth flow)
    2. CRASH_REPORTING_TOKEN env var (legacy static token)
    """
    # Try cached OAuth bearer token first
    bearer = get_cached_bearer_token()
    if bearer:
        return {"Authorization": f"Bearer {bearer}"}

    # Fall back to legacy static token
    legacy = os.environ.get("CRASH_REPORTING_TOKEN")
    if legacy:
        return {"X-API-Authorization": legacy}

    raise AuthenticationError(
        "No authentication token available.\n"
        "Run: PYTHONPATH=.github/skills python3 -m crash_report.authenticate\n"
        "Or set: export CRASH_REPORTING_TOKEN='<token>'"
    )


def api_request(endpoint: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    """Make an authenticated API request and return parsed JSON."""
    url = f"{API_BASE}/{endpoint}"
    if params:
        query = urllib.parse.urlencode(params)
        if query:
            url = f"{url}?{query}"

    req = urllib.request.Request(url, headers=_get_auth_headers())

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
            result: dict[str, Any] = json.loads(resp.read().decode())
            return result
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ApiError(f"Not found: {endpoint}") from e
        if e.code == 401:
            raise ApiError("Authentication failed") from e
        raise ApiError(f"HTTP {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise ApiError(f"Could not connect to {BASE_URL}: {e.reason}") from e


def parse_date(date_str: str) -> str:
    """Parse a date string (ISO date or relative like '30d') to ISO format."""
    if date_str.endswith("d"):
        days = int(date_str[:-1])
        return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    # Validate ISO format
    try:
        datetime.fromisoformat(date_str)
    except ValueError:
        raise ValueError(
            f"Invalid date format: {date_str!r}. Use ISO date (YYYY-MM-DD) or relative (e.g. '30d')."
        ) from None
    return date_str


def format_traceback(tb: list[list[str]]) -> str:
    """Format a traceback list into readable text."""
    lines = []
    for frame in tb:
        if len(frame) >= 4:
            filename, lineno, funcname, text = frame[0], frame[1], frame[2], frame[3]
            lines.append(f'  File "{filename}", line {lineno}, in {funcname}')
            if text:
                lines.append(f"    {text}")
        elif len(frame) >= 3:
            lines.append(f'  File "{frame[0]}", line {frame[1]}, in {frame[2]}')
    return "\n".join(lines)


def cmd_search(args: argparse.Namespace) -> None:
    """Search crash groups with filters."""
    params: dict[str, str] = {}
    if args.since:
        params["since"] = parse_date(args.since)
    if args.min_crashes:
        params["min_crashes"] = str(args.min_crashes)
    if args.type:
        params["crash_type"] = args.type
    if args.unsolved:
        params["solved"] = "false"
    if args.version:
        params["version"] = args.version
    if args.limit:
        params["limit"] = str(args.limit)

    data = api_request("search", params)
    groups = data.get("crash_groups", [])

    if not groups:
        print("No crash groups found matching the criteria.")
        return

    anonymizer = Anonymizer()

    print(f"# Crash Groups ({len(groups)} results)\n")
    print("| Group ID | Type | Crashes | Solved | Exception | Jira |")
    print("|----------|------|---------|--------|-----------|------|")

    for g in groups:
        solved = "Yes" if g["is_solved"] else "No"
        jira = g.get("jira_issue") or "-"
        exc_type = g.get("exc_type", "")
        exc_value = g.get("exc_value", "")
        # Anonymize the exception value (may contain IPs, hostnames, etc.)
        if exc_value:
            exc_value, _ = anonymizer.anonymize_string(exc_value)
        exc_short = f"{exc_type}: {exc_value[:80]}" if exc_value else exc_type
        print(
            f"| [{g['id']}]({g['url']}) | {g['crash_type']} | {g['num_crashes']} "
            f"| {solved} | {exc_short} | {jira} |"
        )


def cmd_popular(args: argparse.Namespace) -> None:
    """Show popular unsolved crash groups."""
    # Use the search endpoint with min_crashes and unsolved filter
    params: dict[str, str] = {"min_crashes": "10", "solved": "false", "limit": str(args.limit)}
    if args.since:
        params["since"] = parse_date(args.since)

    data = api_request("search", params)
    groups = data.get("crash_groups", [])

    if not groups:
        print("No popular unsolved crash groups found.")
        return

    anonymizer = Anonymizer()

    limit_note = f", limit {args.limit}" if args.limit != 50 else ""
    print(f"# Popular Unsolved Crash Groups ({len(groups)} groups with >10 crashes{limit_note})\n")
    print("| Group ID | Type | Crashes | Exception | Jira |")
    print("|----------|------|---------|-----------|------|")

    for g in groups:
        jira = g.get("jira_issue") or "-"
        exc_type = g.get("exc_type", "")
        exc_value = g.get("exc_value", "")
        if exc_value:
            exc_value, _ = anonymizer.anonymize_string(exc_value)
        exc_short = f"{exc_type}: {exc_value[:80]}" if exc_value else exc_type
        print(
            f"| [{g['id']}]({g['url']}) | {g['crash_type']} | {g['num_crashes']} "
            f"| {exc_short} | {jira} |"
        )


def cmd_stats(args: argparse.Namespace) -> None:
    """Show aggregate crash statistics (no anonymization needed)."""
    params: dict[str, str] = {}
    if args.since:
        # Convert to unix timestamp for the horizon parameter
        date = datetime.fromisoformat(parse_date(args.since))
        params["horizon"] = str(int(date.timestamp()))

    data = api_request("crashes", params)
    stats = data.get("stats", {})

    print("# Crash Statistics\n")
    print(f"**Total crashes:** {stats.get('total', 0)}")
    print(f"**Open:** {stats.get('total_open', 0)}")
    print(f"**Solved:** {stats.get('total_solved', 0)}")

    # Fetch supported versions dynamically from the server
    versions_data = api_request("versions")
    supported_versions = versions_data.get("versions", [])

    print("\n## By Version\n")
    print("| Version | Open | Solved |")
    print("|---------|------|--------|")
    for ver in supported_versions:
        ver_key = ver.replace(".", "")  # "2.4.0" -> "240"
        open_count = stats.get(f"version_{ver_key}_open", 0)
        solved_count = stats.get(f"version_{ver_key}_solved", 0)
        if open_count or solved_count:
            print(f"| {ver} | {open_count} | {solved_count} |")

    print("\n## By Type\n")
    print("| Type | Open | Solved |")
    print("|------|------|--------|")
    for type_key in ["gui", "check", "rest_api"]:
        open_count = stats.get(f"type_{type_key}_open", 0)
        solved_count = stats.get(f"type_{type_key}_solved", 0)
        if open_count or solved_count:
            print(f"| {type_key} | {open_count} | {solved_count} |")


def _fetch_crash_report(crash_id: str) -> tuple[dict[str, Any], str]:
    """Fetch a crash report from the remote API, falling back to local OMD sites.

    Returns (report_dict, source) where source is 'remote' or 'local (site: ...)'.
    """
    # Try remote API first
    try:
        data = api_request(f"crash_report/{crash_id}")
        report = data.get("crash_report", {})
        if report:
            return report, "remote (crash.checkmk.com)"
    except ApiError as e:
        sys.stderr.write(f"Remote API error: {e}\n")

    # Fall back to local OMD sites
    sys.stderr.write("Searching local OMD sites...\n")
    local_dir = _find_local_crash(crash_id)
    if local_dir:
        report = _load_local_crash(local_dir)
        return report, report.get("source", "local")

    sys.stderr.write(f"Error: Crash report {crash_id} not found (remote or local).\n")
    sys.exit(1)


def cmd_show(args: argparse.Namespace) -> None:
    """Show individual crash report detail (anonymized)."""
    report, source = _fetch_crash_report(args.crash_id)

    # Anonymize the entire report
    anonymizer = Anonymizer()
    report, _ = anonymizer.anonymize_value(report)

    group = report.get("group", {})

    print(f"# Crash Report: {report['crash_id']}\n")
    print(f"*Source: {source}*\n")

    print("## Summary\n")
    print(f"- **Type:** {report['crash_type']}")
    print(f"- **Checkmk Version:** {report['cmk_version']}")
    print(f"- **Upload Time:** {report['upload_time']}")
    print(f"- **OS:** {report.get('os', 'Unknown')}")
    print(f"- **Edition:** {report.get('edition', 'Unknown')}")
    print(f"- **Core:** {report.get('core', 'Unknown')}")
    print(f"- **Python:** {report.get('python_version', 'Unknown')}")
    if report.get("local_path"):
        print(f"- **Local path:** `{report['local_path']}`")

    print("\n## Group Info\n")
    solved_str = "Yes" if group.get("is_solved") else "No"
    print(f"- **Group ID:** {group.get('id')}")
    print(f"- **Total crashes in group:** {group.get('num_crashes')}")
    print(f"- **Solved:** {solved_str}")
    if group.get("solved_versions"):
        print(f"- **Solved in:** {group['solved_versions']}")
    if group.get("jira_issue"):
        print(f"- **Jira:** {group['jira_issue']}")

    print("\n## Exception\n")
    print(f"**{report.get('exc_type', 'Unknown')}**: {report.get('exc_value', '')}")

    tb = report.get("exc_traceback", [])
    if tb:
        print("\n### Traceback\n")
        print("```")
        print(format_traceback(tb))
        print("```")

    local_vars = report.get("local_vars", "")
    if local_vars:
        print("\n### Local Variables\n")
        print("```")
        print(local_vars[:5000])
        if len(local_vars) > 5000:
            print(f"\n... (truncated, {len(local_vars) - 5000} chars omitted)")
        print("```")

    details = report.get("details", {})
    if details:
        print("\n## Type-Specific Details\n")
        for key, value in details.items():
            if isinstance(value, dict):
                print(f"- **{key}:**")
                for k, v in value.items():
                    print(f"  - {k}: {v}")
            else:
                print(f"- **{key}:** {value}")

    # Extra files from local crash reports
    for extra_key, extra_label in [
        ("agent_output", "Agent Output"),
        ("snmp_info", "SNMP Info"),
    ]:
        extra = report.get(extra_key, "")
        if extra:
            print(f"\n## {extra_label}\n")
            print("```")
            print(extra[:5000])
            if len(extra) > 5000:
                print(f"\n... (truncated, {len(extra) - 5000} chars omitted)")
            print("```")


def cmd_local(args: argparse.Namespace) -> None:
    """List crash reports from local OMD sites."""
    crashes = _list_local_crashes(crash_type=args.type)

    if not crashes:
        sites = _find_omd_sites()
        if not sites:
            print("No accessible OMD sites found in /omd/sites/.")
            print("You may need to run this as the site user or with appropriate permissions.")
        else:
            print(f"No local crash reports found in {len(sites)} site(s).")
        return

    anonymizer = Anonymizer()

    # Group by site
    site_groups: dict[str, list[dict[str, Any]]] = {}
    for c in crashes:
        site_groups.setdefault(c["site"], []).append(c)

    total = len(crashes)
    print(f"# Local Crash Reports ({total} total across {len(site_groups)} site(s))\n")

    for site_name, site_crashes in site_groups.items():
        print(f"## Site: {site_name} ({len(site_crashes)} crashes)\n")
        print("| Crash ID | Type | Version | Time | Exception |")
        print("|----------|------|---------|------|-----------|")

        for c in site_crashes:
            exc_value = c.get("exc_value", "")
            if exc_value:
                exc_value, _ = anonymizer.anonymize_string(exc_value)
            exc_short = f"{c['exc_type']}: {exc_value[:60]}" if exc_value else c["exc_type"]
            print(
                f"| {c['crash_id']} | {c['crash_type']} | {c['cmk_version']} "
                f"| {c['time']} | {exc_short} |"
            )
        print()


def cmd_group(args: argparse.Namespace) -> None:
    """Show crash group detail (anonymized)."""
    data = api_request(f"crash_group/{args.group_id}")
    group = data.get("crash_group", {})

    if not group:
        print(f"Crash group {args.group_id} not found.")
        return

    # Anonymize the entire group
    anonymizer = Anonymizer()
    group, _ = anonymizer.anonymize_value(group)

    print(f"# Crash Group: {group['id']}\n")

    solved_str = "Yes" if group.get("is_solved") else "No"
    print("## Summary\n")
    print(f"- **Type:** {group['crash_type']}")
    print(f"- **Total crashes:** {group['num_crashes']}")
    print(f"- **Solved:** {solved_str}")
    if group.get("solved_by"):
        print(f"- **Solved by:** {group['solved_by']}")
    if group.get("solved_at"):
        print(f"- **Solved at:** {group['solved_at']}")
    if group.get("solved_versions"):
        print(f"- **Solved in:** {group['solved_versions']}")
    if group.get("jira_issue"):
        print(f"- **Jira:** {group['jira_issue']}")

    print("\n## Exception\n")
    print(f"**{group.get('exc_type', 'Unknown')}**: {group.get('exc_value', '')}")

    tb = group.get("exc_traceback", [])
    if tb:
        print("\n### Traceback\n")
        print("```")
        print(format_traceback(tb))
        print("```")

    crashes = group.get("crash_reports", [])
    if crashes:
        print(f"\n## Crash Reports ({len(crashes)})\n")
        print("| Crash ID | Version | Upload Time | Contact |")
        print("|----------|---------|-------------|---------|")
        for c in crashes:
            print(
                f"| {c['crash_id']} | {c['cmk_version']} "
                f"| {c['upload_time']} | {c['contact_mail']} |"
            )


def cmd_check_auth(_args: argparse.Namespace) -> None:
    """Exit 0 if a valid cached token exists, 1 otherwise."""
    token = get_cached_bearer_token()
    if token:
        print("Authenticated (cached token valid).")
        sys.exit(0)
    else:
        print("Not authenticated (no valid cached token).")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch and anonymize crash report data from crash.checkmk.com"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # search
    search_parser = subparsers.add_parser("search", help="Search crash groups with filters")
    search_parser.add_argument("--since", help="Filter by date (ISO date or relative, e.g. '30d')")
    search_parser.add_argument("--min-crashes", type=int, help="Minimum number of crashes in group")
    search_parser.add_argument(
        "--type", help="Crash type filter (check, gui, rest_api, section, etc.)"
    )
    search_parser.add_argument("--unsolved", action="store_true", help="Show only unsolved groups")
    search_parser.add_argument("--version", help="Version prefix filter (e.g. '2.4.0')")
    search_parser.add_argument("--limit", type=int, default=50, help="Max results (default: 50)")

    # popular
    popular_parser = subparsers.add_parser(
        "popular", help="Show popular (>10) unsolved crash groups"
    )
    popular_parser.add_argument("--since", help="Filter by date (ISO date or relative, e.g. '30d')")
    popular_parser.add_argument("--limit", type=int, default=50, help="Max results (default: 50)")

    # stats
    stats_parser = subparsers.add_parser("stats", help="Show aggregate crash statistics")
    stats_parser.add_argument("--since", help="Filter by date (ISO date or relative, e.g. '30d')")

    # show
    show_parser = subparsers.add_parser("show", help="Show individual crash report (anonymized)")
    show_parser.add_argument("crash_id", help="Crash report UUID")

    # group
    group_parser = subparsers.add_parser("group", help="Show crash group detail (anonymized)")
    group_parser.add_argument("group_id", type=int, help="Crash group ID")

    # local
    local_parser = subparsers.add_parser("local", help="List crash reports from local OMD sites")
    local_parser.add_argument(
        "--type", help="Crash type filter (check, gui, rest_api, section, etc.)"
    )

    # check-auth
    subparsers.add_parser("check-auth", help="Check if a valid auth token is cached (exit 0/1)")

    args = parser.parse_args()

    commands = {
        "search": cmd_search,
        "popular": cmd_popular,
        "stats": cmd_stats,
        "show": cmd_show,
        "group": cmd_group,
        "local": cmd_local,
        "check-auth": cmd_check_auth,
    }

    try:
        commands[args.command](args)
    except AuthenticationError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)
    except ApiError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
