# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Core data types for cmk-dev-deploy."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from cmk.dev_deploy.state.deploy_state import DeployerState


class Edition(str, Enum):
    """Checkmk edition identifiers matching version symlink suffixes."""

    COMMUNITY = "community"
    PRO = "pro"
    ULTIMATE = "ultimate"
    ULTIMATEMT = "ultimatemt"
    CLOUD = "cloud"

    @classmethod
    def from_version_suffix(cls, suffix: str) -> Edition:
        """Parse an Edition from the version symlink suffix."""
        try:
            return cls(suffix)
        except ValueError:
            valid = ", ".join(e.value for e in cls)
            raise ValueError(f"Unknown edition suffix: {suffix!r}. Valid editions: {valid}")

    def matches(self, constraint: Collection[str] | None) -> bool:
        """Return True if this edition satisfies *constraint* (None = all match)."""
        return constraint is None or self.value in constraint


@dataclass(frozen=True)
class SiteInfo:
    """Information about a resolved OMD site."""

    name: str
    root: Path
    edition: Edition
    version_string: str
    build_commit: str | None


class ChangeCategory(str, Enum):
    """Categories of changed files, determining deployment strategy."""

    PYTHON = "python"
    CPP = "cpp"
    RUST = "rust"
    VUE = "vue"
    FRONTEND = "frontend"
    CONFIG = "config"
    DATA = "data"
    BUILD = "build"
    TEST = "test"
    OTHER = "other"


@dataclass(frozen=True)
class CategorizationRule:
    """A single file categorization rule derived from the deploy manifest.

    Used by change_detector to classify files by path prefix and extension.
    Rules with extensions=None match any file under the prefix.
    """

    prefix: str
    extensions: frozenset[str] | None
    category: ChangeCategory


@dataclass(frozen=True)
class ChangeSet:
    """Result of change detection between site build commit and working tree."""

    build_commit: str
    files: tuple[str, ...]
    categories: dict[ChangeCategory, tuple[str, ...]]
    deleted_files: tuple[str, ...] = ()

    @property
    def is_empty(self) -> bool:
        """True when no files changed between build commit and working tree."""
        return len(self.files) == 0 and len(self.deleted_files) == 0

    @property
    def has_python_only(self) -> bool:
        """True when all deployable changes are Python files (fast path eligible)."""
        deployable = {
            cat
            for cat in self.categories
            if cat not in (ChangeCategory.TEST, ChangeCategory.OTHER, ChangeCategory.BUILD)
        }
        return deployable == {ChangeCategory.PYTHON} or len(deployable) == 0


class BazelTargetKind(str, Enum):
    """Kind of Bazel target, determining build and install strategy."""

    CC_BINARY = "cc_binary"
    CC_LIBRARY = "cc_library"
    CC_SHARED_LIBRARY = "cc_shared_library"
    RUST_BINARY = "rust_binary"
    RUST_LIBRARY = "rust_library"
    JS_RUN_BINARY = "js_run_binary"
    PY_LIBRARY = "py_library"
    PY_WHEEL = "py_wheel"
    OTHER = "other"

    @classmethod
    def from_query_kind(cls, kind_str: str) -> BazelTargetKind:
        """Parse a kind string, returning OTHER for unknown kinds."""
        try:
            return cls(kind_str)
        except ValueError:
            return cls.OTHER


@dataclass(frozen=True)
class BazelTarget:
    """A single resolved Bazel build target."""

    label: str
    kind: BazelTargetKind
    package: str


@dataclass(frozen=True)
class BazelTargetSet:
    """Result of Bazel target resolution from changed files."""

    targets: tuple[BazelTarget, ...]
    files_queried: int
    files_resolved: int
    from_cache: bool
    query_time_ms: int

    @property
    def is_empty(self) -> bool:
        """True when no Bazel targets need building."""
        return len(self.targets) == 0

    @property
    def labels(self) -> tuple[str, ...]:
        """All target labels, for passing to ``bazel build``."""
        return tuple(t.label for t in self.targets)


class PostInstallAction(str, Enum):
    """Post-install actions to apply to a deployed artifact."""

    SETCAP_NET_RAW = "setcap_net_raw"


@dataclass(frozen=True)
class InstallSpec:
    """Specification for installing a single built artifact to an OMD site."""

    package: str
    package_target: str
    output_basename: str
    install_dest: str
    mode: int
    post_install: tuple[PostInstallAction, ...]
    edition_constraint: frozenset[str] | None
    needs_version_flag: bool
    needs_faked_artifacts: bool

    use_copytree: bool
    """True for directory deploys (Vue/frontend) using copytree instead of install."""

    frontend_supervised: bool = False
    """True if Bazel build is skipped when --frontend is active (Vite HMR)."""


