load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@rules_pkg//:pkg.bzl", "pkg_tar")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")

pkg_files(
    name = "cma_conf",
    srcs = [
        "cma.conf",
    ],
    attributes = pkg_attributes(
        mode = "0644",
    ),
    prefix = "skel/etc/apache/conf.d/",
    tags = ["manual"],
)

pkg_files(
    name = "post_install",
    srcs = [
        "post-install",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "lib/cma",
    tags = ["manual"],
)

pkg_files(
    name = "webconf_snapin",
    srcs = [
        "webconf_snapin.py",
    ],
    attributes = pkg_attributes(
        mode = "0644",
    ),
    prefix = "lib/python3/cmk/gui/plugins/sidebar",
    tags = ["manual"],
)

write_file(
    name = "cma_info_file",
    out = "cma.info",
    content = select(
        {
            "@cmk//distro:debian-12": [
                "MIN_VERSION=1.7.0",
                "",
            ],
            "//conditions:default": [""],
        },
    ),
    target_compatible_with = select(
        {
            "@cmk//distro:debian-12": [],
            "//conditions:default": ["@platforms//:incompatible"],
        },
    ),
)

pkg_files(
    name = "cma_info_file_in_pkg",
    srcs = [
        ":cma_info_file",
    ],
    tags = ["manual"],
)

[
    pkg_tar(
        name = "appliance_install_" + edition,
        srcs = [
            ":cma_conf",
            ":cma_info_file_in_pkg",
            ":post_install",
            ":webconf_snapin",
        ],
        extension = "tar.gz",
        visibility = ["//visibility:public"],
    )
    for edition in [
        "pro",
        "ultimate",
        "ultimatemt",
    ]
]
