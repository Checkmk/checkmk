load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

pkg_files(
    name = "bin_pkg",
    srcs = [
        "lq",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
)

pkg_files(
    name = "hooks_pkg",
    srcs = [
        "LIVESTATUS_TCP",
        "LIVESTATUS_TCP_ONLY_FROM",
        "LIVESTATUS_TCP_PORT",
        "LIVESTATUS_TCP_TLS",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "lib/omd/hooks",
)

pkg_files(
    name = "skel",
    srcs = [
        "skel/etc/logrotate.d/livestatus",
        "skel/etc/mk-livestatus/livestatus.socket",
        "skel/etc/mk-livestatus/livestatus@.service",
        "skel/etc/mk-livestatus/nagios.cfg",
        "skel/etc/mk-livestatus/xinetd.conf",
        "skel/etc/stunnel/conf.d/01-livestatus.conf",
    ],
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_mklink(
    name = "nagios_cfg",
    link_name = "skel/etc/nagios/nagios.d/mk-livestatus.cfg",
    target = "../../mk-livestatus/nagios.cfg",
)

pkg_tar(
    name = "mk-livestatus",
    srcs = [
        ":bin_pkg",
        ":hooks_pkg",
        ":nagios_cfg",
        ":skel",
    ],
    visibility = ["//omd:__pkg__"],
)
