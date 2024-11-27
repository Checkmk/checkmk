#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from collections.abc import Callable, Sequence
from datetime import timedelta

from cmk.ccc import version
from cmk.ccc.version import edition_supports_nagvis

from cmk.utils import paths

from cmk.gui import hooks
from cmk.gui.background_job import BackgroundJobRegistry
from cmk.gui.cron import CronJob, CronJobRegistry
from cmk.gui.valuespec import AutocompleterRegistry
from cmk.gui.watolib.search import MatchItemGeneratorRegistry

from . import (
    _host_attributes,
    _sync_remote_sites,
    activate_changes,
    auth_php,
    autodiscovery,
    automatic_host_removal,
    automation_commands,
    builtin_attributes,
    config_domains,
    config_variable_groups,
    groups,
    host_attributes,
    rulespec_groups,
)
from .activate_changes import (
    ActivateChangesSchedulerBackgroundJob,
    ActivationCleanupBackgroundJob,
    AutomationGetConfigSyncState,
    AutomationReceiveConfigSync,
    execute_activation_cleanup_background_job,
)
from .agent_registration import AutomationRemoveTLSRegistration
from .analyze_configuration import AutomationCheckAnalyzeConfig
from .automation_commands import AutomationCommandRegistry
from .automations import (
    AutomationCheckmkAutomationGetStatus,
    AutomationCheckmkAutomationStart,
    CheckmkAutomationBackgroundJob,
)
from .broker_certificates import AutomationStoreBrokerCertificates
from .bulk_discovery import BulkDiscoveryBackgroundJob
from .config_domain_name import (
    ConfigDomainRegistry,
    ConfigVariableGroupRegistry,
    SampleConfigGeneratorRegistry,
)
from .config_hostname import config_hostname_autocompleter
from .config_sync import ReplicationPathRegistry
from .groups import ContactGroupUsageFinderRegistry as ContactGroupUsageFinderRegistry
from .host_attributes import ABCHostAttribute, HostAttributeRegistry, HostAttributeTopicRegistry
from .host_label_sync import AutomationDiscoveredHostLabelSync, DiscoveredHostLabelSyncJob
from .host_rename import (
    AutomationRenameHostsUUIDLink,
    RenameHostBackgroundJob,
    RenameHostsBackgroundJob,
)
from .hosts_and_folders import (
    collect_all_hosts,
    find_usages_of_contact_group_in_hosts_and_folders,
    FolderValidators,
    FolderValidatorsRegistry,
    MatchItemGeneratorHosts,
    rebuild_folder_lookup_cache,
)
from .network_scan import AutomationNetworkScan, execute_network_scan_job
from .notifications import (
    find_timeperiod_usage_in_notification_rules,
    find_usages_of_contact_group_in_notification_rules,
)
from .parent_scan import ParentScanBackgroundJob
from .rulesets import (
    find_timeperiod_usage_in_host_and_service_rules,
    find_timeperiod_usage_in_time_specific_parameters,
)
from .rulespecs import (
    MatchItemGeneratorRules,
    rulespec_registry,
    RulespecGroupEnforcedServices,
    RulespecGroupRegistry,
)
from .sample_config import (
    ConfigGeneratorAcknowledgeInitialWerks,
    ConfigGeneratorAutomationUser,
    ConfigGeneratorBasicWATOConfig,
    ConfigGeneratorRegistrationUser,
)
from .search import launch_requests_processing_background, SearchIndexBackgroundJob
from .timeperiods import TimeperiodUsageFinderRegistry
from .user_profile import handle_ldap_sync_finished, PushUserProfilesToSite


