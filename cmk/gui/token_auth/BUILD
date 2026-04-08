load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "token_auth",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:exceptions",
        "//cmk/gui:http",
        "//cmk/gui:pages",
        "//cmk/gui:type_defs",
        "//cmk/gui/utils:security_log_events",
        "//cmk/utils",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:user",
        requirement("python-dateutil"),
        requirement("pydantic"),
    ],
)
