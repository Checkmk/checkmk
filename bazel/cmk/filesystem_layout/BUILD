load("@bazel_skylib//lib:selects.bzl", "selects")

package(default_visibility = ["//visibility:public"])

# For a discussion of Linux Standard Base (LSB) vs Filesystem Hierarchy Standard (FHS),
# see https://lists.linux-foundation.org/pipermail/lsb-discuss/2011-February/006674.html

# Current state: debian-based distros use LSB and the others, including el{8,9}
# and sles use FHS.

selects.config_setting_group(
    name = "lsb",
    match_any = [
        "//bazel/cmk/distro:debian",
        "//bazel/cmk/distro:ubuntu",
    ],
)

selects.config_setting_group(
    name = "fhs",
    match_any = [
        "//bazel/cmk/distro:almalinux",
        "//bazel/cmk/distro:sles",
    ],
)
