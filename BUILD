load("@bazel_skylib//rules:common_settings.bzl", "string_flag")
load("@hedron_compile_commands//:refresh_compile_commands.bzl", "refresh_compile_commands")

exports_files([
    "Pipfile",
    "Pipfile.lock",
])

string_flag(
    name = "cmk_version",
    build_setting_default = "UNSET",
    visibility = ["//:__subpackages__"],
)

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
    name = "lsb_filesystem_layout",
    flag_values = {":filesystem_layout": "lsb"},
)

config_setting(
    name = "fhs_filesystem_layout",
    flag_values = {":filesystem_layout": "fhs"},
)

# Generate `compile_commands.json` with `bazel run //:refresh_compile_commands`.
refresh_compile_commands(
    name = "refresh_compile_commands",
    # TODO: Do we want that or not? We get quite a few duplicate entries which often differ without that option.
    # exclude_headers = "all",
    targets = {
        # target: build-flags
        "//packages/cmc:all": "",
        "//packages/livestatus:all": "",
        "//packages/neb:all": "",
        "//packages/unixcat:all": "",
    },
)
