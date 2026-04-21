load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "theme",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/theme"],
    pytest_main = True,
    deps = [
        "//cmk/gui:theme",
        requirement("pytest"),
    ],
)
