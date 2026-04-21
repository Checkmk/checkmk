load("@aspect_bazel_lib//lib:copy_to_directory.bzl", "copy_to_directory")
load("@aspect_bazel_lib//lib:directory_path.bzl", "directory_path")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_filegroup", "pkg_files", "pkg_mkdirs", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:patchelf.bzl", "add_runpath", "set_runpath")

exports_files(["skel.permissions"])

directory_path(
    name = "nagios_lib_dir",
    directory = "@nagios//:gen_dir",
    path = "lib",
    tags = ["manual"],
)

directory_path(
    name = "nagios_share_dir",
    directory = "@nagios//:gen_dir",
    path = "share",
    tags = ["manual"],
)

copy_to_directory(
    name = "nagios_lib_copy",
    srcs = [":nagios_lib_dir"],
    include_external_repositories = ["**"],
    root_paths = ["**/lib"],
    tags = ["manual"],
)

copy_to_directory(
    name = "nagios_share_copy",
    srcs = [":nagios_share_dir"],
    include_external_repositories = ["**"],
    root_paths = ["**/share"],
    tags = ["manual"],
)

pkg_files(
    name = "nagios_lib_files",
    srcs = [":nagios_lib_copy"],
    prefix = "lib",
    strip_prefix = "nagios_lib_copy",
    tags = ["manual"],
)

pkg_files(
    name = "nagios_share_files",
    srcs = [":nagios_share_copy"],
    prefix = "share",
    strip_prefix = "nagios_share_copy",
    tags = ["manual"],
)

pkg_filegroup(
    name = "nagios_without_bin",
    srcs = [
        ":nagios_lib_files",
        ":nagios_share_files",
    ],
    tags = ["manual"],
)

# We must append the rpath. As the configure_make adds the host systems perl distrubution to the rpath as well.
add_runpath(
    name = "nagios_bin_runpath",
    srcs = ["@nagios//:nagios_bin"],
    # nagios links libltdl to load NEB event broker modules. DT_RUNPATH is not
    # searched for dlopen() calls; DT_RPATH is required.
    force_rpath = True,
    rpaths = ["$ORIGIN/../lib"],
    tags = ["manual"],
)

set_runpath(
    name = "nagios_bins_runpath",
    srcs = ["@nagios//:nagiostats_bin"],
    rpaths = ["$ORIGIN/../lib"],
    tags = ["manual"],
)

pkg_files(
    name = "nagios_bin",
    srcs = [
        ":merge-nagios-config",
        ":nagios_bin_runpath",
        ":nagios_bins_runpath",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    tags = ["manual"],
)

pkg_files(
    name = "diskspace_pkg",
    srcs = [
        ":diskspace",
    ],
    prefix = "share/diskspace/",
    renames = {":diskspace": "nagios"},
    tags = ["manual"],
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
    tags = ["manual"],
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
    tags = ["manual"],
)

pkg_mklink(
    name = "80-nagios",
    link_name = "skel/etc/rc.d/80-nagios",
    tags = ["manual"],
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
    tags = ["manual"],
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
    stamp = 1,
    tags = ["manual"],
    visibility = ["//omd:__pkg__"],
)
