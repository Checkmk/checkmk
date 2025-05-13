platform(
    name = "x86_64-unknown-linux-musl",
    constraint_values = [
        ":musl",
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
    visibility = ["//visibility:public"],
)

constraint_setting(
    name = "linker",
    default_constraint_value = ":unknown",
    visibility = ["//visibility:public"],
)

constraint_value(
    name = "musl",
    constraint_setting = ":linker",
    visibility = ["//visibility:public"],
)

constraint_value(
    name = "unknown",
    constraint_setting = ":linker",
    visibility = ["//visibility:public"],
)
