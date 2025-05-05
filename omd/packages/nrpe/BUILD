load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

pkg_files(
    name = "check_nrpe",
    srcs = [
        "@nrpe//:check_nrpe",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "lib/nagios/plugins",
)

pkg_tar(
    name = "nrpe",
    srcs = [
        ":check_nrpe",
    ],
    visibility = ["//omd:__pkg__"],
)
