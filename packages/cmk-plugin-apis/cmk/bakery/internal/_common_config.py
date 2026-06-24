#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping
from enum import Enum
from pathlib import Path
from typing import NamedTuple, Protocol

from pydantic import BaseModel

from ._artifacts import ABCFileContainer, AgentFileLocator
from ._constants import LogicalPath
from ._types import AgentConfig

_DEFAULT_AGENT = "default"

_UNIX_FILE_PERMISSIONS: Mapping[LogicalPath, int] = {
    LogicalPath.AGENT: 0o640,
    LogicalPath.BIN: 0o755,
    LogicalPath.CONFIG: 0o640,
    LogicalPath.ETC: 0o644,
    LogicalPath.HOME: 0o640,
    LogicalPath.LIB: 0o640,
    LogicalPath.LOCAL: 0o750,
    LogicalPath.PLUGINS: 0o755,
    LogicalPath.ROOT: 0o640,
    LogicalPath.VAR: 0o640,
}


class AgentControllerTargetArch(Enum):
    X86 = "x86"
    ARM = "arm"
    X86_AND_ARM = "x86_and_arm"


class DeploymentMode(Enum):
    ROOT = "root"
    NON_ROOT = "non_root"


class UserCreationStrategy(Enum):
    AUTO = "auto"
    USE_EXISTING = "use_existing"


class UserDeploymentConfig(BaseModel, frozen=True):
    user: str
    uid: int | None = None
    gid: int | None = None
    creation_options: UserCreationStrategy


class DeploymentConfig(NamedTuple):
    mode: DeploymentMode
    user_deployment: UserDeploymentConfig


class SingleDirectoryConfig(BaseModel, frozen=True):
    installation_directory: str
    tmpdir: str | None = None

    def get_installdir(self) -> Path:
        return Path(self.installation_directory, _DEFAULT_AGENT)

    def get_tmpdir(self) -> str | None:
        return self.tmpdir

    def get_keeper(self) -> "UnixSingleDirectoryKeeper":
        return UnixSingleDirectoryKeeper(self.installation_directory, _DEFAULT_AGENT)


class CustomizeAgentPackageConfig(BaseModel, frozen=True):
    deployment_mode: DeploymentConfig | None = None
    directory: SingleDirectoryConfig
    agent_controller_arch: AgentControllerTargetArch = AgentControllerTargetArch.X86


def get_agent_controller_arch(agconf: AgentConfig) -> AgentControllerTargetArch:
    if (customize_agent_package := agconf.get("customize_agent_package")) is None:
        return AgentControllerTargetArch.X86

    return CustomizeAgentPackageConfig.model_validate(customize_agent_package).agent_controller_arch


class AgentPathsConfig(BaseModel, frozen=True):
    bin: str
    config: str
    lib: str
    var: str
    tmp: str | None = None

    def get_installdir(self) -> Path | None:
        return None

    def get_tmpdir(self) -> str | None:
        return self.tmp

    def get_keeper(self) -> "UnixMultipleDirectoryKeeper":
        return UnixMultipleDirectoryKeeper(self)


class DirectoryConfig(Protocol):
    def get_installdir(self) -> Path | None: ...

    def get_tmpdir(self) -> str | None: ...

    def get_keeper(self) -> "UnixAgentPathsKeeper": ...


class UnixAgentPathsKeeper(Protocol):
    def make_package_structure(self, root_path: Path) -> None: ...

    def process_file_container(
        self,
        file_container: ABCFileContainer,
        pkg_root: Path,
        locator: AgentFileLocator,
    ) -> None: ...

    def get_base_folders(self) -> Iterable[Path]: ...

    def get_target_path(self, logical_path: LogicalPath) -> Path: ...


def get_unix_agent_paths_keeper(agconf: AgentConfig) -> UnixAgentPathsKeeper:
    return _parse_directory_config(agconf).get_keeper()


