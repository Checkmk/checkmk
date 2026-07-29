load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "validate_config",
    srcs = glob(["**/*.py"]),
    imports = ["../.."],
    tags = [
        "deballast-keep=//cmk/gui:app",  # GUI plugin tree loaded at runtime to populate the config/ruleset registries
        "deballast-keep=//cmk/gui/form_specs:form_specs",  # form specs registered at runtime with the GUI plugin tree
        "deballast-keep=//cmk/gui/watolib:registries",  # registries populated at runtime with the GUI plugin tree
    ],
    visibility = ["//:__subpackages__"],
    deps = [
        "//cmk/gui:app",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/form_specs",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:registries",
        "//cmk/gui/watolib:timeperiods",
        "//cmk/utils",
        "//packages/cmk-ccc:tty",
        requirement("pydantic"),
    ],
)
