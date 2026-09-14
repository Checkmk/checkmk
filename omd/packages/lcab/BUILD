load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:patchelf.bzl", "set_runpath")
load("//bazel/rules:xcomp/transition_wrapper.bzl", "platform_transitioned_target")

platform_transitioned_target(
    name = "hermetic_lcab",
    platform = "//bazel/platforms:x86_64-linux-gcc-hermetic",
    target = "@lcab",
)

set_runpath(
    name = "lcab_runpath",
    srcs = [":hermetic_lcab"],
    rpaths = ["${ORIGIN}/../lib"],
)

pkg_files(
    name = "lcab_bin",
    srcs = [":lcab_runpath"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    tags = ["manual"],
)

pkg_tar(
    name = "lcab",
    srcs = [
        "lcab_bin",
    ],
    stamp = 1,
    tags = ["manual"],
    visibility = ["//omd:__pkg__"],
)
