load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:patchelf.bzl", "set_runpath")

set_runpath(
    name = "check_nrpe_runpath",
    srcs = ["@nrpe//:check_nrpe"],
    rpaths = ["${ORIGIN}/../../../lib"],
)

pkg_files(
    name = "check_nrpe",
    srcs = [
        ":check_nrpe_runpath",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "lib/nagios/plugins",
    tags = ["manual"],
)

pkg_tar(
    name = "nrpe",
    srcs = [
        ":check_nrpe",
    ],
    stamp = 1,
    tags = ["manual"],
    visibility = ["//omd:__pkg__"],
)
