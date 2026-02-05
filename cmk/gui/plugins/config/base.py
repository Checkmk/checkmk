#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Default configuration settings for the Checkmk GUI"""

# mypy: disable-error-code="type-arg"

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from livestatus import BrokerConnections, SiteConfigurations

from cmk.ccc.version import Edition, edition
from cmk.checkengine.discovery import DiscoverySettingFlags
from cmk.gui.role_types import BuiltInUserRole, CustomUserRole
from cmk.gui.type_defs import (
    AgentControllerCertificates,
    BuiltinIconVisibility,
    CustomHostAttrSpec,
    CustomUserAttrSpec,
    GraphTimerange,
    GroupSpec,
    IconSpec,
    PasswordPolicy,
    ReadOnlySpec,
    TrustedCertificateAuthorities,
    UserSpec,
    VirtualHostTreeSpec,
)
from cmk.gui.user_connection_config_types import ConfigurableUserConnectionSpec
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.inventory.config import InvCleanupParams
from cmk.utils import paths
from cmk.utils.tags import TagConfigSpec

CustomLinkSpec = tuple[str, bool, list[tuple[str, str, str | None, str]]]

# Links for everyone
custom_links_guest: list[CustomLinkSpec] = [
    (
        "Add-ons",
        True,
        [
            ("NagVis", "../nagvis/", "icon_nagvis.png", "main"),
        ],
    ),
]

# The members of the role 'user' get the same links as the guests
# but some in addition
custom_links_user: list[CustomLinkSpec] = [
    (
        "Open Source Components",
        False,
        [
            ("CheckMK", "https://checkmk.com", None, "_blank"),
            ("Nagios", "https://www.nagios.org/", None, "_blank"),
            ("NagVis", "https://nagvis.org/", None, "_blank"),
            ("RRDTool", "https://oss.oetiker.ch/rrdtool/", None, "_blank"),
        ],
    )
]

# The admins yet get further links
custom_links_admin: list[CustomLinkSpec] = [
    (
        "Support",
        False,
        [
            ("CheckMK", "https://checkmk.com/", None, "_blank"),
            ("CheckMK Mailinglists", "https://checkmk.com/community.php", None, "_blank"),
            ("CheckMK Exchange", "https://checkmk.com/check_mk-exchange.php", None, "_blank"),
        ],
    )
]


def make_default_user_profile() -> UserSpec:
    return UserSpec(
        contactgroups=[],
        roles=["user"],
        force_authuser=False,
    )


ActivateChangesCommentMode = Literal["enforce", "optional", "disabled"]


