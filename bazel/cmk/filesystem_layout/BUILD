load("@bazel_skylib//rules:common_settings.bzl", "string_flag")

package(default_visibility = ["//visibility:public"])

string_flag(
    # For a discussion of Linux Standard Base (LSB) vs Filesystem Hierarchy Standard (FHS),
    # see https://lists.linux-foundation.org/pipermail/lsb-discuss/2011-February/006674.html
    #
    # Current state: debian-based distros use LSB and the others, including el{8,9} and sles
    # use FHS.
    name = "filesystem_layout",
    build_setting_default = "FILESYSTEM_LAYOUT_INVALID",
    visibility = ["//visibility:public"],
)

config_setting(
    name = "lsb",
    flag_values = {":filesystem_layout": "lsb"},
)

config_setting(
    name = "fhs",
    flag_values = {":filesystem_layout": "fhs"},
)
