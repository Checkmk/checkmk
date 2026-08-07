load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "oauth",
    srcs = glob(
        include = ["**/*.py"],
    ),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        requirement("pydantic"),
        requirement("redis"),
        "//cmk/gui:core_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui:scopes",
        "//cmk/gui/utils:csrf_token",
        "//cmk/gui/wato:base",
        "//cmk/gui/watolib",
        "//cmk/utils:paths",
        "//cmk/utils:redis",
        "//packages/cmk-ccc:site",
    ],
)