@dataclass
class CREConfig:
    # .
    #   .--Generic-------------------------------------------------------------.
    #   |                   ____                      _                        |
    #   |                  / ___| ___ _ __   ___ _ __(_) ___                   |
    #   |                 | |  _ / _ \ '_ \ / _ \ '__| |/ __|                  |
    #   |                 | |_| |  __/ | | |  __/ |  | | (__                   |
    #   |                  \____|\___|_| |_|\___|_|  |_|\___|                  |
    #   |                                                                      |
    #   '----------------------------------------------------------------------'

    # User supplied roles
    roles: dict[str, BuiltInUserRole | CustomUserRole] = field(
        default_factory=lambda: {
            "admin": BuiltInUserRole(
                {
                    "alias": "Administrator",
                    "permissions": {},
                    "builtin": True,
                }
            ),
            "user": BuiltInUserRole(
                {
                    "alias": "Normal monitoring user",
                    "permissions": {},
                    "builtin": True,
                }
            ),
            "guest": BuiltInUserRole(
                {
                    "alias": "Guest user",
                    "permissions": {},
                    "builtin": True,
                }
            ),
            "agent_registration": BuiltInUserRole(
                {
                    "alias": "Agent registration user",
                    "permissions": {},
                    "builtin": True,
                }
            ),
            "no_permissions": BuiltInUserRole(
                {
                    "alias": "Empty template for least privilege roles",
                    "permissions": {},
                    "builtin": True,
                }
            ),
        }
    )

    # define default values for all settings
    sites: SiteConfigurations = field(default_factory=lambda: SiteConfigurations({}))
    broker_connections: BrokerConnections = field(default_factory=lambda: BrokerConnections({}))
    debug: bool = False
    screenshotmode: bool = False
    profile: bool | str = False
    user_online_maxage: int = 30  # seconds

    log_levels: dict[str, int] = field(
        default_factory=lambda: {
            "cmk.web": 30,
            "cmk.web.ldap": 30,
            "cmk.web.saml2": 30,
            "cmk.web.auth": 30,
            "cmk.web.bi.compilation": 30,
            "cmk.web.automations": 30,
            "cmk.web.background-job": 30,
            "cmk.web.ui-job-scheduler": 20,
            "cmk.web.slow-views": 30,
            "cmk.web.agent_registration": 30,
        }
    )

    slow_views_duration_threshold: int = 60

    multisite_users: dict[str, UserSpec] = field(default_factory=dict)
    multisite_hostgroups: dict = field(default_factory=dict)
    multisite_servicegroups: dict = field(default_factory=dict)
    multisite_contactgroups: dict = field(default_factory=dict)

    inventory_cleanup: InvCleanupParams = field(
        default_factory=lambda: InvCleanupParams(
            for_hosts=[],
            default=None,
            abandoned_file_age=30 * 86400,
        )
    )

    #    ____  _     _      _
    #   / ___|(_) __| | ___| |__   __ _ _ __
    #   \___ \| |/ _` |/ _ \ '_ \ / _` | '__|
    #    ___) | | (_| |  __/ |_) | (_| | |
    #   |____/|_|\__,_|\___|_.__/ \__,_|_|
    #

    sidebar: list[tuple[str, str]] = field(
        default_factory=lambda: [
            ("a_welcome", "open"),
            ("tactical_overview", "open"),
            ("bookmarks", "open"),
            ("master_control", "closed"),
        ]
    )

    # Interval of snap-in updates in seconds
    sidebar_update_interval: float = 30.0

    # It is possible (but ugly) to enable a scrollbar in the sidebar
    sidebar_show_scrollbar: bool = False

    # Enable regular checking for notification messages
    sidebar_notify_interval: int = 30

    # Maximum number of results to show in quicksearch dropdown
    quicksearch_dropdown_limit: int = 80

    # Quicksearch search order
    quicksearch_search_order: list[tuple[str, str]] = field(
        default_factory=lambda: [
            ("menu", "continue"),
            ("h", "continue"),
            ("al", "continue"),
            ("ad", "continue"),
            ("s", "continue"),
        ]
    )

    failed_notification_horizon: int = 7 * 60 * 60 * 24

    #    _     _           _ _
    #   | |   (_)_ __ ___ (_) |_ ___
    #   | |   | | '_ ` _ \| | __/ __|
    #   | |___| | | | | | | | |_\__ \
    #   |_____|_|_| |_| |_|_|\__|___/
    #

    soft_query_limit: int = 1000
    hard_query_limit: int = 5000

    #    ____                        _
    #   / ___|  ___  _   _ _ __   __| |___
    #   \___ \ / _ \| | | | '_ \ / _` / __|
    #    ___) | (_) | |_| | | | | (_| \__ \
    #   |____/ \___/ \__,_|_| |_|\__,_|___/
    #

    sound_url: str = "sounds/"
    enable_sounds: bool = False
    sounds: list[tuple[str, str]] = field(
        default_factory=lambda: [
            ("down", "down.wav"),
            ("critical", "critical.wav"),
            ("unknown", "unknown.wav"),
            ("warning", "warning.wav"),
            # ( None,       "ok.wav" ),
        ]
    )

    #   __     ___                             _   _
    #   \ \   / (_) _____      __   ___  _ __ | |_(_) ___  _ __  ___
    #    \ \ / /| |/ _ \ \ /\ / /  / _ \| '_ \| __| |/ _ \| '_ \/ __|
    #     \ V / | |  __/\ V  V /  | (_) | |_) | |_| | (_) | | | \__ \
    #      \_/  |_|\___| \_/\_/    \___/| .__/ \__|_|\___/|_| |_|___/
    #                                   |_|

    view_option_refreshes: list[int] = field(default_factory=lambda: [30, 60, 90, 0])
    view_option_columns: list[int] = field(default_factory=lambda: [1, 2, 3, 4, 5, 6, 8, 10, 12])

    # MISC
    doculink_urlformat: str = "https://checkmk.com/checkmk_%s.html"

    acknowledge_problems: dict[str, bool] = field(
        default_factory=lambda: {
            "ack_sticky": False,
            "ack_notify": True,
            "ack_persistent": False,
        }
    )

    #   ____          _                    _     _       _
    #  / ___|   _ ___| |_ ___  _ __ ___   | |   (_)_ __ | | _____
    # | |  | | | / __| __/ _ \| '_ ` _ \  | |   | | '_ \| |/ / __|
    # | |__| |_| \__ \ || (_) | | | | | | | |___| | | | |   <\__ \
    #  \____\__,_|___/\__\___/|_| |_| |_| |_____|_|_| |_|_|\_\___/
    #

    # TODO: Improve type below, see cmk.gui.plugins.sidebar.custom_links
    custom_links: dict[str, list[CustomLinkSpec]] = field(
        default_factory=lambda: {
            "guest": custom_links_guest,
            "user": custom_links_guest + custom_links_user,
            "admin": custom_links_guest + custom_links_user + custom_links_admin,
        }
    )

    #  __     __         _
    #  \ \   / /_ _ _ __(_) ___  _   _ ___
    #   \ \ / / _` | '__| |/ _ \| | | / __|
    #    \ V / (_| | |  | | (_) | |_| \__ \
    #     \_/ \__,_|_|  |_|\___/ \__,_|___/
    #

    debug_livestatus_queries: bool = False

    # Show livestatus errors in multi site setup if some sites are
    # not reachable.
    show_livestatus_errors: bool = True

    # Whether the livestatu proxy daemon is available
    liveproxyd_enabled: bool = False

    # Patterns to group services in table views together
    service_view_grouping: list[GroupSpec] = field(default_factory=list)

    # Custom user stylesheet to load (resides in htdocs/)
    custom_style_sheet: str | None = None

    # UI theme to use
    ui_theme: str = "modern-dark"

    # Show mode to use
    show_mode: str = "default_show_less"

    # URL for start page in main frame (welcome page)
    start_url: str = "dashboard.py"

    # Page heading for main frame set
    page_heading: str = "Checkmk %s"

    # Default for login screen customization; hiding the version as it can be a security vulnerability
    login_screen: dict = field(default_factory=lambda: {"hide_version": True})

    # Timeout for rescheduling of host- and servicechecks
    reschedule_timeout: float = 10.0

    # Timeout for SNMP walks in seconds
    snmp_walk_download_timeout: float = 900

    # Number of columsn in "Filter" form
    filter_columns: int = 2

    # Default language for l10n
    default_language: str = "en"

    # Default timestamp format to be used in multisite
    default_ts_format: str = "mixed"

    # Maximum livetime of unmodified selections
    selection_livetime: int = 3600

    # Configure HTTP header to read usernames from
    auth_by_http_header: str | None = None

    # Number of rows to display by default in tables rendered with
    # the table.py module
    table_row_limit: int = 100

    # Add an icon pointing to the Setup rule to each service
    multisite_draw_ruleicon: bool = True

    # Default downtime configuration
    adhoc_downtime: dict = field(default_factory=dict)

    # Display dashboard date
    pagetitle_date_format: Literal["yyyy-mm-dd", "dd.mm.yyyy"] | None = None

    # Value of the host_staleness/service_staleness field to make hosts/services
    # appear in a stale state
    staleness_threshold: float = 1.5

    # Escape HTML in plug-in output / log messages
    escape_plugin_output: bool = True

    # Virtual host trees for the "Virtual Host Trees" snap-in
    virtual_host_trees: Sequence[VirtualHostTreeSpec] = field(default_factory=list)

    # Target URL for sending crash reports to
    crash_report_url: str = "https://crash.checkmk.com"
    # Target email address for "Crashed Check" page
    crash_report_target: str = "feedback@checkmk.com"

    # GUI Tests (see cmk-guitest)
    guitests_enabled: bool = False

    # Bulk discovery default options
    bulk_discovery_default_settings: dict[str, Any] = field(
        default_factory=lambda: {
            "mode": (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=False,
                    remove_vanished_services=False,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                    update_host_labels=True,
                ),
            ),
            "selection": (True, False, False, False),
            "performance": (True, 10),
            "error_handling": True,
        }
    )

    use_siteicons: bool = False

    graph_timeranges: list[GraphTimerange] = field(
        default_factory=lambda: [
            GraphTimerange(title="The last 4 hours", duration=4 * 60 * 60),
            GraphTimerange(title="The last 25 hours", duration=25 * 60 * 60),
            GraphTimerange(title="The last 8 days", duration=8 * 24 * 60 * 60),
            GraphTimerange(title="The last 35 days", duration=35 * 24 * 60 * 60),
            GraphTimerange(title="The last 400 days", duration=400 * 24 * 60 * 60),
        ]
    )

    agent_controller_certificates: AgentControllerCertificates = field(
        default_factory=lambda: AgentControllerCertificates(lifetime_in_months=60)
    )

    # Default temperature unit
    default_temperature_unit: str = TemperatureUnit.CELSIUS.value

    # Configuration bundles
    configuration_bundles: dict[str, Any] = field(default_factory=dict)

    #     _   _               ____  ____
    #    | | | |___  ___ _ __|  _ \| __ )
    #    | | | / __|/ _ \ '__| | | |  _ \
    #    | |_| \__ \  __/ |  | |_| | |_) |
    #     \___/|___/\___|_|  |____/|____/
    #

    # This option can not be configured through Setup anymore. Config has been
    # moved to the sites configuration. This might have been configured in master/remote
    # in previous versions and is set on remote sites during Setup synchronization.
    userdb_automatic_sync: str | None = "master"

    # Permission to login to the web gui of a site (can be changed in sites
    # configuration)
    user_login: bool = True

    # Holds dicts defining user connector instances and their properties
    user_connections: Sequence[ConfigurableUserConnectionSpec] = field(default_factory=list)

    default_user_profile: UserSpec = field(default_factory=make_default_user_profile)
    log_logon_failures: bool = True
    lock_on_logon_failures: int | None = 10
    default_dynamic_visual_permission: Literal["yes", "no"] = "yes"
    require_two_factor_all_users: bool = False
    session_mgmt: dict[str, Any] = field(
        default_factory=lambda: {
            "max_duration": {"enforce_reauth": 86400, "enforce_reauth_warning_threshold": 900},
            "user_idle_timeout": 5400,
        }
    )
    # This option can be configured in Global Settings.
    # When configured, these are the expected behaviors:
    # 1. setting this option (the first time) does not log the user out from existing sessions
    # 2. with every successful login, all previous sessions of the user will be removed, only
    # one session (the one resulting from the successful login) will be kept
    single_user_session: int | None = None
    password_policy: PasswordPolicy = field(default_factory=lambda: PasswordPolicy(min_length=12))

    # Individual changes to user's authentication security will trigger either emails or use notifications
    # Default is 7 days
    user_security_notification_duration: dict[str, Any] = field(
        default_factory=lambda: {
            "max_duration": 604800,
            "update_existing_duration": False,
        }
    )

    user_localizations: dict[str, dict[str, str]] = field(
        default_factory=lambda: {
            "Agent type": {
                "de": "Art des Agenten",
            },
            "Business critical": {
                "de": "Geschäftskritisch",
            },
            "Check_MK Agent (Server)": {
                "de": "Check_MK Agent (Server)",
            },
            "Criticality": {
                "de": "Kritikalität",
            },
            "DMZ (low latency, secure access)": {
                "de": "DMZ (geringe Latenz, hohe Sicherheit",
            },
            "Do not monitor this host": {
                "de": "Diesen Host nicht überwachen",
            },
            "Dual: Checkmk Agent + SNMP": {
                "de": "Dual: Checkmk Agent + SNMP",
            },
            "Legacy SNMP device (using V1)": {
                "de": "Alte SNMP-Geräte (mit Version 1)",
            },
            "Local network (low latency)": {
                "de": "Lokales Netzwerk (geringe Latenz)",
            },
            "Networking Segment": {
                "de": "Netzwerksegment",
            },
            "No Agent": {
                "de": "Kein Agent",
            },
            "Productive system": {
                "de": "Produktivsystem",
            },
            "Test system": {
                "de": "Testsystem",
            },
            "WAN (high latency)": {
                "de": "WAN (hohe Latenz)",
            },
            "monitor via Checkmk Agent": {
                "de": "Überwachung via Checkmk Agent",
            },
            "monitor via SNMP": {
                "de": "Überwachung via SNMP",
            },
            "SNMP (Networking device, Appliance)": {
                "de": "SNMP (Netzwerkgerät, Appliance)",
            },
        }
    )

    # Contains user specified icons and actions for hosts and services
    user_icons_and_actions: dict[str, IconSpec] = field(default_factory=dict)

    # Defintions of custom attributes to be used for services
    custom_service_attributes: dict = field(default_factory=dict)

    user_downtime_timeranges: list[dict[str, Any]] = field(
        default_factory=lambda: [
            {"title": "2 hours", "end": 2 * 60 * 60},
            {"title": "Today", "end": "next_day"},
            {"title": "This week", "end": "next_week"},
            {"title": "This month", "end": "next_month"},
            {"title": "This year", "end": "next_year"},
        ]
    )

    # Override toplevel and sort_index settings of built-in icons
    builtin_icon_visibility: dict[str, BuiltinIconVisibility] = field(default_factory=dict)

    trusted_certificate_authorities: TrustedCertificateAuthorities = field(
        default_factory=lambda: TrustedCertificateAuthorities(
            {
                "use_system_wide_cas": True,
                "trusted_cas": [],
            }
        )
    )

    site_subject_alternative_names: list[str] = field(default_factory=list)

    # .
    #   .--EC------------------------------------------------------------------.
    #   |                             _____ ____                               |
    #   |                            | ____/ ___|                              |
    #   |                            |  _|| |                                  |
    #   |                            | |__| |___                               |
    #   |                            |_____\____|                              |
    #   |                                                                      |
    #   '----------------------------------------------------------------------'

    mkeventd_enabled: bool = edition(paths.omd_root) is not Edition.CLOUD  # disabled in CSE
    mkeventd_pprint_rules: bool = False
    mkeventd_notify_contactgroup: str = ""
    mkeventd_notify_facility: int = 16
    mkeventd_notify_remotehost: str | None = None
    mkeventd_connect_timeout: int = 10
    log_level: int = 0
    log_rulehits: bool = False
    rule_optimizer: bool = True

    mkeventd_service_levels: list[tuple[int, str]] = field(
        default_factory=lambda: [
            (0, "(no Service level)"),
            (10, "Silver"),
            (20, "Gold"),
            (30, "Platinum"),
        ]
    )

    # .
    #   .--WATO----------------------------------------------------------------.
    #   |                     __        ___  _____ ___                         |
    #   |                     \ \      / / \|_   _/ _ \                        |
    #   |                      \ \ /\ / / _ \ | || | | |                       |
    #   |                       \ V  V / ___ \| || |_| |                       |
    #   |                        \_/\_/_/   \_\_| \___/                        |
    #   |                                                                      |
    #   '----------------------------------------------------------------------'

    # Pre 1.6 tag configuration variables
    wato_host_tags: list = field(default_factory=list)
    wato_aux_tags: list = field(default_factory=list)
    # Tag configuration variable since 1.6
    wato_tags: TagConfigSpec = field(
        default_factory=lambda: TagConfigSpec(
            {
                "tag_groups": [],
                "aux_tags": [],
            }
        )
    )

    wato_enabled: bool = True
    wato_hide_filenames: bool = True
    wato_hide_hosttags: bool = False
    wato_hide_varnames: bool = True
    wato_max_snapshots: int = 50
    wato_num_hostspecs: int = 12
    wato_num_itemspecs: int = 15
    wato_activation_method: str = "restart"
    wato_write_nagvis_auth: bool = False
    wato_use_git: bool = False
    wato_hidden_users: list = field(default_factory=list)
    wato_user_attrs: Sequence[CustomUserAttrSpec] = field(default_factory=list)
    wato_host_attrs: Sequence[CustomHostAttrSpec] = field(default_factory=list)
    wato_read_only: ReadOnlySpec = field(
        default_factory=lambda: ReadOnlySpec(
            enabled=False,
            message="",
            rw_users=[],
        )
    )
    wato_hide_folders_without_read_permissions: bool = False
    wato_pprint_config: bool = False
    wato_icon_categories: list[tuple[str, str]] = field(
        default_factory=lambda: [
            ("logos", "Logos"),
            ("parts", "Parts"),
            ("misc", "Misc"),
        ]
    )

    wato_activate_changes_comment_mode: ActivateChangesCommentMode = "disabled"

    # .
    #   .--Login with GET--------------------------------------------------------------------.
    #   |    _      ____   _____ _____ _   _   __  __ ______ _______ _    _  ____  _____     |
    #   |    | |    / __ \ / ____|_   _| \ | | |  \/  |  ____|__   __| |  | |/ __ \|  __ \   |
    #   |    | |   | |  | | |  __  | | |  \| | | \  / | |__     | |  | |__| | |  | | |  | |  |
    #   |    | |   | |  | | | |_ | | | | . ` | | |\/| |  __|    | |  |  __  | |  | | |  | |  |
    #   |    | |___| |__| | |__| |_| |_| |\  | | |  | | |____   | |  | |  | | |__| | |__| |  |
    #   |    |______\____/ \_____|_____|_| \_| |_|  |_|______|  |_|  |_|  |_|\____/|_____/   |
    #   |                                                                                    |
    #   '------------------------------------------------------------------------------------'

    enable_login_via_get: bool = False
    enable_deprecated_automation_user_authentication: bool = False

    # .
    #   .--REST API------------------------------------------------------------.
    #   |               ____  _____ ____ _____      _    ____ ___              |
    #   |              |  _ \| ____/ ___|_   _|    / \  |  _ \_ _|             |
    #   |              | |_) |  _| \___ \ | |     / _ \ | |_) | |              |
    #   |              |  _ <| |___ ___) || |    / ___ \|  __/| |              |
    #   |              |_| \_\_____|____/ |_|   /_/   \_\_|  |___|             |
    #   |                                                                      |
    #   '----------------------------------------------------------------------'

    rest_api_etag_locking: bool = True

    # .
    #   .--BI------------------------------------------------------------------.
    #   |                              ____ ___                                |
    #   |                             | __ )_ _|                               |
    #   |                             |  _ \| |                                |
    #   |                             | |_) | |                                |
    #   |                             |____/___|                               |
    #   |                                                                      |
    #   '----------------------------------------------------------------------'

    aggregation_rules: dict = field(default_factory=dict)
    aggregations: list = field(default_factory=list)
    host_aggregations: list = field(default_factory=list)
    bi_packs: dict = field(default_factory=dict)

    default_bi_layout: dict[str, str] = field(
        default_factory=lambda: {
            "node_style": "builtin_hierarchy",
            "line_style": "straight",
        }
    )
    bi_layouts: dict[str, dict] = field(
        default_factory=lambda: {
            "templates": {},
            "aggregations": {},
        }
    )

    # Deprecated. Kept for compatibility.
    bi_compile_log: str | None = None
    bi_precompile_on_demand: bool = False
    bi_use_legacy_compilation: bool = False
    wato_hide_help_in_lists: bool = True

    # new in 2.1
    config_storage_format: Literal["standard", "raw", "pickle", "anon"] = "pickle"

    # Development tools

    inject_js_profiling_code: bool = False
    load_frontend_vue: Literal["static_files", "inject"] = "static_files"
    # Vue experimental feature settings
    vue_experimental_features: dict[str, Any] = field(default_factory=dict)