def register(
    edition: version.Edition,
    rulespec_group_registry: RulespecGroupRegistry,
    automation_command_registry: AutomationCommandRegistry,
    job_registry: BackgroundJobRegistry,
    sample_config_generator_registry: SampleConfigGeneratorRegistry,
    config_domain_registry: ConfigDomainRegistry,
    host_attribute_topic_registry: HostAttributeTopicRegistry,
    host_attribute_registry: HostAttributeRegistry,
    contact_group_usage_finder_registry_: ContactGroupUsageFinderRegistry,
    timeperiod_usage_finder_registry: TimeperiodUsageFinderRegistry,
    config_variable_group_registry: ConfigVariableGroupRegistry,
    autocompleter_registry: AutocompleterRegistry,
    match_item_generator_registry: MatchItemGeneratorRegistry,
    replication_path_registry: ReplicationPathRegistry,
    folder_validators_registry: FolderValidatorsRegistry,
    cron_job_registry: CronJobRegistry,
) -> None:
    _register_automation_commands(automation_command_registry)
    _register_gui_background_jobs(job_registry)
    if edition_supports_nagvis(version.edition(paths.omd_root)):
        _register_nagvis_hooks()
    _register_config_domains(config_domain_registry)
    host_attributes.register(host_attribute_topic_registry)
    activate_changes.register(replication_path_registry)
    _host_attributes.register()
    _register_host_attribute(host_attribute_registry)
    _register_cronjobs(cron_job_registry)
    folder_validators_registry.register(
        FolderValidators(
            str(edition),
            validate_edit_host=lambda s, n, a: None,
            validate_create_hosts=lambda e, s: None,
            validate_create_subfolder=lambda f, a: None,
            validate_edit_folder=lambda f, a: None,
            validate_move_hosts=lambda f, n, t: None,
            validate_move_subfolder_to=lambda f, t: None,
        )
    )
    _sync_remote_sites.register(automation_command_registry, job_registry, cron_job_registry)
    rulespec_groups.register(rulespec_group_registry)
    rulespec_group_registry.register(RulespecGroupEnforcedServices)
    automation_command_registry.register(PushUserProfilesToSite)
    automation_command_registry.register(AutomationStoreBrokerCertificates)
    automation_command_registry.register(AutomationGetConfigSyncState)
    automation_command_registry.register(AutomationReceiveConfigSync)
    automation_command_registry.register(AutomationRemoveTLSRegistration)
    automation_command_registry.register(AutomationCheckAnalyzeConfig)
    automation_command_registry.register(AutomationDiscoveredHostLabelSync)
    automation_command_registry.register(AutomationNetworkScan)
    automation_command_registry.register(AutomationCheckmkAutomationStart)
    automation_command_registry.register(AutomationCheckmkAutomationGetStatus)
    sample_config_generator_registry.register(ConfigGeneratorBasicWATOConfig)
    sample_config_generator_registry.register(ConfigGeneratorAcknowledgeInitialWerks)
    sample_config_generator_registry.register(ConfigGeneratorAutomationUser)
    sample_config_generator_registry.register(ConfigGeneratorRegistrationUser)
    contact_group_usage_finder_registry_.register(find_usages_of_contact_group_in_hosts_and_folders)
    contact_group_usage_finder_registry_.register(
        find_usages_of_contact_group_in_notification_rules
    )
    timeperiod_usage_finder_registry.register(find_timeperiod_usage_in_host_and_service_rules)
    timeperiod_usage_finder_registry.register(find_timeperiod_usage_in_time_specific_parameters)
    timeperiod_usage_finder_registry.register(find_timeperiod_usage_in_notification_rules)
    config_variable_groups.register(config_variable_group_registry)
    autocompleter_registry.register_autocompleter("config_hostname", config_hostname_autocompleter)
    hooks.register_builtin("request-start", launch_requests_processing_background)
    hooks.register_builtin("validate-host", builtin_attributes.validate_host_parents)
    hooks.register_builtin("ldap-sync-finished", handle_ldap_sync_finished)
    match_item_generator_registry.register(
        MatchItemGeneratorRules(
            "rules",
            rulespec_group_registry,
            rulespec_registry,
        )
    )
    match_item_generator_registry.register(
        MatchItemGeneratorHosts(
            "hosts",
            collect_all_hosts,
        )
    )


def _register_automation_commands(automation_command_registry: AutomationCommandRegistry) -> None:
    clss: Sequence[type[automation_commands.AutomationCommand]] = (
        automation_commands.AutomationPing,
        automatic_host_removal.AutomationHostsForAutoRemoval,
        AutomationRenameHostsUUIDLink,
    )
    for cls in clss:
        automation_command_registry.register(cls)


