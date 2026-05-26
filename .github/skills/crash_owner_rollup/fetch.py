# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Fetch unsolved check-crash groups and enrich them with check_type + plugin_path.

Uses the local crash_report module's auth helpers, and caches per-group
enrichment keyed by (group_id, num_crashes). When num_crashes is unchanged
the report fetch is skipped — that's where the runtime win comes from.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import as_completed, ThreadPoolExecutor
from typing import Any

from crash_report.fetch_crash_data import _get_auth_headers, API_BASE

from .cache import EnrichedGroup, load_enrichment_cache, save_enrichment_cache


def _api(path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    url = f"{API_BASE}/{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=_get_auth_headers())
    with urllib.request.urlopen(req, timeout=60) as resp:  # nosec
        result: dict[str, Any] = json.loads(resp.read().decode())
        return result


def _version_tuple(v: str) -> tuple[int, ...]:
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", v)
    if not m:
        return (0,)
    parts = [int(m.group(1)), int(m.group(2)), int(m.group(3))]
    pm = re.search(r"[pb](\d+)$", v)
    if pm:
        parts.append(int(pm.group(1)))
    return tuple(parts)


def _is_min_version(v: str, minimum: tuple[int, int]) -> bool:
    return _version_tuple(v) >= minimum


def _fetch_group_details(
    group_id: int, min_version: tuple[int, int]
) -> tuple[dict[str, Any], str | None]:
    """Fetch group; return (group_dict, newest_crash_id_on_min_version_or_None)."""
    g = _api(f"crash_group/{group_id}").get("crash_group", {})
    reports = sorted(
        g.get("crash_reports") or [],
        key=lambda r: r.get("upload_time", ""),
        reverse=True,
    )
    newest = next(
        (r for r in reports if _is_min_version(r.get("cmk_version", ""), min_version)),
        None,
    )
    return g, (newest or {}).get("crash_id")


def _fetch_report_metadata(crash_id: str) -> tuple[str, str, str]:
    """Return (check_type, section_name, plugin_path) for one crash report."""
    r = _api(f"crash_report/{crash_id}").get("crash_report", {})
    details = r.get("details", {}) or {}
    tb = r.get("exc_traceback") or []
    plugin_path = ""
    for frame in reversed(tb):
        if not frame:
            continue
        fn = frame[0]
        if any(
            s in fn
            for s in (
                "/cmk/plugins/",
                "/cmk/base/plugins/",
                "/local/share/check_mk/",
                "/cmk_addons/",
            )
        ):
            plugin_path = fn
            break
    if not plugin_path and tb:
        plugin_path = tb[-1][0] if tb[-1] else ""
    return (
        details.get("check_type", ""),
        details.get("section_name", ""),
        plugin_path,
    )


def fetch_enriched_groups(
    min_version: tuple[int, int] = (2, 4),
    use_cache: bool = True,
    max_workers: int = 12,
    progress: bool = True,
) -> list[EnrichedGroup]:
    """Return enriched data for every unsolved check group with a min-version+ report.

    Uses (group_id, num_crashes) as the cache key.
    """
    cache = load_enrichment_cache() if use_cache else {}

    listing = _api("search", {"crash_type": "check", "solved": "false", "limit": "1000"}).get(
        "crash_groups", []
    )
    if progress:
        print(f"# {len(listing)} unsolved check groups in listing", file=sys.stderr)

    # Decide who needs a refresh
    fresh: list[EnrichedGroup] = []
    stale_ids: list[int] = []
    for entry in listing:
        gid = int(entry["id"])
        n = int(entry["num_crashes"])
        cached = cache.get(gid)
        if cached is not None and cached.num_crashes == n:
            fresh.append(cached)
        else:
            stale_ids.append(gid)

    if progress:
        print(
            f"# cache hit on {len(fresh)} groups; refreshing {len(stale_ids)}",
            file=sys.stderr,
        )

    # Refresh stale groups: fetch group detail + (if any min-version+ report) crash report
    new_entries: list[EnrichedGroup] = []
    listing_num: dict[int, int] = {int(e["id"]): int(e["num_crashes"]) for e in listing}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        group_futs = {ex.submit(_fetch_group_details, gid, min_version): gid for gid in stale_ids}
        report_jobs: dict[int, tuple[dict[str, Any], str]] = {}
        for i, fut in enumerate(as_completed(group_futs), 1):
            gid = group_futs[fut]
            try:
                gdata, newest_id = fut.result()
            except Exception as exc:
                if progress:
                    print(f"  group {gid} failed: {exc}", file=sys.stderr)
                continue
            if not newest_id:
                # No min-version+ report -> cache the negative result so we skip next run
                new_entries.append(
                    EnrichedGroup(
                        group_id=gid,
                        num_crashes=listing_num.get(gid, int(gdata.get("num_crashes", 0))),
                        has_24_plus=False,
                        check_type="",
                        section_name="",
                        plugin_path="",
                        latest_24_version="",
                    )
                )
                continue
            report_jobs[gid] = (gdata, newest_id)
            if progress and i % 20 == 0:
                print(f"  fetched {i}/{len(stale_ids)} groups", file=sys.stderr)

        report_futs = {
            ex.submit(_fetch_report_metadata, crash_id): (gid, gdata)
            for gid, (gdata, crash_id) in report_jobs.items()
        }
        for j, report_fut in enumerate(as_completed(report_futs), 1):
            gid, gdata = report_futs[report_fut]
            try:
                check_type, section_name, plugin_path = report_fut.result()
            except Exception as exc:
                if progress:
                    print(f"  report for {gid} failed: {exc}", file=sys.stderr)
                check_type, section_name, plugin_path = "", "", ""
            new_entries.append(
                EnrichedGroup(
                    group_id=gid,
                    num_crashes=int(gdata.get("num_crashes", 0)),
                    has_24_plus=True,
                    check_type=check_type,
                    section_name=section_name,
                    plugin_path=plugin_path,
                    latest_24_version="",  # not currently needed downstream
                )
            )
            if progress and j % 20 == 0:
                print(f"  enriched {j} reports", file=sys.stderr)

    # Merge cached + new, including negative (no-2.4+) entries so future runs skip them
    merged: dict[int, EnrichedGroup] = {g.group_id: g for g in fresh}
    for g in new_entries:
        merged[g.group_id] = g
    save_enrichment_cache(merged)

    # Return only groups in the current listing with a min-version+ report
    listing_ids = {int(e["id"]) for e in listing}
    surviving_listing: dict[int, EnrichedGroup] = {
        gid: g for gid, g in merged.items() if gid in listing_ids and g.has_24_plus
    }

    return sorted(surviving_listing.values(), key=lambda g: -g.num_crashes)
