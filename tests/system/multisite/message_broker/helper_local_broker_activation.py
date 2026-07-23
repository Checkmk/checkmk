#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""In-site helper for the message-broker composition tests (SUP-29435).

Reproduces the central activation steps that ``ActivateChangesManager.start()`` runs
locally, using the empty definitions a remote site computes from its own (local-only)
site list. On a remote site the ``is_distributed_setup_remote_site`` guard inside
``_activate_central_steps`` must short-circuit, leaving the central site's broker user
untouched (otherwise the recompute would run ``rabbitmqctl delete_user``).
"""

from collections import defaultdict

from cmk.ccc.version import edition
from cmk.gui import main_modules
from cmk.gui.watolib.activate_changes import (
    _activate_central_steps,
    activation_features_registry,
)
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.wsgi.app import gui_context
from cmk.livestatus_client import SiteConfigurations
from cmk.messaging import rabbitmq
from cmk.utils import paths

if __name__ == "__main__":
    main_modules.register(edition(paths.omd_root))

    with gui_context():
        _activate_central_steps(
            activation_features_registry[str(edition(paths.omd_root))],
            SiteConfigurations({}),
            defaultdict(rabbitmq.Definitions),
            [],
            [],
            folder_tree(),
        )
