load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "types",
    srcs = ["types.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-plugin-apis:rulesets",
    ],
)

py_library(
    name = "loader",
    srcs = ["loader.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui/rule_specs:compatibility",
        "//cmk/gui/rule_specs:types",
        "//packages/cmk-ccc:version",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-plugin-apis:rulesets",
    ],
)

py_library(
    name = "compatibility",
    srcs = ["compatibility.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui/form_specs",
        "//cmk/gui/rule_specs:types",
        "//packages/cmk-plugin-apis:rulesets",
    ],
)

# Temporary: rule_specs files that still belong to the monolithic //cmk/gui target.
# Remove this filegroup once rule_specs is fully extracted.
filegroup(
    name = "gui_srcs",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "compatibility.py",
            "loader.py",
            "types.py",
        ],
    ),
    visibility = ["//cmk/gui:__pkg__"],
)