class UnixMultipleDirectoryKeeper:
    def __init__(self, agent_paths: AgentPathsConfig):
        self._agent_paths = agent_paths

    def make_package_structure(self, root_path: Path) -> None:
        def relative_path(abs_path: str) -> Path:
            return Path(abs_path).relative_to("/")

        for dirpath in (
            self._agent_paths.bin,
            self._agent_paths.config,
            self._agent_paths.lib,
            self._agent_paths.var,
        ):
            (root_path / relative_path(dirpath)).mkdir(exist_ok=True, parents=True)

        (root_path / relative_path(self._agent_paths.lib) / "plugins").mkdir(exist_ok=True)
        (root_path / relative_path(self._agent_paths.lib) / "local").mkdir(exist_ok=True)
        (root_path / relative_path(self._agent_paths.var) / "job").mkdir(exist_ok=True)
        (root_path / relative_path(self._agent_paths.var) / "cache").mkdir(exist_ok=True)
        (root_path / relative_path(self._agent_paths.var) / "spool").mkdir(exist_ok=True)
        (root_path / relative_path(self._agent_paths.var) / "log").mkdir(exist_ok=True)

    def process_file_container(
        self, file_container: ABCFileContainer, pkg_root: Path, locator: AgentFileLocator
    ) -> None:
        file_container.place(
            pkg_root,
            locator,
            self.get_target_path(file_container.logical_path).relative_to("/"),
            _UNIX_FILE_PERMISSIONS[file_container.logical_path],
        )

    def get_base_folders(self) -> Iterable[Path]:
        return (
            Path(base_dir)
            for base_dir in (self._agent_paths.lib, self._agent_paths.config, self._agent_paths.var)
        )

    def get_target_path(self, logical_path: LogicalPath) -> Path:
        return {
            LogicalPath.AGENT: Path(self._agent_paths.lib),
            LogicalPath.BIN: Path(self._agent_paths.bin),
            LogicalPath.CONFIG: Path(self._agent_paths.config),
            LogicalPath.ETC: Path("/etc"),
            LogicalPath.HOME: Path("/var/lib/cmk-agent"),
            LogicalPath.LIB: Path(self._agent_paths.lib),
            LogicalPath.LOCAL: Path(self._agent_paths.lib, "local"),
            LogicalPath.PLUGINS: Path(self._agent_paths.lib, "plugins"),
            LogicalPath.ROOT: Path("/"),
            LogicalPath.VAR: Path(self._agent_paths.var),
        }[logical_path]


class UnixSingleDirectoryKeeper:
    PACKAGE_SUBDIR = Path("package")
    RUNTIME_SUBDIR = Path("runtime")
    TARGET_LOCATION = {
        LogicalPath.AGENT: PACKAGE_SUBDIR / "agent",
        LogicalPath.BIN: PACKAGE_SUBDIR / "bin",
        LogicalPath.CONFIG: PACKAGE_SUBDIR / "config",
        LogicalPath.HOME: PACKAGE_SUBDIR,
        LogicalPath.LIB: PACKAGE_SUBDIR,
        LogicalPath.LOCAL: PACKAGE_SUBDIR / "local",
        LogicalPath.PLUGINS: PACKAGE_SUBDIR / "plugins",
        LogicalPath.VAR: RUNTIME_SUBDIR,
    }
    ACCESSIBLE_FOR_OTHERS = 0o755
    FORBIDDEN_FOR_OTHERS = 0o750

    def __init__(self, install_dir: str, package_name: str):
        self._install_dir: Path = Path(install_dir.lstrip("/")) / package_name

    def make_package_structure(self, root_path: Path) -> None:
        default_agent_dir = root_path / self._install_dir
        default_agent_dir.mkdir(mode=self.ACCESSIBLE_FOR_OTHERS, exist_ok=True, parents=True)

        package_dir = default_agent_dir / self.PACKAGE_SUBDIR
        runtime_dir = default_agent_dir / self.RUNTIME_SUBDIR

        package_dir.mkdir(mode=self.ACCESSIBLE_FOR_OTHERS, exist_ok=True, parents=True)
        (package_dir / "bin").mkdir(mode=self.ACCESSIBLE_FOR_OTHERS, exist_ok=True, parents=True)
        (package_dir / "plugins").mkdir(
            mode=self.ACCESSIBLE_FOR_OTHERS, exist_ok=True, parents=True
        )
        (package_dir / "agent").mkdir(mode=self.FORBIDDEN_FOR_OTHERS, exist_ok=True, parents=True)
        (package_dir / "local").mkdir(mode=self.FORBIDDEN_FOR_OTHERS, exist_ok=True, parents=True)
        (package_dir / "config").mkdir(mode=self.FORBIDDEN_FOR_OTHERS, exist_ok=True, parents=True)
        (package_dir / "scripts").mkdir(mode=self.FORBIDDEN_FOR_OTHERS, exist_ok=True, parents=True)

        runtime_dir.mkdir(mode=self.FORBIDDEN_FOR_OTHERS, exist_ok=True, parents=True)
        (runtime_dir / "log").mkdir(mode=self.FORBIDDEN_FOR_OTHERS, exist_ok=True, parents=True)
        (runtime_dir / "spool").mkdir(mode=self.FORBIDDEN_FOR_OTHERS, exist_ok=True, parents=True)
        (runtime_dir / "job").mkdir(mode=self.FORBIDDEN_FOR_OTHERS, exist_ok=True, parents=True)
        (runtime_dir / "controller").mkdir(
            mode=self.FORBIDDEN_FOR_OTHERS, exist_ok=True, parents=True
        )

    def process_file_container(
        self,
        file_container: ABCFileContainer,
        pkg_root: Path,
        locator: AgentFileLocator,
    ) -> None:
        file_container.place(
            pkg_root,
            locator,
            self.get_target_path(file_container.logical_path).relative_to("/"),
            _UNIX_FILE_PERMISSIONS[file_container.logical_path],
        )

    def get_target_path(self, logical_path: LogicalPath) -> Path:
        match logical_path:
            case LogicalPath.ETC:
                return Path("/etc")
            case LogicalPath.ROOT:
                return Path("/")
            case normal_path:
                return "/" / self._install_dir / self.TARGET_LOCATION[normal_path]

    def get_base_folders(self) -> Iterable[Path]:
        return ("/" / self._install_dir,)


