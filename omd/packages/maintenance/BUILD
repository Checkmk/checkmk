load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mkdirs", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

exports_files(["skel.permissions"])

pkg_files(
    name = "bin_pkg",
    srcs = [
        "logrotate",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
)

pkg_files(
    name = "bin_diskspace_pkg",
    srcs = [
        "diskspace.py",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    renames = {"diskspace.py": "diskspace"},
)

pkg_files(
    name = "skel",
    srcs = [
        "skel/etc/cron.d/diskspace",
        "skel/etc/cron.d/logrotate",
        "skel/etc/init.d/crontab",
        "skel/etc/logrotate.conf",
        "skel/etc/logrotate.d/apache",
        "skel/etc/logrotate.d/diskspace",
    ],
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_mkdirs(
    name = "skel_diskspace",
    dirs = ["skel/local/share/diskspace"],
)

pkg_mklink(
    name = "skel_crontab",
    link_name = "skel/etc/rc.d/99-crontab",
    target = "../init.d/crontab",
)

pkg_tar(
    name = "maintenance",
    srcs = [
        ":bin_diskspace_pkg",
        ":bin_pkg",
        ":skel",
        ":skel_crontab",
        ":skel_diskspace",
    ],
    visibility = ["//omd:__pkg__"],
)
