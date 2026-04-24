# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Service restart/reload engine for OMD sites."""

from __future__ import annotations

import subprocess
import time
from types import MappingProxyType
from typing import TYPE_CHECKING

from cmk.dev_deploy.core.timeouts import SERVICE_RELOAD, SERVICE_RESTART
from cmk.dev_deploy.site.edition_filter import PRO_PLUS_EDITIONS
from cmk.dev_deploy.site.privilege import run_as_site_user, SSHState
from cmk.dev_deploy.types import ChangeCategory, Service, ServiceAction, ServiceResult

if TYPE_CHECKING:
    from cmk.dev_deploy.types import BazelTargetSet, ChangeSet, SiteInfo

# Maps deployer state names to the change categories they handle.
# Used by restart gating to filter which changes trigger service restarts.
DEPLOYER_CATEGORIES: MappingProxyType[str, frozenset[ChangeCategory]] = MappingProxyType(
    {
        "config_spec": frozenset({ChangeCategory.CONFIG, ChangeCategory.DATA}),
        "install_spec": frozenset(
            {
                ChangeCategory.CPP,
                ChangeCategory.RUST,
                ChangeCategory.VUE,
                ChangeCategory.FRONTEND,
            }
        ),
        "wheel_spec": frozenset(
            {ChangeCategory.PYTHON}
        ),  # cmk/ tree deployed as wheel; Python file changes trigger service restarts
    }
)


SERVICE_RESTART_ORDER: tuple[Service, ...] = (
    Service.CRONTAB,
    Service.APACHE,
    Service.AUTOMATION_HELPER,
    Service.UI_JOB_SCHEDULER,
    Service.DCD,
    Service.MKEVENTD,
    Service.AGENT_RECEIVER,
    Service.NAGIOS,
    Service.CMC,
)
"""Dependency-ordered execution sequence for service restarts."""

EDITION_GATED_SERVICES: MappingProxyType[Service, frozenset[str]] = MappingProxyType(
    {
        Service.CMC: PRO_PLUS_EDITIONS,
        Service.DCD: PRO_PLUS_EDITIONS,
    }
)
"""Services that only exist on specific editions."""

# cmc's long-lived helpers import from virtually every wheel, so the default
# has to include cmc:restart.  Edition gating drops it on CRE.
_WHEEL_CONVENTION_DEFAULTS: tuple[tuple[Service, ServiceAction], ...] = (
    (Service.APACHE, ServiceAction.RELOAD),
    (Service.AUTOMATION_HELPER, ServiceAction.RESTART),
    (Service.CMC, ServiceAction.RESTART),
)


