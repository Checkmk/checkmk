#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import uuid
from datetime import datetime
from typing import Any
from uuid import uuid4, uuid5

from livestatus import SiteConfiguration, SiteConfigurations

from cmk.ccc import store
from cmk.ccc.site import omd_site, url_prefix

from cmk.utils.encryption import raw_certificates_from_file
from cmk.utils.log import VERBOSE
from cmk.utils.notify_types import (
    EventRule,
    MailPluginModel,
    NotificationParameterGeneralInfos,
    NotificationParameterID,
    NotificationParameterItem,
    NotificationParameterSpecs,
    NotificationPluginNameStr,
    NotificationRuleID,
    NotifyPlugin,
)
from cmk.utils.paths import configuration_lockfile, site_cert_file
from cmk.utils.tags import sample_tag_config, TagConfig

from cmk.gui.groups import GroupSpec
from cmk.gui.log import logger
from cmk.gui.userdb import create_cmk_automation_user
from cmk.gui.watolib.config_domain_name import (
    sample_config_generator_registry,
    SampleConfigGenerator,
)
from cmk.gui.watolib.config_domains import ConfigDomainCACertificates
from cmk.gui.watolib.global_settings import save_global_settings
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.notifications import (
    NotificationParameterConfigFile,
    NotificationRuleConfigFile,
)
from cmk.gui.watolib.rulesets import FolderRulesets
from cmk.gui.watolib.sites import site_management_registry
from cmk.gui.watolib.tags import TagConfigFile
from cmk.gui.watolib.utils import multisite_dir, wato_root_dir

from ._abc import SampleConfigGeneratorABCGroups
from ._constants import SHIPPED_RULES, USE_NEW_DESCRIPTIONS_FOR_SETTING


# TODO: Must only be unlocked when it was not locked before. We should find a more
# robust way for doing something like this. If it is locked before, it can now happen
# that this call unlocks the wider locking when calling this funktion in a wrong way.
def init_wato_datastructures(with_wato_lock: bool = False) -> None:
    if (
        os.path.exists(ConfigDomainCACertificates.trusted_cas_file)
        and not _need_to_create_sample_config()
    ):
        logger.log(VERBOSE, "No need to create the sample config")
        return

    def init():
        if not os.path.exists(ConfigDomainCACertificates.trusted_cas_file):
            ConfigDomainCACertificates().activate()
        _create_sample_config()

    if with_wato_lock:
        with store.lock_checkmk_configuration(configuration_lockfile):
            init()
    else:
        init()


def _need_to_create_sample_config() -> bool:
    if (
        (multisite_dir() / "tags.mk").exists()
        or (wato_root_dir() / "rules.mk").exists()
        or (wato_root_dir() / "groups.mk").exists()
        or (wato_root_dir() / "notifications.mk").exists()
        or (wato_root_dir() / "global.mk").exists()
    ):
        return False
    return True


def _create_sample_config() -> None:
    """Create a very basic sample configuration

    But only if none of the files that we will create already exists. That is
    e.g. the case after an update from an older version where no sample config
    had been created.
    """
    if not _need_to_create_sample_config():
        return

    logger.debug("Start creating the sample config")
    for generator in sample_config_generator_registry.get_generators():
        try:
            logger.debug("Starting [%s]", generator.ident())
            generator.generate()
            logger.debug("Finished [%s]", generator.ident())
        except Exception:
            logger.exception("Exception in sample config generator [%s]", generator.ident())

    logger.log(VERBOSE, "Finished creating the sample config")


def new_notification_rule_id() -> NotificationRuleID:
    return NotificationRuleID(str(uuid4()))


def new_notification_parameter_id() -> NotificationParameterID:
    return NotificationParameterID(str(uuid4()))


def _default_notification_parameter_id() -> NotificationParameterID:
    return NotificationParameterID(
        str(uuid5(uuid.UUID("f5b3b3b4-4b3b-4b3b-4b3b-4b3b4b3b4b3b"), "seed"))
    )


def _create_default_notify_plugin() -> NotifyPlugin:
    method: NotificationPluginNameStr = "mail"
    params_id: NotificationParameterID = _default_notification_parameter_id()
    default_param: NotificationParameterSpecs = {
        method: {
            params_id: NotificationParameterItem(
                general=NotificationParameterGeneralInfos(
                    description="Default",
                    comment="",
                    docu_url="",
                ),
                parameter_properties=MailPluginModel(),
            )
        }
    }
    NotificationParameterConfigFile().save(default_param, pprint_value=True)
    return method, params_id


