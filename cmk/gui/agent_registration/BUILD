load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "agent_registration",
    srcs = glob(include = ["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:exceptions",
        "//cmk/gui:i18n",
        "//cmk/gui:logged_in",
        "//cmk/gui:permissions",
        "//cmk/gui/fields:base",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/framework:core",
        "//cmk/gui/openapi/framework:types",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/token_auth",
        "//cmk/gui/utils:roles",
        "//cmk/gui/watolib",
        "//cmk/utils",
        "//packages/cmk-ccc:version",
        requirement("python-dateutil"),
    ],
)
