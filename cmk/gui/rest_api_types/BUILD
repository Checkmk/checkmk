load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "notifications",
    srcs = [
        "notifications_rule_types.py",
        "notifications_types.py",
        "site_connection.py",
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
