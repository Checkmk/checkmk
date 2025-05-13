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
    name = "x86_64-linux-musl",
    constraint_values = [
        ":musl",
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
)

constraint_setting(
    name = "linker",
    default_constraint_value = ":linker_unknown",
)

constraint_value(
    name = "musl",
    constraint_setting = ":linker",
)

constraint_value(
    name = "linker_unknown",
    constraint_setting = ":linker",
)

platform(
    name = "x86_64-linux-gcc-hermetic",
    constraint_values = [
        ":hermetic",
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
    visibility = ["//visibility:public"],
)

constraint_setting(
    name = "hermeticity",
    default_constraint_value = ":hermeticity_unknown",
    visibility = ["//visibility:public"],
)

constraint_value(
    name = "hermetic",
    constraint_setting = ":hermeticity",
    visibility = ["//visibility:public"],
)

constraint_value(
    name = "hermeticity_unknown",
    constraint_setting = ":hermeticity",
    visibility = ["//visibility:public"],
)