def resolve_services(
    changes: ChangeSet | None,
    targets: BazelTargetSet | None,
    site: SiteInfo,
    *,
    deployed_deployers: set[str] | None = None,
) -> list[tuple[Service, ServiceAction]]:
    """Determine which services need restart based on what was deployed.

    Uses a three-tier resolution strategy:
      1. Explicit ServiceSpec entries (from deploy_specs.toml overrides)
      2. Wheel convention: any py_wheel package implies apache:reload
      3. Config spec annotations: config specs with a ``services`` field

    Explicit specs always take precedence over convention defaults.
    """
    from cmk.dev_deploy.manifest.reader import (
        get_config_specs,
        get_service_specs,
        get_wheel_specs,
    )

    all_service_specs = get_service_specs()
    all_wheel_specs = get_wheel_specs()
    all_config_specs = get_config_specs()

    # Pre-compute wheel prefixes for tier-2 matching
    wheel_prefixes = tuple(ws.package + "/" for ws in all_wheel_specs)

    raw: list[tuple[Service, ServiceAction]] = []

    if changes is None:
        # No build commit -- deploying everything, use safe defaults.
        raw.extend(_WHEEL_CONVENTION_DEFAULTS)
    else:
        # Build the set of files to check against service specs.
        # When deployed_deployers is set, restrict to categories those deployers handle.
        if deployed_deployers is not None:
            active_categories: set[ChangeCategory] = set()
            for d in deployed_deployers:
                active_categories.update(DEPLOYER_CATEGORIES.get(d, frozenset()))
            active_files: list[str] = []
            for cat in active_categories:
                active_files.extend(changes.categories.get(cat, ()))
            files_to_check: tuple[str, ...] = tuple(active_files)
        else:
            files_to_check = changes.files

        # Three-tier matching for each changed file
        for f in files_to_check:
            # Tier 1: Explicit service specs
            matched_explicit = False
            for spec in all_service_specs:
                if not f.startswith(spec.source_prefix):
                    continue
                if (
                    spec.edition_constraint is not None
                    and site.edition.value not in spec.edition_constraint
                ):
                    continue
                raw.extend(spec.services)
                matched_explicit = True

            if matched_explicit:
                continue

            # Tier 2: Wheel convention.
            if any(f.startswith(prefix) for prefix in wheel_prefixes):
                raw.extend(_WHEEL_CONVENTION_DEFAULTS)
                continue

            # Tier 3: Config spec annotations
            for cspec in all_config_specs:
                if cspec.services and f.startswith(cspec.source_prefix):
                    raw.extend(cspec.services)
                    break

    # Match Bazel target packages against service specs (and convention defaults)
    # When restart gating is active, only check targets if install_spec ran
    check_targets = deployed_deployers is None or "install_spec" in deployed_deployers
    if targets is not None and check_targets:
        packages_seen: set[str] = set()
        for target in targets.targets:
            if target.package in packages_seen:
                continue
            packages_seen.add(target.package)

            # Tier 1: Explicit service specs
            matched_explicit = False
            for spec in all_service_specs:
                prefix = spec.source_prefix.rstrip("/")
                if target.package != prefix:
                    continue
                if (
                    spec.edition_constraint is not None
                    and site.edition.value not in spec.edition_constraint
                ):
                    continue
                raw.extend(spec.services)
                matched_explicit = True

            if not matched_explicit:
                # Tier 2: Wheel convention for target packages
                if any(target.package == wp.rstrip("/") for wp in wheel_prefixes):
                    raw.extend(_WHEEL_CONVENTION_DEFAULTS)

    # Deduplicate: RESTART trumps RELOAD for the same service
    by_service: dict[Service, ServiceAction] = {}
    for svc, action in raw:
        existing = by_service.get(svc)
        if existing is None or action == ServiceAction.RESTART:
            by_service[svc] = action

    # Filter by edition-gated services
    for svc in list(by_service):
        constraint = EDITION_GATED_SERVICES.get(svc)
        if constraint is not None and site.edition.value not in constraint:
            del by_service[svc]

    # Sort by dependency order
    order_index = {svc: i for i, svc in enumerate(SERVICE_RESTART_ORDER)}
    return sorted(by_service.items(), key=lambda pair: order_index.get(pair[0], 999))


def restart_services(
    services: list[tuple[Service, ServiceAction]],
    site: SiteInfo,
    state: SSHState,
) -> ServiceResult:
    """Execute service restart/reload commands, collecting failures without aborting."""
    start = time.monotonic()
    succeeded = 0
    failed = 0
    failures: list[str] = []

    for service, action in services:
        timeout = SERVICE_RELOAD if action == ServiceAction.RELOAD else SERVICE_RESTART
        try:
            result = _run_omd_command(
                site.name, action.value, service.value, state, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            from cmk.dev_deploy.core import output

            output.warn(f"omd {action.value} {service.value}: timed out after {timeout}s")
            failed += 1
            failures.append(service.value)
            continue

        if result.returncode == 0:
            succeeded += 1
        else:
            from cmk.dev_deploy.core import output

            detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
            output.verbose(
                f"omd {action.value} {service.value} failed (exit {result.returncode}): {detail}"
            )
            failed += 1
            failures.append(service.value)

    elapsed = time.monotonic() - start
    return ServiceResult(
        services_restarted=succeeded,
        services_failed=failed,
        elapsed=elapsed,
        failures=tuple(failures),
    )


def _run_omd_command(
    site_name: str,
    action: str,
    service: str,
    state: SSHState,
    timeout: int = 30,
) -> subprocess.CompletedProcess[str]:
    """Run an omd service command as the site user."""
    return run_as_site_user(
        site_name,
        f"omd {action} {service}",
        state,
        timeout=timeout,
    )
