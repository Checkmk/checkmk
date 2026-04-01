# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Custom exception hierarchy for cmk-dev-deploy."""

from __future__ import annotations


class DeployError(Exception):
    """Base exception for all cmk-dev-deploy errors."""

    def __init__(self, message: str, recovery: str | None = None) -> None:
        super().__init__(message)
        self.message: str = message
        self.recovery: str | None = recovery

    def __str__(self) -> str:
        if self.recovery:
            return f"{self.message}\n\n{self.recovery}"
        return self.message


class RepoNotFoundError(DeployError):
    """Raised when the current directory is not inside a git repository."""


class SiteNotFoundError(DeployError):
    """Raised when no OMD site can be detected via the fallback chain."""


class SiteError(DeployError):
    """Raised when a site exists but has structural issues."""


class ChangeDetectionError(DeployError):
    """Raised when git-based change detection fails."""


class BazelBuildError(DeployError):
    """Raised when bazel build, patchelf, or setcap fails."""


class ConfigDeployError(DeployError):
    """Raised when config/data file deployment fails."""


class WheelDeployError(DeployError):
    """Raised when wheel build or extraction fails."""


class FrontendError(DeployError):
    """Raised when the frontend dev server (Vite) fails to start or stop."""


class IBazelError(DeployError):
    """Raised when iBazel binary management fails."""


class ManifestBuildError(DeployError):
    """Raised when manifest generation or rebuild fails."""


class OverlayError(DeployError):
    """Raised when OverlayFS mount or unmount operations fail."""
