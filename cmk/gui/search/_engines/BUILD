load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "_helpers",
    srcs = [
        "__init__.py",
        "_helpers.py",
    ],
    imports = ["../../../.."],
    visibility = ["//visibility:private"],
    deps = [
        "//cmk/gui:core_toolkit",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)

py_library(
    name = "_livestatus",
    srcs = ["_livestatus.py"],
    imports = ["../../../.."],
    visibility = [
        "//cmk/gui/search:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":_helpers",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/search:matchers",
        "//cmk/gui/utils",
        "//cmk/gui/utils:middle",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-ruleset-matcher",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
        "//packages/cmk-web/cmk/web/utils",
    ],
)

py_library(
    name = "_redis",
    srcs = ["_redis.py"],
    imports = ["../../../.."],
    visibility = [
        "//cmk/gui/search:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":_helpers",
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:session_context",
        "//cmk/gui/background_job/job",
        "//cmk/gui/search:_routing",
        "//cmk/gui/search:index",
        "//cmk/gui/search:matchers",
        "//cmk/gui/search:permissions",
        "//cmk/gui/utils",
        "//cmk/gui/utils:middle",
        "//cmk/utils:redis",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
        requirement("pydantic"),
        requirement("redis"),
    ],
)
