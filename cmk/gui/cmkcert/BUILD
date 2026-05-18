load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "cmkcert",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//bin:__pkg__",
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:config",
        "//cmk/gui/wato:base",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/utils",
        "//cmk/utils:paths",
        "//packages/cmk-ccc:site",
        "//packages/cmk-crypto",
        requirement("python-dateutil"),
    ],
)
