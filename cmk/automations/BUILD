load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "automations",
    srcs = [
        "__init__.py",
        "types.py",
    ] + glob([
        "backends/*.py",
        "models/*.py",
        "models/**/*.py",
        "results/*.py",
    ]),
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/checkengine",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:i18n",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:version",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-trace",
        requirement("requests"),
    ],
)
