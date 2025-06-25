load("@//bazel/rules:filtered_subdir.bzl", "filtered_subdir")
load("@//bazel/rules:make_deployable.bzl", "string_replace")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mkdirs", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

pkg_files(
    name = "skel_pkg",
    srcs = glob(
        ["skel/**/*"],
        exclude = [
            "skel/etc/rc.d/**",
            "**/.gitignore",
        ],
    ),
    strip_prefix = strip_prefix.from_pkg(""),
)

exports_files(["skel.permissions"])

pkg_mklink(
    name = "50-npcd",
    link_name = "skel/etc/rc.d/50-npcd",
    target = "../init.d/npcd",
)

pkg_mklink(
    name = "52-pnp_gearman_worker",
    link_name = "skel/etc/rc.d/52-pnp_gearman_worker",
    target = "../init.d/pnp_gearman_worker",
)

pkg_files(
    name = "PNP4NAGIOS_pkg",
    srcs = ["PNP4NAGIOS"],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "lib/omd/hooks",
)

filegroup(
    name = "bin_filegroup",
    srcs = ["@pnp4nagios//:build"],
    output_group = "npcd",
)

pkg_files(
    name = "bin_pkg",
    srcs = [":bin_filegroup"],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "bin",
)

filegroup(
    name = "gen_dir_filegroup",
    srcs = ["@pnp4nagios//:build"],
    output_group = "gen_dir",
)

filtered_subdir(
    name = "lib_filegroup",
    src = ":gen_dir_filegroup",
    excludes = ["kohana/"],
    subdir = "lib",
)

string_replace(
    name = "lib_with_omdroot_filegroup",
    src = ":lib_filegroup",
    filepattern = ["*.pl"],
    replace_labels = {
        "cmk_version": "//bazel/cmk/version",
        "cmk_edition": "//bazel/cmk/edition",
    },
    replace_pattern = "__OMD_ROOT__",
    value = "/omd/versions/{cmk_version}.{cmk_edition}",
)

pkg_files(
    name = "lib_pkg",
    srcs = [":lib_with_omdroot_filegroup"],
    attributes = pkg_attributes(mode = "0755"),
    strip_prefix = strip_prefix.from_pkg("lib_with_omdroot_filegroup"),
)

filtered_subdir(
    name = "man_filegroup",
    src = ":gen_dir_filegroup",
    subdir = "man",
)

pkg_files(
    name = "man_pkg",
    srcs = [":man_filegroup"],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "share",
)

filtered_subdir(
    name = "doc_filegroup",
    src = ":gen_dir_filegroup",
    subdir = "doc/pnp4nagios",
)

pkg_files(
    name = "doc_pkg",
    srcs = [":doc_filegroup"],
    prefix = "share/doc",
)

pkg_files(
    name = "diskspace_pkg",
    srcs = ["diskspace"],
    renames = {"diskspace": "share/diskspace/pnp4nagios"},
)

pkg_mkdirs(
    name = "emptydirs_pkg",
    dirs = [
        "include",
        "skel/var/pnp4nagios/log",
        "skel/var/pnp4nagios/perfdata",
        "skel/var/pnp4nagios/stats",
        "skel/var/pnp4nagios/spool",
        "skel/tmp/pnp4nagios/lock",
        "skel/tmp/pnp4nagios/run",
        "skel/tmp/pnp4nagios/stats",
        "skel/etc/pnp4nagios/config.d",
    ],
)

pkg_tar(
    name = "pnp4nagios",
    srcs = [
        ":50-npcd",
        ":52-pnp_gearman_worker",
        ":PNP4NAGIOS_pkg",
        ":bin_pkg",
        ":diskspace_pkg",
        ":doc_pkg",
        ":emptydirs_pkg",
        ":lib_pkg",
        ":man_pkg",
        ":skel_pkg",
    ],
    visibility = ["//omd:__pkg__"],
)
