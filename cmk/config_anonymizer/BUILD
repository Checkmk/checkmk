load("@aspect_rules_py//py:defs.bzl", "py_library")

exports_files([".f12"])

py_library(
    name = "config_anonymizer",
    srcs = glob(["**/*.py"]),
    imports = ["../.."],
    visibility = ["//cmk:__subpackages__"],
    deps = [
        "//cmk/base:app",
        "//cmk/base:base-app",
        "//cmk/base:config",
        "//cmk/base/configlib",
        "//cmk/checkengine",
        "//cmk/gui:config",
        "//cmk/gui:groups",
        "//cmk/gui:log",
        "//cmk/gui:main_modules",
        "//cmk/gui:script_helpers",
        "//cmk/gui:session",
        "//cmk/gui:site_config",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:groups_io",
        "//cmk/utils",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-livestatus-client",
    ],
)