_WINDOWS_TARGET_LOCATIONS: Mapping[LogicalPath, str] = {
    LogicalPath.AGENT: "",
    LogicalPath.BIN: "bin",
    LogicalPath.CONFIG: "config",
    LogicalPath.ETC: "",
    LogicalPath.HOME: "",
    LogicalPath.LIB: "",
    LogicalPath.LOCAL: "local",
    LogicalPath.PLUGINS: "plugins",
    LogicalPath.ROOT: "",
    LogicalPath.VAR: "",
}


def process_windows_file_container(
    file_container: ABCFileContainer, pkg_root: Path, locator: AgentFileLocator
) -> None:
    file_container.place(
        pkg_root, locator, Path(_WINDOWS_TARGET_LOCATIONS[file_container.logical_path]), 0
    )


class TargetPathsProvider:
    def __init__(self, agconf: AgentConfig):
        self._directory_config: DirectoryConfig = _parse_directory_config(agconf)

    def get_target_path_mapping(self) -> Mapping[LogicalPath, Path]:
        return {
            logical_path: self._directory_config.get_keeper().get_target_path(logical_path)
            for logical_path in LogicalPath
        }

    def get_installdir(self) -> Path | None:
        return self._directory_config.get_installdir()

    def get_tmpdir(self) -> str | None:
        return self._directory_config.get_tmpdir()


class DeploymentModeProvider:
    """Provide configuration about agent package deployment mode: root or non-root,
    and involved users.
    Some fun facts:
    Non-root mode can only happen in one-directory deployment.
    Multi-directory deployment with non-root user doesn't count as "non-root mode", but as
    "root mode with legacy agent user".
    In non-root deployment mode, the agent controller user is identical to the agent user.
    """

    def __init__(self, agconf: AgentConfig):
        if (customize_package := agconf.get("customize_agent_package")) is not None and (
            deployment_config := CustomizeAgentPackageConfig.model_validate(
                customize_package
            ).deployment_mode
        ) is not None:
            self.deployment_config = deployment_config
            self._legacy_agent_user: str | None = None
            return

        self._legacy_agent_user = agconf.get("agent_user", {}).get("user")
        self.deployment_config = DeploymentConfig(
            mode=DeploymentMode.ROOT,
            user_deployment=UserDeploymentConfig(
                user="cmk-agent", creation_options=UserCreationStrategy.AUTO
            ),
        )

    def get_agent_user(self) -> str:
        """Caution: In "root mode with legacy agent user", this function will return the
        "legacy agent user". It differs from the agent controller user."""
        if self._legacy_agent_user is not None:
            return self._legacy_agent_user

        return (
            "root"
            if self.deployment_config.mode is DeploymentMode.ROOT
            else self.deployment_config.user_deployment.user
        )

    def get_agent_user_gid(self) -> int | None:
        return (
            self.deployment_config.user_deployment.gid
            if self.deployment_config.mode is DeploymentMode.NON_ROOT
            else None
        )

    def get_agent_controller_user(self) -> str:
        """Caution: In "root mode with legacy agent user", the agent controller user
        is always "cmk-agent", and differs from the agent user."""
        return self.deployment_config.user_deployment.user

    def get_agent_controller_gid(self) -> int | None:
        """GID customized for the agent controller user, if any. In non-root mode, this
        is identical to the agent user's GID."""
        return self.deployment_config.user_deployment.gid


def _parse_directory_config(agconf: AgentConfig) -> DirectoryConfig:
    if (customize_agent_package := agconf.get("customize_agent_package")) is None:
        return AgentPathsConfig.model_validate(agconf["agent_paths"])
    return CustomizeAgentPackageConfig.model_validate(customize_agent_package).directory
