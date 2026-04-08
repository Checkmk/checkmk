load("@aspect_bazel_lib//lib:copy_to_directory.bzl", "copy_to_directory")
load("@aspect_bazel_lib//lib:directory_path.bzl", "directory_path")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mklink")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:patchelf.bzl", "set_runpath_tree")

exports_files(
    [
        # needed to allow `cmk_password_store.h` to be used
        "cmk_password_store.h",
    ],
    visibility = ["//visibility:public"],
)

filegroup(
    name = "monitoring_plugins_gen_dir",
    srcs = ["@monitoring-plugins//:monitoring-plugins"],
    output_group = "gen_dir",
    tags = ["manual"],
)

directory_path(
    name = "libexec_dir",
    directory = ":monitoring_plugins_gen_dir",
    path = "libexec",
    tags = ["manual"],
)

copy_to_directory(
    name = "libexec_copy",
    srcs = [":libexec_dir"],
    include_external_repositories = ["**"],
    root_paths = ["**/libexec"],
    tags = ["manual"],
)

set_runpath_tree(
    name = "monitoring-plugins_deployable_libexec",
    src = ":libexec_copy",
    rpath = "$ORIGIN/../../../lib",
    tags = ["manual"],
)

pkg_files(
    name = "libexec",
    srcs = [
        ":monitoring-plugins_deployable_libexec",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "lib/nagios/plugins/",
    strip_prefix = "monitoring-plugins_deployable_libexec",
    tags = ["manual"],
)

pkg_mklink(
    name = "check_icmp_symlink",
    link_name = "lib/nagios/plugins/check_host",
    tags = ["manual"],
    target = "check_icmp",
)

pkg_mklink(
    name = "check_ldaps_symlink",
    link_name = "lib/nagios/plugins/check_ldaps",
    tags = ["manual"],
    target = "check_ldap",
)

directory_path(
    name = "monitoring_plugins_share_dir",
    directory = ":monitoring_plugins_gen_dir",
    path = "share",
    tags = ["manual"],
)

copy_to_directory(
    name = "monitoring_plugins_share",
    srcs = [":monitoring_plugins_share_dir"],
    include_external_repositories = ["**"],
    root_paths = ["**/share"],
    tags = ["manual"],
)

pkg_files(
    name = "share_doc",
    srcs = [
        ":monitoring_plugins_share",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "share",
    strip_prefix = "monitoring_plugins_share",
    tags = ["manual"],
)

pkg_tar(
    name = "monitoring-plugins",
    srcs = [
        ":check_icmp_symlink",
        ":check_ldaps_symlink",
        ":libexec",
        ":share_doc",
    ],
    stamp = 1,
    tags = ["manual"],
    visibility = ["//omd:__pkg__"],
)
