load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "watolib_store",
    srcs = ["watolib/store.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:exceptions",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:passwords",
        "//cmk/utils",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:user",
    ],
)

# Temporary: oauth2_connections files that still belong to the monolithic //cmk/gui target.
# Remove this filegroup once oauth2_connections is fully extracted.
filegroup(
    name = "gui_srcs",
    srcs = glob(
        include = ["**/*.py"],
        exclude = ["watolib/store.py"],
    ),
    visibility = ["//cmk/gui:__pkg__"],
)
