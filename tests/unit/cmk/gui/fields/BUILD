load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "fields",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/fields"],
    pytest_main = True,
    deps = [
        "//cmk/gui/fields",
        "//cmk/gui/fields:base",
        requirement("marshmallow"),
        requirement("pytest"),
    ],
)
