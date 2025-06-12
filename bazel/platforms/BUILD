load("@bazel_skylib//lib:selects.bzl", "selects")

package(default_visibility = ["//visibility:public"])

selects.config_setting_group(
    name = "linux_x86_64",
    match_all = [
        "@platforms//os:linux",
        "@platforms//cpu:x86_64",
    ],
)

platform(
    name = "x86_64-unknown-linux-musl",
    constraint_values = [
        ":musl",
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
)

constraint_setting(
    name = "linker",
    default_constraint_value = ":unknown",
)

constraint_value(
    name = "musl",
    constraint_setting = ":linker",
)

constraint_value(
    name = "unknown",
    constraint_setting = ":linker",
)
