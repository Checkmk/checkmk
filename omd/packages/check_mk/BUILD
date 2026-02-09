load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mkdirs", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

exports_files([
    "diskspace",
    "skel.permissions",
])

filegroup(
    name = "hooks",
    srcs = [
        "AGENT_RECEIVER",
        "AGENT_RECEIVER_PORT",
        "AUTOMATION_HELPER",
        "MKEVENTD",
        "MKEVENTD_SNMPTRAP",
        "MKEVENTD_SYSLOG",
        "MKEVENTD_SYSLOG_TCP",
        "MULTISITE_AUTHORISATION",
        "MULTISITE_COOKIE_AUTH",
        "PIGGYBACK_HUB",
        "TRACE_SEND",
        "TRACE_SEND_TARGET",
        "TRACE_SERVICE_NAMESPACE",
    ],
    visibility = ["//omd:__subpackages__"],
)

pkg_files(
    name = "post_create",
    srcs = [
        "post-create/01_create-sample-config.py",
        "post-create/02_message-broker-certs",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "lib/omd/scripts/post-create/",
)

pkg_files(
    name = "post_update",
    srcs = [
        "scripts/post-update/01_mkp-disable-outdated",
        "scripts/post-update/02_cmk-update-config",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "lib/omd/scripts/post-update/",
)

pkg_files(
    name = "post_mv",
    srcs = [
        "scripts/post-mv/01_cmk-post-rename-site",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "lib/omd/scripts/post-mv/",
)

pkg_files(
    name = "post_cp",
    srcs = [
        "scripts/post-cp/01_cmk-post-rename-site",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "lib/omd/scripts/post-cp/",
)

pkg_files(
    name = "post_restore",
    srcs = [
        "scripts/post-restore/01_cmk-post-rename-site",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "lib/omd/scripts/post-restore/",
)

#skel
pkg_files(
    name = "skel",
    srcs = glob(
        ["skel/**/*"],
        exclude = [
            "skel/etc/init.d/*",
            "skel/etc/rc.d/*",
            "**/.gitignore",
            "**/OWNERS",
        ],
    ),
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_files(
    name = "skel_755",
    srcs = glob(
        ["skel/etc/init.d/*"],
        exclude = [
            "**/.f12",
        ],
    ),
    attributes = pkg_attributes(
        mode = "0755",
    ),
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_mklink(
    name = "10-agent-receiver",
    link_name = "skel/etc/rc.d/10-agent-receiver",
    target = "../init.d/agent-receiver",
)

pkg_mklink(
    name = "10-mkeventd",
    link_name = "skel/etc/rc.d/10-mkeventd",
    target = "../init.d/mkeventd",
)

pkg_mklink(
    name = "55-automation-helper",
    link_name = "skel/etc/rc.d/55-automation-helper",
    target = "../init.d/automation-helper",
)

pkg_mklink(
    name = "60-ui-job-scheduler",
    link_name = "skel/etc/rc.d/60-ui-job-scheduler",
    target = "../init.d/ui-job-scheduler",
)

pkg_mklink(
    name = "90-piggyback-hub",
    link_name = "skel/etc/rc.d/90-piggyback-hub",
    target = "../init.d/piggyback-hub",
)

pkg_mkdirs(
    name = "empty_dirs",
    dirs = [
        "lib/nagios/plugins",
        "lib/python3/cmk/gui/plugins/userdb",
        "lib/python3/cmk/gui/plugins/watolib",
        "skel/local/lib/nagios/plugins",
        "skel/local/lib/python3/cmk/gui/plugins/dashboard",
        "skel/local/lib/python3/cmk/gui/plugins/views",
        "skel/local/lib/python3/cmk/plugins",
        "skel/local/lib/python3/cmk_addons/plugins",
        "skel/etc/check_mk/multisite.d/wato",
        "skel/etc/check_mk/conf.d/wato",
        "skel/local/share/doc/check_mk",
        "skel/local/share/check_mk/pnp-templates",
        "skel/local/share/check_mk/web/htdocs/images",
        "skel/local/share/check_mk/web/htdocs",
        "skel/local/share/check_mk/web/htdocs/themes",
        "skel/local/share/check_mk/web/plugins/visuals",
        "skel/local/share/check_mk/web/plugins/perfometer",
        "skel/local/share/check_mk/web/plugins/views",
        "skel/local/share/check_mk/web/plugins/pages",
        "skel/local/share/check_mk/web/plugins/metrics",
        "skel/local/share/check_mk/web/plugins/sidebar",
        "skel/local/share/check_mk/web/plugins/config",
        "skel/local/share/check_mk/web/plugins/icons",
        "skel/local/share/check_mk/web/plugins/dashboard",
        "skel/local/share/check_mk/web/plugins/wato",
        "skel/local/share/check_mk/notifications",
        "skel/local/share/check_mk/locale",
        "skel/local/share/check_mk/inventory",
        "skel/local/share/check_mk/agents/linux/alert_handlers",
        "skel/local/share/check_mk/agents/plugins",
        "skel/local/share/check_mk/agents/bakery",
        "skel/local/share/check_mk/pnp-rraconf",
        "skel/local/share/check_mk/mibs",
        "skel/local/share/check_mk/alert_handlers",
        "skel/local/share/check_mk/reporting/images",
        "skel/var/check_mk/web",
        "skel/var/check_mk/discovered_host_labels",
        "skel/var/check_mk/precompiled",
        "skel/var/check_mk/autochecks",
        "skel/var/check_mk/backup",
        "skel/var/check_mk/logwatch",
        "skel/var/check_mk/snmpwalks",
        "skel/var/check_mk/packages",
        "skel/var/check_mk/crashes",
        "skel/var/check_mk/wato/snapshots",
        "skel/var/check_mk/wato",
        "skel/var/check_mk/wato/log",
        "skel/var/check_mk/packages_local",
        "skel/var/log/mkeventd",
        "skel/tmp/check_mk/piggyback",
        "skel/tmp/check_mk/piggyback_sources",
        "skel/tmp/check_mk/counters",
        "skel/tmp/check_mk/cache",
        "skel/tmp/check_mk/debug",
    ],
)

pkg_tar(
    name = "check_mk",
    srcs = [
        ":10-agent-receiver",
        ":10-mkeventd",
        ":55-automation-helper",
        ":60-ui-job-scheduler",
        ":90-piggyback-hub",
        ":empty_dirs",
        ":post_cp",
        ":post_create",
        ":post_mv",
        ":post_restore",
        ":post_update",
        ":skel",
        ":skel_755",
    ],
    stamp = 1,
    visibility = ["//omd:__pkg__"],
)
