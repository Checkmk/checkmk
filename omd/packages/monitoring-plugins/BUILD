load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mklink")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:exclude_from_filegroup.bzl", "exclude_from_filegroup")
load("//bazel/rules:make_deployable.bzl", "make_deployable_dir")

exports_files(
    [
        # needed to allow `cmk_password_store.h` to be used
        "cmk_password_store.h",
    ],
    visibility = ["//visibility:public"],
)

make_deployable_dir(
    name = "monitoring-plugins_deployable_libexec",
    src = "@monitoring-plugins//:gen_dir",
    input_dir = "libexec",
    rpath = "\\$ORIGIN/../../../lib",
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
    strip_prefix = "libexec",
)

pkg_mklink(
    name = "check_icmp_symlink",
    link_name = "lib/nagios/plugins/check_host",
    target = "check_icmp",
)

pkg_mklink(
    name = "check_ldaps_symlink",
    link_name = "lib/nagios/plugins/check_ldaps",
    target = "check_ldap",
)

exclude_from_filegroup(
    name = "share",
    src = "@monitoring-plugins//:gen_dir",
    excludes = [
        "libexec/*",
        "include/*",
    ],
)

pkg_files(
    name = "share_doc",
    srcs = [
        ":share",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    strip_prefix = "rest",
)

pkg_tar(
    name = "monitoring-plugins",
    srcs = [
        ":check_icmp_symlink",
        ":check_ldaps_symlink",
        ":libexec",
        ":share_doc",
    ],
    visibility = ["//omd:__pkg__"],
)
