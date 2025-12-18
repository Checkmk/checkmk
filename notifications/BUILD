load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

pkg_files(
    name = "notifications_pkg",
    srcs = glob(
        ["*"],
        exclude = [
            ".f12",
            "BUILD",
            "OWNERS",
            "README",
        ],
    ),
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "share/check_mk/notifications",
)

pkg_files(
    name = "readme",
    srcs = ["README"],
    prefix = "share/check_mk/notifications",
)

pkg_files(
    name = "templates",
    srcs = glob(["templates/mail/*"]),
    prefix = "share/check_mk/notifications/templates/mail",
)

pkg_tar(
    name = "notifications",
    srcs = [
        ":notifications_pkg",
        ":readme",
        ":templates",
    ],
    stamp = 1,
    visibility = ["//omd:__pkg__"],
)