@dataclass(frozen=True)
class WheelDeploySpec:
    """Specification for deploying a Python wheel package to an OMD site."""

    package: str
    wheel_targets: tuple[str, ...]
    edition_constraint: frozenset[str] | None

    deploy_mode: WheelDeployMode
    """Deploy strategy: DIRECT (direct source copy) or GENERATED (bazel build + zipfile)."""

    source_subdirs: tuple[str, ...]
    distribution_name: str

    edition_filter: bool = False
    """When True, run post-deploy edition directory pruning (cmk/ tree)."""


@dataclass(frozen=True)
class ConfigFileEntry:
    """A single file entry from the Bazel pkg_files build graph."""

    src: str
    dest: str
    mode: str


class DeployMethod(StrEnum):
    """How to deploy files from source to destination."""

    COPY_DIR = "copy_dir"
    INSTALL_FILES = "install_files"
    LOCALE_COMPILE = "locale_compile"


class WheelDeployMode(StrEnum):
    """How to deploy a Python wheel package."""

    DIRECT = "direct"
    FLAT = "flat"
    GENERATED = "generated"


@dataclass(frozen=True)
class ConfigDeploySpec:
    """Specification for deploying a config/data directory to an OMD site."""

    source_prefix: str
    site_dest: str
    method: DeployMethod
    mode: int | None
    includes: tuple[str, ...]
    files: tuple[ConfigFileEntry, ...]

    delete_extra: bool
    """Whether to delete extraneous files at the destination."""

    file_chmod: str | None
    """File chmod value, e.g. ``'755'`` (for agents/windows/plugins)."""

    services: tuple[tuple[Service, ServiceAction], ...] = ()
    """Service restarts triggered by changes to files under this config spec."""


class ServiceAction(StrEnum):
    """How to manage a service after deployment."""

    RELOAD = "reload"
    RESTART = "restart"


class Service(StrEnum):
    """OMD site services that may need restart after deployment."""

    APACHE = "apache"
    CRONTAB = "crontab"
    NAGIOS = "nagios"
    CMC = "cmc"
    AUTOMATION_HELPER = "automation-helper"
    UI_JOB_SCHEDULER = "ui-job-scheduler"
    MKEVENTD = "mkeventd"
    AGENT_RECEIVER = "agent-receiver"
    DCD = "dcd"


@dataclass(frozen=True)
class ServiceSpec:
    """Mapping from a source path prefix to affected services."""

    source_prefix: str
    services: tuple[tuple[Service, ServiceAction], ...]
    edition_constraint: frozenset[str] | None


@dataclass(frozen=True)
class BuildResult:
    """Summary of a compiled-asset build and install cycle."""

    targets_built: int
    artifacts_installed: int
    elapsed: float
    skipped_edition: int


@dataclass(frozen=True)
class ConfigDeployResult:
    """Summary of a config/data file deployment cycle."""

    specs_deployed: int
    files_installed: int
    elapsed: float
    locale_compiled: int


@dataclass(frozen=True)
class WheelDeployResult:
    """Summary of a wheel package deployment cycle."""

    wheels_deployed: int
    wheels_skipped: int
    wheels_skipped_edition: int
    wheels_skipped_missing: int
    elapsed: float
    per_package_states: dict[str, DeployerState]
    step_timings: tuple[object, ...] = ()


@dataclass(frozen=True)
class ServiceResult:
    """Summary of service restart/reload operations."""

    services_restarted: int
    services_failed: int
    elapsed: float
    failures: tuple[str, ...]


@dataclass(frozen=True)
class SkipResult:
    """Result of a path-aware skip decision for a single deployer."""

    should_skip: bool
    reason: str
    deployer: str
    paths_checked: tuple[str, ...]
    changed_files: tuple[str, ...]


@dataclass(frozen=True)
class StepResult:
    """Result of a single deployment step."""

    name: str
    success: bool
    message: str | None
    elapsed: float
    start_offset: float = 0.0
    captured_output: tuple[tuple[str, Any], ...] = ()


@dataclass(frozen=True)
class DeployCycleResult:
    """Summary of a single deploy cycle for watch mode display."""

    exit_code: int
    deployed: tuple[str, ...]
    skipped: tuple[str, ...]
    skipped_reasons: dict[str, str]
    services_restarted: int
    all_skipped: bool


@dataclass(frozen=True)
class FrontendConfig:
    """Configuration for the iBazel frontend supervisor."""

    project_path: Path
    repo_root: Path
    port: int = 5173

    startup_timeout: float = 300.0
    """Generous (5 min) to accommodate cold-cache iBazel builds."""

    stderr_buffer_lines: int = 50

    health_check_interval: float = 0.5
    """Seconds between TCP port probes during startup."""


def detect_frontend_project(repo_root: Path) -> Path:
    """Auto-detect the cmk-frontend-vue project path."""
    from cmk.dev_deploy.errors import FrontendError

    default = repo_root / "packages" / "cmk-frontend-vue"
    if default.is_dir() and (default / "vite.config.ts").is_file():
        return default
    raise FrontendError(
        f"Frontend project not found at {default}",
        recovery="Specify project path with --frontend-path",
    )
