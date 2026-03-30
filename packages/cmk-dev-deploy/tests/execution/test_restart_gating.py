# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for service restart gating via deployed_deployers filter."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from cmk.dev_deploy.execution.service_manager import (
    DEPLOYER_CATEGORIES,
    resolve_services,
)
from cmk.dev_deploy.types import (
    BazelTarget,
    BazelTargetKind,
    BazelTargetSet,
    ChangeCategory,
    ChangeSet,
    Edition,
    Service,
    ServiceAction,
    ServiceSpec,
    SiteInfo,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service_spec(
    source_prefix: str,
    services: list[tuple[Service, ServiceAction]],
    edition_constraint: frozenset[str] | None = None,
) -> ServiceSpec:
    """Construct a ServiceSpec with given prefix and service pairs."""
    return ServiceSpec(
        source_prefix=source_prefix,
        services=tuple(services),
        edition_constraint=edition_constraint,
    )


def _make_changes(
    files: tuple[str, ...],
    categories: dict[ChangeCategory, tuple[str, ...]] | None = None,
) -> ChangeSet:
    """Construct a ChangeSet with given files and explicit categories."""
    if categories is None:
        categories = {}
    return ChangeSet(
        build_commit="a" * 40,
        files=files,
        categories=categories,
    )


def _make_site(edition: str = "pro") -> SiteInfo:
    """Construct a SiteInfo with minimal fields for testing."""
    return SiteInfo(
        name="test",
        root=Path("/omd/sites/test"),
        edition=Edition.from_version_suffix(edition),
        version_string=f"2.6.0-2026.02.13.{edition}",
        build_commit="b" * 40,
    )


# Test service specs fixture modelling the real manifest
_TEST_SERVICE_SPECS: tuple[ServiceSpec, ...] = (
    _make_service_spec("cmk/", [(Service.APACHE, ServiceAction.RELOAD)]),
    _make_service_spec(
        "cmk/gui/",
        [
            (Service.APACHE, ServiceAction.RELOAD),
            (Service.UI_JOB_SCHEDULER, ServiceAction.RESTART),
        ],
    ),
    _make_service_spec("agents/", [(Service.CRONTAB, ServiceAction.RELOAD)]),
    _make_service_spec("packages/livestatus", [(Service.NAGIOS, ServiceAction.RESTART)]),
)


def _make_targets(packages: tuple[str, ...]) -> BazelTargetSet:
    """Create a BazelTargetSet from package names."""
    targets = tuple(
        BazelTarget(label=f"//{pkg}:all", kind=BazelTargetKind.CC_BINARY, package=pkg)
        for pkg in packages
    )
    return BazelTargetSet(
        targets=targets,
        files_queried=len(packages),
        files_resolved=len(packages),
        from_cache=False,
        query_time_ms=0,
    )


# ---------------------------------------------------------------------------
# TestResolveServicesWithDeployedDeployers
# ---------------------------------------------------------------------------


@patch("cmk.dev_deploy.manifest.reader.get_config_specs", return_value=())
@patch("cmk.dev_deploy.manifest.reader.get_wheel_specs", return_value=())
@patch(
    "cmk.dev_deploy.manifest.reader.get_service_specs",
    return_value=_TEST_SERVICE_SPECS,
)
class TestResolveServicesWithDeployedDeployers:
    """Tests for resolve_services deployed_deployers filter."""

    def test_no_filter_returns_all_matching(
        self, _mock_svc: object, _mock_whl: object, _mock_cfg: object
    ) -> None:
        """deployed_deployers=None -> all matching files contribute (backward compat)."""
        changes = _make_changes(
            files=("cmk/foo.py", "agents/bar.cfg"),
            categories={
                ChangeCategory.PYTHON: ("cmk/foo.py",),
                ChangeCategory.CONFIG: ("agents/bar.cfg",),
            },
        )
        site = _make_site()
        result = resolve_services(changes, None, site, deployed_deployers=None)
        services = {svc for svc, _ in result}
        assert Service.APACHE in services
        assert Service.CRONTAB in services

    def test_filter_wheel_python_only(
        self, _mock_svc: object, _mock_whl: object, _mock_cfg: object
    ) -> None:
        """deployed_deployers={'wheel_spec'} -> only python category files match."""
        changes = _make_changes(
            files=("cmk/foo.py", "agents/bar.cfg"),
            categories={
                ChangeCategory.PYTHON: ("cmk/foo.py",),
                ChangeCategory.CONFIG: ("agents/bar.cfg",),
            },
        )
        site = _make_site()
        result = resolve_services(changes, None, site, deployed_deployers={"wheel_spec"})
        services = {svc for svc, _ in result}
        # cmk/foo.py is PYTHON -> apache (wheel_spec handles PYTHON category)
        assert Service.APACHE in services
        # agents/bar.cfg is CONFIG -> crontab, but config_spec didn't run
        assert Service.CRONTAB not in services

    def test_filter_config_only(
        self, _mock_svc: object, _mock_whl: object, _mock_cfg: object
    ) -> None:
        """deployed_deployers={'config_spec'} -> only config/data category files match."""
        changes = _make_changes(
            files=("cmk/foo.py", "agents/bar.cfg"),
            categories={
                ChangeCategory.PYTHON: ("cmk/foo.py",),
                ChangeCategory.CONFIG: ("agents/bar.cfg",),
            },
        )
        site = _make_site()
        result = resolve_services(changes, None, site, deployed_deployers={"config_spec"})
        services = {svc for svc, _ in result}
        # agents/bar.cfg is CONFIG -> crontab
        assert Service.CRONTAB in services
        # cmk/foo.py is PYTHON -> apache, but wheel_spec didn't run
        assert Service.APACHE not in services

    def test_filter_install_spec_checks_targets(
        self, _mock_svc: object, _mock_whl: object, _mock_cfg: object
    ) -> None:
        """deployed_deployers={'install_spec'} with targets -> target packages match."""
        changes = _make_changes(
            files=("packages/livestatus/src/foo.cc",),
            categories={
                ChangeCategory.CPP: ("packages/livestatus/src/foo.cc",),
            },
        )
        targets = _make_targets(("packages/livestatus",))
        site = _make_site()
        result = resolve_services(changes, targets, site, deployed_deployers={"install_spec"})
        services = {svc for svc, _ in result}
        assert Service.NAGIOS in services

    def test_filter_excludes_targets_when_install_not_deployed(
        self, _mock_svc: object, _mock_whl: object, _mock_cfg: object
    ) -> None:
        """deployed_deployers={'wheel_spec'} -> targets NOT checked."""
        changes = _make_changes(
            files=("cmk/foo.py", "packages/livestatus/src/foo.cc"),
            categories={
                ChangeCategory.PYTHON: ("cmk/foo.py",),
                ChangeCategory.CPP: ("packages/livestatus/src/foo.cc",),
            },
        )
        targets = _make_targets(("packages/livestatus",))
        site = _make_site()
        result = resolve_services(changes, targets, site, deployed_deployers={"wheel_spec"})
        services = {svc for svc, _ in result}
        # wheel_spec ran -> apache from cmk/foo.py
        assert Service.APACHE in services
        # install_spec didn't run -> nagios from packages/livestatus should NOT appear
        assert Service.NAGIOS not in services

    def test_empty_deployed_deployers_returns_nothing(
        self, _mock_svc: object, _mock_whl: object, _mock_cfg: object
    ) -> None:
        """deployed_deployers=set() -> no files match, no targets match."""
        changes = _make_changes(
            files=("cmk/foo.py", "agents/bar.cfg"),
            categories={
                ChangeCategory.PYTHON: ("cmk/foo.py",),
                ChangeCategory.CONFIG: ("agents/bar.cfg",),
            },
        )
        targets = _make_targets(("packages/livestatus",))
        site = _make_site()
        result = resolve_services(changes, targets, site, deployed_deployers=set())
        assert result == []

    def test_deployer_categories_mapping_complete(
        self, _mock_svc: object, _mock_whl: object, _mock_cfg: object
    ) -> None:
        """DEPLOYER_CATEGORIES has entries for all 3 deployer names."""
        expected = {"config_spec", "install_spec", "wheel_spec"}
        assert set(DEPLOYER_CATEGORIES.keys()) == expected
