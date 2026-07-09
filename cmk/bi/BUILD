load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "bi",
    srcs = glob(["**/*.py"]),
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//packages/cmk-maps:__pkg__",
        "//tests/unit:__subpackages__",
    ],
    deps = [
        "//cmk/fields",
        "//cmk/utils",
        "//cmk/utils:redis",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-livestatus-client",
        requirement("marshmallow"),
        requirement("marshmallow-oneofschema"),
        requirement("redis"),
        requirement("psutil"),
    ],
)
