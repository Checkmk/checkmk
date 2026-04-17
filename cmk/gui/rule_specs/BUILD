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
    name = "legacy_converter",
    srcs = ["legacy_converter.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":compatibility",
        ":types",
        "//cmk/gui:agent_bakery",
        "//cmk/gui:exceptions",
        "//cmk/gui:i18n",
        "//cmk/gui/form_specs",
        "//cmk/gui/graphing",
        "//cmk/gui/inventory",
        "//cmk/gui/oauth2_connections",
        "//cmk/gui/oauth2_connections:watolib_store",
        "//cmk/gui/userdb",
        "//cmk/gui/utils:autocompleter_config",
        "//cmk/gui/utils:urls",
        "//cmk/gui/valuespec",
        "//cmk/gui/watolib",
        "//cmk/utils",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
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

py_library(
    name = "registering",
    srcs = ["registering.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":legacy_converter",
        ":loader",
        "//cmk/gui:i18n",
        "//cmk/gui:legacy_plugins",
        "//cmk/gui:log",
        "//cmk/gui/watolib",
        "//packages/cmk-ccc:debug",
    ],
)
