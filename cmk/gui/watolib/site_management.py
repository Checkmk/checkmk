#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Set

from livestatus import (
    BrokerConnection,
    BrokerConnections,
    ConnectionId,
    SiteConfiguration,
    SiteConfigurations,
)

from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.user import UserId
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.watolib.activate_changes import clear_site_replication_status
from cmk.gui.watolib.automations import do_site_login, remote_automation_config_from_site_config
from cmk.gui.watolib.broker_certificates import trigger_remote_certs_creation
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.config_domain_name import ABCConfigDomain
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.watolib.sites import site_management_registry
from cmk.utils.licensing.license_distribution_registry import distribute_license_to_remotes

DEFAULT_MESSAGE_BROKER_PORT = 5672


class SiteDoesNotExistException(Exception): ...


class LoginException(Exception): ...


class SitesApiMgr:
    def __init__(self) -> None:
        self.site_mgmt = site_management_registry["site_management"]
        self.all_sites = self.site_mgmt.load_sites()

    def get_all_sites(self) -> SiteConfigurations:
        return self.all_sites

    def get_a_site(self, site_id: SiteId) -> SiteConfiguration:
        if not (existing_site := self.all_sites.get(site_id)):
            raise SiteDoesNotExistException
        return existing_site

    def delete_a_site(self, site_id: SiteId, *, pprint_value: bool, use_git: bool) -> None:
        if self.all_sites.get(site_id):
            self.site_mgmt.delete_site(site_id, pprint_value=pprint_value, use_git=use_git)
        raise SiteDoesNotExistException

    def login_to_site(
        self, site_id: SiteId, username: str, password: str, *, pprint_value: bool, debug: bool
    ) -> None:
        site = self.get_a_site(site_id)
        if "secret" not in site:  # when login is not already done
            try:
                site["secret"] = do_site_login(site, UserId(username), password, debug=debug)
            except Exception as exc:
                raise LoginException(str(exc))

            self.site_mgmt.save_sites(self.all_sites, activate=True, pprint_value=pprint_value)
            trigger_remote_certs_creation(site_id, site, force=False, debug=debug)
            distribute_license_to_remotes(
                logger,
                remote_automation_configs=[remote_automation_config_from_site_config(site)],
            )

    def logout_of_site(self, site_id: SiteId, *, pprint_value: bool) -> None:
        site = self.get_a_site(site_id)
        if "secret" in site:
            del site["secret"]
            self.site_mgmt.save_sites(self.all_sites, activate=True, pprint_value=pprint_value)

    def validate_and_save_site(
        self, site_id: SiteId, site_config: SiteConfiguration, *, pprint_value: bool
    ) -> None:
        self.site_mgmt.validate_configuration(site_id, site_config, self.all_sites)
        self.all_sites[site_id] = site_config
        self.site_mgmt.save_sites(self.all_sites, activate=True, pprint_value=pprint_value)

    def get_connected_sites_to_update(
        self,
        *,
        new_or_deleted_connection: bool,
        modified_site: SiteId,
        current_site_config: SiteConfiguration,
        old_site_config: SiteConfiguration | None,
        site_configs: SiteConfigurations,
    ) -> set[SiteId]:
        return self.site_mgmt.get_connected_sites_to_update(
            new_or_deleted_connection=new_or_deleted_connection,
            modified_site=modified_site,
            current_config=current_site_config,
            old_config=old_site_config,
            site_configs=site_configs,
        )

    def get_broker_connections(self) -> BrokerConnections:
        return self.site_mgmt.get_broker_connections()

    def validate_and_save_broker_connection(
        self,
        connection_id: ConnectionId,
        broker_connection: BrokerConnection,
        *,
        is_new: bool,
        pprint_value: bool,
    ) -> tuple[SiteId, SiteId]:
        return self.site_mgmt.validate_and_save_broker_connection(
            connection_id,
            broker_connection,
            is_new=is_new,
            pprint_value=pprint_value,
        )

    def delete_broker_connection(
        self, connection_id: ConnectionId, pprint_value: bool
    ) -> tuple[SiteId, SiteId]:
        return self.site_mgmt.delete_broker_connection(connection_id, pprint_value)


def add_changes_after_editing_broker_connection(
    *,
    connection_id: str,
    is_new_broker_connection: bool,
    sites: list[SiteId],
    use_git: bool,
) -> str:
    change_message = (
        _("Created new peer-to-peer broker connection ID %s") % connection_id
        if is_new_broker_connection
        else _("Modified peer-to-peer broker connection ID %s") % connection_id
    )

    add_change(
        action_name="edit-sites",
        text=change_message,
        user_id=user.id,
        need_sync=True,
        need_restart=True,
        sites=[omd_site()] + sites,
        domains=[ConfigDomainGUI()],
        use_git=use_git,
    )

    return change_message


def add_changes_after_editing_site_connection(
    *,
    site_id: SiteId,
    is_new_connection: bool,
    replication_enabled: bool,
    is_local_site: bool,
    connected_sites: Set[SiteId],
    use_git: bool,
) -> str:
    change_message = (
        _("Created new connection to site %s") % site_id
        if is_new_connection
        else _("Modified site connection %s") % site_id
    )

    sites_to_update = connected_sites | {site_id}
    add_change(
        action_name="edit-sites",
        text=change_message,
        user_id=user.id,
        sites=list(sites_to_update),
        # This was ABCConfigDomain.enabled_domains() before. Since e.g. apache config domain takes
        # significant more time to restart than the other domains, we now try to be more specific
        # and mention potentially affected domains instead. The idea here is to first hard code
        # the list of config domains produced by enabled_domains and then reduce it step by step.
        #
        # One the list is minimized, we can turn it into an explicit positive list.
        #
        # If you extend this, please also check the other "add_change" calls triggered by the site
        # management.
        domains=[
            d
            for d in ABCConfigDomain.enabled_domains()
            if d.ident()
            not in {
                "apache",
                "ca-certificates",
                "check_mk",
                "diskspace",
                "ec",
                "metric_backend",
                "omd",
                "otel_collector",
                "rrdcached",
                # Can we remove more here? Investigate further to minimize the domains:
                # "liveproxyd",
                # "multisite",
                # "piggyback_hub",
                # "dcd",
                # "mknotifyd",
            }
        ],
        use_git=use_git,
    )

    # In case a site is not being replicated anymore, confirm all changes for this site!
    if not replication_enabled and not is_local_site:
        clear_site_replication_status(site_id)

    if site_id != omd_site():
        # On central site issue a change only affecting the GUI
        add_change(
            action_name="edit-sites",
            text=change_message,
            user_id=user.id,
            sites=[omd_site()],
            domains=[ConfigDomainGUI()],
            use_git=use_git,
        )

    return change_message
