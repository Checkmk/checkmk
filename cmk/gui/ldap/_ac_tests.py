#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from typing import override

import cmk.gui.ldap.ldap_connector as ldap
from cmk.ccc.site import SiteId
from cmk.gui.config import active_config, Config
from cmk.gui.i18n import _
from cmk.gui.userdb import active_connections
from cmk.gui.watolib.analyze_configuration import (
    ACResultState,
    ACSingleResult,
    ACTest,
    ACTestCategories,
)


class ACTestLDAPSecured(ACTest):
    @override
    def category(self) -> str:
        return ACTestCategories.security

    @override
    def title(self) -> str:
        return _("Secure LDAP")

    @override
    def help(self) -> str:
        return _(
            "When using the regular LDAP protocol all data transfered between the Checkmk "
            "and LDAP servers is sent over the network in plain text (unencrypted). This also "
            "includes the passwords users enter to authenticate with the LDAP Server. It is "
            "highly recommended to enable SSL for securing the transported data."
        )

    # TODO: Only test master site?
    @override
    def is_relevant(self) -> bool:
        return bool(
            [
                c
                for _cid, c in active_connections(active_config.user_connections)
                if c.type() == "ldap"
            ]
        )

    @override
    def execute(self, site_id: SiteId, config: Config) -> Iterator[ACSingleResult]:
        for connection_id, connection in active_connections(config.user_connections):
            if connection.type() != "ldap":
                continue

            assert isinstance(connection, ldap.LDAPUserConnector)

            if connection.use_ssl():
                yield ACSingleResult(
                    state=ACResultState.OK,
                    text=_("%s: Uses SSL") % connection_id,
                    site_id=site_id,
                )

            else:
                yield ACSingleResult(
                    state=ACResultState.WARN,
                    text=_("%s: Not using SSL. Consider enabling it in the connection settings.")
                    % connection_id,
                    site_id=site_id,
                )
