# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Centralized timeout constants for subprocess invocations.

All timeout values (in seconds) for external commands are collected here
so they can be reviewed and adjusted in one place.
"""

# Git commands (rev-parse, cat-file, diff --name-only, ls-files)
GIT_QUICK: int = 5

# Git diff with path filtering (can be slower on large repos)
GIT_DIFF_PATHS: int = 10

# Bazel info (normal operations)
BAZEL_INFO: int = 30

# Bazel info for diagnostic/preflight checks (kept short so a cold/hung
# Bazel server does not block the tool or the crash reporter)
BAZEL_INFO_QUICK: int = 3

# Full bazel build (C++, Rust, Vue — can be slow from clean)
BAZEL_BUILD: int = 600

# Wheel-specific bazel build (typically faster than full builds)
BAZEL_WHEEL_BUILD: int = 300

# bazel cquery for artifact location
BAZEL_CQUERY: int = 60

# bazel cquery for wheel artifact (typically faster)
BAZEL_CQUERY_QUICK: int = 30

# make print-VERSION
VERSION_CMD: int = 10

# OMD commands (omd stop/start) and overlay mount/umount operations
OVERLAY_CMD: int = 60

# Service reload (quick operation)
SERVICE_RELOAD: int = 10

# Service restart (may take longer)
SERVICE_RESTART: int = 30

# msgfmt locale compilation
MSGFMT: int = 30
