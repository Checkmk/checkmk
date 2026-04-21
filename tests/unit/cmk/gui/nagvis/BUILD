load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "nagvis",
    srcs = glob(["**/*.py"]),
    pytest_main = True,
    deps = [
        "//cmk/gui/nagvis",
        requirement("pytest"),
    ],
)
