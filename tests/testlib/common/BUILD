load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "repo",
    srcs = ["repo.py"],
    imports = ["../../.."],
    visibility = [
        "//non-free/tests:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [],
)

py_library(
    name = "utils",
    srcs = [
        "utils.py",
        "utils2.py",
    ],
    imports = ["../../.."],
    visibility = [
        "//buildscripts/scripts:__pkg__",
        "//non-free/packages/cmk-metric-backend:__pkg__",
        "//non-free/tests:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":repo",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-trace",
        requirement("beautifulsoup4"),
        requirement("pexpect"),
        requirement("psutil"),
        requirement("pyyaml"),
    ],
)

py_library(
    name = "empty_config",
    testonly = True,
    srcs = ["empty_config.py"],
    imports = ["../../.."],
    visibility = [
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/base",
        "//cmk/utils:paths",
        "//packages/cmk-ruleset-matcher",
    ],
)