def _register_gui_background_jobs(job_registry: BackgroundJobRegistry) -> None:
    job_registry.register(config_domains.OMDConfigChangeBackgroundJob)
    job_registry.register(automatic_host_removal.HostRemovalBackgroundJob)
    job_registry.register(autodiscovery.AutodiscoveryBackgroundJob)
    job_registry.register(BulkDiscoveryBackgroundJob)
    job_registry.register(SearchIndexBackgroundJob)
    job_registry.register(ActivationCleanupBackgroundJob)
    job_registry.register(ActivateChangesSchedulerBackgroundJob)
    job_registry.register(ParentScanBackgroundJob)
    job_registry.register(RenameHostsBackgroundJob)
    job_registry.register(RenameHostBackgroundJob)
    job_registry.register(DiscoveredHostLabelSyncJob)
    job_registry.register(CheckmkAutomationBackgroundJob)


def _register_config_domains(config_domain_registry: ConfigDomainRegistry) -> None:
    config_domain_registry.register(config_domains.ConfigDomainCore())
    config_domain_registry.register(config_domains.ConfigDomainGUI())
    config_domain_registry.register(config_domains.ConfigDomainLiveproxy())
    config_domain_registry.register(config_domains.ConfigDomainCACertificates())
    config_domain_registry.register(config_domains.ConfigDomainOMD())


def _register_host_attribute(host_attribute_registry: HostAttributeRegistry) -> None:
    clss: Sequence[type[ABCHostAttribute]] = [
        builtin_attributes.HostAttributeAlias,
        builtin_attributes.HostAttributeIPv4Address,
        builtin_attributes.HostAttributeIPv6Address,
        builtin_attributes.HostAttributeAdditionalIPv4Addresses,
        builtin_attributes.HostAttributeAdditionalIPv6Addresses,
        builtin_attributes.HostAttributeSNMPCommunity,
        builtin_attributes.HostAttributeParents,
        builtin_attributes.HostAttributeNetworkScan,
        builtin_attributes.HostAttributeNetworkScanResult,
        builtin_attributes.HostAttributeManagementAddress,
        builtin_attributes.HostAttributeManagementProtocol,
        builtin_attributes.HostAttributeManagementSNMPCommunity,
        builtin_attributes.HostAttributeManagementIPMICredentials,
        builtin_attributes.HostAttributeSite,
        builtin_attributes.HostAttributeLockedBy,
        builtin_attributes.HostAttributeLockedAttributes,
        builtin_attributes.HostAttributeMetaData,
        builtin_attributes.HostAttributeDiscoveryFailed,
        builtin_attributes.HostAttributeWaitingForDiscovery,
        builtin_attributes.HostAttributeLabels,
        groups.HostAttributeContactGroups,
    ]
    for cls in clss:
        host_attribute_registry.register(cls)


def _register_nagvis_hooks() -> None:
    # TODO: Should we not execute this hook also when folders are modified?
    args: Sequence[tuple[str, Callable]] = (
        ("userdb-job", auth_php._on_userdb_job),
        ("users-saved", lambda users: auth_php._create_auth_file("users-saved", users)),
        ("roles-saved", lambda x: auth_php._create_auth_file("roles-saved")),
        ("contactgroups-saved", lambda x: auth_php._create_auth_file("contactgroups-saved")),
        ("activate-changes", lambda x: auth_php._create_auth_file("activate-changes")),
    )
    for name, func in args:
        hooks.register_builtin(name, func)


def _register_cronjobs(cron_job_registry: CronJobRegistry) -> None:
    cron_job_registry.register(
        CronJob(
            name="execute_activation_cleanup_background_job",
            callable=execute_activation_cleanup_background_job,
            interval=timedelta(minutes=1),
        )
    )
    cron_job_registry.register(
        CronJob(
            name="execute_network_scan_job",
            callable=execute_network_scan_job,
            interval=timedelta(minutes=1),
        )
    )
    cron_job_registry.register(
        CronJob(
            name="rebuild_folder_lookup_cache",
            callable=rebuild_folder_lookup_cache,
            interval=timedelta(minutes=1),
        )
    )
    cron_job_registry.register(
        CronJob(
            name="execute_host_removal_background_job",
            callable=automatic_host_removal.execute_host_removal_background_job,
            interval=timedelta(minutes=1),
        )
    )
    cron_job_registry.register(
        CronJob(
            name="execute_autodiscovery",
            callable=autodiscovery.execute_autodiscovery,
            interval=timedelta(minutes=5),
        )
    )
