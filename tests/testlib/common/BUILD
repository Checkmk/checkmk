load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "repo",
    srcs = ["repo.py"],
    imports = ["../../.."],
    visibility = [
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
        "//tests:__subpackages__",
    ],
    deps = [
        ":repo",
        "//cmk/base/configlib",
        "//cmk/utils",
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
    srcs = ["empty_config.py"],
    imports = ["../../.."],
    visibility = [
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/base",
        "//cmk/utils",
    ],
)
