# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.service_manager (resolve_services)."""

from __future__ import annotations

from pathlib import Path

import pytest

from cmk.dev_deploy.execution.service_manager import resolve_services
from cmk.dev_deploy.types import (
    BazelTarget,
    BazelTargetKind,
    BazelTargetSet,
    ChangeCategory,
    ChangeSet,
    ConfigDeploySpec,
    DeployMethod,
    Edition,
    Service,
    ServiceAction,
    ServiceSpec,
    SiteInfo,
    WheelDeployMode,
    WheelDeploySpec,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _site(edition: Edition = Edition.PRO) -> SiteInfo:
    return SiteInfo(
        name="test",
        root=Path("/omd/sites/test"),
        edition=edition,
        version_string="2.6.0.pro",
        build_commit="a" * 40,
    )


def _changeset(
    files: tuple[str, ...] = (),
    categories: dict[ChangeCategory, tuple[str, ...]] | None = None,
) -> ChangeSet:
    return ChangeSet(
        build_commit="b" * 40,
        files=files,
        categories=categories or {},
    )


def _target_set(targets: tuple[BazelTarget, ...] = ()) -> BazelTargetSet:
    return BazelTargetSet(
        targets=targets,
        files_queried=0,
        files_resolved=0,
        from_cache=False,
        query_time_ms=0,
    )


def _bazel_target(package: str, label: str | None = None) -> BazelTarget:
    return BazelTarget(
        label=label or f"//{package}:target",
        kind=BazelTargetKind.CC_BINARY,
        package=package,
    )


def _wheel_spec(package: str) -> WheelDeploySpec:
    return WheelDeploySpec(
        package=package,
        wheel_targets=(f"//{package}:wheel",),
        edition_constraint=None,
        deploy_mode=WheelDeployMode.DIRECT,
        source_subdirs=(),
        distribution_name=package.replace("/", "-"),
    )


def _config_spec(
    source_prefix: str,
    services: tuple[tuple[Service, ServiceAction], ...] = (),
) -> ConfigDeploySpec:
    return ConfigDeploySpec(
        source_prefix=source_prefix,
        site_dest=f"share/{source_prefix}",
        method=DeployMethod.COPY_DIR,
        mode=None,
        includes=(),
        files=(),
        delete_extra=False,
        file_chmod=None,
        services=services,
    )


def _patch_specs(
    monkeypatch: pytest.MonkeyPatch,
    *,
    service_specs: list[ServiceSpec] | None = None,
    wheel_specs: list[WheelDeploySpec] | None = None,
    config_specs: list[ConfigDeploySpec] | None = None,
) -> None:
    """Patch all three spec getters used by resolve_services()."""
    monkeypatch.setattr(
        "cmk.dev_deploy.manifest.reader.get_service_specs",
        lambda: service_specs or [],
    )
    monkeypatch.setattr(
        "cmk.dev_deploy.manifest.reader.get_wheel_specs",
        lambda: wheel_specs or [],
    )
    monkeypatch.setattr(
        "cmk.dev_deploy.manifest.reader.get_config_specs",
        lambda: config_specs or [],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestResolveServicesDefaults:
    """When changes is None, return safe defaults."""

    def test_changes_none_returns_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_specs(monkeypatch)
        result = resolve_services(None, None, _site())
        assert (Service.APACHE, ServiceAction.RELOAD) in result
        assert (Service.AUTOMATION_HELPER, ServiceAction.RESTART) in result
        assert len(result) == 2


class TestResolveServicesFileMatching:
    """File path matching against service specs."""

    def test_no_specs_match_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_specs(
            monkeypatch,
            service_specs=[
                ServiceSpec(
                    source_prefix="cmk/gui/",
                    services=((Service.APACHE, ServiceAction.RELOAD),),
                    edition_constraint=None,
                ),
            ],
        )
        changes = _changeset(files=("packages/foo/bar.py",))
        result = resolve_services(changes, None, _site())
        assert result == []

    def test_file_matches_spec(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_specs(
            monkeypatch,
            service_specs=[
                ServiceSpec(
                    source_prefix="cmk/gui/",
                    services=((Service.APACHE, ServiceAction.RELOAD),),
                    edition_constraint=None,
                ),
            ],
        )
        changes = _changeset(files=("cmk/gui/views.py",))
        result = resolve_services(changes, None, _site())
        assert result == [(Service.APACHE, ServiceAction.RELOAD)]


class TestResolveServicesDedup:
    """RESTART trumps RELOAD for the same service."""

    def test_restart_trumps_reload(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_specs(
            monkeypatch,
            service_specs=[
                ServiceSpec(
                    source_prefix="cmk/gui/",
                    services=((Service.APACHE, ServiceAction.RELOAD),),
                    edition_constraint=None,
                ),
                ServiceSpec(
                    source_prefix="cmk/gui/plugins/",
                    services=((Service.APACHE, ServiceAction.RESTART),),
                    edition_constraint=None,
                ),
            ],
        )
        changes = _changeset(
            files=("cmk/gui/views.py", "cmk/gui/plugins/wato.py"),
        )
        result = resolve_services(changes, None, _site())
        assert len(result) == 1
        assert result[0] == (Service.APACHE, ServiceAction.RESTART)


class TestResolveServicesEditionGating:
    """Edition-gated services (CMC, DCD) filtered on community."""

    def test_edition_gated_filtered_on_community(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_specs(
            monkeypatch,
            service_specs=[
                ServiceSpec(
                    source_prefix="cmk/cmc/",
                    services=((Service.CMC, ServiceAction.RESTART),),
                    edition_constraint=None,
                ),
            ],
        )
        changes = _changeset(files=("cmk/cmc/core.py",))
        result = resolve_services(changes, None, _site(Edition.COMMUNITY))
        assert result == []

    def test_edition_gated_included_on_pro(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_specs(
            monkeypatch,
            service_specs=[
                ServiceSpec(
                    source_prefix="cmk/cmc/",
                    services=((Service.CMC, ServiceAction.RESTART),),
                    edition_constraint=None,
                ),
            ],
        )
        changes = _changeset(files=("cmk/cmc/core.py",))
        result = resolve_services(changes, None, _site(Edition.PRO))
        assert result == [(Service.CMC, ServiceAction.RESTART)]


class TestResolveServicesOrdering:
    """Results follow SERVICE_RESTART_ORDER."""

    def test_ordering_follows_restart_order(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_specs(
            monkeypatch,
            service_specs=[
                ServiceSpec(
                    source_prefix="cmk/gui/",
                    services=(
                        (Service.AUTOMATION_HELPER, ServiceAction.RESTART),
                        (Service.APACHE, ServiceAction.RELOAD),
                    ),
                    edition_constraint=None,
                ),
            ],
        )
        changes = _changeset(files=("cmk/gui/views.py",))
        result = resolve_services(changes, None, _site())
        services = [svc for svc, _ in result]
        assert services.index(Service.APACHE) < services.index(Service.AUTOMATION_HELPER)


class TestResolveServicesDeployedDeployers:
    """deployed_deployers restricts which file categories are checked."""

    def test_deployed_deployers_restricts_categories(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_specs(
            monkeypatch,
            service_specs=[
                ServiceSpec(
                    source_prefix="cmk/gui/",
                    services=((Service.APACHE, ServiceAction.RELOAD),),
                    edition_constraint=None,
                ),
            ],
        )
        # The file is in changes.files but NOT in any category handled by config_spec
        changes = _changeset(
            files=("cmk/gui/views.py",),
            categories={
                ChangeCategory.PYTHON: ("cmk/gui/views.py",),
            },
        )
        # Only config_spec deployed -> only CONFIG/DATA categories checked
        # PYTHON category is not in config_spec's categories, so no files match
        result = resolve_services(changes, None, _site(), deployed_deployers={"config_spec"})
        assert result == []

    def test_deployed_deployers_includes_matching_category(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_specs(
            monkeypatch,
            service_specs=[
                ServiceSpec(
                    source_prefix="cmk/gui/",
                    services=((Service.APACHE, ServiceAction.RELOAD),),
                    edition_constraint=None,
                ),
            ],
        )
        changes = _changeset(
            files=("cmk/gui/views.py",),
            categories={
                ChangeCategory.PYTHON: ("cmk/gui/views.py",),
            },
        )
        # wheel_spec handles PYTHON -> file is checked
        result = resolve_services(changes, None, _site(), deployed_deployers={"wheel_spec"})
        assert result == [(Service.APACHE, ServiceAction.RELOAD)]


class TestResolveServicesBazelTargets:
    """Bazel target package matching against service specs."""

    def test_bazel_target_matches_spec(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_specs(
            monkeypatch,
            service_specs=[
                ServiceSpec(
                    source_prefix="packages/livestatus/",
                    services=((Service.CMC, ServiceAction.RESTART),),
                    edition_constraint=None,
                ),
            ],
        )
        targets = _target_set(
            targets=(_bazel_target("packages/livestatus"),),
        )
        changes = _changeset()
        result = resolve_services(changes, targets, _site())
        assert result == [(Service.CMC, ServiceAction.RESTART)]

    def test_bazel_target_gated_on_install_spec_deployer(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_specs(
            monkeypatch,
            service_specs=[
                ServiceSpec(
                    source_prefix="packages/livestatus/",
                    services=((Service.CMC, ServiceAction.RESTART),),
                    edition_constraint=None,
                ),
            ],
        )
        targets = _target_set(
            targets=(_bazel_target("packages/livestatus"),),
        )
        changes = _changeset()
        # Only wheel_spec deployed -> install_spec not in deployed_deployers -> targets skipped
        result = resolve_services(changes, targets, _site(), deployed_deployers={"wheel_spec"})
        assert result == []

    def test_bazel_target_included_when_install_spec_deployed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_specs(
            monkeypatch,
            service_specs=[
                ServiceSpec(
                    source_prefix="packages/livestatus/",
                    services=((Service.CMC, ServiceAction.RESTART),),
                    edition_constraint=None,
                ),
            ],
        )
        targets = _target_set(
            targets=(_bazel_target("packages/livestatus"),),
        )
        changes = _changeset()
        result = resolve_services(changes, targets, _site(), deployed_deployers={"install_spec"})
        assert result == [(Service.CMC, ServiceAction.RESTART)]


# ---------------------------------------------------------------------------
# Convention defaults (tier 2 & 3)
# ---------------------------------------------------------------------------


class TestWheelConventionDefault:
    """Wheel packages auto-derive apache:reload when no explicit spec matches."""

    def test_wheel_convention_apache_reload(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """File under a wheel prefix with no explicit service spec -> apache:reload."""
        _patch_specs(
            monkeypatch,
            wheel_specs=[_wheel_spec("packages/cmk-ccc")],
        )
        changes = _changeset(files=("packages/cmk-ccc/foo.py",))
        result = resolve_services(changes, None, _site())
        assert result == [(Service.APACHE, ServiceAction.RELOAD)]

    def test_explicit_overrides_wheel_convention(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Explicit service spec takes precedence over wheel convention."""
        _patch_specs(
            monkeypatch,
            service_specs=[
                ServiceSpec(
                    source_prefix="packages/cmk-ec",
                    services=((Service.MKEVENTD, ServiceAction.RESTART),),
                    edition_constraint=None,
                ),
            ],
            wheel_specs=[_wheel_spec("packages/cmk-ec")],
        )
        changes = _changeset(files=("packages/cmk-ec/foo.py",))
        result = resolve_services(changes, None, _site())
        assert result == [(Service.MKEVENTD, ServiceAction.RESTART)]

    def test_sub_path_override_within_wheel(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Sub-path explicit spec wins over wheel convention for the cmk/ wheel."""
        _patch_specs(
            monkeypatch,
            service_specs=[
                ServiceSpec(
                    source_prefix="cmk/base/",
                    services=((Service.AUTOMATION_HELPER, ServiceAction.RESTART),),
                    edition_constraint=None,
                ),
            ],
            wheel_specs=[_wheel_spec("cmk")],
        )
        changes = _changeset(files=("cmk/base/config.py",))
        result = resolve_services(changes, None, _site())
        # Explicit spec wins — only automation-helper, no apache:reload from wheel
        assert result == [(Service.AUTOMATION_HELPER, ServiceAction.RESTART)]

    def test_no_default_for_unmatched_file(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """File not under any wheel or config spec -> no services."""
        _patch_specs(
            monkeypatch,
            wheel_specs=[_wheel_spec("packages/cmk-ccc")],
        )
        changes = _changeset(files=("some/random/file.txt",))
        result = resolve_services(changes, None, _site())
        assert result == []

    def test_wheel_convention_deduplicates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Multiple files under different wheels still produce single apache:reload."""
        _patch_specs(
            monkeypatch,
            wheel_specs=[
                _wheel_spec("packages/cmk-ccc"),
                _wheel_spec("packages/cmk-crypto"),
            ],
        )
        changes = _changeset(
            files=(
                "packages/cmk-ccc/foo.py",
                "packages/cmk-crypto/bar.py",
            ),
        )
        result = resolve_services(changes, None, _site())
        assert result == [(Service.APACHE, ServiceAction.RELOAD)]

    def test_wheel_convention_for_bazel_targets(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Bazel target matching also falls through to wheel convention."""
        _patch_specs(
            monkeypatch,
            wheel_specs=[_wheel_spec("packages/cmk-ccc")],
        )
        targets = _target_set(
            targets=(_bazel_target("packages/cmk-ccc"),),
        )
        changes = _changeset()
        result = resolve_services(changes, targets, _site())
        assert result == [(Service.APACHE, ServiceAction.RELOAD)]

    def test_wheel_convention_respects_deployer_gating(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Wheel convention only fires when wheel_spec is in deployed_deployers."""
        _patch_specs(
            monkeypatch,
            wheel_specs=[_wheel_spec("packages/cmk-ccc")],
        )
        changes = _changeset(
            files=("packages/cmk-ccc/foo.py",),
            categories={
                ChangeCategory.PYTHON: ("packages/cmk-ccc/foo.py",),
            },
        )
        # config_spec deployed -> PYTHON not in its categories -> file not checked
        result = resolve_services(changes, None, _site(), deployed_deployers={"config_spec"})
        assert result == []


class TestConfigSpecServicesAnnotation:
    """Config specs with services annotation trigger restarts."""

    def test_config_spec_services(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """File under config spec with services -> those services triggered."""
        _patch_specs(
            monkeypatch,
            config_specs=[
                _config_spec(
                    "agents/",
                    services=((Service.APACHE, ServiceAction.RELOAD),),
                ),
            ],
        )
        changes = _changeset(files=("agents/plugins/foo",))
        result = resolve_services(changes, None, _site())
        assert result == [(Service.APACHE, ServiceAction.RELOAD)]

    def test_config_spec_without_services_no_restart(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Config spec without services annotation does not trigger restarts."""
        _patch_specs(
            monkeypatch,
            config_specs=[_config_spec("omd/packages/")],
        )
        changes = _changeset(files=("omd/packages/foo/bar",))
        result = resolve_services(changes, None, _site())
        assert result == []

    def test_explicit_spec_overrides_config_spec(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Explicit service spec takes precedence over config spec annotation."""
        _patch_specs(
            monkeypatch,
            service_specs=[
                ServiceSpec(
                    source_prefix="agents/special/",
                    services=((Service.AUTOMATION_HELPER, ServiceAction.RESTART),),
                    edition_constraint=None,
                ),
            ],
            config_specs=[
                _config_spec(
                    "agents/",
                    services=((Service.APACHE, ServiceAction.RELOAD),),
                ),
            ],
        )
        changes = _changeset(files=("agents/special/foo",))
        result = resolve_services(changes, None, _site())
        # Explicit spec wins
        assert result == [(Service.AUTOMATION_HELPER, ServiceAction.RESTART)]

    def test_config_spec_services_respects_deployer_gating(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Config spec services only fire when config_spec is in deployed_deployers."""
        _patch_specs(
            monkeypatch,
            config_specs=[
                _config_spec(
                    "agents/",
                    services=((Service.APACHE, ServiceAction.RELOAD),),
                ),
            ],
        )
        changes = _changeset(
            files=("agents/plugins/foo",),
            categories={
                ChangeCategory.CONFIG: ("agents/plugins/foo",),
            },
        )
        # wheel_spec deployed -> CONFIG not in its categories -> file not checked
        result = resolve_services(changes, None, _site(), deployed_deployers={"wheel_spec"})
        assert result == []
