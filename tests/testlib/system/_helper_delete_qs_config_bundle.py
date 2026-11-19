#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""In-site helper: delete a configuration bundle and the objects it owns.

Takes the bundle id as a positional argument.

Exit codes
----------
0  Bundle was found and deleted successfully.
1  Bundle was not found; nothing to delete.
2  Unexpected error during deletion (details on stderr).
3  Wrong number of arguments.
"""

from __future__ import annotations

import sys
import traceback
from collections.abc import Callable


def delete_bundle(
    bundle_id: str,
    *,
    bundle_exists: Callable[[str], bool],
    delete: Callable[[str], None],
) -> int:
    """Core deletion logic, returns an exit code.

    0 — deleted, 1 — absent, 2 — unexpected error.
    """
    if not bundle_exists(bundle_id):
        return 1
    try:
        delete(bundle_id)
    except Exception:
        print(f"Failed to delete bundle {bundle_id!r}", file=sys.stderr)  # noqa: T201
        traceback.print_exc()
        return 2
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <bundle_id>", file=sys.stderr)  # noqa: T201
        sys.exit(3)

    from cmk.ccc.site import omd_site
    from cmk.ccc.version import edition
    from cmk.gui import main_modules  # type: ignore[attr-defined]
    from cmk.gui.config import active_config
    from cmk.gui.logged_in import user
    from cmk.gui.permissions import all_permissions
    from cmk.gui.session_context import SuperUserContext
    from cmk.gui.user_sites import activation_sites
    from cmk.gui.utils.roles import UserPermissions
    from cmk.gui.watolib.configuration_bundle_store import BundleId, ConfigBundleStore
    from cmk.gui.watolib.configuration_bundles import delete_config_bundle
    from cmk.gui.watolib.hosts_and_folders import make_folder_tree
    from cmk.gui.watolib.pending_changes import PendingChanges, PendingChangesStore
    from cmk.gui.wsgi.app import gui_context  # type: ignore[import-not-found]
    from cmk.utils import paths

    bundle_id = sys.argv[1]
    main_modules.register(edition(paths.omd_root), debug=False)

    with gui_context(), SuperUserContext():
        store = ConfigBundleStore().load_for_reading()

        def _delete(bid: str) -> None:
            delete_config_bundle(
                make_folder_tree(active_config),
                BundleId(bid),
                acting_user=user,
                user_permissions=UserPermissions.from_config(active_config, all_permissions()),
                pprint_value=active_config.wato_pprint_config,
                debug=active_config.debug,
                pending_changes=PendingChanges(
                    activation_sites=activation_sites(active_config.sites),
                    local_site=omd_site(),
                    acting_user=user.id,
                    store=PendingChangesStore(),
                    hooks=(),
                ),
            )

        sys.exit(
            delete_bundle(
                bundle_id, bundle_exists=lambda bid: BundleId(bid) in store, delete=_delete
            )
        )
