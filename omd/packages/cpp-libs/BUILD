load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

# Select cpp_libs source based on active toolchain:
# - Bootlin GCC (hermetic): use Bootlin libraries
# - Local GCC (non-hermetic): use unified local GCC libraries that auto-select based on gcc_path flag
pkg_files(
    name = "cpp-libs-pkg",
    srcs = select({
        # When using Bootlin GCC toolchain (hermetic platform) - uses same constraint_value as toolchain
        "//bazel/platforms:is_hermetic": ["@gcc-linux-x86_64//:cpp_libs"],
        # When using local GCC toolchain - unified target handles gcc_path selection internally
        "//conditions:default": ["//bazel/toolchains/cc/gcc/local:cpp_libs"],
    }),
    prefix = "lib",
    tags = ["manual"],
)

pkg_tar(
    name = "cpp-libs",
    srcs = [
        "cpp-libs-pkg",
    ],
    stamp = 1,
    tags = ["manual"],
    visibility = ["//visibility:public"],
)
