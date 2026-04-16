load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "legacy_bakery_rulesets",
    srcs = glob(include = ["**/*.py"]),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:agent_bakery",
        "//cmk/gui:exceptions",
        "//cmk/gui:i18n",
        "//cmk/gui:type_defs",
        "//cmk/gui/plugins/wato",
        "//cmk/gui/valuespec",
        "//cmk/gui/wato",
        "//cmk/gui/wato:base",
        "//cmk/gui/watolib",
    ],
)
