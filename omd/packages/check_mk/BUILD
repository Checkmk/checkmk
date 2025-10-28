load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

exports_files(["diskspace"])

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

pkg_tar(
    name = "check_mk",
    srcs = [
        ":post_cp",
        ":post_create",
        ":post_mv",
        ":post_restore",
        ":post_update",
    ],
    empty_dirs = [
        "lib/nagios/plugins",
        "skel/local/lib/nagios/plugins",
        "skel/local/lib/python3/cmk/gui/plugins/dashboard",
        "skel/local/lib/python3/cmk/gui/plugins/views",
        "skel/local/lib/python3/cmk/plugins",
        "skel/local/lib/python3/cmk_addons/plugins",
    ],
    visibility = ["//omd:__pkg__"],
)
