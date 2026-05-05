load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "unit",
    size = "small",
    srcs = glob(["*.py"]),
    pytest_main = True,
    deps = [
        "//packages/cmk-web/cmk/web/utils",
        requirement("pytest"),
    ],
)
