load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "gui",
    testonly = True,
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//non-free/packages/cmk-robotmk:__pkg__",
        "//tests:__pkg__",
        "//tests/testlib/unit:__pkg__",
        "//tests/unit:__subpackages__",
    ],
    deps = [
        "//cmk/base:app",
        "//cmk/base:config",
        "//cmk/gui",
        "//tests:rest_api_client",
        "//tests/testlib/common:empty_config",
        "//tests/testlib/common:repo",
        "//tests/testlib/common:utils",
        requirement("flask"),
        requirement("pytest-mock"),
        requirement("pytest"),
        requirement("werkzeug"),
    ],
)
