load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "plugins_siteless",
    testonly = True,
    srcs = glob(["**/*.py"]),
    imports = ["../.."],
    deps = [
        "//tests/testlib/common:empty_config",
        "//tests/testlib/common:repo",
        requirement("pytest"),
    ],
)
