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

# Default linker for anyone not setting the linker to `musl`.
# You shouldn't ever need to set this value manually.
constraint_value(
    name = "unknown",
    constraint_setting = ":linker",
    visibility = ["//visibility:public"],
)
