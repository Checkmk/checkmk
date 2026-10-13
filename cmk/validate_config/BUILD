load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "validate_config",
    srcs = glob(
        include = ["**/*.py"],
        exclude = ["__main__.py"],
    ),
    imports = ["../.."],
    visibility = ["//:__subpackages__"],
    deps = [
        "//cmk/gui:core_toolkit",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:timeperiods",
        "//cmk/utils",
        "//packages/cmk-ccc:tty",
        requirement("pydantic"),
    ],
)

py_library(
    name = "__main__",
    srcs = ["__main__.py"],
    imports = ["../.."],
    visibility = ["//cmk:__pkg__"],
    deps = [
        ":validate_config",
        "//cmk/base",
        "//cmk/gui:app",
        "//cmk/gui:config",
        "//cmk/gui/watolib",
        "//cmk/utils:paths",
        "//cmk/utils:redis",
        "//packages/cmk-ccc:version",
        "//packages/cmk-wsgi",
    ],
)
