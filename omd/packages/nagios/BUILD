load("@//bazel/rules:exclude_from_filegroup.bzl", "exclude_from_filegroup")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mkdirs", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

exports_files(["skel.permissions"])

exclude_from_filegroup(
    name = "nagios_rest",
    src = "@nagios//:gen_dir",
    excludes = ["bin/*"],
)

pkg_files(
    name = "nagios_without_bin",
    srcs = [
        "nagios_rest",
    ],
    strip_prefix = "rest",
)

pkg_files(
    name = "nagios_bin",
    srcs = [
        ":merge-nagios-config",
        "@nagios//:nagios_bin",
        "@nagios//:nagiostats_bin",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
)

pkg_files(
    name = "diskspace_pkg",
    srcs = [
        ":diskspace",
    ],
    prefix = "share/diskspace/",
    renames = {":diskspace": "nagios"},
)

pkg_files(
    name = "skel",
    srcs = [
        "skel/etc/nagios/conf.d/templates.cfg",
        "skel/etc/nagios/nagios.cfg",
        "skel/etc/nagios/nagios.d/dependency.cfg",
        "skel/etc/nagios/nagios.d/eventhandler.cfg",
        "skel/etc/nagios/nagios.d/flapping.cfg",
        "skel/etc/nagios/nagios.d/freshness.cfg",
        "skel/etc/nagios/nagios.d/logging.cfg",
        "skel/etc/nagios/nagios.d/misc.cfg",
        "skel/etc/nagios/nagios.d/obsess.cfg",
        "skel/etc/nagios/nagios.d/omd.cfg",
        "skel/etc/nagios/nagios.d/retention.cfg",
        "skel/etc/nagios/nagios.d/timing.cfg",
        "skel/etc/nagios/nagios.d/tuning.cfg",
        "skel/etc/nagios/resource.cfg",
        "skel/etc/nagios/ssi/README",
    ],
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_files(
    name = "skel_755",
    srcs = [
        "skel/etc/init.d/nagios",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_mklink(
    name = "80-nagios",
    link_name = "skel/etc/rc.d/80-nagios",
    target = "../init.d/nagios",
)

pkg_mkdirs(
    name = "skel_dirs",
    dirs = [
        "skel/var/nagios/",
        "skel/var/nagios/archive/",
        "skel/local/share/nagios/htdocs/theme/",
        "skel/local/share/nagios/htdocs/",
        "skel/tmp/nagios/checkresults/",
        "skel/tmp/nagios/tmp/",
    ],
)

pkg_tar(
    name = "nagios",
    srcs = [
        ":80-nagios",
        ":diskspace_pkg",
        ":nagios_bin",
        ":nagios_without_bin",
        ":skel",
        ":skel_755",
        ":skel_dirs",
    ],
    visibility = ["//omd:__pkg__"],
)
