load("@rules_pkg//:pkg.bzl", "pkg_tar", "pkg_zip")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mklink")

pkg_zip(
    name = "oci_light_win_x64",
    srcs = ["@oci-basic-light-win-x64//:srcs"],
    stamp = 1,
    tags = ["manual"],
    visibility = ["//visibility:public"],
)

pkg_files(
    name = "oci_light_win_x64_pkg",
    srcs = [":oci_light_win_x64"],
    attributes = pkg_attributes(mode = "0644"),
    renames = {":oci_light_win_x64": "share/check_mk/agents/packages/mk-oracle/oci_light_win_x64.zip"},
    tags = ["manual"],
)

pkg_tar(
    name = "oci_light_win_x64.tar",
    srcs = [":oci_light_win_x64_pkg"],
    tags = ["manual"],
    visibility = ["//visibility:public"],
)

clntsh_symlinks = [
    "libclntsh.so",
    "libclntsh.so.10.1",
    "libclntsh.so.11.1",
    "libclntsh.so.12.1",
    "libclntsh.so.18.1",
    "libclntsh.so.19.1",
    "libclntsh.so.20.1",
]

clntshcore_symlinks = [
    "libclntshcore.so",
    "libclntshcore.so.12.1",
    "libclntshcore.so.18.1",
    "libclntshcore.so.19.1",
    "libclntshcore.so.20.1",
]

occi_symlinks = [
    "libocci.so",
    "libocci.so.10.1",
    "libocci.so.11.1",
    "libocci.so.12.1",
    "libocci.so.18.1",
    "libocci.so.19.1",
    "libocci.so.20.1",
]

[pkg_mklink(
    name = link_name,
    link_name = link_name,
    tags = ["manual"],
    target = "libclntsh.so.21.1",
) for link_name in clntsh_symlinks]

[pkg_mklink(
    name = "core" + link_name,
    link_name = link_name,
    tags = ["manual"],
    target = "libclntshcore.so.21.1",
) for link_name in clntshcore_symlinks]

[pkg_mklink(
    name = "occi" + link_name,
    link_name = link_name,
    tags = ["manual"],
    target = "libocci.so.21.1",
) for link_name in occi_symlinks]

pkg_mklink(
    name = "libocci_gcc53.so",
    link_name = "libocci_gcc53.so",
    tags = ["manual"],
    target = "libocci_gcc53.so.21.1",
)

pkg_zip(
    name = "oci_light_lin_x64",
    srcs = [
               ":libocci_gcc53.so",
               "@oci-basic-light-lin-x64//:srcs",
           ] + [":%s" % link_name for link_name in clntsh_symlinks] +
           [":core%s" % link_name for link_name in clntshcore_symlinks] +
           [":occi%s" % link_name for link_name in occi_symlinks],
    mode = "0644",
    stamp = 1,
    tags = ["manual"],
)

pkg_files(
    name = "oci_light_lin_x64_files",
    srcs = [":oci_light_lin_x64"],
    attributes = pkg_attributes(mode = "0644"),
    renames = {":oci_light_lin_x64": "share/check_mk/agents/packages/mk-oracle/oci_light_lin_x64.zip"},
    tags = ["manual"],
)

pkg_tar(
    name = "oci_light_lin_x64.tar",
    srcs = [":oci_light_lin_x64_files"],
    tags = ["manual"],
    visibility = ["//visibility:public"],
)