def get_default_notification_rule() -> EventRule:
    return EventRule(
        rule_id=new_notification_rule_id(),
        allow_disable=True,
        contact_all=False,
        contact_all_with_email=False,
        contact_object=True,
        description="HTML email to all contacts about service/host status changes",
        disabled=False,
        notify_plugin=("mail", _default_notification_parameter_id()),
        match_host_event=["?d", "?r"],
        match_service_event=["?c", "?w", "?r"],
    )


class SampleConfigGeneratorGroups(SampleConfigGeneratorABCGroups):
    def _all_group_spec(self) -> GroupSpec:
        return {
            "alias": "Everything",
        }


class ConfigGeneratorBasicWATOConfig(SampleConfigGenerator):
    @classmethod
    def ident(cls) -> str:
        return "basic_wato_config"

    @classmethod
    def sort_index(cls) -> int:
        return 11

    def generate(self) -> None:
        save_global_settings(self._initial_global_settings(), skip_cse_edition_check=True)

        self._initialize_tag_config()

        root_folder = folder_tree().root_folder()
        rulesets = FolderRulesets.load_folder_rulesets(root_folder)
        rulesets.replace_folder_config(root_folder, SHIPPED_RULES)
        rulesets.save_folder(pprint_value=False, debug=False)

        _create_default_notify_plugin()
        notification_rules = [get_default_notification_rule()]
        NotificationRuleConfigFile().save(notification_rules, pprint_value=True)

    def _initial_global_settings(self) -> dict[str, Any]:
        settings = {
            **USE_NEW_DESCRIPTIONS_FOR_SETTING,
            "trusted_certificate_authorities": {
                "use_system_wide_cas": True,
                # Add the CA of the site to the trusted CAs. This has the benefit that remote sites
                # automatically trust central sites in distributed setups where the config is replicated.
                "trusted_cas": (
                    (site_cas := raw_certificates_from_file(site_cert_file))
                    and [site_cas[-1]]
                    or []
                ),
            },
        }

        return settings

    def _initialize_tag_config(self) -> None:
        tag_config = TagConfig.from_config(sample_tag_config())
        TagConfigFile().save(tag_config.get_dict_format(), pprint_value=True)


class ConfigGeneratorLocalSiteConnection(SampleConfigGenerator):
    @classmethod
    def ident(cls) -> str:
        return "create_local_site_connection"

    @classmethod
    def sort_index(cls) -> int:
        return 20

    def generate(self) -> None:
        site_mgmt = site_management_registry["site_management"]
        site_mgmt.save_sites(
            self._default_single_site_configuration(),
            activate=True,
            pprint_value=True,
        )

    def _default_single_site_configuration(self) -> SiteConfigurations:
        return SiteConfigurations(
            {
                omd_site(): SiteConfiguration(
                    {
                        "id": omd_site(),
                        "alias": f"Local site {omd_site()}",
                        "socket": ("local", None),
                        "disable_wato": True,
                        "disabled": False,
                        "insecure": False,
                        "url_prefix": url_prefix(),
                        "multisiteurl": "",
                        "persist": False,
                        "replicate_ec": False,
                        "replicate_mkps": False,
                        "replication": None,
                        "timeout": 5,
                        "user_login": True,
                        "proxy": None,
                        "user_sync": "all",
                        "status_host": None,
                        "message_broker_port": 5672,
                    }
                )
            }
        )


class ConfigGeneratorAcknowledgeInitialWerks(SampleConfigGenerator):
    """This is not really the correct place for such kind of action, but the best place we could
    find to execute it only for new created sites."""

    @classmethod
    def ident(cls) -> str:
        return "acknowledge_initial_werks"

    @classmethod
    def sort_index(cls) -> int:
        return 40

    def generate(self) -> None:
        # Local import has been added to quick-fix an import cycle between cmk.gui.werks and watolib
        from cmk.gui import werks

        werks.acknowledge_all_werks(check_permission=False)


class ConfigGeneratorRegistrationUser(SampleConfigGenerator):
    """Create the default Checkmk "agent registation" user"""

    name = "agent_registration"
    role = "agent_registration"
    alias = "Check_MK Agent Registration - used for agent registration"

    @classmethod
    def ident(cls) -> str:
        return "create_registration_automation_user"

    @classmethod
    def sort_index(cls) -> int:
        return 60

    def generate(self) -> None:
        create_cmk_automation_user(
            datetime.now(), name=self.name, role=self.role, alias=self.alias, store_secret=True
        )
