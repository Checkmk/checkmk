#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.i18n import _, _l
from cmk.gui.permissions import (
    Permission,
    PermissionRegistry,
    PermissionSection,
    PermissionSectionRegistry,
)


def register(
    permission_section_registry: PermissionSectionRegistry, permission_registry: PermissionRegistry
) -> None:
    permission_section_registry.register(PERMISSION_SECTION_WATO)

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="use",
            title=_l("Use WATO"),
            description=_l(
                "This permissions allows users to use Setup - Checkmk's "
                "Web Administration Tool. Without this "
                "permission all references to Setup (buttons, links, "
                "snap-ins) will be invisible."
            ),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="edit",
            title=_l("Make changes, perform actions"),
            description=_l(
                "This permission is needed in order to make any "
                "changes or perform any actions at all. "
                "Without this permission, the user is only "
                "able to view data, and that only in modules he "
                "has explicit permissions for."
            ),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="seeall",
            title=_l("Read access to all modules"),
            description=_l(
                "When this permission is set then the user sees "
                "also such modules he has no explicit "
                "access to (see below)."
            ),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="activate",
            title=_l("Activate configuration"),
            description=_l(
                "This permission is needed for activating the "
                "current configuration (and thus rewriting the "
                "monitoring configuration and restart the monitoring daemon.)"
            ),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="activateforeign",
            title=_l("Activate foreign changes"),
            description=_l(
                "When several users work in parallel with Setup then "
                "several pending changes of different users might pile up "
                "before changes are activated. Only with this permission "
                "a user will be allowed to activate the current configuration "
                "if this situation appears."
            ),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="discard",
            title=_l("Revert changes"),
            description=_l(
                "This permission allows to revert pending changes. Beware that this holds only for "
                "the user's own pending changes, not for those of other users (foreign changes)."
            ),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="discardforeign",
            title=_l("Revert foreign changes"),
            description=_l(
                "When several users work in parallel with Setup then several pending changes of "
                "different users might pile up before changes are activated. Only with this permission "
                "a user will be allowed to revert all pending changes, including foreign ones."
            ),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="auditlog",
            title=_l("Audit log"),
            description=_l(
                "Access to the historic audit log. "
                "The currently pending changes can be seen by all users "
                "with access to Setup."
            ),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="clear_auditlog",
            title=_l("Archive audit log"),
            description=_l(
                "Archive the entries of the audit log. To be able to archive the audit log "
                'a user needs the generic Setup permission "Make changes, perform actions", '
                'the "View audit log" and this permission.'
            ),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="hosts",
            title=_l("Host management"),
            description=_l(
                "Access to the management of hosts and folders. This "
                "module has some additional permissions (see below)."
            ),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="edit_hosts",
            title=_l("Modify existing hosts"),
            description=_l(
                "Modify the properties of existing hosts. Please note: "
                "for the management of services (inventory) there is "
                "a separate permission (see below)"
            ),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="parentscan",
            title=_l("Perform network parent scan"),
            description=_l(
                "This permission is necessary for performing automatic "
                "scans for network parents of hosts (making use of traceroute). "
                "Please note, that for actually modifying the parents via the "
                "scan and for the creation of gateway hosts proper permissions "
                "for host and folders are also necessary."
            ),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="move_hosts",
            title=_l("Move existing hosts"),
            description=_l(
                "Move existing hosts to other folders. Please also add the permission "
                "<i>Modify existing hosts</i>."
            ),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="manage_hosts",
            title=_l("Add & remove hosts"),
            description=_l(
                "Add hosts to the monitoring and remove hosts "
                "from the monitoring. Please also add the permission "
                "<i>Modify existing hosts</i>."
            ),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="rename_hosts",
            title=_l("Rename existing hosts"),
            description=_l(
                "Rename existing hosts. Please also add the permission <i>Modify existing hosts</i>."
            ),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="diag_host",
            title=_l("Host diagnostic"),
            description=_l(
                "Check whether or not the host is reachable, test the different methods "
                "a host can be accessed, for example via agent, SNMPv1, SNMPv2 to find out "
                "the correct monitoring configuration for that host."
            ),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="clone_hosts",
            title=_l("Clone hosts"),
            description=_l(
                "Clone existing hosts to create new ones from the existing one."
                "Please also add the permission <i>Add & remove hosts</i>."
            ),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="random_hosts",
            title=_l("Create random hosts"),
            description=_l(
                "The creation of random hosts is a facility for test and development "
                "and disabled by default. It allows you to create a number of random "
                "hosts and thus simulate larger environments."
            ),
            defaults=[],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="update_dns_cache",
            title=_l("Update site DNS Cache"),
            description=_l(
                "Updating the sites DNS cache is necessary in order to reflect IP address "
                "changes in hosts that are configured without an explicit address."
            ),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="services",
            title=_l("Manage services"),
            description=_l("Do inventory and service configuration on existing hosts."),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="edit_folders",
            title=_l("Modify existing folders"),
            description=_l("Modify the properties of existing folders."),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="manage_folders",
            title=_l("Add & remove folders"),
            description=_l(
                "Add new folders and delete existing folders. If a folder to be deleted contains hosts then "
                "the permission to delete hosts is also required."
            ),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="passwords",
            title=_l("Password management"),
            description=_l("This permission is needed for the module <i>Passwords</i>."),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="edit_all_passwords",
            title=_l("Write access to all passwords"),
            description=_l(
                "Without this permission, users can only edit passwords which are shared with a contact "
                "group they are member of. This permission grants full access to all passwords."
            ),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="edit_all_predefined_conditions",
            title=_l("Write access to all predefined conditions"),
            description=_l(
                "Without this permission, users can only edit predefined conditions which are "
                "shared with a contact group they are member of. This permission grants full "
                "access to all predefined conditions."
            ),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="see_all_folders",
            title=_l("Read access to all hosts and folders"),
            description=_l(
                "Users without this permissions can only see folders with a contact group they are in."
            ),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="all_folders",
            title=_l("Write access to all hosts and folders"),
            description=_l(
                "Without this permission, operations on folders can only be done by users that are members of "
                "one of the folders contact groups. This permission grants full access to all folders and hosts."
            ),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="hosttags",
            title=_l("Manage tags"),
            description=_l(
                "Create, remove and edit tags. Removing tags also might remove rules, "
                "so this permission should not be available to normal users."
            ),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="global",
            title=_l("Global settings"),
            description=_l("Access to the module <i>Global settings</i>"),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="rulesets",
            title=_l("Rulesets"),
            description=_l(
                "Access to the module for managing Checkmk rules. Please note that a user can only "
                "manage rules in folders he has permissions to."
            ),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="groups",
            title=_l("Host & service groups"),
            description=_l("Access to the modules for managing host and service groups."),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="timeperiods",
            title=_l("Time periods"),
            description=_l("Access to the module <i>Time periods</i>"),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="sites",
            title=_l("Site management"),
            description=_l(
                "Access to the module for managing connections to remote monitoring sites."
            ),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="automation",
            title=_l("Site remote automation"),
            description=_l(
                "This permission is needed for a remote administration of the site "
                "as a distributed Setup slave."
            ),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="users",
            title=_l("User management"),
            description=_l(
                "This permission is needed for the modules <b>Users</b>, "
                "<b>Roles</b> and <b>Contact groups</b>"
            ),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="user_migrate",
            title=_l("Migrate users to another connection"),
            description=_l(
                "This permission allows users to migrate other users to another connection"
            ),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="show_last_user_activity",
            title=_l("Show last user activity"),
            description=_l("Show the online state and last user activity on the users page"),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="notifications",
            title=_l("Notification configuration"),
            description=_l(
                "This permission is needed for the new rule based notification configuration via the Setup module <i>Notifications</i>."
            ),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="backups",
            title=_l("Backup & restore"),
            description=_l(
                "Access to the module <i>Site backup</i>. Please note: a user with "
                "write access to this module "
                "can make arbitrary changes to the configuration by restoring uploaded snapshots."
            ),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="pattern_editor",
            title=_l("Logfile pattern analyzer"),
            description=_l("Access to the module for analyzing and validating logfile patterns."),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="icons",
            title=_l("Manage custom icons"),
            description=_l("Upload or delete custom icons"),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="custom_attributes",
            title=_l("Manage custom attributes"),
            description=_l("Manage custom host- and user attributes"),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="download_agents",
            title=_l("Monitoring Agents"),
            description=_l(
                "Download the default Checkmk monitoring agents for Linux, "
                "Windows and other operating systems."
            ),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="download_agent_output",
            title=_l("Download agent output / SNMP walks"),
            description=_l(
                "Allows to download the current agent output or SNMP walks of the monitored hosts."
            ),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="set_read_only",
            title=_l("Set Setup to read only mode for other users"),
            description=_l("Prevent other users from making modifications to Setup."),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="analyze_config",
            title=_l("Access analyze configuration"),
            description=_l(
                "Setup has a module that gives you hints on how to tune your Checkmk installation."
            ),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="diagnostics",
            title=_l("Access the diagnostics mode"),
            description=_l("Collect information of Checkmk sites for diagnostic analysis."),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="add_or_modify_executables",
            title=_l("Add or modify executables"),
            description=_l(
                "There are different places in Checkmk where an admin can use the GUI to add "
                "executable code to a Checkmk site or agent. For example when configuring "
                "datasource programs, the user inserts a command line for gathering monitoring data. "
                "This command line is then executed during monitoring by Checkmk. Another example is "
                "the upload of extension packages (MKPs). All these functions have in "
                "common that the user provides data that is executed by Checkmk or the agent. "
                'If you want to ensure that your Setup users cannot "inject" arbitrary executables '
                "into your Checkmk installation, you only need to remove this permission for them. "
                "This permission is needed in addition to the other component related permissions. "
                "For example you need the <tt>wato.rulesets</tt> permission together with this "
                "permission to be able to configure rulesets where bare command lines are "
                "configured."
            ),
            defaults=["admin"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="service_discovery_to_undecided",
            title=_l("Service discovery: Move to undecided services"),
            description=_l("Service discovery: Move to undecided services"),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="service_discovery_to_monitored",
            title=_l("Service discovery: Move to monitored services"),
            description=_l("Service discovery: Move to monitored services"),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="service_discovery_to_ignored",
            title=_l("Service discovery: Disabled services"),
            description=_l("Service discovery: Disabled services"),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="service_discovery_to_removed",
            title=_l("Service discovery: Remove services"),
            description=_l("Service discovery: Remove services"),
            defaults=["admin", "user"],
        )
    )

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="check_plugins",
            title=_l("Catalog of check plug-ins"),
            description=_l("Use the catalog of check plug-ins."),
            defaults=["admin", "user"],
        )
    )


PERMISSION_SECTION_WATO = PermissionSection(
    name="wato",
    title=_("Setup"),
)
