# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Git queries shared by change detection, deploy state, and the watch loop."""

import subprocess
from pathlib import Path

from cmk.dev_deploy.core.timeouts import GIT_QUICK


def query_untracked_files(repo_root: Path) -> list[str]:
    """Return untracked, non-ignored files as repo-relative paths.

    Files that have never been ``git add``-ed are invisible to every form
    of ``git diff``, so every consumer of a diff must union them in
    explicitly.  Without that, a whole new feature directory only ever
    reaches the site as a side effect of some unrelated tracked file
    changing in the same package -- Bazel globs the source tree and builds
    the new files, but change detection never asks it to.

    ``--exclude-standard`` honours ``.gitignore``, so build output and
    editor scratch files stay out.

    Returns an empty list on subprocess error, which degrades to the
    tracked-only behaviour rather than aborting the deploy.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(repo_root),
            timeout=GIT_QUICK,
        )
    except subprocess.TimeoutExpired, OSError:
        return []
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.strip().splitlines() if line]
