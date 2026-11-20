load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "cmkcert",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:app",
        "//cmk/gui:config",
        "//cmk/gui/wato:base",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/utils",
        "//cmk/utils:paths",
        "//packages/cmk-ccc:config-path",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:version",
        "//packages/cmk-crypto",
        "//packages/cmk-relay-protocols",
        requirement("cryptography"),
        requirement("python-dateutil"),
    ],
)
