load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "notifications",
    srcs = [
        "notifications_rule_types.py",
        "notifications_types.py",
    ],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui/watolib:tag_config_file",
        "//cmk/utils",
        "//packages/cmk-ec",
    ],
)

# Temporary: rest_api_types files that still belong to the monolithic //cmk/gui target.
# Remove this filegroup once rest_api_types is fully extracted.
filegroup(
    name = "gui_srcs",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "notifications_rule_types.py",
            "notifications_types.py",
        ],
    ),
    visibility = ["//cmk/gui:__pkg__"],
)
